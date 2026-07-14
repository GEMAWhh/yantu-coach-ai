import os
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path


class AppEnvironment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


@dataclass(frozen=True)
class RuntimeSettings:
    environment: AppEnvironment
    data_root: Path

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


@lru_cache
def get_settings() -> RuntimeSettings:
    environment = _parse_environment(os.getenv("YANTU_APP_ENV", AppEnvironment.DEV.value))
    data_root = _resolve_data_root(environment)
    _guard_environment_separation(environment, data_root)
    return RuntimeSettings(environment=environment, data_root=data_root)
