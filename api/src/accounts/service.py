from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.config import AuthSettings
from src.accounts.exceptions import (
    AccountConflictError,
    AccountForbiddenError,
    AccountNotFoundError,
    AuthenticationError,
)
from src.accounts.models import Company, CompanyMembership, User
from src.accounts.schemas import (
    AddCompanyMemberRequest,
    CompanyMemberResponse,
    CompanyResponse,
    CompanyRole,
    CreateCompanyRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateCompanyMemberRequest,
    UpdateCompanyRequest,
    UpdateMeRequest,
    UserResponse,
)
from src.accounts.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from src.projects.models import Project
from src.projects.utils import slugify

LEGACY_COMPANY_ID = "legacy-workspace"


class AccountService:
    def __init__(self, session: AsyncSession, settings: AuthSettings) -> None:
        self.session = session
        self.settings = settings

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        existing = await self.session.scalar(select(User).where(User.email == payload.email))
        if existing is not None:
            raise AccountConflictError("A user with this email already exists")

        user = User(
            id=str(uuid4()),
            name=payload.name.strip(),
            email=str(payload.email),
            password_hash=hash_password(payload.password),
        )
        self.session.add(user)
        await self.session.flush()
        legacy_company = await self.session.get(Company, LEGACY_COMPANY_ID)
        if legacy_company is not None:
            member_count = await self.session.scalar(
                select(func.count())
                .select_from(CompanyMembership)
                .where(CompanyMembership.company_id == LEGACY_COMPANY_ID)
            )
            if member_count == 0:
                self.session.add(
                    CompanyMembership(
                        company_id=LEGACY_COMPANY_ID,
                        user_id=user.id,
                        role=CompanyRole.OWNER,
                    )
                )
        await self._commit()
        await self.session.refresh(user)
        return self._token_response(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.session.scalar(select(User).where(User.email == payload.email))
        if user is None:
            verify_dummy_password(payload.password)
            raise AuthenticationError("Invalid email or password")
        if not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return self._token_response(user)

    async def update_me(self, user: User, payload: UpdateMeRequest) -> User:
        values = payload.model_dump(exclude_unset=True)
        if "avatar_url" in values and values["avatar_url"] is not None:
            values["avatar_url"] = str(values["avatar_url"])
        for field, value in values.items():
            setattr(user, field, value)
        user.updated_at = datetime.now(UTC)
        await self._commit()
        await self.session.refresh(user)
        return user

    async def create_company(
        self,
        user: User,
        payload: CreateCompanyRequest,
    ) -> CompanyResponse:
        base_id = slugify(payload.name, fallback="company")
        company_id = base_id
        if await self.session.get(Company, company_id) is not None:
            company_id = f"{base_id}-{uuid4().hex[:8]}"
        company = Company(id=company_id, name=payload.name.strip())
        self.session.add(company)
        self.session.add(
            CompanyMembership(
                company_id=company.id,
                user_id=user.id,
                role=CompanyRole.OWNER,
            )
        )
        await self._commit()
        return await self.get_company(user, company.id)

    async def list_companies(self, user: User) -> list[CompanyResponse]:
        memberships = list(
            await self.session.scalars(
                select(CompanyMembership)
                .where(CompanyMembership.user_id == user.id)
                .options(selectinload(CompanyMembership.company))
                .order_by(CompanyMembership.created_at, CompanyMembership.company_id)
            )
        )
        return [
            await self._company_response(membership.company, CompanyRole(membership.role))
            for membership in memberships
        ]

    async def get_company(self, user: User, company_id: str) -> CompanyResponse:
        membership = await self._membership(user.id, company_id)
        return await self._company_response(
            membership.company,
            CompanyRole(membership.role),
        )

    async def update_company(
        self,
        owner: User,
        company_id: str,
        payload: UpdateCompanyRequest,
    ) -> CompanyResponse:
        membership = await self._require_owner(owner.id, company_id)
        membership.company.name = payload.name.strip()
        membership.company.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_company(owner, company_id)

    async def list_members(
        self,
        user: User,
        company_id: str,
    ) -> list[CompanyMemberResponse]:
        await self._membership(user.id, company_id)
        memberships = list(
            await self.session.scalars(
                select(CompanyMembership)
                .where(CompanyMembership.company_id == company_id)
                .options(selectinload(CompanyMembership.user))
                .order_by(CompanyMembership.created_at, CompanyMembership.user_id)
            )
        )
        return [self._member_response(membership) for membership in memberships]

    async def add_member(
        self,
        owner: User,
        company_id: str,
        payload: AddCompanyMemberRequest,
    ) -> CompanyMemberResponse:
        await self._require_owner(owner.id, company_id)
        user = await self.session.scalar(select(User).where(User.email == payload.email))
        if user is None:
            raise AccountNotFoundError("No registered user has this email")
        if await self.session.get(CompanyMembership, (company_id, user.id)) is not None:
            raise AccountConflictError("The user already belongs to this company")
        membership = CompanyMembership(
            company_id=company_id,
            user_id=user.id,
            role=payload.role,
        )
        self.session.add(membership)
        await self._commit()
        return self._member_response(await self._membership(user.id, company_id))

    async def update_member(
        self,
        owner: User,
        company_id: str,
        user_id: str,
        payload: UpdateCompanyMemberRequest,
    ) -> CompanyMemberResponse:
        await self._require_owner(owner.id, company_id)
        membership = await self._membership(user_id, company_id)
        if (
            membership.role == CompanyRole.OWNER
            and payload.role is CompanyRole.MEMBER
            and await self._owner_count(company_id) == 1
        ):
            raise AccountConflictError("A company must retain at least one owner")
        membership.role = payload.role
        membership.updated_at = datetime.now(UTC)
        await self._commit()
        return self._member_response(await self._membership(user_id, company_id))

    async def remove_member(
        self,
        owner: User,
        company_id: str,
        user_id: str,
    ) -> None:
        await self._require_owner(owner.id, company_id)
        membership = await self._membership(user_id, company_id)
        if membership.role == CompanyRole.OWNER and await self._owner_count(company_id) == 1:
            raise AccountConflictError("A company must retain at least one owner")
        await self.session.delete(membership)
        await self._commit()

    async def _membership(self, user_id: str, company_id: str) -> CompanyMembership:
        membership = await self.session.scalar(
            select(CompanyMembership)
            .where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.user_id == user_id,
            )
            .options(
                selectinload(CompanyMembership.company),
                selectinload(CompanyMembership.user),
            )
        )
        if membership is None:
            raise AccountNotFoundError("Company or membership was not found")
        return membership

    async def _require_owner(
        self,
        user_id: str,
        company_id: str,
    ) -> CompanyMembership:
        membership = await self._membership(user_id, company_id)
        if membership.role != CompanyRole.OWNER:
            raise AccountForbiddenError("Only company owners can manage this company")
        return membership

    async def _owner_count(self, company_id: str) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(CompanyMembership)
                .where(
                    CompanyMembership.company_id == company_id,
                    CompanyMembership.role == CompanyRole.OWNER,
                )
            )
            or 0
        )

    async def _company_response(
        self,
        company: Company,
        role: CompanyRole,
    ) -> CompanyResponse:
        member_count = int(
            await self.session.scalar(
                select(func.count())
                .select_from(CompanyMembership)
                .where(CompanyMembership.company_id == company.id)
            )
            or 0
        )
        project_count = int(
            await self.session.scalar(
                select(func.count()).select_from(Project).where(Project.company_id == company.id)
            )
            or 0
        )
        return CompanyResponse(
            id=company.id,
            name=company.name,
            role=role,
            member_count=member_count,
            project_count=project_count,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )

    @staticmethod
    def _member_response(membership: CompanyMembership) -> CompanyMemberResponse:
        return CompanyMemberResponse(
            user=UserResponse.model_validate(membership.user),
            role=CompanyRole(membership.role),
            joined_at=membership.created_at,
        )

    def _token_response(self, user: User) -> TokenResponse:
        token, expires_in = create_access_token(user.id, self.settings)
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        )

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AccountConflictError(
                "The operation conflicts with existing account data"
            ) from exc
