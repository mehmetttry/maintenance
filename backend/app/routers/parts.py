# app/routers/parts.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..core.db import get_db
from ..models.part import Part
from .warehouse_guard import require_roles

router = APIRouter(prefix="/parts", tags=["parts"])

@router.get("/_ping")
def parts_ping():
    return {"ok": True}

# Sadece store ve admin erişsin
Guard = require_roles("store", "admin")

@router.get("/below-min", dependencies=[Depends(Guard)])
def parts_below_min(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    sort: str = Query(
        "-gap",
        description="İzinli: gap, -gap, PartCode, -PartCode, PartName, -PartName, PartID, -PartID",
    ),
    db: Session = Depends(get_db),
):
    cs = func.coalesce(Part.CurrentStock, 0)
    ms = func.coalesce(Part.MinStock, 0)
    gap_expr = (ms - cs)  # stok açığı (pozitifse eksik var)

    sort_map = {
        "gap": gap_expr,
        "-gap": desc(gap_expr),
        "PartCode": Part.PartCode,
        "-PartCode": desc(Part.PartCode),
        "PartName": Part.PartName,
        "-PartName": desc(Part.PartName),
        "PartID": Part.PartID,
        "-PartID": desc(Part.PartID),
    }
    order_by_clause = sort_map.get(sort, desc(gap_expr))

    base_q = (
        db.query(Part)
          .filter(Part.IsActive == True)   # pasif parçaları listeleme
          .filter(gap_expr > 0)            # min altı
    )

    total = base_q.count()

    rows = (
        base_q
        .order_by(order_by_clause)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "value": [
            {
                "PartID": p.PartID,
                "PartCode": p.PartCode,
                "PartName": p.PartName,
                "Unit": p.Unit,
                "MinStock": int(p.MinStock or 0),
                "CurrentStock": int(p.CurrentStock or 0),
            }
            for p in rows
        ],
        "Count": total,
    }


@router.get("/reorder-suggestion", dependencies=[Depends(Guard)])
def parts_reorder_suggestion(
    min_gap: int = Query(1, ge=1, description="En az şu kadar açık varsa öner"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    sort: str = Query(
        "-gap",
        description="İzinli: gap, -gap, PartCode, -PartCode, PartName, -PartName, PartID, -PartID",
    ),
    db: Session = Depends(get_db),
):
    """
    SuggestQty = max(MinStock - CurrentStock, 0)
    """
    cs = func.coalesce(Part.CurrentStock, 0)
    ms = func.coalesce(Part.MinStock, 0)
    gap_expr = (ms - cs)

    sort_map = {
        "gap": gap_expr,
        "-gap": desc(gap_expr),
        "PartCode": Part.PartCode,
        "-PartCode": desc(Part.PartCode),
        "PartName": Part.PartName,
        "-PartName": desc(Part.PartName),
        "PartID": Part.PartID,
        "-PartID": desc(Part.PartID),
    }
    order_by_clause = sort_map.get(sort, desc(gap_expr))

    base_q = (
        db.query(Part)
          .filter(Part.IsActive == True)
          .filter(gap_expr >= min_gap)
    )

    total = base_q.count()
    rows = (
        base_q
        .order_by(order_by_clause)
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for p in rows:
        min_stock = int(p.MinStock or 0)
        cur_stock = int(p.CurrentStock or 0)
        gap = max(min_stock - cur_stock, 0)
        result.append({
            "PartID": p.PartID,
            "PartCode": p.PartCode,
            "PartName": p.PartName,
            "Unit": p.Unit,
            "MinStock": min_stock,
            "CurrentStock": cur_stock,
            "Gap": gap,
            "SuggestQty": gap
        })

    return {"value": result, "Count": total}


# --- Tekil Parça Detayı (çakışmasın diye /id/{part_id}) ---
@router.get("/id/{part_id}", dependencies=[Depends(Guard)])
def get_part(part_id: int, db: Session = Depends(get_db)):
    """
    Tek parça detayı döner.
    Örnek yanıt:
    {
      "PartID": 1, "PartCode": "...", "PartName": "...",
      "Unit": "adet", "MinStock": 100, "CurrentStock": 42, "IsActive": true
    }
    """
    p = (
        db.query(Part)
        .filter(Part.PartID == part_id)
        .filter(Part.IsActive == True)  # noqa: E712
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Part not found")

    return {
        "PartID": p.PartID,
        "PartCode": p.PartCode,
        "PartName": p.PartName,
        "Unit": p.Unit,
        "MinStock": int(p.MinStock or 0),
        "CurrentStock": int(p.CurrentStock or 0),
        "IsActive": bool(p.IsActive),
    }
