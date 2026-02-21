from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from .db import AuditLogModel


def log_event(
    db: Session,
    event_type: str,
    entity_id: str,
    payload: Dict[str, Any],
) -> None:
    db.add(
        AuditLogModel(
            event_type=event_type,
            entity_id=entity_id,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
    )
