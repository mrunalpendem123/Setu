# Configuration Reference

Environment variables for each service in the reference implementation.

---

## Indus (orchestrator)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL (`postgresql+psycopg://...`) |
| `INDUS_API_KEYS` | — | Comma-separated keys authorizing merchants to redeem tokens |
| `INDUS_API_KEY` | — | Key sent to merchant for token redemption |
| `TOKEN_TTL_SECONDS` | `86400` | Buyer / fulfillment token lifetime |
| `RAZORPAY_KEY_ID` | — | `rzp_test_...` or `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | — | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | — | Inbound webhook HMAC-SHA256 secret |
| `RAZORPAY_ACCOUNT_ID` | — | Platform Route account ID |
| `RAZORPAY_TIMEOUT_SECONDS` | `20` | — |
| `RAZORPAY_MAX_RETRIES` | `3` | — |
| `RAZORPAY_RETRY_BACKOFF_MS` | `200` | — |
| `SARVAM_BASE_URL` | `https://api.sarvam.ai` | Sarvam AI base URL |
| `SARVAM_API_KEY` | — | Sarvam API key |
| `SARVAM_API_KEY_HEADER` | `api-subscription-key` | Header name for Sarvam auth |
| `SARVAM_MODEL` | `sarvam-m` | Model to use |
| `SARVAM_PROXY_PATH` | `/v1/chat/completions` | Path for raw Sarvam proxy |
| `SARVAM_TIMEOUT_SECONDS` | `20` | — |
| `SARVAM_MAX_RETRIES` | `2` | — |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | — |
| `LOG_LEVEL` | `INFO` | — |

---

## Merchant

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL |
| `INDUS_API_KEYS` | — | Comma-separated keys authorizing Indus |
| `INDUS_BASE_URL` | — | Indus base URL for token redemption |
| `INDUS_API_KEY` | — | Key sent when redeeming tokens |
| `RAZORPAY_KEY_ID` | — | Razorpay key ID |
| `RAZORPAY_KEY_SECRET` | — | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | — | Inbound webhook HMAC-SHA256 secret |
| `RAZORPAY_MERCHANT_ACCOUNT_ID` | — | Linked account for Route settlement (`acc_...`) |
| `RAZORPAY_ACCEPTED_STATUSES` | `captured,authorized,requires_customer_action` | Statuses treated as verified |
| `RAZORPAY_TIMEOUT_SECONDS` | `20` | — |
| `RAZORPAY_MAX_RETRIES` | `3` | — |
| `MERCHANT_NAME` | — | Shown in product feed |
| `MERCHANT_URL` | — | — |
| `MERCHANT_PRIVACY_URL` | — | — |
| `MERCHANT_TOS_URL` | — | — |
| `ORDER_WEBHOOK_URL` | — | Where to send order events |
| `ORDER_WEBHOOK_SECRET` | — | HMAC secret for webhook signing |
| `RATE_LIMIT_ENABLED` | `true` | — |
| `LOG_LEVEL` | `INFO` | — |

---

## PSP stub

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | SQLAlchemy DB URL |
| `ACP_API_KEYS` | — | Comma-separated keys |
| `ACP_API_VERSION` | `2025-09-29` | — |
