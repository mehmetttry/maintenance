from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic import ConfigDict

class WarehouseTxnCreate(BaseModel):
    PartID: int = Field(..., ge=1)
    TxnType: Literal["IN", "OUT"]
    Quantity: int = Field(..., gt=0)
    Reason: Optional[str] = None
    WorkOrderID: Optional[int] = None

class WarehouseTxnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM objelerini dönerken işe yarar
    TxnID: int
    PartID: int
    TxnType: str
    Quantity: int
