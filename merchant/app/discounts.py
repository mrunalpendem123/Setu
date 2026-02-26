from __future__ import annotations

from typing import Dict, Any, Optional


COUPONS: Dict[str, Dict[str, Any]] = {
    "INDUS10": {"type": "percent", "value": 10, "max_uses": 1000},
    "FLAT200": {"type": "flat", "value": 200},
}


def apply_coupon(code: str, subtotal: int) -> int:
    """Apply coupon and return discount amount in paise. Returns 0 if invalid."""
    if not code:
        return 0
    coupon = COUPONS.get(code.upper())
    if not coupon:
        return 0
    if coupon["type"] == "percent":
        return int(round(subtotal * coupon["value"] / 100))
    if coupon["type"] == "flat":
        return min(int(coupon["value"]), subtotal)
    return 0


def get_coupon(code: str) -> Optional[Dict[str, Any]]:
    """Return coupon definition or None if not found."""
    if not code:
        return None
    return COUPONS.get(code.upper())
