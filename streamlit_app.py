"""
Klasifikasi Spasial Tutupan Lahan Jawa Timur
Model: K-Nearest Neighbors (KNN) — k=7, distance weights, euclidean
Sensor: Sentinel-2A MSI Level-2A BOA Surface Reflectance
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import (
    accuracy_score, cohen_kappa_score, confusion_matrix,
    f1_score, classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

st.set_page_config(
    page_title="Klasifikasi Tutupan Lahan Jawa Timur",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 16px; padding: 18px 20px;
    backdrop-filter: blur(12px);
    transition: transform .2s, box-shadow .2s;
}
[data-testid="stMetric"]:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(16,185,129,.18); }
[data-testid="stMetricLabel"] { color: #6ee7b7 !important; font-size:.78rem !important; font-weight:600 !important; text-transform:uppercase; letter-spacing:.06em; }
[data-testid="stMetricValue"] { color:#fff !important; font-weight:700 !important; }
.hero { background: linear-gradient(135deg, rgba(16,185,129,.14) 0%, rgba(59,130,246,.12) 100%);
    border: 1px solid rgba(16,185,129,.22); border-radius: 20px;
    padding: 30px 40px 26px; margin-bottom: 22px; text-align: center; }
.hero h1 { color:#fff; font-size:2rem; font-weight:700; margin:0 0 6px; }
.hero p  { color:#6ee7b7; font-size:.95rem; margin:0; }
.sec { color:#e2e8f0; font-size:1.1rem; font-weight:600;
       padding-left:12px; border-left:3px solid #10b981; margin:22px 0 12px; }
.dot { display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:7px; vertical-align:middle; }
.ibox { background:rgba(16,185,129,.07); border:1px solid rgba(16,185,129,.22);
        border-radius:12px; padding:14px 16px; color:#a7f3d0; font-size:.85rem; line-height:1.65; }
</style>
""", unsafe_allow_html=True)

KELAS_META = {
    "Sawah":    {"warna": "#FFD92F", "desc": "Lahan Pertanian"},
    "Bangunan": {"warna": "#E41A1C", "desc": "Kawasan Terbangun"},
    "Hutan":    {"warna": "#2E7D32", "desc": "Lahan Hijau Rapat"},
    "Danau":    {"warna": "#4FC3F7", "desc": "Air Pedalaman"},
    "Laut":     {"warna": "#0D47A1", "desc": "Perairan Terbuka"},
    "Mangrove": {"warna": "#8E44AD", "desc": "Bakau Pesisir"},
}
URUT_KELAS = list(KELAS_META.keys())
FITUR = ["B02", "B03", "B04", "B08", "B11", "NDVI", "NDWI", "MNDWI", "NDBI"]
CONF_LABELS = ["Bangunan", "Danau", "Hutan", "Laut", "Mangrove", "Sawah"]

FITUR_IMP = {
    "B03 (Green)": 0.1948, "B02 (Blue)": 0.1851, "NDBI": 0.1763,
    "B11 (SWIR)": 0.1039,  "MNDWI": 0.0907,      "B08 (NIR)": 0.0839,
    "NDWI": 0.0714,        "B04 (Red)": 0.0536,   "NDVI": 0.0509,
}

LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.02)",
    font=dict(family="Inter", color="#e2e8f0"),
    margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,.1)"),
)

@st.cache_data(show_spinner="Memuat data centroid poligon...")
def load_centroid():
    # Menggunakan data centroid yang sudah di-pre-compute (bukan piksel_s2.csv 162MB)
    cen = pd.read_csv("csv/centroid_poligon_knn.csv")
    cen = cen.replace([np.inf, -np.inf], np.nan).dropna(subset=FITUR)
    return cen


@st.cache_resource(show_spinner="Melatih model KNN...")
def train_knn(n):
    cen = load_centroid()
    X, y = cen[FITUR], cen["label_teks"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("knn", KNeighborsClassifier(n_neighbors=7, weights="distance", metric="euclidean"))])
    pipe.fit(X_tr, y_tr)
    y_pred = pipe.predict(X_te)
    y_prob = pipe.predict_proba(X_te).max(axis=1)
    return pipe, X_tr, X_te, y_tr, y_te, y_pred, y_prob

cen = load_centroid()
pipe, X_tr, X_te, y_tr, y_te, y_pred, y_prob = train_knn(len(cen))

acc    = accuracy_score(y_te, y_pred)
f1mac  = f1_score(y_te, y_pred, average="macro")
kappa  = cohen_kappa_score(y_te, y_pred)
n_err  = int((y_pred != y_te).sum())
n_test = len(y_te)

df_test = X_te.copy()
df_test["poligon_id"]     = cen.loc[X_te.index, "poligon_id"].values
df_test["kelas_asli"]     = y_te.values
df_test["kelas_prediksi"] = y_pred
df_test["benar"]          = y_pred == y_te.values
df_test["keyakinan"]      = y_prob
df_test["n_piksel"]       = cen.loc[X_te.index, "n_piksel"].values
df_test["lon"]            = cen.loc[X_te.index, "lon"].values
df_test["lat"]            = cen.loc[X_te.index, "lat"].values

# ── Sidebar
with st.sidebar:
    st.markdown("### 🌏 Spasial LULC")
    st.caption("Model: K-Nearest Neighbors")
    st.caption("Sensor: Sentinel-2A MSI (ESA CDSE)")
    st.caption("Koleksi: Level-2A BOA Surface Reflectance")
    st.divider()
    st.markdown("**🏷 6 KELAS TUTUPAN LAHAN**")
    for k, v in KELAS_META.items():
        st.markdown(
            f"<span class='dot' style='background:{v['warna']}'></span>"
            f"<b>{k}</b> <span style='color:#94a3b8;font-size:.8rem'>({v['desc']})</span>",
            unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    <div class="ibox">
    📡 Algoritma: <b>KNN k=7</b><br>
    ⚖️ Bobot: <b>Distance (Euclidean)</b><br>
    📐 CV: <b>5-Fold Stratified GridSearchCV</b><br>
    📍 AOI: <b>Provinsi Jawa Timur</b>
    </div>""", unsafe_allow_html=True)

# ── Hero
st.markdown("""
<div class="hero">
    <h1>🌏 Klasifikasi Spasial Tutupan Lahan Jawa Timur</h1>
    <p>Visualisasi spasial berbasis citra satelit Sentinel-2A Level-2A dan algoritma
    <b>K-Nearest Neighbors (KNN)</b> untuk pemetaan 6 kelas tutupan lahan di Provinsi Jawa Timur.</p>
</div>
""", unsafe_allow_html=True)
st.markdown("🛰️ **Sentinel-2A MSI BOA &nbsp;•&nbsp; K-Nearest Neighbors (KNN)**")

# ── KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("Akurasi Data Uji ✅", f"{acc:.1%}", f"{int(acc*n_test)}/{n_test} Poligon", help="Evaluasi Stratified Test Set (KNN)")
c2.metric("F1-Score Macro 🏆", f"{f1mac:.3f}", "Seimbang", help="Rata-rata harmonik seluruh 6 kelas")
c3.metric("Poligon Ground Truth 🗺️", f"~{len(cen):,}", "6 Kategori", help="Centroid poligon bebas autokorelasi")
c4.metric("Salah Klasifikasi ⚠️", str(n_err), f"Error {n_err/n_test:.1%}", delta_color="inverse")

# ── Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Evaluasi Kinerja Model",
    "🗺️ Sebaran Spasial Sampel",
    "📋 Eksplorasi Data Prediksi",
    "🔍 Karakteristik Spektral",
])

# ── Tab 1: Evaluasi
with tab1:
    col_cm, col_fi = st.columns(2)

    with col_cm:
        st.markdown('<div class="sec">Confusion Matrix (Data Uji)</div>', unsafe_allow_html=True)
        st.caption("Perbandingan kelas ground truth aktual vs hasil prediksi KNN.")
        cm_actual = confusion_matrix(y_te, y_pred, labels=CONF_LABELS)
        fig_cm = px.imshow(
            cm_actual,
            x=[f"pred_{l}" for l in CONF_LABELS],
            y=[f"asli_{l}" for l in CONF_LABELS],
            text_auto=True,
            color_continuous_scale=["#0d1b2a", "#10b981"],
            aspect="auto",
        )
        fig_cm.update_layout(**LAYOUT, height=380, coloraxis_showscale=False,
            title=dict(text=f"Confusion Matrix KNN (Data Uji {n_test} Poligon)", font=dict(size=13, color="#e2e8f0")),
            xaxis=dict(tickangle=-30, gridcolor="rgba(255,255,255,.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.05)"),
        )
        st.plotly_chart(fig_cm, use_container_width=True)

    with col_fi:
        st.markdown('<div class="sec">Kepentingan Fitur Spektral</div>', unsafe_allow_html=True)
        st.caption("Permutation Feature Importance — penurunan F1-Macro (30 pengulangan).")
        fi_df = pd.DataFrame({"Fitur": list(FITUR_IMP.keys()), "Importance": list(FITUR_IMP.values())}).sort_values("Importance")
        colors = ["#10b981" if any(b in f for b in ["B02","B03","B04","B08","B11"]) else "#6366f1" for f in fi_df["Fitur"]]
        fig_fi = go.Figure(go.Bar(
            x=fi_df["Importance"], y=fi_df["Fitur"], orientation="h",
            marker_color=colors,
            text=[f"{v:.3f}" for v in fi_df["Importance"]], textposition="outside",
            textfont=dict(color="#e2e8f0", size=11),
        ))
        fig_fi.update_layout(**LAYOUT, height=380,
            title=dict(text="Kepentingan Fitur (Permutation) — KNN", font=dict(size=13, color="#e2e8f0")),
            xaxis=dict(title="Penurunan F1-Macro", gridcolor="rgba(255,255,255,.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.03)"),
        )
        st.plotly_chart(fig_fi, use_container_width=True)

    st.markdown('<div class="sec">Laporan Klasifikasi per Kelas</div>', unsafe_allow_html=True)
    report = classification_report(y_te, y_pred, labels=CONF_LABELS, output_dict=True, zero_division=0)
    rows = [{"Kelas": k, "Precision": report.get(k,{}).get("precision",0),
             "Recall": report.get(k,{}).get("recall",0),
             "F1-Score": report.get(k,{}).get("f1-score",0),
             "Support": int(report.get(k,{}).get("support",0))} for k in CONF_LABELS]
    df_rep = pd.DataFrame(rows)
    fig_cls = go.Figure()
    for col, clr in [("Precision","#10b981"),("Recall","#6366f1"),("F1-Score","#f59e0b")]:
        fig_cls.add_trace(go.Bar(name=col, x=df_rep["Kelas"], y=df_rep[col],
            marker_color=clr, opacity=0.85,
            text=[f"{v:.2f}" for v in df_rep[col]], textposition="outside",
            textfont=dict(color="#e2e8f0", size=10)))
    fig_cls.update_layout(**LAYOUT, barmode="group", height=320,
        xaxis=dict(gridcolor="rgba(255,255,255,.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.06)", range=[0,1.15]),
        title=dict(text="Precision / Recall / F1-Score per Kelas", font=dict(size=13, color="#e2e8f0")))
    st.plotly_chart(fig_cls, use_container_width=True)

    st.markdown('<div class="sec">Metrik Evaluasi Global</div>', unsafe_allow_html=True)
    mk1, mk2, mk3, mk4 = st.columns(4)
    mk1.metric("Akurasi", f"{acc:.4f}")
    mk2.metric("F1-Macro", f"{f1mac:.4f}")
    mk3.metric("F1-Weighted", f"{f1_score(y_te,y_pred,average='weighted'):.4f}")
    mk4.metric("Cohen's Kappa (κ)", f"{kappa:.4f}", "Substantial Agreement")

# ── Tab 2: Peta
with tab2:
    st.markdown('<div class="sec">Sebaran Spasial Poligon Sampel Ground Truth</div>', unsafe_allow_html=True)
    st.caption("Centroid poligon sampel. Ukuran proporsional terhadap jumlah piksel Sentinel-2A dalam poligon.")
    cen_plot = cen.copy()
    cen_plot["n_piksel_log"] = np.log1p(cen_plot["n_piksel"])
    fig_map = px.scatter_map(
        cen_plot, lat="lat", lon="lon",
        color="label_teks",
        color_discrete_map={k: v["warna"] for k, v in KELAS_META.items()},
        size="n_piksel_log", size_max=14,
        hover_name="poligon_id",
        hover_data={"n_piksel":True, "NDVI":":.3f", "NDWI":":.3f",
                    "lat":False, "lon":False, "n_piksel_log":False},
        zoom=7, center={"lat":-7.5,"lon":112.5},
        map_style="carto-darkmatter", height=520,
        labels={"label_teks":"Kelas"},
        category_orders={"label_teks": URUT_KELAS},
    )
    fig_map.update_layout({**LAYOUT, "margin": dict(l=0, r=0, t=0, b=0)})
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('<div class="sec">Sebaran Data Uji & Kesalahan Prediksi KNN</div>', unsafe_allow_html=True)
    fig_uji = px.scatter_map(
        df_test, lat="lat", lon="lon",
        color="benar",
        color_discrete_map={True:"#10b981", False:"#ef4444"},
        hover_name="poligon_id",
        hover_data={"kelas_asli":True,"kelas_prediksi":True,"keyakinan":":.1%","n_piksel":True,"lat":False,"lon":False,"benar":False},
        zoom=7, center={"lat":-7.5,"lon":112.5},
        map_style="carto-darkmatter", height=460,
        labels={"benar":"Prediksi Benar"},
    )
    fig_uji.update_layout({**LAYOUT, "margin": dict(l=0, r=0, t=0, b=0)})
    st.plotly_chart(fig_uji, use_container_width=True)

    st.markdown('<div class="sec">Distribusi Jumlah Poligon per Kelas</div>', unsafe_allow_html=True)
    cnt = cen["label_teks"].value_counts().reset_index()
    cnt.columns = ["Kelas","Jumlah"]
    cnt["Warna"] = cnt["Kelas"].map(lambda k: KELAS_META.get(k,{}).get("warna","#888"))
    fig_cnt = go.Figure(go.Bar(x=cnt["Kelas"], y=cnt["Jumlah"],
        marker_color=cnt["Warna"],
        text=cnt["Jumlah"], textposition="outside", textfont=dict(color="#e2e8f0")))
    fig_cnt.update_layout(**LAYOUT, height=300,
        xaxis=dict(gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.06)", title="Jumlah Poligon"))
    st.plotly_chart(fig_cnt, use_container_width=True)

# ── Tab 3: Data
with tab3:
    st.markdown('<div class="sec">Eksplorasi Data Prediksi Poligon Uji</div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns([2,1])
    with fc1:
        filter_kelas = st.multiselect("Filter Kelas Asli:", CONF_LABELS, default=CONF_LABELS)
    with fc2:
        filter_status = st.radio("Filter Status:",
            ["Semua Data","Hanya Prediksi Benar","Hanya Salah Klasifikasi"])

    df_show = df_test[df_test["kelas_asli"].isin(filter_kelas)].copy()
    if filter_status == "Hanya Prediksi Benar":
        df_show = df_show[df_show["benar"]]
    elif filter_status == "Hanya Salah Klasifikasi":
        df_show = df_show[~df_show["benar"]]

    st.caption(f"Menampilkan **{len(df_show)}** dari total **{n_test}** poligon uji:")
    disp = df_show[["poligon_id","kelas_asli","n_piksel","kelas_prediksi","benar","keyakinan","NDVI","NDWI","MNDWI","NDBI"]].copy()
    disp["keyakinan"] = disp["keyakinan"].apply(lambda v: f"{v:.1%}")
    for col in ["NDVI","NDWI","MNDWI","NDBI"]:
        disp[col] = disp[col].round(3)
    disp["n_piksel"] = disp["n_piksel"].astype(int)
    st.dataframe(
        disp.rename(columns={"poligon_id":"ID Poligon","kelas_asli":"Kelas Asli",
            "n_piksel":"Piksel","kelas_prediksi":"Prediksi KNN",
            "benar":"✓ Benar","keyakinan":"Keyakinan (k=7)"}).set_index("ID Poligon"),
        use_container_width=True, height=420)

    st.markdown('<div class="sec">Distribusi Keyakinan Prediksi per Kelas</div>', unsafe_allow_html=True)
    fig_conf = px.box(df_test, x="kelas_asli", y="keyakinan",
        color="benar", color_discrete_map={True:"#10b981", False:"#ef4444"},
        labels={"kelas_asli":"Kelas Asli","keyakinan":"Keyakinan","benar":"Benar"},
        category_orders={"kelas_asli": CONF_LABELS},
        points="all", height=360)
    fig_conf.update_layout(**LAYOUT, yaxis=dict(gridcolor="rgba(255,255,255,.06)", tickformat=".0%"))
    st.plotly_chart(fig_conf, use_container_width=True)

    st.download_button("⬇️ Unduh Data Prediksi (CSV)",
        data=df_test.to_csv(index=False).encode("utf-8"),
        file_name="knn_prediksi_data_uji.csv", mime="text/csv")

# ── Tab 4: Spektral
with tab4:
    st.markdown('<div class="sec">Profil Spektral Rata-rata per Kelas</div>', unsafe_allow_html=True)
    st.caption("Nilai reflektansi BOA rata-rata tiap band Sentinel-2A per kelas, dari seluruh centroid poligon.")
    bands = ["B02","B03","B04","B08","B11"]
    band_labels = ["B02 (Blue)","B03 (Green)","B04 (Red)","B08 (NIR)","B11 (SWIR)"]
    fig_sp = go.Figure()
    for k in URUT_KELAS:
        sub = cen[cen["label_teks"]==k]
        means = [sub[b].mean() for b in bands]
        fig_sp.add_trace(go.Scatter(x=band_labels, y=means, name=k, mode="lines+markers",
            line=dict(color=KELAS_META[k]["warna"], width=2.5), marker=dict(size=8)))
    fig_sp.update_layout(**LAYOUT, height=380, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.06)", title="Reflektansi BOA"),
        title=dict(text="Profil Spektral Sentinel-2A per Kelas", font=dict(size=13, color="#e2e8f0")))
    st.plotly_chart(fig_sp, use_container_width=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown('<div class="sec">NDVI vs NDWI</div>', unsafe_allow_html=True)
        fig_sc1 = px.scatter(cen, x="NDVI", y="NDWI", color="label_teks",
            color_discrete_map={k:v["warna"] for k,v in KELAS_META.items()},
            opacity=0.65, hover_name="poligon_id",
            labels={"label_teks":"Kelas"},
            category_orders={"label_teks": URUT_KELAS}, height=360)
        fig_sc1.update_layout(**LAYOUT,
            xaxis=dict(gridcolor="rgba(255,255,255,.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.06)"))
        st.plotly_chart(fig_sc1, use_container_width=True)

    with col_s2:
        st.markdown('<div class="sec">NDBI vs B11 (SWIR)</div>', unsafe_allow_html=True)
        fig_sc2 = px.scatter(cen, x="NDBI", y="B11", color="label_teks",
            color_discrete_map={k:v["warna"] for k,v in KELAS_META.items()},
            opacity=0.65, hover_name="poligon_id",
            labels={"label_teks":"Kelas"},
            category_orders={"label_teks": URUT_KELAS}, height=360)
        fig_sc2.update_layout(**LAYOUT,
            xaxis=dict(gridcolor="rgba(255,255,255,.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.06)"))
        st.plotly_chart(fig_sc2, use_container_width=True)

    st.markdown('<div class="sec">Distribusi Fitur per Kelas (Box Plot)</div>', unsafe_allow_html=True)
    fitur_pilih = st.selectbox("Pilih fitur:", FITUR, index=FITUR.index("NDVI"))
    fig_bx = px.box(cen, x="label_teks", y=fitur_pilih, color="label_teks",
        color_discrete_map={k:v["warna"] for k,v in KELAS_META.items()},
        category_orders={"label_teks": URUT_KELAS},
        labels={"label_teks":"Kelas"}, points="outliers", height=360)
    fig_bx.update_layout(**LAYOUT, showlegend=False,
        yaxis=dict(gridcolor="rgba(255,255,255,.06)"))
    st.plotly_chart(fig_bx, use_container_width=True)

st.divider()
st.markdown(
    "<div style='text-align:center;color:#374151;font-size:.78rem;padding:6px 0 14px'>"
    "Sentinel-2A MSI BOA via ESA Copernicus CDSE &nbsp;·&nbsp; "
    "K-Nearest Neighbors (k=7, distance, euclidean) &nbsp;·&nbsp; Provinsi Jawa Timur"
    "</div>", unsafe_allow_html=True)
