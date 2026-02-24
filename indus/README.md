# Indus Orchestrator

This service coordinates merchant checkout sessions and Hyperswitch payments.
It uses Postgres persistence.

## Endpoints

- `POST /indus/checkout`
- `POST /indus/checkout/{id}/update`
- `GET /indus/checkout/{id}`
- `POST /indus/checkout/{id}/cancel`
- `POST /indus/checkout/{id}/payment_intent`
- `POST /indus/checkout/{id}/complete`
- `POST /indus/payments`
- `POST /indus/payments/{id}`
- `POST /indus/payments/{id}/confirm`
- `POST /indus/payments/{id}/confirm_intent`
- `GET /indus/payments/{id}`
- `GET /indus/payments/{id}/payment_methods`
- `POST /indus/payments/{id}/cancel`
- `POST /indus/payments/{id}/cancel_post_capture`
- `POST /indus/payments/{id}/capture`
- `POST /indus/payments/{id}/incremental_authorization`
- `POST /indus/payments/{id}/extend_authorization`
- `POST /indus/payments/session_tokens`
- `GET /indus/payment_links/{id}`
- `GET /indus/payments`
- `POST /indus/payments/{id}/3ds/authentication`
- `POST /indus/payments/{id}/complete_authorize`
- `POST /indus/payments/{id}/create_external_sdk_tokens`
- `POST /indus/payments/{id}/update_metadata`
- `POST /indus/payments/{id}/eligibility`
- `POST /indus/payment_method_sessions`
- `POST /indus/api_keys/{merchant_id}`
- `POST /indus/sarvam/proxy`
- `POST /webhooks/orders`

Checkout status flow mirrors OpenAI Commerce:

- `not_ready_for_payment` -> `ready_for_payment` -> `completed` (or `canceled`)

## Env Vars

- `DATABASE_URL` (Postgres)
- `INDUS_API_KEY` (token for merchant; optional)
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
- `HYPERSWITCH_PROFILE_ID` (optional)
- `HYPERSWITCH_PUBLISHABLE_KEY` (required for session tokens / payment links)
- `HYPERSWITCH_ADMIN_API_KEY` (required for API key creation)
- `HYPERSWITCH_VAULT_API_KEY` (required for payment method sessions)
- `HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH` (default `/v2/payment-method-session`)
- `HYPERSWITCH_TIMEOUT_SECONDS` (default `20`)
- `HYPERSWITCH_MAX_RETRIES` (default `3`)
- `HYPERSWITCH_RETRY_BACKOFF_MS` (default `200`)

Webhooks:

- `ORDER_WEBHOOK_SECRET` (optional; verify Merchant-Signature)

Sarvam (optional):

- `SARVAM_BASE_URL`
- `SARVAM_API_KEY`
- `SARVAM_API_KEY_HEADER` (default `api-subscription-key`)
- `SARVAM_PROXY_PATH`
- `SARVAM_TIMEOUT_SECONDS` (default `20`)
- `SARVAM_MAX_RETRIES` (default `2`)
- `SARVAM_RETRY_BACKOFF_MS` (default `200`)

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/indus"
export INDUS_API_KEY=demo_key
export HYPERSWITCH_API_KEY=your_key
uvicorn app.main:app --reload --port 8000
```

If you are running the Rust payments service, set:

```
export PAYMENTS_SERVICE_URL="http://localhost:9000"
```
