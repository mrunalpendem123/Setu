# RFC: Payment Handlers

Defines how payment providers are integrated and how payment tokens are exchanged.

Current implementation uses **Razorpay** directly via `indus/app/razorpay_client.py`.

---

## Handler IDs

| ID | Method | Notes |
|----|--------|-------|
| `com.razorpay.upi_collect` | UPI Collect (server-to-server, no redirect) | Primary agentic payment path |
| `com.razorpay.upi_intent` | UPI Intent (deep link) | Mobile app / web |
| `com.razorpay.upi_qr` | UPI QR Code | Desktop / kiosk |
| `com.razorpay.card` | Card (via Razorpay.js) | Client-side tokenization |

## Token exchange

```
Indus → POST /indus/checkout/{id}/payment_intent
  body: { amount, currency, payment_method_type, upi_data: { vpa } }
  → { payment_id: "pay_xxx", razorpay_order_id: "order_xxx", status }

Indus → POST /checkout_sessions/{id}/complete
  body: { payment_data: { provider: "razorpay", token: "pay_xxx" } }

Merchant → GET /v1/payments/pay_xxx  (Razorpay)
  → verify amount, currency, status
```
