# Sarvam Shopping Playground

A mobile-style AI shopping demo with real Sarvam AI chat and end-to-end checkout flow.

## Run

```bash
cd demo
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn httpx pydantic
.venv/bin/python3 server.py
```

Open: **http://localhost:3000**

## Features

- 🪷 Sarvam-inspired mobile UI (mandala logo, orange theme)
- 🤖 Real Sarvam AI chat (model: sarvam-m)
- 🛍️ 8 Indian products: kurtas, sarees, jewelry, electronics, yoga, spices
- 📦 Product detail sheet (slide-up drawer)
- 💳 Checkout with UPI / Card / Net Banking
- ✅ Order confirmation screen with order ID
- 📱 Phone frame UI (393×852px)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/` | Mobile app HTML |
| GET  | `/api/products` | Product catalog |
| POST | `/api/chat` | Sarvam AI chat |
| POST | `/api/checkout` | Place order |
