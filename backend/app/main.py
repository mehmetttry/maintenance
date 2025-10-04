# backend/app/main.py
import os, json
from typing import Optional
from fastapi import FastAPI, APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

# .env yükle
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from app.core.db import get_db, engine
from app.models.user import AppUser
from app.models import WarehouseTxn

# --- Router importları ---
from app.routers.purchase import router as purchase_router
from app.routers.auth import router as auth_router
from app.routers.parts import router as parts_router
from app.routers.warehouse_guard import require_roles
from app.routers.reports import router as reports_router
from app.routers.maintenance import router as maintenance_router
from app.routers.workorders import router as workorders_router

# --- Service importları (IN/OUT için) ---
from app.services.warehouse_service import create_txn

# --- API zarfları ---
from app.core.api import ok, fail, list_meta, UTF8JSONResponse

# --- CORS ---
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TORA_M PROJECT", default_response_class=UTF8JSONResponse)

print("=== LOADED main.py from:", __file__)

# JSON Content-Type charset düzeltmesi
@app.middleware("http")
async def _force_json_charset(request, call_next):
    resp = await call_next(request)
    ct = resp.headers.get("content-type", "")
    if ct.lower().startswith("application/json") and "charset=" not in ct.lower():
        resp.headers["content-type"] = "application/json; charset=utf-8"
    return resp


# -----------------------------
# Global hata zarfı (ARTIK AÇIK)
# -----------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_to_envelope(request: Request, exc: StarletteHTTPException):
    return fail(str(exc.detail) if exc.detail else exc.__class__.__name__, status_code=exc.status_code)

@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_to_envelope(request: Request, exc: FastAPIHTTPException):
    return fail(str(exc.detail) if exc.detail else exc.__class__.__name__, status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_to_envelope(request: Request, exc: RequestValidationError):
    return fail("Validation error", status_code=422, meta={"errors": exc.errors()})


# -----------------------------
# CORS yapılandırması (.env)
# -----------------------------
def _parse_origins(env_val: str | None):
    if not env_val or env_val.strip() == "*":
        return ["*"]
    try:
        import json as _json
        parsed = _json.loads(env_val)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return [s.strip() for s in env_val.split(",") if s.strip()]

ALLOWED_ORIGINS = _parse_origins(os.getenv("CORS_ALLOW_ORIGINS", "*"))
print("CORS allow_origins =", ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- startup: AppUser tablosu yoksa oluştur ----
@app.on_event("startup")
def _ensure_user_table():
    try:
        AppUser.__table__.create(bind=engine, checkfirst=True)
    except Exception as e:
        print("WARN: AppUser table create failed:", e)

# ---- Sağlık uçları ----
@app.get("/health")
def health():
    return ok({"service": "TORA_M PROJECT"})

@app.get("/db-ping")
def db_ping(db: Session = Depends(get_db)):
    val = db.execute(text("SELECT 1")).scalar()
    return ok({"db": "ok", "select1": val})

# ---- Geliştirici yardımcıları ----
@app.get("/__whoami", include_in_schema=False)
def whoami():
    return {"file": __file__}

@app.get("/__routes", include_in_schema=False)
def dump_routes():
    return [getattr(r, "path", str(r)) for r in app.routes]


# =========================
# Purchase DEBUG
# =========================
purchase_debug = APIRouter(prefix="/purchase-debug", tags=["purchase-debug"])

@purchase_debug.get("/_ping")
def purchase_ping():
    return {"ok": True}

@purchase_debug.post("/_echo", status_code=201)
def echo(payload: dict):
    return {"echo": payload}


# =========================
# Warehouse (guarded)
# =========================
Guard = require_roles("store", "admin")
warehouse = APIRouter(
    prefix="/warehouse",
    tags=["warehouse"],
    dependencies=[Depends(Guard)],
)

@warehouse.get("/_ping")
def warehouse_ping():
    return {"ok": True}

@warehouse.get("/txns")
def list_warehouse_txns(db: Session = Depends(get_db)):
    rows = (
        db.query(WarehouseTxn)
          .order_by(WarehouseTxn.TxnID.desc())
          .limit(100)
          .all()
    )
    items = [
        {
            "TxnID": r.TxnID,
            "PartID": r.PartID,
            "TxnType": r.TxnType,
            "Quantity": r.Quantity,
            "Reason": r.Reason,
            "WorkOrderID": getattr(r, "WorkOrderID", None),
        }
        for r in rows
    ]
    return ok(items, meta=list_meta(items))

# ---- IN/OUT payload modeli ----
class _IOPayload(BaseModel):
    PartID: int = Field(..., ge=1)
    Quantity: int = Field(..., gt=0)
    Reason: Optional[str] = None
    WorkOrderID: Optional[int] = None

@warehouse.post("/in", status_code=201)
def warehouse_in(payload: _IOPayload, db: Session = Depends(get_db)):
    tx = create_txn(
        db,
        part_id=payload.PartID,
        txn_type="IN",
        quantity=payload.Quantity,
        reason=payload.Reason,
        workorder_id=payload.WorkOrderID,
    )
    return ok({
        "TxnID": tx.TxnID,
        "PartID": tx.PartID,
        "TxnType": tx.TxnType,
        "Quantity": tx.Quantity,
        "Reason": tx.Reason,
        "WorkOrderID": getattr(tx, "WorkOrderID", None),
    })

@warehouse.post("/out", status_code=201)
def warehouse_out(payload: _IOPayload, db: Session = Depends(get_db)):
    tx = create_txn(
        db,
        part_id=payload.PartID,
        txn_type="OUT",
        quantity=payload.Quantity,
        reason=payload.Reason,
        workorder_id=payload.WorkOrderID,
    )
    return ok({
        "TxnID": tx.TxnID,
        "PartID": tx.PartID,
        "TxnType": tx.TxnType,
        "Quantity": tx.Quantity,
        "Reason": tx.Reason,
        "WorkOrderID": getattr(tx, "WorkOrderID", None),
    })


# =========================
# Router kayıtları
# =========================
app.include_router(auth_router)
app.include_router(parts_router)
app.include_router(purchase_router)
app.include_router(purchase_debug)
app.include_router(warehouse)
app.include_router(reports_router)
app.include_router(maintenance_router)   # /requests
app.include_router(workorders_router)    # /workorders

print(">>> /reports routes registered")
print(">>> /auth routes registered")
print(">>> /parts routes registered")
print(">>> /purchase routes registered")
print(">>> /purchase-debug routes registered")
print(">>> /warehouse routes registered")
print(">>> /maintenance (/requests) routes registered")
print(">>> /workorders routes registered")
