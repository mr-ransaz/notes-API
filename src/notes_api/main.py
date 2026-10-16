import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from notes_api import __version__
from notes_api.config import Settings
from notes_api.database import create_database, init_db
from notes_api.errors import install_error_handlers
from notes_api.rate_limit import LoginRateLimiter
from notes_api.routers import auth, notes, users
from notes_api.schemas import ErrorResponse
from notes_api.security import hash_password


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings if settings is not None else Settings()
        engine, app.state.session_factory = create_database(
            app.state.settings.database_url
        )
        try:
            init_db(engine)
            app.state.dummy_hash = hash_password(secrets.token_urlsafe(32))
            app.state.login_limiter = LoginRateLimiter()
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="notes-api",
        version=__version__,
        lifespan=lifespan,
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 401, 404, 405, 409, 422, 429, 500)
        },
    )
    install_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(notes.router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
