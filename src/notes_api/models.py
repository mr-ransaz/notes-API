from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from notes_api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32, collation="NOCASE"), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
