from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, CheckConstraint, text
)
from ..core.db import Base

ALLOWED_ROLES = ("viewer", "operator", "tech", "store", "admin")

class AppUser(Base):
    __tablename__ = "AppUser"

    UserID         = Column(Integer, primary_key=True, autoincrement=True)
    Username       = Column(String(50),  nullable=False, unique=True)
    FullName       = Column(String(100))
    # unique=True KALDIRILDI
    Email          = Column(String(200))
    HashedPassword = Column(String(255), nullable=False)
    # server_default güvenli biçimde SQL ifadesiyle verildi
    Role           = Column(String(20),  nullable=False, server_default=text("'viewer'"))
    IsActive       = Column(Boolean,     nullable=False, server_default=text("1"))
    CreatedAt      = Column(DateTime,    nullable=False, server_default=text("SYSDATETIME()"))

    __table_args__ = (
        CheckConstraint(
            "Role in ('viewer','operator','tech','store','admin')",
            name="CK_AppUser_Role"
        ),
    )