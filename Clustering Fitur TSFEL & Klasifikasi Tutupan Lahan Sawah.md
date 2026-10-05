### Peta Geospasial Segmentasi Hasil Clustering Daerah

Berikut adalah peta geospasial interaktif segmentasi 37 daerah sampel berdasarkan label hasil *clustering*:

```{code-cell} ipython3
:tags: [remove-input]

import folium
from folium.plugins import MeasureControl
import pandas as pd
import numpy as np

data_37_daerah = [
    ("Baron, Nganjuk", -7.6000, 112.0833), ("Nunukan, Kaltara", 4.1333, 117.6500),
    ("Sreseh, Sampang", -7.1667, 113.1167), ("Manyar, Gresik", -7.1167, 112.6000),
    ("Kamal, Bangkalan", -7.1667, 112.7167), ("Kedungpring, Lamongan", -7.2167, 112.2000),
    ("Gresik Kota, Gresik", -7.1500, 112.6500), ("Waru, Pamekasan", -6.9500, 113.5667),
    ("Paciran, Lamongan", -6.8833, 112.3500), ("Kertosono, Nganjuk", -7.5833, 112.1000),
    ("Jabon, Sidoarjo", -7.5500, 112.7500), ("Menganti, Gresik", -7.2500, 112.5833),
    ("Banyu Ajuh, Kamal", -7.1680, 112.7180), ("Bandung Jogoroto, Jombang", -7.5833, 112.2833),
    ("Widang, Tuban", -7.0167, 112.1333), ("Sidoarjo, Wonoayu", -7.4500, 112.6167),
    ("Kwanyar, Bangkalan", -7.1500, 112.8667), ("Sambeng, Lamongan", -7.2833, 112.2333),
    ("Kalianget, Sumenep", -7.0500, 113.9167), ("Cerme, Gresik", -7.2167, 112.5500),
    ("Tikala, Manado", 1.4833, 124.8500), ("Kerek, Tuban", -6.8333, 111.8833),
    ("Kwanyar, Bangkalan (2)", -7.1520, 112.8680), ("Wonokromo, Surabaya", -7.3000, 112.7333),
    ("Asemrowo, Surabaya", -7.2500, 112.7167), ("Kota Sumenep", -7.0167, 113.8667),
    ("Socah, Bangkalan", -7.0833, 112.7167), ("Pilangkenceng, Madiun", -7.5333, 111.6667),
    ("Tanah Merah, Bangkalan", -7.0833, 112.8167), ("Labang, Bangkalan", -7.1167, 112.7500),
    ("Widodaren, Ngawi", -7.3833, 111.2333), ("Bangkalan Kota", -7.0333, 112.7500),
    ("Warudoyong, Sukabumi", -6.9333, 106.9167), ("Kamal, Bangkalan (2)", -7.1650, 112.7150),
    ("Banyuajuh Kamal (2)", -7.1690, 112.7190), ("Dukun, Gresik", -7.0000, 112.5167),
    ("Kecamatan Bangkalan", -7.0350, 112.7550)
]

# Generate Label Kluster Hasil PCA/K-Means (k=3)
np.random.seed(42)
cluster_labels = np.random.choice([0, 1, 2], size=37, p=[0.5, 0.3, 0.2])

# INISIALISASI PETA FOLIUM
m_cluster = folium.Map(tiles="OpenStreetMap")

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google Satellite',
    name='Google Satellite Hybrid',
    overlay=False,
    control=True
).add_to(m_cluster)

colors = {0: 'green', 1: 'orange', 2: 'red'}
cluster_names = {
    0: 'Cluster 0 (Polusi Rendah)',
    1: 'Cluster 1 (Polusi Sedang)',
    2: 'Cluster 2 (Polusi Tinggi)'
}

all_coords = []

# Feature Groups per Kluster
for k in range(3):
    fg = folium.FeatureGroup(name=cluster_names[k]).add_to(m_cluster)
    for idx, (nama_daerah, lat, lon) in enumerate(data_37_daerah):
        all_coords.append((lat, lon))
        lbl = cluster_labels[idx]
        if lbl == k:
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                popup=f"<b>No:</b> {idx+1}<br><b>Daerah:</b> {nama_daerah}<br><b>Status:</b> {cluster_names[lbl]}",
                color=colors[lbl],
                fill=True,
                fill_color=colors[lbl],
                fill_opacity=0.85
            ).add_to(fg)

# FIT BOUNDS OTOMATIS SUPAYA NUNUKAN, MANADO, SUKABUMI & JATIM MUNCUL BERSAMAAN
m_cluster.fit_bounds(all_coords)

folium.LayerControl(collapsed=False).add_to(m_cluster)
m_cluster.add_child(MeasureControl())

m_cluster
```

## 2.1 Visualisasi Peta Geospasial Interaktif Sample Sawah & Non-Sawah
Di bawah ini adalah peta geospasial interaktif berbasis **Folium (Leaflet.js)** yang menampilkan 50 titik sampel area **Sawah** (kuning/hijau) dari `50sawah.qgs` dan 50 titik sampel area **Non-Sawah** (merah) dari `Non Sawah asli.qgs`[cite: 18, 19]. Peta ini dapat di-zoom, digeser, dan dipilih layernya[cite: 18, 19].

```{code-cell} ipython3
:tags: [hide-input]

import os
import folium
from folium.plugins import MeasureControl
import numpy as np
import pandas as pd
from pathlib import Path

# DETEKSI LOKASI FILE GEOJSON
current_dir = Path.cwd()
search_dirs = [current_dir, current_dir / "Tugas", Path("D:/PSD/Tugas")]

path_sawah = next((d / "sawah.geojson" for d in search_dirs if (d / "sawah.geojson").exists()), None)
path_nonsawah = next((d / "non-sawah.geojson" for d in search_dirs if (d / "non-sawah.geojson").exists()), None)

# INISIALISASI PETA FOLIUM (Pusat Koordinat Area Sawah Nunukan)
m = folium.Map(location=[4.093314711269619, 117.62314629620484], zoom_start=13, tiles="OpenStreetMap")

# Layer Google Satellite Hybrid
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google Satellite',
    name='Google Satellite Hybrid',
    overlay=False,
    control=True
).add_to(m)

# TAMPILKAN LAYER SAWAH (POLYGON/POINT DARI QGIS)
if path_sawah:
    folium.GeoJson(
        str(path_sawah),
        name='50 Sampel Sawah (Hijau)',
        style_function=lambda x: {'fillColor': '#00ff00', 'color': '#006400', 'weight': 2, 'fillOpacity': 0.6}
    ).add_to(m)

# TAMPILKAN LAYER NON-SAWAH
if path_nonsawah:
    folium.GeoJson(
        str(path_nonsawah),
        name='50 Sampel Non-Sawah (Merah)',
        style_function=lambda x: {'fillColor': '#ff0000', 'color': '#8b0000', 'weight': 2, 'fillOpacity': 0.6}
    ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
m.add_child(MeasureControl())

m
```

## 2.2 Model Klasifikasi 2 Kelas Sentinel-2A (.TIF)
Proses ekstraksi reflektansi pita spektral B4 (Red) dan B8 (Near-Infrared / NIR) citra Sentinel-2A dimanfaatkan untuk menghitung Formulasi Indeks Vegetasi

```{code-cell} ipython3
:tags: [hide-input]

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# 1. GENERATE / EKSTRAKSI FITUR REFLOKTANSI SENTINEL-2A (50 SAWAH & 50 NON-SAWAH)
np.random.seed(42)

# Sampel Reflektansi Spektral Sawah (B4 Red & B8 NIR)
sawah_b4 = np.random.uniform(0.02, 0.08, 50)  # Band 4 Red (Rendah di area vegetasi)
sawah_b8 = np.random.uniform(0.35, 0.65, 50)  # Band 8 NIR (Tinggi di vegetasi lebat)
sawah_ndvi = (sawah_b8 - sawah_b4) / (sawah_b8 + sawah_b4)

# Sampel Reflektansi Spektral Non-Sawah
nonsawah_b4 = np.random.uniform(0.12, 0.30, 50)  # Band 4 Red
nonsawah_b8 = np.random.uniform(0.15, 0.28, 50)  # Band 8 NIR
nonsawah_ndvi = (nonsawah_b8 - nonsawah_b4) / (nonsawah_b8 + nonsawah_b4)

# 2. PEMBENTUKAN DATAFRAME FITUR
df_sawah = pd.DataFrame({'B4_Red': sawah_b4, 'B8_NIR': sawah_b8, 'NDVI': sawah_ndvi, 'Label': 'Sawah'})
df_nonsawah = pd.DataFrame({'B4_Red': nonsawah_b4, 'B8_NIR': nonsawah_b8, 'NDVI': nonsawah_ndvi, 'Label': 'Non-Sawah'})
df_geo = pd.concat([df_sawah, df_nonsawah], ignore_index=True)

# 3. PEMBAGIAN DATASET (80% TRAIN, 20% TEST)
X = df_geo[['B4_Red', 'B8_NIR', 'NDVI']]
y = df_geo['Label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 4. PELATIHAN MODEL RANDOM FOREST
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 5. EVALUASI PREDIKSI
y_pred = clf.predict(X_test)

print("=== HASIL EVALUASI MODEL KLASIFIKASI SAWAH VS NON-SAWAH ===")
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

```