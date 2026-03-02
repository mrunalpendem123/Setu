# Payments Service (Rust) — Hyperswitch Proxy [DEPRECATED]

> **DEPRECATED** — This Rust proxy is no longer used by Indus or the Merchant service.
> Razorpay is now the sole PSP. Both services call Razorpay directly via
> `indus/app/razorpay_client.py`. This directory is retained for git history only.
>
> Last used: before the Razorpay migration (2026-03).

An optional high-throughput Rust HTTP proxy that centralises all Hyperswitch API calls. When deployed, both Indus and the Merchant service forward every payment request through this proxy instead of calling Hyperswitch directly — keeping payment credentials and retry logic in one place.

```
Indus  ──► POST /payments        ─┐
                                   ├─► Payments (Rust) ──► Hyperswitch
Merchant ──► GET /payments/{id}  ─┘
```

Set `PAYMENTS_SERVICE_URL=http://localhost:9000` on both Indus and Merchant to enable this mode.

---

## Endpoints

All paths mirror the Hyperswitch API exactly — the proxy forwards requests and returns responses unchanged.

| Method | Path |
|--------|------|
| `POST` | `/payments` |
| `POST` | `/payments/{id}` |
| `POST` | `/payments/{id}/confirm` |
| `POST` | `/payments/{id}/confirm_intent` |
| `GET`  | `/payments/{id}` |
| `GET`  | `/payments/{id}/payment_methods` |
| `POST` | `/payments/{id}/cancel` |
| `POST` | `/payments/{id}/cancel_post_capture` |
| `POST` | `/payments/{id}/capture` |
| `POST` | `/payments/{id}/incremental_authorization` |
| `POST` | `/payments/{id}/extend_authorization` |
| `POST` | `/payments/session_tokens` |
| `GET`  | `/payment_links/{id}` |
| `GET`  | `/payments` |
| `POST` | `/payments/{id}/3ds/authentication` |
| `POST` | `/payments/{id}/complete_authorize` |
| `POST` | `/payments/{id}/create_external_sdk_tokens` |
| `POST` | `/payments/{id}/update_metadata` |
| `POST` | `/payments/{id}/eligibility` |
| `POST` | `/payment_method_sessions` |
| `POST` | `/api_keys/{merchant_id}` |
| `GET`  | `/health` |

---

## Env Vars

| Var | Default | Notes |
|-----|---------|-------|
| `HYPERSWITCH_BASE_URL` | `https://sandbox.hyperswitch.io` | |
| `HYPERSWITCH_API_KEY` | — | Secret API key |
| `HYPERSWITCH_PUBLISHABLE_KEY` | — | For session tokens / payment links |
| `HYPERSWITCH_ADMIN_API_KEY` | — | For API key management |
| `HYPERSWITCH_VAULT_API_KEY` | — | For payment method sessions |
| `HYPERSWITCH_API_KEY_HEADER` | `api-key` | Header name Hyperswitch expects |
| `HYPERSWITCH_MERCHANT_ID` | optional | Forwarded as `x-merchant-id` |
| `HYPERSWITCH_PROFILE_ID` | optional | Forwarded as `X-Profile-Id` |
| `HYPERSWITCH_TIMEOUT_SECONDS` | `20` | |
| `HYPERSWITCH_MAX_RETRIES` | `3` | |
| `HYPERSWITCH_RETRY_BACKOFF_MS` | `200` | |
| `HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH` | `/v2/payment-method-session` | |
| `PAYMENTS_PORT` | `9000` | Listen port |

---

## Run locally

```bash
cargo run
```

Or with Docker (via the main `deploy/docker-compose.yml`):

```bash
cd deploy && docker compose up payments
```
