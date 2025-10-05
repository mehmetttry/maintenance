# ToraMakina – Bakım & Stok Yönetim Sistemi

Atölyelerde bakım süreçlerini ve stok takibini dijitalleştirmek için geliştirilmiştir. 
Staj kapsamında yönlendirmeyle geliştirilmiş; eğitim amaçlıdır.

## Teknoloji Yığını
- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Database:** Microsoft SQL Server (MSSQL + ODBC Driver 18)
- **Frontend:** Streamlit
- **Testing:** Pytest
- **Server:** Uvicorn
- **CI :** GitHub Actions (smoke workflow)

## Modüller
- **Bakım:** MaintenanceRequest, WorkOrder (talep → iş emri, atama, kapatma)
- **Stok:** Part, WarehouseTxn (IN/OUT, min stok altı uyarıları)
- **Satınalma:** Supplier, PurchaseOrder (Created/Ordered/Received)
- **Raporlar:** En çok arıza veren makine, en çok tüketilen parça, açık iş emirleri

## Roller
viewer · operator · tech · store · admin

## Kurulum
```bash
# 1) Sanal ortam
python -m venv .venv
# Windows için
.\.venv\Scripts\activate
# 2) Bağımlılıklar
pip install -r requirements.txt
```

### .env
`.env.example` dosyasını kopyalayıp `.env` olarak kaydedin ve değerleri doldurun:
```
MSSQL_DSN="mssql+pyodbc://@localhost\\SQLEXPRESS/ToraMakina?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"
JWT_SECRET="replace-with-a-strong-random-secret"
JWT_ALG="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
API_BASE="http://127.0.0.1:8011"
# CORS_ALLOW_ORIGINS="*"
```


## Çalıştırma
```bash
# Backend (API)
uvicorn backend.app.main:app --reload --port 8011

# Frontend (UI)
streamlit run frontend/Home.py
```
- API Dokümanları: http://127.0.0.1:8011/docs  
- Uygulama: http://127.0.0.1:8501
  

## Proje Yapısı (özet)
```
maintenance/
  backend/
    app/
      models/  routers/  services/  repositories/  schemas/  core/
      main.py
    alembic/
  frontend/
    Home.py
    pages/ (stocks.py, maintenance.py, reports.py)
  .env.example
  README.md
```

## 📄 Lisans
MIT – Ayrıntı için LICENSE dosyasına bakın.
