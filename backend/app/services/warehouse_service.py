# backend/app/services/warehouse_service.py
from __future__ import annotations
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models import WarehouseTxn, Part, WorkOrder


def create_txn(
    db: Session,
    *,
    part_id: int,
    txn_type: str,         # "IN" | "OUT"
    quantity: int,         # > 0
    reason: str | None = None,
    workorder_id: int | None = None,
) -> WarehouseTxn:
    """
    Depo hareketi oluşturur ve Part.CurrentStock'u günceller.
    - IN  -> stok += quantity
    - OUT -> stok -= quantity (yetersiz stokta 409)
    - Satır kilidi: Part üzerinde UPDLOCK/ROWLOCK (yarışlara karşı)
    """
    try:
        # 1) Girdi doğrulama
        if quantity is None or quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Quantity > 0 olmalı."
            )
        if txn_type not in ("IN", "OUT"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="TxnType 'IN' | 'OUT' olmalı."
            )

        # 2) Part satırını kilitle (SQL Server için UPDLOCK/ROWLOCK)
        db.execute(
            text("SELECT PartID FROM Part WITH (UPDLOCK, ROWLOCK) WHERE PartID = :pid"),
            {"pid": part_id},
        )
        part = db.get(Part, part_id)
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parça (Part) bulunamadı."
            )

        # 3) (Opsiyonel) WorkOrder doğrulaması
        if workorder_id is not None:
            wo = db.get(WorkOrder, workorder_id)
            if not wo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="WorkOrder bulunamadı."
                )

        # 4) Stok hesapla
        cur = part.CurrentStock or 0
        if txn_type == "OUT":
            if cur < quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Stok yetersiz. Mevcut: {cur}, istenen: {quantity}"
                )
            part.CurrentStock = cur - quantity
        else:  # "IN"
            part.CurrentStock = cur + quantity

        # 5) Hareket kaydı
        tx = WarehouseTxn(
            PartID=part.PartID,
            TxnType=txn_type,
            Quantity=quantity,
            Reason=reason,
            WorkOrderID=workorder_id,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Beklenmeyen hata: {str(e)}"
        )


def list_txns(
    db: Session,
    *,
    part_id: Optional[int] = None,
    txn_type: Optional[str] = None,   # "IN" | "OUT"
    q: Optional[str] = None,          # Reason içinde arama
    skip: int = 0,
    limit: int = 100,
    sort: str = "-TxnID",             # "TxnID" | "-TxnID"
) -> List[WarehouseTxn]:
    query = db.query(WarehouseTxn)

    if part_id is not None:
        query = query.filter(WarehouseTxn.PartID == part_id)
    if txn_type is not None:
        query = query.filter(WarehouseTxn.TxnType == txn_type)
    if q:
        query = query.filter(func.lower(WarehouseTxn.Reason).like(f"%{q.lower()}%"))

    col = WarehouseTxn.TxnID
    query = query.order_by(col.desc() if sort.startswith("-") else col.asc())

    return query.offset(max(0, skip)).limit(min(max(1, limit), 500)).all()
