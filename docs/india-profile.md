# ACP-India Profile

This document defines the India profile of the Agentic Commerce Protocol (ACP).
It keeps ACP semantics intact and only binds India-specific requirements and payment execution.

## Payment Handler Binding

- Payment execution MUST use Hyperswitch.
- The payment handler MUST support UPI and cards.
- The agent MUST create a payment intent and obtain a `client_secret` for client-side UX.
- Merchants MUST verify the payment status and amount before order creation.

## Address & Contact

- Postal code MUST be a valid Indian PIN code format.
- `country` MUST be `IN`.
- `state` SHOULD be an ISO-3166-2 IN state code.
- Phone numbers SHOULD be E.164 formatted.

## Tax and Compliance Hooks

- Merchants SHOULD include GST metadata when applicable.
- The protocol SHOULD allow India-specific invoices and tax fields via extensions.

## Scope

- This profile does not change the ACP state model.
- It does not change the ACP checkout or order lifecycle.
- It only binds the payment handler to Hyperswitch and adds India-specific address constraints.
