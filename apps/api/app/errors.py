from http import HTTPStatus
from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class VersionConflictError(ApiError):
    def __init__(self, *, expected: str, received: str | None) -> None:
        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            code="VERSION_CONFLICT",
            message="Resource version conflict",
            details={"expected": expected, "received": received},
        )
