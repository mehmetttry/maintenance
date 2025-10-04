# app/routers/workorders.py
from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.maintenance import WorkOrderCreate, WorkOrderOut
from app.services.maintenance_service import create_workorder, close_workorder
from app.models import WorkOrder  # mevcut modellerden import

router = APIRouter(prefix="/workorders", tags=["Work Orders"])

@router.post("", response_model=WorkOrderOut)
def create_wo(payload: WorkOrderCreate, db: Session = Depends(get_db)):
    # --- EKLENDİ: aynı RequestID için ikinci iş emri engeli ---
    existing = db.query(WorkOrder).filter(WorkOrder.RequestID == payload.RequestID).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Bu talep için zaten bir iş emri var (RequestID={payload.RequestID})."
        )
    # -----------------------------------------------------------

    return create_workorder(
        db,
        request_id=payload.RequestID,
        technician_id=payload.TechnicianID,
        notes=payload.Notes,
    )

@router.post("/{workorder_id}/close", response_model=WorkOrderOut)
def close_wo(workorder_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return close_workorder(db, workorder_id=workorder_id)
