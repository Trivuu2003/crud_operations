from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .billing import router as billing_router
from .config import settings
from .models import Base
from .users_routes import router as users_router
from .db import engine


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Yash App API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api")
    api_router.include_router(auth_router)
    api_router.include_router(users_router)
    api_router.include_router(billing_router)
    app.include_router(api_router)

    return app


app = create_app()


