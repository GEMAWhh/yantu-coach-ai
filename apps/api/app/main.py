from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.schemas.health import HealthResponse
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_runtime_dirs()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="研途教练 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        settings = get_settings()
        return HealthResponse(
            status="ok",
            service="yantu-coach-api",
            environment=settings.environment.value,
            data_root=settings.public_data_root,
        )

    return app


app = create_app()
