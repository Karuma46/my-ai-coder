from datetime import datetime
from enum import StrEnum

from pydantic import AnyUrl, EmailStr, Field, field_validator, model_validator

from src.projects.schemas import APIModel, StrictRequest


class CompanyRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class UserResponse(APIModel):
    id: str
    name: str
    email: EmailStr
    avatar_url: str | None
    initials: str
    created_at: datetime
    updated_at: datetime


class RegisterRequest(StrictRequest):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=1_024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(StrictRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1_024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UpdateMeRequest(StrictRequest):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: AnyUrl | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateMeRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided")
        return self


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class CompanyResponse(APIModel):
    id: str
    name: str
    role: CompanyRole
    member_count: int
    project_count: int
    created_at: datetime
    updated_at: datetime


class CreateCompanyRequest(StrictRequest):
    name: str = Field(min_length=1, max_length=120)


class UpdateCompanyRequest(StrictRequest):
    name: str = Field(min_length=1, max_length=120)


class AddCompanyMemberRequest(StrictRequest):
    email: EmailStr
    role: CompanyRole = CompanyRole.MEMBER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UpdateCompanyMemberRequest(StrictRequest):
    role: CompanyRole


class CompanyMemberResponse(APIModel):
    user: UserResponse
    role: CompanyRole
    joined_at: datetime
