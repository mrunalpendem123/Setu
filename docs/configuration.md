# Configuration Reference

Environment variables for each service in the reference implementation.

---

## Indus (orchestrator)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL (`sqlite:///./indus.db` or `postgresql+psycopg://...`) |
| `MERCHANT_API_KEYS` | — | Comma-separated keys authorizing merchants to redeem tokens |
| `INDUS_API_KEY` | — | Key sent to merchant for token redemption |
| `TOKEN_TTL_SECONDS` | `86400` | Buyer / fulfillment token lifetime |
| `PAYMENTS_SERVICE_URL` | — | URL of Payments proxy (Rust). If unset, calls Hyperswitch directly |
| `HYPERSWITCH_BASE_URL` | `https://sandbox.hyperswitch.io` | — |
| `HYPERSWITCH_API_KEY` | — | Hyperswitch secret key |
| `HYPERSWITCH_PUBLISHABLE_KEY` | — | For session tokens / payment links |
| `HYPERSWITCH_ADMIN_API_KEY` | — | For API key creation |
| `HYPERSWITCH_VAULT_API_KEY` | — | For payment method sessions |
| `SARVAM_BASE_URL` | — | Sarvam AI base URL |
| `SARVAM_API_KEY` | — | Sarvam API key |
| `SARVAM_PROXY_PATH` | `/v1/chat/completions` | Path for Sarvam proxy |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `LOG_LEVEL` | `INFO` | — |

---

## Merchant

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL |
| `INDUS_API_KEYS` | — | Comma-separated keys authorizing Indus |
| `INDUS_BASE_URL` | — | Indus base URL for token redemption |
| `INDUS_API_KEY` | — | Key sent when redeeming tokens |
| `PAYMENTS_SERVICE_URL` | — | Payments proxy URL. Falls back to Hyperswitch directly |
| `HYPERSWITCH_API_KEY` | — | Hyperswitch secret key (fallback) |
| `HYPERSWITCH_ACCEPTED_STATUSES` | `succeeded,processing,requires_capture,requires_customer_action` | Payment statuses treated as verified |
| `MERCHANT_NAME` | — | Shown in product feed |
| `MERCHANT_URL` | — | — |
| `MERCHANT_PRIVACY_URL` | — | — |
| `MERCHANT_TOS_URL` | — | — |
| `ORDER_WEBHOOK_URL` | — | Where to send order events |
| `ORDER_WEBHOOK_SECRET` | — | HMAC secret for webhook signing |
| `RATE_LIMIT_ENABLED` | `true` | — |

---

## Payments (Rust proxy)

| Variable | Default | Description |
|---|---|---|
| `HYPERSWITCH_BASE_URL` | `https://sandbox.hyperswitch.io` | — |
| `HYPERSWITCH_API_KEY` | — | — |
| `HYPERSWITCH_PUBLISHABLE_KEY` | — | — |
| `HYPERSWITCH_ADMIN_API_KEY` | — | — |
| `HYPERSWITCH_VAULT_API_KEY` | — | — |
| `HYPERSWITCH_PROFILE_ID` | — | Optional |
| `PAYMENTS_PORT` | `9000` | — |

---

## PSP stub

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL |
| `ACP_API_KEYS` | — | Comma-separated keys |
| `ACP_API_VERSION` | `2025-09-29` | — |
