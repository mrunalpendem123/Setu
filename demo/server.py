#!/usr/bin/env python3
"""
Sarvam Shopping Playground
===========================
Run:
    cd demo && .venv/bin/python3 server.py
Open: http://localhost:3000
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
SARVAM_API_KEY   = "sk_1tuhccqv_6atJF411oSRkt7wZYlmUopLN"
SARVAM_BASE_URL  = "https://api.sarvam.ai"
SARVAM_MODEL     = "sarvam-m"

# ── Hyperswitch / Fauxpay ─────────────────────────────────────────────────────
HYPERSWITCH_API_KEY  = "mrunal"
HYPERSWITCH_BASE_URL = "https://sandbox.hyperswitch.io"
HYPERSWITCH_PROFILE_ID = "pro_W7dpZJT1cqlty6Ud7e1u"

# ── Product Catalog ───────────────────────────────────────────────────────────
CATALOG: Dict[str, Dict[str, Any]] = {
    "item_001": {
        "id": "item_001", "title": "Banarasi Silk Kurta",
        "description": "Handwoven Banarasi silk kurta with intricate zari embroidery. Perfect for Diwali and festive occasions. Available in sizes S–XXL.",
        "price": 349900, "original_price": 499900, "category": "clothing",
        "image_url": "https://images.unsplash.com/photo-1594938298603-c8148c4b5946?w=600&q=80",
        "rating": 4.7, "reviews": 1243, "merchant": "Ajio",
        "tags": ["kurta", "silk", "festive", "traditional", "clothing", "diwali", "banarasi"],
        "in_stock": True, "hsn_code": "62052000",
    },
    "item_002": {
        "id": "item_002", "title": "Noise Cancelling Headphones",
        "description": "Premium over-ear headphones with 40-hour battery, active noise cancellation, and Hi-Res Audio certification. Foldable design.",
        "price": 129900, "original_price": 189900, "category": "electronics",
        "image_url": "https://images.unsplash.com/photo-1546435770-a3e736e19f91?w=600&q=80",
        "rating": 4.5, "reviews": 892, "merchant": "Amazon",
        "tags": ["headphones", "audio", "music", "electronics", "earphones", "noise", "gadget"],
        "in_stock": True, "hsn_code": "85183000",
    },
    "item_003": {
        "id": "item_003", "title": "Premium Carry-On Suitcase",
        "description": "Lightweight 20\" carry-on suitcase with TSA lock, 360° spinner wheels, and USB charging port. Fits most overhead compartments.",
        "price": 899900, "original_price": 1299900, "category": "travel",
        "image_url": "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=600&q=80",
        "rating": 4.6, "reviews": 567, "merchant": "Flipkart",
        "tags": ["suitcase", "luggage", "travel", "bag", "carry-on", "trip", "journey"],
        "in_stock": True, "hsn_code": "42021200",
    },
    "item_004": {
        "id": "item_004", "title": "Kanjivaram Silk Saree",
        "description": "Pure Kanjivaram silk saree with traditional zari border in gold and crimson. Authentic Tamil Nadu weave. Comes with blouse piece.",
        "price": 1499900, "original_price": 1999900, "category": "clothing",
        "image_url": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&q=80",
        "rating": 4.9, "reviews": 2341, "merchant": "Myntra",
        "tags": ["saree", "silk", "kanjivaram", "traditional", "festive", "clothing", "diwali"],
        "in_stock": True, "hsn_code": "62046990",
    },
    "item_005": {
        "id": "item_005", "title": "Gold-Plated Jhumka Earrings",
        "description": "Handcrafted gold-plated jhumka earrings with ruby and emerald stones. Made by Rajasthani artisans. Hypoallergenic hooks.",
        "price": 249900, "original_price": 349900, "category": "jewelry",
        "image_url": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80",
        "rating": 4.8, "reviews": 1567, "merchant": "Meesho",
        "tags": ["jewelry", "earrings", "gold", "jhumka", "accessories", "gift", "traditional"],
        "in_stock": True, "hsn_code": "71179090",
    },
    "item_006": {
        "id": "item_006", "title": "Eco Yoga & Meditation Mat",
        "description": "6mm thick eco-friendly yoga mat made from natural rubber. Non-slip surface, alignment lines, includes carry strap.",
        "price": 199900, "original_price": 249900, "category": "wellness",
        "image_url": "https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=600&q=80",
        "rating": 4.4, "reviews": 3421, "merchant": "Tata CLiQ",
        "tags": ["yoga", "mat", "fitness", "wellness", "meditation", "exercise", "health"],
        "in_stock": True, "hsn_code": "39269099",
    },
    "item_007": {
        "id": "item_007", "title": "Artisan Spice Gift Box",
        "description": "Curated set of 12 premium Indian spices from Kerala farms — cardamom, pepper, turmeric, and more. Beautiful gift packaging.",
        "price": 149900, "original_price": 199900, "category": "food",
        "image_url": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&q=80",
        "rating": 4.7, "reviews": 892, "merchant": "BigBasket",
        "tags": ["spices", "food", "gift", "kerala", "cooking", "masala", "gourmet"],
        "in_stock": True, "hsn_code": "09109990",
    },
    "item_008": {
        "id": "item_008", "title": "AMOLED Smartwatch Pro",
        "description": "1.43\" AMOLED always-on display, 7-day battery, SpO2 & heart rate monitoring, 100+ sports modes, IP68 water resistant.",
        "price": 2499900, "original_price": 3499900, "category": "electronics",
        "image_url": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=600&q=80",
        "rating": 4.6, "reviews": 4521, "merchant": "Croma",
        "tags": ["watch", "smartwatch", "wearable", "electronics", "fitness", "gadget", "tech"],
        "in_stock": True, "hsn_code": "91029900",
    },
}

SYSTEM_PROMPT = """You are Sarvam, a warm and clever Indian AI assistant — like a knowledgeable friend who loves shopping AND can chat about anything.

IMPORTANT: Always respond ONLY with valid JSON in this exact format:
{
  "message": "your friendly response (1-3 sentences)",
  "search_query": "product keywords to search, or null",
  "intent": "shopping" | "greeting" | "general"
}

Rules:
- Be warm, smart, and conversational — like a helpful desi friend.
- Shopping / products / gifts / recommendations → intent "shopping" + search_query keywords
- Name meanings, fun facts, jokes, language, general questions → intent "general", search_query null
- Greetings → intent "greeting", search_query null
- For name meanings: give the actual Sanskrit/Hindi meaning with warmth
- For facts about India, culture, language, history → answer accurately and enthusiastically
- Keep answers concise but genuinely helpful (not one-word)
- Never mention JSON in your message"""


def search_products(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    if not query:
        return list(CATALOG.values())[:max_results]
    q = query.lower()
    qw = set(w for w in re.split(r'\W+', q) if len(w) > 2)
    scored = []
    for item in CATALOG.values():
        s = 0
        for tag in item.get("tags", []):
            if tag in q: s += 4
        s += len(set(item["title"].lower().split()) & qw) * 3
        if item["category"] in q: s += 3
        s += len(set(w for w in item["description"].lower().split() if len(w) > 4) & qw)
        if s > 0: scored.append((s, item))
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:max_results]]


# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Sarvam Shopping Playground")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class CheckoutRequest(BaseModel):
    item_id: str
    quantity: int = 1
    buyer_name: str
    buyer_phone: str
    address: str
    city: str
    state: str
    pincode: str
    payment_method: str = "upi"
    card_number: Optional[str] = None
    card_exp_month: Optional[str] = None
    card_exp_year: Optional[str] = None
    card_cvv: Optional[str] = None
    upi_vpa: Optional[str] = None  # e.g. "raj@upi"

# In-memory store for simulated async payments
import time as _time
_pending: Dict[str, Dict] = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML)

@app.get("/api/products")
async def get_products():
    return list(CATALOG.values())

@app.get("/api/products/{item_id}")
async def get_product(item_id: str):
    if item_id not in CATALOG:
        raise HTTPException(status_code=404, detail="Product not found")
    return CATALOG[item_id]

@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SARVAM_BASE_URL}/v1/chat/completions",
                headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                json={"model": SARVAM_MODEL, "messages": messages, "max_tokens": 400, "temperature": 0.7},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Sarvam API {resp.status_code}: {resp.text}")
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        try:
            m = re.search(r'\{[\s\S]*\}', raw)
            parsed = json.loads(m.group()) if m else {}
        except Exception:
            parsed = {}
        message      = parsed.get("message") or raw
        search_query = parsed.get("search_query")
        intent       = parsed.get("intent", "general")
        last = req.messages[-1].content.lower() if req.messages else ""
        kws  = {"buy","find","show","looking","want","need","gift","recommend","suggest","best",
                "cheap","under","saree","kurta","headphone","watch","yoga","spice","suitcase","travel"}
        if intent != "shopping" and any(k in last for k in kws):
            intent = "shopping"; search_query = search_query or last
        products = search_products(search_query or last) if intent == "shopping" else []
        return {"message": message, "products": products, "intent": intent}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Sarvam API timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/checkout")
async def checkout(req: CheckoutRequest):
    import hashlib
    if req.item_id not in CATALOG:
        raise HTTPException(status_code=404, detail="Product not found")
    item     = CATALOG[req.item_id]
    subtotal = item["price"] * req.quantity
    gst      = int(subtotal * 0.18)
    total    = subtotal + gst
    parts    = req.buyer_name.strip().split()
    billing  = {
        "address": {"line1": req.address, "city": req.city, "state": req.state,
                    "zip": req.pincode, "country": "IN",
                    "first_name": parts[0], "last_name": " ".join(parts[1:])},
        "phone": {"number": req.buyer_phone.replace("+91", ""), "country_code": "+91"},
    }
    order_id   = f"ORD-{uuid4().hex[:8].upper()}"
    payment_id: Optional[str] = None
    payment_status = "simulated"

    # ── CARD ─────────────────────────────────────────────────────────────────
    if req.payment_method == "card" and req.card_number:
        exp_year = req.card_exp_year or ""
        if len(exp_year) == 2: exp_year = "20" + exp_year
        hs_payload = {
            "amount": total, "currency": "INR", "confirm": True,
            "capture_method": "automatic", "payment_method": "card",
            "payment_method_data": {"card": {
                "card_number": (req.card_number or "").replace(" ", ""),
                "card_exp_month": req.card_exp_month, "card_exp_year": exp_year,
                "card_holder_name": req.buyer_name, "card_cvc": req.card_cvv,
            }},
            "billing": billing,
            "profile_id": HYPERSWITCH_PROFILE_ID,
            "metadata": {"order_source": "sarvam_playground"},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                hs = await client.post(
                    f"{HYPERSWITCH_BASE_URL}/payments",
                    headers={"api-key": HYPERSWITCH_API_KEY, "Content-Type": "application/json"},
                    json=hs_payload,
                )
            hd = hs.json()
            if hs.status_code in (401, 403) or (hd.get("error") or {}).get("code") in ("IR_01","IR_02","HE_01"):
                raise ValueError("auth_error")
            payment_id     = hd.get("payment_id")
            payment_status = hd.get("status", "unknown")
            if payment_status not in {"succeeded","processing","requires_capture","partially_captured"}:
                raise HTTPException(status_code=402, detail=f"Payment declined: {(hd.get('error') or {}).get('message') or payment_status}")
        except HTTPException:
            raise
        except Exception:
            seed = f"{req.item_id}{req.buyer_name}{_time.time()}"
            payment_id     = "pay_" + hashlib.sha256(seed.encode()).hexdigest()[:20]
            payment_status = "succeeded"

    # ── UPI ──────────────────────────────────────────────────────────────────
    elif req.payment_method == "upi":
        vpa = (req.upi_vpa or "").strip()
        ptype = "upi_collect" if vpa else "upi_intent"
        hs_payload: Dict[str, Any] = {
            "amount": total, "currency": "INR", "confirm": True,
            "capture_method": "automatic", "payment_method": "upi",
            "payment_method_type": ptype,
            "billing": billing,
            "profile_id": HYPERSWITCH_PROFILE_ID,
            "metadata": {"order_source": "sarvam_playground"},
        }
        if vpa:
            hs_payload["payment_method_data"] = {"upi": {"vpa_id": vpa}}
        real_hs = False
        hd: Dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                hs = await client.post(
                    f"{HYPERSWITCH_BASE_URL}/payments",
                    headers={"api-key": HYPERSWITCH_API_KEY, "Content-Type": "application/json"},
                    json=hs_payload,
                )
            hd = hs.json()
            err_code = (hd.get("error") or {}).get("code", "")
            if hs.status_code < 400 and err_code not in ("IR_01","IR_02","HE_01"):
                payment_id     = hd.get("payment_id")
                payment_status = hd.get("status", "requires_customer_action")
                real_hs = True
        except Exception:
            pass

        if not real_hs:
            # Sandbox / demo fallback — simulate async UPI
            seed = f"upi{req.item_id}{req.buyer_name}{_time.time()}"
            payment_id = "pay_" + hashlib.sha256(seed.encode()).hexdigest()[:20]
            payment_status = "requires_customer_action"

        # Track in-memory so the poll endpoint can auto-resolve after 6s
        _pending[payment_id] = {
            "status": payment_status,
            "resolve_at": _time.time() + 6,
            "next_action": hd.get("next_action"),
        }
        return {
            "order_id": order_id, "payment_id": payment_id,
            "payment_status": payment_status,
            "status": "pending_upi",
            "upi_vpa": vpa or None,
            "next_action": hd.get("next_action"),
            "item": item, "quantity": req.quantity,
            "subtotal": subtotal, "gst": gst, "total": total,
            "buyer_name": req.buyer_name, "payment_method": "upi",
            "estimated_delivery": "3–5 business days",
        }

    # ── NET BANKING ───────────────────────────────────────────────────────────
    elif req.payment_method == "netbanking":
        seed = f"nb{req.item_id}{req.buyer_name}{_time.time()}"
        payment_id = "pay_" + hashlib.sha256(seed.encode()).hexdigest()[:20]
        payment_status = "requires_customer_action"
        _pending[payment_id] = {"status": payment_status, "resolve_at": _time.time() + 8, "next_action": None}
        return {
            "order_id": order_id, "payment_id": payment_id,
            "payment_status": payment_status, "status": "pending_netbanking",
            "item": item, "quantity": req.quantity,
            "subtotal": subtotal, "gst": gst, "total": total,
            "buyer_name": req.buyer_name, "payment_method": "netbanking",
            "estimated_delivery": "3–5 business days",
        }

    return {
        "order_id": order_id, "payment_id": payment_id, "payment_status": payment_status,
        "status": "confirmed", "item": item, "quantity": req.quantity,
        "subtotal": subtotal, "gst": gst, "total": total,
        "buyer_name": req.buyer_name, "payment_method": req.payment_method,
        "estimated_delivery": "3–5 business days",
    }


@app.get("/api/payment/{payment_id}")
async def get_payment_status(payment_id: str):
    """Poll Hyperswitch (or in-memory store for simulated) for payment status."""
    # First try in-memory (simulated/pending payments)
    if payment_id in _pending:
        p = _pending[payment_id]
        if _time.time() >= p["resolve_at"]:
            p["status"] = "succeeded"
        return {"payment_id": payment_id, "status": p["status"], "next_action": p.get("next_action")}
    # Try real Hyperswitch
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{HYPERSWITCH_BASE_URL}/payments/{payment_id}",
                headers={"api-key": HYPERSWITCH_API_KEY},
            )
        data = resp.json()
        return {"payment_id": payment_id, "status": data.get("status", "unknown"),
                "next_action": data.get("next_action")}
    except Exception:
        return {"payment_id": payment_id, "status": "unknown", "next_action": None}


# ── Frontend ──────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Sarvam</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --or:#FF6B35;--ord:#E85520;--ol:#FFF0E8;
  --ubg:#F5E4CE;--utx:#7B3B1A;
  --navy:#1B2963;
  --gr:#22C55E;
  --bd:#EFEFEF;--mt:#9A9A9A;
  --r:14px;--rs:10px;
}
html,body{height:100%;background:#D8D8D8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center}

/* ── Phone frame ── */
#phone{
  width:393px;height:852px;
  background:#0A0A0A;
  border-radius:52px;
  box-shadow:0 40px 90px rgba(0,0,0,.65),inset 0 0 0 1px #2A2A2A;
  overflow:hidden;position:relative;flex-shrink:0;
}
#phone::before{/* Dynamic Island */
  content:'';position:absolute;top:11px;left:50%;transform:translateX(-50%);
  width:120px;height:36px;background:#0A0A0A;border-radius:20px;z-index:999;
}
#sw{position:absolute;inset:0;border-radius:50px;overflow:hidden;background:#fff}

/* ── Screens ── */
.screen{
  position:absolute;inset:0;display:flex;flex-direction:column;background:#fff;
  transition:transform .3s cubic-bezier(.4,0,.2,1),opacity .3s;will-change:transform;
}
.screen.hidden    {transform:translateX(100%);opacity:0;pointer-events:none}
.screen.slide-out {transform:translateX(-25%);opacity:0;pointer-events:none}

/* ── Status bar ── */
.sb{display:flex;align-items:center;justify-content:space-between;padding:54px 26px 4px;flex-shrink:0}
.sb-t{font-size:16px;font-weight:600;letter-spacing:-.3px;color:#111}
.sb-i{display:flex;align-items:center;gap:5px}

/* ════════════════ WELCOME ════════════════ */
.w-hdr{display:flex;align-items:center;gap:10px;padding:6px 22px 14px;flex-shrink:0}
.hmbg{font-size:22px;font-weight:300;color:#111;background:none;border:none;cursor:pointer;line-height:1;padding:0;letter-spacing:-1px}
.sw-word{font-size:26px;font-weight:800;color:#111;letter-spacing:-.8px}

.w-logo{padding:18px 22px 4px;flex-shrink:0}
.w-logo svg{width:80px;height:80px;display:block}

.w-greet{padding:12px 22px 28px;flex-shrink:0}
.w-sub{font-size:15px;color:#9A9A9A;font-weight:400;margin-bottom:5px}
.w-q{font-size:27px;font-weight:700;color:#111;line-height:1.25}

/* Prompt list — vertical full-width pills */
.plist{display:flex;flex-direction:column;gap:10px;padding:0 16px;flex:1;overflow-y:auto}
.plist::-webkit-scrollbar{display:none}
.pi{
  display:flex;align-items:center;gap:14px;
  padding:11px 16px;border-radius:100px;
  border:1.5px solid #EBEBEB;background:#fff;
  cursor:pointer;flex-shrink:0;text-align:left;
  transition:background .15s;
}
.pi:active{background:#FFF8F4}
.pt{width:42px;height:42px;border-radius:50%;object-fit:cover;flex-shrink:0;background:#EEE}
.pt-txt{font-size:15px;color:#222;font-weight:400;line-height:1.3}

/* Welcome input */
.w-inp-area{padding:12px 14px 38px;flex-shrink:0}
.w-inp-bar{display:flex;align-items:center;background:#F2F2F2;border-radius:50px;padding:6px 6px 6px 20px}
.w-inp-bar input{flex:1;border:none;background:transparent;font-size:16px;color:#444;outline:none}
.w-inp-bar input::placeholder{color:#AAAAAA}
.mic-btn{
  width:50px;height:50px;border-radius:50%;
  background:var(--navy);border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}

/* ════════════════ CHAT ════════════════ */
.c-hdr{
  display:flex;align-items:center;gap:10px;
  padding:4px 18px 12px;border-bottom:1px solid #F2F2F2;flex-shrink:0;
}
.c-title{flex:1;font-size:17px;font-weight:600;color:#111;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.c-edit{background:none;border:none;cursor:pointer;padding:2px}

.msgs{flex:1;overflow-y:auto;padding:20px 18px 8px;display:flex;flex-direction:column;gap:14px}
.msgs::-webkit-scrollbar{width:0}

.mrow{display:flex;animation:min .22s ease}
@keyframes min{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.mrow.u{justify-content:flex-end}

/* User bubble — warm beige */
.bub-u{
  max-width:78%;padding:12px 18px;
  background:var(--ubg);color:var(--utx);
  border-radius:22px;font-size:15px;line-height:1.5;font-weight:400;
}
/* AI text — no bubble, plain */
.bub-a{max-width:95%;font-size:15px;line-height:1.72;color:#1A1A1A}
.bub-a h2{font-size:18px;font-weight:700;margin:16px 0 6px;color:#111}
.bub-a h3{font-size:16px;font-weight:700;margin:12px 0 4px;color:#111}
.bub-a p{margin-bottom:10px}
.bub-a strong{font-weight:700}
.bub-a ul{padding-left:18px;margin-bottom:10px}
.bub-a li{margin-bottom:4px}

/* Thinking row */
.think{display:flex;align-items:center;gap:9px}
.think-icon{width:24px;height:24px;flex-shrink:0;animation:tspin 2.2s linear infinite}
@keyframes tspin{to{transform:rotate(360deg)}}
.think-lbl{font-size:15px;color:#9A9A9A}

/* Product grid in chat */
.pgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%}
.pcard{
  border-radius:var(--r);overflow:hidden;background:#fff;
  border:1px solid #EEE;cursor:pointer;
  box-shadow:0 2px 8px rgba(0,0,0,.06);transition:transform .13s;
}
.pcard:active{transform:scale(.97)}
.pcard img{width:100%;aspect-ratio:1;object-fit:cover;display:block}
.pcb{padding:9px 10px}
.pct{font-size:12px;font-weight:600;color:#222;line-height:1.3;
     display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:5px}
.pcp{font-size:13px;font-weight:700;color:var(--or)}
.pco{font-size:11px;color:var(--mt);text-decoration:line-through;margin-left:3px}
.pcr{font-size:11px;color:var(--mt);margin-top:3px}
.pcm{display:flex;align-items:center;gap:4px;margin-top:5px;font-size:10px;color:#888;font-weight:500}
.pcm-dot{width:5px;height:5px;border-radius:50%;background:#D0D0D0;flex-shrink:0}

/* Chat input */
.c-inp-area{border-top:1px solid #F2F2F2;padding:10px 14px 34px;flex-shrink:0;background:#fff}
.c-inp-bar{display:flex;align-items:center;background:#F2F2F2;border-radius:50px;padding:6px 6px 6px 20px}
.c-inp-bar input{flex:1;border:none;background:transparent;font-size:16px;color:#222;outline:none}
.c-inp-bar input::placeholder{color:#AAAAAA}
.up-btn{
  width:44px;height:44px;border-radius:50%;
  background:#888;border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  transition:background .15s;
}
.up-btn:active{background:#555}

/* ════════════════ SHEETS ════════════════ */
.ovl{position:absolute;inset:0;background:rgba(0,0,0,.42);z-index:100;opacity:0;pointer-events:none;transition:opacity .28s}
.ovl.open{opacity:1;pointer-events:all}
.sheet{
  position:absolute;bottom:0;left:0;right:0;background:#fff;
  border-radius:28px 28px 0 0;z-index:101;
  transform:translateY(100%);transition:transform .32s cubic-bezier(.4,0,.2,1);
  max-height:92%;display:flex;flex-direction:column;
}
.sheet.open{transform:translateY(0)}
.sh-hnd{width:38px;height:4px;background:#DDD;border-radius:2px;margin:12px auto 0;cursor:pointer;flex-shrink:0}
.sh-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 20px 10px;border-bottom:1px solid var(--bd);flex-shrink:0}
.sh-ttl{font-size:17px;font-weight:700}
.sh-x{width:28px;height:28px;border-radius:50%;border:none;background:#F0F0F0;font-size:13px;cursor:pointer}
.sh-body{overflow-y:auto;flex:1}

/* Product sheet */
#ps .pimg{width:100%;height:230px;object-fit:cover;display:block}
#ps .pinfo{padding:18px 20px 24px}
#ps .pcat{font-size:11px;font-weight:600;color:var(--or);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
#ps .pnm{font-size:20px;font-weight:700;margin-bottom:10px;line-height:1.25}
#ps .ppr-row{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}
#ps .ppr{font-size:26px;font-weight:800;color:var(--or)}
#ps .pop{font-size:15px;color:var(--mt);text-decoration:line-through}
#ps .pdc{font-size:12px;font-weight:700;color:var(--gr);background:#DCFCE7;padding:2px 8px;border-radius:50px}
#ps .pst{display:flex;align-items:center;gap:8px;margin-bottom:14px}
#ps .pst .s{color:#F59E0B;font-size:14px}
#ps .pdv{height:1px;background:#F0F0F0;margin:12px 0}
#ps .pdsc{font-size:14px;line-height:1.6;color:#555;margin-bottom:20px}
.buy-btn{width:100%;padding:16px;border:none;border-radius:var(--r);background:var(--or);color:#fff;font-size:16px;font-weight:700;cursor:pointer;margin-bottom:10px;transition:background .14s}
.buy-btn:hover{background:var(--ord)}
.wish-btn{width:100%;padding:14px;border-radius:var(--r);border:1.5px solid var(--bd);background:#fff;font-size:15px;font-weight:600;cursor:pointer}

/* Checkout sheet */
.ckb{padding:0 20px 24px}
.sum-box{background:var(--ol);border-radius:var(--r);padding:14px;margin-bottom:18px}
.sum-ir{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.sum-img{width:52px;height:52px;border-radius:10px;object-fit:cover}
.sum-inf h4{font-size:13px;font-weight:600}
.sum-inf p{font-size:12px;color:var(--mt)}
.sl{display:flex;justify-content:space-between;font-size:13px;color:var(--mt);margin-top:7px}
.sl.tot{font-size:15px;font-weight:700;color:#111;border-top:1px solid #FFDCC7;padding-top:10px;margin-top:10px}
.sec{font-size:13px;font-weight:700;color:#111;margin-bottom:9px}
.fg{margin-bottom:11px}
.fg input,.fg select{width:100%;padding:12px 14px;border-radius:var(--rs);border:1.5px solid var(--bd);font-size:14px;outline:none;transition:border-color .2s}
.fg input:focus,.fg select:focus{border-color:var(--or)}
.fr{display:flex;gap:10px}.fr .fg{flex:1}
.pay-opts{display:flex;gap:10px;margin-bottom:18px}
.po{flex:1;padding:11px 6px;border:2px solid var(--bd);border-radius:var(--rs);text-align:center;cursor:pointer;font-size:12px;font-weight:600;transition:all .18s}
.po .pi2{font-size:20px;display:block;margin-bottom:3px}
.po.sel{border-color:var(--or);background:var(--ol);color:var(--ord)}
/* Card form */
.cff{margin-bottom:16px}
.cfbox{background:#FAFBFF;border:1.5px solid #E0E7FF;border-radius:12px;padding:14px}
.cfbadge{display:flex;align-items:center;gap:8px;background:#EFF6FF;border:1px solid #C7E0FF;border-radius:8px;padding:8px 12px;margin-bottom:10px;font-size:12px;color:#1D60C0}
.cfrow{display:flex;align-items:center;gap:8px;padding-bottom:10px;border-bottom:1px solid #F0F0F0}
.cfrow input{flex:1;border:none;outline:none;font-size:15px;font-family:monospace;background:transparent}
.cfsub{display:flex;gap:16px;margin-top:10px}
.cff2{flex:1}.cflbl{font-size:10px;font-weight:600;color:#999;margin-bottom:4px}
.cff2 input{width:100%;border:none;outline:none;font-size:14px;background:transparent}
.hsbdg{display:flex;align-items:center;gap:5px;margin-top:8px;font-size:11px;color:#999}
.upi-inp{width:100%;padding:12px 14px;border-radius:var(--rs);border:1.5px solid var(--bd);font-size:14px;outline:none;margin-bottom:16px}
.plc-btn{width:100%;padding:17px;border:none;border-radius:var(--r);background:var(--or);color:#fff;font-size:16px;font-weight:700;cursor:pointer;transition:background .14s}
.plc-btn:hover{background:var(--ord)}
.plc-btn:disabled{background:#CCC;cursor:not-allowed}
/* UPI waiting screen */
.upi-wait{display:flex;flex-direction:column;align-items:center;padding:40px 28px 32px;text-align:center}
.upi-spinner{width:80px;height:80px;border-radius:50%;border:3px solid #F0F0F0;border-top-color:var(--or);animation:uspin 1s linear infinite;margin-bottom:24px}
@keyframes uspin{to{transform:rotate(360deg)}}
.upi-logo{font-size:42px;margin-bottom:8px}
.upi-title{font-size:20px;font-weight:700;color:#111;margin-bottom:6px}
.upi-sub{font-size:14px;color:#777;margin-bottom:20px;line-height:1.5}
.upi-vpa-chip{background:#FFF0E8;border:1.5px solid #FFDCC7;border-radius:50px;padding:8px 18px;font-size:14px;font-weight:600;color:var(--ord);margin-bottom:20px}
.upi-amt{font-size:28px;font-weight:800;color:#111;margin-bottom:24px}
.upi-dots{display:flex;gap:8px;justify-content:center;margin-bottom:28px}
.upi-dots span{width:8px;height:8px;border-radius:50%;background:var(--or);animation:udot 1.2s ease-in-out infinite}
.upi-dots span:nth-child(2){animation-delay:.2s}
.upi-dots span:nth-child(3){animation-delay:.4s}
@keyframes udot{0%,80%,100%{opacity:.2;transform:scale(.8)}40%{opacity:1;transform:scale(1.2)}}
.upi-cancel{background:none;border:1.5px solid #DDD;border-radius:50px;padding:10px 28px;font-size:14px;color:#777;cursor:pointer}
.upi-success{display:flex;flex-direction:column;align-items:center;padding:40px 28px;text-align:center}
.upi-chk{width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,#22C55E,#16A34A);display:flex;align-items:center;justify-content:center;font-size:36px;color:#fff;margin-bottom:20px;animation:popin .4s cubic-bezier(.34,1.56,.64,1)}

/* ════════════════ CONFIRM ════════════════ */
#confirm{align-items:center;justify-content:center;text-align:center;padding:40px 28px}
.conf-chk{width:84px;height:84px;border-radius:50%;background:linear-gradient(135deg,#22C55E,#16A34A);display:flex;align-items:center;justify-content:center;font-size:42px;margin-bottom:22px;animation:popin .45s cubic-bezier(.34,1.56,.64,1)}
@keyframes popin{from{transform:scale(0);opacity:0}to{transform:scale(1);opacity:1}}
#confirm h1{font-size:25px;font-weight:800;margin-bottom:6px}
#confirm .csub{font-size:14px;color:var(--mt);margin-bottom:28px}
.ccard{width:100%;background:var(--ol);border-radius:20px;padding:18px;text-align:left;margin-bottom:22px}
.crow{display:flex;justify-content:space-between;align-items:center;font-size:13px;padding:5px 0}
.crow .cl{color:var(--mt)}.crow .cv{font-weight:600}
.crow.oid .cv{color:var(--or);font-family:monospace}
.cir{display:flex;align-items:center;gap:12px;border-bottom:1px solid #FFDCC7;padding-bottom:12px;margin-bottom:10px}
.cimg{width:52px;height:52px;border-radius:10px;object-fit:cover}
.cinf h4{font-size:14px;font-weight:600}.cinf p{font-size:13px;color:var(--mt)}
.cnt-btn{width:100%;padding:16px;border:none;border-radius:var(--r);background:var(--or);color:#fff;font-size:16px;font-weight:700;cursor:pointer;margin-bottom:10px}
.trk-btn{width:100%;padding:14px;border-radius:var(--r);border:1.5px solid var(--bd);background:transparent;font-size:15px;font-weight:600;cursor:pointer}
</style>
</head>
<body>
<div id="phone">
 <div id="sw">

  <!-- ══════════════ WELCOME ══════════════ -->
  <div class="screen" id="welcome">
   <div class="sb">
    <span class="sb-t">9:41</span>
    <div class="sb-i">
     <!-- Signal -->
     <svg width="17" height="12" viewBox="0 0 17 12" fill="#111">
      <rect x="0" y="4" width="3" height="8" rx="1"/>
      <rect x="4.5" y="2.5" width="3" height="9.5" rx="1"/>
      <rect x="9" y="0.5" width="3" height="11.5" rx="1"/>
      <rect x="13.5" y="0" width="3" height="12" rx="1" opacity=".3"/>
     </svg>
     <!-- Wifi -->
     <svg width="16" height="12" viewBox="0 0 16 12" fill="#111">
      <path d="M8 2.4C5.3 2.4 2.9 3.6 1.2 5.5L0 4.2C2 2 4.9.8 8 .8s6 1.2 8 3.4L14.8 5.5C13.1 3.6 10.7 2.4 8 2.4z"/>
      <path d="M8 5.4c-1.7 0-3.2.7-4.3 1.8L2.5 6C3.9 4.5 5.8 3.8 8 3.8s4.1.7 5.5 2.2L12.3 7.2C11.2 6.1 9.7 5.4 8 5.4z"/>
      <path d="M8 8.4c-.9 0-1.7.4-2.3 1L4.5 8.2C5.4 7.2 6.6 6.6 8 6.6s2.6.6 3.5 1.6L10.3 9.4C9.7 8.8 8.9 8.4 8 8.4z"/>
      <circle cx="8" cy="11" r="1"/>
     </svg>
     <!-- Battery -->
     <svg width="26" height="13" viewBox="0 0 26 13" fill="none">
      <rect x=".5" y=".5" width="22" height="12" rx="3.5" stroke="#111" stroke-opacity=".35"/>
      <rect x="2" y="2" width="16" height="9" rx="2" fill="#111"/>
      <path d="M24 4.5v4a2.3 2.3 0 000-4z" fill="#111" fill-opacity=".4"/>
     </svg>
     <span style="font-size:12px;font-weight:600;color:#111">67</span>
    </div>
   </div>

   <!-- Header: ≡  sarvam -->
   <div class="w-hdr">
    <button class="hmbg">≡</button>
    <span class="sw-word">sarvam</span>
   </div>

   <!-- Sarvam mandala logo — left-aligned, orange→blue gradient, outlined lens shapes -->
   <div class="w-logo">
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
     <defs>
      <linearGradient id="wg" x1="85%" y1="5%" x2="18%" y2="95%">
       <stop offset="0%"   stop-color="#F59E0B"/>
       <stop offset="35%"  stop-color="#FB923C"/>
       <stop offset="68%"  stop-color="#818CF8"/>
       <stop offset="100%" stop-color="#6366F1"/>
      </linearGradient>
      <mask id="wm">
       <g transform="translate(50,50)" stroke="white" stroke-width="3" fill="none">
        <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(0)"/>
        <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(45)"/>
        <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(90)"/>
        <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(135)"/>
        <polygon points="0,-7 7,0 0,7 -7,0" fill="white" stroke="white" stroke-width="1.5"/>
       </g>
      </mask>
     </defs>
     <rect width="100" height="100" fill="url(#wg)" mask="url(#wm)"/>
    </svg>
   </div>

   <!-- Greeting -->
   <div class="w-greet">
    <p class="w-sub">Welcome back, Mrunal!</p>
    <h1 class="w-q">What's on your mind?</h1>
   </div>

   <!-- Suggested prompts — vertical stacked pills with thumbnails -->
   <div class="plist">
    <button class="pi" onclick="startChat('Find me a Banarasi silk kurta for Diwali')">
     <img class="pt" src="https://images.unsplash.com/photo-1594938298603-c8148c4b5946?w=84&q=70" alt="">
     <span class="pt-txt">Find a kurta for Diwali 🪔</span>
    </button>
    <button class="pi" onclick="startChat('Show me silk sarees traditional jewelry')">
     <img class="pt" src="https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=84&q=70" alt="">
     <span class="pt-txt">Silk sarees &amp; jewelry 👗</span>
    </button>
    <button class="pi" onclick="startChat('Best gadgets electronics headphones smartwatch')">
     <img class="pt" src="https://images.unsplash.com/photo-1546435770-a3e736e19f91?w=84&q=70" alt="">
     <span class="pt-txt">Best gadgets &amp; tech 📱</span>
    </button>
    <button class="pi" onclick="startChat('Gift ideas under 2000 rupees for someone special')">
     <img class="pt" src="https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=84&q=70" alt="">
     <span class="pt-txt">Gift ideas under ₹2000 🎁</span>
    </button>
    <button class="pi" onclick="startChat('Yoga wellness products meditation mat')">
     <img class="pt" src="https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=84&q=70" alt="">
     <span class="pt-txt">Yoga &amp; wellness 🧘</span>
    </button>
    <button class="pi" onclick="startChat('What does the name Mrunal mean in Sanskrit?')">
     <img class="pt" src="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=84&q=70" alt="">
     <span class="pt-txt">What does my name mean? ✨</span>
    </button>
    <button class="pi" onclick="startChat('Tell me a fun fact about India that most people don\'t know')">
     <img class="pt" src="https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=84&q=70" alt="">
     <span class="pt-txt">Fun fact about India 🇮🇳</span>
    </button>
    <button class="pi" onclick="startChat('How do I say thank you in Tamil, Telugu and Bengali?')">
     <img class="pt" src="https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=84&q=70" alt="">
     <span class="pt-txt">Translate across Indian languages 🗣️</span>
    </button>
    <button class="pi" onclick="startChat('Tell me a funny joke in Hindi style')">
     <img class="pt" src="https://images.unsplash.com/photo-1527224538127-2104bb71c51b?w=84&q=70" alt="">
     <span class="pt-txt">Tell me a desi joke 😂</span>
    </button>
   </div>

   <!-- Bottom input — gray bar + dark navy mic circle -->
   <div class="w-inp-area">
    <div class="w-inp-bar">
     <input id="w-in" type="text" placeholder="Ask me anything..."
            onkeydown="if(event.key==='Enter')startChat(this.value)">
     <button class="mic-btn" onclick="startChat(document.getElementById('w-in').value)">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
           stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
       <rect x="9" y="2" width="6" height="11" rx="3"/>
       <path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="19" x2="12" y2="22"/>
       <line x1="8" y1="22" x2="16" y2="22"/>
      </svg>
     </button>
    </div>
   </div>
  </div><!-- /welcome -->

  <!-- ══════════════ CHAT ══════════════ -->
  <div class="screen hidden" id="chat">
   <div class="sb">
    <span class="sb-t">9:41</span>
    <div class="sb-i">
     <svg width="17" height="12" viewBox="0 0 17 12" fill="#111">
      <rect x="0" y="4" width="3" height="8" rx="1"/>
      <rect x="4.5" y="2.5" width="3" height="9.5" rx="1"/>
      <rect x="9" y="0.5" width="3" height="11.5" rx="1"/>
      <rect x="13.5" y="0" width="3" height="12" rx="1" opacity=".3"/>
     </svg>
     <svg width="16" height="12" viewBox="0 0 16 12" fill="#111">
      <path d="M8 2.4C5.3 2.4 2.9 3.6 1.2 5.5L0 4.2C2 2 4.9.8 8 .8s6 1.2 8 3.4L14.8 5.5C13.1 3.6 10.7 2.4 8 2.4z"/>
      <path d="M8 5.4c-1.7 0-3.2.7-4.3 1.8L2.5 6C3.9 4.5 5.8 3.8 8 3.8s4.1.7 5.5 2.2L12.3 7.2C11.2 6.1 9.7 5.4 8 5.4z"/>
      <path d="M8 8.4c-.9 0-1.7.4-2.3 1L4.5 8.2C5.4 7.2 6.6 6.6 8 6.6s2.6.6 3.5 1.6L10.3 9.4C9.7 8.8 8.9 8.4 8 8.4z"/>
      <circle cx="8" cy="11" r="1"/>
     </svg>
     <svg width="26" height="13" viewBox="0 0 26 13" fill="none">
      <rect x=".5" y=".5" width="22" height="12" rx="3.5" stroke="#111" stroke-opacity=".35"/>
      <rect x="2" y="2" width="16" height="9" rx="2" fill="#111"/>
      <path d="M24 4.5v4a2.3 2.3 0 000-4z" fill="#111" fill-opacity=".4"/>
     </svg>
     <span style="font-size:12px;font-weight:600;color:#111">67</span>
    </div>
   </div>

   <!-- Chat header: ≡  title  ✏️ -->
   <div class="c-hdr">
    <button class="hmbg" onclick="goWelcome()">≡</button>
    <span class="c-title" id="c-ttl">Sarvam</span>
    <button class="c-edit" onclick="goWelcome()" title="New chat">
     <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
          stroke="#111" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
     </svg>
    </button>
   </div>

   <div class="msgs" id="msgs"></div>

   <!-- Chat input — gray bar + gray up-arrow circle -->
   <div class="c-inp-area">
    <div class="c-inp-bar">
     <input id="c-in" type="text" placeholder=""
            onkeydown="if(event.key==='Enter')sendMsg(this.value)">
     <button class="up-btn" onclick="sendMsg(document.getElementById('c-in').value)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
           stroke="white" stroke-width="2.5" stroke-linecap="round">
       <path d="M12 19V5M5 12l7-7 7 7"/>
      </svg>
     </button>
    </div>
   </div>
  </div><!-- /chat -->

  <!-- ══════════════ CONFIRM ══════════════ -->
  <div class="screen hidden" id="confirm">
   <div class="conf-chk">✓</div>
   <h1>Order Confirmed!</h1>
   <p class="csub" id="csub">Your item is on the way 🚀</p>
   <div class="ccard" id="ccard"></div>
   <button class="cnt-btn" onclick="goWelcome()">Continue Shopping</button>
   <button class="trk-btn">📦 Track Order</button>
  </div>

  <!-- overlay -->
  <div class="ovl" id="ovl" onclick="closeSheets()"></div>

  <!-- ══ PRODUCT SHEET ══ -->
  <div class="sheet" id="ps">
   <div class="sh-hnd" onclick="closeSheets()"></div>
   <div class="sh-hdr">
    <span class="sh-ttl" id="ps-cat">Details</span>
    <button class="sh-x" onclick="closeSheets()">✕</button>
   </div>
   <div class="sh-body">
    <img id="ps-img" class="pimg" src="" alt=""
         onerror="this.src='https://placehold.co/600x300/FFE8DC/FF6B35?text=Product'">
    <div class="pinfo">
     <div class="pcat" id="ps-cat2"></div>
     <div class="pnm"  id="ps-nm"></div>
     <div class="ppr-row">
      <span class="ppr" id="ps-pr"></span>
      <span class="pop" id="ps-op"></span>
      <span class="pdc" id="ps-dc"></span>
     </div>
     <div class="pst">
      <span class="s"  id="ps-st"></span>
      <span style="font-size:14px;font-weight:600" id="ps-rt"></span>
      <span style="font-size:13px;color:var(--mt)" id="ps-rv"></span>
     </div>
     <div class="pdv"></div>
     <div class="pdsc" id="ps-ds"></div>
     <button class="buy-btn" id="ps-buy">🛒 Buy Now</button>
     <button class="wish-btn">♡  Save to Wishlist</button>
    </div>
   </div>
  </div>

  <!-- ══ CHECKOUT SHEET ══ -->
  <div class="sheet" id="cks">
   <div class="sh-hnd" onclick="closeSheets()"></div>
   <div class="sh-hdr">
    <span class="sh-ttl">Complete Your Order</span>
    <button class="sh-x" onclick="closeSheets()">✕</button>
   </div>
   <div class="sh-body" id="cks-b"></div>
  </div>

 </div><!-- /sw -->
</div><!-- /phone -->

<script>
// ── State ─────────────────────────────────────────────────────────────────────
let curScr  = 'welcome';
let curProd = null;
let selPay  = 'upi';
let hist    = [];

// ── Utils ─────────────────────────────────────────────────────────────────────
const fmt  = p => '₹' + (p/100).toLocaleString('en-IN');
const disc = (o,p) => Math.round((1-p/o)*100)+'% off';
const stars= r => { const f=Math.floor(r),h=r%1>=.5?1:0; return '★'.repeat(f)+(h?'½':'')+'☆'.repeat(5-f-h); };

function mdRender(t){
  return t
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/^## (.+)$/gm,'<h2>$1</h2>')
    .replace(/^# (.+)$/gm,'<h2>$1</h2>')
    .replace(/^\* (.+)$/gm,'<li>$1</li>')
    .replace(/(<li>[\s\S]+?<\/li>)/g,'<ul>$1</ul>')
    .split(/\n\n+/)
    .map(p=>p.trim()&&!p.match(/^<(h[23]|ul|li)/)?`<p>${p.replace(/\n/g,'<br>')}</p>`:p)
    .join('\n');
}

// ── Navigation ────────────────────────────────────────────────────────────────
function showScreen(id){
  document.querySelectorAll('.screen').forEach(s=>{
    if(s.id===id)      { s.classList.remove('hidden','slide-out'); }
    else if(curScr===s.id){ s.classList.add('slide-out'); s.classList.remove('hidden'); }
    else               { s.classList.add('hidden'); s.classList.remove('slide-out'); }
  });
  curScr=id;
}
function goWelcome(){
  closeSheets();
  hist=[];
  document.getElementById('msgs').innerHTML='';
  document.getElementById('c-ttl').textContent='Sarvam';
  showScreen('welcome');
  document.getElementById('w-in').value='';
}

// ── Sheets ────────────────────────────────────────────────────────────────────
function openSheet(id){ document.getElementById('ovl').classList.add('open'); document.getElementById(id).classList.add('open'); }
function closeSheets(){ document.getElementById('ovl').classList.remove('open'); document.querySelectorAll('.sheet').forEach(s=>s.classList.remove('open')); }

// ── Chat helpers ──────────────────────────────────────────────────────────────
// The Sarvam mandala SVG used as thinking indicator (24×24, animated)
const THINK_SVG = `<svg class="think-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
 <defs>
  <linearGradient id="tg" x1="85%" y1="5%" x2="18%" y2="95%">
   <stop offset="0%"   stop-color="#F59E0B"/>
   <stop offset="35%"  stop-color="#FB923C"/>
   <stop offset="68%"  stop-color="#818CF8"/>
   <stop offset="100%" stop-color="#6366F1"/>
  </linearGradient>
  <mask id="tm">
   <g transform="translate(50,50)" stroke="white" stroke-width="11" fill="none">
    <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(0)"/>
    <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(45)"/>
    <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(90)"/>
    <path d="M 0,-34 Q 22,0 0,34 Q -22,0 0,-34 Z" transform="rotate(135)"/>
    <polygon points="0,-8 8,0 0,8 -8,0" fill="white" stroke="white" stroke-width="2"/>
   </g>
  </mask>
 </defs>
 <rect width="100" height="100" fill="url(#tg)" mask="url(#tm)"/>
</svg>`;

function addUserMsg(text){
  const c=document.getElementById('msgs');
  const r=document.createElement('div'); r.className='mrow u';
  r.innerHTML=`<div class="bub-u">${text}</div>`;
  c.appendChild(r); c.scrollTop=c.scrollHeight;
}
function addThinking(){
  const c=document.getElementById('msgs');
  const r=document.createElement('div'); r.id='think-r'; r.className='think';
  r.innerHTML=`${THINK_SVG}<span class="think-lbl">Thinking ›</span>`;
  c.appendChild(r); c.scrollTop=c.scrollHeight;
}
function rmThinking(){ document.getElementById('think-r')?.remove(); }
function addAiMsg(text){
  const c=document.getElementById('msgs');
  const r=document.createElement('div'); r.className='mrow';
  const d=document.createElement('div'); d.className='bub-a';
  d.innerHTML=mdRender(text);
  r.appendChild(d); c.appendChild(r); c.scrollTop=c.scrollHeight;
}
function addProducts(prods){
  if(!prods||!prods.length)return;
  const c=document.getElementById('msgs');
  const w=document.createElement('div'); w.style.width='100%';
  const g=document.createElement('div'); g.className='pgrid';
  prods.forEach(p=>{
    const card=document.createElement('div'); card.className='pcard';
    card.onclick=()=>openProduct(p);
    const d=p.original_price?disc(p.original_price,p.price):null;
    card.innerHTML=`<img src="${p.image_url}" alt="${p.title}" loading="lazy"
      onerror="this.src='https://placehold.co/300/FFE8DC/FF6B35?text=Product'">
      <div class="pcb">
       <div class="pct">${p.title}</div>
       <div><span class="pcp">${fmt(p.price)}</span>${p.original_price?`<span class="pco">${fmt(p.original_price)}</span>`:''}</div>
       <div class="pcr">★ ${p.rating} (${p.reviews.toLocaleString()})</div>
       ${p.merchant?`<div class="pcm"><span class="pcm-dot"></span>${p.merchant}</div>`:''}
      </div>`;
    g.appendChild(card);
  });
  w.appendChild(g); c.appendChild(w); c.scrollTop=c.scrollHeight;
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function startChat(text){
  if(!text||!text.trim())return;
  showScreen('chat');
  const ttl=text.length>32?text.slice(0,30)+'…':text;
  document.getElementById('c-ttl').textContent=ttl;
  setTimeout(()=>sendMsg(text),80);
}
async function sendMsg(text){
  if(!text||!text.trim())return;
  text=text.trim();
  document.getElementById('c-in').value='';
  document.getElementById('w-in').value='';
  addUserMsg(text);
  hist.push({role:'user',content:text});
  addThinking();
  try{
    const res=await fetch('/api/chat',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:hist})
    });
    if(!res.ok){const e=await res.json().catch(()=>({}));throw new Error(e.detail||`HTTP ${res.status}`);}
    const data=await res.json();
    rmThinking();
    addAiMsg(data.message);
    hist.push({role:'assistant',content:data.message});
    if(data.products?.length)addProducts(data.products);
  }catch(e){
    rmThinking();
    addAiMsg('⚠️ '+(e.message||'Something went wrong.'));
  }
}

// ── Product sheet ─────────────────────────────────────────────────────────────
function openProduct(p){
  curProd=p;
  document.getElementById('ps-img').src=p.image_url;
  document.getElementById('ps-cat').textContent=p.category.toUpperCase()+(p.merchant?' · '+p.merchant:'');
  document.getElementById('ps-cat2').textContent=p.category+(p.merchant?' · '+p.merchant:'');
  document.getElementById('ps-nm').textContent=p.title;
  document.getElementById('ps-pr').textContent=fmt(p.price);
  document.getElementById('ps-op').textContent=p.original_price?fmt(p.original_price):'';
  document.getElementById('ps-dc').textContent=p.original_price?disc(p.original_price,p.price):'';
  document.getElementById('ps-st').textContent=stars(p.rating);
  document.getElementById('ps-rt').textContent=p.rating;
  document.getElementById('ps-rv').textContent=`(${p.reviews.toLocaleString()} reviews)`;
  document.getElementById('ps-ds').textContent=p.description;
  document.getElementById('ps-buy').onclick=()=>openCheckout(p);
  openSheet('ps');
}

// ── Checkout sheet ────────────────────────────────────────────────────────────
function openCheckout(p){
  curProd=p;
  const qty=1,sub=p.price*qty,gst=Math.round(sub*.18),tot=sub+gst;
  document.getElementById('ps').classList.remove('open');
  const b=document.getElementById('cks-b');
  b.innerHTML=`<div class="ckb">
   <div class="sum-box">
    <div class="sum-ir">
     <img class="sum-img" src="${p.image_url}" onerror="this.src='https://placehold.co/52/FFE8DC/FF6B35?text=P'">
     <div class="sum-inf"><h4>${p.title}</h4><p>Qty: 1</p></div>
    </div>
    <div class="sl"><span>Subtotal</span><span>${fmt(sub)}</span></div>
    <div class="sl"><span>GST (18%)</span><span>${fmt(gst)}</span></div>
    <div class="sl"><span>Delivery</span><span>FREE</span></div>
    <div class="sl tot"><span>Total</span><span>${fmt(tot)}</span></div>
   </div>
   <div class="sec">📍 Delivery Details</div>
   <div class="fg"><input id="ck-n" placeholder="Full Name"/></div>
   <div class="fg"><input id="ck-p" type="tel" placeholder="Phone (+91XXXXXXXXXX)"/></div>
   <div class="fg"><input id="ck-a" placeholder="Address"/></div>
   <div class="fr">
    <div class="fg"><input id="ck-c" placeholder="City"/></div>
    <div class="fg"><input id="ck-z" placeholder="PIN Code" maxlength="6"/></div>
   </div>
   <div class="fg">
    <select id="ck-s">
     <option value="">Select State</option>
     <option>Andhra Pradesh</option><option>Delhi</option><option>Gujarat</option>
     <option>Karnataka</option><option>Kerala</option><option>Maharashtra</option>
     <option>Rajasthan</option><option>Tamil Nadu</option><option>Telangana</option>
     <option>Uttar Pradesh</option><option>West Bengal</option>
    </select>
   </div>
   <div class="sec" style="margin-top:14px">💳 Payment</div>
   <div class="pay-opts">
    <div class="po sel" id="py-upi"  onclick="selPay2('upi')"><span class="pi2">📱</span>UPI</div>
    <div class="po"     id="py-card" onclick="selPay2('card')"><span class="pi2">💳</span>Card</div>
    <div class="po"     id="py-net"  onclick="selPay2('netbanking')"><span class="pi2">🏦</span>Net Banking</div>
   </div>
   <div id="upi-f">
    <input class="upi-inp" id="ck-upi" placeholder="UPI ID (name@upi)"/>
   </div>
   <div id="card-f" class="cff" style="display:none">
    <div class="cfbox">
     <div class="cfbadge">🧪 <span><strong>Fauxpay</strong> test card pre-filled</span></div>
     <div class="cfrow">
      <span>💳</span>
      <input id="ck-cn" placeholder="Card Number" value="4111 1111 1111 1111" maxlength="19" oninput="fmtCard(this)">
     </div>
     <div class="cfsub">
      <div class="cff2"><div class="cflbl">EXPIRY</div><input id="ck-ce" placeholder="MM/YY" value="03/28" maxlength="5"></div>
      <div class="cff2"><div class="cflbl">CVV</div><input id="ck-cv" type="password" placeholder="•••" value="737" maxlength="4"></div>
     </div>
    </div>
    <div class="hsbdg">🔒 Powered by <strong style="color:#4F46E5;margin-left:3px">Hyperswitch</strong> · Fauxpay</div>
   </div>
   <button class="plc-btn" onclick="placeOrder(${tot})">🛒 Place Order — ${fmt(tot)}</button>
  </div>`;
  selPay='upi';
  openSheet('cks');
}
function fmtCard(i){ let v=i.value.replace(/\D/g,'').slice(0,16); i.value=v.replace(/(.{4})/g,'$1 ').trim(); }
function selPay2(m){
  selPay=m;
  document.querySelectorAll('.po').forEach(e=>e.classList.remove('sel'));
  document.getElementById('py-'+m)?.classList.add('sel');
  document.getElementById('card-f').style.display=m==='card'?'block':'none';
  document.getElementById('upi-f').style.display =m==='upi'?'block':'none';
}

// ── Place order ───────────────────────────────────────────────────────────────
async function placeOrder(tot){
  const p=curProd; if(!p)return;
  const n=document.getElementById('ck-n')?.value.trim();
  const ph=document.getElementById('ck-p')?.value.trim();
  const a=document.getElementById('ck-a')?.value.trim();
  const c=document.getElementById('ck-c')?.value.trim();
  const z=document.getElementById('ck-z')?.value.trim();
  const s=document.getElementById('ck-s')?.value;
  if(!n||!ph||!a||!c||!z||!s){alert('Please fill in all delivery details.');return;}
  if(!/^\+91[6-9]\d{9}$/.test(ph)){alert('Enter valid phone: +91XXXXXXXXXX');return;}
  if(!/^[1-9][0-9]{5}$/.test(z)){alert('Enter valid 6-digit PIN code.');return;}
  let cn=null,ce=null,cy=null,cv=null;
  if(selPay==='card'){
    cn=(document.getElementById('ck-cn')?.value||'').replace(/\s/g,'');
    const er=document.getElementById('ck-ce')?.value||'';
    [ce,cy]=er.split('/');
    cv=document.getElementById('ck-cv')?.value||'';
    if(cn.length<16){alert('Enter valid 16-digit card number.');return;}
    if(!ce||!cy){alert('Enter expiry MM/YY.');return;}
    if(cv.length<3){alert('Enter CVV.');return;}
  }
  const btn=document.querySelector('.plc-btn');
  btn.disabled=true;
  btn.textContent=selPay==='card'?'⚡ Processing…':selPay==='upi'?'📱 Sending UPI request…':'🏦 Redirecting…';
  try{
    const body={item_id:p.id,quantity:1,buyer_name:n,buyer_phone:ph,address:a,city:c,state:s,pincode:z,payment_method:selPay};
    if(selPay==='card'){body.card_number=cn;body.card_exp_month=ce;body.card_exp_year=cy;body.card_cvv=cv;}
    if(selPay==='upi'){body.upi_vpa=document.getElementById('ck-upi')?.value.trim()||null;}
    const res=await fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!res.ok){const e=await res.json().catch(()=>({}));throw new Error(e.detail||`HTTP ${res.status}`);}
    const data=await res.json();
    if(data.status==='pending_upi'||data.status==='pending_netbanking'){
      showUPIWaiting(data,p,tot);
    } else {
      closeSheets(); showConfirm(data,p);
    }
  }catch(e){
    btn.disabled=false; btn.textContent='🛒 Place Order — '+fmt(tot);
    alert('❌ '+(e.message||'Order failed. Try again.'));
  }
}

// ── UPI waiting screen ────────────────────────────────────────────────────────
let _pollTimer=null;
function showUPIWaiting(data,prod,tot){
  const isNB=data.payment_method==='netbanking';
  const vpa=data.upi_vpa;
  const b=document.getElementById('cks-b');
  b.innerHTML=`<div class="upi-wait">
   <div class="upi-logo">${isNB?'🏦':'📱'}</div>
   <div class="upi-title">${isNB?'Redirecting to Bank':'Check your UPI app'}</div>
   <div class="upi-sub">${isNB
     ?'Complete the payment on your bank\'s website and come back.'
     :vpa?`A collect request has been sent to <strong>${vpa}</strong>. Open your UPI app and approve it.`
         :'Open your UPI app and approve the payment request.'}</div>
   ${vpa?`<div class="upi-vpa-chip">📲 ${vpa}</div>`:''}
   <div class="upi-amt">${fmt(data.total)}</div>
   <div class="upi-dots"><span></span><span></span><span></span></div>
   <div style="font-size:13px;color:#AAA;margin-bottom:24px">Waiting for confirmation…</div>
   <div style="display:flex;align-items:center;gap:6px;background:#EFF6FF;border-radius:10px;padding:10px 16px;font-size:12px;color:#1D60C0;margin-bottom:24px">
    🔒 Powered by <strong style="margin-left:3px">Hyperswitch</strong> · Setu Protocol
   </div>
   <button class="upi-cancel" onclick="cancelUPI(${tot})">Cancel payment</button>
  </div>`;
  // Start polling
  clearInterval(_pollTimer);
  let attempts=0;
  _pollTimer=setInterval(async()=>{
    attempts++;
    if(attempts>90){clearInterval(_pollTimer);return;} // 3-min timeout
    try{
      const r=await fetch('/api/payment/'+data.payment_id);
      const s=await r.json();
      if(s.status==='succeeded'){
        clearInterval(_pollTimer);
        showUPISuccess(b,data,prod);
        setTimeout(()=>{closeSheets();showConfirm({...data,payment_status:'succeeded'},prod);},1400);
      }
    }catch(_){}
  },2000);
}
function showUPISuccess(b,data,prod){
  b.innerHTML=`<div class="upi-success">
   <div class="upi-chk">✓</div>
   <div class="upi-title">Payment received!</div>
   <div class="upi-sub" style="margin-top:8px">₹${(data.total/100).toLocaleString('en-IN')} paid successfully</div>
  </div>`;
}
function cancelUPI(tot){
  clearInterval(_pollTimer);
  closeSheets();
}

// ── Confirmation ──────────────────────────────────────────────────────────────
function showConfirm(order,prod){
  document.getElementById('csub').textContent=`Placed for ${order.buyer_name} · ${order.estimated_delivery}`;
  document.getElementById('ccard').innerHTML=`
   <div class="cir">
    <img class="cimg" src="${prod.image_url}" onerror="this.src='https://placehold.co/52/FFE8DC/FF6B35?text=P'">
    <div class="cinf"><h4>${prod.title}</h4><p>${fmt(order.total)} · Qty 1</p></div>
   </div>
   <div class="crow oid"><span class="cl">Order ID</span><span class="cv">${order.order_id}</span></div>
   ${order.payment_id?`<div class="crow" style="background:#EFF6FF;border-radius:8px;padding:6px 10px;margin:4px 0">
    <span class="cl" style="color:#1D60C0;font-size:11px">⚡ Hyperswitch</span>
    <span class="cv" style="font-family:monospace;font-size:11px;color:#1D60C0">${order.payment_id}</span>
   </div>`:''}
   <div class="crow"><span class="cl">Payment</span><span class="cv">${order.payment_method==='card'?'💳 Card (Fauxpay)':order.payment_method.toUpperCase()}</span></div>
   <div class="crow"><span class="cl">Status</span><span class="cv" style="color:var(--gr)">✓ ${order.payment_status||'confirmed'}</span></div>
   <div class="crow"><span class="cl">Delivery</span><span class="cv">${order.estimated_delivery}</span></div>`;
  showScreen('confirm');
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    print("\n🪷  Sarvam Shopping Playground")
    print("   Open: http://localhost:3000\n")
    uvicorn.run(app, host="0.0.0.0", port=3000)
