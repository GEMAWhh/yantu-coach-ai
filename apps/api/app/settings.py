import os
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit


class AppEnvironment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


@dataclass(frozen=True)
class RuntimeSettings:
    environment: AppEnvironment
    data_root: Path
    cors_allowed_origins: tuple[str, ...]
    auth_token_sha256: str | None

    @property
    def authentication_required(self) -> bool:
        return self.auth_token_sha256 is not None

    @property
    def public_data_root(self) -> str:
        return f"data/{self.environment.value}"

    @property
    def database_dir(self) -> Path:
        return self.data_root / "database"

    @property
    def database_path(self) -> Path:
        return self.database_dir / "study.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def files_dir(self) -> Path:
        return self.data_root / "files"

    @property
    def settings_dir(self) -> Path:
        return self.data_root / "settings"

    @property
    def backups_dir(self) -> Path:
        return self.data_root / "backups"

    @property
    def logs_dir(self) -> Path:
        return self.data_root / "logs"

    @property
    def cache_dir(self) -> Path:
        return self.data_root / "cache"

    def ensure_runtime_dirs(self) -> None:
        for path in [
            self.database_dir,
            self.files_dir / "original",
            self.files_dir / "derived",
            self.files_dir / "thumbnails",
            self.settings_dir,
            self.data_root / "exports",
            self.backups_dir,
            self.logs_dir,
            self.cache_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _parse_environment(raw_value: str) -> AppEnvironment:
    try:
        return AppEnvironment(raw_value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AppEnvironment)
        raise ValueError(f"YANTU_APP_ENV must be one of: {allowed}") from exc


def _default_data_root(environment: AppEnvironment) -> Path:
    return _repo_root() / "data" / environment.value


def _resolve_data_root(environment: AppEnvironment) -> Path:
    configured_root = os.getenv("YANTU_DATA_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return _default_data_root(environment).resolve()


def _guard_environment_separation(environment: AppEnvironment, data_root: Path) -> None:
    default_prod_root = _default_data_root(AppEnvironment.PROD).resolve()
    if environment is not AppEnvironment.PROD and data_root == default_prod_root:
        raise RuntimeError("dev/test runtime must not use the production data directory")
    if environment is not AppEnvironment.PROD and data_root.name == AppEnvironment.PROD.value:
        raise RuntimeError("dev/test runtime must not use a production-named data directory")


def _parse_cors_allowed_origins(environment: AppEnvironment) -> tuple[str, ...]:
    raw_origins = os.getenv("YANTU_CORS_ALLOWED_ORIGINS")
    if raw_origins is None:
        if environment is AppEnvironment.DEV:
            return ("http://127.0.0.1:5173", "http://localhost:5173")
        return ()

    origins: list[str] = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise ValueError("YANTU_CORS_ALLOWED_ORIGINS must not contain wildcard origins")

        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "YANTU_CORS_ALLOWED_ORIGINS entries must be HTTP(S) origins without paths"
            )
        if origin not in origins:
            origins.append(origin)
    return tuple(origins)


def _parse_auth_token_sha256(environment: AppEnvironment) -> str | None:
    raw_digest = os.getenv("YANTU_AUTH_TOKEN_SHA256")
    if raw_digest is None or not raw_digest.strip():
        if environment is AppEnvironment.PROD:
            raise RuntimeError("YANTU_AUTH_TOKEN_SHA256 is required in production")
        return None

    digest = raw_digest.strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("YANTU_AUTH_TOKEN_SHA256 must be a 64-character SHA-256 hex digest")
    return digest


@lru_cache
def get_settings() -> RuntimeSettings:
    environment = _parse_environment(os.getenv("YANTU_APP_ENV", AppEnvironment.DEV.value))
    data_root = _resolve_data_root(environment)
    _guard_environment_separation(environment, data_root)
    return RuntimeSettings(
        environment=environment,
        data_root=data_root,
        cors_allowed_origins=_parse_cors_allowed_origins(environment),
        auth_token_sha256=_parse_auth_token_sha256(environment),
    )
