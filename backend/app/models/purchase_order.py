from sqlalchemy import Column, Integer, String, Date, DECIMAL, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class PurchaseOrder(Base):
    __tablename__ = "PurchaseOrder"

    POID       = Column(Integer, primary_key=True, autoincrement=True)
    SupplierID = Column(Integer, ForeignKey("Supplier.SupplierID"), nullable=False)
    PartID     = Column(Integer, ForeignKey("Part.PartID"),       nullable=False)
    Qty        = Column(Integer,     nullable=False)
    UnitPrice  = Column(DECIMAL(10,2), nullable=False)
    PODate     = Column(Date,        nullable=False, server_default=text("CAST(SYSUTCDATETIME() AS DATE)"))
    ETA        = Column(Date)
    Status_s   = Column(String(20),  nullable=False)

    __table_args__ = (
        CheckConstraint("Qty > 0", name="CK_PO_Qty_Positive"),
        CheckConstraint("UnitPrice > 0", name="CK_PO_UnitPrice_Positive"),
        CheckConstraint("Status_s IN ('Created','Ordered','Received','Canceled')", name="CK_PO_Status"),
    )

    # Çift yönlü ilişkiler
    supplier = relationship("Supplier", back_populates="purchase_orders")
    part     = relationship("Part",     back_populates="purchase_orders")
