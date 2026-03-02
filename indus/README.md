# Indus — The Sarvam-Powered Agent

Indus is the AI agent at the heart of Setu. Think of it exactly like ChatGPT's shopping agent, but built for India: it understands 11 Indic languages via **Sarvam-M**, holds buyer PII securely, and drives purchases through **Razorpay** (UPI / RuPay / NetBanking / cards) — the only PSP with live NPCI-endorsed agentic payments and UPI Reserve Pay (PIN-less).

```
User (Hindi / Tamil / Telugu / ...)
        │
        ▼
  Indus / Sarvam-M  ←── the agent brain
        │
        ├──► Merchant  (product feed, checkout sessions)
        └──► Razorpay  (payment creation, UPI Reserve Pay, Route settlement)
```

Indus orchestrates the full checkout loop:

1. Fetches product feed from the merchant
2. Understands the user's request in their language (Sarvam-M)
3. Creates a checkout session with encrypted buyer / fulfillment tokens (no raw PII sent to merchant)
4. Selects a fulfillment option
5. Creates a payment via Razorpay (UPI collect / intent / QR, card, NetBanking)
6. Completes checkout — merchant redeems tokens + verifies payment via Razorpay
7. Order confirmed — Razorpay Route splits payment to merchant UPI VPA — no browser opened

---

## Endpoints

### Checkout (agent-facing)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/checkout` | Full checkout in one call |
| `POST` | `/indus/checkout/{id}/update` | Update items / shipping |
| `GET`  | `/indus/checkout/{id}` | Retrieve session state |
| `POST` | `/indus/checkout/{id}/cancel` | Cancel session |
| `POST` | `/indus/checkout/{id}/payment_intent` | Create Razorpay payment intent (UPI collect / QR / intent) |
| `POST` | `/indus/checkout/{id}/reserve_pay` | Create UPI Reserve Pay mandate (PIN-less agentic) |
| `POST` | `/indus/checkout/{id}/complete` | Mark checkout complete |
| `POST` | `/indus/checkout/{id}/refund` | Issue refund via Razorpay |

### Token redemption (merchant → Indus)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/tokens/{token}/redeem` | Merchant redeems buyer / fulfillment token |

### Razorpay payment operations

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/indus/payments/{id}` | Retrieve Razorpay payment |
| `POST` | `/indus/payments/{id}/capture` | Capture authorised payment |
| `POST` | `/indus/payments/{id}/refunds` | Issue refund |
| `POST` | `/indus/payments/{id}/transfers` | Razorpay Route transfer to merchant |

### Merchant registry

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/indus/merchants` | Register merchant (name, base_url, upi_vpa, razorpay_account_id) |
| `GET`  | `/indus/merchants` | List all merchants |
| `GET`  | `/indus/merchants/{id}` | Get single merchant |

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
        ├─ UPI async ──→ awaiting_payment  ←── Razorpay webhook fires
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

### Razorpay

| Var | Default | Notes |
|-----|---------|-------|
| `RAZORPAY_KEY_ID` | — | `rzp_test_...` or `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | — | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | — | For inbound webhook signature verification |
| `RAZORPAY_ACCOUNT_ID` | — | Platform Route account |
| `RAZORPAY_TIMEOUT_SECONDS` | `20` | |
| `RAZORPAY_MAX_RETRIES` | `3` | |
| `RAZORPAY_RETRY_BACKOFF_MS` | `200` | |

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
export RAZORPAY_KEY_ID=rzp_test_...
export RAZORPAY_KEY_SECRET=your_secret
export SARVAM_API_KEY=your_sarvam_key

uvicorn app.main:app --reload --port 8000
```
