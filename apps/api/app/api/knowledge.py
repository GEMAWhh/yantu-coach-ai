from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.knowledge.service import (
    KnowledgeError,
    check_prerequisites,
    create_knowledge_edge,
    create_knowledge_node,
    get_knowledge_node,
    get_knowledge_tree,
    list_knowledge_nodes,
    soft_delete_knowledge_node,
    update_knowledge_node,
)
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.knowledge import (
    KnowledgeEdgeCreate,
    KnowledgeEdgeResponse,
    KnowledgeNodeCreate,
    KnowledgeNodeListResponse,
    KnowledgeNodeResponse,
    KnowledgeNodeTreeResponse,
    KnowledgeNodeUpdate,
    PrerequisiteCheckResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/nodes", response_model=ApiResponse[KnowledgeNodeResponse])
def create_node(
    request: Request,
    payload: KnowledgeNodeCreate,
) -> ApiResponse[KnowledgeNodeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            node = create_knowledge_node(session, **payload.model_dump())
            session.flush()
            response = KnowledgeNodeResponse.from_model(node)
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.get("/nodes", response_model=ApiResponse[KnowledgeNodeListResponse])
def list_nodes(
    request: Request,
    parent_id: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> ApiResponse[KnowledgeNodeListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        nodes = list_knowledge_nodes(
            session,
            parent_id=parent_id,
            include_deleted=include_deleted,
        )
        items = [KnowledgeNodeResponse.from_model(node) for node in nodes]
    return api_response(KnowledgeNodeListResponse(items=items, total=len(items)), request)


@router.get("/nodes/{node_id}", response_model=ApiResponse[KnowledgeNodeResponse])
def get_node(
    request: Request,
    node_id: str,
) -> ApiResponse[KnowledgeNodeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = KnowledgeNodeResponse.from_model(get_knowledge_node(session, node_id))
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.patch("/nodes/{node_id}", response_model=ApiResponse[KnowledgeNodeResponse])
def update_node(
    request: Request,
    node_id: str,
    payload: KnowledgeNodeUpdate,
) -> ApiResponse[KnowledgeNodeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            node = update_knowledge_node(
                session,
                node_id,
                **payload.model_dump(exclude_unset=True),
            )
            session.flush()
            response = KnowledgeNodeResponse.from_model(node)
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.delete("/nodes/{node_id}", response_model=ApiResponse[KnowledgeNodeResponse])
def delete_node(
    request: Request,
    node_id: str,
) -> ApiResponse[KnowledgeNodeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            node = soft_delete_knowledge_node(session, node_id)
            session.flush()
            response = KnowledgeNodeResponse.from_model(node)
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.get("/nodes/{node_id}/tree", response_model=ApiResponse[KnowledgeNodeTreeResponse])
def get_node_tree(
    request: Request,
    node_id: str,
) -> ApiResponse[KnowledgeNodeTreeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = KnowledgeNodeTreeResponse.from_tree(get_knowledge_tree(session, node_id))
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.get(
    "/nodes/{node_id}/prerequisites",
    response_model=ApiResponse[PrerequisiteCheckResponse],
)
def get_node_prerequisites(
    request: Request,
    node_id: str,
) -> ApiResponse[PrerequisiteCheckResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = PrerequisiteCheckResponse.from_check(check_prerequisites(session, node_id))
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


@router.post("/edges", response_model=ApiResponse[KnowledgeEdgeResponse])
def create_edge(
    request: Request,
    payload: KnowledgeEdgeCreate,
) -> ApiResponse[KnowledgeEdgeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            edge = create_knowledge_edge(session, **payload.model_dump())
            session.flush()
            response = KnowledgeEdgeResponse.from_model(edge)
    except KnowledgeError as exc:
        raise _api_knowledge_error(exc) from exc
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_knowledge_error(exc: KnowledgeError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
