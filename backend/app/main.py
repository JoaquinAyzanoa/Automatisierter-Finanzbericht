from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    # Seed the admin user from ADMIN_USER / ADMIN_PASSWORD env vars.
    db = SessionLocal()
    try:
        AuthService(db).seed_admin()
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "docs": "/docs"}

    return app


app = create_app()
