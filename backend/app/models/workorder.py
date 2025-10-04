from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class WorkOrder(Base):
    __tablename__ = "WorkOrder"

    WorkOrderID  = Column(Integer, primary_key=True, autoincrement=True)
    RequestID    = Column(Integer, ForeignKey("MaintenanceRequest.RequestID"), nullable=False)
    TechnicianID = Column(Integer, ForeignKey("Technician.TechnicianID"), nullable=False)
    OpenedAt     = Column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    ClosedAt     = Column(DateTime)
    Notes        = Column(String(1000))
    Status_s     = Column(String(20), nullable=False, server_default=text("'Open'"))

    __table_args__ = (
        CheckConstraint("Status_s in ('Open','InProgress','Closed')", name="CK_WO_Status"),
        UniqueConstraint('RequestID', name='UQ_WorkOrder_RequestID'),
    )

    # İlişkiler
    request    = relationship("MaintenanceRequest", back_populates="workorder")
    technician = relationship("Technician",        back_populates="workorders")
    txns       = relationship("WarehouseTxn",      back_populates="workorder")
