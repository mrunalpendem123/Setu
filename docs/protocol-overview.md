# Protocol Overview

ACP-India (Indus Profile) is India's payment handler binding for the Agentic Commerce Protocol.

---

## Roles (from base ACP)

| Role | What they do | In this repo |
|---|---|---|
| **Buyer** | The human. Approves purchases through the agent's UI | — |
| **Agent** | The AI. Calls merchant APIs, manages session state, renders checkout UI | `indus/` |
| **Merchant** | Implements the 5 ACP endpoints. Stays merchant of record. | `merchant/` |
| **Payment Handler** | Issues scoped one-time tokens. Processes the actual charge. | Hyperswitch via `payments/` |

The agent never navigates a website. The merchant never handles raw card data. The payment handler never knows about the session — it just issues a token with allowance constraints.

---

## Session states

```
not_ready_for_payment     ← created; fulfillment option not yet selected
        ↓  update with fulfillment_option_id
ready_for_payment         ← all required fields present
        ↓  complete with payment token
        │
        ├─ approval_required=true ──→ pending_approval    ← awaiting merchant review
        │                                    ↓  merchant approves (webhook/poll)
        │                             ready_for_payment
        │
        ├─ 3DS needed ──────────────→ authentication_required  ← agent collects 3DS result
        │                                    ↓  re-submit with authentication_result
        │                             ready_for_payment
        │
        └─────────────────────────→ completed             ← order created (terminal)

any non-terminal state → cancel → canceled  (terminal)
session TTL elapsed    → expired             (terminal, surfaced on read)
```

**Terminal states**: `completed`, `canceled`, `expired` — no further transitions allowed.
**Blocking states**: `pending_approval`, `authentication_required` — session stays open, agent waits or re-submits.

---

## The 5 ACP endpoints (what every merchant must implement)

```
POST   /checkout_sessions           create session
GET    /checkout_sessions/{id}      retrieve session
POST   /checkout_sessions/{id}      update session (shipping, items, coupons)
POST   /checkout_sessions/{id}/complete   pay + create order
POST   /checkout_sessions/{id}/cancel     cancel session
```

---

## Delegated payment — how the token works

ACP's security model: the agent never passes raw card data to the merchant.

```
1. Agent → PSP:  POST /agentic_commerce/delegate_payment
                 {
                   payment_method,
                   allowance: {
                     reason: "one_time",
                     max_amount: 158182,
                     currency: "inr",
                     checkout_session_id: "cs_abc",
                     merchant_id: "merchant_xyz",
                     expires_at: "..."
                   },
                   risk_signals: [{ type: "card_testing", score: 0, action: "authorized" }],
                   metadata: {}
                 }

2. PSP → Agent:  { id: "vt_xyz", status: "issued" }   ← a scoped token

3. Agent → Merchant: POST /checkout_sessions/{id}/complete
                     { payment_handler_id: "hyperswitch.upi", payment_token: "dpt_xyz" }

4. Merchant → PSP:   charge using dpt_xyz internally

Token constraints enforced by PSP:
  - max_amount: cannot charge more than allowed
  - reason "one_time": cannot be reused
  - checkout_session_id: token is bound to a specific session
  - merchant_id: token is bound to a specific merchant
  - expires_at: invalid after expiry
```

In base ACP, the PSP is **Stripe** (Shared Payment Tokens).
In the Indus Profile, the PSP is **Hyperswitch**.

---

## What the Indus Profile adds

- `payment_handler_id: "hyperswitch.upi"` — UPI as a first-class payment method
- UPI sub-types: `upi_collect`, `upi_intent`, `upi_qr`
- `requires_customer_action` as a valid pending state (user approving on phone)
- Indian address validation (PIN code, country=IN, +91 phone)
- GST metadata on line items (HSN codes, GSTIN, tax rate)
- Sarvam AI endpoints for multilingual checkout assist
- Merchant registry (`/indus/merchants`)
- Capability negotiation endpoint (`/indus/capabilities`)

---

## Extension points

| Extension | RFC |
|---|---|
| Capability negotiation | `rfc/capability-negotiation.md` |
| Discounts and coupons | `rfc/discounts.md` |
| Merchant registry | `rfc/merchant-registry.md` |
| Agent discovery | `rfc/agent-discovery.md` |
| Payment handler binding | `rfc/payment-handlers.md` |
