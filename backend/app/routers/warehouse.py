from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.models import WarehouseTxn, Part
from app.routers.warehouse_guard import require_roles

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

# store|admin guard
Guard = require_roles("store", "admin")

@router.get("/_ping")
def warehouse_ping():
    return {"ok": True}

@router.get("/txns", dependencies=[Depends(Guard)])
def list_warehouse_txns(db: Session = Depends(get_db)):
    rows = (
        db.query(WarehouseTxn)
        .order_by(WarehouseTxn.TxnID.desc())
        .all()
    )
    return [
        {
            "TxnID": r.TxnID,
            "TxnType": r.TxnType,
            "PartID": r.PartID,
            "Quantity": r.Quantity,
            "TxnDate": r.TxnDate,
            "Reason": r.Reason,
            "WorkOrderID": r.WorkOrderID,
        }
        for r in rows
    ]

# --- Sprint-5: Stok Çıkışı (OUT) ---
@router.post("/issue", dependencies=[Depends(Guard)])
def issue_stock(part_id: int, qty: int, db: Session = Depends(get_db), workorder_id: int | None = None):
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Miktar sıfırdan büyük olmalı")

    part = db.query(Part).filter(Part.PartID == part_id, Part.IsActive == True).first()
    if not part:
        raise HTTPException(status_code=404, detail="Parça bulunamadı")

    if (part.CurrentStock or 0) < qty:
        raise HTTPException(status_code=400, detail="Yeterli stok yok")

    # stok düş
    part.CurrentStock = (part.CurrentStock or 0) - qty

    # txn kaydı oluştur
    txn = WarehouseTxn(
        PartID=part_id,
        TxnType="OUT",
        Quantity=qty,
        Reason="Issue",
        WorkOrderID=workorder_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {"ok": True, "TxnID": txn.TxnID, "CurrentStock": part.CurrentStock}

# --- Sprint-5: Stok Girişi (IN) ---
@router.post("/receive", dependencies=[Depends(Guard)])
def receive_stock(part_id: int, qty: int, db: Session = Depends(get_db), reason: str = "Receive"):
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Miktar sıfırdan büyük olmalı")

    part = db.query(Part).filter(Part.PartID == part_id, Part.IsActive == True).first()
    if not part:
        raise HTTPException(status_code=404, detail="Parça bulunamadı")

    # stok artır
    part.CurrentStock = (part.CurrentStock or 0) + qty

    # txn kaydı oluştur
    txn = WarehouseTxn(
        PartID=part_id,
        TxnType="IN",
        Quantity=qty,
        Reason=reason,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {"ok": True, "TxnID": txn.TxnID, "CurrentStock": part.CurrentStock}
