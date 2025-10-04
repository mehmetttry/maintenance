from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.maintenance_service import create_request, list_requests

router = APIRouter(prefix="/requests", tags=["requests"])

class RequestIn(BaseModel):
    MachineID: int
    OpenedBy: Optional[str] = None
    Priority_s: Optional[int] = None
    Description_s: Optional[str] = None

@router.post("", status_code=201)
def create_request_ep(body: RequestIn, db: Session = Depends(get_db)):
    return create_request(
        db,
        machine_id=body.MachineID,
        opened_by=body.OpenedBy,
        priority=body.Priority_s,
        description=body.Description_s,
    )

@router.get("", response_model=List[dict])
def list_requests_ep(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    rows = list_requests(db, status_s=status)
    # hızlı dönüş: dict listesi
    return [
        {
            "RequestID": r.RequestID,
            "MachineID": r.MachineID,
            "OpenedAt": r.OpenedAt,
            "OpenedBy": r.OpenedBy,
            "Priority_s": r.Priority_s,
            "Status_s": r.Status_s,
            "Description_s": r.Description_s,
        }
        for r in rows
    ]
