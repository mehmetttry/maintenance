# frontend/pages/reorder.py
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Reorder / Satın Alma", layout="wide")

# ---------------- Helpers ----------------
def _normalize_token(raw) -> str:
    s = str(raw or "").strip().strip('"').strip("'")
    if not s:
        return ""
    if s.lower().startswith("bearer "):
        s = s.split(" ", 1)[1].strip()
    return s

def get_api_base_and_token():
    api_base = st.session_state.get("api_base") or os.getenv("API_BASE", "http://127.0.0.1:8011")
    token = _normalize_token(st.session_state.get("jwt", ""))
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    return api_base.rstrip("/"), token, hdrs

def get_json(url: str, hdrs: dict):
    r = requests.get(url, headers=hdrs, timeout=20)
    r.raise_for_status()
    return r.json()

def post_json(url: str, hdrs: dict, payload: dict):
    r = requests.post(url, headers={**hdrs, "Content-Type": "application/json"}, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def ensure_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        # {"ok":true,"data":[...]}  |  {"items":[...]}  |  {"value":[...]}
        for k in ("data", "items", "value"):
            if isinstance(x.get(k), list):
                return x[k]
    return []

def toast(msg: str, icon: str = "✅"):
    try:
        st.toast(msg, icon=icon)
    except Exception:
        st.success(msg)

def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# ---------------- UI ----------------
st.title("🛒 Reorder / Satın Alma")
API_BASE, TOKEN, HDRS = get_api_base_and_token()

with st.sidebar:
    st.info(f"API: {API_BASE}")
    st.write("JWT:", "✅ Var" if TOKEN else "❌ Yok")

# ---- 1) Öneriler ----
st.subheader("📌 Reorder Önerileri")
suggest_raw = None
try:
    suggest_raw = get_json(f"{API_BASE}/parts/reorder-suggestion", HDRS)
except requests.HTTPError as e:
    st.error(f"Öneriler alınamadı: {e.response.status_code} — {e.response.text[:160]}")
except requests.RequestException as e:
    st.error(f"Ağ hatası: {e}")

rows = ensure_list(suggest_raw) if suggest_raw is not None else []
df = pd.DataFrame(rows)

if df.empty:
    st.info("Şu anda reorder önerisi yok gibi görünüyor.")
else:
    # Sütun isimlerini kullanıcı dostu hale getir
    rename_map = {
        "PartID": "ParçaID",
        "PartCode": "Kod",
        "PartName": "Ad",
        "CurrentStock": "Mevcut",
        "MinStock": "Min",
        # Muhtemel öneri miktarı alanları:
        "SuggestedQty": "Öneri",
        "ReorderQty": "Öneri",
        "Qty": "Öneri",
        "NeedQty": "Öneri",
    }
    df_disp = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    st.dataframe(df_disp, use_container_width=True, height=320)

    # Seçim ve toplu PO oluşturma
    st.markdown("**Seçilen satırlar için PO oluştur**")
    idx_sel = st.multiselect("Satır seç", options=list(df.index), help="CTRL/SHIFT ile birden fazla seçebilirsin.")
    c1, c2, c3 = st.columns([1,1,2])
    supplier_id = c1.number_input("SupplierID", min_value=1, step=1, value=1)
    default_price = c2.number_input("Birim Fiyat (varsayılan)", min_value=0.01, step=0.01, value=1.00, format="%.2f")
    create_clicked = c3.button("Seçili satırlar için PO oluştur", type="primary", use_container_width=True)

    def _pick_qty(row: dict) -> int:
        for key in ("SuggestedQty", "ReorderQty", "NeedQty", "Qty"):
            if key in row and row[key] is not None:
                try:
                    q = int(row[key])
                    if q > 0: return q
                except Exception:
                    pass
        return 1

    if create_clicked:
        if not idx_sel:
            st.warning("Satır seçmedin.")
        else:
            created = []
            errors = []
            for i in idx_sel:
                row = df.loc[i].to_dict()
                part_id = int(row.get("PartID") or row.get("partId") or 0)
                if part_id <= 0:
                    errors.append(f"Satır {i}: PartID yok/0")
                    continue
                qty = _pick_qty(row)
                price = float(row.get("UnitPrice") or default_price)

                payload = {
                    "SupplierID": int(supplier_id),
                    "PartID": part_id,
                    "Qty": int(qty),
                    "UnitPrice": price,
                }
                try:
                    res = post_json(f"{API_BASE}/purchase-orders", HDRS, payload)
                    # Cevap düz objeyse POID direkt olabilir; yoksa data.POID dene
                    poid = res.get("POID") or (res.get("data", {}) if isinstance(res.get("data"), dict) else {}).get("POID")
                    created.append(poid or "?")
                except requests.RequestException as e:
                    errors.append(f"Satır {i}: {e}")
            if created:
                toast(f"PO oluşturuldu: #{', #'.join(map(str, created))}")
            if errors:
                st.error("Bazı satırlar hata verdi:\n- " + "\n- ".join(map(str, errors)))

# ---- 2) Hızlı PO İşlemleri ----
st.subheader("⚙️ PO Hızlı İşlemler")
c1, c2, c3, c4 = st.columns([1,1,1,3])
poid = c1.number_input("POID", min_value=1, step=1, value=1)
place_clicked = c2.button("Place", use_container_width=True)
receive_clicked = c3.button("Receive", use_container_width=True)
cancel_clicked = c4.button("Cancel", use_container_width=True)

def _call_po_action(action: str):
    try:
        url = f"{API_BASE}/purchase-orders/{int(poid)}/{action}"
        res = post_json(url, HDRS, {})
        toast(f"{action.capitalize()} OK — PO #{int(poid)}")
        _rerun()
    except requests.HTTPError as e:
        st.error(f"{action} HTTP hatası: {e.response.status_code} — {e.response.text[:180]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

if place_clicked: _call_po_action("place")
if receive_clicked: _call_po_action("receive")
if cancel_clicked: _call_po_action("cancel")

st.caption("Not: Bu sayfa için store/admin rolü gerekir.")
