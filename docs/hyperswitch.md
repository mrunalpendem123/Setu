# Hyperswitch Payment Experience Alignment

This repository follows Hyperswitch's recommended payment experience flow:

## Server-Side Flow

1. Create a Payment (`POST /payments`) from the server.
2. Return `client_secret` to the client.
3. Use `payments/update` if you need to reuse the same customer session for Express Checkout.

The `client_secret` is passed to the SDK/HyperLoader to render the UI. Never expose your API key to the client.

## Client-Side Flow (Unified / Express Checkout)

- Unified Checkout and Express Checkout both initialize the UI using the `client_secret` returned by the server.
- The client mounts the checkout element (HyperLoader) and completes the payment.
- After redirect, the client can retrieve the payment status using the `payment_intent_client_secret`.

## How this repo maps to the flow

- `POST /indus/checkout/{id}/payment_intent` creates the payment and returns `client_secret`.
- The client uses that `client_secret` to render Unified Checkout or Express Checkout.
- `POST /indus/payments/{id}` can be used for Express Checkout reuse, matching Hyperswitch's guidance.

References:
- Hyperswitch server setup and payment experience docs.
