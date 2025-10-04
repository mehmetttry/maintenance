from sqlalchemy import Column, Integer, String, Date, Boolean, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class Machine(Base):
    __tablename__ = "Machine"

    MachineID = Column(Integer, primary_key=True, autoincrement=True)
    Code      = Column(String(50),  nullable=False, unique=True)
    Name      = Column(String(200), nullable=False)
    Location  = Column(String(200))
    CommissionDate = Column(Date)
    IsActive  = Column(Boolean,     nullable=False, server_default=text("1"))

    # 1 makine -> N talep
    requests = relationship(
        "MaintenanceRequest",
        back_populates="machine",
        cascade="all, delete-orphan"
    )
