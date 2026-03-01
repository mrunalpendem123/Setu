# Merchant Service — Reference ACP Seller

This is the reference merchant implementation for the Setu protocol. It exposes the five ACP checkout endpoints that **Indus (the agent)** calls to browse products, create checkout sessions, and confirm orders.

The merchant never handles raw buyer PII. Instead it receives encrypted `buyer_token` and `fulfillment_token` values issued by Indus, redeems them at order time to retrieve the buyer's name / address, then verifies payment directly with Hyperswitch.

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
          merchant → GET  /payments/{id}  (Hyperswitch) ← verifies payment
          merchant → creates order → fires order.created webhook
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
| `POST` | `/webhooks/hyperswitch` | Receive Hyperswitch payment events (UPI async) |
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
        │   awaiting_payment  ←── Hyperswitch fires POST /webhooks/hyperswitch
        │        ↓  payment.succeeded
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

### Hyperswitch (direct mode)

Used when `PAYMENTS_SERVICE_URL` is **not** set.

| Var | Default |
|-----|---------|
| `HYPERSWITCH_BASE_URL` | `https://sandbox.hyperswitch.io` |
| `HYPERSWITCH_API_KEY` | — |
| `HYPERSWITCH_API_KEY_HEADER` | `api-key` |
| `HYPERSWITCH_MERCHANT_ID` | optional |
| `HYPERSWITCH_PROFILE_ID` | optional |
| `HYPERSWITCH_ACCEPTED_STATUSES` | `succeeded,processing,requires_capture,requires_customer_action` |
| `HYPERSWITCH_WEBHOOK_SECRET` | — | HMAC-SHA512 secret for inbound Hyperswitch webhooks |
| `HYPERSWITCH_TIMEOUT_SECONDS` | `20` |
| `HYPERSWITCH_MAX_RETRIES` | `3` |
| `HYPERSWITCH_RETRY_BACKOFF_MS` | `200` |

### Rust payments proxy (optional)

| Var | Notes |
|-----|-------|
| `PAYMENTS_SERVICE_URL` | If set, Hyperswitch calls go through the Rust proxy at port 9000 |
| `PAYMENTS_SERVICE_TIMEOUT_SECONDS` | `20` |

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
export HYPERSWITCH_API_KEY=your_key
export HYPERSWITCH_WEBHOOK_SECRET=your_hs_webhook_secret

uvicorn app.main:app --reload --port 8001
```

To use the Rust payments proxy:

```bash
export PAYMENTS_SERVICE_URL="http://localhost:9000"
```

---

## Feed export

```bash
python -m app.feed_export
```
