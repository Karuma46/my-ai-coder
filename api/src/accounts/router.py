from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from src.accounts.dependencies import AccountServiceDep, CurrentUser
from src.accounts.schemas import (
    AddCompanyMemberRequest,
    CompanyMemberResponse,
    CompanyResponse,
    CreateCompanyRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateCompanyMemberRequest,
    UpdateCompanyRequest,
    UpdateMeRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1")
CompanyId = Annotated[str, Path(alias="companyId", min_length=1)]
UserId = Annotated[str, Path(alias="userId", min_length=1)]


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register a user and issue an access token",
)
async def register(
    payload: RegisterRequest,
    service: AccountServiceDep,
) -> TokenResponse:
    return await service.register(payload)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Sign in with email and password",
)
async def login(payload: LoginRequest, service: AccountServiceDep) -> TokenResponse:
    return await service.login(payload)


@router.get(
    "/me",
    response_model=UserResponse,
    tags=["Account"],
    summary="Get the signed-in user",
)
async def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    tags=["Account"],
    summary="Update the signed-in user's profile",
)
async def update_me(
    payload: UpdateMeRequest,
    user: CurrentUser,
    service: AccountServiceDep,
):
    return await service.update_me(user, payload)


@router.get(
    "/companies",
    response_model=list[CompanyResponse],
    tags=["Companies"],
    summary="List companies the signed-in user belongs to",
)
async def list_companies(
    user: CurrentUser,
    service: AccountServiceDep,
) -> list[CompanyResponse]:
    return await service.list_companies(user)


@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Companies"],
    summary="Create a company and become its owner",
)
async def create_company(
    payload: CreateCompanyRequest,
    user: CurrentUser,
    service: AccountServiceDep,
) -> CompanyResponse:
    return await service.create_company(user, payload)


@router.get(
    "/companies/{companyId}",
    response_model=CompanyResponse,
    tags=["Companies"],
    summary="Get a company",
)
async def get_company(
    company_id: CompanyId,
    user: CurrentUser,
    service: AccountServiceDep,
) -> CompanyResponse:
    return await service.get_company(user, company_id)


@router.patch(
    "/companies/{companyId}",
    response_model=CompanyResponse,
    tags=["Companies"],
    summary="Update a company",
)
async def update_company(
    company_id: CompanyId,
    payload: UpdateCompanyRequest,
    user: CurrentUser,
    service: AccountServiceDep,
) -> CompanyResponse:
    return await service.update_company(user, company_id, payload)


@router.get(
    "/companies/{companyId}/members",
    response_model=list[CompanyMemberResponse],
    tags=["Companies"],
    summary="List company members",
)
async def list_members(
    company_id: CompanyId,
    user: CurrentUser,
    service: AccountServiceDep,
) -> list[CompanyMemberResponse]:
    return await service.list_members(user, company_id)


@router.post(
    "/companies/{companyId}/members",
    response_model=CompanyMemberResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Companies"],
    summary="Add a registered user to a company",
)
async def add_member(
    company_id: CompanyId,
    payload: AddCompanyMemberRequest,
    user: CurrentUser,
    service: AccountServiceDep,
) -> CompanyMemberResponse:
    return await service.add_member(user, company_id, payload)


@router.patch(
    "/companies/{companyId}/members/{userId}",
    response_model=CompanyMemberResponse,
    tags=["Companies"],
    summary="Change a company member's role",
)
async def update_member(
    company_id: CompanyId,
    user_id: UserId,
    payload: UpdateCompanyMemberRequest,
    user: CurrentUser,
    service: AccountServiceDep,
) -> CompanyMemberResponse:
    return await service.update_member(user, company_id, user_id, payload)


@router.delete(
    "/companies/{companyId}/members/{userId}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Companies"],
    summary="Remove a company member",
)
async def remove_member(
    company_id: CompanyId,
    user_id: UserId,
    user: CurrentUser,
    service: AccountServiceDep,
) -> Response:
    await service.remove_member(user, company_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
