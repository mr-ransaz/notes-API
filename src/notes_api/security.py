from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from notes_api.config import Settings

password_hasher = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerificationError, InvalidHashError:
        return False


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings) -> int:
    claims = jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=["HS256"],
        options={"require": ["sub", "exp", "iat"]},
    )
    subject = claims["sub"]
    # Keep the subject in the same canonical form as issued IDs.
    if not subject.isascii() or not subject.isdecimal() or len(subject) > 19:
        raise jwt.InvalidTokenError("Invalid subject")
    user_id = int(subject)
    if not 1 <= user_id <= 2**63 - 1 or str(user_id) != subject:
        raise jwt.InvalidTokenError("Invalid subject")
    return user_id
