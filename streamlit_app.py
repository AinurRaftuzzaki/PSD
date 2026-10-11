import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analisis Polutan Udara – Nunukan",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(99,179,237,0.15);
    }
    [data-testid="stMetricLabel"] { color: #90cdf4 !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 700 !important; }

    /* Header gradient */
    .hero-header {
        background: linear-gradient(135deg, rgba(99,179,237,0.15) 0%, rgba(154,117,253,0.15) 100%);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 20px;
        padding: 32px 40px;
        margin-bottom: 24px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .hero-header h1 { color: #ffffff; font-size: 2.2rem; font-weight: 700; margin: 0 0 8px 0; }
    .hero-header p  { color: #90cdf4; font-size: 1rem; margin: 0; }

    /* Section title */
    .section-title {
        color: #e2e8f0;
        font-size: 1.15rem;
        font-weight: 600;
        margin: 24px 0 12px 0;
        padding-left: 12px;
        border-left: 3px solid #63b3ed;
    }

    /* Pill badge */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green  { background: rgba(72,187,120,0.15); color: #68d391; border: 1px solid rgba(72,187,120,0.3); }
    .badge-yellow { background: rgba(246,173,85,0.15);  color: #fbd38d; border: 1px solid rgba(246,173,85,0.3); }
    .badge-red    { background: rgba(252,129,74,0.15);  color: #fc8181; border: 1px solid rgba(252,129,74,0.3); }

    /* Info box */
    .info-box {
        background: rgba(99,179,237,0.07);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 12px;
        padding: 16px;
        color: #cbd5e0;
        font-size: 0.88rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
POLLUTANT_META = {
    "CO":  {"label": "Karbon Monoksida (CO)",  "unit": "mol/m²",  "color": "#f6ad55", "safe_max": 0.035},
    "NO2": {"label": "Nitrogen Dioksida (NO2)", "unit": "mol/m²",  "color": "#fc8181", "safe_max": 0.00002},
    "SO2": {"label": "Sulfur Dioksida (SO2)",   "unit": "mol/m²",  "color": "#9f7aea", "safe_max": 0.00003},
}

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.02)",
    font=dict(family="Inter", color="#e2e8f0"),
    margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
)

@st.cache_data
def load_data():
    raw  = pd.read_csv("csv/Polutan_Nunukan.csv",        parse_dates=["date"])
    lin  = pd.read_csv("csv/Polutan_Nunukan_Linear.csv", parse_dates=["date"])
    poly = pd.read_csv("csv/Polutan_Nunukan_Poly.csv",   parse_dates=["date"])
    co_ts  = pd.read_csv("csv/CO_Nunukan_Timeseries_fixed.csv",  parse_dates=["date"])
    no2_ts = pd.read_csv("csv/NO2_Nunukan_Timeseries_fixed.csv", parse_dates=["date"])
    so2_ts = pd.read_csv("csv/SO2_Nunukan_Timeseries_fixed.csv", parse_dates=["date"])
    return raw, lin, poly, co_ts, no2_ts, so2_ts

raw, lin, poly, co_ts, no2_ts, so2_ts = load_data()
INDIVIDUAL = {"CO": co_ts, "NO2": no2_ts, "SO2": so2_ts}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌿 Filter Data")
    st.divider()

    selected_pollutants = st.multiselect(
        "Pilih Polutan",
        options=["CO", "NO2", "SO2"],
        default=["CO", "NO2", "SO2"],
    )

    interp_method = st.radio(
        "Metode Interpolasi",
        options=["Linear", "Polinomial"],
        index=0,
    )

    st.divider()
    st.markdown("""
    <div class="info-box">
    📡 Data dari <b>Sentinel-5P TROPOMI</b><br>
    📍 Lokasi: <b>Nunukan, Kalimantan Utara</b><br>
    📅 Periode: <b>Agu 2025 – Agu 2026</b>
    </div>
    """, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1>🌿 Analisis Polutan Udara Kota Nunukan</h1>
    <p>Monitoring kualitas udara berbasis data satelit Sentinel-5P · Kalimantan Utara, Indonesia</p>
</div>
""", unsafe_allow_html=True)

if not selected_pollutants:
    st.warning("⚠️ Pilih minimal satu polutan di sidebar.")
    st.stop()

df_interp = lin if interp_method == "Linear" else poly

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Statistik Ringkas</div>', unsafe_allow_html=True)
kpi_cols = st.columns(len(selected_pollutants) * 3)

for idx, pol in enumerate(selected_pollutants):
    series = df_interp[pol].dropna()
    mean_v, max_v, min_v = series.mean(), series.max(), series.min()
    base = idx * 3
    with kpi_cols[base]:
        st.metric(f"Rata-rata {pol}", f"{mean_v:.2e}")
    with kpi_cols[base + 1]:
        st.metric(f"Maks {pol}", f"{max_v:.2e}", f"↑ {((max_v-mean_v)/mean_v*100):.1f}%")
    with kpi_cols[base + 2]:
        st.metric(f"Min {pol}", f"{min_v:.2e}", f"↓ {((mean_v-min_v)/mean_v*100):.1f}%")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Time Series",
    "🔍 Perbandingan",
    "📦 Distribusi",
    "📋 Data",
])

# Tab 1 ─ Time Series
with tab1:
    st.markdown('<div class="section-title">Time Series Konsentrasi Polutan</div>', unsafe_allow_html=True)
    show_raw    = st.checkbox("Tampilkan data mentah", value=True)
    show_interp = st.checkbox("Tampilkan data interpolasi", value=True)

    for pol in selected_pollutants:
        meta = POLLUTANT_META[pol]
        fig = go.Figure()

        if show_raw:
            raw_s = INDIVIDUAL[pol].dropna()
            fig.add_trace(go.Scatter(
                x=raw_s["date"], y=raw_s[pol],
                mode="markers", name=f"{pol} – Asli",
                marker=dict(color=meta["color"], size=4, opacity=0.6),
            ))

        if show_interp:
            fig.add_trace(go.Scatter(
                x=df_interp["date"], y=df_interp[pol],
                mode="lines", name=f"{pol} – {interp_method}",
                line=dict(color=meta["color"], width=2),
            ))

        fig.add_hline(
            y=meta["safe_max"],
            line=dict(color="rgba(252,129,74,0.5)", dash="dot", width=1.5),
            annotation_text=f"Ambang {pol}",
            annotation_font_color="#fc8181",
        )
        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=meta["label"], font=dict(size=15, color="#e2e8f0")),
            xaxis_title="Tanggal", yaxis_title=meta["unit"],
            height=320, hovermode="x unified",
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 2 ─ Comparison
with tab2:
    st.markdown('<div class="section-title">Perbandingan Polutan (Dinormalisasi)</div>', unsafe_allow_html=True)
    normed = df_interp[["date"] + selected_pollutants].copy()
    for pol in selected_pollutants:
        c = normed[pol]; normed[pol] = (c - c.min()) / (c.max() - c.min())

    fig2 = go.Figure()
    for pol in selected_pollutants:
        meta = POLLUTANT_META[pol]
        fig2.add_trace(go.Scatter(
            x=normed["date"], y=normed[pol],
            mode="lines", name=pol,
            line=dict(color=meta["color"], width=2),
        ))
    fig2.update_layout(
        **LAYOUT_BASE, height=360, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Nilai Ternormalisasi"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    if len(selected_pollutants) > 1:
        st.markdown('<div class="section-title">Matriks Korelasi</div>', unsafe_allow_html=True)
        corr = df_interp[selected_pollutants].corr()
        fig_c = px.imshow(corr, text_auto=".2f",
                          color_continuous_scale=["#302b63","#63b3ed","#90cdf4"],
                          zmin=-1, zmax=1)
        fig_c.update_layout(**LAYOUT_BASE, height=320)
        st.plotly_chart(fig_c, use_container_width=True)

    st.markdown('<div class="section-title">Rata-rata Bulanan</div>', unsafe_allow_html=True)
    monthly = df_interp.copy()
    monthly["bulan"] = monthly["date"].dt.to_period("M").astype(str)
    m_avg = monthly.groupby("bulan")[selected_pollutants].mean().reset_index()
    fig_b = go.Figure()
    for pol in selected_pollutants:
        fig_b.add_trace(go.Bar(x=m_avg["bulan"], y=m_avg[pol],
                               name=pol, marker_color=POLLUTANT_META[pol]["color"], opacity=0.85))
    fig_b.update_layout(**LAYOUT_BASE, barmode="group", height=360,
                        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"))
    st.plotly_chart(fig_b, use_container_width=True)

# Tab 3 ─ Distribution
with tab3:
    st.markdown('<div class="section-title">Histogram Distribusi</div>', unsafe_allow_html=True)
    hcols = st.columns(len(selected_pollutants))
    for i, pol in enumerate(selected_pollutants):
        meta = POLLUTANT_META[pol]
        with hcols[i]:
            fig_h = go.Figure(go.Histogram(x=df_interp[pol].dropna(), nbinsx=30,
                                           marker_color=meta["color"], opacity=0.8))
            fig_h.update_layout(**LAYOUT_BASE, height=260, showlegend=False,
                                title=dict(text=pol, font=dict(size=14, color="#e2e8f0")),
                                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"))
            st.plotly_chart(fig_h, use_container_width=True)

    st.markdown('<div class="section-title">Box Plot</div>', unsafe_allow_html=True)
    fig_box = go.Figure()
    for pol in selected_pollutants:
        meta = POLLUTANT_META[pol]
        fig_box.add_trace(go.Box(y=df_interp[pol].dropna(), name=pol,
                                 marker_color=meta["color"], line_color=meta["color"]))
    fig_box.update_layout(**LAYOUT_BASE, height=360,
                          yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="mol/m²"))
    st.plotly_chart(fig_box, use_container_width=True)

    st.markdown('<div class="section-title">Statistik Deskriptif</div>', unsafe_allow_html=True)
    desc = df_interp[selected_pollutants].describe().T
    desc.index.name = "Polutan"
    desc = desc.rename(columns={"count":"n","mean":"Rata-rata","std":"Std Dev",
                                 "min":"Min","25%":"Q1","50%":"Median","75%":"Q3","max":"Maks"})
    st.dataframe(desc.style.format("{:.4e}"), use_container_width=True)

# Tab 4 ─ Raw Data
with tab4:
    st.markdown('<div class="section-title">Data Mentah</div>', unsafe_allow_html=True)
    display_raw = raw[["date"] + [p for p in selected_pollutants if p in raw.columns]].copy()
    missing = display_raw[selected_pollutants].isnull().sum()

    mc = st.columns(len(selected_pollutants))
    for i, pol in enumerate(selected_pollutants):
        pct = missing[pol] / len(display_raw) * 100
        lvl = "badge-red" if pct > 30 else ("badge-yellow" if pct > 10 else "badge-green")
        with mc[i]:
            st.markdown(f"**{pol}** – Missing: <span class='badge {lvl}'>{missing[pol]} ({pct:.1f}%)</span>",
                        unsafe_allow_html=True)

    st.dataframe(display_raw.set_index("date"), use_container_width=True)

    st.markdown(f'<div class="section-title">Data Interpolasi ({interp_method})</div>', unsafe_allow_html=True)
    display_i = df_interp[["date"] + [p for p in selected_pollutants if p in df_interp.columns]].copy()
    st.dataframe(display_i.set_index("date"), use_container_width=True)

    st.download_button(
        label=f"⬇️ Unduh Data Interpolasi ({interp_method})",
        data=display_i.to_csv(index=False).encode("utf-8"),
        file_name=f"polutan_nunukan_{interp_method.lower()}.csv",
        mime="text/csv",
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align:center; color:#4a5568; font-size:0.8rem; padding: 8px 0 16px;'>
    Data satelit Sentinel-5P via OpenEO · Kabupaten Nunukan, Kalimantan Utara · 2025–2026
</div>
""", unsafe_allow_html=True)
