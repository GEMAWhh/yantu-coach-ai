from logging.config import fileConfig

from alembic import context
from sqlalchemy import Engine

from app.db.database import get_engine
from app.db.migrations import use_batch_migrations
from app.models import Base
from app.settings import RuntimeSettings, get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _settings() -> RuntimeSettings:
    configured = config.attributes.get("settings")
    if isinstance(configured, RuntimeSettings):
        return configured
    return get_settings()


def run_migrations_offline() -> None:
    settings = _settings()
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = _settings()
    settings.ensure_runtime_dirs()
    connectable: Engine = get_engine(settings.database_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=use_batch_migrations(settings),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
