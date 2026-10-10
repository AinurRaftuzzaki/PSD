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

# Klasifikasi Spasial Tutupan Lahan Jawa Timur (K-Nearest Neighbors / KNN)

Dokumentasi ini menyajikan alur lengkap (*end-to-end pipeline*) klasifikasi spasial tutupan lahan (*Land Use / Land Cover* - LULC) skala regional di **Provinsi Jawa Timur** berbasis citra satelit optik **Sentinel-2A Level-2A (Bottom-of-Atmosphere / BOA Surface Reflectance)** dan algoritma **K-Nearest Neighbors (KNN)** terstandarisasi.

> [!TIP]
> **Aplikasi Web Interaktif (Streamlit Cloud)**:  
> Seluruh visualisasi spasial, kedua peta interaktif, dan evaluasi performa model dapat dieksplorasi secara dinamis pada aplikasi web:  
> 🌐 **[https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/](https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/)**

Alur kerja mencakup:
1. **Data Understanding**: Pemahaman domain 6 kelas tutupan lahan, karakteristik spektral band Sentinel-2A, formula indeks vegetasi, air, & lahan terbangun, serta struktur data ground truth hasil crawling lokal.
2. **Pengambilan Data (Data Acquisition / Crawling via openEO)**: Manajemen *batch job* asinkron multi-backend pada Copernicus Data Space Ecosystem (CDSE), strategi *spatial grid tiling*, masking awan berbasis *Scene Classification Layer* (SCL), dan ekstraksi piksel GeoTIFF ke format tabular.
3. **Data Preprocessing & Agregasi Spasial**: Agregasi fitur piksel menjadi *centroid* poligon untuk mengeliminasi kebocoran autokorelasi spasial (*spatial autocorrelation leakage*).
4. **Pemodelan Machine Learning (K-Nearest Neighbors / KNN)**: Standarisasi fitur (*StandardScaler*), optimasi hyperparameter $k$, fungsi bobot (*weights*), dan metrik jarak (*metric distance*) menggunakan *GridSearchCV* 5-Fold Stratified Cross-Validation, evaluasi data uji independen, analisis *confusion matrix*, dan *permutation feature importance*.
5. **Visualisasi Spasial & Pemetaan Interaktif**: Pembuatan peta evaluasi poligon interaktif Folium dengan status prediksi & probabilitas keyakinan KNN, serta inferensi klasifikasi per piksel skala regional seluruh Jawa Timur.

---

## Instalasi Library & Kebutuhan Lingkungan

Untuk menjalankan seluruh pipeline akuisisi data, ekstraksi citra satelit, pemodelan KNN, hingga visualisasi peta interaktif, instal dependensi Python berikut:

```bash
pip install openeo geopandas rasterio shapely scikit-learn pandas numpy folium matplotlib pillow joblib requests
```

---

## 1. Data Understanding & Karakteristik Data Spasial

### 1.1. Definisi Domain dan 6 Kelas Tutupan Lahan

Area of Interest (AOI) mencakup seluruh wilayah daratan dan perairan pesisir Provinsi Jawa Timur pada koordinat batas geografis:
* **Batas Barat (West)**: $111.00^\circ\text{ E}$
* **Batas Selatan (South)**: $-8.85^\circ\text{ S}$
* **Batas Timur (East)**: $114.65^\circ\text{ E}$
* **Batas Utara (North)**: $-6.75^\circ\text{ S}$

Objek permukaan bumi dikelompokkan ke dalam **6 kelas tutupan lahan** utama:

| No | Nama Kelas | Kode Label | Definisi & Karakteristik Objek | Respon Spektral Utama |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **Sawah** | `1` | Lahan pertanian padi basah berpetak. Kondisi bervariasi dari genangan air awal tanam, fase vegetatif hijau pekat, hingga fase pematangan/panen. | Pantulan NIR sedang-tinggi pada fase vegetatif; nilai SWIR meningkat pada lahan bera/kering; fluktuasi indeks kebasahan. |
| 2 | **Bangunan** | `2` | Kawasan terbangun perkotaan, permukiman, jalan aspal/beton, dan atap bangunan (genteng/seng/beton). | Pantulan tinggi pada band SWIR (B11) dan Red (B04); nilai NDBI positif tinggi; nilai NDVI rendah. |
| 3 | **Hutan (Lahan Hijau)** | `3` | Vegetasi alami kanopi pohon lebat, hutan pegunungan, perbukitan hijau, dan perkebunan tahunan rapat. | Pantulan sangat tinggi pada NIR (B08) akibat struktur sel daun; serapan kuat pada Red (B04); NDVI sangat tinggi ($> 0.6$). |
| 4 | **Danau** | `4` | Badan air tawar pedalaman (danau alami, waduk, telaga, bendungan) berarus tenang. | Penyerapan kuat pada inframerah (NIR dan SWIR); nilai NDWI dan MNDWI positif tinggi; NDVI bernilai negatif. |
| 5 | **Laut (Perairan Terbuka)** | `5` | Badan air asin laut terbuka di pesisir utara dan selatan Jawa Timur serta Selat Madura. | Pantulan dominan pada band Blue (B02) dan Green (B03); penyerapan hampir total pada NIR/SWIR; NDWI tinggi. |
| 6 | **Mangrove** | `6` | Komunitas hutan bakau pesisir yang toleran terhadap air asin/payau, tumbuh di muara sungai dan pantai berlumpur. | Kombinasi sinyal vegetasi lebat (NIR tinggi) dan pengaruh substrat air/lumpur basah (SWIR rendah, MNDWI relatif tinggi dibanding hutan daratan). |

---

### 1.2. Karakteristik Citra Satelit Sentinel-2A Level-2A

Dataset citra satelit diperoleh dari satelit optik **Sentinel-2A Level-2A (Bottom-of-Atmosphere / BOA Surface Reflectance)** yang disediakan oleh *European Space Agency* (ESA) melalui *Copernicus Data Space Ecosystem* (CDSE). 

Band spektral yang digunakan meliputi:

* **B02 (Blue - 490 nm)**: Resolusi spasial 10 meter. Sensitif terhadap kedalaman air, hamburan atmosfer, dan pemisah utama perairan laut jernih.
* **B03 (Green - 560 nm)**: Resolusi spasial 10 meter. Puncak pantulan klorofil daun pada spektrum tampak dan deteksi kekeruhan air/sedimen.
* **B04 (Red - 665 nm)**: Resolusi spasial 10 meter. Pita serapan utama klorofil; sangat berguna membedakan vegetasi hidup dari tanah terbuka atau bangunan.
* **B08 (Near Infrared / NIR - 842 nm)**: Resolusi spasial 10 meter. Pantulan maksimal struktur kanopi sel mesofil daun vegetasi; diserap hampir sempurna oleh badan air jernih.
* **B11 (Short-Wave Infrared / SWIR - 1610 nm)**: Resolusi spasial 20 meter (di-resample ke 10 m). Sensitif terhadap kadar kelembapan tanah, kebasahan vegetasi, dan material semen/bebatuan bangunan.
* **SCL (Scene Classification Layer)**: Lapisan klasifikasi kualitas piksel otomatis dari prosesor Sen2Cor (level 20 m) untuk memfilter piksel awan jenuh, bayangan awan (*cloud shadow*), awan cirrus, dan awan tebal.

---

### 1.3. Rekayasa Fitur Indeks Spektral (Spectral Indices)

Untuk mempertegas batas pemisah antar-kelas (*feature separability*) di dalam ruang jarak vektor (*vector distance space*), dihitung empat indeks spektral turunan yang dinormalisasi:

#### A. Normalized Difference Vegetation Index (NDVI)
Membedakan kerapatan dan kehijauan vegetasi dari non-vegetasi:
$$\text{NDVI} = \frac{\text{B08} - \text{B04}}{\text{B08} + \text{B04} + \epsilon}$$

#### B. Normalized Difference Water Index (NDWI - McFeeters)
Mengisolasi badan air permukaan terbuka dari tutupan lahan daratan:
$$\text{NDWI} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08} + \epsilon}$$

#### C. Modified Normalized Difference Water Index (MNDWI - Xu)
Meningkatkan akurasi deteksi air dengan menekan sinyal pantulan area terbangun/bangunan:
$$\text{MNDWI} = \frac{\text{B03} - \text{B11}}{\text{B03} + \text{B11} + \epsilon}$$

#### D. Normalized Difference Built-up Index (NDBI)
Mendeteksi konsentrasi kawasan terbangun, perkerasan beton, dan lahan terbuka:
$$\text{NDBI} = \frac{\text{B11} - \text{B08}}{\text{B11} + \text{B08} + \epsilon}$$

*(Konstanta $\epsilon = 10^{-9}$ ditambahkan pada penyebut untuk mencegah kesalahan pembagian dengan nol / division by zero).*

---

### 1.4. Sebaran Data Ground Truth Hasil Crawling Lokal

Data *ground truth* dikumpulkan dari file Shapefile terkompresi (`.zip`) yang didigitasi secara akurat dari citra resolusi tinggi di Jawa Timur:
* `sawah.zip`: 50 poligon sampel
* `Bangunan.zip`: 50 poligon sampel
* `Lahan_Hijau.zip`: 50 poligon sampel (49 poligon valid menghasilkan piksel)
* `Danau.zip`: 50 poligon sampel
* `Laut.zip`: 50 poligon sampel
* `Mangrove.zip`: 60 poligon sampel

Dari total **310 poligon sampel**, sebanyak **309 poligon valid** berhasil diekstraksi menghasilkan total **833,498 piksel berlabel** setelah penyaringan awan SCL dan deduplikasi zona grid.

---

## 2. Pengambilan Data (Data Acquisition / Crawling via openEO)

Wilayah Provinsi Jawa Timur membentang lebih dari 400 km dari barat ke timur. Mengunduh citra satelit sekaligus dalam satu scene besar akan menyebabkan *out-of-memory*, batas kuota pemrosesan timeout pada server openEO, dan file citra yang terlampau besar. 

Oleh karena itu, diterapkan strategi akuisisi terstruktur:
1. **Spatial Grid Tiling**: Wilayah studi dibagi ke dalam grid berukuran `TILE_DEG = 0.20°` (~22 km $\times$ 22 km) dengan margin buffer `BUFFER_DEG = 0.005°` (~500 m) agar poligon di perbatasan sel tetap terakuisisi utuh.
2. **Parallel Batch Job Processing**: Pengiriman *batch job* asinkron ke server openEO CDSE dikelola oleh `MultiBackendJobManager` dan `CsvJobDatabase` dengan 2 worker konkuren, dilengkapi mekanisme auto-retry untuk job yang gagal.
3. **Pembersihan Awan Tingkat Piksel**: Menggunakan band SCL untuk membuang piksel awan/bayangan awan (label 1, 3, 8, 9, 10), dilanjutkan dengan agregasi temporal median (`median_time()`) pada rentang akuisisi September 2026.
4. **Ekstraksi Piksel Terbatas per Poligon**: Poligon laut dan hutan yang sangat luas dibatasi maksimal `MAKS_PIKSEL_PER_POLIGON = 2000` dengan *random sub-sampling* agar distribusi sampel piksel tetap proporsional.
5. **Deduplikasi Grid Spasial**: Hanya piksel yang pusat koordinatnya berada di dalam sel grid tile bersangkutan yang disimpan, mencegah duplikasi piksel pada zona tumpang tindih (*overlap*) antar-tile.

### Kode Program Akuisisi & Ekstraksi Piksel

```python
"""
Sentinel-2 L2A (CDSE openEO) per-tile + ekstraksi KELAS PER PIKSEL -> CSV.
Setiap baris CSV = satu piksel dengan atribut band spektral dan indeks turunan.
"""

from datetime import datetime
from pathlib import Path
import threading
import time

import geopandas as gpd
import numpy as np
import openeo
from openeo.extra.job_management import CsvJobDatabase, MultiBackendJobManager
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.mask import mask as rio_mask
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window
from shapely.geometry import box
from shapely.validation import make_valid

# ==============================================================================
# KONFIGURASI SESUAI GROUND TRUTH PROYEK
# ==============================================================================
SUMBER = {  # nama kelas: (path file, kode label)
    "Sawah": ("sawah.zip", 1),
    "Bangunan": ("Bangunan.zip", 2),
    "Hutan": ("Lahan_Hijau.zip", 3),
    "Danau": ("Danau.zip", 4),
    "Laut": ("Laut.zip", 5),
    "Mangrove": ("Mangrove.zip", 6),
}

TILE_DEG = 0.20  # Ukuran tile ~22 km (~2200 x 2200 piksel @10m)
BUFFER_DEG = 0.005  # Margin ~500 m di sekeliling sampel

TANGGAL = ["2026-09-01", "2026-09-30"]
BANDS = ["B02", "B03", "B04", "B08", "B11"]
PAKAI_MASK_SCL = True  # Masking awan & bayangan berbasis SCL
MAX_CLOUD = 30  # Ambang batas tutupan awan scene

PARALEL = 2  # Jumlah worker paralel openEO CDSE
MAKS_PIKSEL_PER_POLIGON = 2000  # Sub-sampling acak poligon besar
SEED = 42

OUT_DIR = Path("hasil_s2_piksel")
JOB_DB_PATH = OUT_DIR / "daftar_job.csv"
PETA_CSV = OUT_DIR / "peta_sampel_tile.csv"
PIKSEL_OUT = OUT_DIR / "piksel_s2.csv"


# 1. BACA & GABUNGKAN POLIGON GROUND TRUTH
def baca_semua() -> gpd.GeoDataFrame:
  bagian = []
  for nama, (file, label) in SUMBER.items():
    g = gpd.read_file(file).to_crs("EPSG:4326")
    g["poligon_no"] = np.arange(len(g))
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["geometry"] = g.geometry.apply(
        lambda x: x if x.is_valid else make_valid(x)
    )
    g["label_teks"] = nama
    g["label"] = label
    g["poligon_id"] = [f"{nama}_{n:04d}" for n in g["poligon_no"]]
    g = g[["poligon_id", "poligon_no", "label", "label_teks", "geometry"]]
    print(
        f"Jumlah sampel {nama:<9}: {len(g)}  bounds={[round(v, 3) for v in g.total_bounds]}"
    )
    bagian.append(g)

  gdf = gpd.GeoDataFrame(pd.concat(bagian, ignore_index=True), crs="EPSG:4326")
  print(f"Total sampel gabungan   : {len(gdf)}")
  return gdf


# 2. PEMBAGIAN GRID TILING
def buat_tile(gdf: gpd.GeoDataFrame):
  T, B = TILE_DEG, BUFFER_DEG
  peta, batas, sel_xy = [], {}, {}

  for idx, geom in gdf.geometry.items():
    minx, miny, maxx, maxy = geom.bounds
    for gx in range(int(np.floor(minx / T)), int(np.floor(maxx / T)) + 1):
      for gy in range(int(np.floor(miny / T)), int(np.floor(maxy / T)) + 1):
        sel = box(gx * T, gy * T, (gx + 1) * T, (gy + 1) * T)
        if not geom.intersects(sel):
          continue
        bagian = geom.intersection(sel)
        if bagian.is_empty:
          continue
        b = bagian.bounds
        tid = f"x{gx}_y{gy}"
        peta.append({
            "tile_id": tid,
            "sampel_id": idx,
            "poligon_id": gdf.at[idx, "poligon_id"],
        })
        sel_xy[tid] = (gx, gy)
        if tid in batas:
          o = batas[tid]
          batas[tid] = (
              min(o[0], b[0]),
              min(o[1], b[1]),
              max(o[2], b[2]),
              max(o[3], b[3]),
          )
        else:
          batas[tid] = b

  tiles = pd.DataFrame([{
      "tile_id": tid,
      "gx": sel_xy[tid][0],
      "gy": sel_xy[tid][1],
      "west": b[0] - B,
      "south": b[1] - B,
      "east": b[2] + B,
      "north": b[3] + B,
  } for tid, b in batas.items()])
  peta = pd.DataFrame(peta)
  tiles["n_sampel"] = tiles["tile_id"].map(
      peta.groupby("tile_id")["sampel_id"].nunique()
  )
  return tiles, peta


# 3. KIRIM JOB KE OPENEO
def start_job(row, connection, **kwargs):
  bbox = {
      "west": float(row["west"]),
      "south": float(row["south"]),
      "east": float(row["east"]),
      "north": float(row["north"]),
  }
  bands = BANDS + ["SCL"] if PAKAI_MASK_SCL else BANDS
  cube = connection.load_collection(
      "SENTINEL2_L2A",
      spatial_extent=bbox,
      temporal_extent=TANGGAL,
      bands=bands,
      max_cloud_cover=MAX_CLOUD,
  )

  if PAKAI_MASK_SCL:
    scl = cube.band("SCL")
    # Mask: 1=jenuh, 3=bayangan awan, 8/9=awan sedang/tinggi, 10=cirrus
    mask_awan = (
        (scl == 1) | (scl == 3) | (scl == 8) | (scl == 9) | (scl == 10)
    )
    cube = cube.filter_bands(BANDS).mask(mask_awan)

  komposit = cube.median_time()
  return komposit.create_job(title=f"s2_{row['tile_id']}", out_format="GTiff")


# 4. REKAYASA INDEKS SPEKTRAL
def tambah_indeks(df: pd.DataFrame) -> pd.DataFrame:
  e = 1e-9
  df["NDVI"] = (df["B08"] - df["B04"]) / (df["B08"] + df["B04"] + e)
  df["NDWI"] = (df["B03"] - df["B08"]) / (df["B03"] + df["B08"] + e)
  df["MNDWI"] = (df["B03"] - df["B11"]) / (df["B03"] + df["B11"] + e)
  df["NDBI"] = (df["B11"] - df["B08"]) / (df["B11"] + df["B08"] + e)
  return df
```

### Ringkasan Hasil Ekstraksi Piksel Lokal

Proses crawling dan ekstraksi piksel menghasilkan dataset tabular komprehensif pada file `hasil_s2_piksel/piksel_s2.csv`:

```
Tersimpan: hasil_s2_piksel/piksel_s2.csv
Total piksel berlabel : 833,498 piksel
Distribusi piksel per kelas:
  Bangunan  : 108,284 piksel
  Danau     :  82,232 piksel
  Hutan     : 201,452 piksel
  Laut      : 294,000 piksel
  Mangrove  :  54,116 piksel
  Sawah     :  93,414 piksel
Jumlah poligon unik yang menghasilkan piksel valid: 309 poligon
```

---

## 3. Data Preprocessing & Agregasi Spasial (Centroid Poligon)

### Masalah Autokorelasi Spasial (*Spatial Autocorrelation Leakage*)

Dalam data penginderaan jauh (*remote sensing*), piksel-piksel yang berada di dalam satu poligon yang sama memiliki autokorelasi spasial yang sangat tinggi (nilai spektral hampir identik). 

> [!WARNING]
> Jika data dipecah (*train/test split*) pada tingkat piksel secara acak, piksel dari poligon lahan yang sama akan terdistribusi ke dalam data latih sekaligus data uji. Hal ini menimbulkan **kebocoran data spasial (*spatial data leakage*)**, di mana algoritma seperti KNN atau Random Forest seolah-olah memiliki akurasi $>99\%$ akibat menghafal tetangga piksel yang bersebelahan, namun gagal ketika diuji pada wilayah poligon baru.

### Solusi: Agregasi Tingkat Poligon (Centroid Aggregation)

Untuk mengeliminasi kebocoran spasial, seluruh piksel yang berasal dari satu poligon diagregasi menjadi **satu entitas observasi poligon (centroid)** menggunakan nilai rata-rata (*mean*) fitur spektral:

```python
FITUR = ["B02", "B03", "B04", "B08", "B11", "NDVI", "NDWI", "MNDWI", "NDBI"]
AGREGASI = "mean"  # Menghitung centroid spektral rata-rata


def buat_centroid(df: pd.DataFrame) -> pd.DataFrame:
  df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FITUR)
  agg = df.groupby("poligon_id")[FITUR].agg(AGREGASI)
  info = df.groupby("poligon_id").agg(
      label=("label", "first"),
      label_teks=("label_teks", "first"),
      n_piksel=("label", "size"),
      lon_centroid=("lon", "mean"),
      lat_centroid=("lat", "mean"),
  )
  cen = info.join(agg).reset_index()
  return cen
```

Setelah dilakukan agregasi, diperoleh **309 poligon sampel unik**:
* **Mangrove**: 60 poligon
* **Bangunan**: 50 poligon
* **Danau**: 50 poligon
* **Laut**: 50 poligon
* **Sawah**: 50 poligon
* **Hutan**: 49 poligon

---

## 4. Proses Pemodelan Machine Learning (K-Nearest Neighbors / KNN)

### 4.1. Landasan Teori Algoritma K-Nearest Neighbors (KNN)

**K-Nearest Neighbors (KNN)** adalah algoritma pembelajaran terbimbing (*supervised learning*) berbasis instans (*instance-based learning*) atau *lazy learner*. Berbeda dengan Random Forest yang membangun pohon keputusan parametrik, KNN tidak menggeneralisasi model fungsi eksplisit saat pelatihan, melainkan menyimpan seluruh sampel latih dalam ruang fitur multi-dimensi.

Saat data uji baru $\mathbf{x}$ diberikan, KNN melakukan tahapan berikut:
1. **Perhitungan Jarak Geometris**: Menghitung jarak antara vektor $\mathbf{x}$ dan seluruh vektor sampel latih $\mathbf{x}_i \in \mathcal{D}_{\text{train}}$ menggunakan metrik jarak (misalnya **Euclidean Distance**):
   $$d(\mathbf{x}, \mathbf{x}_i) = \sqrt{\sum_{j=1}^{p} (x_j - x_{ij})^2}$$
   atau **Manhattan Distance**:
   $$d(\mathbf{x}, \mathbf{x}_i) = \sum_{j=1}^{p} |x_j - x_{ij}|$$
2. **Pencarian $k$ Tetangga Terdekat**: Mengurutkan seluruh jarak dan memilih $k$ sampel terdekat.
3. **Voting dan Pembobotan Jarak (*Distance Weighting*)**:
   Jika menggunakan pembobotan seragam (*uniform*), kelas ditentukan berdasarkan modus mayoritas. Namun, dengan pembobotan invers jarak (*distance weighting*), kontribusi tetangga ke-$i$ diberi bobot:
   $$w_i = \frac{1}{d(\mathbf{x}, \mathbf{x}_i)}$$
   Probabilitas kelas $c$ dihitung melalui normalisasi bobot tetangga:
   $$P(y = c \mid \mathbf{x}) = \frac{\sum_{i \in \mathcal{N}_k, y_i = c} w_i}{\sum_{i \in \mathcal{N}_k} w_i}$$

#### Mengapa Standarisasi Fitur (*Feature Scaling*) Wajib untuk KNN?
Fitur reflektansi Sentinel-2A (B02–B11) memiliki skala nilai orde $0 - 5000$ (atau $0 - 0.5$ dalam fraksi), sedangkan indeks spektral normalisasi (NDVI, NDWI, MNDWI, NDBI) berada pada rentang $-1.0$ hingga $+1.0$. Tanpa standarisasi, band spektral berorde besar akan mendominasi perhitungan jarak Euclidean dan membuat fitur indeks tidak memiliki pengaruh. Oleh karena itu, diterapkan **StandardScaler** (Z-score normalization):
$$z = \frac{x - \mu}{\sigma}$$
sehingga seluruh 9 fitur memiliki rata-rata $\mu = 0$ dan varians $\sigma^2 = 1$.

---

### 4.2. Pembagian Data (Stratified Train-Test Split)

Data dibagi menggunakan skema *Stratified Train-Test Split* dengan proporsi **70% Data Latih (216 poligon)** dan **30% Data Uji (93 poligon)** menggunakan nilai acak terkontrol (`random_state=42`) agar proporsi kelas tetap konsisten:

```
Train : 216 poligon (70%)
Test  :  93 poligon (30%)
Distribusi Kelas Data Uji:
  - Mangrove : 18 poligon
  - Bangunan : 15 poligon
  - Danau    : 15 poligon
  - Hutan    : 15 poligon
  - Laut     : 15 poligon
  - Sawah    : 15 poligon
```

---

### 4.3. Penyetelan Hyperparameter (GridSearchCV & 5-Fold CV)

Penyetelan hyperparameter dijalankan menggunakan `Pipeline([('scaler', StandardScaler()), ('knn', KNeighborsClassifier())])` dengan skema 5-Fold Stratified Cross-Validation untuk mengoptimasi metrik **F1-Macro**:

```python
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

pipe = Pipeline([("scaler", StandardScaler()), ("knn", KNeighborsClassifier())])

PARAM_GRID = {
    "knn__n_neighbors": [3, 5, 7, 9, 11],
    "knn__weights": ["uniform", "distance"],
    "knn__metric": ["euclidean", "manhattan", "minkowski"],
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
gs = GridSearchCV(
    pipe, PARAM_GRID, cv=cv, scoring="f1_macro", n_jobs=-1, refit=True
)
gs.fit(X_train, y_train)
```

**Hasil Optimasi Hyperparameter:**
* Total kombinasi yang diuji: $5 \times 2 \times 3 = 30$ kandidat ($150$ fits pada 5-fold CV).
* **Konfigurasi Terbaik**:
  ```python
  {
      "knn__metric": "euclidean",
      "knn__n_neighbors": 7,
      "knn__weights": "distance",
  }
  ```
* **Skor F1-Macro Cross-Validation**: **0.8546** (85.46%).

---

### 4.4. Evaluasi Performa Model pada Data Uji (93 Poligon)

Model KNN terbaik diuji pada **93 poligon data uji independen** yang belum pernah dilihat sama sekali:

#### Ringkasan Metrik Evaluasi:
* **Akurasi Keseluruhan (Accuracy)**: **0.8495** (84.95%) — **79 dari 93 poligon terprediksi dengan benar**.
* **F1-Macro Score**: **0.8446** (84.46%)
* **F1-Weighted Score**: **0.8450** (84.50%)
* **Cohen's Kappa ($\kappa$)**: **0.8192** (Tingkat kesepakatan sangat tinggi / *Substantial to Almost Perfect Agreement*)

#### Laporan Klasifikasi per Kelas (Classification Report):

| Kelas Tutupan Lahan | Precision | Recall | F1-Score | Support (Poligon Uji) |
| :--- | :---: | :---: | :---: | :---: |
| **Bangunan** | 0.7895 | **1.0000** | 0.8824 | 15 |
| **Danau** | **1.0000** | 0.6000 | 0.7500 | 15 |
| **Hutan** | 0.8667 | 0.8667 | 0.8667 | 15 |
| **Laut** | 0.8824 | **1.0000** | **0.9375** | 15 |
| **Mangrove** | 0.8824 | 0.8333 | 0.8571 | 18 |
| **Sawah** | 0.7500 | 0.8000 | 0.7742 | 15 |
| **Rata-rata Makro (Macro Avg)** | **0.8618** | **0.8500** | **0.8446** | 93 |
| **Rata-rata Tertimbang (Weighted Avg)** | **0.8625** | **0.8495** | **0.8450** | 93 |

---

### 4.5. Analisis Confusion Matrix

Distribusi prediksi model KNN pada 93 poligon sampel data uji disajikan dalam tabel kontingensi berikut:

```
Confusion Matrix (KNN k=7, distance, euclidean):
               pred_Bangunan  pred_Danau  pred_Hutan  pred_Laut  pred_Mangrove  pred_Sawah
asli_Bangunan             15           0           0          0              0           0
asli_Danau                 2           9           0          2              1           1
asli_Hutan                 1           0          13          0              0           1
asli_Laut                  0           0           0         15              0           0
asli_Mangrove              0           0           1          0             15           2
asli_Sawah                 1           0           1          0              1          12
```

#### Temuan Analisis Pola Spasial KNN:
1. **Recall Sempurna pada Kelas Ekstrem (100% Benar)**: 
   * **Bangunan (15/15)** dan **Laut (15/15)** memiliki sensitivitas sempurna ($1.00$). Karakteristik spektral laut terbuka (penyerapan NIR/SWIR total dan pantulan tinggi pada band biru B02) serta kawasan bangunan (reflektansi tinggi pada B11 dan NDBI positif kuat) membentuk klaster geometris yang sangat terisolasi dari kelas lain dalam ruang jarak Euclidean terstandarisasi.
2. **Karakteristik Transisi Danau ke Air Lain & Lahan Basah**:
   * Kelas Danau memperoleh precision sempurna ($1.00$) namun recall $0.60$ (9/15 benar). Sebanyak 2 poligon danau terklasifikasi sebagai laut karena sifat optik air tawar jernih yang identik dengan air laut dalam spektrum optik, 2 poligon terprediksi sebagai bangunan (akibat tingginya kekeruhan/sedimentasi atau sempadan perkerasan waduk), 1 sebagai mangrove, dan 1 sebagai sawah.
3. **Pemisahan Kelas Vegetasi (Hutan, Mangrove, Sawah)**:
   * **Hutan** mencapai F1-score 0.8667 (13/15 benar).
   * **Mangrove** mencapai F1-score 0.8571 (15/18 benar), dengan 1 poligon terprediksi sebagai hutan kanopi rapat dan 2 poligon terprediksi sebagai sawah basah.
   * **Sawah** memiliki recall 0.8000 (12/15 benar). Dinamika fenologi sawah (fase genangan air, fase vegetatif hijau klorofil, dan fase bera/panen tanah terbuka) menyebabkan posisinya dalam ruang fitur berada di antara klaster air, vegetasi, dan tanah terbuka.

---

### 4.6. Analisis Tingkat Kepentingan Fitur (*Permutation Feature Importance*)

Berbeda dengan Random Forest yang memiliki kalkulasi *Gini Impurity reduction*, algoritma KNN tidak menghasilkan bobot fitur secara bawaan. Oleh karena itu, tingkat kepentingan fitur dievaluasi menggunakan metode **Permutation Feature Importance** pada data uji (mengacak nilai tiap fitur sebanyak 30 kali pengulangan dan mengukur penurunan F1-Macro):

| Peringkat | Fitur Spektral | Penurunan Rata-rata F1-Macro | Kontribusi Relatif (%) | Peran dan Signifikansi Fisis pada KNN |
| :---: | :---: | :---: | :---: | :--- |
| **1** | **B03 (Green)** | **0.1948** $\pm$ 0.028 | **19.28%** | Fitur paling menentukan dalam ruang jarak KNN. Membedakan kejernihan air, kedalaman perairan, dan puncak pantulan klorofil daun. |
| **2** | **B02 (Blue)** | **0.1851** $\pm$ 0.047 | **18.32%** | Sangat signifikan dalam mengisolasi badan air laut terbuka dan efek hamburan atmosfer pesisir. |
| **3** | **NDBI** | **0.1763** $\pm$ 0.037 | **17.44%** | Memberikan pemisahan jarak Euclidean yang sangat tegas antara kawasan binaan/terbangun dari tutupan alami vegetasi & air. |
| **4** | **B11 (SWIR)** | **0.1039** $\pm$ 0.030 | **10.29%** | Mengukur kelembapan kanopi dan membedakan permukaan basah/lumpur dari tanah kering/beton. |
| **5** | **MNDWI** | **0.0907** $\pm$ 0.025 | **8.98%** | Menekan pantulan bangunan saat mendeteksi badan air tawar pedalaman dan waduk. |
| **6** | **B08 (NIR)** | **0.0839** $\pm$ 0.024 | **8.30%** | Membedakan kanopi sel mesofil daun vegetasi hidup dari penyerapan penuh oleh perairan. |
| **7** | **NDWI** | **0.0714** $\pm$ 0.027 | **7.06%** | Mempertegas ambang batas kebasahan permukaan dan batas genangan sawah. |
| **8** | **B04 (Red)** | **0.0536** $\pm$ 0.022 | **5.31%** | Pita serapan klorofil tanaman untuk kalkulasi gradien spektral vegetasi. |
| **9** | **NDVI** | **0.0509** $\pm$ 0.018 | **5.03%** | Membantu memisahkan strata kerapatan kanopi antara hutan rapat, mangrove, dan sawah. |

---

## 5. Menampilkan Peta & Visualisasi Spasial

> [!NOTE]
> **Dashboard Web Streamlit**:  
> Seluruh visualisasi spasial, kontrol layer, dan metrik interaktif dapat diakses pada web:  
> 🔗 **[https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/](https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/)**

Visualisasi spasial dibangun menggunakan pustaka **Folium** (berbasis *Leaflet.js*).

---

### 5.1. Peta 1: Evaluasi Poligon Sampel & Hasil Prediksi KNN (Folium)

Peta pertama berfokus pada evaluasi geometris dan verifikasi akurasi data uji pada 309 poligon sampel *ground truth*:
* **Layer 6 Kelas Tutupan Lahan**: Poligon diwarnai sesuai palet standar GIS (Sawah: hijau muda, Bangunan: merah, Hutan: hijau tua, Danau: biru muda, Laut: biru tua, Mangrove: cokelat).
* **Layer Sorotan Data Uji**: Poligon data uji (93 sampel) diberi garis tepi (*outline*) **biru tegas** (ketebalan 3 piksel).
* **Layer Sorotan Salah Klasifikasi**: Poligon yang salah terprediksi disorot dengan garis tepi **oranye putus-putus** (`dashArray: 6 4`) dan dilengkapi **marker pin oranye dengan ikon tanda seru** (`exclamation-sign`).
* **Popup & Tooltip Interaktif**: Menampilkan metadata poligon, status subset (`Data Uji` / `Data Latih`), status evaluasi (`✓ Benar` / `✗ SALAH`), kelas prediksi KNN, probabilitas keyakinan tetangga terdekat, jumlah piksel, dan nilai rata-rata NDVI & NDWI.

```python
"""
Pembuatan Peta Evaluasi Poligon Interaktif (Folium) berbasis KNN
"""

from pathlib import Path
import folium
import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
from shapely.validation import make_valid
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SUMBER = {
    "Sawah": "sawah.zip",
    "Bangunan": "Bangunan.zip",
    "Hutan": "Lahan_Hijau.zip",
    "Danau": "Danau.zip",
    "Laut": "Laut.zip",
    "Mangrove": "Mangrove.zip",
}

WARNA = {
    "Sawah": "#a6d96a",  # Hijau muda
    "Bangunan": "#e31a1c",  # Merah
    "Hutan": "#1a9641",  # Hijau tua
    "Danau": "#4eb3d3",  # Biru muda
    "Laut": "#0b3c8c",  # Biru tua
    "Mangrove": "#8c510a",  # Cokelat
}

FITUR = ["B02", "B03", "B04", "B08", "B11", "NDVI", "NDWI", "MNDWI", "NDBI"]


def buat_peta_knn():
  # 1. Baca geometri poligon sampel dari shapefile lokal
  bagian = []
  for nama, file in SUMBER.items():
    g = gpd.read_file(file).to_crs("EPSG:4326")
    g["poligon_no"] = np.arange(len(g))
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["geometry"] = g.geometry.apply(
        lambda x: x if x.is_valid else make_valid(x)
    )
    g["poligon_id"] = [f"{nama}_{n:04d}" for n in g["poligon_no"]]
    g["kelas"] = nama
    bagian.append(g[["poligon_id", "kelas", "geometry"]])

  gdf = gpd.GeoDataFrame(pd.concat(bagian, ignore_index=True), crs="EPSG:4326")
  gdf["geometry"] = gdf.geometry.simplify(0.00003, preserve_topology=True)

  # 2. Baca piksel dan hitung centroid rata-rata
  df_px = pd.read_csv("hasil_s2_piksel/piksel_s2.csv")
  df_px = df_px.replace([np.inf, -np.inf], np.nan).dropna(subset=FITUR)
  agg = df_px.groupby("poligon_id")[FITUR].mean()
  info = df_px.groupby("poligon_id").agg(
      label=("label", "first"),
      label_teks=("label_teks", "first"),
      n_piksel=("label", "size"),
      lon_centroid=("lon", "mean"),
      lat_centroid=("lat", "mean"),
  )
  cen = info.join(agg).reset_index()

  # 3. Latih Model KNN Pipeline (StandardScaler + KNeighborsClassifier)
  X = cen[FITUR]
  y = cen["label_teks"]
  X_train, X_test, y_train, y_test = train_test_split(
      X, y, test_size=0.3, random_state=42, stratify=y
  )

  knn_pipe = Pipeline([
      ("scaler", StandardScaler()),
      (
          "knn",
          KNeighborsClassifier(
              n_neighbors=7, weights="distance", metric="euclidean"
          ),
      ),
  ])
  knn_pipe.fit(X_train, y_train)

  # Prediksi data uji & probabilitas keyakinan
  cen["subset"] = "train"
  cen.loc[X_test.index, "subset"] = "test"

  test_preds = knn_pipe.predict(X_test)
  test_probs = knn_pipe.predict_proba(X_test).max(axis=1)

  cen["kelas_prediksi"] = np.nan
  cen["keyakinan"] = np.nan
  cen["benar"] = np.nan

  cen.loc[X_test.index, "kelas_prediksi"] = test_preds
  cen.loc[X_test.index, "keyakinan"] = test_probs
  cen.loc[X_test.index, "benar"] = test_preds == y_test

  # Gabungkan dengan GeoDataFrame
  h = gdf.merge(
      cen[[
          "poligon_id",
          "n_piksel",
          "NDVI",
          "NDWI",
          "subset",
          "kelas_prediksi",
          "keyakinan",
          "benar",
      ]],
      on="poligon_id",
      how="left",
  )

  # 4. Format Tooltip & Popup HTML
  def teks_tip(r):
    if r["subset"] == "test":
      simbol = (
          "✓ Benar"
          if r["benar"]
          else f"✗ SALAH (Prediksi: {r['kelas_prediksi']})"
      )
      return f"[Data Uji] {r['poligon_id']} | Asli: {r['kelas']} | {simbol}"
    return f"[Data Latih] {r['poligon_id']} | Kelas: {r['kelas']}"

  def teks_popup(r):
    is_test = r["subset"] == "test"
    if is_test:
      subset_badge = (
          "<span style='background:#0d6efd; color:white; padding:2px 6px;"
          " border-radius:3px; font-size:11px;'>Data Uji (KNN)</span>"
      )
      status_badge = (
          "<span style='background:#28a745; color:white; padding:2px 6px;"
          " border-radius:3px; font-size:11px;'>Benar</span>"
          if r["benar"]
          else (
              "<span style='background:#dc3545; color:white; padding:2px 6px;"
              " border-radius:3px; font-size:11px;'>SALAH</span>"
          )
      )
      pred_val = f"<b style='color:#0d6efd;'>{r['kelas_prediksi']}</b>"
      keyak_val = f"{r['keyakinan']:.1%}" if pd.notna(r["keyakinan"]) else "-"
    else:
      subset_badge = (
          "<span style='background:#6c757d; color:white; padding:2px 6px;"
          " border-radius:3px; font-size:11px;'>Data Latih</span>"
      )
      status_badge = "<span style='color:#6c757d;'>Training</span>"
      pred_val = "<span style='color:#6c757d;'>- (Data Latih)</span>"
      keyak_val = "-"

    px_val = f"{int(r['n_piksel']):,}" if pd.notna(r["n_piksel"]) else "-"
    ndvi_val = f"{r['NDVI']:.3f}" if pd.notna(r["NDVI"]) else "-"
    ndwi_val = f"{r['NDWI']:.3f}" if pd.notna(r["NDWI"]) else "-"

    return f"""
        <div style='font-family: sans-serif; font-size:12px; min-width:210px; line-height:1.5;'>
            <div style='font-size:13px; font-weight:bold; margin-bottom:4px;'>{r['poligon_id']}</div>
            <div style='margin-bottom:6px;'>{subset_badge} {status_badge}</div>
            <table style='width:100%; border-collapse:collapse; font-size:12px;'>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Kelas Asli:</td><td style='padding:2px 0; font-weight:bold;'>{r['kelas']}</td></tr>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Prediksi KNN:</td><td style='padding:2px 0;'>{pred_val}</td></tr>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Keyakinan (k=7):</td><td style='padding:2px 0;'>{keyak_val}</td></tr>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Jumlah Piksel:</td><td style='padding:2px 0;'>{px_val}</td></tr>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Rata-rata NDVI:</td><td style='padding:2px 0;'>{ndvi_val}</td></tr>
                <tr style='border-top:1px solid #dee2e6;'><td style='padding:2px 0; color:#6c757d;'>Rata-rata NDWI:</td><td style='padding:2px 0;'>{ndwi_val}</td></tr>
            </table>
        </div>
        """

  h["tip"] = h.apply(teks_tip, axis=1)
  h["popup"] = h.apply(teks_popup, axis=1)

  # 5. Inisialisasi Peta Folium
  minx, miny, maxx, maxy = h.total_bounds
  peta = folium.Map(
      location=[(miny + maxy) / 2, (minx + maxx) / 2],
      zoom_start=9,
      tiles="OpenStreetMap",
  )

  folium.TileLayer(
      tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attr="Esri World Imagery",
      name="Citra Satelit (Esri)",
  ).add_to(peta)

  # Layer Tiap Kelas Tutupan Lahan
  for nama, warna in WARNA.items():
    sub = h[h["kelas"] == nama]
    fg = folium.FeatureGroup(name=f"Kelas: {nama} ({len(sub)} poligon)")
    folium.GeoJson(
        sub[["tip", "popup", "geometry"]],
        style_function=lambda f, w=warna: {
            "color": "#333",
            "weight": 1.2,
            "fillColor": w,
            "fillOpacity": 0.75,
        },
        highlight_function=lambda f: {"weight": 3, "fillOpacity": 0.95},
        tooltip=folium.GeoJsonTooltip(fields=["tip"], labels=False),
        popup=folium.GeoJsonPopup(
            fields=["popup"], labels=False, max_width=300
        ),
    ).add_to(fg)
    fg.add_to(peta)

  # Sorotan Poligon Data Uji (Outline Biru)
  sub_uji = h[h["subset"] == "test"]
  fg_uji = folium.FeatureGroup(
      name=f"Data Uji ({len(sub_uji)} poligon)", show=True
  )
  folium.GeoJson(
      sub_uji[["tip", "geometry"]],
      style_function=lambda f: {
          "color": "#0d6efd",
          "weight": 3,
          "fill": False,
      },
      tooltip=folium.GeoJsonTooltip(fields=["tip"], labels=False),
  ).add_to(fg_uji)
  fg_uji.add_to(peta)

  # Sorotan Poligon Salah Klasifikasi (Outline Oranye & Marker Ikon)
  sub_salah = h[h["benar"] == False]
  fg_salah = folium.FeatureGroup(
      name=f"Salah Klasifikasi KNN ({len(sub_salah)} poligon)", show=True
  )
  folium.GeoJson(
      sub_salah[["tip", "geometry"]],
      style_function=lambda f: {
          "color": "#ff7800",
          "weight": 4,
          "fill": False,
          "dashArray": "6 4",
      },
  ).add_to(fg_salah)
  for _, r in sub_salah.iterrows():
    pt = r.geometry.representative_point()
    folium.Marker(
        location=[pt.y, pt.x],
        icon=folium.Icon(color="orange", icon="exclamation-sign"),
        tooltip=(
            f"SALAH: {r['poligon_id']} | Asli: {r['kelas']}, Prediksi:"
            f" {r['kelas_prediksi']}"
        ),
        popup=folium.Popup(r["popup"], max_width=300),
    ).add_to(fg_salah)
  fg_salah.add_to(peta)

  folium.LayerControl(collapsed=False).add_to(peta)
  peta.save("peta_klasifikasi_knn.html")
  return peta


peta = buat_peta_knn()
peta
```

#### Tampilan Peta Interaktif Evaluasi Poligon (Folium):

```{raw} html
<div style="margin: 20px 0; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08);">
    <div style="background: #f6f8fa; padding: 10px 16px; border-bottom: 1px solid #d0d7de; display: flex; justify-content: space-between; align-items: center; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; font-size: 13px;">
        <span><b>Peta Interaktif 1:</b> Evaluasi Poligon Sampel & Hasil Prediksi K-Nearest Neighbors (Folium)</span>
        <div>
            <a href="https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/" target="_blank" style="color: #0F766E; text-decoration: none; font-weight: 600; padding: 4px 10px; background: #E7F4F2; border: 1px solid #99F6E4; border-radius: 4px; margin-right: 6px;">🚀 Buka di Web Streamlit</a>
            <a href="peta_klasifikasi_knn.html" target="_blank" style="color: #0969da; text-decoration: none; font-weight: 600; padding: 4px 10px; background: white; border: 1px solid #d0d7de; border-radius: 4px;">↗ Layar Penuh</a>
        </div>
    </div>
    <iframe src="peta_klasifikasi_knn.html" width="100%" height="620px" style="border: none; display: block;"></iframe>
</div>
```

---

### 5.2. Peta 2: Klasifikasi Tutupan Lahan Skala Regional Jawa Timur (Folium ImageOverlay)

Peta kedua menghasilkan visualisasi inferensi spasial per piksel skala regional mencakup seluruh daratan Provinsi Jawa Timur:
1. **Mozaik Citra Satelit Esri (Zoom 10)**: Diunduh secara paralel menghasilkan mozaik resolusi $3072 \times 1792$ piksel.
2. **Masking Batas Daratan**: Menggunakan file GeoJSON batas resmi provinsi Jawa Timur (`jawa_timur_provinsi.geojson`) yang dirasterisasi menggunakan fungsi `rasterize`.
3. **Penyelarasan Spektral Citra Nyata**: Memetakan nilai RGB citra satelit ke 9 fitur Sentinel-2A menggunakan regresi Random Forest.
4. **Prediksi Per Piksel Menggunakan Model KNN Terstandarisasi**: Mengklasifikasikan piksel daratan secara granular menggunakan model KNN ($k=7$, *distance weights*).
5. **Pewarnaan Palet RGBA Semitransparan**:
   * **Sawah**: Kuning (`#FFD92F`)
   * **Bangunan**: Merah (`#E41A1C`)
   * **Mangrove**: Ungu (`#8E44AD`)
   * **Lahan Hijau / Hutan**: Hijau Tua (`#2E7D32`)
   * **Perairan Terbuka / Laut**: Biru Tua (`#0D47A1`)
   * **Danau**: Biru Muda (`#4FC3F7`)
6. **Integrasi Folium ImageOverlay**: Citra raster RGBA diposisikan di atas citra satelit Esri dengan opasitas dinamis $65\%$, dilengkapi pengalih basemap (*Esri Satellite* dan *Google Hybrid*) serta kontrol layer titik sampel ground truth.

```python
"""
Klasifikasi Per Piksel Skala Regional Jawa Timur (Folium ImageOverlay) berbasis KNN
"""

from concurrent.futures import ThreadPoolExecutor
import io
import math
import os
from pathlib import Path
import folium
from folium.raster_layers import ImageOverlay
import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

AOI = [111.0, -8.85, 114.65, -6.75]  # [barat, selatan, timur, utara]
FITUR = ["B02", "B03", "B04", "B08", "B11", "NDVI", "NDWI", "MNDWI", "NDBI"]

WARNA_KELAS = {
    "Sawah": "#FFD92F",
    "Bangunan": "#E41A1C",
    "Mangrove": "#8E44AD",
    "Hutan": "#2E7D32",
    "Laut": "#0D47A1",
    "Danau": "#4FC3F7",
}


def hex_ke_rgb(h):
  h = h.lstrip("#")
  return [int(h[i : i + 2], 16) for i in (0, 2, 4)]


# 1. Muat Centroid Data Latih & Latih Model Pipeline KNN
df_px = pd.read_csv("hasil_s2_piksel/piksel_s2.csv")
df_px = df_px.replace([np.inf, -np.inf], np.nan).dropna(subset=FITUR)
agg = df_px.groupby("poligon_id")[FITUR].mean()
info = df_px.groupby("poligon_id").agg(
    label=("label", "first"),
    label_teks=("label_teks", "first"),
    lon_centroid=("lon", "mean"),
    lat_centroid=("lat", "mean"),
)
cen = info.join(agg).reset_index()

model_knn = Pipeline([
    ("scaler", StandardScaler()),
    (
        "knn",
        KNeighborsClassifier(
            n_neighbors=7, weights="distance", metric="euclidean"
        ),
    ),
])
model_knn.fit(cen[FITUR], cen["label_teks"])

# 2. Citra Satelit Esri & Koordinat Bounding Box
FILE_SATELIT = "satelit_aoi.jpeg"
img_sat = Image.open(FILE_SATELIT)
W, H = 1536, 896
img_res = img_sat.resize((W, H), Image.Resampling.BILINEAR)
arr_rgb = np.array(img_res)

lat_s, lon_w = -8.85, 111.0
lat_n, lon_e = -6.75, 114.65


def coord_to_px(lat, lon):
  c = int((lon - lon_w) / (lon_e - lon_w) * W)
  r = int((lat_n - lat) / (lat_n - lat_s) * H)
  return np.clip(r, 0, H - 1), np.clip(c, 0, W - 1)


# 3. Estimator Fitur Spektral RGB -> Sentinel-2
rgb_samples = [
    arr_rgb[
        coord_to_px(row["lat_centroid"], row["lon_centroid"])[0],
        coord_to_px(row["lat_centroid"], row["lon_centroid"])[1],
        :3,
    ]
    for _, row in cen.iterrows()
]
reg_mapper = RandomForestRegressor(n_estimators=30, random_state=42, n_jobs=-1)
reg_mapper.fit(np.array(rgb_samples), cen[FITUR].values)

# 4. Masking Daratan Jawa Timur
prov = gpd.read_file("jawa_timur_provinsi.geojson")
transform = from_bounds(lon_w, lat_s, lon_e, lat_n, W, H)
mask_daratan = rasterize(
    [(geom, 1) for geom in prov.geometry],
    out_shape=(H, W),
    transform=transform,
    fill=0,
    dtype=np.uint8,
)

# 5. Prediksi Granular Per Piksel Daratan via KNN
idx_daratan = np.where(mask_daratan == 1)
rgb_daratan = arr_rgb[idx_daratan[0], idx_daratan[1], :3]
feat_daratan = reg_mapper.predict(rgb_daratan)
preds_daratan = model_knn.predict(feat_daratan)

# Susun Matriks Piksel RGBA
rgba = np.zeros((H, W, 4), dtype=np.uint8)
idx_laut = np.where(mask_daratan == 0)
rgba[idx_laut[0], idx_laut[1]] = hex_ke_rgb(WARNA_KELAS["Laut"]) + [225]

for k, col in WARNA_KELAS.items():
  idx_k = np.where(preds_daratan == k)[0]
  rgba[idx_daratan[0][idx_k], idx_daratan[1][idx_k]] = hex_ke_rgb(col) + [225]

# 6. Membangun Peta Interaktif Folium
pusat = [(AOI[1] + AOI[3]) / 2, (AOI[0] + AOI[2]) / 2]
peta = folium.Map(location=pusat, zoom_start=8, tiles=None, control_scale=True)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri",
    name="Esri Satellite",
    max_zoom=19,
    overlay=False,
).add_to(peta)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attr="Google Hybrid",
    name="Google Hybrid (dengan label)",
    max_zoom=20,
    overlay=False,
    show=False,
).add_to(peta)

batas_peta = [[lat_s, lon_w], [lat_n, lon_e]]
ImageOverlay(
    image=rgba,
    bounds=batas_peta,
    opacity=0.65,
    name="Hasil Klasifikasi K-Nearest Neighbors (KNN)",
    zindex=5,
).add_to(peta)

# Tambahkan Titik Sampel Validasi per Kelas
for nama in WARNA_KELAS.keys():
  grup = folium.FeatureGroup(name=f"Titik Sampel: {nama}", show=False)
  for _, r in cen[cen["label_teks"] == nama].iterrows():
    folium.CircleMarker(
        [r["lat_centroid"], r["lon_centroid"]],
        radius=4,
        color="white",
        weight=1,
        fill=True,
        fill_color=WARNA_KELAS[nama],
        fill_opacity=1,
        popup=f"{nama} ({r['lon_centroid']:.4f}, {r['lat_centroid']:.4f})",
    ).add_to(grup)
  grup.add_to(peta)

# Legenda Interaktif LULC
item_legenda = "".join(
    f'<div style="margin:2px 0"><span'
    f' style="display:inline-block;width:14px;height:14px;background:{WARNA_KELAS[k]};border:1px'
    f' solid #333;margin-right:6px;vertical-align:middle"></span>{k}</div>'
    for k in WARNA_KELAS.keys()
)
legenda_html = (
    f'<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:rgba(255,255,255,0.95);'
    f'padding:10px 14px;border:1px solid #888;border-radius:6px;font:12px sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.2);">'
    f'<b>Legenda Tutupan Lahan (KNN)</b><hr style="margin:5px 0">{item_legenda}</div>'
)
peta.get_root().html.add_child(folium.Element(legenda_html))

folium.LayerControl(collapsed=False).add_to(peta)
peta.save("hasil_klasifikasi_knn.html")

peta
```

#### Tampilan Peta Interaktif Skala Regional (Folium ImageOverlay):

```{raw} html
<div style="margin: 20px 0; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08);">
    <div style="background: #f6f8fa; padding: 10px 16px; border-bottom: 1px solid #d0d7de; display: flex; justify-content: space-between; align-items: center; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; font-size: 13px;">
        <span><b>Peta Interaktif 2:</b> Klasifikasi Tutupan Lahan Skala Regional Jawa Timur (Folium ImageOverlay - KNN)</span>
        <div>
            <a href="https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/" target="_blank" style="color: #0F766E; text-decoration: none; font-weight: 600; padding: 4px 10px; background: #E7F4F2; border: 1px solid #99F6E4; border-radius: 4px; margin-right: 6px;">🚀 Buka di Web Streamlit</a>
            <a href="hasil_klasifikasi_knn.html" target="_blank" style="color: #0969da; text-decoration: none; font-weight: 600; padding: 4px 10px; background: white; border: 1px solid #d0d7de; border-radius: 4px;">↗ Layar Penuh</a>
        </div>
    </div>
    <iframe src="hasil_klasifikasi_knn.html" width="100%" height="640px" style="border: none; display: block;"></iframe>
</div>
```

---

## 6. Kesimpulan & Ringkasan Hasil

1. **Performa Solid Algoritma Non-Parametrik KNN**: Penerapan algoritma K-Nearest Neighbors dengan standarisasi `StandardScaler` dan pembobotan jarak (*distance-weighted*, $k=7$) menghasilkan **akurasi data uji 84.95%**, **F1-Macro 84.46%**, dan **Cohen's Kappa 0.8192** pada 93 poligon data uji independen.
2. **Karakteristik Klasifikasi Berbasis Jarak**:
   * Kelas dengan klaster spektral terpisah tegas (**Bangunan** dan **Laut**) mencapai **recall 100%**, membuktikan jarak Euclidean sangat efektif mendeteksi objek dengan absorpsi spektral ekstrem dan respon NDBI dominan.
   * Kelas transisi air dan lahan basah (**Danau** dan **Sawah**) memiliki tantangan tumpang tindih jarak dengan perairan laut dangkal dan vegetasi basah, yang diatasi secara efektif melalui pembobotan jarak $1 / d$.
3. **Pemberantasan Spatial Data Leakage**: Agregasi piksel menjadi centroid pada 309 poligon unik menjamin bahwa model mengevaluasi objek secara objektif pada tingkat bentang lahan, bukan sekadar menghafal piksel tetangga yang bersebelahan.
4. **Fitur Paling Berpengaruh**: Berdasarkan *Permutation Feature Importance*, band **B03 (Green - 19.28%)**, **B02 (Blue - 18.32%)**, dan indeks **NDBI (17.44%)** menjadi prediktor paling menentukan dalam menyusun topologi jarak terdekat pada ruang fitur multi-spektral.
5. **Eksplorasi Spasial Terbuka**: Seluruh hasil klasifikasi spasial, peta evaluasi poligon, serta peta tutupan lahan skala regional Jawa Timur dapat diakses dan dieksplorasi secara daring di: **[https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/](https://klasifikasi-spasial-tutupan-lahan-jawatimur.streamlit.app/)**.
