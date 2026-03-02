# ACP-India Profile (Indus)

This document defines the **India payment handler binding** of the Agentic Commerce Protocol.

It does not change the ACP state model, checkout lifecycle, or order semantics.
It only specifies what is **required or different** when ACP runs in India — primarily
replacing **Stripe** as the default payment handler with **Razorpay**.

---

## 1. Payment Handler

- MUST use **Razorpay** as the payment handler.
- Razorpay is the only PSP with live NPCI-endorsed agentic payments, UPI Reserve Pay (PIN-less), and Razorpay Route for direct merchant VPA settlement.
- The payment handler binding replaces Stripe in base ACP.

### UPI payment methods

Razorpay exposes four UPI flows. The agent picks the right one based on context:

| `payment_method_type` | Flow | When to use |
|---|---|---|
| `upi_collect` | Agent sends VPA, user approves collect request | Agent knows the user's VPA — primary agentic path |
| `upi_intent` | Deep-links to user's UPI app | Mobile web / app |
| `upi_qr` | Display a QR code | Desktop / TV / kiosk |
| `upi_reserve_pay` | PIN-less SBMD mandate | Recurring / subscription-style agentic payments |

UPI Collect returns `status: pending_customer_action` immediately.
This is **not a failure** — it means the user is approving on their phone.
The protocol accepts `pending_customer_action` as a valid pending state.

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
- Example: ₹944.00 = `94400` paise.

---

## 4. Tax — GST

Merchants SHOULD attach GST metadata to line items when applicable.

```jsonc
{
  "gst_metadata": {
    "gstin": "29ABCDE1234F1Z5",   // buyer GSTIN for B2B invoices (optional)
    "hsn_code": "85183000",        // HSN code for the product
    "tax_label": "GST",
    "tax_rate_pct": 18.0           // 0 / 5 / 12 / 18 / 28
  }
}
```

Standard GST rates in India: 0%, 5%, 12%, 18%, 28%.
Cotton apparel under ₹1,000 → 5%. Electronics → 18%.

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
