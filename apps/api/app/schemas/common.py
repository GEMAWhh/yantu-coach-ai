from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ResponseMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str


class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)

    data: T
    meta: ResponseMeta


class ApiErrorBody(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    error: ApiErrorBody
