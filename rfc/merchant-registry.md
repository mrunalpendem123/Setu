# Merchant Registry

## Summary

Define a registry service that allows agents to discover merchants and their capabilities.

## Goals

- Enable multi-merchant discovery
- Publish merchant metadata and capabilities
- Provide a stable lookup by merchant id

## Non-Goals

- Payment processing
- Fulfillment execution

## Proposed Objects

- Merchant record: id, name, base_url, country, categories
- Capabilities: payment methods, fulfillment types, features

## Endpoints (Sketch)

- `GET /registry/merchants` (search / filter)
- `GET /registry/merchants/{merchant_id}` (details)

## Security

- Registry MAY be public or authenticated.
- Agents SHOULD cache registry results.
