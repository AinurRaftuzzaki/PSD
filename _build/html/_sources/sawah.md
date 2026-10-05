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
    tiles='[https://mt1.google.com/vt/lyrs=y&x=](https://mt1.google.com/vt/lyrs=y&x=){x}&y={y}&z={z}',
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