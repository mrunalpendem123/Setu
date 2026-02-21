from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class TokenRecord:
    token_id: str
    max_amount: int
    currency: str
    expires_at: datetime
    status: str
    created_at: datetime
    used_at: datetime | None
    metadata: Dict[str, Any]


tokens: Dict[str, TokenRecord] = {}


def save_token(record: TokenRecord) -> None:
    tokens[record.token_id] = record


def get_token(token_id: str) -> TokenRecord | None:
    return tokens.get(token_id)
