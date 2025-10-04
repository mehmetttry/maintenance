from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, SmallInteger, CheckConstraint, text
from sqlalchemy.orm import relationship
from ..core.db import Base

class MaintenanceRequest(Base):
    __tablename__ = "MaintenanceRequest"

    RequestID     = Column(Integer, primary_key=True, autoincrement=True)
    MachineID     = Column(Integer, ForeignKey("Machine.MachineID"), nullable=False)
    OpenedAt      = Column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    OpenedBy      = Column(String(100))
    Priority_s    = Column(SmallInteger)
    Status_s      = Column(String(20), nullable=False, server_default=text("'Open'"))
    Description_s = Column(String(1000))

    __table_args__ = (
        CheckConstraint("Status_s in ('Open','InProgress','Closed')", name="CK_Request_Status"),
    )

    # 1-1 ilişki (aynı talebe ikinci WO yasak)
    workorder = relationship("WorkOrder", back_populates="request", uselist=False)

    # Makine ilişkisi (tek yönlü; istersen Machine tarafına back_populates ekleyebiliriz)
    machine = relationship("Machine")

    # machine = relationship("Machine")
    machine = relationship("Machine", back_populates="requests")
