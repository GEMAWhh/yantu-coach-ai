import os
import re
from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url


class AppEnvironment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class DatabaseBackend(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class EvidenceAIProviderName(StrEnum):
    FAKE = "fake"
    DEEPSEEK = "deepseek"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass(frozen=True)
class SupabaseStorageSettings:
    project_url: str
    secret_key: str = field(repr=False)
    bucket: str


@dataclass(frozen=True)
class EvidenceAISettings:
    provider: EvidenceAIProviderName
    base_url: str | None
    api_key: str | None = field(repr=False)
    model: str
    timeout_seconds: float


@dataclass(frozen=True)
class RuntimeSettings:
    environment: AppEnvironment
    data_root: Path
    database_url: str
    database_backend: DatabaseBackend
    cors_allowed_origins: tuple[str, ...]
    auth_token_sha256: str | None
    supabase_storage: SupabaseStorageSettings | None
    evidence_ai: EvidenceAISettings

    @property
    def authentication_required(self) -> bool:
        return self.auth_token_sha256 is not None

    @property
    def cloud_asset_storage_ready(self) -> bool:
        return self.supabase_storage is not None

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
        paths = [
            self.files_dir / "original",
            self.files_dir / "derived",
            self.files_dir / "thumbnails",
            self.settings_dir,
            self.data_root / "exports",
            self.backups_dir,
            self.logs_dir,
            self.cache_dir,
        ]
        if self.database_backend is DatabaseBackend.SQLITE:
            paths.append(self.database_dir)
        for path in paths:
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


def _parse_supabase_storage(
    environment: AppEnvironment,
) -> SupabaseStorageSettings | None:
    raw_url = os.getenv("YANTU_SUPABASE_URL")
    raw_secret = os.getenv("YANTU_SUPABASE_SECRET_KEY")
    raw_bucket = os.getenv("YANTU_SUPABASE_STORAGE_BUCKET")
    configured_values = (raw_url, raw_secret, raw_bucket)
    if all(value is None or not value.strip() for value in configured_values):
        return None
    if environment is not AppEnvironment.PROD:
        raise RuntimeError("dev/test runtime must not use Supabase Storage")
    if any(value is None or not value.strip() for value in configured_values):
        raise RuntimeError(
            "YANTU_SUPABASE_URL, YANTU_SUPABASE_SECRET_KEY, and "
            "YANTU_SUPABASE_STORAGE_BUCKET must be configured together"
        )
    assert raw_url is not None
    assert raw_secret is not None
    assert raw_bucket is not None

    project_url = raw_url.strip().rstrip("/")
    parsed = urlsplit(project_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or not parsed.hostname.endswith(".supabase.co")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("YANTU_SUPABASE_URL must be an HTTPS Supabase project origin")

    secret_key = raw_secret.strip()
    if len(secret_key) < 32:
        raise ValueError("YANTU_SUPABASE_SECRET_KEY is invalid")

    bucket = raw_bucket.strip()
    if re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,62}", bucket) is None:
        raise ValueError("YANTU_SUPABASE_STORAGE_BUCKET must be a safe lowercase bucket name")
    return SupabaseStorageSettings(
        project_url=project_url,
        secret_key=secret_key,
        bucket=bucket,
    )


def _default_sqlite_database_url(data_root: Path) -> str:
    return f"sqlite:///{(data_root / 'database' / 'study.db').as_posix()}"


def _parse_evidence_ai_settings() -> EvidenceAISettings:
    raw_provider = os.getenv("YANTU_EVIDENCE_AI_PROVIDER", EvidenceAIProviderName.FAKE.value)
    try:
        provider = EvidenceAIProviderName(raw_provider.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in EvidenceAIProviderName)
        raise ValueError(f"YANTU_EVIDENCE_AI_PROVIDER must be one of: {allowed}") from exc

    if provider is EvidenceAIProviderName.FAKE:
        return EvidenceAISettings(
            provider=provider,
            base_url=None,
            api_key=None,
            model="fake-evidence-provider",
            timeout_seconds=30.0,
        )

    raw_api_key = os.getenv("YANTU_EVIDENCE_AI_API_KEY")
    if raw_api_key is None or not raw_api_key.strip():
        raise RuntimeError("YANTU_EVIDENCE_AI_API_KEY is required for a real AI provider")

    default_base_url = (
        "https://api.deepseek.com" if provider is EvidenceAIProviderName.DEEPSEEK else None
    )
    raw_base_url = os.getenv("YANTU_EVIDENCE_AI_BASE_URL") or default_base_url
    if raw_base_url is None or not raw_base_url.strip():
        raise RuntimeError("YANTU_EVIDENCE_AI_BASE_URL is required for openai_compatible provider")
    base_url = raw_base_url.strip().rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("YANTU_EVIDENCE_AI_BASE_URL must be an HTTPS URL without credentials")

    default_model = "deepseek-flash" if provider is EvidenceAIProviderName.DEEPSEEK else None
    raw_model = os.getenv("YANTU_EVIDENCE_AI_MODEL") or default_model
    if raw_model is None or not raw_model.strip():
        raise RuntimeError("YANTU_EVIDENCE_AI_MODEL is required for openai_compatible provider")

    raw_timeout = os.getenv("YANTU_EVIDENCE_AI_TIMEOUT_SECONDS", "60")
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError as exc:
        raise ValueError("YANTU_EVIDENCE_AI_TIMEOUT_SECONDS must be a number") from exc
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("YANTU_EVIDENCE_AI_TIMEOUT_SECONDS must be between 1 and 300")

    return EvidenceAISettings(
        provider=provider,
        base_url=base_url,
        api_key=raw_api_key.strip(),
        model=raw_model.strip(),
        timeout_seconds=timeout_seconds,
    )


def _parse_database_url(
    environment: AppEnvironment,
    data_root: Path,
) -> tuple[str, DatabaseBackend]:
    configured_url = os.getenv("YANTU_DATABASE_URL")
    if configured_url is None or not configured_url.strip():
        if environment is AppEnvironment.PROD:
            raise RuntimeError("YANTU_DATABASE_URL is required in production")
        return _default_sqlite_database_url(data_root), DatabaseBackend.SQLITE

    raw_url = configured_url.strip()
    try:
        parsed = make_url(raw_url)
    except Exception as exc:
        raise ValueError("YANTU_DATABASE_URL must be a valid database URL") from exc

    if parsed.get_backend_name() == DatabaseBackend.SQLITE:
        if environment is AppEnvironment.PROD:
            raise RuntimeError("production must use a PostgreSQL YANTU_DATABASE_URL")
        return raw_url, DatabaseBackend.SQLITE

    if parsed.get_backend_name() != DatabaseBackend.POSTGRESQL:
        raise ValueError("YANTU_DATABASE_URL must use SQLite or PostgreSQL")
    if environment is not AppEnvironment.PROD:
        raise RuntimeError("dev/test runtime must not use a cloud PostgreSQL database")
    if parsed.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("YANTU_DATABASE_URL must use the psycopg PostgreSQL driver")
    if not parsed.host or not parsed.database or not parsed.username or parsed.password is None:
        raise ValueError(
            "YANTU_DATABASE_URL must include PostgreSQL host, database, and credentials"
        )
    if parsed.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("YANTU_DATABASE_URL must require TLS with sslmode=require")

    if parsed.drivername == "postgresql":
        raw_url = f"postgresql+psycopg{raw_url[len('postgresql') :]}"
    return raw_url, DatabaseBackend.POSTGRESQL


@lru_cache
def get_settings() -> RuntimeSettings:
    environment = _parse_environment(os.getenv("YANTU_APP_ENV", AppEnvironment.DEV.value))
    data_root = _resolve_data_root(environment)
    _guard_environment_separation(environment, data_root)
    cors_allowed_origins = _parse_cors_allowed_origins(environment)
    auth_token_sha256 = _parse_auth_token_sha256(environment)
    database_url, database_backend = _parse_database_url(environment, data_root)
    supabase_storage = _parse_supabase_storage(environment)
    evidence_ai = _parse_evidence_ai_settings()
    return RuntimeSettings(
        environment=environment,
        data_root=data_root,
        database_url=database_url,
        database_backend=database_backend,
        cors_allowed_origins=cors_allowed_origins,
        auth_token_sha256=auth_token_sha256,
        supabase_storage=supabase_storage,
        evidence_ai=evidence_ai,
    )
