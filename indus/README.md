# Indus — The Sarvam-Powered Agent

Indus is the AI agent at the heart of Setu. Think of it exactly like ChatGPT's shopping agent, but built for India: it understands 11 Indic languages via **Sarvam-M**, holds buyer PII securely, and drives purchases through **Hyperswitch** (UPI / RuPay / NetBanking / cards) instead of Stripe.

```
User (Hindi / Tamil / Telugu / ...)
        │
        ▼
  Indus / Sarvam-M  ←── the agent brain
        │
        ├──► Merchant  (product feed, checkout sessions)
        └──► Hyperswitch  (payment creation & confirmation)
```

Indus orchestrates the full checkout loop:

1. Fetches product feed from the merchant
2. Understands the user's request in their language (Sarvam-M)
3. Creates a checkout session with encrypted buyer / fulfillment tokens (no raw PII sent to merchant)
4. Selects a fulfillment option
5. Creates a payment via Hyperswitch (UPI collect / intent / QR, card, NetBanking)
6. Completes checkout — merchant redeems tokens + verifies payment via Hyperswitch
7. Order confirmed — no browser opened

---

## Endpoints

### Checkout (agent-facing)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/checkout` | Full checkout in one call |
| `POST` | `/indus/checkout/{id}/update` | Update items / shipping |
| `GET`  | `/indus/checkout/{id}` | Retrieve session state |
| `POST` | `/indus/checkout/{id}/cancel` | Cancel session |
| `POST` | `/indus/checkout/{id}/payment_intent` | Create Hyperswitch payment intent |
| `POST` | `/indus/checkout/{id}/complete` | Mark checkout complete |
| `POST` | `/indus/checkout/{id}/refund` | Issue refund via Hyperswitch |

### Token redemption (merchant → Indus)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/tokens/{token}/redeem` | Merchant redeems buyer / fulfillment token |

### Hyperswitch passthrough (proxied)

| Method | Path |
|--------|------|
| `POST` | `/indus/payments` |
| `POST` | `/indus/payments/{id}` |
| `POST` | `/indus/payments/{id}/confirm` |
| `POST` | `/indus/payments/{id}/confirm_intent` |
| `GET`  | `/indus/payments/{id}` |
| `GET`  | `/indus/payments/{id}/payment_methods` |
| `POST` | `/indus/payments/{id}/cancel` |
| `POST` | `/indus/payments/{id}/cancel_post_capture` |
| `POST` | `/indus/payments/{id}/capture` |
| `POST` | `/indus/payments/{id}/incremental_authorization` |
| `POST` | `/indus/payments/{id}/extend_authorization` |
| `POST` | `/indus/payments/session_tokens` |
| `GET`  | `/indus/payment_links/{id}` |
| `GET`  | `/indus/payments` |
| `POST` | `/indus/payments/{id}/3ds/authentication` |
| `POST` | `/indus/payments/{id}/complete_authorize` |
| `POST` | `/indus/payments/{id}/create_external_sdk_tokens` |
| `POST` | `/indus/payments/{id}/update_metadata` |
| `POST` | `/indus/payments/{id}/eligibility` |
| `POST` | `/indus/payment_method_sessions` |
| `POST` | `/indus/api_keys/{merchant_id}` |
| `POST` | `/indus/payments/{id}/refunds` |

### Sarvam AI

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/sarvam/proxy` | Raw Sarvam-M proxy |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/orders` | Receive order events from merchant |

### Utility

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |

---

## Checkout session state machine

```
not_ready_for_payment
        ↓  (fulfillment option selected)
ready_for_payment
        ↓  (complete called)
        ├─ UPI async ──→ awaiting_payment  ←── Hyperswitch webhook fires
        │                        ↓
        └─────────────────→ completed   (order created)

any state → canceled  (terminal)
```

---

## Env Vars

### Core

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `INDUS_API_KEYS` | — | Comma-separated keys; merchants use these to redeem tokens |
| `INDUS_API_KEY` | — | Key Indus sends to merchant |
| `TOKEN_TTL_SECONDS` | `86400` | Buyer / fulfillment token lifetime |
| `LOG_LEVEL` | `INFO` | |
| `RATE_LIMIT_ENABLED` | `true` | |
| `RATE_LIMIT_REQUESTS` | `60` | |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | |

### Hyperswitch (direct mode)

Used when `PAYMENTS_SERVICE_URL` is **not** set.

| Var | Default |
|-----|---------|
| `HYPERSWITCH_BASE_URL` | `https://sandbox.hyperswitch.io` |
| `HYPERSWITCH_API_KEY` | — |
| `HYPERSWITCH_PUBLISHABLE_KEY` | — |
| `HYPERSWITCH_ADMIN_API_KEY` | — |
| `HYPERSWITCH_VAULT_API_KEY` | — |
| `HYPERSWITCH_API_KEY_HEADER` | `api-key` |
| `HYPERSWITCH_MERCHANT_ID` | optional |
| `HYPERSWITCH_PROFILE_ID` | optional |
| `HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH` | `/v2/payment-method-session` |
| `HYPERSWITCH_TIMEOUT_SECONDS` | `20` |
| `HYPERSWITCH_MAX_RETRIES` | `3` |
| `HYPERSWITCH_RETRY_BACKOFF_MS` | `200` |

### Rust payments proxy (optional)

| Var | Default |
|-----|---------|
| `PAYMENTS_SERVICE_URL` | — (if set, Hyperswitch calls go through Rust proxy) |
| `PAYMENTS_SERVICE_TIMEOUT_SECONDS` | `20` |

### Sarvam AI

| Var | Default |
|-----|---------|
| `SARVAM_BASE_URL` | — |
| `SARVAM_API_KEY` | — |
| `SARVAM_API_KEY_HEADER` | `api-subscription-key` |
| `SARVAM_PROXY_PATH` | — |
| `SARVAM_TIMEOUT_SECONDS` | `20` |
| `SARVAM_MAX_RETRIES` | `2` |
| `SARVAM_RETRY_BACKOFF_MS` | `200` |

### Webhooks

| Var | Notes |
|-----|-------|
| `ORDER_WEBHOOK_SECRET` | Optional — verify `Merchant-Signature` on inbound order events |

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/indus"
export INDUS_API_KEYS=demo_key
export INDUS_API_KEY=demo_key
export TOKEN_TTL_SECONDS=86400
export HYPERSWITCH_API_KEY=your_key
export HYPERSWITCH_PUBLISHABLE_KEY=pk_...
export SARVAM_API_KEY=your_sarvam_key

uvicorn app.main:app --reload --port 8000
```

To use the Rust payments proxy instead of calling Hyperswitch directly:

```bash
export PAYMENTS_SERVICE_URL="http://localhost:9000"
```
