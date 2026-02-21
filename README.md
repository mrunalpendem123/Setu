# Indus Checkout + Hyperswitch (Setu)

This repo contains a complete, working **Indus checkout orchestration** stack for India with **UPI + cards** via Hyperswitch. It is built to match the OpenAI Commerce checkout flow and status model, but **remains Indus‑native** (no ACP protocol headers or schema requirements).

It includes:

- **Indus Orchestrator** (client-facing API)
- **Merchant API** (partner merchant MoR)
- **Hyperswitch integration** (payments create/confirm/verify + full payment API pass‑through)
- **Sarvam proxy integration** (optional, via configured endpoint)
- **Product Feed** (JSON/CSV)
- **Postgres persistence**
- **Idempotency** support
- **Webhooks** for order events

---

## Architecture (High Level)

- Indus App talks to **Indus Orchestrator**.
- Indus Orchestrator talks to **Merchant API** for checkout/session/order.
- Indus Orchestrator talks to **Hyperswitch** for payment creation & optional lifecycle actions.
- Merchant API verifies payment with Hyperswitch on completion.

### Architecture Flowchart

```mermaid
flowchart LR
  subgraph "Client"
    UserApp["Indus App (client/UI)"]
  end

  subgraph "Indus Orchestrator Service"
    IndusAPI["Indus API (FastAPI)"]
    IndusDB["Indus Postgres\nindus_sessions, indus_payments, indus_order_events"]
  end

  subgraph "Merchant Service"
    MerchantAPI["Merchant API (FastAPI)"]
    MerchantDB["Merchant Postgres\ncheckout_sessions, orders, idempotency_keys, audit_logs"]
    Feed["Product Feed Endpoint\nGET /product_feed"]
  end

  subgraph "Payments"
    Hyperswitch["Hyperswitch API"]
  end

  UserApp -->|"Checkout, Payment Intent, Complete"| IndusAPI
  IndusAPI -->|"Create/Update/Get/Cancel/Complete"| MerchantAPI
  IndusAPI -->|"Create Payment\n/indus/checkout/{id}/payment_intent"| Hyperswitch
  MerchantAPI -->|"Verify Payment\nGET /payments/{payment_id}"| Hyperswitch
  MerchantAPI -->|"Order webhook\norder.created / order.updated"| IndusAPI

  IndusAPI --> IndusDB
  MerchantAPI --> MerchantDB
  MerchantAPI --> Feed
```

Services:

- `indus/` – orchestrator (client-facing)
- `merchant/` – merchant API (MoR)
- `psp/` – ACP delegated payment stub (unused; safe to delete if you don’t need it)

---

## Checkout Status Flow

The checkout session status matches OpenAI Commerce conventions:

```
not_ready_for_payment -> ready_for_payment -> completed (or canceled)
```

`not_ready_for_payment` means fulfillment address or option is missing.

### Checkout Flowchart

```mermaid
sequenceDiagram
  participant U as "Indus App"
  participant I as "Indus API"
  participant M as "Merchant API"
  participant H as "Hyperswitch"
  participant MDB as "Merchant DB"
  participant IDB as "Indus DB"

  U->>I: "POST /indus/checkout"
  I->>M: "POST /checkout_sessions"
  M->>MDB: "create checkout_session"
  M-->>I: "checkout_session (status: not_ready_for_payment)"
  I->>IDB: "store indus_session"
  I-->>U: "checkout_session"

  U->>I: "POST /indus/checkout/{id}/update\n(fulfillment_address + fulfillment_option_id)"
  I->>M: "POST /checkout_sessions/{id}"
  M->>MDB: "update session + totals"
  M-->>I: "checkout_session (status: ready_for_payment)"
  I-->>U: "checkout_session"

  U->>I: "POST /indus/checkout/{id}/payment_intent"
  I->>H: "POST /payments (Hyperswitch)"
  H-->>I: "payment_id + client_secret"
  I->>IDB: "store payment record"
  I-->>U: "payment_id + client_secret"

  U->>I: "POST /indus/checkout/{id}/complete\n(payment_data.token)"
  I->>M: "POST /checkout_sessions/{id}/complete"
  M->>H: "GET /payments/{payment_id} (verify)"
  H-->>M: "status/amount/currency"
  M->>MDB: "mark completed, create order"
  M-->>I: "order summary"
  I-->>U: "order_id + status"
```

---

## Payment Flow (UPI / Cards via Hyperswitch)

1. **Create checkout** (`/indus/checkout`) → returns checkout session.
2. **Update checkout** with `fulfillment_address` + `fulfillment_option_id` → status becomes `ready_for_payment`.
3. **Create payment intent** (`/indus/checkout/{id}/payment_intent`) → calls Hyperswitch `/payments`.
4. **Complete checkout** (`/indus/checkout/{id}/complete`) with `payment_data.token` → merchant verifies via Hyperswitch `/payments/{id}`.

### Payment Flowchart

```mermaid
flowchart TD
  Start["Start Payment (Indus)"]
  Create["POST /indus/checkout/{id}/payment_intent"]
  HSCreate["Hyperswitch /payments (create)"]
  PayFlow["User completes UPI or card flow"]
  Confirm["Optional: /indus/payments/{id}/confirm"]
  Verify["Merchant verifies /payments/{id}"]
  Complete["Checkout Complete -> Order Created"]

  Start --> Create
  Create --> HSCreate
  HSCreate --> PayFlow
  PayFlow --> Confirm
  PayFlow --> Verify
  Confirm --> Verify
  Verify --> Complete
```

---

## Hyperswitch API Coverage (Indus Pass‑Through)

Indus exposes nearly the entire Hyperswitch Payments API (as pass‑through):

- Create/update/confirm/retrieve/cancel/capture payments
- Incremental auth / extend auth
- Session tokens
- Payment link retrieval
- List payments
- 3DS authentication
- Complete authorize
- Update metadata
- Submit eligibility
- Payment method sessions (vault key)
- API key creation (admin key)

See `indus/README.md` for the full list of endpoints.

---

## Repo Layout

```
/indus
  /app
    main.py              # Indus API + Hyperswitch pass-through
    hyperswitch.py       # Hyperswitch client (auth + retries)
    models.py            # Indus API schema
    db.py                # Postgres persistence
    merchant_client.py   # Merchant API client
/merchant
  /app
    main.py              # Merchant checkout/order API
    payment_verify.py    # Hyperswitch verification
    feed.py              # Product feed builder
    feed_export.py       # Export/push feed
    models.py            # Merchant schema
    db.py                # Postgres persistence
/psp
  # ACP delegated payment stub (unused)
```

---

## Environment Variables

### Common

- `DATABASE_URL` – Postgres connection string
- `LOG_LEVEL` (default `INFO`)
- `RATE_LIMIT_ENABLED` (default `true`)
- `RATE_LIMIT_REQUESTS` (default `60`)
- `RATE_LIMIT_WINDOW_SECONDS` (default `60`)

### Indus Orchestrator

- `INDUS_API_KEY` – optional internal auth between Indus → Merchant

Hyperswitch:

- `HYPERSWITCH_BASE_URL` (default `https://sandbox.hyperswitch.io`)
- `HYPERSWITCH_API_KEY`
- `HYPERSWITCH_API_KEY_HEADER` (default `api-key`)
- `HYPERSWITCH_MERCHANT_ID` (optional)
- `HYPERSWITCH_PUBLISHABLE_KEY` (required for session tokens / payment links)
- `HYPERSWITCH_ADMIN_API_KEY` (required for API key creation)
- `HYPERSWITCH_VAULT_API_KEY` (required for payment method sessions)
- `HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH` (default `/v2/payment-method-session`)
- `HYPERSWITCH_TIMEOUT_SECONDS` (default `20`)
- `HYPERSWITCH_MAX_RETRIES` (default `3`)
- `HYPERSWITCH_RETRY_BACKOFF_MS` (default `200`)

### Merchant API

- `INDUS_API_KEYS` – comma‑separated keys to authorize Indus
- `HYPERSWITCH_BASE_URL`, `HYPERSWITCH_API_KEY`, `HYPERSWITCH_API_KEY_HEADER`, `HYPERSWITCH_MERCHANT_ID`
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

Sarvam (optional):

- `SARVAM_BASE_URL`
- `SARVAM_API_KEY`
- `SARVAM_API_KEY_HEADER` (default `api-subscription-key`)
- `SARVAM_PROXY_PATH`
- `SARVAM_TIMEOUT_SECONDS` (default `20`)
- `SARVAM_MAX_RETRIES` (default `2`)
- `SARVAM_RETRY_BACKOFF_MS` (default `200`)

---

## Quick Start (Local)

### 1) Merchant API

```bash
cd merchant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/merchant"
export INDUS_API_KEYS=demo_key
export HYPERSWITCH_API_KEY=your_key
export MERCHANT_NAME="Demo Merchant"
export MERCHANT_URL="https://merchant.example.com"
export MERCHANT_PRIVACY_URL="https://merchant.example.com/privacy"
export MERCHANT_TOS_URL="https://merchant.example.com/terms"
export MERCHANT_SUPPORT_URL="https://merchant.example.com/support"
export MERCHANT_BRAND="Demo Brand"
uvicorn app.main:app --reload --port 8001
```

### 2) Indus Orchestrator

```bash
cd indus
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/indus"
export INDUS_API_KEY=demo_key
export HYPERSWITCH_API_KEY=your_key
export HYPERSWITCH_PUBLISHABLE_KEY=your_publishable_key
export HYPERSWITCH_ADMIN_API_KEY=your_admin_key
export HYPERSWITCH_VAULT_API_KEY=your_vault_key
uvicorn app.main:app --reload --port 8000
```

## Quick Start (Docker)

```bash
export HYPERSWITCH_API_KEY=your_key
export HYPERSWITCH_PUBLISHABLE_KEY=your_publishable_key
export HYPERSWITCH_ADMIN_API_KEY=your_admin_key
export HYPERSWITCH_VAULT_API_KEY=your_vault_key
docker compose up --build
```

Indus will be on `http://localhost:8000` and Merchant on `http://localhost:8001`.

---

## Example Flow (curl)

### Create checkout

```bash
curl -s -X POST http://localhost:8000/indus/checkout \
  -H 'Content-Type: application/json' \
  -d '{
    "merchant_base_url": "http://localhost:8001",
    "items": [{"id": "item_123", "quantity": 1}],
    "buyer": {"email": "user@example.com"}
  }'
```

### Provide fulfillment details

```bash
curl -s -X POST http://localhost:8000/indus/checkout/<SESSION_ID>/update \
  -H 'Content-Type: application/json' \
  -d '{
    "fulfillment_address": {
      "name": "Asha Verma",
      "line_one": "11 MG Road",
      "city": "Bengaluru",
      "state": "KA",
      "country": "IN",
      "postal_code": "560001",
      "phone_number": "+91 90000 00000"
    },
    "fulfillment_option_id": "standard"
  }'
```

### Create payment intent

```bash
curl -s -X POST http://localhost:8000/indus/checkout/<SESSION_ID>/payment_intent \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 99900,
    "currency": "inr",
    "payment_method": "upi",
    "payment_method_type": "upi_intent"
  }'
```

### Complete checkout

```bash
curl -s -X POST http://localhost:8000/indus/checkout/<SESSION_ID>/complete \
  -H 'Content-Type: application/json' \
  -d '{
    "payment_data": {
      "provider": "hyperswitch",
      "token": "<PAYMENT_ID>"
    }
  }'
```

### Sarvam proxy (optional)

Set `SARVAM_BASE_URL`, `SARVAM_API_KEY`, and `SARVAM_PROXY_PATH`, then:

```bash
curl -s -X POST http://localhost:8000/indus/sarvam/proxy \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "Find me a suitcase under 10k"
  }'
```

---

## Product Feed

- `GET /product_feed` returns JSON
- `GET /product_feed?format=csv` returns CSV
- `python -m app.feed_export` writes to `FEED_OUTPUT_PATH` and optionally pushes to `FEED_PUSH_URL`

---

## Database Tables

**Indus DB**

- `indus_sessions` – checkout sessions
- `indus_payments` – payment records
- `indus_order_events` – webhook logs

**Merchant DB**

- `checkout_sessions` – merchant checkout sessions
- `orders` – created orders
- `idempotency_keys` – idempotency store
- `audit_logs` – payment verification and order creation events

---

## Security & Idempotency

- Optional internal auth between Indus and Merchant via `X-Indus-Key`.
- Idempotency supported for POSTs when `Idempotency-Key` is supplied.

## PCI / Card Data Handling

- This system **does not accept or store raw card PAN**.
- Card data should be collected by Hyperswitch/PSP‑hosted UI or SDKs.
- You are responsible for ensuring your deployment meets PCI‑DSS scope requirements.

---

## What’s Not Included

- Sarvam LLM API calls (not wired yet)
- Frontend UI (this repo is API + backend only)
- Live connector config for Hyperswitch (must be set in your Hyperswitch account)

---

## Troubleshooting

- **`HYPERSWITCH_*` errors** → check required keys and merchant ID.
- **Payment verification fails** → check payment status, currency, amount.
- **Feed errors** → missing required merchant fields.

---

## License

Add your preferred license.
