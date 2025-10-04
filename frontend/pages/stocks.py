# frontend/pages/stocks.py
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Stoklar", layout="wide")

# --- Ortak yardımcılar ---
def get_api_base_and_token():
    api_base = st.session_state.get("api_base") or os.getenv("API_BASE", "http://127.0.0.1:8011")
    token = st.session_state.get("jwt", "")
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    return api_base.rstrip("/"), token, hdrs

def get_json(url: str, hdrs: dict):
    r = requests.get(url, headers=hdrs, timeout=15)
    r.raise_for_status()
    return r.json()

def post_json(url: str, hdrs: dict, payload: dict):
    r = requests.post(url, headers={**hdrs, "Content-Type": "application/json"}, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def toast(msg: str, icon: str = "✅"):
    try:
        st.toast(msg, icon=icon)
    except Exception:
        st.success(msg)

API_BASE, TOKEN, HDRS = get_api_base_and_token()

st.title("📦 Stok Yönetimi")

with st.sidebar:
    st.info(f"API: {API_BASE}")
    st.write("JWT:", "✅ Var" if TOKEN else "❌ Yok")

# --- Alt stok liste ---
st.subheader("⚠️ Minimum Stok Altındaki Parçalar")
try:
    data = get_json(f"{API_BASE}/parts/below-min", HDRS)
    df = pd.DataFrame(data if isinstance(data, list) else data.get("value", data.get("data", [])))
    if df.empty:
        st.info("Tüm parçalar minimum stok üzerinde görünüyor.")
    else:
        cols_map = {
            "PartID": "ParçaID",
            "PartCode": "Kod",
            "PartName": "Ad",
            "CurrentStock": "Mevcut",
            "MinStock": "Min",
        }
        df = df.rename(columns={k: v for k, v in cols_map.items() if k in df.columns})
        st.dataframe(df, use_container_width=True, height=300)
except requests.HTTPError as e:
    st.error(f"Liste alınamadı: {getattr(e.response,'status_code', '?')}")
except requests.RequestException as e:
    st.error(f"Ağ hatası: {e}")

st.divider()

# --- Hızlı Parça Detayı (yeni uç: /parts/id/{part_id}) ---
with st.expander("🔎 Parça Detayı (ID ile getir)"):
    pid_q = st.number_input("ParçaID", min_value=1, step=1, key="detail_pid")
    if st.button("Detayı Getir", key="btn_detail"):
        try:
            detail = get_json(f"{API_BASE}/parts/id/{int(pid_q)}", HDRS)
            st.json(detail)
        except requests.HTTPError as e:
            st.error(f"Detay alınamadı: {getattr(e.response,'status_code','?')} — {getattr(e.response,'text','')[:160]}")
        except requests.RequestException as e:
            st.error(f"Ağ hatası: {e}")

# --- Hızlı Giriş/Çıkış formları ---
c_in, c_out = st.columns(2)

def _safe_detail(pid: int):
    try:
        return get_json(f"{API_BASE}/parts/id/{int(pid)}", HDRS) or {}
    except Exception:
        return {}

with c_in:
    st.subheader("📥 Depo Giriş (IN)")
    with st.form("form_in", clear_on_submit=True):
        part_id_in = st.number_input("ParçaID", min_value=1, step=1)
        qty_in = st.number_input("Miktar", min_value=1, step=1)
        reason_in = st.text_input("Açıklama", value="manual IN")
        wo_in = st.number_input("WorkOrderID (opsiyonel)", min_value=0, step=1, value=0)
        submitted_in = st.form_submit_button("Giriş (IN) işle")
    if submitted_in:
        before = _safe_detail(part_id_in)
        try:
            payload = {
                "PartID": int(part_id_in),
                "Quantity": int(qty_in),
                "Reason": reason_in or None,
                "WorkOrderID": (int(wo_in) if wo_in > 0 else None),
            }
            res = post_json(f"{API_BASE}/warehouse/in", HDRS, payload)
            if res.get("ok"):
                after = _safe_detail(part_id_in)
                txn = res.get("data", {})
                b = before.get("CurrentStock")
                a = after.get("CurrentStock")
                note = f" — stok: {b} → {a}" if (b is not None and a is not None) else ""
                toast(f"IN OK — TxnID: {txn.get('TxnID','?')}{note}")
            else:
                st.error(f"IN hatası: {res.get('error')}")
        except requests.HTTPError as e:
            st.error(f"IN HTTP hatası: {e.response.status_code} — {e.response.text[:160]}")
        except requests.RequestException as e:
            st.error(f"Ağ hatası: {e}")

with c_out:
    st.subheader("📤 Depo Çıkış (OUT)")
    with st.form("form_out", clear_on_submit=True):
        part_id_out = st.number_input("ParçaID ", min_value=1, step=1, key="part_out")
        qty_out = st.number_input("Miktar ", min_value=1, step=1, key="qty_out")
        reason_out = st.text_input("Açıklama ", value="manual OUT", key="reason_out")
        wo_out = st.number_input("WorkOrderID (opsiyonel) ", min_value=0, step=1, value=0, key="wo_out")
        submitted_out = st.form_submit_button("Çıkış (OUT) işle")
    if submitted_out:
        before = _safe_detail(part_id_out)
        try:
            payload = {
                "PartID": int(part_id_out),
                "Quantity": int(qty_out),
                "Reason": reason_out or None,
                "WorkOrderID": (int(wo_out) if wo_out > 0 else None),
            }
            res = post_json(f"{API_BASE}/warehouse/out", HDRS, payload)
            if res.get("ok"):
                after = _safe_detail(part_id_out)
                txn = res.get("data", {})
                b = before.get("CurrentStock")
                a = after.get("CurrentStock")
                note = f" — stok: {b} → {a}" if (b is not None and a is not None) else ""
                toast(f"OUT OK — TxnID: {txn.get('TxnID','?')}{note}")
            else:
                st.error(f"OUT hatası: {res.get('error')}")
        except requests.HTTPError as e:
            st.error(f"OUT HTTP hatası: {e.response.status_code} — {e.response.text[:160]}")
        except requests.RequestException as e:
            st.error(f"Ağ hatası: {e}")

st.caption("Not: Bu sayfa için store/admin rolü gerekir. Tekil parça detayı için yeni uç: `/parts/id/{part_id}`.")
