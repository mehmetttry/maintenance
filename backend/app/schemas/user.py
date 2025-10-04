from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict

RoleLiteral = Literal["viewer", "operator", "tech", "store", "admin"]

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6, max_length=128)
    role: Optional[RoleLiteral] = "viewer"   # 👈 rol artık register sırasında geçilebilir

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    UserID: int
    Username: str
    FullName: Optional[str]
    Email: Optional[EmailStr]
    Role: RoleLiteral
    IsActive: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
