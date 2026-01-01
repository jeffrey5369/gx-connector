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
    """
    Quick test that your GX Personal Token works (does not change anything).
    You may need to adjust this endpoint later depending on GX docs,
    but it’s a safe sanity check.
    """
    if not GX_PERSONAL_TOKEN:
        raise HTTPException(status_code=500, detail="Missing GX_PERSONAL_TOKEN")

    url = f"{GX_API_BASE}/used/public-api/v1/listings"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {GX_PERSONAL_TOKEN}",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=headers)

    return {"status_code": r.status_code, "ok": (200 <= r.status_code < 300)}