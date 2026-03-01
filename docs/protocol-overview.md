# Protocol Overview — Setu (ACP-India / Indus Profile)

Setu is India's implementation of the Agentic Commerce Protocol (ACP). It substitutes India's native payment and language stack into the same role pattern that ChatGPT's shopping agent uses with Stripe.

---

## Roles

| Role | What they do | In this repo | Analogy |
|------|-------------|--------------|---------|
| **Buyer** | The human. Speaks in any of 11 Indic languages. Approves purchases. | — | ChatGPT user |
| **Agent** | The AI. Understands the buyer's request, manages session state, orchestrates merchant + PSP calls. | `indus/` (Sarvam-M) | ChatGPT |
| **Merchant** | Implements the 5 ACP checkout endpoints. Stays merchant of record. Never sees raw buyer PII. | `merchant/` | Any online store |
| **PSP** | Issues scoped one-time payment tokens. Processes the actual charge. | Hyperswitch via `payments/` | Stripe |

The agent (Indus / Sarvam-M) is the single orchestrator. It never opens a browser or fills a form. The merchant never handles raw card data. The PSP (Hyperswitch) never knows about the checkout session — it just issues a token and confirms the charge.

---

## End-to-end flow

```
User: "ek white kurta dikhao under 1500 mein"
                │
                ▼
        Indus / Sarvam-M
          (the agent)
                │
    ┌───────────┴────────────┐
    │                        │
    ▼                        ▼
 Merchant               Hyperswitch
 /product_feed          POST /payments
 /checkout_sessions     GET  /payments/{id}
 /checkout_sessions/    (UPI collect / intent / QR /
   {id}/complete         card / NetBanking)
    │
    ▼
 order.created webhook → buyer notified
```

---

## Session states

```
not_ready_for_payment     ← created; fulfillment option not yet selected
        ↓  update with fulfillment_option_id
ready_for_payment         ← all required fields present
        ↓  complete with payment token
        │
        ├─ UPI async ──────────────→ awaiting_payment   ← user approves on phone
        │                                   ↓  Hyperswitch webhook fires
        │                            completed           ← order created (terminal)
        │
        ├─ approval_required=true → pending_approval    ← awaiting merchant review
        │                                   ↓  merchant approves
        │                            ready_for_payment
        │
        ├─ 3DS needed ─────────────→ authentication_required
        │                                   ↓  re-submit with authentication_result
        │                            ready_for_payment
        │
        └─────────────────────────→ completed            ← order created (terminal)

any non-terminal state → canceled  (terminal)
session TTL elapsed    → expired   (terminal, surfaced on read)
```

**Terminal states**: `completed`, `canceled`, `expired`
**Blocking states**: `pending_approval`, `authentication_required`, `awaiting_payment`

---

## The 5 ACP endpoints (every merchant must implement)

```
GET    /product_feed                        return catalog
POST   /checkout_sessions                   create session
GET    /checkout_sessions/{id}              retrieve session
POST   /checkout_sessions/{id}              update session (shipping, items, coupons)
POST   /checkout_sessions/{id}/complete     pay + create order
POST   /checkout_sessions/{id}/cancel       cancel session
```

---

## Token architecture

Indus holds buyer PII. The merchant never receives raw names, emails, or addresses — only encrypted tokens it redeems at order time.

```
1. Indus stores buyer data → issues btok_* (buyer token) + ftok_* (fulfillment token)

2. Indus → Merchant:
     POST /checkout_sessions
     { buyer_token: "btok_...", fulfillment_token: "ftok_..." }

3. At complete time, merchant redeems:
     POST /indus/tokens/btok_.../redeem   → { name, email }
     POST /indus/tokens/ftok_.../redeem   → { address, phone }

Token constraints:
  - TTL: configurable (default 24 h)
  - Single use per redemption type
  - Bound to checkout session ID
```

---

## Payment flow — Hyperswitch

Hyperswitch replaces Stripe in the Indus Profile.

```
1. Indus → Hyperswitch:
     POST /payments
     {
       amount: 158182,          ← paise (₹1,581.82)
       currency: "INR",
       payment_method: "upi",
       payment_method_type: "upi_collect",
       payment_method_data: { upi: { vpa_id: "raj@upi" } },
       metadata: { checkout_session_id: "cs_abc" }
     }

2. Hyperswitch → Indus:
     { payment_id: "pay_xyz", status: "requires_customer_action" }

3. Indus → Merchant:
     POST /checkout_sessions/cs_abc/complete
     { payment_data: { provider: "hyperswitch", token: "pay_xyz" } }

4. Merchant:
     → redeems buyer_token + fulfillment_token from Indus
     → GET /payments/pay_xyz from Hyperswitch (verify status)
     → status "requires_customer_action" → set session to awaiting_payment

5. User approves payment in UPI app

6. Hyperswitch fires:
     POST /webhooks/hyperswitch  (on merchant)
     { event_type: "payment_succeeded", payment_id: "pay_xyz" }

7. Merchant:
     → creates order
     → fires order.created webhook to buyer endpoint
```

---

## India-specific features

### UPI payment types

| Type | Use case |
|------|----------|
| `upi_collect` | Pull from VPA — user approves collect request |
| `upi_intent` | Deep-link to user's UPI app |
| `upi_qr` | Generate QR code for scanning |

### Indian address validation

```json
{
  "country": "IN",
  "postal_code": "560001",         // ^[1-9][0-9]{5}$
  "phone_number": "+919876543210"  // ^\\+91[6-9]\\d{9}$
}
```

### GST on line items

```json
{
  "gst_metadata": {
    "hsn_code": "50072090",
    "tax_label": "GST",
    "tax_rate_pct": 5.0,
    "gstin": "29ABCDE1234F1Z5"
  }
}
```

### Multilingual checkout (Sarvam-M)

```json
POST /indus/sarvam/proxy
{
  "query": "1000 rupee ke andar headphones chahiye",
  "language": "hi"
}
```

Supports: Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Malayalam, Odia, Punjabi, Assamese.

---

## Extension points

| Extension | Description | RFC |
|-----------|-------------|-----|
| Capability negotiation | Agents and merchants advertise supported features | `rfc/capability-negotiation.md` |
| Discounts and coupons | Coupon codes applied during session update | `rfc/discounts.md` |
| Merchant registry | Indus maintains a discoverable list of ACP merchants | `rfc/merchant-registry.md` |
| Agent discovery | How merchants find the right agent endpoint | `rfc/agent-discovery.md` |
| Payment handler binding | `com.hyperswitch.upi` handler specification | `rfc/payment-handlers.md` |
