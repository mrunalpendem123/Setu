# Razorpay Integration Guide

Setu uses **Razorpay** as the sole PSP. Razorpay is the only PSP with live NPCI-endorsed agentic payments, full UPI Reserve Pay (PIN-less), and Razorpay Route for direct merchant VPA settlement.

---

## Auth

All Razorpay API calls use **HTTP Basic Auth**: `key_id:key_secret`.

```
Authorization: Basic base64(RAZORPAY_KEY_ID:RAZORPAY_KEY_SECRET)
```

Base URL: `https://api.razorpay.com/v1`

---

## Payment flows

### UPI Collect (primary agentic flow — no redirect)

```
1. POST /v1/orders
   { amount, currency: "INR", receipt: session_id, notes: { checkout_session_id } }
   → { id: "order_xxx" }

2. POST /v1/payments/create/json
   { amount, currency, order_id, method: "upi", vpa, contact, email }
   → { razorpay_payment_id: "pay_xxx" }

3. User approves collect request on their UPI app

4. Razorpay fires POST /webhooks/razorpay with event: "payment.captured"

5. Merchant triggers Route transfer → merchant VPA settled
```

### UPI Intent (deep link)

```
1. POST /v1/orders  (same as above)
2. Build deep link: upi://pay?pa=<merchant_vpa>&am=<amount>&tr=<order_id>&cu=INR
3. User taps link → opens UPI app → approves
4. Razorpay webhook: payment.captured
```

### UPI QR Code

```
1. POST /v1/orders
2. POST /v1/payments/qr-codes
   { type: "upi_qr", payment_amount, notes: { checkout_session_id } }
   → { id: "qr_xxx", image_url, short_url }
3. User scans → pays
4. Razorpay webhook: payment.captured
```

### UPI Reserve Pay (PIN-less mandate)

```
1. POST /v1/orders  { amount: max_amount }
2. POST /v1/payments/create/upi_mandate
   { order_id, customer_id, vpa, max_amount, type: "upi_mandate" }
→ User authorises once → agent can debit freely up to max_amount
```

### Card

Card payments use Razorpay.js on the frontend. The backend creates an order and passes `order_id` + `key_id` to the client.

---

## Webhook verification

```python
import hmac, hashlib

expected = hmac.new(
    RAZORPAY_WEBHOOK_SECRET.encode(),
    request_body,
    hashlib.sha256,
).hexdigest()

assert hmac.compare_digest(expected, request.headers["X-Razorpay-Signature"])
```

Configure in Razorpay Dashboard → Webhooks → set URL to `https://<merchant>/webhooks/razorpay`.

Active events: `payment.captured`, `payment.failed`.

---

## Route — merchant settlement

After `payment.captured`, trigger a transfer to the merchant's linked account:

```
POST /v1/payments/{payment_id}/transfers
{
  "transfers": [{
    "account": "acc_xxx",      ← merchant's Razorpay linked account ID
    "amount": 94400,           ← paise
    "currency": "INR"
  }]
}
```

Set `RAZORPAY_MERCHANT_ACCOUNT_ID=acc_xxx` to enable automatic Route transfers on every capture.

---

## Env vars

| Var | Notes |
|-----|-------|
| `RAZORPAY_KEY_ID` | `rzp_test_...` or `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | HMAC-SHA256 secret for inbound webhook verification |
| `RAZORPAY_ACCOUNT_ID` | Platform Route account ID |
| `RAZORPAY_MERCHANT_ACCOUNT_ID` | Merchant linked account for settlement (`acc_...`) |
