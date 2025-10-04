# app/routers/purchase.py
from typing import List, Optional, Literal
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, conint, field_validator
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.routers.warehouse_guard import require_roles  # guard
from app.schemas.purchase import PORead
from app.models.part import Part
from app.models.purchase_order import PurchaseOrder   # ✅ doğru import

from app.services.purchase_service import (
    list_pos,
    create_po,
    place_po,
    receive_po,
    cancel_po,
)

# ✅ Reason standardını tek kaynaktan kullanmak için import
from app.domain.constants import REASON_PO_RECEIVE

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

# Role guard (store veya admin)
Guard = require_roles("store", "admin")

MONEY_PLACES = Decimal("0.01")  # 2 hane

# Dokümantasyon/testlerde kontrol edebilmek için örnek dize
REASON_PO_RECEIVE_DOC = REASON_PO_RECEIVE.format("<POID>")


# --- LIST ---
@router.get("/", response_model=List[PORead])
def list_purchase_orders_slash(
    status_s: Optional[Literal["Created", "Ordered", "Received", "Canceled"]] = Query(None),
    supplier_id: Optional[int] = Query(None, ge=1),
    part_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort: str = Query("-POID"),
    db: Session = Depends(get_db),
):
    return list_pos(
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


@router.get("", response_model=List[PORead], include_in_schema=False)
def list_purchase_orders_noslash(
    status_s: Optional[Literal["Created", "Ordered", "Received", "Canceled"]] = Query(None),
    supplier_id: Optional[int] = Query(None, ge=1),
    part_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort: str = Query("-POID"),
    db: Session = Depends(get_db),
):
    return list_pos(
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


# --- CREATE ---
class POCreateIn(BaseModel):
    SupplierID: int
    PartID: int
    Qty: conint(gt=0)
    UnitPrice: Decimal

    @field_validator("UnitPrice")
    @classmethod
    def _price_decimal(cls, v: Decimal) -> Decimal:
        try:
            d = v if isinstance(v, Decimal) else Decimal(str(v))
            d = d.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("UnitPrice must be a valid decimal")
        if d <= 0:
            raise ValueError("UnitPrice must be > 0")
        return d


@router.post("", response_model=PORead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(Guard)])
def create_purchase_order(payload: POCreateIn, db: Session = Depends(get_db)):
    return create_po(
        db,
        supplier_id=int(payload.SupplierID),
        part_id=int(payload.PartID),
        qty=int(payload.Qty),
        unit_price=payload.UnitPrice,
        eta=None,
    )


@router.post("/", response_model=PORead, include_in_schema=False, status_code=status.HTTP_201_CREATED, dependencies=[Depends(Guard)])
def create_purchase_order_slash(payload: POCreateIn, db: Session = Depends(get_db)):
    return create_po(
        db,
        supplier_id=int(payload.SupplierID),
        part_id=int(payload.PartID),
        qty=int(payload.Qty),
        unit_price=payload.UnitPrice,
        eta=None,
    )


# --- FROM SUGGESTION ---
class POFromSuggestionIn(BaseModel):
    SupplierID: int
    PartID: int
    UnitPrice: Decimal

    @field_validator("UnitPrice")
    @classmethod
    def _price_decimal(cls, v: Decimal) -> Decimal:
        try:
            d = v if isinstance(v, Decimal) else Decimal(str(v))
            d = d.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("UnitPrice must be a valid decimal")
        if d <= 0:
            raise ValueError("UnitPrice must be > 0")
        return d


@router.post("/from-suggestion", response_model=PORead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(Guard)])
def create_po_from_suggestion(payload: POFromSuggestionIn, db: Session = Depends(get_db)):
    part = (
        db.query(Part)
        .filter(Part.PartID == payload.PartID)
        .filter(Part.IsActive == True)  # noqa: E712
        .first()
    )
    if not part:
        raise HTTPException(status_code=404, detail="Part not found or inactive")

    ms = int(part.MinStock or 0)
    cs = int(part.CurrentStock or 0)
    gap = ms - cs
    if gap <= 0:
        raise HTTPException(status_code=400, detail=f"No shortage for PartID={payload.PartID} (gap={gap})")

    return create_po(
        db,
        supplier_id=int(payload.SupplierID),
        part_id=int(payload.PartID),
        qty=int(gap),
        unit_price=payload.UnitPrice,
        eta=None,
    )


# --- WORKFLOW ---
@router.post("/{po_id}/place", response_model=PORead, dependencies=[Depends(Guard)])
def place_purchase_order(po_id: int, db: Session = Depends(get_db)):
    return place_po(db, po_id=po_id)


@router.post("/{po_id}/receive", response_model=PORead, dependencies=[Depends(Guard)])
def receive_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """
    Idempotent: Zaten 'Received' ise 409 döner.
    Depo IN kaydı purchase_service.receive_po içinde oluşturulur (router tekrar oluşturmaz).
    Reason standardı tek kaynaktan: REASON_PO_RECEIVE -> örnek: REASON_PO_RECEIVE.format(POID)
    """
    return receive_po(db, po_id=po_id)


@router.post("/{po_id}/cancel", response_model=PORead, dependencies=[Depends(Guard)])
def cancel_purchase_order(po_id: int, db: Session = Depends(get_db)):
    return cancel_po(db, po_id=po_id)
