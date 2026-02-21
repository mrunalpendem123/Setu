from __future__ import annotations

from fastapi import HTTPException


def raise_error(status_code: int, code: str, message: str, param: str | None = None) -> None:
    detail = {"code": code, "message": message, "param": param}
    raise HTTPException(status_code=status_code, detail=detail)
