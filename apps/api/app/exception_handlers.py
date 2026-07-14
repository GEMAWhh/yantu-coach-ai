from http import HTTPStatus

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import ApiError
from app.responses import error_response


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):
        raise exc
    return error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return error_response(
        request=request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": jsonable_encoder(exc.errors())},
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    if exc.status_code == HTTPStatus.NOT_FOUND:
        return error_response(
            request=request,
            status_code=HTTPStatus.NOT_FOUND,
            code="NOT_FOUND",
            message="Resource not found",
            details={"path": request.url.path},
        )
    if exc.status_code == HTTPStatus.CONFLICT:
        return error_response(
            request=request,
            status_code=HTTPStatus.CONFLICT,
            code="VERSION_CONFLICT",
            message="Resource version conflict",
        )
    return error_response(
        request=request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=str(exc.detail),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        request=request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
    )
