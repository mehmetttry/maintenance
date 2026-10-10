# ToraMakina – Bakım ve Stok Yönetim Sistemi

Atölyedeki bakım taleplerini, iş emirlerini, yedek parça stoğunu ve satınalma emirlerini tek bir veritabanında izlemek için geliştirilmiş bir web uygulaması. Staj kapsamında, yönlendirmeyle geliştirilmiştir; eğitim amaçlıdır.

Uygulama iki parçadan oluşur:

- **API (`backend/`)**: FastAPI + SQLAlchemy. Veritabanı Microsoft SQL Server; şema Alembic migration'larıyla yönetilir.
- **Arayüz (`frontend/`)**: Streamlit. API'ye HTTP üzerinden bağlanır, JWT ile kimlik doğrular.

## Özellikler

- **Bakım:** bakım talebi açma ve listeleme (`/requests`), talepten iş emri oluşturma ve iş emri kapatma (`/workorders`).
- **Stok:** parça sorgulama (`/parts/id/{id}`), minimum stok altındaki parçalar (`/parts/below-min`), sipariş önerisi (`/parts/reorder-suggestion`), depo giriş/çıkış hareketleri (`/warehouse/in`, `/warehouse/out`, `/warehouse/txns`).
- **Satınalma:** satınalma emri oluşturma (elle veya sipariş önerisinden), durum geçişleri `Created → Ordered → Received` ve iptal (`/purchase-orders/{id}/place | receive | cancel`). Teslim alınan emir depoya giriş hareketi olarak işlenir.
- **Raporlar:** en çok arıza veren makineler, en çok tüketilen parçalar, açık iş emirlerinin yaşlandırması (`/reports/...`).
- **Kimlik doğrulama ve roller:** `/auth/register`, `/auth/login` (OAuth2 form, JWT), `/auth/me`. Roller: `viewer`, `operator`, `tech`, `store`, `admin`. Parça, depo ve satınalma uçları `store` veya `admin` rolü ister.
- **Tutarlı yanıt formatı:** hatalar ve liste yanıtları ortak bir zarf (envelope) yapısıyla döner (`backend/app/core/api.py`).

## Teknoloji Yığını

| Katman | Kullanılan |
|---|---|
| API | FastAPI, Uvicorn, Pydantic v2 |
| Veri erişimi | SQLAlchemy 2, Alembic |
| Veritabanı | Microsoft SQL Server (pyodbc, ODBC Driver 18) |
| Kimlik doğrulama | python-jose (JWT), passlib + bcrypt |
| Arayüz | Streamlit, pandas, Plotly, Altair |
| Test / CI | pytest, PowerShell smoke testleri, GitHub Actions |

## Gereksinimler

- Python 3.11 (CI bu sürümle çalışır)
- Microsoft SQL Server (örnek bağlantı `localhost\SQLEXPRESS`)
- [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)

## Kurulum

```bash
git clone https://github.com/mehmetttry/maintenance.git
cd maintenance

python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` hem API hem arayüz bağımlılıklarını kurar. Yalnızca API gerekiyorsa `pip install -r backend/requirements.txt` yeterlidir.

### Ortam değişkenleri

`.env.example` dosyasını proje köküne `.env` olarak kopyalayın ve değerleri doldurun:

```bash
cp .env.example .env
```

| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `MSSQL_DSN` | Evet* | SQLAlchemy bağlantı adresi. Örnek Windows kimlik doğrulamasıyla (`trusted_connection=yes`) bağlanır. |
| `DATABASE_URL` | Hayır* | `MSSQL_DSN` yoksa bu kullanılır. *İkisinden biri tanımlı olmalı, aksi halde API başlamaz. |
| `JWT_SECRET` | Evet | JWT imzalama anahtarı. Tanımlanmazsa koddaki geliştirme varsayılanı kullanılır; gerçek ortamda mutlaka değiştirin. |
| `JWT_ALG` | Hayır | Varsayılan `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Hayır | Varsayılan `60`. |
| `API_BASE` | Hayır | Streamlit'in bağlanacağı API adresi. Varsayılan `http://127.0.0.1:8011`. |
| `CORS_ALLOW_ORIGINS` | Hayır | `*`, virgülle ayrılmış liste ya da JSON dizi. Varsayılan `*`. |
| `API_TOKEN` | Hayır | Streamlit ana sayfasındaki jeton alanının varsayılan değeri. |

### Veritabanı şeması

SQL Server'da `ToraMakina` veritabanını (veya DSN'de verdiğiniz adı) oluşturduktan sonra migration'ları uygulayın:

```bash
cd backend
alembic upgrade head
```

Alembic, bağlantı adresini `alembic.ini` yerine uygulamanın kendi ayarından (`app/core/db.py`, yani `MSSQL_DSN`) alır.

İsteğe bağlı örnek veri:

```bash
cd backend
python -m app.scripts.seed
```

## Çalıştırma

API ve arayüz ayrı terminallerde çalışır.

**API** (`backend/` klasöründen; importlar `app.` önekiyle yazıldığı için çalışma dizini `backend` olmalıdır):

```bash
cd backend
uvicorn app.main:app --reload --port 8011
```

- Swagger arayüzü: http://127.0.0.1:8011/docs
- Sağlık kontrolü: `GET /health`, veritabanı kontrolü: `GET /db-ping`

**Streamlit arayüzü** (proje kökünden):

```bash
streamlit run frontend/Home.py
```

Varsayılan adres http://localhost:8501. Kenar çubuğundan API adresi girilir ve kullanıcı adı/parola ile giriş yapılır. Sayfalar: Ana pano, Bakım İşlemleri, Stoklar, Reorder / Satın Alma, Satınalma Emirleri, Raporlar.

## Test

```bash
cd backend
pytest
```

Uçtan uca smoke testleri PowerShell betikleridir ve çalışan bir API'ye istek atar:

```powershell
.\backend\scripts\smoke.ps1 -Base http://127.0.0.1:8011
```

GitHub Actions iş akışı (`.github/workflows/po-receive-smoke.yml`) Windows üzerinde SQLite ile API'yi başlatır ve satınalma emri oluşturma → sipariş → teslim alma akışını, teslimin stoğa tek bir giriş hareketi olarak yansımasını ve ikinci teslim alma isteğinin `409` ile reddedilmesini test eder.

## Klasör Yapısı

```
maintenance/
├── backend/
│   ├── alembic/               # migration ortamı ve sürümleri
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py            # FastAPI uygulaması (giriş noktası)
│   │   ├── core/              # db bağlantısı, JWT/rol kontrolü, yanıt zarfı
│   │   ├── models/            # SQLAlchemy modelleri
│   │   ├── schemas/           # Pydantic şemaları
│   │   ├── routers/           # auth, parts, purchase, warehouse, maintenance, workorders, reports
│   │   ├── services/          # iş kuralları (bakım, satınalma, depo)
│   │   ├── domain/            # sabitler
│   │   └── scripts/seed.py    # örnek veri
│   ├── scripts/               # smoke testi, demo veri, grafik ve DDL yardımcı betikleri
│   ├── tests/                 # pytest ve PowerShell smoke testleri
│   └── requirements.txt       # API bağımlılıkları
├── frontend/
│   ├── Home.py                # Streamlit ana pano
│   ├── pages/                 # maintenance, stocks, reorder, purchase_orders, reports
│   └── dashboard.html         # tarayıcıda açılan statik pano (API'ye doğrudan bağlanır)
├── .github/workflows/         # CI smoke testi
├── .env.example
├── requirements.txt           # API + arayüz bağımlılıkları
└── LICENSE
```

## Veri Modeli

Tablolar: `Machine`, `Technician`, `MaintenanceRequest`, `WorkOrder`, `Part`, `WarehouseTxn`, `Supplier`, `PurchaseOrder`, `AppUser`.

## Lisans

MIT. Ayrıntılar için `LICENSE` dosyasına bakın.
