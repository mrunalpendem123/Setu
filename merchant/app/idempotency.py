from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        row = self.db.get(IdempotencyModel, key)
        if not row:
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
        )
        self.db.merge(row)
        self.db.commit()

    @staticmethod
    def build_request_hash(method: str, path: str, body: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(method.encode())
        hasher.update(b"|")
        hasher.update(path.encode())
        hasher.update(b"|")
        hasher.update(body)
        return hasher.hexdigest()
