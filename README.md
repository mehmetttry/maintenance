# ToraMakina – Bakım ve Stok Yönetim Sistemi

Bu proje, bir atölyedeki bakım süreçlerini ve stok yönetimini dijitalleştirmek amacıyla geliştirilmiştir.

- **Backend:** FastAPI, SQLAlchemy, Alembic  
- **Database:** Microsoft SQL Server (MSSQL)  
- **Frontend:** Streamlit  
- **Testing:** Pytest  
- **Deployment:** Uvicorn  

##  Özellikler
- Makine ve teknisyen yönetimi  
- Bakım talepleri & iş emirleri oluşturma  
- Stok giriş/çıkış işlemleri  
- Satınalma önerileri  
- Raporlama (en çok arıza veren makine, min stok altı parçalar vb.)

## Kurulum
```bash
# ortamı oluştur
python -m venv .venv
source .venv/Scripts/activate  # (Windows için)
pip install -r requirements.txt
