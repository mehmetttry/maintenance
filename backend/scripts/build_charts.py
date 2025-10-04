# backend/scripts/build_charts.py
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]  # D:\ToraM_Proje
OUT  = ROOT / "report_outputs"
OUT.mkdir(exist_ok=True)

# ---------- 1) Pareto: En çok arıza veren makineler ----------
p_fail = OUT / "top-failure-machines.csv"
if p_fail.exists() and p_fail.stat().st_size > 3:  # 3 byte ~ min. boş dosya
    df = pd.read_csv(p_fail, encoding="utf-8")
    if not df.empty and {"machineName","failureCount"}.issubset(df.columns):
        df = df.sort_values("failureCount", ascending=False).reset_index(drop=True)
        df["cum"]  = df["failureCount"].cumsum()
        total = df["failureCount"].sum() or 1
        df["cum_pct"] = df["cum"] / total * 100

        plt.figure(figsize=(9,5))
        # bar
        plt.bar(df["machineName"], df["failureCount"])
        # cumulative line (ikinci eksen)
        plt.twinx()
        plt.plot(df["machineName"], df["cum_pct"], marker="o")
        plt.axhline(80, linestyle="--")
        plt.ylabel("Kümülatif %")
        # x label'ları okunaklı
        plt.xticks(rotation=25, ha="right")
        plt.title("Pareto — Arıza Sayısı (Makine)")
        plt.tight_layout()
        plt.savefig(OUT / "chart_pareto_failures.png", dpi=150)
        plt.close()

# ---------- 2) Yaş Kovası: Açık iş emirleri ----------
p_age = OUT / "open-wo-aging_summary.csv"
if p_age.exists() and p_age.stat().st_size > 3:
    ds = pd.read_csv(p_age, encoding="utf-8")
    if not ds.empty and {"ageBucket","openWOCount"}.issubset(ds.columns):
        # Kovalara sabit sıralama verelim
        order = ["0-2","3-5","6-10",">10"]
        ds["ageBucket"] = pd.Categorical(ds["ageBucket"], categories=order, ordered=True)
        ds = ds.sort_values("ageBucket")

        plt.figure(figsize=(7,4))
        plt.bar(ds["ageBucket"], ds["openWOCount"])
        plt.xlabel("Yaş Kovası (gün)")
        plt.ylabel("Açık İş Emri Adedi")
        plt.title("Açık İş Emirleri — Yaş Dağılımı")
        plt.tight_layout()
        plt.savefig(OUT / "chart_open_wo_age_buckets.png", dpi=150)
        plt.close()
