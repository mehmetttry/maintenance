from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import (
    hash_password, verify_password, create_access_token, get_current_user, require_roles
)
from ..models.user import AppUser
from ..schemas.user import UserCreate, UserRead, Token

router = APIRouter(prefix="/auth", tags=["auth"])

# ---- Model alan adları için esnek saptama ----
PW_FIELD = "HashedPassword" if hasattr(AppUser, "HashedPassword") else (
    "PasswordHash" if hasattr(AppUser, "PasswordHash") else None
)
if PW_FIELD is None:
    raise RuntimeError("AppUser: 'HashedPassword' ya da 'PasswordHash' alanı bulunamadı.")

def _get_user_password_value(user: AppUser) -> Optional[str]:
    return getattr(user, PW_FIELD, None)

def _set_user_password_value(user: AppUser, hashed: str) -> None:
    setattr(user, PW_FIELD, hashed)

# ID alanı olası adları
ID_CANDIDATES = ["UserID", "ID", "UserId"]

def _serialize_user(u: AppUser) -> dict:
    # ID için olası adlardan ilk bulunanı kullan
    uid = None
    for cand in ID_CANDIDATES:
        if hasattr(u, cand):
            uid = getattr(u, cand)
            break
    return {
        "UserID": uid,
        "Username": getattr(u, "Username", None),
        "FullName": getattr(u, "FullName", None),
        "Email": getattr(u, "Email", None),
        "Role": getattr(u, "Role", None),
        "IsActive": getattr(u, "IsActive", None),
    }

ALLOWED_ROLES = {"viewer", "operator", "tech", "store", "admin"}

# ---- Uçlar ----
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    username = payload.username.strip()
    full_name = payload.full_name.strip() if payload.full_name else None
    email = (payload.email or None)
    if email:
        email = email.strip().lower()

    # İstekten rol al (varsa), yoksa viewer
    role = (getattr(payload, "role", None) or "viewer").strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Geçersiz rol: '{role}'. İzin verilen roller: {sorted(list(ALLOWED_ROLES))}")

    if db.query(AppUser).filter(AppUser.Username == username).first():
        raise HTTPException(status_code=400, detail="kullanıcı adı zaten mevcut")
    if email and db.query(AppUser).filter(AppUser.Email == email).first():
        raise HTTPException(status_code=400, detail="email zaten mevcut")

    user = AppUser(
        Username=username,
        FullName=full_name,
        Email=email,
        Role=role,
        IsActive=True,
    )
    _set_user_password_value(user, hash_password(payload.password))

    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = form.username.strip()
    user = db.query(AppUser).filter(AppUser.Username == username).first()

    hashed = _get_user_password_value(user) if user else None
    if (not user) or (not hashed) or (not verify_password(form.password, hashed)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="kullanıcı adı/şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(sub=user.Username, role=user.Role)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def me(current: AppUser = Depends(get_current_user)):
    return _serialize_user(current)

# ---- Admin-only test ucu (rol guard) ----
@router.get("/admin-ping")
def admin_ping(current: AppUser = Depends(require_roles("admin"))):
    return {"ok": True, "msg": f"Hello admin {current.Username}"}
