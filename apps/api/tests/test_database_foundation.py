from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.db.database import get_engine, get_session_factory
from app.db.migrations import (
    DATABASE_HEAD_REVISION,
    get_database_pragmas,
    get_database_revision,
    initialize_database,
    upgrade_database,
)
from app.models.audit import AuditEvent
from app.services.audit import write_audit_event
from app.settings import RuntimeSettings, get_settings


@pytest.fixture
def test_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[RuntimeSettings, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_empty_database_upgrades_to_head(test_settings: RuntimeSettings) -> None:
    assert not test_settings.database_path.exists()

    upgrade_database(test_settings)

    assert test_settings.database_path.is_file()
    assert get_database_revision(test_settings) == DATABASE_HEAD_REVISION


def test_sqlite_wal_foreign_keys_and_fk_enforcement(test_settings: RuntimeSettings) -> None:
    initialize_database(test_settings)

    pragmas = get_database_pragmas(test_settings)
    assert pragmas["foreign_keys"] == 1
    assert pragmas["journal_mode"].lower() == "wal"

    engine = get_engine(test_settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE fk_parent_test (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE fk_child_test ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES fk_parent_test(id)"
                ")"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO fk_child_test (id, parent_id) VALUES (1, 404)"))


def test_audit_event_writes_inside_transaction(test_settings: RuntimeSettings) -> None:
    initialize_database(test_settings)
    session_factory = get_session_factory(test_settings.database_url)

    with session_factory.begin() as session:
        event = write_audit_event(
            session,
            event_type="database.initialized",
            actor_type="system",
            object_type="database",
            after_json={"revision": DATABASE_HEAD_REVISION},
            reason="test audit insert",
            request_id="db-audit",
        )
        event_id = event.id

    with session_factory() as session:
        stored = session.get(AuditEvent, event_id)
        assert stored is not None
        assert stored.event_type == "database.initialized"
        assert stored.after_json == {"revision": DATABASE_HEAD_REVISION}


def test_transaction_rollback_removes_audit_event(test_settings: RuntimeSettings) -> None:
    initialize_database(test_settings)
    session_factory = get_session_factory(test_settings.database_url)

    with pytest.raises(RuntimeError, match="rollback"):
        with session_factory.begin() as session:
            write_audit_event(
                session,
                event_type="database.rollback",
                actor_type="system",
                object_type="database",
                reason="should rollback",
            )
            raise RuntimeError("rollback")

    with session_factory() as session:
        count = session.scalar(select(func.count(AuditEvent.id)))
        assert count == 0


def test_test_environment_rejects_production_named_data_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "prod"))
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="production"):
        get_settings()

    assert not (tmp_path / "data" / "prod").exists()


def test_optimistic_version_conflict_is_detected(test_settings: RuntimeSettings) -> None:
    initialize_database(test_settings)
    session_factory = get_session_factory(test_settings.database_url)

    with session_factory.begin() as session:
        event = write_audit_event(
            session,
            event_type="database.versioned",
            actor_type="system",
            object_type="audit_event",
            reason="initial",
        )
        event_id = event.id

    first_session = session_factory()
    second_session = session_factory()
    try:
        first_copy = first_session.get(AuditEvent, event_id)
        second_copy = second_session.get(AuditEvent, event_id)
        assert first_copy is not None
        assert second_copy is not None

        first_copy.reason = "first update"
        first_session.commit()

        second_copy.reason = "stale update"
        with pytest.raises(StaleDataError):
            second_session.commit()
    finally:
        first_session.close()
        second_session.close()
