# Merchant Service — Reference ACP Seller

This is the reference merchant implementation for the Setu protocol. It exposes the five ACP checkout endpoints that **Indus (the agent)** calls to browse products, create checkout sessions, and confirm orders.

The merchant never handles raw buyer PII. Instead it receives encrypted `buyer_token` and `fulfillment_token` values issued by Indus, redeems them at order time to retrieve the buyer's name / address, then verifies payment directly with Razorpay.

```
Indus (agent)
    │
    ├─ GET  /product_feed            ← Indus fetches catalog
    ├─ POST /checkout_sessions        ← Indus creates session (with tokens)
    ├─ POST /checkout_sessions/{id}   ← Indus selects shipping
    ├─ POST /checkout_sessions/{id}/complete  ← Indus submits payment token
    │
    └── on complete:
          merchant → POST /indus/tokens/{btok}/redeem   ← fetches buyer name/email
          merchant → POST /indus/tokens/{ftok}/redeem   ← fetches delivery address
          merchant → GET  /payments/{id}  (Razorpay)   ← verifies payment
          merchant → creates order → fires order.created webhook
          merchant → Razorpay Route transfer to merchant linked account
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/product_feed` | ACP-format product catalog (JSON/CSV) |
| `POST` | `/checkout_sessions` | Create checkout session |
| `GET`  | `/checkout_sessions/{id}` | Retrieve session |
| `POST` | `/checkout_sessions/{id}` | Update session (shipping, items, coupons) |
| `POST` | `/checkout_sessions/{id}/complete` | Pay and create order |
| `POST` | `/checkout_sessions/{id}/cancel` | Cancel session |
| `POST` | `/orders/{id}/update` | Update order status (requires `X-Indus-Key`) |
| `POST` | `/webhooks/razorpay` | Receive Razorpay payment events (UPI async, Route transfer) |
| `GET`  | `/health` | Health check |

---

## Checkout session state machine

```
not_ready_for_payment   ← session created; no fulfillment option yet
        ↓  POST /checkout_sessions/{id}  { fulfillment_option_id }
ready_for_payment
        ↓  POST /checkout_sessions/{id}/complete  { payment_data }
        │
        ├─ UPI async (requires_customer_action)
        │        ↓
        │   awaiting_payment  ←── Razorpay fires POST /webhooks/razorpay
        │        ↓  payment.captured
        └─────── completed   ← order created, webhook fired

any non-terminal → canceled  (terminal)
```

---

## Auth

If `INDUS_API_KEYS` is set, all write requests must include:

```
X-Indus-Key: <token>
```

Token redemption calls (merchant → Indus) use `INDUS_API_KEY` sent as `X-Indus-Key`.

Idempotency: all `POST` requests accept an optional `Idempotency-Key` header.

---

## Env Vars

### Core

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `INDUS_API_KEYS` | — | Keys that Indus uses to call the merchant |
| `INDUS_BASE_URL` | — | Indus base URL for token redemption |
| `INDUS_API_KEY` | — | Key sent to Indus when redeeming tokens |
| `LOG_LEVEL` | `INFO` | |
| `RATE_LIMIT_ENABLED` | `true` | |
| `RATE_LIMIT_REQUESTS` | `60` | |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | |
| `IDEMPOTENCY_TTL_SECONDS` | `86400` | |

### Razorpay

| Var | Default | Notes |
|-----|---------|-------|
| `RAZORPAY_KEY_ID` | — | `rzp_test_...` or `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | — | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | — | HMAC-SHA256 secret for inbound webhook verification |
| `RAZORPAY_MERCHANT_ACCOUNT_ID` | — | Route: merchant linked account ID (`acc_...`) for settlement |
| `RAZORPAY_ACCEPTED_STATUSES` | `captured,authorized,requires_customer_action` | |
| `RAZORPAY_TIMEOUT_SECONDS` | `20` | |
| `RAZORPAY_MAX_RETRIES` | `3` | |
| `RAZORPAY_RETRY_BACKOFF_MS` | `200` | |

### Product feed

| Var | Default |
|-----|---------|
| `MERCHANT_NAME` | — |
| `MERCHANT_URL` | — |
| `MERCHANT_PRIVACY_URL` | — |
| `MERCHANT_TOS_URL` | — |
| `MERCHANT_SUPPORT_URL` | optional |
| `MERCHANT_BRAND` | optional |
| `FEED_ELIGIBLE_SEARCH` | `true` |
| `FEED_ELIGIBLE_CHECKOUT` | `true` |
| `FEED_SHIPPING` | `IN:ALL:Standard:0.00 INR` |
| `FEED_TARGET_COUNTRIES` | `IN` |
| `FEED_STORE_COUNTRY` | `IN` |
| `FEED_GLOBAL_DEFAULTS_PATH` | optional JSON |
| `FEED_ITEM_OVERRIDES_PATH` | optional JSON |
| `FEED_FORMAT` | `json` / `csv` |
| `FEED_OUTPUT_PATH` | `./export/product_feed.json` |
| `FEED_PUSH_URL` | optional |
| `FEED_PUSH_METHOD` | `POST` |
| `FEED_PUSH_API_KEY` | optional |

### Outbound order webhooks

| Var | Default | Notes |
|-----|---------|-------|
| `ORDER_WEBHOOK_URL` | — | Where to POST `order.created` / `order.updated` events |
| `ORDER_WEBHOOK_SECRET` | — | HMAC-SHA256 signing secret for `Merchant-Signature` header |
| `ORDER_EVENT_STYLE` | `dot` | `dot` → `order.created`; `underscore` → `order_created` |
| `ORDER_WEBHOOK_TIMEOUT_SECONDS` | `5` | |
| `ORDER_WEBHOOK_MAX_RETRIES` | `3` | |
| `ORDER_WEBHOOK_RETRY_BACKOFF_MS` | `200` | |

### Audit logging

Financial events (payment verification, order creation) are written to the `audit_logs` table automatically.

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/indus"
export INDUS_API_KEYS=demo_key
export INDUS_BASE_URL="http://localhost:8000"
export INDUS_API_KEY=demo_key
export RAZORPAY_KEY_ID=rzp_test_...
export RAZORPAY_KEY_SECRET=your_secret
export RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

uvicorn app.main:app --reload --port 8001
```

---

## Feed export

```bash
python -m app.feed_export
```
