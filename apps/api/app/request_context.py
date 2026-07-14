from uuid import uuid4

from fastapi import Request

REQUEST_ID_HEADER = "X-Request-ID"


def normalize_request_id(raw_value: str | None) -> str:
    if raw_value is None:
        return str(uuid4())
    value = raw_value.strip()
    if not value or len(value) > 128:
        return str(uuid4())
    return value


def get_request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if isinstance(value, str) and value:
        return value
    return normalize_request_id(None)
