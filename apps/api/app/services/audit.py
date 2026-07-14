from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def write_audit_event(
    session: Session,
    *,
    event_type: str,
    actor_type: str,
    object_type: str,
    actor_id: str | None = None,
    object_id: str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    reason: str | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=str(uuid4()),
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        object_type=object_type,
        object_id=object_id,
        before_json=before_json,
        after_json=after_json,
        reason=reason,
        request_id=request_id,
    )
    session.add(event)
    return event
