from __future__ import annotations
from datetime import date
from typing import List, Optional
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models import PurchaseOrder, Supplier, Part, WarehouseTxn
from app.domain.constants import REASON_PO_RECEIVE

logger = logging.getLogger(__name__)

MONEY_PLACES = Decimal("0.01")


def _dialect(db: Session) -> str:
    try:
        return db.bind.dialect.name
    except Exception:
        return "unknown"


def _to_money(val) -> Decimal:
    try:
        d = val if isinstance(val, Decimal) else Decimal(str(val))
        return d.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="UnitPrice decimal olmalı.",
        )


def create_po(
    db: Session, *, supplier_id: int, part_id: int, qty: int, unit_price, eta=None
) -> PurchaseOrder:
    # qty
    if qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Qty ve UnitPrice pozitif olmalı.",
        )
    # fiyat (Decimal + 2 hane)
    price = _to_money(unit_price)
    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Qty ve UnitPrice pozitif olmalı.",
        )

    # varlık kontrolleri
    if not db.get(Supplier, supplier_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tedarikçi bulunamadı.")
    if not db.get(Part, part_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parça bulunamadı.")

    po = PurchaseOrder(
        SupplierID=int(supplier_id),
        PartID=int(part_id),
        Qty=int(qty),
        UnitPrice=price,  # Decimal
        ETA=eta,
        PODate=date.today(),
        Status_s="Created",
    )
    try:
        db.add(po)
        db.commit()
        db.refresh(po)
        return po
    except Exception as e:
        db.rollback()
        logger.exception("create_po error (SupplierID=%s, PartID=%s)", supplier_id, part_id)
        raise HTTPException(status_code=500, detail=f"create_po error: {type(e).__name__}: {e}")


def _lock_po_for_update(db: Session, po_id: int) -> Optional[PurchaseOrder]:
    """
    PO satırını güncelleme için kilitle ve taze oku.
    MSSQL'de UPDLOCK+ROWLOCK kullanılır; diğerlerinde SELECT ... FOR UPDATE.
    """
    try:
        if _dialect(db) == "mssql":
            db.execute(
                text("SELECT POID FROM PurchaseOrder WITH (UPDLOCK, ROWLOCK) WHERE POID=:pid"),
                {"pid": po_id},
            )
            po = db.get(PurchaseOrder, po_id)
            if po:
                # Session cache ihtimaline karşı taze veriyi çek
                db.refresh(po)
            return po
        else:
            return (
                db.query(PurchaseOrder)
                .filter(PurchaseOrder.POID == po_id)
                .with_for_update()
                .one_or_none()
            )
    except Exception:
        return db.get(PurchaseOrder, po_id)


def place_po(db: Session, *, po_id: int) -> PurchaseOrder:
    po = _lock_po_for_update(db, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PO bulunamadı.")

    # idempotent
    if po.Status_s == "Ordered":
        return po
    if po.Status_s != "Created":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{po.Status_s}' durumundan 'Ordered' yapılamaz.",
        )

    po.Status_s = "Ordered"
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


def receive_po(db: Session, *, po_id: int) -> PurchaseOrder:
    po = _lock_po_for_update(db, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PO bulunamadı.")

    # --- DOUBLE RECEIVE GUARD (1) : Durum kontrolü idempotent yerine anlamlı hata döndür
    if po.Status_s == "Received":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu PO zaten 'Received'. Tekrar receive edilemez.",
        )
    if po.Status_s != "Ordered":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{po.Status_s}' durumundan 'Received' yapılamaz.",
        )

    try:
        # Part'ı da kilitle
        if _dialect(db) == "mssql":
            db.execute(
                text("SELECT PartID FROM Part WITH (UPDLOCK, ROWLOCK) WHERE PartID=:pid"),
                {"pid": po.PartID},
            )
            part = db.get(Part, po.PartID)
            if part:
                db.refresh(part)
        else:
            part = (
                db.query(Part)
                .filter(Part.PartID == po.PartID)
                .with_for_update()
                .one_or_none()
            )

        if not part:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parça bulunamadı.")

        # --- DOUBLE RECEIVE GUARD (2) : WarehouseTxn'de aynı PO için önceden IN var mı?
        reason = REASON_PO_RECEIVE.format(po.POID)
        already_exists = False
        if _dialect(db) == "mssql":
            # HOLDLOCK => seri hale getir; aynı anda iki receive'ın kaçmasını engeller
            row = db.execute(
                text(
                    "SELECT TOP 1 TxnID FROM WarehouseTxn WITH (UPDLOCK, HOLDLOCK) "
                    "WHERE TxnType='IN' AND Reason=:reason"
                ),
                {"reason": reason},
            ).first()
            already_exists = row is not None
        else:
            row = (
                db.query(WarehouseTxn)
                .filter(WarehouseTxn.TxnType == "IN", WarehouseTxn.Reason == reason)
                .with_for_update()
                .first()
            )
            already_exists = row is not None

        if already_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu PO için daha önce IN hareketi oluşturulmuş (double receive engellendi).",
            )

        # Stoğu artır
        part.CurrentStock = int(part.CurrentStock or 0) + int(po.Qty or 0)
        db.add(part)

        # Depo hareketi (IN)
        tx = WarehouseTxn(
            PartID=po.PartID,
            TxnType="IN",
            Quantity=int(po.Qty or 0),
            Reason=reason,
            WorkOrderID=None,
        )
        db.add(tx)

        # PO durumu
        po.Status_s = "Received"
        db.add(po)

        db.commit()
        db.refresh(po)
        return po

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("receive_po error (POID=%s)", po_id)
        raise HTTPException(status_code=500, detail=f"receive_po error: {type(e).__name__}: {e}")


def cancel_po(db: Session, *, po_id: int) -> PurchaseOrder:
    """
    Created/Ordered -> Canceled (idempotent).
    Received olan iptal edilemez.
    """
    po = _lock_po_for_update(db, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PO bulunamadı.")

    # idempotent
    if po.Status_s == "Canceled":
        return po
    if po.Status_s == "Received":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Received bir PO iptal edilemez.",
        )

    # Created veya Ordered ise iptal et
    po.Status_s = "Canceled"
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


# ---- Listeleme servisi ----
def list_pos(
    db: Session,
    *,
    status_s: Optional[str] = None,
    supplier_id: Optional[int] = None,
    part_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    sort: str = "-POID",
) -> List[PurchaseOrder]:
    q = db.query(PurchaseOrder)

    if status_s:
        q = q.filter(PurchaseOrder.Status_s == status_s)
    if supplier_id:
        q = q.filter(PurchaseOrder.SupplierID == supplier_id)
    if part_id:
        q = q.filter(PurchaseOrder.PartID == part_id)
    if date_from:
        q = q.filter(PurchaseOrder.PODate >= date_from)
    if date_to:
        q = q.filter(PurchaseOrder.PODate <= date_to)

    order_fields = {
        "POID": PurchaseOrder.POID,
        "PODate": PurchaseOrder.PODate,
        "ETA": PurchaseOrder.ETA,
    }
    desc = sort.startswith("-")
    key = sort[1:] if desc else sort
    col = order_fields.get(key, PurchaseOrder.POID)
    q = q.order_by(col.desc() if desc else col.asc())

    return q.offset(max(0, skip)).limit(min(max(1, limit), 500)).all()

