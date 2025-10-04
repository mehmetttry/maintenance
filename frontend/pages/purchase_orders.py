# frontend/pages/purchase_orders.py
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Satınalma Emirleri", layout="wide")

# ---------- Helpers ----------
def get_api_base_and_token():
    api_base = st.session_state.get("api_base") or os.getenv("API_BASE", "http://127.0.0.1:8011")
    token = st.session_state.get("jwt", "")
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

def to_list_like(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        if isinstance(x.get("value"), list):
            return x["value"]
        if isinstance(x.get("data"), list):
            return x["data"]
        # bazı uçlar düz liste döndürür; bazıları {"ok":true,"data":[...]} döndürür
        d = x.get("data")
        return d if isinstance(d, list) else []
    return []

def toast(msg: str, icon: str="✅"):
    try: st.toast(msg, icon=icon)
    except Exception: st.success(msg)

API_BASE, TOKEN, HDRS = get_api_base_and_token()

st.title("🧾 Satınalma Emirleri")
with st.sidebar:
    st.info(f"API: {API_BASE}")
    st.write("JWT:", "✅ Var" if TOKEN else "❌ Yok")

# ---------- Reorder önerileri ----------
st.subheader("📒 Reorder Önerileri")
c1, c2, c3 = st.columns([1,1,1])
min_gap = c1.number_input("Minimum Açık (min_gap)", min_value=1, value=1, step=1)
top = c2.number_input("Limit", min_value=1, value=20, step=1)
btn_load_sug = c3.button("Önerileri Yükle")

sug_df = pd.DataFrame()
if btn_load_sug:
    try:
        raw = get_json(f"{API_BASE}/parts/reorder-suggestion?min_gap={int(min_gap)}&limit={int(top)}", HDRS)
        items = to_list_like(raw)
        sug_df = pd.DataFrame(items)
        if sug_df.empty:
            st.info("Öneri yok.")
        else:
            st.dataframe(sug_df, use_container_width=True, height=280)
            # hızlı seçim için ilk satırın PartID'sini cachele
            if "PartID" in sug_df.columns:
                st.session_state["suggest_part"] = int(sug_df.iloc[0]["PartID"])
    except requests.RequestException as e:
        st.error(f"Öneriler alınamadı: {e}")

st.markdown("---")

# ---------- Öneriden PO oluştur ----------
st.subheader("🆕 Öneriden PO Oluştur")
c = st.columns([1,1,1,1,1])
part_id_in = c[0].number_input("PartID", min_value=1, step=1, value=int(st.session_state.get("suggest_part", 1)))
supplier_id_in = c[1].number_input("SupplierID", min_value=1, step=1, value=1)
qty_in = c[2].number_input("Qty (manuel)", min_value=1, step=1, value=1)
unit_price_in = c[3].number_input("UnitPrice", min_value=0.01, step=0.01, value=10.00, format="%.2f")
b_manual = c[4].button("PO Oluştur (manuel)")
b_auto   = st.button("PO Oluştur (öneriden — Qty=Gap)")

if b_manual:
    try:
        payload = {
            "SupplierID": int(supplier_id_in),
            "PartID": int(part_id_in),
            "Qty": int(qty_in),
            "UnitPrice": float(unit_price_in),
        }
        po = post_json(f"{API_BASE}/purchase-orders", HDRS, payload)
        poid = po.get("POID") or (po.get("data") or {}).get("POID")
        toast(f"PO oluşturuldu (POID={poid})")
        st.session_state["last_poid"] = poid
    except requests.HTTPError as e:
        st.error(f"PO oluşturma hatası: {e.response.status_code} — {e.response.text[:180]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

if b_auto:
    try:
        payload = {
            "SupplierID": int(supplier_id_in),
            "PartID": int(part_id_in),
            "UnitPrice": float(unit_price_in),
        }
        po = post_json(f"{API_BASE}/purchase-orders/from-suggestion", HDRS, payload)
        poid = po.get("POID") or (po.get("data") or {}).get("POID")
        toast(f"PO (öneri) oluşturuldu (POID={poid})")
        st.session_state["last_poid"] = poid
    except requests.HTTPError as e:
        st.error(f"PO(öneri) hatası: {e.response.status_code} — {e.response.text[:180]}")
    except requests.RequestException as e:
        st.error(f"Ağ hatası: {e}")

# ---------- PO liste ----------
st.subheader("📋 PO Listesi")
colL, colR = st.columns([3,2])
with colL:
    try:
        lst = get_json(f"{API_BASE}/purchase-orders/", HDRS)
        rows = lst if isinstance(lst, list) else lst.get("items", lst.get("data", lst))
        df_po = pd.DataFrame(rows)
        if not df_po.empty:
            df_po = df_po.sort_values("POID")
            st.dataframe(df_po, use_container_width=True, height=300)
        else:
            st.info("PO listesi boş.")
    except requests.RequestException as e:
        st.error(f"PO listesi alınamadı: {e}")

with colR:
    st.write("**İşlemler**")
    poid_in = st.number_input("POID", min_value=1, step=1, value=int(st.session_state.get("last_poid") or 1))
    b1, b2, b3 = st.columns(3)
    if b1.button("Place"):
        try:
            res = post_json(f"{API_BASE}/purchase-orders/{int(poid_in)}/place", HDRS, {})
            toast(f"Placed (POID={res.get('POID', poid_in)})")
        except requests.RequestException as e:
            st.error(f"Place hatası: {e}")
    if b2.button("Receive"):
        try:
            res = post_json(f"{API_BASE}/purchase-orders/{int(poid_in)}/receive", HDRS, {})
            toast(f"Receive OK (POID={res.get('POID', poid_in)})")
        except requests.HTTPError as e:
            txt = getattr(e.response, "text", "")[:200]
            st.error(f"Receive hatası: {e.response.status_code} — {txt}")
        except requests.RequestException as e:
            st.error(f"Receive hatası: {e}")
    if b3.button("Cancel"):
        try:
            res = post_json(f"{API_BASE}/purchase-orders/{int(poid_in)}/cancel", HDRS, {})
            toast(f"Canceled (POID={res.get('POID', poid_in)})", icon="⚠️")
        except requests.RequestException as e:
            st.error(f"Cancel hatası: {e}")

st.markdown("---")

# ---------- Txn arama (Reason ile) ----------
st.subheader("📦 Depo Hareketleri — Reason Filtresi")
cA, cB, cC = st.columns([1,1,1])
poid_for_reason = cA.number_input("POID", min_value=1, step=1, value=int(st.session_state.get("last_poid") or 1))
pattern = cB.selectbox("Şablon", ["PO Receive #<POID>", "PO#<POID> Received"])
btn_txn = cC.button("Ara")

if btn_txn:
    try:
        if pattern.startswith("PO Receive"):
            reason = f"PO Receive #{int(poid_for_reason)}"
        else:
            reason = f"PO#{int(poid_for_reason)} Received"
        url = f"{API_BASE}/warehouse/txns?reason={requests.utils.quote(reason)}"
        res = get_json(url, HDRS)
        data = res.get("data", res.get("value", res))
        df_tx = pd.DataFrame(data)
        if df_tx.empty:
            st.info("Kayıt bulunamadı.")
        else:
            st.dataframe(df_tx, use_container_width=True, height=240)
    except requests.RequestException as e:
        st.error(f"Txn arama hatası: {e}")
