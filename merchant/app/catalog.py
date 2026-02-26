from __future__ import annotations

from typing import Dict, Any


CATALOG: Dict[str, Dict[str, Any]] = {
    "item_123": {
        "title": "Monos Carry-On Pro Suitcase",
        "description": "Lightweight carry-on suitcase with durable shell.",
        "price": 99900,  # paise
        "image_url": "https://example.com/items/item_123.png",
        "product_url": "https://example.com/products/item_123",
        "availability": "in_stock",
        "hsn_code": "42021200",
    },
    "item_456": {
        "title": "Noise Cancelling Headphones",
        "description": "Over-ear headphones with active noise cancellation.",
        "price": 129900,
        "image_url": "https://example.com/items/item_456.png",
        "product_url": "https://example.com/products/item_456",
        "availability": "in_stock",
        "hsn_code": "85183000",
    },
}


def get_item(item_id: str) -> Dict[str, Any]:
    if item_id not in CATALOG:
        raise KeyError(f"Unknown item: {item_id}")
    return CATALOG[item_id]
