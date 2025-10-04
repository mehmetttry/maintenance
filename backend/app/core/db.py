import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import dotenv_values, load_dotenv, find_dotenv

# Proje kökü ve .env yolu
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DOTENV = os.path.join(BASE_DIR, ".env")

def _norm_key(k: str) -> str:
    # BOM ve fazladan boşlukları temizle
    return k.replace("\ufeff", "").strip() if isinstance(k, str) else k

# .env yolunu bul
dotenv_path = DEFAULT_DOTENV if os.path.exists(DEFAULT_DOTENV) else find_dotenv(filename=".env", usecwd=True)

# .env içeriğini BOM duyarlı şekilde oku ve ortam değişkenlerine enjekte et
if dotenv_path:
    cfg = dotenv_values(dotenv_path, encoding="utf-8-sig")  # <- BOM'u yutar
    normalized = {}
    for k, v in cfg.items():
        nk = _norm_key(k)
        normalized[nk] = v
        if v is not None and (nk not in os.environ or not os.environ[nk].strip()):
            os.environ[nk] = v
    # (opsiyonel) load_dotenv – override=False bırakıyoruz
    load_dotenv(dotenv_path, override=False)

DSN = os.environ.get("MSSQL_DSN")
if not DSN or not DSN.strip():
    raise RuntimeError(
        "MSSQL_DSN tanımlı değil ya da boş (.env/ortam). "
        f"Denediğim .env: {dotenv_path or '(bulunamadı)'}"
    )

# Dialect'e göre engine argümanlarını ayarla
dsn_lower = DSN.lower()
is_mssql = dsn_lower.startswith("mssql") or "pyodbc" in dsn_lower

engine_kwargs = dict(
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# MSSQL + pyodbc ise hız için aktif, diğerlerinde VERME
if is_mssql:
    engine_kwargs["fast_executemany"] = True
elif dsn_lower.startswith("sqlite"):
    # SQLite için thread hatalarını önle
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DSN, **engine_kwargs)


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
