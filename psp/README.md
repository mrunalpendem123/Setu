# ACP Delegated Payment PSP (Stub)

This is a minimal stub of the ACP delegated payment endpoint for PSPs.
It is **not production-ready** and does not handle PCI or real tokenization.

## Endpoints

- `POST /agentic_commerce/delegate_payment`
- `GET /agentic_commerce/delegate_payment/{token}` (internal)
- `POST /agentic_commerce/delegate_payment/{token}/redeem` (internal)

## Env Vars

- `ACP_API_KEYS` (comma-separated tokens)
- `ACP_API_VERSIONS` (comma-separated, default `2025-09-29`)
- `ACP_SIGNATURE_SECRET` (optional)
- `ACP_TIMESTAMP_TOLERANCE_SECONDS` (default 300)

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ACP_API_KEYS=demo_key
uvicorn app.main:app --reload --port 8002
```
