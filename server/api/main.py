from __future__ import annotations
import os
import json
import hmac
from hashlib import sha512
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, Header, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from jose import jwt
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .models import AdminUser, License, Activation, RevokedToken

APP = FastAPI(title="FarmApp Licensing API")

# ====== Configuration ======
ISS = os.getenv("LICENSE_ISS", "ahmedhussein.online")
AUD = os.getenv("LICENSE_AUD", "FarmApp")
PRIVKEY_PATH = os.getenv("LICENSE_PRIVKEY_PATH", "/run/keys/private.pem")
PUBKEY_PATH = os.getenv("LICENSE_PUBKEY_PATH", PRIVKEY_PATH)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")  # Set a strong secret in production.
SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "change-this-in-production")

# ====== DB Init ======
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure default admin exists
with SessionLocal() as db:
    if not db.query(AdminUser).filter(AdminUser.username == ADMIN_USERNAME).first():
        db.add(AdminUser(username=ADMIN_USERNAME, password_hash=bcrypt.hash(ADMIN_PASSWORD)))
        db.commit()

# ====== Models (I/O) ======
class ActivateReq(BaseModel):
    license_key: str
    hwid: str
    device_limit: int = 1

class ActivateResp(BaseModel):
    token: str

class VerifyResp(BaseModel):
    ok: bool
    message: Optional[str] = None

class DeactivateReq(BaseModel):
    token: str

# ====== JWT helpers ======
def _load_privkey() -> str:
    with open(PRIVKEY_PATH, "r", encoding="utf-8") as f:
        return f.read()

def _issue_token(license_key: str, customer: str, hwid: str, plan: str, days: int = 365) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": ISS,
        "aud": AUD,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(days=days)).timestamp()),
        "customer": customer,
        "plan": plan,
        "hwid": hwid,
        "devices": 1,
    }
    priv = _load_privkey()
    return jwt.encode(payload, priv, algorithm="ES256")

# ====== API Endpoints ======
@APP.post("/api/v1/activate", response_model=ActivateResp)
async def activate(req: ActivateReq, db: Session = Depends(get_db)):
    key = req.license_key.strip()
    if not key:
        raise HTTPException(400, "license_key required")

    lic = db.query(License).filter(License.key == key).first()
    if not lic:
        # Demo behavior: accept keys starting with FA-
        if not key.upper().startswith("FA-"):
            raise HTTPException(400, "Invalid license key")
        lic = License(
            key=key,
            customer="Customer",
            plan="standard",
            device_limit=req.device_limit or 1,
            active=True,
        )
        db.add(lic)
        db.commit()
        db.refresh(lic)

    if not lic.active:
        raise HTTPException(403, "License inactive")

    # Check device limit (allow existing hwid re-activation)
    existing = db.query(Activation).filter(Activation.license_id == lic.id).all()
    if not any(a.hwid == req.hwid for a in existing) and len(existing) >= int(lic.device_limit or 1):
        raise HTTPException(403, "Device limit reached")

    token = _issue_token(lic.key, lic.customer or "Customer", req.hwid, lic.plan or "standard", days=365)

    # Upsert activation for this hwid
    act = db.query(Activation).filter(Activation.license_id == lic.id, Activation.hwid == req.hwid).first()
    if act:
        act.token = token
    else:
        act = Activation(license_id=lic.id, hwid=req.hwid, token=token)
        db.add(act)
    db.commit()

    return ActivateResp(token=token)

@APP.get("/api/v1/verify", response_model=VerifyResp)
async def verify(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1].strip()

    # Revocation check
    if db.query(RevokedToken.id).filter(RevokedToken.token == token).first():
        return VerifyResp(ok=False, message="Revoked")

    # Verify JWT signature and claims
    try:
        with open(PUBKEY_PATH, "r", encoding="utf-8") as f:
            verify_key = f.read()
        jwt.decode(
            token,
            verify_key,
            algorithms=["ES256"],
            audience=AUD,
            issuer=ISS,
        )
        return VerifyResp(ok=True)
    except Exception:
        # Fallback: accept recently issued tokens stored in DB (optional)
        if db.query(Activation.id).filter(Activation.token == token).first():
            return VerifyResp(ok=True)
        return VerifyResp(ok=False, message="Invalid token")

@APP.post("/api/v1/deactivate")
async def deactivate(req: DeactivateReq, db: Session = Depends(get_db)):
    # Remove activation if exists
    db.query(Activation).filter(Activation.token == req.token).delete()
    # Add to revoked list (idempotent)
    if not db.query(RevokedToken.id).filter(RevokedToken.token == req.token).first():
        db.add(RevokedToken(token=req.token))
    db.commit()
    return {"ok": True}

# ====== Admin UI (templates + sessions) ======
APP.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, session_cookie="fa_admin")

# Mount templates and optional static
TEMPLATES = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    APP.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Session helpers
def _is_admin(request: Request) -> bool:
    return bool(request.session.get("admin") is True)

def _require_admin(request: Request) -> Optional[RedirectResponse]:
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    return None

@APP.api_route("/admin/login", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def admin_login_form(request: Request):
    if _is_admin(request):
        return RedirectResponse("/admin", status_code=302)
    return TEMPLATES.TemplateResponse("login.html", {"request": request, "error": None})

@APP.post("/admin/login")
async def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    # Use env-configured admin for simplicity; optionally verify against DB hashed user
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/admin", status_code=302)
    return TEMPLATES.TemplateResponse("login.html", {"request": request, "error": "اسم مستخدم أو كلمة مرور غير صحيحة"})

@APP.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)

@APP.api_route("/admin", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    redir = _require_admin(request)
    if redir:
        return redir
    total_licenses = db.query(License).count()
    total_activations = db.query(Activation).count()
    total_revoked = db.query(RevokedToken).count()

    # Simple dicts for template
    licenses = [
        {
            "key": l.key,
            "customer": l.customer,
            "plan": l.plan,
            "limit": l.device_limit,
            "active": l.active,
        }
        for l in db.query(License).all()
    ]
    activations = [
        {
            "license_key": db.query(License.key).filter(License.id == a.license_id).scalar(),
            "hwid": a.hwid,
            "token": a.token,
        }
        for a in db.query(Activation).all()
    ]

    return TEMPLATES.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_licenses": total_licenses,
            "total_activations": total_activations,
            "total_revoked": total_revoked,
            "licenses": licenses,
            "activations": activations,
        },
    )

@APP.post("/admin/license/create")
async def admin_license_create(
    request: Request,
    license_key: str = Form(...),
    customer: str = Form("Customer"),
    plan: str = Form("standard"),
    limit: int = Form(1),
    active: bool = Form(True),
    db: Session = Depends(get_db),
):
    redir = _require_admin(request)
    if redir:
        return redir
    key = license_key.strip()
    if not key:
        raise HTTPException(400, "license_key required")
    if db.query(License.id).filter(License.key == key).first():
        raise HTTPException(400, "license key exists")
    db.add(
        License(
            key=key,
            customer=customer.strip() or "Customer",
            plan=plan.strip() or "standard",
            device_limit=int(limit) if limit else 1,
            active=bool(active),
        )
    )
    db.commit()
    return RedirectResponse("/admin", status_code=302)

@APP.post("/admin/license/toggle")
async def admin_license_toggle(request: Request, license_key: str = Form(...), active: int = Form(1), db: Session = Depends(get_db)):
    redir = _require_admin(request)
    if redir:
        return redir
    lic = db.query(License).filter(License.key == license_key).first()
    if not lic:
        raise HTTPException(404, "license not found")
    lic.active = bool(int(active))
    db.commit()
    return RedirectResponse("/admin", status_code=302)

@APP.post("/admin/token/revoke")
async def admin_token_revoke(request: Request, token: str = Form(...), db: Session = Depends(get_db)):
    redir = _require_admin(request)
    if redir:
        return redir
    if not db.query(RevokedToken.id).filter(RevokedToken.token == token).first():
        db.add(RevokedToken(token=token))
    db.query(Activation).filter(Activation.token == token).delete()
    db.commit()
    return RedirectResponse("/admin", status_code=302)

@APP.post("/admin/activation/remove")
async def admin_activation_remove(request: Request, token: str = Form(...), db: Session = Depends(get_db)):
    redir = _require_admin(request)
    if redir:
        return redir
    db.query(Activation).filter(Activation.token == token).delete()
    db.commit()
    return RedirectResponse("/admin", status_code=302)

# Graceful redirects for trailing slashes
@APP.api_route("/admin/", methods=["GET", "HEAD"], include_in_schema=False)
async def admin_slash():
    return RedirectResponse("/admin", status_code=302)

@APP.api_route("/admin/login/", methods=["GET", "HEAD"], include_in_schema=False)
async def admin_login_slash():
    return RedirectResponse("/admin/login", status_code=302)

# ====== Webhook (placeholder) ======
@APP.post("/webhook/paymob")
async def paymob_webhook(request: Request, x_hmac_signature: str | None = Header(None)):
    body = await request.body()
    hmac_key = os.getenv("PAYMOB_HMAC_KEY", "")
    if not hmac_key:
        data = await request.json()
    else:
        calc = hmac.new(hmac_key.encode(), body, sha512).hexdigest()
        if x_hmac_signature != calc:
            raise HTTPException(403, "Invalid HMAC")
        data = json.loads(body)
    # TODO: create License row from successful payment event
    print("Webhook received:", data)
    return {"ok": True}

# ====== Health ======
@APP.get("/")
async def root():
    return {"status": "ok"}