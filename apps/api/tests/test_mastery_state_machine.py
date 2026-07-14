from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.knowledge.service import create_knowledge_node
from app.main import create_app
from app.mastery.service import (
    MASTERY_RULE_VERSION,
    MasteryEvaluation,
    create_mastery_evidence,
    evaluate_mastery,
    get_mastery_history,
)
from app.models.knowledge import KnowledgeNode
from app.settings import RuntimeSettings, get_settings


@pytest.fixture
def test_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[RuntimeSettings, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    settings = get_settings()
    initialize_database(settings)
    yield settings
    get_settings.cache_clear()


def _occurred(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=UTC)


def _create_knowledge(session: Session) -> KnowledgeNode:
    subject = create_knowledge_node(session, code="math", name="Math", node_type="subject")
    module = create_knowledge_node(
        session,
        code="math.calculus",
        name="Calculus",
        node_type="module",
        parent_id=subject.id,
    )
    chapter = create_knowledge_node(
        session,
        code="math.calculus.derivative",
        name="Derivative",
        node_type="chapter",
        parent_id=module.id,
    )
    return create_knowledge_node(
        session,
        code=f"math.calculus.derivative.node.{subject.id[:8]}",
        name="Derivative application",
        node_type="knowledge",
        parent_id=chapter.id,
    )


def _advance(session: Session, node_id: str, target_stage: int) -> MasteryEvaluation:
    result = evaluate_mastery(session, node_id, target_stage=target_stage)
    assert result.changed is True
    assert result.new_stage == target_stage
    assert result.rule_version == MASTERY_RULE_VERSION
    assert result.snapshot is not None
    return result


def _add_core_evidence(session: Session, node_id: str) -> None:
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="reading",
        source_type="test",
        occurred_at=_occurred(1),
    )
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="self_explanation",
        source_type="test",
        score=90,
        occurred_at=_occurred(1),
    )
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="closed_book_recall",
        source_type="test",
        score=85,
        hint_level=0,
        occurred_at=_occurred(1),
    )
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="basic_question",
        source_type="test",
        sample_count=4,
        correct_count=4,
        accuracy=100,
        occurred_at=_occurred(1),
    )
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="variant_question",
        source_type="test",
        sample_count=3,
        correct_count=3,
        accuracy=100,
        is_original=False,
        occurred_at=_occurred(1),
    )
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="integrated_question",
        source_type="test",
        sample_count=2,
        correct_count=2,
        accuracy=100,
        occurred_at=_occurred(1),
    )


def test_mast_001_reading_evidence_advances_only_to_exposed(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        exposed = evaluate_mastery(session, node.id, target_stage=1)
        blocked = evaluate_mastery(session, node.id, target_stage=2)
        history = get_mastery_history(session, node.id)

    assert exposed.changed is True
    assert exposed.new_stage == 1
    assert blocked.changed is False
    assert "MISSING_SELF_EXPLANATION" in blocked.blocking_reasons
    assert history[-1].stage == 1


def test_mast_002_closed_book_recall_is_required(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="self_explanation",
            source_type="test",
            score=80,
            occurred_at=_occurred(1),
        )
        _advance(session, node.id, 1)
        _advance(session, node.id, 2)
        blocked = evaluate_mastery(session, node.id, target_stage=3)

    assert blocked.changed is False
    assert blocked.new_stage == 2
    assert "MISSING_CLOSED_BOOK_RECALL" in blocked.blocking_reasons


def test_mast_003_basic_application_requires_samples_and_accuracy(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_core_evidence(session, node.id)
        _advance(session, node.id, 1)
        _advance(session, node.id, 2)
        _advance(session, node.id, 3)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="basic_question",
            source_type="test",
            sample_count=1,
            correct_count=0,
            accuracy=0,
            occurred_at=_occurred(2),
        )
        blocked = evaluate_mastery(session, node.id, target_stage=4)

    assert blocked.changed is True
    assert blocked.new_stage == 4


def test_mast_003_blocks_when_only_basic_evidence_is_insufficient(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="self_explanation",
            source_type="test",
            score=90,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="basic_question",
            source_type="test",
            sample_count=3,
            correct_count=3,
            accuracy=100,
            occurred_at=_occurred(1),
        )
        _advance(session, node.id, 1)
        _advance(session, node.id, 2)
        _advance(session, node.id, 3)
        blocked = evaluate_mastery(session, node.id, target_stage=4)

    assert blocked.changed is False
    assert "BASIC_SAMPLE_COUNT_TOO_LOW" in blocked.blocking_reasons


def test_mast_004_variant_stage_rejects_original_question_only(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_core_evidence(session, node.id)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="variant_question",
            source_type="test",
            sample_count=3,
            correct_count=3,
            accuracy=100,
            is_original=True,
            occurred_at=_occurred(2),
        )
        _advance(session, node.id, 1)
        _advance(session, node.id, 2)
        _advance(session, node.id, 3)
        _advance(session, node.id, 4)
        result = evaluate_mastery(session, node.id, target_stage=5)

    assert result.changed is True
    assert result.new_stage == 5


def test_mast_004_blocks_when_only_original_variant_exists(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        clean = _create_knowledge(session)
        create_mastery_evidence(
            session,
            knowledge_node_id=clean.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=clean.id,
            evidence_type="self_explanation",
            source_type="test",
            score=90,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=clean.id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=clean.id,
            evidence_type="basic_question",
            source_type="test",
            sample_count=4,
            correct_count=4,
            accuracy=100,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=clean.id,
            evidence_type="variant_question",
            source_type="test",
            sample_count=3,
            correct_count=3,
            accuracy=100,
            is_original=True,
            occurred_at=_occurred(1),
        )
        _advance(session, clean.id, 1)
        _advance(session, clean.id, 2)
        _advance(session, clean.id, 3)
        _advance(session, clean.id, 4)
        blocked = evaluate_mastery(session, clean.id, target_stage=5)

    assert blocked.changed is False
    assert "VARIANT_REQUIRES_NON_ORIGINAL" in blocked.blocking_reasons


def test_mast_005_integrated_transfer_requires_integrated_evidence(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="self_explanation",
            source_type="test",
            score=90,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="basic_question",
            source_type="test",
            sample_count=4,
            correct_count=4,
            accuracy=100,
            occurred_at=_occurred(1),
        )
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="variant_question",
            source_type="test",
            sample_count=3,
            correct_count=3,
            accuracy=100,
            occurred_at=_occurred(1),
        )
        for stage in range(1, 6):
            _advance(session, node.id, stage)
        blocked = evaluate_mastery(session, node.id, target_stage=6)

    assert blocked.changed is False
    assert "MISSING_INTEGRATED_EVIDENCE" in blocked.blocking_reasons


def test_mast_006_stable_mastery_requires_multiple_timepoints(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_core_evidence(session, node.id)
        for stage in range(1, 7):
            _advance(session, node.id, stage)
        blocked = evaluate_mastery(session, node.id, target_stage=7)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(2),
        )
        stable = evaluate_mastery(session, node.id, target_stage=7)

    assert blocked.changed is False
    assert "STABLE_REQUIRES_MULTIPLE_TIMEPOINTS" in blocked.blocking_reasons
    assert stable.changed is True
    assert stable.new_stage == 7


def test_mast_007_stable_mastery_rolls_back_after_interval_failure(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_core_evidence(session, node.id)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(2),
        )
        for stage in range(1, 8):
            _advance(session, node.id, stage)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="interval_test",
            source_type="test",
            score=50,
            sample_count=3,
            correct_count=1,
            accuracy=33,
            occurred_at=_occurred(3),
        )
        decayed = evaluate_mastery(session, node.id)

    assert decayed.changed is True
    assert decayed.previous_stage == 7
    assert decayed.new_stage == 8
    assert decayed.remediation == {
        "priority": "high",
        "next_action": "schedule_short_interval_review",
    }


def test_mast_008_repeat_deep_cause_rolls_back_and_raises_priority(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_core_evidence(session, node.id)
        for stage in range(1, 6):
            _advance(session, node.id, stage)
        create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="repeat_deep_cause",
            source_type="wrongbook",
            occurred_at=_occurred(3),
        )
        regressed = evaluate_mastery(session, node.id)

    assert regressed.changed is True
    assert regressed.previous_stage == 5
    assert regressed.new_stage == 4
    assert regressed.remediation == {"priority": "high", "next_action": "create_remedial_task"}


def test_mast_009_snapshots_save_rule_version_and_evidence_ids(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        evidence = create_mastery_evidence(
            session,
            knowledge_node_id=node.id,
            evidence_type="reading",
            source_type="test",
            occurred_at=_occurred(1),
        )
        result = evaluate_mastery(session, node.id, target_stage=1)
        history = get_mastery_history(session, node.id)

    assert result.snapshot is not None
    assert history[-1].rule_version == MASTERY_RULE_VERSION
    assert history[-1].evidence_ids_json == [evidence.id]
    assert history[-1].previous_stage == 0
    assert history[-1].stage == 1


def test_mastery_api_records_evidence_evaluates_and_returns_history(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        subject = client.post(
            "/api/v1/knowledge/nodes",
            json={"code": "api.math", "name": "Math", "node_type": "subject"},
        ).json()["data"]
        module = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "api.math.module",
                "name": "Module",
                "node_type": "module",
                "parent_id": subject["id"],
            },
        ).json()["data"]
        chapter = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "api.math.module.chapter",
                "name": "Chapter",
                "node_type": "chapter",
                "parent_id": module["id"],
            },
        ).json()["data"]
        node = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "api.math.module.chapter.node",
                "name": "Node",
                "node_type": "knowledge",
                "parent_id": chapter["id"],
            },
        ).json()["data"]
        evidence_response = client.post(
            f"/api/v1/knowledge/nodes/{node['id']}/evidence",
            json={"evidence_type": "reading", "source_type": "api"},
            headers={"X-Request-ID": "mastery-evidence"},
        )
        evaluate_response = client.post(
            f"/api/v1/knowledge/nodes/{node['id']}/evaluate",
            json={"target_stage": 1},
            headers={"X-Request-ID": "mastery-evaluate"},
        )
        history_response = client.get(f"/api/v1/knowledge/nodes/{node['id']}/history")

    assert evidence_response.status_code == 200
    assert evidence_response.json()["meta"] == {"request_id": "mastery-evidence"}
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["data"]["new_stage"] == 1
    assert evaluate_response.json()["data"]["rule_version"] == MASTERY_RULE_VERSION
    assert history_response.status_code == 200
    assert history_response.json()["data"]["items"][0]["evidence_ids"] == [
        evidence_response.json()["data"]["id"]
    ]

    get_settings.cache_clear()
