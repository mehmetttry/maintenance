from typing import Optional, Literal
from datetime import date

from fastapi import FastAPI, APIRouter, Query
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import PurchaseOrder, WarehouseTxn
from app.services.purchase_service import list_pos
from app.routers.purchase import router as purchase_router  # place/receive

print("=== LOADED app.app_entry ===")

app = FastAPI(title="TORA_M PROJECT")

@app.get("/__whoami")
def whoami():
    # Hangi dosya gerçekten yüklendiğini görmek için
    return {"module": __name__, "file": __file__}

@app.get("/__routes")
def routes():
    # Yüklü tüm path'leri gör
    return sorted({getattr(r, "path", None) for r in app.router.routes})

@app.get("/health")
def health():
    return {"ok": True}

# ---------------- Purchase (geçici create + echo + list) ----------------
purchase = APIRouter(prefix="/purchase-orders", tags=["purchase"])

@purchase.get("/_ping")
def purchase_ping():
    return {"ok": True}

@purchase.post("/_echo", status_code=201)
def echo(payload: dict):
    return {"echo": payload}

@purchase.post("", status_code=201)
def create_po(payload: dict):
    from traceback import format_exc
    db: Session = SessionLocal()
    try:
        sid   = int(payload["SupplierID"])
        pid   = int(payload["PartID"])
        qty   = int(payload["Qty"])
        price = float(str(payload["UnitPrice"]).replace(",", "."))

        po = PurchaseOrder(
            SupplierID=sid,
            PartID=pid,
            Qty=qty,
            UnitPrice=price,
            Status_s="Created",
            PODate=date.today(),
        )
        db.add(po)
        db.commit()
        db.refresh(po)

        return {
            "POID": po.POID,
            "SupplierID": po.SupplierID,
            "PartID": po.PartID,
            "Qty": po.Qty,
            "UnitPrice": float(po.UnitPrice),
            "Status_s": po.Status_s,
            "PODate": po.PODate.isoformat() if getattr(po, "PODate", None) else None,
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e), "trace": format_exc()[:1200]}
    finally:
        db.close()

@purchase.get("/", status_code=200)
def list_purchase_orders(
    status_s: Optional[Literal["Created", "Ordered", "Received", "Canceled"]] = Query(None),
    supplier_id: Optional[int] = Query(None, ge=1),
    part_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort: str = Query("-POID"),
):
    db: Session = SessionLocal()
    try:
        rows = list_pos(
            db,
            status_s=status_s,
            supplier_id=supplier_id,
            part_id=part_id,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
            sort=sort,
        )
        return [
            {
                "POID": r.POID,
                "SupplierID": r.SupplierID,
                "PartID": r.PartID,
                "Qty": r.Qty,
                "UnitPrice": float(r.UnitPrice),
                "PODate": r.PODate.isoformat() if getattr(r, "PODate", None) else None,
                "ETA": r.ETA.isoformat() if getattr(r, "ETA", None) else None,
                "Status_s": r.Status_s,
            }
            for r in rows
        ]
    finally:
        db.close()

@purchase.get("", include_in_schema=False)
def list_purchase_orders_noslash(
    status_s: Optional[Literal["Created", "Ordered", "Received", "Canceled"]] = Query(None),
    supplier_id: Optional[int] = Query(None, ge=1),
    part_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort: str = Query("-POID"),
):
    return list_purchase_orders(status_s, supplier_id, part_id, date_from, date_to, skip, limit, sort)

# ---------------- Warehouse (ping + liste) ----------------
warehouse = APIRouter(prefix="/warehouse", tags=["warehouse"])

@warehouse.get("/_ping")
def warehouse_ping():
    return {"ok": True}

@warehouse.get("/txns")
def list_warehouse_txns():
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(WarehouseTxn)
              .order_by(WarehouseTxn.TxnID.desc())
              .limit(100)
              .all()
        )
        return [
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
    finally:
        db.close()

# ---------------- Router’ları uygula ----------------
app.include_router(purchase)          # create/_ping/_echo + GET liste
app.include_router(purchase_router)   # /purchase-orders/{po_id}/place & /receive
app.include_router(warehouse)         # /warehouse/_ping & /txns
