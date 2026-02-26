# Protocol Overview

ACP-India (Indus Profile) is a binding of OpenAI's Agentic Commerce Protocol for India.

---

## Roles

| Role | Description | Reference implementation |
|---|---|---|
| **Agent** | The AI that shops on behalf of the user | Indus (`indus/`) |
| **Merchant** | The seller and merchant of record | `merchant/` |
| **Payment Handler** | Executes the actual payment | Hyperswitch via `payments/` |

---

## Core objects

**Checkout session** — the cart. Owned by the merchant, orchestrated by the agent.

```
Status: not_ready_for_payment
           ↓  (fulfillment address + option provided)
        ready_for_payment
           ↓  (payment verified)
        completed
           ↓  (or at any point)
        canceled
```

**Payment intent** — a Hyperswitch payment. Created by Indus, verified by merchant.

**Order** — created by the merchant after payment is verified.

**Buyer token / Fulfillment token** — opaque tokens issued by Indus. The agent's PII never leaves Indus — merchants receive tokens and redeem them when needed.

---

## Protocol bindings

```
Agent → Merchant      checkout session lifecycle (create, update, complete, cancel)
Agent → Hyperswitch   payment intent creation and confirmation
Merchant → Agent      token redemption (buyer data, fulfillment address)
Merchant → Agent      webhook (order.created, order.updated)
```

---

## The 4 calls

```
POST /indus/checkout                          create session + issue tokens
POST /indus/checkout/{id}/update              update items / address / shipping option
POST /indus/checkout/{id}/payment_intent      create Hyperswitch payment
POST /indus/checkout/{id}/complete            verify payment + create order
```

---

## Extension points

The protocol is designed to be extended without breaking the core flow:

| Extension | RFC |
|---|---|
| Capability negotiation | `rfc/capability-negotiation.md` |
| Discounts and coupons | `rfc/discounts.md` |
| Merchant registry | `rfc/merchant-registry.md` |
| Agent discovery | `rfc/agent-discovery.md` |
| Payment handler binding | `rfc/payment-handlers.md` |
| India GST / tax fields | `docs/india-profile.md` |
