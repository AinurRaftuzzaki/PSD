---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Panduan Deployment Visualisasi Spasial ke Streamlit

Panduan ini mendokumentasikan langkah demi langkah (**step-by-step**) untuk mendeploy visualisasi hasil pemodelan klasifikasi tutupan lahan (*Land Use / Land Cover* - LULC) Jawa Timur dari materi {doc}`klasifikasi-spasial-tutupan-lahan-knn` ke dalam aplikasi web interaktif berbasis **Streamlit**, baik untuk dijalankan di lingkungan lokal (*local development*) maupun dipublikasikan secara daring (*cloud hosting*) melalui **Streamlit Community Cloud**.

---

## 1. Ringkasan Aset Visualisasi dari Notebook

Dari eksperimen pemodelan klasifikasi spasial, terdapat tiga kategori visualisasi dan data yang dihasilkan:

| Kategori Aset | File Sumber | Deskripsi Visualisasi |
| :--- | :--- | :--- |
| **Peta Interaktif 1 (Vektor)** | `peta_klasifikasi_rf.html` / `peta_klasifikasi_knn.html` | Peta interaktif Folium berbasis poligon sampel 6 kelas tutupan lahan (~300 poligon), dilengkapi layer sorotan data uji (outline biru), layer salah klasifikasi (outline oranye + ikon peringatan), serta popup rincian nilai spektral (NDVI, NDWI, jumlah piksel, dan probabilitas prediksi). |
| **Peta Interaktif 2 (Regional)** | `hasil_klasifikasi_random_forest.html` / `hasil_klasifikasi_knn.html` | Peta inferensi spasial skala regional seluruh daratan Jawa Timur berbasis grid resolusi tinggi (~200m/piksel) dengan overlay transparan 6 kelas di atas citra satelit *Esri World Imagery* (z=10). |
| **Grafik Evaluasi Model** | `confusion_matrix.png`, `kepentingan_fitur.png` | Visualisasi matriks kontinjensi (*confusion matrix*) data uji (akurasi 96.4%) dan diagram batang kepentingan fitur Gini (*feature importance*) yang menonjolkan peran dominan band SWIR (B11) dan NDBI. |
| **Data Tabular Evaluasi** | `prediksi_data_uji.csv`, `confusion_matrix.csv`, `kepentingan_fitur.csv` | Data 83 poligon uji beserta kelas aktual, hasil prediksi model Random Forest / KNN, status kebenaran prediksi, dan nilai probabilitas setiap kelas. |

---

## 2. Arsitektur & Strategi Rendering di Streamlit

Dalam mendeploy visualisasi geospasial Folium ke Streamlit, terdapat dua pendekatan utama:

```{list-table} Perbandingan Pendekatan Rendering Peta di Streamlit
:header-rows: 1

* - Pendekatan
  - Cara Kerja
  - Kelebihan
  - Rekomendasi Penggunaan
* - **Metode 1: Pre-rendered HTML IFrame** *(Rekomendasi Utama)*
  - Membaca file peta HTML yang diekspor dari Folium (`peta.save()`) lalu merendernya via `streamlit.components.v1.html(konten_html, height=720)`.
  - **Sangat cepat & ringan**: Waktu pemuatan (*loading time*) instan. Menghindari konsumsi RAM server cloud berlebih karena komputasi piksel berat (1536 x 896) tidak diulang setiap kali pengguna berinteraksi.
  - **Terbaik untuk produksi & Streamlit Cloud** (free tier RAM 1 GB).
* - **Metode 2: Dynamic Python Folium (`streamlit-folium`)**
  - Mengonstruksi objek `folium.Map` secara dinamis di kode Python Streamlit dan dirender via `st_folium(peta)`.
  - Memungkinkan komunikasi dua arah (menangkap koordinat klik pengguna atau poligon yang dipilih untuk filter data).
  - Membutuhkan waktu render ulang saat state widget berubah; memerlukan dependensi tambahan `streamlit-folium`.
```

Pada panduan ini, kita menerapkan **arsitektur hibrida terbaik**:
1. Merender peta interaktif berskala besar menggunakan **IFrame komponen HTML** teroptimasi.
2. Menyajikan kartu metrik, filter interaktif, diagram evaluasi, tabel data uji, dan fitur ekspor CSV menggunakan **fitur native Streamlit**.

---

## 3. Struktur Direktori Proyek Deployment

Untuk mempublikasikan aplikasi ke GitHub dan Streamlit Community Cloud secara rapi dan mandiri (*standalone*), siapkan struktur folder sebagai berikut:

```text
streamlit_spasial_jatim/
│
├── .streamlit/
│   └── config.toml                 # Konfigurasi tema warna & batas unggahan
│
├── data/
│   ├── prediksi_data_uji.csv       # Hasil prediksi data uji
│   ├── confusion_matrix.csv        # Tabel matriks kontinjensi
│   ├── kepentingan_fitur.csv       # Nilai Gini feature importance
│   ├── confusion_matrix.png        # Grafik gambar confusion matrix
│   └── kepentingan_fitur.png       # Grafik gambar feature importance
│
├── maps/
│   ├── peta_klasifikasi_rf.html              # Peta evaluasi poligon sampel
│   └── hasil_klasifikasi_random_forest.html  # Peta regional se-Jawa Timur
│
├── app.py                          # Skrip utama aplikasi Streamlit
├── requirements.txt                # Daftar library Python yang dibutuhkan
└── README.md                       # Dokumentasi repositori
```

```{tip}
Jika dijalankan di dalam repositori proyek sains data ini, file skrip `streamlit_app.py` sudah dilengkapi algoritma pencari file otomatis (`cari_file()`), sehingga dapat langsung membaca aset dari folder `data/Klasifikasi/` dan `data/Klasifikasi/hasil_rf/` tanpa perlu memindahkan file secara manual.
```

---

## 4. Kode Lengkap Aplikasi Streamlit (`app.py`)

Simpan kode berikut sebagai `app.py`:

```python
"""
Dashboard Klasifikasi Spasial Tutupan Lahan (LULC) Jawa Timur
Berbasis Sentinel-2A Level-2A & Algoritma Random Forest / KNN
"""

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from PIL import Image

# ==============================================================================
# 1. KONFIGURASI HALAMAN & TEMA
# ==============================================================================
st.set_page_config(
    page_title="Klasifikasi Spasial Tutupan Lahan Jawa Timur",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1b4332;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #495057;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f1f3f5;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2d6a4f !important;
        color: white !important;
    }
    .info-box {
        background: #e8f5e9;
        border-left: 4px solid #2e7d32;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 10px 0 15px 0;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. HELPER PENCARIAN FILE ASET & CACHING
# ==============================================================================
def cari_file(nama_file: str) -> Path | None:
    """Mencari file di berbagai kemungkinan direktori lokal."""
    kandidat = [
        Path(nama_file),
        Path("maps") / nama_file,
        Path("data") / nama_file,
        Path("data/Klasifikasi") / nama_file,
        Path("views/klasifikasi-spasial") / nama_file,
        Path("data/Klasifikasi/hasil_rf") / nama_file,
        Path("hasil_rf") / nama_file,
    ]
    for path in kandidat:
        if path.exists():
            return path
    return None


@st.cache_data
def muat_data_csv(path_str: str) -> pd.DataFrame | None:
    path = Path(path_str)
    if path.exists():
        return pd.read_csv(path)
    return None


@st.cache_data
def muat_konten_html(path_str: str) -> str | None:
    path = Path(path_str)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


# ==============================================================================
# 3. SIDEBAR: METADATA & FILTER
# ==============================================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e0/Sentinel-2_model.png", width=260)
    st.markdown("### 🛰️ Spasial LULC Jawa Timur")
    st.caption("**Model**: Random Forest Classifier / KNN (Scikit-Learn)")
    st.caption("**Sensor**: Sentinel-2A MSI (ESA Copernicus)")
    st.caption("**Koleksi**: Level-2A Surface Reflectance (BOA)")
    
    st.markdown("---")
    st.markdown("#### 🏷️ 6 Kelas Tutupan Lahan")
    st.markdown("""
    - <span style='color:#FFD92F; font-weight:bold;'>■</span> **Sawah**: Lahan pertanian padi
    - <span style='color:#E41A1C; font-weight:bold;'>■</span> **Bangunan**: Perkotaan / pemukiman
    - <span style='color:#2E7D32; font-weight:bold;'>■</span> **Hutan / Lahan Hijau**: Kanopi rapat
    - <span style='color:#4FC3F7; font-weight:bold;'>■</span> **Danau**: Badan air pedalaman
    - <span style='color:#0D47A1; font-weight:bold;'>■</span> **Laut**: Perairan terbuka pesisir
    - <span style='color:#8E44AD; font-weight:bold;'>■</span> **Mangrove**: Hutan bakau pasang-surut
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### ⚙️ Pengaturan Tampilan")
    tinggi_peta = st.slider("Tinggi Frame Peta (px):", min_value=500, max_value=950, value=720, step=20)
    st.info("💡 **Tips**: Gunakan tab di layar utama untuk berpindah antara peta poligon, peta regional, dan metrik model.")


# ==============================================================================
# 4. HEADER UTAMA & KARTU METRIK RINGKASAN
# ==============================================================================
st.markdown("<div class='main-title'>Dashboard Klasifikasi Spasial Tutupan Lahan Jawa Timur</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Visualisasi Geospasial Interaktif dan Evaluasi Model Machine Learning "
    "berbasis Citra Satelit Sentinel-2A</div>",
    unsafe_allow_html=True
)

# Memuat data hasil evaluasi
p_pred = cari_file("prediksi_data_uji.csv")
df_pred = muat_data_csv(str(p_pred)) if p_pred else None

# Baris Metrik Utama
col1, col2, col3, col4 = st.columns(4)
if df_pred is not None:
    n_uji = len(df_pred)
    n_benar = int(df_pred["benar"].sum())
    n_salah = n_uji - n_benar
    akurasi = (n_benar / n_uji) * 100
    
    with col1:
        st.metric(label="🎯 Akurasi Data Uji", value=f"{akurasi:.1f}%", delta=f"{n_benar}/{n_uji} Poligon")
    with col2:
        st.metric(label="📐 F1-Score Macro", value="0.963", delta="Keseimbangan Kelas Tinggi")
    with col3:
        st.metric(label="📦 Total Poligon Sampel", value="~300", delta="6 Kelas Tutupan Lahan")
    with col4:
        st.metric(label="⚠️ Salah Klasifikasi", value=f"{n_salah} Poligon", delta="-3.6% Error", delta_color="inverse")
else:
    with col1:
        st.metric(label="🎯 Akurasi Data Uji", value="96.4%")
    with col2:
        st.metric(label="📐 F1-Score Macro", value="0.963")
    with col3:
        st.metric(label="📦 Total Poligon Sampel", value="~300")
    with col4:
        st.metric(label="🛰️ Fitur Spektral", value="9 Fitur (5 Band + 4 Indeks)")


# ==============================================================================
# 5. TAB NAVIGASI UTAMA
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Peta Evaluasi Poligon (Vector)",
    "🌏 Peta Regional Skala Jawa Timur (High-Res)",
    "📊 Evaluasi Model & Feature Importance",
    "📋 Eksplorasi Data Uji & Ekspor"
])

# TAB 1: PETA POLIGON
with tab1:
    st.markdown("### 🗺️ Peta Evaluasi Poligon Sampel & Hasil Prediksi Data Uji")
    st.markdown("""
    <div class='info-box'>
        <b>Panduan Layer Peta:</b>
        <ul>
            <li><b>Layer 6 Kelas:</b> Menampilkan poligon ground truth utuh dengan warna standar GIS.</li>
            <li><b>Outline Biru:</b> Poligon subset <i>Data Uji (Testing)</i> yang diuji oleh model.</li>
            <li><b>Outline Oranye + Tanda Seru:</b> Poligon yang <b>salah diklasifikasikan</b> oleh model.</li>
            <li><b>Klik Poligon:</b> Menampilkan popup nilai NDVI, NDWI, jumlah piksel, dan probabilitas kelas.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    file_peta1 = cari_file("peta_klasifikasi_rf.html") or cari_file("peta_klasifikasi_knn.html")
    if file_peta1:
        konten_html1 = muat_konten_html(str(file_peta1))
        components.html(konten_html1, height=tinggi_peta, scrolling=True)
    else:
        st.error("File `peta_klasifikasi_rf.html` / `peta_klasifikasi_knn.html` tidak ditemukan.")

# TAB 2: PETA REGIONAL JAWA TIMUR
with tab2:
    st.markdown("### 🌏 Peta Inferensi Klasifikasi Tutupan Lahan Se-Jawa Timur")
    st.markdown("""
    <div class='info-box'>
        <b>Karakteristik Peta Regional:</b>
        <ul>
            <li><b>Resolusi Tinggi Granular:</b> Grid inferensi 1536 x 896 piksel (~200m per piksel) seluruh Jawa Timur.</li>
            <li><b>Esri Satellite Mosaic (z=10):</b> Citra satelit tertanam dengan lapisan prediksi transparan (opasitas 65%).</li>
            <li><b>Masking Daratan:</b> Menggunakan batas provinsi Jawa Timur untuk membedakan daratan dan laut terbuka.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    file_peta2 = cari_file("hasil_klasifikasi_random_forest.html") or cari_file("hasil_klasifikasi_knn.html")
    if file_peta2:
        konten_html2 = muat_konten_html(str(file_peta2))
        components.html(konten_html2, height=tinggi_peta, scrolling=True)
    else:
        st.error("File `hasil_klasifikasi_random_forest.html` / `hasil_klasifikasi_knn.html` tidak ditemukan.")

# TAB 3: EVALUASI PERFORMA
with tab3:
    st.markdown("### 📊 Evaluasi Kinerja Model")
    col_kiri, col_kanan = st.columns(2)
    
    with col_kiri:
        st.markdown("#### 🎯 Confusion Matrix (Data Uji)")
        p_cm_img = cari_file("confusion_matrix.png")
        if p_cm_img:
            st.image(Image.open(p_cm_img), caption="Confusion Matrix Data Uji", use_container_width=True)
        else:
            p_cm_csv = cari_file("confusion_matrix.csv")
            if p_cm_csv:
                st.dataframe(pd.read_csv(p_cm_csv, index_col=0), use_container_width=True)
        st.caption("Akurasi data uji mencapai 96.4% (80 dari 83 poligon benar).")
    
    with col_kanan:
        st.markdown("#### 🌲 Kepentingan Fitur Spektral (Gini Importance)")
        p_fi_img = cari_file("kepentingan_fitur.png")
        if p_fi_img:
            st.image(Image.open(p_fi_img), caption="Feature Importance Model", use_container_width=True)
        else:
            p_fi_csv = cari_file("kepentingan_fitur.csv")
            if p_fi_csv:
                st.dataframe(pd.read_csv(p_fi_csv), use_container_width=True)
        st.caption("Band SWIR (B11) dan indeks NDBI berkontribusi paling dominan dalam pemisahan kelas.")

# TAB 4: TABEL DATA & EKSPOR
with tab4:
    st.markdown("### 📋 Detail Prediksi Data Uji (83 Poligon)")
    if df_pred is not None:
        c1, c2 = st.columns(2)
        with c1:
            pilihan_kelas = st.multiselect(
                "Filter Kelas Asli:",
                options=sorted(df_pred["kelas_asli"].unique()),
                default=sorted(df_pred["kelas_asli"].unique())
            )
        with c2:
            status_filter = st.radio(
                "Filter Status Prediksi:",
                options=["Semua", "Hanya Benar", "Hanya Salah Klasifikasi"],
                horizontal=True
            )
        
        df_tampil = df_pred[df_pred["kelas_asli"].isin(pilihan_kelas)].copy()
        if status_filter == "Hanya Benar":
            df_tampil = df_tampil[df_tampil["benar"] == True]
        elif status_filter == "Hanya Salah Klasifikasi":
            df_tampil = df_tampil[df_tampil["benar"] == False]
            
        st.write(f"Menampilkan **{len(df_tampil)}** dari total **{len(df_pred)}** poligon uji:")
        st.dataframe(df_tampil, use_container_width=True, height=350)
        
        csv_bytes = df_tampil.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Unduh Data Hasil Prediksi (CSV)",
            data=csv_bytes,
            file_name="hasil_prediksi_data_uji.csv",
            mime="text/csv"
        )
    else:
        st.warning("File `prediksi_data_uji.csv` tidak ditemukan.")

# FOOTER
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6c757d; font-size: 0.85rem;'>"
    "Proyek Sains Data — Klasifikasi Spasial LULC Jawa Timur | Sentinel-2A"
    "</div>",
    unsafe_allow_html=True
)
```

---

## 5. Konfigurasi Dependensi & Tema

### 5.1. File `requirements.txt`

Buat file `requirements.txt` dengan isi berikut:

```text
streamlit>=1.30.0
pandas>=2.0.0
numpy>=1.24.0
pillow>=9.5.0
matplotlib>=3.7.0
```

```{note}
Karena peta interaktif dibaca dalam format HTML (`peta_klasifikasi_rf.html` dan `hasil_klasifikasi_random_forest.html`), library berat seperti `geopandas`, `rasterio`, atau `openeo` **tidak perlu** diinstal di lingkungan Streamlit runtime. Hal ini membuat waktu instalasi dependensi di cloud menjadi sangat cepat (< 1 menit) dan tidak membebani limit memori.
```

### 5.2. File `.streamlit/config.toml` (Opsional untuk Personalisasi Tema)

Buat direktori `.streamlit/` dan file `config.toml`:

```toml
[theme]
primaryColor = "#2d6a4f"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8f9fa"
textColor = "#212529"
font = "sans serif"

[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = true
```

---

## 6. Langkah-Langkah Menjalankan di Komputer Lokal (*Local Run*)

Berikut tahapan menjalankan aplikasi di komputer lokal:

### Langkah 1: Buka Terminal / PowerShell
Pastikan Anda berada di direktori kerja proyek:
```bash
cd "d:/PSD/Tugas"
```

### Langkah 2: Buat & Aktifkan Virtual Environment (Rekomendasi)
```bash
# Membuat virtual environment
python -m venv .venv

# Aktivasi di Windows PowerShell:
.venv\Scripts\Activate.ps1

# Atau di Command Prompt (cmd):
.venv\Scripts\activate.bat

# Atau di Linux/macOS:
source .venv/bin/activate
```

### Langkah 3: Instal Dependensi
```bash
pip install -r requirements.txt
```

### Langkah 4: Jalankan Aplikasi Streamlit
```bash
streamlit run app.py
```

### Langkah 5: Buka di Browser
Aplikasi secara otomatis membuka peramban di alamat:
```text
http://localhost:8501
```

---

## 7. Langkah-Langkah Deploy ke Streamlit Community Cloud

Streamlit Community Cloud ([share.streamlit.io](https://share.streamlit.io/)) menyediakan hosting gratis untuk aplikasi Streamlit langsung dari repositori GitHub.

### Tahap 1: Persiapan Repositori GitHub

1. Buat repositori baru di GitHub (misal: `klasifikasi-spasial-jatim-streamlit`).
2. Pastikan file `.gitignore` dibuat agar file besar yang tidak digunakan di runtime (seperti file zip mentah atau GeoTIFF ratusan MB) tidak ikut terunggah:

```gitignore
# .gitignore
.venv/
__pycache__/
*.tif
*.tiff
*.zip
dataset.csv
```

3. Lakukan inisialisasi git, commit, dan push:
```bash
git init
git add app.py requirements.txt .streamlit/ data/ maps/ README.md
git commit -m "feat: inisialisasi aplikasi dashboard spasial tutupan lahan jatim"
git branch -M main
git remote add origin https://github.com/<username-anda>/<nama-repo-anda>.git
git push -u origin main
```

### Tahap 2: Mendaftarkan Aplikasi di Streamlit Cloud

1. Kunjungi [https://share.streamlit.io/](https://share.streamlit.io/) dan login menggunakan akun **GitHub** Anda.
2. Klik tombol **"Create app"** (atau **"New app"**).
3. Isi formulir konfigurasi deployment:
   * **Repository**: Pilih repositori GitHub Anda (misal: `<username>/klasifikasi-spasial-jatim-streamlit`).
   * **Branch**: `main`.
   * **Main file path**: `app.py` (atau `streamlit_app.py` sesuai nama file utama Anda).
   * **App URL (opsional)**: Tentukan subdomain khusus (misal: `klasifikasi-spasial-jatim.streamlit.app`).
4. Klik tombol **"Deploy!"**.

### Tahap 3: Pemantauan Build & Peluncuran

1. Buka tab **"Manage app"** di pojok kanan bawah untuk memantau proses instalasi *dependencies* dari `requirements.txt`.
2. Setelah proses instalasi selesai (biasanya berlangsung 1–2 menit), aplikasi akan langsung aktif dan dapat diakses publik melalui tautan:
   ```text
   https://<nama-subdomain>.streamlit.app
   ```

---

## 8. Tips Optimasi, Best Practices, & Troubleshooting

### 1. Menghindari Out of Memory (OOM) di Streamlit Cloud
* **Penyebab**: Server gratis Streamlit Cloud memiliki alokasi memori RAM sebesar 1 GB. Melakukan rasterisasi citra regional Jawa Timur ($1536 \times 896$) atau *training* model langsung di runtime web server dapat memicu penghentian paksa (*crash OOM*).
* **Solusi**: Lakukan proses *training* dan *raster rendering* di lingkungan Jupyter Notebook. Simpan hasilnya menjadi file HTML serta file metrik CSV/PNG. Aplikasi Streamlit cukup bertugas sebagai antarmuka penyaji visualisasi (*presentation layer*).

### 2. Mengatasi Scroll Ganda pada IFrame Folium
* Atur parameter `scrolling=True` dan tinggi komponen yang cukup (`height=720` atau lebih) pada `components.html(konten_html, height=tinggi_peta, scrolling=True)` agar pengguna dapat melakukan pergeseran peta (*panning*) dan pembesaran (*zooming*) dengan lancar tanpa terpotong oleh batas kontainer.

### 3. Menggunakan `@st.cache_data` untuk File CSV
* Terapkan dekorator `@st.cache_data` pada fungsi pemuatan data (`muat_data_csv()` dan `muat_konten_html()`). Dengan caching, file hanya dibaca satu kali dari disk ke memori, sehingga interaksi pengguna (seperti pemilihan filter kelas tutupan lahan) akan dieksekusi secara instan tanpa lag.
