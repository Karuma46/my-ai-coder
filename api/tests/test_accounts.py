from collections.abc import AsyncIterator

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.accounts.config import get_auth_settings
from src.accounts.models import Company
from src.accounts.service import LEGACY_COMPANY_ID
from src.database import Base, get_db
from src.github.dependencies import get_github_service
from src.main import app


@pytest.fixture
async def account_client(tmp_path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'accounts.db'}"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    class FakeGithub:
        def validate_repository(self, repository: str) -> None:
            return None

    async def override_github():
        return FakeGithub()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_github_service] = override_github
    app.state.account_session_factory = session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    del app.state.account_session_factory
    await engine.dispose()


async def register_user(
    client: AsyncClient,
    *,
    name: str,
    email: str,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201
    return response.json()


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_registration_login_and_current_user(account_client: AsyncClient) -> None:
    registered = await register_user(
        account_client,
        name="Owner User",
        email="OWNER@example.com",
    )
    token = str(registered["accessToken"])
    settings = get_auth_settings()
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    assert claims["sub"] == registered["user"]["id"]

    me_response = await account_client.get("/api/v1/me", headers=authorization(token))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "owner@example.com"

    login_response = await account_client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert login_response.status_code == 200
    assert login_response.json()["tokenType"] == "bearer"

    invalid_login = await account_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["error"]["code"] == "UNAUTHORIZED"

    unauthenticated = await account_client.get("/api/v1/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"


async def test_first_registered_user_claims_legacy_workspace(
    account_client: AsyncClient,
) -> None:
    async with app.state.account_session_factory() as session:
        session.add(Company(id=LEGACY_COMPANY_ID, name="Legacy Workspace"))
        await session.commit()

    registered = await register_user(
        account_client,
        name="First User",
        email="first@example.com",
    )
    companies = await account_client.get(
        "/api/v1/companies",
        headers=authorization(str(registered["accessToken"])),
    )

    assert companies.status_code == 200
    assert companies.json()[0]["id"] == LEGACY_COMPANY_ID
    assert companies.json()[0]["role"] == "owner"


async def test_only_owners_add_members_and_projects_are_company_scoped(
    account_client: AsyncClient,
) -> None:
    owner = await register_user(
        account_client,
        name="Company Owner",
        email="owner@example.com",
    )
    member = await register_user(
        account_client,
        name="Company Member",
        email="member@example.com",
    )
    outsider = await register_user(
        account_client,
        name="Outside User",
        email="outside@example.com",
    )
    owner_headers = authorization(str(owner["accessToken"]))
    member_headers = authorization(str(member["accessToken"]))
    outsider_headers = authorization(str(outsider["accessToken"]))

    company_response = await account_client.post(
        "/api/v1/companies",
        json={"name": "Acme"},
        headers=owner_headers,
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    assert company_response.json()["role"] == "owner"

    updated_company = await account_client.patch(
        f"/api/v1/companies/{company_id}",
        json={"name": "Acme Roadmaps"},
        headers=owner_headers,
    )
    assert updated_company.status_code == 200
    assert updated_company.json()["name"] == "Acme Roadmaps"

    remove_last_owner = await account_client.patch(
        f"/api/v1/companies/{company_id}/members/{owner['user']['id']}",
        json={"role": "member"},
        headers=owner_headers,
    )
    assert remove_last_owner.status_code == 409

    add_member_response = await account_client.post(
        f"/api/v1/companies/{company_id}/members",
        json={"email": "member@example.com"},
        headers=owner_headers,
    )
    assert add_member_response.status_code == 201
    assert add_member_response.json()["role"] == "member"

    member_company = await account_client.post(
        "/api/v1/companies",
        json={"name": "Member Owned Company"},
        headers=member_headers,
    )
    assert member_company.status_code == 201
    member_companies = await account_client.get(
        "/api/v1/companies",
        headers=member_headers,
    )
    assert {company["role"] for company in member_companies.json()} == {
        "member",
        "owner",
    }

    forbidden_add = await account_client.post(
        f"/api/v1/companies/{company_id}/members",
        json={"email": "outside@example.com"},
        headers=member_headers,
    )
    assert forbidden_add.status_code == 403
    assert forbidden_add.json()["error"]["code"] == "FORBIDDEN"

    forbidden_update = await account_client.patch(
        f"/api/v1/companies/{company_id}",
        json={"name": "Member Rename"},
        headers=member_headers,
    )
    assert forbidden_update.status_code == 403

    project_response = await account_client.post(
        "/api/v1/projects",
        json={
            "companyId": company_id,
            "name": "Acme API",
            "path": "/acme-api",
        },
        headers=member_headers,
    )
    assert project_response.status_code == 201
    assert project_response.json()["companyId"] == company_id

    member_projects = await account_client.get(
        "/api/v1/projects",
        headers=member_headers,
    )
    assert [project["id"] for project in member_projects.json()["items"]] == ["acme-api"]

    outsider_projects = await account_client.get(
        "/api/v1/projects",
        headers=outsider_headers,
    )
    assert outsider_projects.status_code == 200
    assert outsider_projects.json()["items"] == []

    hidden_project = await account_client.get(
        "/api/v1/projects/acme-api",
        headers=outsider_headers,
    )
    assert hidden_project.status_code == 404
