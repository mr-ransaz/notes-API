from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RegisterRequest(InputModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=12, max_length=128, repr=False)

    @field_validator("password")
    @classmethod
    def nonblank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be only whitespace")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HealthResponse(BaseModel):
    status: Literal["ok"]


def nonblank_title(value: str) -> str:
    if not value.strip():
        raise ValueError("Title cannot be only whitespace")
    return value


Title = Annotated[
    str, Field(min_length=1, max_length=200), AfterValidator(nonblank_title)
]
Body = Annotated[str, Field(max_length=10000)]


class NoteCreate(InputModel):
    title: Title
    body: Body = ""


class NotePatch(InputModel):
    title: Title | SkipJsonSchema[None] = None
    body: Body | SkipJsonSchema[None] = None

    @field_validator("title", "body")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Note fields cannot be null")
        return value

    @model_validator(mode="after")
    def require_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one note field")
        return self


class NoteQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=2**63 - 1)
    q: str | None = Field(default=None, max_length=200)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str


class ErrorDetail(BaseModel):
    location: list[str | int]
    type: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    error: ErrorBody
