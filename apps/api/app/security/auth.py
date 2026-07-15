from collections.abc import Awaitable, Callable
from hashlib import sha256
from hmac import compare_digest

from fastapi import Request, Response

from app.responses import error_response
from app.settings import get_settings

PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/api/v1/health",
        "/api/v1/meta",
        "/api/v1/openapi.json",
        "/docs",
    }
)


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token or len(token) > 512:
        return None
    return token


def _is_authorized(request: Request, expected_digest: str) -> bool:
    token = _bearer_token(request)
    if token is None:
        return False
    received_digest = sha256(token.encode("utf-8")).hexdigest()
    return compare_digest(received_digest, expected_digest)


async def personal_token_auth_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    settings = get_settings()
    if (
        not settings.authentication_required
        or request.method == "OPTIONS"
        or request.url.path in PUBLIC_PATHS
    ):
        return await call_next(request)

    expected_digest = settings.auth_token_sha256
    if expected_digest is not None and _is_authorized(request, expected_digest):
        return await call_next(request)

    response = error_response(
        request=request,
        status_code=401,
        code="AUTHENTICATION_REQUIRED",
        message="A valid personal access key is required",
    )
    response.headers["WWW-Authenticate"] = "Bearer"
    return response
