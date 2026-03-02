# Setu — Agentic Commerce Protocol for India

> AI agents that shop for you, built for India's payment stack.

---

## What is Setu?

**Setu** is an open protocol that lets AI agents complete purchases on behalf of users — without opening a browser, filling forms, or navigating checkout flows.

The **agent** in Setu is **Indus** — powered by **Sarvam-M**, India's multilingual AI model. Think of it exactly like ChatGPT's shopping feature, but built for India: it speaks Hindi, Tamil, Telugu, Kannada, and 7 other Indian languages, and pays natively via UPI and Razorpay instead of Stripe.

```
User says: "ek white kurta dikhao under 1500 mein"

Indus (Sarvam AI):
  1. Understands the request in Hindi
  2. Fetches product feed from merchant
  3. Shows options, user picks one
  4. Collects address & payment info
  5. Creates payment via Razorpay (UPI / card)
  6. Completes checkout with merchant
  7. Order confirmed — no browser opened
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                        User                          │
│          chat & shop  │  payment card / UPI info     │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│           Indus  /  Sarvam-M  (the Agent)            │
│                                                      │
│  • Understands 11 Indic languages (Sarvam-M)         │
│  • Manages checkout session state                    │
│  • Issues scoped buyer/fulfillment tokens            │
│  • Orchestrates merchant + Razorpay calls            │
└───────────────┬──────────────────┬───────────────────┘
                │                  │
   Product Feed │                  │ Get Payment Token
   Checkout     │                  │ (UPI / card / netbanking)
                ▼                  ▼
       ┌──────────────┐   ┌────────────────────┐
       │   Merchant   │   │   Razorpay (PSP)   │
       │              │   │                    │
       │ /checkout_   │   │ POST /orders       │
       │  sessions    │   │ → order_id         │
       │              │   │                    │
       │ Verifies  ───┼──►│ GET /payments/{id} │
       │ payment      │   │                    │
       │              │   └────────────────────┘
       │ Order webhook│
       └──────┬───────┘
              │
              ▼
         User / webhook endpoint
         (order updates)
```

Setu implements the same pattern as ChatGPT's shopping agent — substituting India's stack:

| ChatGPT Shopping | Setu |
|---|---|
| ChatGPT (GPT-4) | Indus (Sarvam-M, 11 Indic languages) |
| Stripe | Razorpay (UPI + RuPay + NetBanking + cards) |
| English only | Hindi, Tamil, Telugu, Kannada + 7 more |
| USD / EUR | INR (paise), GST-aware |

---

## How the flow works

### Step 1 — Agent fetches product feed

```
Indus → GET http://merchant.com/product_feed

Merchant: [{ id, title, price_inr, hsn_code, gst_rate, ... }]
```

### Step 2 — Agent creates a checkout session

```
Indus → POST http://merchant.com/checkout_sessions
{
  items: [{ id: "item_456", quantity: 1 }],
  buyer_token: "btok_...",         ← encrypted token; Indus holds the PII
  fulfillment_token: "ftok_..."    ← encrypted token; Indus holds the address
}

Merchant: {
  id: "cs_abc",
  status: "not_ready_for_payment",
  line_items: [...],
  totals: { subtotal: 129900, tax: 23382, total: 153282 },  // paise
  fulfillment_options: [
    { id: "standard", title: "3–5 days", cost: 0 },
    { id: "express",  title: "1–2 days", cost: 4900 }
  ],
  payment_handlers: [{ id: "com.razorpay.upi_collect", ... }]
}
```

### Step 3 — Agent selects shipping → session becomes ready

```
Indus → POST http://merchant.com/checkout_sessions/cs_abc
{ fulfillment_option_id: "express" }

Merchant: { status: "ready_for_payment", totals: { total: 158182 } }
```

### Step 4 — Agent creates payment via Razorpay

```
Indus → POST /indus/checkout/cs_abc/payment_intent
{
  amount: 158182,
  currency: "INR",
  payment_method: "upi",
  payment_method_type: "upi_collect",
  upi_data: { vpa: "raj@upi" }
}

Razorpay: {
  payment_id: "pay_xyz",
  razorpay_order_id: "order_abc",
  status: "pending_customer_action"   ← user approves in their UPI app
}
```

### Step 5 — Agent completes checkout with merchant

```
Indus → POST http://merchant.com/checkout_sessions/cs_abc/complete
{ payment_data: { provider: "razorpay", token: "pay_xyz" } }

Merchant internally:
  1. Redeems buyer_token      → Indus  (fetches buyer name/email)
  2. Redeems fulfillment_token → Indus (fetches delivery address)
  3. Verifies payment status   → Razorpay GET /payments/pay_xyz
  4. Creates order, fires order.created webhook
  5. Razorpay Route transfer   → merchant UPI VPA settled automatically

Merchant: { order_id: "ord_123", status: "completed" }
```

**5 steps. No browser. No form. No redirect.**

---

## UPI async flow (requires_customer_action)

UPI payments don't confirm immediately — the user must approve on their phone. Setu handles this automatically:

```
Step 4 → Razorpay returns status: "pending_customer_action"
Step 5 → Merchant sets session to "awaiting_payment"

[User opens UPI app and approves]

Razorpay fires: POST /webhooks/razorpay  (on merchant)
  → Merchant creates order automatically
  → Triggers Razorpay Route transfer to merchant VPA
  → Fires order.created webhook
  → Agent sees order_id in next poll
```

---

## India-specific features

### All three UPI variants

```jsonc
{ "payment_method_type": "upi_collect", "upi_data": { "vpa": "raj@upi" } }  // pull from VPA
{ "payment_method_type": "upi_intent"  }                                      // deep-link to app
{ "payment_method_type": "upi_qr"      }                                      // QR code
```

### UPI Reserve Pay (PIN-less agentic payments)

```jsonc
POST /indus/checkout/{id}/reserve_pay
{ "vpa": "raj@upi", "max_amount": 500000 }
// User authorises once → agent debits freely up to max_amount
```

### Indian address validation

```jsonc
{
  "country": "IN",
  "postal_code": "560001",          // ^[1-9][0-9]{5}$
  "phone_number": "+919876543210"   // ^+91[6-9]\d{9}$
}
```

### GST on line items

```jsonc
{
  "gst_metadata": {
    "hsn_code": "85183000",
    "tax_label": "GST",
    "tax_rate_pct": 18.0,
    "gstin": "29ABCDE1234F1Z5"   // optional, for B2B
  }
}
```

### Sarvam multilingual checkout

```bash
# "1000 rupee ke andar headphones chahiye" (Hindi)
POST /indus/sarvam/product_search
{
  "query": "1000 rupee ke andar headphones chahiye",
  "language": "hi",
  "merchant_base_url": "http://merchant.example.com"
}
```

---

## Repo structure

```
indus/         ← Indus — the Sarvam-powered agent runtime (port 8000)
merchant/      ← Reference merchant service — ACP checkout endpoints (port 8001)
psp/           ← Delegated payment stub — for vt_* token flows (port 8002)
payments/      ← DEPRECATED: Hyperswitch Rust proxy (retained for git history)

spec/          ← Protocol definition (OpenAPI + JSON Schema)
rfc/           ← Design decisions and rationale
docs/          ← India profile, configuration reference
examples/      ← Concrete request/response walkthroughs
deploy/        ← Docker Compose for the full stack
demo/          ← Sarvam Shopping Playground (single-file live demo)
scripts/       ← Dev helpers
```

---

## Quick start

```bash
git clone https://github.com/your-org/setu.git && cd setu

# Fill in your API keys
cp .env.example .env
# RAZORPAY_KEY_ID=rzp_test_...   (get from dashboard.razorpay.com)
# SARVAM_API_KEY=...             (get from dashboard.sarvam.ai)

# Start all services
cd deploy && docker compose up --build
```

Then run a full checkout:

```bash
curl -s -X POST http://localhost:8000/indus/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_base_url": "http://localhost:8001",
    "items": [{ "id": "item_001", "quantity": 1 }],
    "buyer": { "name": "Raj Kumar", "email": "raj@example.com" },
    "fulfillment_address": {
      "name": "Raj Kumar", "line_one": "12 MG Road",
      "city": "Bengaluru", "state": "KA",
      "country": "IN", "postal_code": "560001",
      "phone_number": "+919876543210"
    }
  }' | python3 -m json.tool
```

See `examples/` for the complete flow with payment and completion.

---

## Try the demo

```bash
cd demo
pip install -r requirements.txt
export SARVAM_API_KEY=your_key
python server.py
# Open http://localhost:3000
```

Chat in any Indian language, browse products, pay with UPI or card (Fauxpay test cards included).

---

## Services

| Service | Port | Role |
|---|---|---|
| **Indus** | 8000 | Sarvam-powered agent — the brain of the operation |
| **Merchant** | 8001 | ACP checkout endpoints, product feed, order management |
| **PSP stub** | 8002 | Delegated token endpoint — for `vt_*` pre-authorized payment tokens |
| **Postgres** | 5432 | Persistent store for sessions, payments, tokens, orders |

---

## Essential env vars

```bash
# Razorpay (required)
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_ACCOUNT_ID=acc_...              # platform Route account
RAZORPAY_MERCHANT_ACCOUNT_ID=acc_...     # merchant linked account for settlement

# Sarvam AI (required for multilingual features)
SARVAM_API_KEY=your_key
SARVAM_BASE_URL=https://api.sarvam.ai

# Database
DATABASE_URL=postgresql+psycopg://setu:setu@localhost:5432/indus

# Service auth
INDUS_API_KEYS=demo_key      # merchant → indus token redemption
INDUS_API_KEY=demo_key       # indus → merchant calls

# Webhooks
ORDER_WEBHOOK_URL=https://your-endpoint.example.in/webhook
ORDER_WEBHOOK_SECRET=your_secret
```

Full reference: `.env.example` and `docs/configuration.md`.

---

## Docs

| | |
|---|---|
| `docs/protocol-overview.md` | Roles, session state machine, extension points |
| `docs/india-profile.md` | UPI, GST, PIN codes — full India spec |
| `docs/configuration.md` | Every env var, every service |
| `rfc/agentic-checkout.md` | Core checkout flow design |
| `rfc/payment-handlers.md` | `com.razorpay.upi_collect` handler binding |
| `examples/` | Full request/response walkthroughs |

---

## License

MIT. See `LICENSE`.
