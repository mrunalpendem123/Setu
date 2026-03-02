# Protocol Overview — Setu (ACP-India / Indus Profile)

Setu is India's implementation of the Agentic Commerce Protocol (ACP). It substitutes India's native payment and language stack into the same role pattern that ChatGPT's shopping agent uses with Stripe.

---

## Roles

| Role | What they do | In this repo | Analogy |
|------|-------------|--------------|---------|
| **Buyer** | The human. Speaks in any of 11 Indic languages. Approves purchases. | — | ChatGPT user |
| **Agent** | The AI. Understands the buyer's request, manages session state, orchestrates merchant + PSP calls. | `indus/` (Sarvam-M) | ChatGPT |
| **Merchant** | Implements the 5 ACP checkout endpoints. Stays merchant of record. Never sees raw buyer PII. | `merchant/` | Any online store |
| **PSP** | Issues payment orders, processes UPI/card charges, settles via Route. | Razorpay | Stripe |

The agent (Indus / Sarvam-M) is the single orchestrator. It never opens a browser or fills a form. The merchant never handles raw card data. The PSP (Razorpay) never knows about the checkout session — it just creates an order, accepts the charge, and routes settlement to the merchant's UPI VPA.

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
 Merchant               Razorpay
 /product_feed          POST /v1/orders
 /checkout_sessions     POST /v1/payments/create/json
 /checkout_sessions/    GET  /v1/payments/{id}
   {id}/complete         (UPI collect / intent / QR /
    │                     card / NetBanking)
    ▼
 order.created webhook → buyer notified
 Razorpay Route → merchant VPA settled
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
        │                                   ↓  Razorpay webhook fires
        │                            completed           ← order created (terminal)
        │
        └─────────────────────────→ completed            ← order created (terminal)

any non-terminal state → canceled  (terminal)
session TTL elapsed    → expired   (terminal, surfaced on read)
```

**Terminal states**: `completed`, `canceled`, `expired`
**Blocking states**: `awaiting_payment`

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

## Payment flow — Razorpay

Razorpay replaces Stripe in the Indus Profile.

```
1. Indus → Razorpay:
     POST /v1/orders
     {
       amount: 94400,           ← paise (₹944.00)
       currency: "INR",
       receipt: "cs_abc",
       notes: { checkout_session_id: "cs_abc" }
     }

2. Razorpay → Indus:
     { id: "order_xyz", status: "created" }

3. Indus → Razorpay (UPI Collect):
     POST /v1/payments/create/json
     { amount, currency, order_id, method: "upi", vpa: "raj@upi", ... }

4. Razorpay → Indus:
     { razorpay_payment_id: "pay_abc", status: "created" }
     ← user approves collect request on their UPI app

5. Indus → Merchant:
     POST /checkout_sessions/cs_abc/complete
     { payment_data: { provider: "razorpay", token: "pay_abc" } }

6. Merchant:
     → redeems buyer_token + fulfillment_token from Indus
     → GET /v1/payments/pay_abc from Razorpay (verify status)
     → status "created" / "requires_customer_action" → set session to awaiting_payment

7. User approves payment in UPI app

8. Razorpay fires:
     POST /webhooks/razorpay  (on merchant)
     { event: "payment.captured", payload: { payment: { entity: { id: "pay_abc", ... } } } }

9. Merchant:
     → creates order
     → triggers Razorpay Route transfer to merchant UPI VPA
     → fires order.created webhook to buyer endpoint
```

---

## India-specific features

### UPI payment types

| Type | Use case |
|------|----------|
| `upi_collect` | Pull from VPA — user approves collect request (agentic, no redirect) |
| `upi_intent` | Deep-link to user's UPI app |
| `upi_qr` | Generate QR code for scanning |
| `upi_reserve_pay` | PIN-less SBMD mandate — user authorises once, agent debits repeatedly |

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
POST /indus/sarvam/product_search
{
  "query": "1000 rupee ke andar headphones chahiye",
  "language": "hi",
  "merchant_base_url": "http://merchant.example.com"
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
| Payment handler binding | `com.razorpay.upi_collect` handler specification | `rfc/payment-handlers.md` |
