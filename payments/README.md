# Payments Service (Rust)

This service is a Rust HTTP proxy to Hyperswitch. It centralizes all payment calls and keeps payment logic out of the Python services.

The client UI should be initialized using the `client_secret` returned by `POST /payments` (Unified or Express Checkout).

## Endpoints

- `POST /payments`
- `POST /payments/{id}`
- `POST /payments/{id}/confirm`
- `POST /payments/{id}/confirm_intent`
- `GET /payments/{id}`
- `GET /payments/{id}/payment_methods`
- `POST /payments/{id}/cancel`
- `POST /payments/{id}/cancel_post_capture`
- `POST /payments/{id}/capture`
- `POST /payments/{id}/incremental_authorization`
- `POST /payments/{id}/extend_authorization`
- `POST /payments/session_tokens`
- `GET /payment_links/{id}`
- `GET /payments`
- `POST /payments/{id}/3ds/authentication`
- `POST /payments/{id}/complete_authorize`
- `POST /payments/{id}/create_external_sdk_tokens`
- `POST /payments/{id}/update_metadata`
- `POST /payments/{id}/eligibility`
- `POST /payment_method_sessions`
- `POST /api_keys/{merchant_id}`
- `GET /health`

## Env Vars

- `HYPERSWITCH_BASE_URL` (default `https://sandbox.hyperswitch.io`)
- `HYPERSWITCH_API_KEY`
- `HYPERSWITCH_PUBLISHABLE_KEY`
- `HYPERSWITCH_ADMIN_API_KEY`
- `HYPERSWITCH_VAULT_API_KEY`
- `HYPERSWITCH_API_KEY_HEADER` (default `api-key`)
- `HYPERSWITCH_MERCHANT_ID` (optional)
- `HYPERSWITCH_PROFILE_ID` (optional)
- `HYPERSWITCH_TIMEOUT_SECONDS` (default `20`)
- `HYPERSWITCH_MAX_RETRIES` (default `3`)
- `HYPERSWITCH_RETRY_BACKOFF_MS` (default `200`)
- `HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH` (default `/v2/payment-method-session`)
- `PAYMENTS_PORT` (default `9000`)

## Run

```bash
cargo run
```
