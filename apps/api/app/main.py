from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    imports_router,
    knowledge_router,
    mastery_router,
    planning_router,
    reviews_router,
    time_calibration_router,
)
from app.db.migrations import initialize_database
from app.errors import ApiError, VersionConflictError
from app.exception_handlers import (
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.middleware import request_id_middleware
from app.responses import ERROR_RESPONSES, api_response
from app.schemas.common import ApiResponse
from app.schemas.health import HealthResponse
from app.schemas.meta import ApiMetaResponse, VersionCheckResponse
from app.settings import get_settings

CONTRACT_VERSION: Literal["contract-v1"] = "contract-v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_runtime_dirs()
    initialize_database(settings)
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="研途教练 API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        responses=ERROR_RESPONSES,
        lifespan=lifespan,
    )
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/health", response_model=ApiResponse[HealthResponse], tags=["system"])
    @app.get("/api/v1/health", response_model=ApiResponse[HealthResponse], tags=["system"])
    def health(request: Request) -> ApiResponse[HealthResponse]:
        settings = get_settings()
        return api_response(
            HealthResponse(
                status="ok",
                service="yantu-coach-api",
                environment=settings.environment.value,
                data_root=settings.public_data_root,
            ),
            request,
        )

    @app.get("/api/v1/meta", response_model=ApiResponse[ApiMetaResponse], tags=["system"])
    def meta(
        request: Request,
        include_features: Annotated[bool, Query(description="Include contract features")] = True,
    ) -> ApiResponse[ApiMetaResponse]:
        settings = get_settings()
        features = [
            "request-id",
            "response-envelope",
            "error-envelope",
            "version-conflict",
            "localstorage-import-preview",
            "localstorage-import-commit",
            "knowledge-nodes",
            "knowledge-prerequisites",
            "mastery-evidence",
            "mastery-state-machine",
            "goals-tasks",
            "task-results",
            "review-scheduler",
            "review-results",
            "time-calibration",
        ]
        return api_response(
            ApiMetaResponse(
                service="yantu-coach-api",
                api_version="v1",
                contract_version=CONTRACT_VERSION,
                environment=settings.environment.value,
                features=features if include_features else [],
            ),
            request,
        )

    @app.post(
        "/api/v1/meta/version-check",
        response_model=ApiResponse[VersionCheckResponse],
        tags=["system"],
    )
    def version_check(
        request: Request,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> ApiResponse[VersionCheckResponse]:
        if if_match != CONTRACT_VERSION:
            raise VersionConflictError(expected=CONTRACT_VERSION, received=if_match)
        return api_response(
            VersionCheckResponse(status="ok", contract_version=CONTRACT_VERSION),
            request,
        )

    app.include_router(imports_router)
    app.include_router(knowledge_router)
    app.include_router(mastery_router)
    app.include_router(planning_router)
    app.include_router(reviews_router)
    app.include_router(time_calibration_router)

    return app


app = create_app()
