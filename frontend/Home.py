# frontend/Home.py
import os, datetime as dt, time
import requests, pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Bakım Panosu — Sprint 7", layout="wide")

# Varsayılanlar
DEFAULT_API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8011")
DEFAULT_TOKEN    = os.getenv("API_TOKEN", "")

def _normalize_token(raw: str) -> str:
    s = str(raw or "").strip().strip('"').strip("'")
    if not s:
        return ""
    # "Bearer ..." gelmişse sadece JWT'yi al
    if s.lower().startswith("bearer "):
        s = s.split(" ", 1)[1].strip()
    return s

if "jwt" not in st.session_state:
    st.session_state["jwt"] = _normalize_token(DEFAULT_TOKEN)

st.title("Bakım Panosu")

# --------- Sidebar: Ayarlar / Giriş / Sağlık ---------
with st.sidebar:
    st.header("Ayarlar")
    api_base = st.text_input("API Tabanı", value=DEFAULT_API_BASE, key="api_base")

    st.divider()
    st.subheader("Giriş (JWT)")
    colu, colp = st.columns(2)
    username = colu.text_input("Kullanıcı", value="", placeholder="store1", key="user")
    password = colp.text_input("Parola", value="", type="password", placeholder="Passw0rd!", key="pass")
    c1, c2 = st.columns([1,1])
    do_login  = c1.button("Giriş Yap", key="btn_login")
    do_logout = c2.button("Çıkış", key="btn_logout")

    manual_token = st.text_input("Jeton (manüel)", value=st.session_state.get("jwt",""), type="password", key="manual_token")

    def _login(api_base: str, u: str, p: str) -> str:
        url = f"{api_base.rstrip('/')}/auth/login"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"username": u, "password": p}
        r = requests.post(url, headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.json().get("access_token","")

    if do_login:
        try:
            tok = _login(api_base, username, password)
            tok = _normalize_token(tok)
            if tok:
                st.session_state["jwt"] = tok
                st.success("Giriş başarılı — token alındı.")
            else:
                st.error("Giriş başarısız: access_token boş.")
        except requests.RequestException as e:
            st.error(f"Giriş hatası: {e}")

    if do_logout:
        st.session_state["jwt"] = ""
        st.info("Çıkış yapıldı.")

    # Manüel token değiştiyse normalize edip yaz
    if manual_token != st.session_state.get("jwt",""):
        st.session_state["jwt"] = _normalize_token(manual_token)

    st.divider()
    st.subheader("API Sağlık")
    def _health(api_base: str):
        try:
            h = requests.get(f"{api_base.rstrip('/')}/health", timeout=5)
            h.raise_for_status()
            return True, h.json()
        except Exception as e:
            return False, str(e)
    ok, payload = _health(api_base)
    if ok:
        st.success("API: Tamam")
    else:
        st.error(f"API erişilemedi: {payload}")

API_BASE = (api_base or DEFAULT_API_BASE).strip().rstrip("/")
TOKEN    = _normalize_token(st.session_state.get("jwt",""))
HDRS     = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# --------- Filtreler ---------
c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
start = c1.date_input("Başlangıç", dt.date(2025, 8, 1), key="start_date")
end   = c2.date_input("Bitiş",    dt.date(2025, 9, 1), key="end_date")
top   = c3.number_input("Top", min_value=1, max_value=100, value=10, step=1, key="top_n")
refresh = c4.button("Yenile", key="btn_refresh")
retry_clicked = c5.button("Tekrar Dene", key="btn_retry")
status = st.empty()

# ---------- Hata sınıfı & istek yardımcıları ----------
class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        self.status = status; self.url = url; super().__init__(message)

def _friendly_http_message(status: int, url: str, body_preview: str = "") -> str:
    if status == 401: return "Yetkisiz (401): Giriş yapın."
    if status == 403: return "Erişim engellendi (403)."
    if status == 404: return f"Bulunamadı (404): {url}"
    if status == 422: return "Geçersiz istek (422): Tarih formatı YYYY-MM-DD mi?"
    if status >= 500: return f"Sunucu hatası ({status})."
    return f"HTTP hata {status}: {body_preview}"

def get_json(url: str, hdrs: dict):
    try:
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        raise ApiError("Zaman aşımı.")
    except requests.ConnectionError:
        raise ApiError("Bağlantı kurulamadı: API kapalı ya da URL yanlış.")
    except requests.HTTPError as e:
        resp = e.response; body = ""
        try: body = resp.text[:160]
        except Exception: pass
        raise ApiError(_friendly_http_message(resp.status_code, url, body), resp.status_code, url)
    except requests.RequestException as e:
        raise ApiError(f"Ağ hatası: {e}")

def ensure_array(x):
    # ok-zarfı veya düz liste olabilir
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        d = x.get("data", x)  # {"ok":true,"data":[...]} -> [...]
        if isinstance(d, list):
            return d
        if isinstance(x.get("value"), list):
            return x["value"]
    return []

@st.cache_data(ttl=30)
def load_reports(api_base: str, hdrs: dict, s_iso: str, e_iso_inclusive: str, t: int):
    urls = {
        "fail": f"{api_base}/reports/top-failure-machines-list?start={s_iso}&end={e_iso_inclusive}&top={t}",
        "parts": f"{api_base}/reports/top-consumed-parts-list?start={s_iso}&end={e_iso_inclusive}&top={t}",
        "aging": f"{api_base}/reports/open-workorders-aging",
    }
    fail = ensure_array(get_json(urls["fail"], hdrs))
    parts = ensure_array(get_json(urls["parts"], hdrs))

    aging_raw = get_json(urls["aging"], hdrs)
    if isinstance(aging_raw, dict) and isinstance(aging_raw.get("data"), dict):
        aging = aging_raw["data"].get("summary", [])
    else:
        aging = aging_raw if isinstance(aging_raw, list) else aging_raw.get("summary", [])

    return fail, parts, aging

def _empty_fig(height=320, text="Veri yok"):
    fig = go.Figure()
    fig.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=height)
    fig.add_annotation(text=text, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    return fig

# Manuel refresh-cache temizliği
if refresh or retry_clicked:
    try:
        st.cache_data.clear()
    except Exception:
        pass

# ------------------ ANA AKIŞ ------------------
try:
    status.info("Yükleniyor…")
    s_iso = start.isoformat()
    e_iso_inclusive = (end + dt.timedelta(days=1)).isoformat()

    with st.spinner("Raporlar çekiliyor…"):
        fail_raw, parts_raw, aging_raw = load_reports(API_BASE, HDRS, s_iso, e_iso_inclusive, int(top))

    # Yer tutucular
    fail_box  = st.container()
    age_box   = st.container()
    part_box  = st.container()

    # ===== 1) Pareto — Arıza (Makine) =====
    with fail_box:
        st.subheader("Pareto — Arıza (Makine)")
        ch_fail = st.empty(); dl_fail = st.empty(); grid_fail = st.empty()

        df_f = pd.DataFrame(fail_raw)
        if not df_f.empty:
            df_f = df_f.rename(columns={"machineName":"Makine", "failureCount":"Arıza"})
            df_f["Arıza"] = pd.to_numeric(df_f["Arıza"], errors="coerce").fillna(0)
            total = float(df_f["Arıza"].sum() or 1)
            df_f["Kümülatif %"] = (df_f["Arıza"].cumsum()/total*100).round(0)

        if not df_f.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=df_f["Makine"], y=df_f["Arıza"], name="Arıza",
                        text=df_f["Arıza"], textposition="outside", texttemplate="%{text:.0f}")
            fig.add_scatter(x=df_f["Makine"], y=df_f["Kümülatif %"], name="Kümülatif %",
                            mode="lines+markers+text",
                            text=[f"{int(v)}%" for v in df_f["Kümülatif %"]],
                            textposition="top center", secondary_y=True)
            fig.update_yaxes(title_text="Arıza", secondary_y=False)
            fig.update_yaxes(title_text="Kümülatif %", secondary_y=True, range=[0,100])
            fig.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=360)
            ch_fail.plotly_chart(fig, use_container_width=True, key="chart_fail")
            dl_fail.download_button("CSV indir — Pareto", df_f.to_csv(index=False).encode("utf-8"),
                                    "pareto_ariza.csv", "text/csv", key="dl_fail")
            grid_fail.dataframe(df_f, use_container_width=True, height=300)
        else:
            ch_fail.plotly_chart(_empty_fig(360), use_container_width=True, key="chart_fail")
            dl_fail.empty(); grid_fail.info("Pareto için veri yok.")

    # ===== 2) Açık İş Emirleri — Yaş Dağılımı =====
    with age_box:
        st.subheader("Açık İş Emirleri — Yaş Dağılımı")
        ch_age = st.empty(); dl_age = st.empty(); grid_age = st.empty()

        df_a = pd.DataFrame(aging_raw)
        if not df_a.empty:
            df_a = df_a.rename(columns={"ageBucket":"Yaş", "bucket":"Yaş", "openWOCount":"Açık WO", "count":"Açık WO"})
            order = ["0-2","3-5","6-10",">10"]
            df_a["Yaş"] = pd.Categorical(df_a["Yaş"], categories=order, ordered=True)
            df_a = df_a.sort_values("Yaş")

        if not df_a.empty:
            fig2 = go.Figure(data=[go.Bar(x=df_a["Yaş"], y=df_a["Açık WO"], name="Açık WO",
                                          text=df_a["Açık WO"], textposition="outside", texttemplate="%{text:.0f}")])
            fig2.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=320)
            ch_age.plotly_chart(fig2, use_container_width=True, key="chart_age")
            dl_age.download_button("CSV indir — Yaş Dağılımı", df_a.to_csv(index=False).encode("utf-8"),
                                   "acik_wo_yas.csv", "text/csv", key="dl_age")
            grid_age.dataframe(df_a, use_container_width=True, height=220)
        else:
            ch_age.plotly_chart(_empty_fig(320), use_container_width=True, key="chart_age")
            dl_age.empty(); grid_age.info("Açık WO yaş dağılımı için veri yok.")

    # ===== 3) En Çok Tüketilen Parçalar =====
    with part_box:
        st.subheader("En Çok Tüketilen Parçalar")
        ch_parts = st.empty(); dl_parts = st.empty(); grid_parts = st.empty()

        df_p = pd.DataFrame(parts_raw)
        if not df_p.empty:
            df_p = df_p.rename(columns={"partName":"Parça", "qtyOut":"Tüketim"})
            df_p["Tüketim"] = pd.to_numeric(df_p["Tüketim"], errors="coerce").fillna(0)

        if not df_p.empty:
            fig3 = go.Figure(data=[go.Bar(x=df_p["Parça"], y=df_p["Tüketim"], name="Tüketim",
                                          text=df_p["Tüketim"], textposition="outside", texttemplate="%{text:.0f}")])
            fig3.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=360)
            ch_parts.plotly_chart(fig3, use_container_width=True, key="chart_parts")
            dl_parts.download_button("CSV indir — Parçalar", df_p.to_csv(index=False).encode("utf-8"),
                                     "top_parcalar.csv", "text/csv", key="dl_parts")
            grid_parts.dataframe(df_p, use_container_width=True, height=300)
        else:
            ch_parts.plotly_chart(_empty_fig(360), use_container_width=True, key="chart_parts")
            dl_parts.empty(); grid_parts.info("Tüketilen parça listesi boş.")

    status.success("Hazır — " + time.strftime("%H:%M:%S"))
except ApiError as ex:
    status.error(f"Hata: {ex}")
    st.info("İpucu: Sol menüden API Tabanı ve giriş bilgilerini kontrol et.")
    st.button("Tekrar Dene", key="btn_retry_err")
except Exception as ex:
    status.error(f"Beklenmeyen hata: {ex}")
    st.button("Tekrar Dene", key="btn_retry_unexp")
