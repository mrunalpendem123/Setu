# PSP Stub — Delegated Payment Endpoint

This is a minimal stub of the ACP delegated payment endpoint. In the Setu protocol the real PSP is **Hyperswitch** — this stub exists for testing the `vt_*` / `dpt_*` pre-authorized token flow without needing a live Hyperswitch account.

> **Not production-ready.** Does not perform real tokenization or PCI-scoped storage.

---

## What this does

In the delegated payment flow, Indus (the agent) obtains a scoped one-time payment token from the PSP *before* calling the merchant. The merchant redeems the token to charge the buyer — it never sees raw card data.

```
Indus → POST /agentic_commerce/delegate_payment
          { payment_method, allowance: { max_amount, currency, merchant_id, ... } }

PSP  → { id: "vt_xyz", status: "issued" }   ← scoped token

Indus → POST /checkout_sessions/{id}/complete
          { payment_data: { provider: "psp", token: "vt_xyz" } }

Merchant → POST /agentic_commerce/delegate_payment/vt_xyz/redeem
             ← PSP enforces max_amount, one-time use, merchant binding
```

In production deployments, replace this stub with real Hyperswitch delegated payment endpoints.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agentic_commerce/delegate_payment` | Issue a scoped payment token |
| `GET`  | `/agentic_commerce/delegate_payment/{token}` | Inspect token (internal) |
| `POST` | `/agentic_commerce/delegate_payment/{token}/redeem` | Redeem token to charge (internal) |
| `GET`  | `/health` | Health check |

---

## Token constraints enforced

- `max_amount` — merchant cannot charge more than the allowed amount
- `reason: "one_time"` — token is single-use; reuse returns 409
- `checkout_session_id` — token is bound to a specific checkout session
- `merchant_id` — token is bound to a specific merchant
- `expires_at` — token is invalid after expiry

---

## Env Vars

| Var | Default | Notes |
|-----|---------|-------|
| `ACP_API_KEYS` | — | Comma-separated API keys (Indus uses one of these) |
| `ACP_API_VERSIONS` | `2025-09-29` | Accepted `ACP-Version` header values |
| `ACP_SIGNATURE_SECRET` | optional | HMAC request signing |
| `ACP_TIMESTAMP_TOLERANCE_SECONDS` | `300` | Clock skew tolerance for signed requests |

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ACP_API_KEYS=demo_key

uvicorn app.main:app --reload --port 8002
```
