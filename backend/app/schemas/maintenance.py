# app/schemas/maintenance.py
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field

# Tek tip durum kümesi (bu dosyada tanımlayalım)
StatusLiteral = Literal["Open", "InProgress", "Closed"]

# ---- Requests ----
class RequestCreate(BaseModel):
    MachineID: int
    OpenedBy: Optional[str] = None
    Priority_s: Optional[int] = Field(default=None, ge=1, le=5)
    Description_s: Optional[str] = None

class RequestOut(BaseModel):
    RequestID: int
    MachineID: int
    OpenedAt: datetime
    OpenedBy: Optional[str]
    Priority_s: Optional[int]
    Status_s: StatusLiteral
    Description_s: Optional[str]
    model_config = ConfigDict(from_attributes=True)

# ---- WorkOrders ----
class WorkOrderCreate(BaseModel):
    RequestID: int
    TechnicianID: int
    Notes: Optional[str] = None

class WorkOrderOut(BaseModel):
    WorkOrderID: int
    RequestID: int
    TechnicianID: Optional[int]
    OpenedAt: datetime
    ClosedAt: Optional[datetime]
    Status_s: StatusLiteral
    Notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
