from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from notes_api.dependencies import SessionDep, unauthorized
from notes_api.models import User
from notes_api.schemas import RegisterRequest, TokenResponse, UserResponse
from notes_api.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=UserResponse)
def register(data: RegisterRequest, session: SessionDep) -> User:
    user = User(
        username=data.username.lower(), password_hash=hash_password(data.password)
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Username is already registered") from None
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> TokenResponse:
    if len(form.username) > 32 or len(form.password) > 128:
        raise HTTPException(422, "Login fields exceed length limits")
    user = session.scalar(select(User).where(User.username == form.username.lower()))
    stored_hash = user.password_hash if user else request.app.state.dummy_hash
    verified = verify_password(form.password, stored_hash)
    if not verified or user is None:
        raise unauthorized()
    return TokenResponse(
        access_token=create_access_token(user.id, request.app.state.settings)
    )
