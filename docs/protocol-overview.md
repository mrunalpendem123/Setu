# Protocol Overview

The Indus Commerce Protocol (ACP‑India) defines a standard, agent‑centric checkout flow for India.
It mirrors ACP semantics and uses Hyperswitch as the payment handler.

## Roles

- Agent: the user-facing AI app (Indus)
- Merchant: seller and merchant of record (MoR)
- Payment Handler: Hyperswitch (UPI + cards)

## Core Objects

- Checkout session (state machine)
- Payment intent / payment token
- Order
- Buyer + fulfillment tokens

## State Model

`not_ready_for_payment -> ready_for_payment -> completed (or canceled)`

## Tokenization

- Buyer and fulfillment data are owned by the agent.
- Merchants only receive tokens and redeem them when needed.

## Extensions

- Capability negotiation
- Payment handlers
- Discounts and promotions
- India-specific compliance fields
