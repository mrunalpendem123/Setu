from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import IdempotencyModel


@dataclass
class IdempotencyRecord:
    request_hash: str
    response_body: Dict[str, Any]
    status_code: int


class IdempotencyStore:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _ttl_seconds(self) -> int:
        return int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))

    def _is_expired(self, created_at: datetime) -> bool:
        ttl = timedelta(seconds=self._ttl_seconds())
        now = datetime.now(timezone.utc)
        created = created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return now - created > ttl

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        row = self.db.get(IdempotencyModel, key)
        if not row:
            return None
        if self._is_expired(row.created_at):
            self.db.delete(row)
            self.db.commit()
            return None
        return IdempotencyRecord(
            request_hash=row.request_hash,
            response_body=row.response_body,
            status_code=row.status_code,
        )

    def save(self, key: str, record: IdempotencyRecord) -> None:
        row = IdempotencyModel(
            key=key,
            request_hash=record.request_hash,
            response_body=record.response_body,
            status_code=record.status_code,
            created_at=datetime.now(timezone.utc),
        )
        try:
            self.db.add(row)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    @staticmethod
    def build_request_hash(method: str, path: str, body: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(method.encode())
        hasher.update(b"|")
        hasher.update(path.encode())
        hasher.update(b"|")
        hasher.update(body)
        return hasher.hexdigest()
