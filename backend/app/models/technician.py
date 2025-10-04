from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..core.db import Base

class Technician(Base):
    __tablename__ = "Technician"

    TechnicianID = Column(Integer, primary_key=True, autoincrement=True)

    # DB'de sütun adı FullName; Python tarafında Name olarak kullan
    Name       = Column("FullName", String(200), nullable=False)

    # DB'de mevcut sütunlar
    SkillLevel = Column(Integer)
    Phone      = Column(String(50))

    # İlişki
    workorders = relationship("WorkOrder", back_populates="technician")
