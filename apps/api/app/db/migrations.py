from pathlib import Path
from typing import TypedDict

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db.database import get_engine
from app.settings import DatabaseBackend, RuntimeSettings

DATABASE_HEAD_REVISION = "0012_wrongbook_draft_pipeline"


class DatabasePragmas(TypedDict):
    foreign_keys: int
    journal_mode: str


def _api_root() -> Path:
    return Path(__file__).resolve().parents[2]


def make_alembic_config(settings: RuntimeSettings) -> Config:
    api_root = _api_root()
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    config.attributes["settings"] = settings
    return config


def use_batch_migrations(settings: RuntimeSettings) -> bool:
    return settings.database_backend is DatabaseBackend.SQLITE


def upgrade_database(settings: RuntimeSettings, revision: str = "head") -> None:
    settings.ensure_runtime_dirs()
    command.upgrade(make_alembic_config(settings), revision)


def initialize_database(settings: RuntimeSettings) -> None:
    upgrade_database(settings)
    if settings.database_backend is DatabaseBackend.SQLITE:
        get_database_pragmas(settings)
    else:
        _verify_postgresql_connection(settings)


def get_database_revision(settings: RuntimeSettings) -> str | None:
    engine = get_engine(settings.database_url)
    with engine.connect() as connection:
        if not inspect(connection).has_table("alembic_version"):
            return None
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        return str(revision)


def get_database_pragmas(settings: RuntimeSettings) -> DatabasePragmas:
    if settings.database_backend is not DatabaseBackend.SQLITE:
        raise RuntimeError("SQLite pragmas are unavailable for PostgreSQL")
    engine = get_engine(settings.database_url)
    with engine.connect() as connection:
        foreign_keys = int(connection.execute(text("PRAGMA foreign_keys")).scalar_one())
        journal_mode = str(connection.execute(text("PRAGMA journal_mode")).scalar_one())
        return {"foreign_keys": foreign_keys, "journal_mode": journal_mode}


def _verify_postgresql_connection(settings: RuntimeSettings) -> None:
    engine = get_engine(settings.database_url)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
