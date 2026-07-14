from pathlib import Path
from typing import TypedDict

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.database import get_engine
from app.settings import RuntimeSettings

DATABASE_HEAD_REVISION = "0009_evidence_draft_pipeline"


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


def upgrade_database(settings: RuntimeSettings, revision: str = "head") -> None:
    settings.ensure_runtime_dirs()
    command.upgrade(make_alembic_config(settings), revision)


def initialize_database(settings: RuntimeSettings) -> None:
    upgrade_database(settings)
    get_database_pragmas(settings)


def get_database_revision(settings: RuntimeSettings) -> str | None:
    engine = get_engine(settings.database_url)
    with engine.connect() as connection:
        table_exists = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'alembic_version'"
            )
        ).scalar_one_or_none()
        if table_exists is None:
            return None
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        return str(revision)


def get_database_pragmas(settings: RuntimeSettings) -> DatabasePragmas:
    engine = get_engine(settings.database_url)
    with engine.connect() as connection:
        foreign_keys = int(connection.execute(text("PRAGMA foreign_keys")).scalar_one())
        journal_mode = str(connection.execute(text("PRAGMA journal_mode")).scalar_one())
        return {"foreign_keys": foreign_keys, "journal_mode": journal_mode}
