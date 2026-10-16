from fastapi import APIRouter

from notes_api.dependencies import CurrentUser
from notes_api.models import User
from notes_api.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user
