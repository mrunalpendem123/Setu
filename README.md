# ACP-India — The Indus Profile

> India's binding of [OpenAI's Agentic Commerce Protocol](https://openai.com/index/introducing-the-model-spec/).

---

## What is ACP?

OpenAI's **Agentic Commerce Protocol (ACP)** defines a standard for how AI agents complete purchases on behalf of users — without a human typing at a checkout form.

An agent (running on an LLM) can:
1. Browse a merchant's product feed
2. Create a checkout session
3. Pay using a delegated payment token
4. Receive an order confirmation

ACP defines the API shapes, state model, token lifecycle, and extension points that make this work across any merchant.

---

## What this repo proposes

**ACP works out of the box for the US (Stripe + cards). India needs its own binding.**

This repo defines the **Indus Profile** — ACP adapted for India's payment ecosystem and language stack.

| Dimension | Base ACP | ACP-India (Indus) |
|---|---|---|
| Payment processor | Stripe | **Hyperswitch** (UPI + cards) |
| Agent language | English | **Sarvam AI** (Hindi, Tamil, Telugu, ...) |
| Address format | Generic | **Indian PIN code** + state validation |
| Payment methods | Card | **Card + UPI** (collect, intent, QR) |
| Tax metadata | None | **GST** (GSTIN, HSN codes, 18% default) |
| Currency | USD | **INR (paise)** |

Everything else — the checkout session state machine, token lifecycle, order model, capability negotiation, delegated payments — is **identical to base ACP**.

---

## Repo structure

```
spec/                   ← protocol definition (OpenAPI + JSON Schema)
rfc/                    ← design decisions and rationale
docs/                   ← India profile, principles, configuration
examples/               ← concrete request/response walkthroughs

indus/                  ← reference: Indus orchestrator (agent-side)
merchant/               ← reference: merchant service (seller-side)
payments/               ← reference: Hyperswitch proxy (Rust)
psp/                    ← reference: delegated payment handler stub

deploy/                 ← Docker Compose (if you want containers)
scripts/                ← dev helpers
```

The **spec, rfc, docs, and examples folders are the protocol**. The code is a reference implementation to prove it works — not a product.

---

## The 4 API calls that define the protocol

```
1.  POST /indus/checkout
    Agent → Indus, with items + buyer + address
    Indus → Merchant, issues buyer/fulfillment tokens (address never leaves Indus)

2.  POST /indus/checkout/{id}/update
    Agent picks a shipping option → session becomes ready_for_payment

3.  POST /indus/checkout/{id}/payment_intent
    Indus → Hyperswitch, creates UPI or card payment
    Returns payment_id + client_secret for the agent's UX

4.  POST /indus/checkout/{id}/complete
    Agent sends payment_id → Merchant verifies with Hyperswitch → Order created
```

That's the whole flow. The rest is India-specific wiring.

---

## Quick start (no Docker)

Runs entirely on SQLite. No Postgres, no containers.

```bash
# clone
git clone https://github.com/mrunalpendem123/Setu.git
cd Setu

# start both services (SQLite-backed)
./scripts/run_dev.sh
```

Then in another terminal:

```bash
# check capabilities
curl http://localhost:8000/indus/capabilities

# full checkout (Bengaluru shopper, ₹1299 headphones)
curl -s -X POST http://localhost:8000/indus/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_base_url": "http://localhost:8001",
    "items": [{"id": "item_456", "quantity": 1}],
    "buyer": {
      "name": "Raj Kumar",
      "email": "raj@example.com",
      "phone_number": "+919876543210"
    },
    "fulfillment_address": {
      "name": "Raj Kumar",
      "line_one": "12 MG Road",
      "city": "Bengaluru",
      "state": "KA",
      "country": "IN",
      "postal_code": "560001",
      "phone_number": "+919876543210"
    }
  }' | python3 -m json.tool
```

See `examples/` for the full sequence of requests.

---

## India-specific extensions

### UPI payment flow

```jsonc
// POST /indus/checkout/{id}/payment_intent
{
  "amount": 153282,        // paise (₹1532.82)
  "currency": "inr",
  "payment_method": "upi",
  "payment_method_type": "upi_collect",  // or upi_intent, upi_qr
  "upi_data": { "vpa": "raj@upi" }
}
// → status "requires_customer_action" = waiting for UPI approval on phone
// → this is valid, not a failure — protocol accepts it
```

### Indian address validation

```jsonc
{
  "country": "IN",           // must be IN
  "postal_code": "560001",   // must match ^[1-9][0-9]{5}$
  "phone_number": "+919876543210"  // must match ^+91[6-9]\d{9}$
}
```

### GST metadata on line items

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
# multilingual product search
POST /indus/sarvam/product_search
{ "query": "1000 rupee ke andar headphones", "language": "hi", "merchant_base_url": "..." }

# NL checkout assist
POST /indus/sarvam/checkout_assist
{ "session_id": "cs_...", "user_message": "मुझे express delivery चाहिए", "language": "hi" }
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

```bash
curl http://localhost:8001/capabilities
```
```json
{
  "supported_payment_methods": ["card", "upi"],
  "fulfillment_types": ["shipping"],
  "currency": "inr",
  "country": "IN"
}
```

---

## Buyer privacy model

The agent (Indus) owns buyer PII — the merchant never sees it directly.

```
Agent sends address to Indus
  → Indus stores it, issues an opaque token: ftok_<uuid>
  → Merchant receives only the token
  → Merchant redeems it at order completion: POST /indus/tokens/{token}/redeem
  → Token expires after TOKEN_TTL_SECONDS (default 24h)
```

---

## Spec and RFCs

| File | What it defines |
|---|---|
| `spec/2026-02-24/openapi/indus.yaml` | Indus orchestrator API |
| `spec/2026-02-24/openapi/merchant.yaml` | Merchant API |
| `rfc/agentic-checkout.md` | Core checkout flow design |
| `rfc/capability-negotiation.md` | Capability discovery |
| `rfc/merchant-registry.md` | Merchant registry |
| `rfc/discounts.md` | Coupon / discount extension |
| `rfc/payment-handlers.md` | Payment handler binding |
| `docs/india-profile.md` | India profile constraints |
| `docs/protocol-overview.md` | Protocol roles and state model |

---

## Configuration

See [`docs/configuration.md`](docs/configuration.md) for all environment variables.

For Docker-based deployment, see [`deploy/`](deploy/).

---

## License

MIT. See `LICENSE`.
