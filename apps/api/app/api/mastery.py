from fastapi import APIRouter, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.knowledge.service import KnowledgeError
from app.mastery.service import (
    MasteryServiceError,
    create_mastery_evidence,
    evaluate_mastery,
    get_mastery_history,
    list_mastery_evidence,
    rollback_mastery,
)
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.mastery import (
    MasteryEvaluateRequest,
    MasteryEvaluationResponse,
    MasteryEvidenceCreate,
    MasteryEvidenceListResponse,
    MasteryEvidenceResponse,
    MasteryHistoryResponse,
    MasteryRollbackRequest,
    MasterySnapshotResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1/knowledge/nodes", tags=["mastery"])


@router.post("/{node_id}/evidence", response_model=ApiResponse[MasteryEvidenceResponse])
def create_evidence(
    request: Request,
    node_id: str,
    payload: MasteryEvidenceCreate,
) -> ApiResponse[MasteryEvidenceResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            evidence = create_mastery_evidence(
                session,
                knowledge_node_id=node_id,
                **payload.model_dump(),
            )
            response = MasteryEvidenceResponse.from_model(evidence)
    except (KnowledgeError, MasteryServiceError) as exc:
        raise _api_mastery_error(exc) from exc
    return api_response(response, request)


@router.get("/{node_id}/evidence", response_model=ApiResponse[MasteryEvidenceListResponse])
def list_evidence(
    request: Request,
    node_id: str,
) -> ApiResponse[MasteryEvidenceListResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            evidence = list_mastery_evidence(session, node_id)
            items = [MasteryEvidenceResponse.from_model(item) for item in evidence]
    except (KnowledgeError, MasteryServiceError) as exc:
        raise _api_mastery_error(exc) from exc
    return api_response(MasteryEvidenceListResponse(items=items, total=len(items)), request)


@router.post("/{node_id}/evaluate", response_model=ApiResponse[MasteryEvaluationResponse])
def evaluate_node(
    request: Request,
    node_id: str,
    payload: MasteryEvaluateRequest,
) -> ApiResponse[MasteryEvaluationResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            evaluation = evaluate_mastery(session, node_id, target_stage=payload.target_stage)
            response = MasteryEvaluationResponse.from_evaluation(evaluation)
    except (KnowledgeError, MasteryServiceError) as exc:
        raise _api_mastery_error(exc) from exc
    return api_response(response, request)


@router.post("/{node_id}/rollback", response_model=ApiResponse[MasteryEvaluationResponse])
def rollback_node(
    request: Request,
    node_id: str,
    payload: MasteryRollbackRequest,
) -> ApiResponse[MasteryEvaluationResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            evaluation = rollback_mastery(
                session,
                node_id,
                target_stage=payload.target_stage,
                evidence_id=payload.evidence_id,
                reason=payload.reason,
            )
            response = MasteryEvaluationResponse.from_evaluation(evaluation)
    except (KnowledgeError, MasteryServiceError) as exc:
        raise _api_mastery_error(exc) from exc
    return api_response(response, request)


@router.get("/{node_id}/history", response_model=ApiResponse[MasteryHistoryResponse])
def history(
    request: Request,
    node_id: str,
) -> ApiResponse[MasteryHistoryResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            snapshots = get_mastery_history(session, node_id)
            items = [MasterySnapshotResponse.from_model(snapshot) for snapshot in snapshots]
    except (KnowledgeError, MasteryServiceError) as exc:
        raise _api_mastery_error(exc) from exc
    return api_response(MasteryHistoryResponse(items=items, total=len(items)), request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_mastery_error(exc: KnowledgeError | MasteryServiceError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
