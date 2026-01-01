import os
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

GX_API_BASE = os.getenv("GX_API_BASE", "https://www.sweetwater.com").rstrip("/")
GX_PERSONAL_TOKEN = os.getenv("GX_PERSONAL_TOKEN", "")
GX_WEBHOOK_SECRET = os.getenv("GX_WEBHOOK_SECRET", "")  # shared secret GX will send back

@app.get("/health")
def health():
    return {"ok": True}
@app.get("/debug/env")
def debug_env():
    t = os.getenv("GX_PERSONAL_TOKEN", "")
    return {
        "GX_API_BASE": os.getenv("GX_API_BASE", ""),
        "GX_PERSONAL_TOKEN_set": bool(t),
        "GX_PERSONAL_TOKEN_len": len(t),
        "GX_PERSONAL_TOKEN_prefix": t[:6],   # only first 6 chars (safe)
        "GX_WEBHOOK_SECRET_set": bool(os.getenv("GX_WEBHOOK_SECRET", "")),
    }
def _check_gx_webhook_auth(request: Request):
    """
    GX webhooks will include: Authorization: Bearer <token_you_set_in_GX>
    We'll compare it to GX_WEBHOOK_SECRET.
    """
    if not GX_WEBHOOK_SECRET:
        # If you forget to set it, fail closed.
        raise HTTPException(status_code=500, detail="Server not configured (missing GX_WEBHOOK_SECRET)")

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        received = auth.split(" ", 1)[1].strip()
    else:
        received = ""

    if received != GX_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/gx/webhook")
async def gx_webhook(request: Request):
    _check_gx_webhook_auth(request)

    payload = await request.json()

    # For now: just acknowledge and log basic shape (Render will show logs)
    event_type = payload.get("event_type") or payload.get("type") or "unknown"
    return {"received": True, "event_type": event_type}

@app.get("/gx/ping")
async def gx_ping():
    if not GX_PERSONAL_TOKEN:
        raise HTTPException(status_code=500, detail="Missing GX_PERSONAL_TOKEN")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {GX_PERSONAL_TOKEN}",
        "User-Agent": "gx-connector/1.0",
    }

    user_url = f"{GX_API_BASE}/used/public-api/v1/user"
    listings_url = f"{GX_API_BASE}/used/public-api/v1/listings"

    async with httpx.AsyncClient(timeout=20) as client:
        r_user = await client.get(user_url, headers=headers)
        r_listings = await client.get(listings_url, headers=headers)

    return {
        "user_status": r_user.status_code,
        "user_preview": (r_user.text or "")[:200],
        "listings_status": r_listings.status_code,
        "listings_preview": (r_listings.text or "")[:200],
    }
