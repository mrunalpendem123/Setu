# Setu

> An open protocol for AI agents to complete purchases in India — without navigating a browser.

---

## What is Setu?

**Setu** is an agentic commerce protocol for India.

It gives merchants a set of REST API endpoints that AI agents can call to complete a purchase — instead of agents trying to navigate a web browser through a checkout form.

Today, if an AI agent wants to buy something for you, it has to:
- Open a browser
- Click through product pages
- Fill in address forms
- Handle payment redirects
- Hope nothing breaks mid-flow

**Setu replaces all of that.** A merchant implements 5 API endpoints. An agent calls them in sequence. The purchase is done.

```
Agent → POST /checkout_sessions                   (create cart)
Agent → POST /checkout_sessions/{id}              (select shipping)
Agent → POST /delegate_payment                    (get a one-time payment token)
Agent → POST /checkout_sessions/{id}/complete     (pay + confirm order)
```

The **human still approves** — through the agent's UI, not through a merchant's website. The **merchant stays merchant of record**. The **payment token is scoped** — it can only charge the exact amount, in the exact currency, once.

---

## Why India needs its own protocol

Existing agentic commerce flows are built around western payment rails — cards and bank transfers via Stripe.

India's payment reality is different:

| Reality | Why it matters |
|---|---|
| **70%+ of digital payments are UPI** | Generic payment handlers don't support UPI collect / intent / QR natively |
| **Hyperswitch covers all Indian rails** | UPI, RuPay, NetBanking, cards — one API |
| **Sarvam AI speaks Indian languages** | Hindi, Tamil, Telugu, Kannada — buyers don't always shop in English |
| **GST is mandatory on B2B** | Line items need HSN codes + GSTIN, not just a subtotal |
| **PIN codes have strict formats** | `^[1-9][0-9]{5}$` — generic address models fail silently |

**Setu is built for this stack from the ground up.**

---

## What Setu defines

| Dimension | Setu |
|---|---|
| Payment handler | **Hyperswitch** (UPI + cards + NetBanking) |
| Agent layer | **Sarvam AI** (multilingual, India-first) |
| Payment methods | **UPI collect, UPI intent, UPI QR, cards** |
| Address format | **Indian PIN code** + state validation |
| Tax metadata | **GST** — GSTIN, HSN codes, 18% default |
| Currency | **INR in paise** |

---

## Repo structure

```
spec/          ← protocol definition (OpenAPI + JSON Schema)
rfc/           ← design decisions and rationale
docs/          ← India profile, configuration reference
examples/      ← concrete request/response walkthroughs

indus/         ← reference: Indus orchestrator (agent-side)
merchant/      ← reference: merchant service (seller-side)
payments/      ← reference: Hyperswitch proxy (Rust)
psp/           ← reference: delegated payment handler stub

deploy/        ← Docker Compose (if you want containers)
scripts/       ← dev helpers
```

The **spec, rfc, docs, and examples are the protocol**. The code proves it works.

---

## How the flow works

### Step 1 — Agent creates a checkout session

```
Agent → POST http://merchant.com/checkout_sessions
Body: { items, buyer, fulfillment_address }

Merchant responds: {
  id: "cs_abc",
  status: "not_ready_for_payment",   ← missing shipping option
  line_items: [...],
  totals: { subtotal: 129900, tax: 23382, total: 153282 },  // paise
  fulfillment_options: [
    { id: "standard", title: "3-5 days", total: 0 },
    { id: "express",  title: "1-2 days", total: 4900 }
  ],
  payment_handlers: [{ id: "hyperswitch.upi", ... }]
}
```

### Step 2 — Agent picks shipping → session becomes ready

```
Agent → POST http://merchant.com/checkout_sessions/cs_abc
Body: { fulfillment_option_id: "express" }

Merchant responds: { status: "ready_for_payment", totals: { total: 158182 } }
```

### Step 3 — Agent gets a scoped payment token from Hyperswitch

```
Agent → POST http://hyperswitch.com/agentic_commerce/delegate_payment
Body: {
  payment_method: { type: "upi", vpa: "raj@upi" },
  allowance: { amount_cents: 158182, currency: "inr", expires_at: "+30min" },
  risk_signals: { ... }
}

Hyperswitch responds: { id: "dpt_xyz", status: "issued" }
// This token can ONLY charge ₹1581.82, once, before expiry.
```

### Step 4 — Agent completes the checkout with that token

```
Agent → POST http://merchant.com/checkout_sessions/cs_abc/complete
Body: { payment_handler_id: "hyperswitch.upi", payment_token: "dpt_xyz" }

Merchant calls Hyperswitch internally → verifies → creates order
Merchant responds: { order_id: "ord_123", status: "completed" }
```

**4 API calls. No browser. No form. No redirect.**

---

## India-specific extensions

### UPI flows

```jsonc
// Step 3 has three UPI variants:
{ "type": "upi_collect", "vpa": "raj@upi" }   // agent knows buyer's VPA
{ "type": "upi_intent" }                        // deep-link to UPI app (mobile)
{ "type": "upi_qr" }                            // show QR code (desktop/kiosk)

// All three return status: "requires_customer_action"
// = user is approving on their phone — not a failure, a valid pending state
```

### Indian address validation

```jsonc
{
  "country": "IN",                  // must be IN
  "postal_code": "560001",          // ^[1-9][0-9]{5}$  (no leading zero)
  "phone_number": "+919876543210"   // ^+91[6-9]\d{9}$
}
```

### GST on line items

```jsonc
{
  "gst_metadata": {
    "hsn_code": "85183000",
    "tax_label": "GST",
    "tax_rate_pct": 18.0
  }
}
```

### Sarvam AI checkout assistant

```bash
# Buyer says: "1000 rupee ke andar headphones chahiye"
POST /indus/sarvam/product_search
{ "query": "1000 rupee ke andar headphones", "language": "hi", "merchant_base_url": "..." }

# Buyer says: "mujhe express delivery chahiye"
POST /indus/sarvam/checkout_assist
{ "session_id": "cs_abc", "user_message": "express delivery chahiye", "language": "hi" }
```

---

## Capability negotiation

```bash
curl http://localhost:8000/indus/capabilities
```
```json
{
  "protocol_version": "2026-02-24",
  "payment_providers": ["hyperswitch"],
  "payment_methods": ["card", "upi", "netbanking"],
  "token_ttl_seconds": 86400,
  "fulfillment_types": ["shipping"],
  "extensions": ["india_gst", "upi_vpa"]
}
```

---

## Quick start (no Docker, no Postgres)

```bash
git clone https://github.com/mrunalpendem123/Setu.git && cd Setu
./scripts/run_dev.sh
```

```bash
# In another terminal — full checkout for Raj Kumar, Bengaluru
curl -s -X POST http://localhost:8000/indus/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_base_url": "http://localhost:8001",
    "items": [{"id": "item_456", "quantity": 1}],
    "buyer": { "name": "Raj Kumar", "email": "raj@example.com" },
    "fulfillment_address": {
      "name": "Raj Kumar", "line_one": "12 MG Road",
      "city": "Bengaluru", "state": "KA",
      "country": "IN", "postal_code": "560001",
      "phone_number": "+919876543210"
    }
  }' | python3 -m json.tool
```

See `examples/` for the full sequence.

---

## Spec and RFCs

| File | What it covers |
|---|---|
| `spec/2026-02-24/openapi/indus.yaml` | Indus orchestrator API (agent-side) |
| `spec/2026-02-24/openapi/merchant.yaml` | Merchant checkout API |
| `rfc/agentic-checkout.md` | Core checkout flow design |
| `rfc/capability-negotiation.md` | Capability discovery |
| `rfc/payment-handlers.md` | Hyperswitch handler binding |
| `rfc/discounts.md` | Coupon and discount extension |
| `rfc/merchant-registry.md` | Merchant discovery |
| `docs/india-profile.md` | Full India profile spec |
| `docs/protocol-overview.md` | Roles, state model, extension points |

---

## Configuration

See [`docs/configuration.md`](docs/configuration.md).
For Docker deployment, see [`deploy/`](deploy/).

---

## License

MIT. See `LICENSE`.
