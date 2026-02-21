from __future__ import annotations

import os
from pathlib import Path

import httpx

from .feed import render_product_feed


def export_feed() -> Path:
    feed_format = os.getenv("FEED_FORMAT", "json")
    output_path = Path(os.getenv("FEED_OUTPUT_PATH", "./export/product_feed.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = render_product_feed(format=feed_format)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def push_feed(path: Path) -> None:
    push_url = os.getenv("FEED_PUSH_URL")
    if not push_url:
        return

    headers = {"Content-Type": "application/json" if path.suffix == ".json" else "text/csv"}
    api_key = os.getenv("FEED_PUSH_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    method = os.getenv("FEED_PUSH_METHOD", "POST").upper()
    with httpx.Client(timeout=30.0) as client:
        request = client.request(method, push_url, content=path.read_bytes(), headers=headers)
        request.raise_for_status()


def main() -> None:
    path = export_feed()
    push_feed(path)


if __name__ == "__main__":
    main()
