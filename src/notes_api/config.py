from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOTES_API_", env_file=".env", extra="forbid"
    )

    secret_key: SecretStr
    database_url: str = "sqlite:///./notes.db"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("secret_key")
    @classmethod
    def strong_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret.strip()) < 32 or secret.startswith("REPLACE_"):
            raise ValueError("Use a generated secret of at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def sqlite_only(cls, value: str) -> str:
        if not value.startswith("sqlite:///") or value == "sqlite:///:memory:":
            raise ValueError("Use a file-based sqlite:/// database URL")
        return value
