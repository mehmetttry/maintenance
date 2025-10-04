from fastapi.testclient import TestClient
from app.main import app

def test_health_ok():
    with TestClient(app) as c:
        r = c.get("/health")

    assert r.status_code == 200

    # JSON ya da düz metin dönse de kabul edecek şekilde kontrol et
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        data = r.json()
        assert isinstance(data, dict)
        # {"ok": true} benzeri
        assert data.get("ok") is True
    else:
        text = (r.text or "").lower()
        assert "ok" in text or "true" in text
