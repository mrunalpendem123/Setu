from __future__ import annotations

import os


def get_indus_capabilities() -> dict:
    return {
        "protocol_version": "2026-02-24",
        "payment_providers": ["hyperswitch"],
        "payment_methods": ["card", "upi", "netbanking"],
        "token_ttl_seconds": int(os.getenv("TOKEN_TTL_SECONDS", "86400")),
        "fulfillment_types": ["shipping"],
        "extensions": ["india_gst", "upi_vpa"],
    }
