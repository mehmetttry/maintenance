from sqlalchemy import Column, Integer, String, Boolean, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class Part(Base):
    __tablename__ = "Part"

    PartID       = Column(Integer, primary_key=True, autoincrement=True)
    PartCode     = Column(String(50),  nullable=False, unique=True)
    PartName     = Column(String(200), nullable=False)
    Unit         = Column(String(10),  nullable=False)
    MinStock     = Column(Integer,     nullable=False, server_default=text("0"))
    CurrentStock = Column(Integer,     nullable=False, server_default=text("0"))
    IsActive     = Column(Boolean,     nullable=False, server_default=text("1"))

    # Depo hareketleri
    txns = relationship("WarehouseTxn", back_populates="part")

    # PurchaseOrder ilişkisi (eksikti → eklendi)
    purchase_orders = relationship("PurchaseOrder", back_populates="part")
