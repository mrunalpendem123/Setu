# ACP-India Profile (Indus)

This document defines the **India payment handler binding** of the Agentic Commerce Protocol.

It does not change the ACP state model, checkout lifecycle, or order semantics.
It only specifies what is **required or different** when ACP runs in India — primarily
replacing **Stripe** as the default payment handler with **Hyperswitch**.

---

## 1. Payment Handler

- MUST use **Hyperswitch** as the payment handler.
- Hyperswitch MUST be configured with at least one UPI connector (PhonePe, Paytm, Razorpay, etc.) and one card connector.
- The payment handler binding replaces Stripe in base ACP.

### UPI payment methods

Hyperswitch exposes three UPI flows. The agent picks the right one based on context:

| `payment_method_type` | Flow | When to use |
|---|---|---|
| `upi_collect` | Agent sends VPA, user approves on their app | Agent knows the user's VPA |
| `upi_intent` | Deep-links to user's UPI app | Mobile web / app |
| `upi_qr` | Display a QR code | Desktop / TV / kiosk |

All three return `status: requires_customer_action` immediately.
This is **not a failure** — it means the user is approving on their phone.
The protocol accepts `requires_customer_action` as a valid pending state.

---

## 2. Address Format

All fulfillment addresses MUST conform to Indian postal standards:

| Field | Constraint |
|---|---|
| `country` | MUST be `"IN"` |
| `postal_code` | MUST match `^[1-9][0-9]{5}$` (6-digit Indian PIN code, no leading zero) |
| `phone_number` | MUST match `^\+91[6-9]\d{9}$` (E.164, Indian mobile) |
| `state` | SHOULD be an ISO 3166-2 IN state code (e.g. `KA`, `MH`, `DL`) |

---

## 3. Currency

- All amounts are in **INR**, expressed in **paise** (smallest unit).
- `currency` field MUST be `"inr"`.
- Example: ₹1532.82 = `153282` paise.

---

## 4. Tax — GST

Merchants SHOULD attach GST metadata to line items when applicable.

```jsonc
{
  "gst_metadata": {
    "gstin": "29ABCDE1234F1Z5",   // buyer GSTIN for B2B invoices (optional)
    "hsn_code": "85183000",        // HSN code for the product
    "tax_label": "GST",
    "tax_rate_pct": 18.0
  }
}
```

Standard GST rates in India: 0%, 5%, 12%, 18%, 28%.

---

## 5. Agent Layer — Sarvam AI

The reference agent is powered by **Sarvam AI**, which provides:
- Indian language support (Hindi, Tamil, Telugu, Kannada, Bengali, ...)
- NLU for product search in regional languages
- Checkout assist via natural language

The Indus orchestrator exposes Sarvam endpoints:
- `POST /indus/sarvam/product_search` — multilingual product search
- `POST /indus/sarvam/checkout_assist` — NL interface for checkout steps

These are **optional extensions**. The core checkout flow does not require Sarvam.

---

## 6. What does NOT change from base ACP

- Checkout session state machine: `not_ready_for_payment → ready_for_payment → completed / canceled`
- Token lifecycle: buyer and fulfillment tokens issued by agent, redeemed by merchant
- Order model: merchant creates order on payment verification
- Capability negotiation semantics
- Idempotency model (`Idempotency-Key` header)
- Webhook event shape (`order.created`, `order.updated`)
