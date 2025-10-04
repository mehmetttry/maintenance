# backend/app/core/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url
from dotenv import dotenv_values, load_dotenv, find_dotenv

# Proje kökü ve .env yolu
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DOTENV = os.path.join(BASE_DIR, ".env")

def _norm_key(k: str) -> str:
    return k.replace("\ufeff", "").strip() if isinstance(k, str) else k

# .env yolunu bul ve ortamı yükle (CI’daki env’i ezmeden)
dotenv_path = DEFAULT_DOTENV if os.path.exists(DEFAULT_DOTENV) else find_dotenv(filename=".env", usecwd=True)
if dotenv_path:
    cfg = dotenv_values(dotenv_path, encoding="utf-8-sig")
    for k, v in cfg.items():
        nk = _norm_key(k)
        if v is not None and (nk not in os.environ or not os.environ[nk].strip()):
            os.environ[nk] = v
    load_dotenv(dotenv_path, override=False)

DSN = os.environ.get("MSSQL_DSN") or os.environ.get("DATABASE_URL")
if not DSN or not DSN.strip():
    raise RuntimeError(f"MSSQL_DSN / DATABASE_URL tanımlı değil. .env: {dotenv_path or '(bulunamadı)'}")

url = make_url(DSN)
engine_kwargs = dict(pool_pre_ping=True)

# Dialect'e göre güvenli ayarlar
backend = url.get_backend_name()  # örn: 'sqlite', 'mssql'
if backend.startswith("sqlite"):
    # SQLite'ta thread check'i kapat, pool boyutu argümanları verme
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif backend.startswith("mssql"):
    # Sadece mssql+pyodbc için hızlı bulk ve pool ayarları
    engine_kwargs.update(pool_size=5, max_overflow=10, fast_executemany=True)

engine = create_engine(DSN, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
