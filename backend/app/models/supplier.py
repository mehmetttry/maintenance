from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..core.db import Base

class Supplier(Base):
    __tablename__ = "Supplier"

    SupplierID   = Column(Integer, primary_key=True, autoincrement=True)
    # DB’de kolon adı "Name", biz attr olarak SupplierName kullanıyoruz
    SupplierName = Column("Name", String(200), nullable=False)
    Phone        = Column(String(50))
    Email        = Column(String(200))

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
