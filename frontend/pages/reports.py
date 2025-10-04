import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Raporlar", layout="wide")

st.title("📊 Raporlar")

# Token session'da saklanmış olmalı (login sayfasından)
API_BASE = st.session_state.get("API_BASE", "http://127.0.0.1:8011")
token = st.session_state.get("token")

if not token:
    st.warning("⚠️ Lütfen önce giriş yapınız.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# --- En çok arıza veren makineler ---
st.subheader("En Çok Arıza Veren Makineler")

try:
    resp = requests.get(f"{API_BASE}/reports/top-failure-machines?top=10", headers=headers)
    resp.raise_for_status()
    data = resp.json().get("value", [])
    if data:
        df_fail = pd.DataFrame(data)
        st.dataframe(df_fail)

        chart = (
            alt.Chart(df_fail)
            .mark_bar()
            .encode(
                x=alt.X("failureCount:Q", title="Arıza Sayısı"),
                y=alt.Y("MachineName:N", sort="-x", title="Makine"),
                tooltip=["MachineName", "failureCount"]
            )
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Veri bulunamadı.")
except Exception as e:
    st.error(f"Hata: {e}")

st.markdown("---")

# --- En çok tüketilen parçalar ---
st.subheader("En Çok Tüketilen Parçalar")

try:
    resp = requests.get(f"{API_BASE}/reports/top-consumed-parts?top=10", headers=headers)
    resp.raise_for_status()
    data = resp.json().get("value", [])
    if data:
        df_parts = pd.DataFrame(data)
        st.dataframe(df_parts)

        chart = (
            alt.Chart(df_parts)
            .mark_bar()
            .encode(
                x=alt.X("consumedCount:Q", title="Tüketim"),
                y=alt.Y("PartName:N", sort="-x", title="Parça"),
                tooltip=["PartName", "consumedCount"]
            )
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Veri bulunamadı.")
except Exception as e:
    st.error(f"Hata: {e}")
