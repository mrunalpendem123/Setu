# Agent Discovery

## Summary

Define how merchants can advertise their endpoints and how agents discover supported protocol versions.

## Goals

- Version negotiation
- Capability discovery
- Backward-compatible upgrades

## Proposed Mechanism

- Well-known document: `/.well-known/agentic-commerce.json`
- Declares protocol version, endpoints, and supported extensions

## Security

- Signed metadata SHOULD be supported for high-trust discovery.
- Agents SHOULD verify signatures where provided.
