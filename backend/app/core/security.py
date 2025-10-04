# backend/app/core/security.py
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .db import get_db
from ..models.user import AppUser  # ALLOWED_ROLES gerekirse ekle

# OpenAPI için şema kalsın (login formuna dair dokümantasyon)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Parola hash kalıbı
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ---- Parola yardımcıları ----
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

# ---- JWT üretimi ----
def create_access_token(sub: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": sub, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ---- Authorization başlığını toleranslı çöz ----
def _extract_bearer_token(request: Request) -> str:
    """
    'Authorization' başlığını esnek parse eder:
      - Fazladan boşluklar: "Bearer   <JWT>"
      - Üst üste 'Bearer': "Bearer Bearer <JWT>"
      - Tırnaklı değer:    Authorization: "Bearer <JWT>"
    """
    auth = request.headers.get("Authorization")
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulaması gerekli",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not auth:
        raise cred_exc

    auth = str(auth).strip().strip('"').strip("'")
    scheme, param = get_authorization_scheme_param(auth)

    if not scheme or scheme.lower() != "bearer":
        raise cred_exc

    token = (param or "").strip()

    # "Bearer Bearer <JWT>" vakası
    if token.lower().startswith("bearer "):
        token = token.split(None, 1)[1].strip()

    # Çift/çoklu boşlukları temizle (JWT içinde boşluk olmamalı)
    token = token.replace(" ", "")

    if not token:
        raise cred_exc

    return token

# ---- Token'dan kullanıcıyı çöz ----
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(_extract_bearer_token),
) -> AppUser:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulaması gerekli",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get("sub")
        if not username:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = db.query(AppUser).filter(AppUser.Username == username).first()
    if not user or not user.IsActive:
        raise cred_exc
    return user

# ---- Rol kontrol bağımlılığı ----
def require_roles(*roles: str):
    UserDep = Annotated[AppUser, Depends(get_current_user)]
    def _dep(current: UserDep) -> AppUser:
        if current.Role not in roles:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkin yok")
        return current
    return _dep
