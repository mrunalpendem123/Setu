from __future__ import annotations

import csv
import io
import json
import os
from typing import Dict, Any, List

from .catalog import CATALOG


def _read_json(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def _money(amount: int, currency: str) -> str:
    return f"{amount / 100:.2f} {currency.upper()}"


def _shipping_entries() -> List[str]:
    raw = os.getenv("FEED_SHIPPING", "IN:ALL:Standard:0.00 INR")
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def _merchant_fields() -> Dict[str, Any]:
    return {
        "seller_name": os.getenv("MERCHANT_NAME"),
        "seller_url": os.getenv("MERCHANT_URL"),
        "seller_privacy_policy": os.getenv("MERCHANT_PRIVACY_URL"),
        "seller_tos": os.getenv("MERCHANT_TOS_URL"),
    }


def _required_feed_fields() -> List[str]:
    return [
        "item_id",
        "title",
        "description",
        "url",
        "image_url",
        "price",
        "availability",
        "brand",
        "seller_name",
        "seller_url",
        "is_eligible_search",
        "is_eligible_checkout",
    ]


def _ensure_required_checkout_fields(item: Dict[str, Any]) -> None:
    missing = [key for key in _required_feed_fields() if not item.get(key)]
    if item.get("is_eligible_checkout"):
        for key in ("seller_privacy_policy", "seller_tos"):
            if not item.get(key):
                missing.append(key)
    if missing:
        raise RuntimeError(f"Missing required feed fields: {', '.join(sorted(set(missing)))}")


def build_product_feed(currency: str = "inr") -> Dict[str, Any]:
    defaults = _read_json(os.getenv("FEED_GLOBAL_DEFAULTS_PATH"))
    overrides = _read_json(os.getenv("FEED_ITEM_OVERRIDES_PATH"))
    shipping = _shipping_entries()
    merchant_fields = _merchant_fields()

    is_checkout = os.getenv("FEED_ELIGIBLE_CHECKOUT", "true").lower() == "true"
    is_search = os.getenv("FEED_ELIGIBLE_SEARCH", "true").lower() == "true"

    target_countries = [value.strip() for value in os.getenv("FEED_TARGET_COUNTRIES", "IN").split(",") if value.strip()]
    store_country = os.getenv("FEED_STORE_COUNTRY", "IN")
    brand = os.getenv("MERCHANT_BRAND", merchant_fields.get("seller_name") or "")

    items: List[Dict[str, Any]] = []
    for item_id, data in CATALOG.items():
        base = {
            "item_id": item_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "image_url": data.get("image_url"),
            "url": data.get("product_url"),
            "availability": data.get("availability", "in_stock"),
            "price": _money(int(data.get("price", 0)), currency),
            "shipping": shipping,
            "brand": data.get("brand", brand),
            "target_countries": target_countries,
            "store_country": data.get("store_country", store_country),
            "is_eligible_search": is_search,
            "is_eligible_checkout": is_checkout,
        }
        merged = {**defaults, **base, **merchant_fields, **overrides.get(item_id, {})}
        _ensure_required_checkout_fields(merged)
        items.append(merged)

    return {"items": items}


def render_product_feed(format: str = "json", currency: str = "inr") -> str:
    feed = build_product_feed(currency=currency)
    if format == "json":
        return json.dumps(feed, ensure_ascii=True)

    items = feed.get("items", [])
    if not items:
        return ""

    output = io.StringIO()
    fieldnames = sorted({key for item in items for key in item.keys()})
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        row = dict(item)
        if isinstance(row.get("shipping"), list):
            row["shipping"] = ",".join(row["shipping"])  # type: ignore[assignment]
        if isinstance(row.get("target_countries"), list):
            row["target_countries"] = ",".join(row["target_countries"])  # type: ignore[assignment]
        writer.writerow(row)
    return output.getvalue()
