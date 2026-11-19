from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="🛒", layout="wide")
sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).parent
SEGMENT_ORDER = ["Champions", "Loyal", "New High Value", "Promising", "At Risk", "Lost"]
SEGMENT_COLORS = {"Champions": "#1f5fa8", "Loyal": "#4f86c6", "New High Value": "#2a9d8f",
                  "Promising": "#8fc7bf", "At Risk": "#e9a23b", "Lost": "#b0b0b0"}
CLASS_LABELS = ["Cepat (<=10 hari)", "Sedang (10-15 hari)", "Lambat (>15 hari)"]
CLASS_COLORS = {"Cepat (<=10 hari)": "#2a9d8f", "Sedang (10-15 hari)": "#e9a23b", "Lambat (>15 hari)": "#d1495b"}


# ---------------------------------------------------------------- data
@st.cache_data
def load_data():
    df = pd.read_csv(BASE_DIR / "main_data.csv", parse_dates=["order_date"])
    geo = pd.read_csv(BASE_DIR / "state_geo.csv")
    return df, geo


def quartile_score(series, labels):
    """Skor kuartil 1-4. Jika batas bin tidak unik, pakai peringkat agar tetap berjalan."""
    try:
        return pd.qcut(series, 4, labels=labels).astype(int)
    except ValueError:
        return pd.qcut(series.rank(method="first"), 4, labels=labels).astype(int)


@st.cache_data
def compute_rfm(df):
    ref_date = df["order_date"].max() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_key")
           .agg(last_purchase=("order_date", "max"),
                frequency=("order_key", "nunique"),
                monetary=("price", "sum"))
           .reset_index())
    rfm["recency"] = (ref_date - rfm["last_purchase"]).dt.days
    rfm["r_score"] = quartile_score(rfm["recency"], [4, 3, 2, 1])
    rfm["m_score"] = quartile_score(rfm["monetary"], [1, 2, 3, 4])
    rfm["f_score"] = pd.cut(rfm["frequency"], bins=[0, 1, 2, np.inf], labels=[1, 2, 3]).astype(int)

    conditions = [
        (rfm["f_score"] >= 2) & (rfm["r_score"] >= 3),
        (rfm["f_score"] >= 2) & (rfm["r_score"] <= 2),
        (rfm["f_score"] == 1) & (rfm["r_score"] >= 3) & (rfm["m_score"] >= 3),
        (rfm["f_score"] == 1) & (rfm["r_score"] >= 3) & (rfm["m_score"] <= 2),
        (rfm["f_score"] == 1) & (rfm["r_score"] <= 2) & (rfm["m_score"] >= 3),
    ]
    rfm["segment"] = np.select(conditions, SEGMENT_ORDER[:5], default="Lost")

    summary = (rfm.groupby("segment")
               .agg(customers=("customer_key", "count"), revenue=("monetary", "sum"),
                    avg_recency=("recency", "mean"), avg_monetary=("monetary", "mean"))
               .reindex(SEGMENT_ORDER).fillna(0).reset_index())
    summary["customer_pct"] = summary["customers"] / summary["customers"].sum() * 100
    summary["revenue_pct"] = summary["revenue"] / summary["revenue"].sum() * 100
    return summary


def compute_state_summary(df, geo):
    orders = df.drop_duplicates("order_key")
    by_order = orders.groupby("customer_state").agg(
        orders=("order_key", "count"), avg_delivery_days=("delivery_days", "mean"),
        avg_review_score=("review_score", "mean"))
    by_item = df.groupby("customer_state").agg(revenue=("price", "sum"), customers=("customer_key", "nunique"))
    out = by_item.join(by_order).reset_index()
    out["revenue_pct"] = out["revenue"] / out["revenue"].sum() * 100
    out["delivery_class"] = pd.cut(out["avg_delivery_days"], bins=[0, 10, 15, np.inf], labels=CLASS_LABELS)
    out = out.merge(geo, on="customer_state", how="left")
    return out.sort_values("revenue", ascending=False)


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


# ---------------------------------------------------------------- load + filter
df_all, geo = load_data()

st.sidebar.title("Filter")
min_date, max_date = df_all["order_date"].min().date(), df_all["order_date"].max().date()
date_range = st.sidebar.date_input("Rentang tanggal pembelian", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)
all_states = sorted(df_all["customer_state"].unique())
selected_states = st.sidebar.multiselect("State pelanggan", options=all_states, default=all_states)
top_n = st.sidebar.slider("Jumlah kategori/state teratas", min_value=5, max_value=15, value=10)
st.sidebar.caption("Revenue = jumlah harga barang (tanpa ongkos kirim) dari pesanan berstatus delivered.")

st.title("🛒 Dashboard Analisis E-Commerce Olist")
st.caption("Pesanan delivered, Januari 2017 sampai Agustus 2018. Revenue dalam Real Brasil (R$).")

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pilih tanggal awal dan tanggal akhir pada filter di sebelah kiri.")
    st.stop()

start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
df = df_all[(df_all["order_date"] >= start_date) & (df_all["order_date"] <= end_date)
            & (df_all["customer_state"].isin(selected_states))]
if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

# ---------------------------------------------------------------- ringkasan
orders_unique = df.drop_duplicates("order_key")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total revenue", f"R$ {df['price'].sum():,.0f}")
c2.metric("Jumlah pesanan", f"{df['order_key'].nunique():,}")
c3.metric("Pelanggan unik", f"{df['customer_key'].nunique():,}")
c4.metric("Rata-rata review", f"{orders_unique['review_score'].mean():.2f}")
c5.metric("Rata-rata waktu kirim", f"{orders_unique['delivery_days'].mean():.1f} hari")

tab1, tab2, tab3 = st.tabs(["📦 Kategori Produk", "👥 Segmentasi Pelanggan (RFM)", "🗺️ Geografis & Pengiriman"])

# ---------------------------------------------------------------- tab 1
with tab1:
    st.subheader(f"Top {top_n} kategori produk berdasarkan revenue")
    cat = (df.groupby("product_category")
           .agg(revenue=("price", "sum"), orders=("order_key", "nunique"))
           .sort_values("revenue", ascending=False))
    cat["share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100
    top_cat = cat.head(top_n).reset_index()

    fig, ax = plt.subplots(figsize=(10, 0.5 * top_n + 1.5))
    palette = ["#1f5fa8"] + ["#a9c3e0"] * (len(top_cat) - 1)
    sns.barplot(data=top_cat, x="revenue", y="product_category", hue="product_category",
                palette=palette, legend=False, ax=ax)
    for i, row in top_cat.iterrows():
        ax.text(row["revenue"], i, f"  R$ {row['revenue'] / 1e6:.2f} jt ({row['share_pct']:.1f}%)", va="center", fontsize=9)
    ax.set_xlabel("Total revenue (R$)")
    ax.set_ylabel("")
    ax.set_xlim(0, top_cat["revenue"].max() * 1.35)
    sns.despine(left=True)
    show(fig)

    st.write(f"Kategori teratas **{top_cat.iloc[0]['product_category']}** menyumbang "
             f"**{top_cat.iloc[0]['share_pct']:.1f}%** revenue. {top_n} kategori teratas bersama-sama menyumbang "
             f"**{top_cat['share_pct'].sum():.1f}%**.")
    st.dataframe(top_cat.rename(columns={"product_category": "Kategori", "revenue": "Revenue (R$)",
                                         "orders": "Pesanan", "share_pct": "Kontribusi (%)"}),
                 hide_index=True)

# ---------------------------------------------------------------- tab 2
with tab2:
    st.subheader("Segmentasi pelanggan dengan RFM")
    st.caption("Recency = hari sejak pembelian terakhir, Frequency = jumlah pesanan, Monetary = total belanja. "
               "Tanggal referensi mengikuti rentang tanggal yang dipilih.")
    if df["customer_key"].nunique() < 20:
        st.info("Jumlah pelanggan terlalu sedikit untuk segmentasi RFM. Perluas filter.")
    else:
        seg = compute_rfm(df)
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for ax, col, pct, title in [(axes[0], "customers", "customer_pct", "Jumlah pelanggan per segmen"),
                                    (axes[1], "revenue", "revenue_pct", "Revenue per segmen (R$)")]:
            sns.barplot(data=seg, x=col, y="segment", hue="segment", palette=SEGMENT_COLORS,
                        legend=False, order=SEGMENT_ORDER, ax=ax)
            for i, r in seg.iterrows():
                ax.text(r[col], i, f"  {r[col]:,.0f} ({r[pct]:.1f}%)", va="center", fontsize=9)
            ax.set_title(title, loc="left")
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.set_xlim(0, seg[col].max() * 1.4)
        sns.despine(left=True)
        plt.tight_layout()
        show(fig)

        top_seg = seg.sort_values("revenue", ascending=False).iloc[0]
        st.write(f"Segmen dengan revenue terbesar: **{top_seg['segment']}** "
                 f"({top_seg['revenue_pct']:.1f}% revenue dari {top_seg['customer_pct']:.1f}% pelanggan).")
        st.dataframe(seg.rename(columns={"segment": "Segmen", "customers": "Pelanggan", "revenue": "Revenue (R$)",
                                         "avg_recency": "Rata-rata recency (hari)", "avg_monetary": "Rata-rata belanja (R$)",
                                         "customer_pct": "Pelanggan (%)", "revenue_pct": "Revenue (%)"}),
                     hide_index=True)

# ---------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Persebaran revenue, waktu pengiriman, dan review per state")
    state = compute_state_summary(df, geo)

    left, right = st.columns(2)
    with left:
        top_state = state.head(top_n)
        fig, ax = plt.subplots(figsize=(7, 0.45 * top_n + 1.5))
        sns.barplot(data=top_state, x="revenue", y="customer_state", hue="customer_state",
                    palette=["#1f5fa8"] + ["#a9c3e0"] * (len(top_state) - 1), legend=False, ax=ax)
        for i, (_, r) in enumerate(top_state.iterrows()):
            ax.text(r["revenue"], i, f"  {r['revenue_pct']:.1f}%", va="center", fontsize=9)
        ax.set_title(f"{len(top_state)} state dengan revenue tertinggi", loc="left")
        ax.set_xlabel("Total revenue (R$)")
        ax.set_ylabel("")
        ax.set_xlim(0, top_state["revenue"].max() * 1.2)
        sns.despine(left=True)
        show(fig)
    with right:
        by_days = state.sort_values("avg_delivery_days", ascending=False)
        fig, ax = plt.subplots(figsize=(7, max(4, 0.25 * len(by_days) + 1)))
        sns.barplot(data=by_days, x="avg_delivery_days", y="customer_state", hue="delivery_class",
                    palette=CLASS_COLORS, dodge=False, ax=ax)
        ax.set_title("Rata-rata waktu pengiriman (hari)", loc="left")
        ax.set_xlabel("Hari dari pembelian sampai diterima")
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(title="Kelas", loc="lower right", fontsize=8)
        sns.despine(left=True)
        show(fig)

    st.markdown("**Peta persebaran revenue** (ukuran titik = revenue, warna = kelas waktu pengiriman: "
                "hijau cepat, kuning sedang, merah lambat)")
    geo_map = state.dropna(subset=["latitude", "longitude"]).copy()
    geo_map["size"] = geo_map["revenue"] / geo_map["revenue"].max() * 300000 + 30000
    geo_map["color"] = geo_map["delivery_class"].astype(str).map(CLASS_COLORS)
    st.map(geo_map, latitude="latitude", longitude="longitude", size="size", color="color")

    st.markdown("**Lama pengiriman dan review score**")
    rv = orders_unique.dropna(subset=["review_score"]).copy()
    rv["Lama pengiriman"] = pd.cut(rv["delivery_days"], bins=[0, 7, 14, 21, 28, np.inf],
                                   labels=["<=7 hari", "8-14 hari", "15-21 hari", "22-28 hari", ">28 hari"])
    rv_sum = rv.groupby("Lama pengiriman", observed=True).agg(Pesanan=("order_key", "count"),
                                                              Rata_rata_review=("review_score", "mean")).reset_index()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    sns.barplot(data=rv_sum, x="Lama pengiriman", y="Rata_rata_review", color="#4f86c6", ax=ax)
    for i, v in enumerate(rv_sum["Rata_rata_review"]):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Rata-rata review (1-5)")
    sns.despine()
    show(fig)

    st.dataframe(state[["customer_state", "customers", "revenue", "revenue_pct", "avg_delivery_days",
                        "avg_review_score", "delivery_class"]]
                 .rename(columns={"customer_state": "State", "customers": "Pelanggan", "revenue": "Revenue (R$)",
                                  "revenue_pct": "Revenue (%)", "avg_delivery_days": "Rata-rata hari kirim",
                                  "avg_review_score": "Rata-rata review", "delivery_class": "Kelas pengiriman"}),
                 hide_index=True)

st.caption("Sumber data: Brazilian E-Commerce Public Dataset by Olist. Proyek akhir analisis data.")
