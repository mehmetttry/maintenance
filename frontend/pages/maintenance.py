# frontend/pages/maintenance.py
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Bakım İşlemleri", layout="wide")

# --- Ortak yardımcılar / durum ---
def get_api():
    api_base = st.session_state.get("api_base") or os.getenv("API_BASE", "http://127.0.0.1:8011")
    api_base = api_base.rstrip("/")
    token = st.session_state.get("jwt", "")
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    return api_base, token, hdrs

def get_json(url: str, hdrs: dict):
    r = requests.get(url, headers=hdrs, timeout=15)
    r.raise_for_status()
    return r.json()

def post_json(url: str, hdrs: dict, payload: dict | None = None):
    if payload is None:
        r = requests.post(url, headers=hdrs, timeout=15)
    else:
        r = requests.post(url, headers={**hdrs, "Content-Type": "application/json"}, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def toast(msg: str, icon: str = "✅"):
    try:
        st.toast(msg, icon=icon)
    except Exception:
        st.success(msg)

st.title("🛠️ Bakım İşlemleri")
API_BASE, TOKEN, HDRS = get_api()
with st.sidebar:
    st.info(f"API: {API_BASE}")
    st.write("JWT:", "✅ Var" if TOKEN else "❌ Yok")

if not TOKEN:
    st.warning("Sol menüden giriş yapın (JWT yok).")
    st.stop()

# ===== 1) Arıza Talebi (Request) Oluştur =====
st.subheader("➕ Arıza Talebi Oluştur")
with st.form("form_request", clear_on_submit=True):
    c1, c2 = st.columns(2)
    machine_id = c1.number_input("MachineID", min_value=1, step=1)
    priority = c2.number_input("Öncelik (1-5, opsiyonel)", min_value=1, max_value=5, step=1, value=3)
    desc = st.text_input("Açıklama", value="frontend request")
    submitted_req = st.form_submit_button("Talep Oluştur")
if submitted_req:
    try:
        payload = {"MachineID": int(machine_id), "Priority_s": int(priority), "Description_s": desc or None}
        res = post_json(f"{API_BASE}/requests", HDRS, payload)
        rid = res.get("RequestID") or res.get("data", {}).get("RequestID")
        toast(f"Request oluşturuldu (ID: {rid})")
    except requests.HTTPError as e:
        st.error(f"Request hatası: {e.response.status_code} — {e.response.text[:160]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

st.divider()

# ===== 2) Açık Talepler (Open) =====
st.subheader("📋 Açık Talepler")
try:
    rows = get_json(f"{API_BASE}/requests?status=Open", HDRS)
    df_req = pd.DataFrame(rows if isinstance(rows, list) else rows.get("data", []))
    if df_req.empty:
        st.info("Açık talep yok.")
    else:
        show = df_req.rename(columns={
            "RequestID": "ReqID",
            "MachineID": "Makine",
            "OpenedAt": "Açılış",
            "OpenedBy": "Açan",
            "Priority_s": "Öncelik",
            "Status_s": "Durum",
            "Description_s": "Açıklama",
        })
        st.dataframe(show, use_container_width=True, height=260)
except requests.HTTPError as e:
    st.error(f"Liste hatası: {e.response.status_code}")
except requests.RequestException as e:
    st.error(f"Ağ hatası: {e}")

st.divider()

# ===== 3) İş Emri (WorkOrder) Aç =====
st.subheader("🧰 İş Emri Aç")
with st.form("form_wo", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    req_id = c1.number_input("RequestID", min_value=1, step=1)
    tech_id = c2.number_input("TechnicianID", min_value=1, step=1, value=1)
    notes = c3.text_input("Not", value="frontend WO")
    submitted_wo = st.form_submit_button("WorkOrder Oluştur")
if submitted_wo:
    try:
        res = post_json(f"{API_BASE}/workorders", HDRS, {"RequestID": int(req_id), "TechnicianID": int(tech_id), "Notes": notes or None})
        wid = res.get("WorkOrderID") or res.get("data", {}).get("WorkOrderID")
        toast(f"WorkOrder açıldı (ID: {wid})")
    except requests.HTTPError as e:
        st.error(f"WO hatası: {e.response.status_code} — {e.response.text[:160]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

st.divider()

# ===== 4) İş Emri Kapat =====
st.subheader("✅ İş Emri Kapat")
with st.form("form_close", clear_on_submit=True):
    close_id = st.number_input("WorkOrderID", min_value=1, step=1)
    submitted_close = st.form_submit_button("Kapat")
if submitted_close:
    try:
        res = post_json(f"{API_BASE}/workorders/{int(close_id)}/close", HDRS, None)
        toast(f"WorkOrder kapatıldı (ID: {int(close_id)})")
    except requests.HTTPError as e:
        st.error(f"Kapatma hatası: {e.response.status_code} — {e.response.text[:160]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

st.caption("Not: Talepleri listelemek için `/requests?status=Open`, WO için `/workorders` ve kapatma için `/workorders/{id}/close` uçları kullanılır.")
