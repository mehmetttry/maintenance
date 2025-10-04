from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class WarehouseTxn(Base):
    __tablename__ = "WarehouseTxn"

    TxnID       = Column(Integer, primary_key=True, autoincrement=True)
    PartID      = Column(Integer, ForeignKey("Part.PartID"), nullable=False)
    TxnType     = Column(String(3), nullable=False)  # 'IN' | 'OUT'
    Quantity    = Column(Integer, nullable=False)
    TxnDate     = Column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    Reason      = Column(String(100))
    WorkOrderID = Column(Integer, ForeignKey("WorkOrder.WorkOrderID"))

    __table_args__ = (
        CheckConstraint("TxnType IN ('IN','OUT')", name="CK_WTxn_TxnType"),
        CheckConstraint("Quantity > 0",            name="CK_WTxn_Quantity_Positive"),
    )

    # SADECE back_populates kullan
    part      = relationship("Part",      back_populates="txns")
    workorder = relationship("WorkOrder", back_populates="txns")
