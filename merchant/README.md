# Merchant API (Indus)

This service implements a robust checkout/order API for partner merchants (MoR)
with Postgres persistence and optional service-to-service auth.

## Endpoints

- `POST /checkout_sessions`
- `POST /checkout_sessions/{id}`
- `GET /checkout_sessions/{id}`
- `POST /checkout_sessions/{id}/cancel`
- `POST /checkout_sessions/{id}/complete`
- `POST /orders/{id}/update` (emits `order.updated`)
- `GET /product_feed`

Checkout status flow:

- `not_ready_for_payment` -> `ready_for_payment` -> `completed` (or `canceled`)

## Auth (optional)

If `INDUS_API_KEYS` is set, requests must include:

- `X-Indus-Key: <token>`

Idempotency:

- `Idempotency-Key` (applies to POST requests)

## Env Vars

Core:

- `DATABASE_URL` (Postgres)
- `INDUS_API_KEYS` (comma-separated tokens)
- `LOG_LEVEL` (default `INFO`)
- `RATE_LIMIT_ENABLED` (default `true`)
- `RATE_LIMIT_REQUESTS` (default `60`)
- `RATE_LIMIT_WINDOW_SECONDS` (default `60`)
- `PAYMENTS_SERVICE_URL` (optional; if set, use Rust payments service)
- `PAYMENTS_SERVICE_TIMEOUT_SECONDS` (default `20`)

Hyperswitch (used when `PAYMENTS_SERVICE_URL` is not set). If `PAYMENTS_SERVICE_URL` is set, Hyperswitch keys are only required on the Rust payments service:

- `HYPERSWITCH_BASE_URL` (default `https://sandbox.hyperswitch.io`)
- `HYPERSWITCH_API_KEY`
- `HYPERSWITCH_API_KEY_HEADER` (default `api-key`)
- `HYPERSWITCH_MERCHANT_ID` (optional)
- `HYPERSWITCH_ACCEPTED_STATUSES` (default `succeeded,processing,requires_capture`)
- `HYPERSWITCH_TIMEOUT_SECONDS` (default `20`)
- `HYPERSWITCH_MAX_RETRIES` (default `3`)
- `HYPERSWITCH_RETRY_BACKOFF_MS` (default `200`)

Product Feed:

- `MERCHANT_NAME`
- `MERCHANT_URL`
- `MERCHANT_PRIVACY_URL`
- `MERCHANT_TOS_URL`
- `MERCHANT_SUPPORT_URL` (optional)
- `MERCHANT_BRAND` (optional)
- `FEED_ELIGIBLE_SEARCH` (default `true`)
- `FEED_ELIGIBLE_CHECKOUT` (default `true`)
- `FEED_SHIPPING` (default `IN:ALL:Standard:0.00 INR`)
- `FEED_TARGET_COUNTRIES` (default `IN`)
- `FEED_STORE_COUNTRY` (default `IN`)
- `FEED_GLOBAL_DEFAULTS_PATH` (optional JSON)
- `FEED_ITEM_OVERRIDES_PATH` (optional JSON)
- `FEED_FORMAT` (json/csv)
- `FEED_OUTPUT_PATH` (default `./export/product_feed.json`)
- `FEED_PUSH_URL` (optional)
- `FEED_PUSH_METHOD` (default `POST`)
- `FEED_PUSH_API_KEY` (optional)

Webhooks:

- `ORDER_WEBHOOK_URL` (optional)
- `ORDER_WEBHOOK_SECRET` (optional)
- `ORDER_EVENT_STYLE` (dot/underscore; default `dot`)
- `ORDER_WEBHOOK_TIMEOUT_SECONDS` (default `5`)
- `ORDER_WEBHOOK_MAX_RETRIES` (default `3`)
- `ORDER_WEBHOOK_RETRY_BACKOFF_MS` (default `200`)

Idempotency:

- `IDEMPOTENCY_TTL_SECONDS` (default `86400`)

Audit Logging:

- Writes financial events to `audit_logs` table (payment verification, order created)

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/merchant"
export INDUS_API_KEYS=demo_key
export HYPERSWITCH_API_KEY=your_key
uvicorn app.main:app --reload --port 8001
```

If you are running the Rust payments service, set:

```
export PAYMENTS_SERVICE_URL="http://localhost:9000"
```

## Feed Export

```bash
python -m app.feed_export
```
