from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError, IntegrityError
from fastapi import HTTPException

from app.models import Machine, MaintenanceRequest, Technician, WorkOrder

# SQLAlchemy 1.3/1.4 uyumlu get
def _get(db: Session, model, pk):
    get_fn = getattr(db, "get", None)
    if callable(get_fn):
        return get_fn(model, pk)           # SA 1.4+
    return db.query(model).get(pk)          # SA 1.3

# -------- Requests --------
def create_request(
    db: Session, *,
    machine_id: int,
    opened_by: Optional[str],
    priority: Optional[int],
    description: Optional[str],
):
    try:
        if not _get(db, Machine, machine_id):
            raise HTTPException(status_code=404, detail="Machine not found")

        req = MaintenanceRequest(
            MachineID=machine_id,
            OpenedBy=opened_by,
            Priority_s=priority,
            Description_s=description,
            OpenedAt=datetime.utcnow(),   # DB default olmasa da boş gitmez
            Status_s="Open",
        )
        db.add(req)
        db.flush()
        db.commit()
        db.refresh(req)
        return req
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, DBAPIError) as e:
        db.rollback()
        msg = str(getattr(e, "orig", e))
        raise HTTPException(status_code=400, detail=f"db_error: {msg}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"create_request_error: {e!r}")

def list_requests(db: Session, *, status_s: Optional[str]):
    q = db.query(MaintenanceRequest)
    if status_s:
        q = q.filter(MaintenanceRequest.Status_s == status_s)
    return q.order_by(MaintenanceRequest.RequestID.desc()).all()

# -------- WorkOrders --------
def create_workorder(
    db: Session, *,
    request_id: int,
    technician_id: int,
    notes: Optional[str],
):
    try:
        req = _get(db, MaintenanceRequest, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.Status_s == "Closed":
            raise HTTPException(status_code=409, detail="Request already closed")

        if db.query(WorkOrder).filter(WorkOrder.RequestID == request_id).first():
            raise HTTPException(status_code=409, detail="WorkOrder already exists for this request")

        tech = _get(db, Technician, technician_id)
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found")

        wo = WorkOrder(RequestID=request_id, TechnicianID=technician_id, Notes=notes)
        db.add(wo)
        req.Status_s = "InProgress"
        db.flush()
        db.commit()
        db.refresh(wo)
        return wo
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, DBAPIError) as e:
        db.rollback()
        msg = str(getattr(e, "orig", e))
        raise HTTPException(status_code=400, detail=f"db_error: {msg}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"create_workorder_error: {e!r}")

def close_workorder(db: Session, *, workorder_id: int):
    try:
        wo = _get(db, WorkOrder, workorder_id)
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.ClosedAt is not None:
            raise HTTPException(status_code=409, detail="WorkOrder is already closed")

        wo.ClosedAt = datetime.utcnow()
        wo.Status_s = "Closed"
        if wo.request and wo.request.Status_s != "Closed":
            wo.request.Status_s = "Closed"

        db.flush()
        db.commit()
        db.refresh(wo)
        return wo
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, DBAPIError) as e:
        db.rollback()
        msg = str(getattr(e, "orig", e))
        raise HTTPException(status_code=400, detail=f"db_error: {msg}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"close_workorder_error: {e!r}")
