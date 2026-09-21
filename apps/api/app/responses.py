from typing import Any, TypeVar

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.request_context import REQUEST_ID_HEADER, get_request_id
from app.schemas.common import ApiErrorBody, ApiErrorResponse, ApiResponse, ResponseMeta

T = TypeVar("T", bound=BaseModel)


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ApiErrorResponse, "description": "Authentication required"},
    404: {"model": ApiErrorResponse, "description": "Resource not found"},
    409: {"model": ApiErrorResponse, "description": "Version conflict"},
    422: {"model": ApiErrorResponse, "description": "Validation error"},
    500: {"model": ApiErrorResponse, "description": "Internal server error"},
    503: {"model": ApiErrorResponse, "description": "Required cloud persistence is not ready"},
}


def api_response(data: T, request: Request) -> ApiResponse[T]:
    return ApiResponse(data=data, meta=ResponseMeta(request_id=get_request_id(request)))


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    body = ApiErrorResponse(
        error=ApiErrorBody(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers={REQUEST_ID_HEADER: request_id},
    )
