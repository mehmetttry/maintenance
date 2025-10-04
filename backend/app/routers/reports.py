# backend/app/routers/reports.py
from datetime import date, datetime, time, timezone
from typing import List, Optional, Tuple
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder  # <-- EKLENDİ
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    Machine,
    MaintenanceRequest,
    Part,
    WarehouseTxn,
    WorkOrder,
)

# --- Standart API zarfı ---
from app.core.api import ok, list_meta

router = APIRouter(prefix="/reports", tags=["reports"])

# ---------- Ortak: tarih aralığı doğrulaması ----------
def validate_period(
    start: date = Query(..., description="UTC tarih, örn: 2025-08-01"),
    end:   date = Query(..., description="UTC tarih (hariç), örn: 2025-09-01"),
) -> Tuple[date, date]:
    if end <= start:
        raise HTTPException(
            status_code=422,
            detail="Geçersiz aralık: 'end' > 'start' olmalı. Not: 'end' HARIÇ (YYYY-MM-DD).",
        )
    if (end - start).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Aralık çok uzun: en fazla 366 gün.",
        )
    return (start, end)

# =========================
# TOP FAILURE MACHINES
# =========================
class TopFailureItem(BaseModel):
    machineId: int
    machineName: str
    failureCount: int

@router.get("/top-failure-machines")
def top_failure_machines(
    period: Tuple[date, date] = Depends(validate_period),
    top:   int  = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    start, end = period
    start_dt = datetime.combine(start, time.min)
    end_dt   = datetime.combine(end,   time.min)
    try:
        q = (
            db.query(
                Machine.MachineID.label("machineId"),
                Machine.Name.label("machineName"),
                func.count(MaintenanceRequest.RequestID).label("failureCount"),
            )
            .join(MaintenanceRequest, MaintenanceRequest.MachineID == Machine.MachineID)
            .filter(
                MaintenanceRequest.OpenedAt >= start_dt,
                MaintenanceRequest.OpenedAt <  end_dt,
            )
            .group_by(Machine.MachineID, Machine.Name)
            .order_by(desc("failureCount"), Machine.Name)
            .limit(top)
        )
        rows = [dict(r._mapping) for r in q.all()]
        meta = {**list_meta(rows), "start": start.isoformat(), "end": end.isoformat(), "top": top}
        return ok(rows, meta=meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reports/top-failure-machines failed: {e}")

# --- RAW (-list) → KALICI YÖNLENDİRME (301) ---
@router.get("/top-failure-machines-list", include_in_schema=False)
def top_failure_machines_list_redirect(request: Request):
    url = str(request.url).replace("/top-failure-machines-list", "/top-failure-machines")
    return RedirectResponse(url, status_code=301)

# =========================
# TOP CONSUMED PARTS
# =========================
class TopConsumedItem(BaseModel):
    partId: int
    partName: str
    qtyOut: float

@router.get("/top-consumed-parts")
def top_consumed_parts(
    period: Tuple[date, date] = Depends(validate_period),
    top:   int  = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    start, end = period
    start_dt = datetime.combine(start, time.min)
    end_dt   = datetime.combine(end,   time.min)

    subq = (
        db.query(
            WarehouseTxn.PartID.label("PartID"),
            func.sum(WarehouseTxn.Quantity).label("QtyOut"),
        )
        .filter(
            WarehouseTxn.TxnDate >= start_dt,
            WarehouseTxn.TxnDate <  end_dt,
            WarehouseTxn.TxnType == "OUT",
        )
        .group_by(WarehouseTxn.PartID)
    ).subquery()

    q = (
        db.query(
            Part.PartID.label("partId"),
            Part.PartName.label("partName"),
            func.coalesce(subq.c.QtyOut, 0).label("qtyOut"),
        )
        .join(subq, subq.c.PartID == Part.PartID)
        .order_by(desc(func.coalesce(subq.c.QtyOut, 0)), Part.PartName)
        .limit(top)
    )
    rows = [dict(r._mapping) for r in q.all()]
    meta = {**list_meta(rows), "start": start.isoformat(), "end": end.isoformat(), "top": top}
    return ok(rows, meta=meta)

# --- RAW (-list) → KALICI YÖNLENDİRME (301) ---
@router.get("/top-consumed-parts-list", include_in_schema=False)
def top_consumed_parts_list_redirect(request: Request):
    url = str(request.url).replace("/top-consumed-parts-list", "/top-consumed-parts")
    return RedirectResponse(url, status_code=301)

# =========================
# OPEN WORKORDERS AGING — Standart zarf + UTC asOf
# =========================
class AgingItem(BaseModel):
    workOrderId: int
    requestId: int
    machineId: int
    machineName: str
    openedAt: datetime
    ageDays: int
    ageBucket: str

class AgingBucket(BaseModel):
    ageBucket: str
    openWOCount: int

@router.get("/open-workorders-aging")
def open_workorders_aging(
    asOf: Optional[datetime] = Query(None, description="UTC ISO; boş bırakılırsa 'now(UTC)'. Naive verilirse UTC varsayılır."),
    db: Session = Depends(get_db),
):
    as_of = asOf or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    q = (
        db.query(
            WorkOrder.WorkOrderID.label("workOrderId"),
            WorkOrder.RequestID.label("requestId"),
            MaintenanceRequest.MachineID.label("machineId"),
            Machine.Name.label("machineName"),
            WorkOrder.OpenedAt.label("openedAt"),
        )
        .join(MaintenanceRequest, MaintenanceRequest.RequestID == WorkOrder.RequestID)
        .join(Machine, Machine.MachineID == MaintenanceRequest.MachineID)
        .filter(WorkOrder.ClosedAt.is_(None))
        .order_by(WorkOrder.WorkOrderID.desc())
    )

    rows = q.all()

    def bucket(days: int) -> str:
        if days <= 2: return "0-2"
        if days <= 5: return "3-5"
        if days <= 10: return "6-10"
        return ">10"

    items: List[AgingItem] = []
    for r in rows:
        opened = r.openedAt or as_of
        if isinstance(opened, datetime) and opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        age_days = max(0, (as_of - opened).days)
        items.append(AgingItem(
            workOrderId=r.workOrderId,
            requestId=r.requestId,
            machineId=r.machineId,
            machineName=r.machineName,
            openedAt=opened,
            ageDays=age_days,
            ageBucket=bucket(age_days),
        ))

    counts = {"0-2": 0, "3-5": 0, "6-10": 0, ">10": 0}
    for it in items:
        counts[it.ageBucket] = counts.get(it.ageBucket, 0) + 1

    summary = [
        AgingBucket(ageBucket="0-2",  openWOCount=counts["0-2"]),
        AgingBucket(ageBucket="3-5",  openWOCount=counts["3-5"]),
        AgingBucket(ageBucket="6-10", openWOCount=counts["6-10"]),
        AgingBucket(ageBucket=">10",  openWOCount=counts[">10"]),
    ]

    data = {
        "items": [it.model_dump() for it in items],
        "summary": [s.model_dump() for s in summary],
    }
    meta = {
        "asOf": as_of.isoformat(),
        "tz": "UTC",
        "openWOCount": len(items),
    }
    # Datetime içeren yapıyı JSON'a güvenli çevir
    payload = jsonable_encoder(data)
    return ok(payload, meta=meta)
