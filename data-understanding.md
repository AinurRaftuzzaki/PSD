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


# Data Understanding

## Data Collection

Langkah pertama dalam proyek ini adalah mengumpulkan data polutan udara (seperti NO₂, CO, dan SO₂) yang bertipe deret waktu (*Time Series*). Dataset ini diambil dari platform satelit [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/).

Buat akun terlebih dahulu di website Copernicus agar bisa melakukan crawling data menggunakan library openEO.

## Install Library

Untuk melakukan proses crawling data, kita membutuhkan pustaka Python pendukung yaitu `openeo` untuk berkomunikasi dengan API Copernicus, dan `netCDF4` untuk membaca format data cuaca spasial (`.nc`).

```bash
pip install openeo
pip install netCDF4
```

## Autentikasi dan Pengambilan Data

Skrip di bawah ini melakukan proses autentikasi untuk menghubungkan sistem lokal kita dengan server Copernicus menggunakan _device code flow_.

```python
import openeo

connection = openeo.connect("openeo.dataspace.copernicus.eu").authenticate_oidc()
```

Saat menjalankan baris di atas, akan muncul permintaan autentikasi:

```
Visit (link authentikasi) 📋 to authenticate.
✅ Authorized successfully
Authenticated using device code flow.
```

Klik link autentikasi lalu login menggunakan akun Copernicus.

## Definisi Area dan Pengambilan Data NO₂, CO dan SO₂ dari geojson

Setelah berhasil masuk, langkah selanjutnya adalah menentukan wilayah spesifik. Titik koordinat wilayah Nunukan (Poligon) didapatkan menggunakan alat bantu pemetaan [geojson.io](https://geojson.io) dengan menggambar kotak di atas wilayah yang diinginkan kemudian menyalin koordinatnya.

![Grafik Data](geojson.png)

Koordinat yang didapatkan dimasukkan ke dalam variabel aoi (Area of Interest). Satelit Sentinel-5P kemudian diminta untuk mengambil data polutan berdasarkan bounding box wilayah tersebut dengan menyesuaikan variabel s5post atribut bands.

Karena satelit mungkin merekam area yang sama beberapa kali, dilakukan agregasi temporal harian agar hanya terdapat rata-rata satu data per hari. Dilanjutkan dengan agregasi spasial agar seluruh grid pada wilayah Nganjuk dirata-rata menjadi satu nilai tunggal.

```
aoi = {
    "type": "Polygon",
    # Paste koordinat yang didapat 
    "coordinates":
        [
            [
              117.58812764552601,
              4.133326974398287
            ],
            [
              117.75161907303544,
              4.133326974398287
            ],
            [
              117.75161907303544,
              3.971832859595736
            ],
            [
              117.58812764552601,
              3.971832859595736
            ],
            [
              117.58812764552601,
              4.133326974398287
            ]
    ]
}

s5post = connection.load_collection(
    "SENTINEL_5P_L2",
    temporal_extent=["2025-10-01", "2026-06-01"],
    spatial_extent={
        "west": 117.58812764552601,
        "south": 3.971832859595736,
        "east": 117.75161907303544,
        "north": 4.133326974398287
    },
    # Disesuaikan dengan data yang dibutuhkan
    bands=["SO2"],
)

# Agregasi harian agar tidak ada lebih dari satu data per hari
s5p_no2_daily = s5post.aggregate_temporal_period(reducer="mean", period="day")

# Agregasi spasial untuk menghasilkan rata-rata time series per AOI
s5p_no2_aoi = s5p_no2_daily.aggregate_spatial(reducer="mean", geometries=aoi)
```
## Eksekusi Job dan Download

Proses agregasi data spasial ini membutuhkan waktu sehingga dikirim sebagai “Batch Job”.
```
job = s5post.execute_batch(title="NO2 in Nunukan", outputfile="NO2DiNunukan.nc")
```

Tunggu proses selesai. Status dan progres eksekusi bisa dipantau di openEO editor. Setelah diproses oleh server, output akan otomatis diunduh berupa file NetCDF NO2DiNunukan.nc.

```
0:00:00 Job 'j-26082816305840dfb06d9ac4e7a7f81e': send 'start'
0:00:03 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:00:08 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:00:15 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:00:23 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:00:33 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:00:46 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:01:01 Job 'j-26082816305840dfb06d9ac4e7a7f81e': queued (progress 0%)
0:01:21 Job 'j-26082816305840dfb06d9ac4e7a7f81e': running (progress N/A)
0:01:45 Job 'j-26082816305840dfb06d9ac4e7a7f81e': running (progress N/A)
0:02:15 Job 'j-26082816305840dfb06d9ac4e7a7f81e': running (progress N/A)
0:02:53 Job 'j-26082816305840dfb06d9ac4e7a7f81e': running (progress N/A)
0:03:40 Job 'j-26082816305840dfb06d9ac4e7a7f81e': finished (progress 100%)
```

## Simpan Data dalam Bentuk CSV
Format mentah NetCDF (.nc) yang kita dapatkan masih berbentuk matriks spasial tiga dimensi yang kurang ramah untuk dianalisis secara tabular. Oleh karena itu, kita membedah file tersebut menggunakan Python untuk di-convert ke dalam .csv:
* **Data waktu (Time) dikonversi menjadi format tanggal yang bisa dibaca.
* **Untuk mengatasi potensi adanya nilai kosong (null) di grid spasial tertentu, digunakan metode Interpolasi Linier.
* **Setelah data dibersihkan, seluruh grid Nganjuk dirata-rata untuk setiap harinya lalu disimpan ke dalam format tabel (CSV) agar mudah diproses.

```
import numpy as np
import pandas as pd
import netCDF4

file_path = "NO2DiNunukan.nc"
ds = netCDF4.Dataset(file_path)
# Ambil NO2
no2 = ds.variables["NO2"][:]

# Ambil Time
time = ds.variables["t"][:]

# Konversi waktu ke format tanggal
try:
    time_units = ds.variables["t"].units
    dates = netCDF4.num2date(time, units=time_units)
except Exception:
    dates = time  # fallback jika tidak ada units

        
new_dates = []
new_no2 = []

for i in range(len(dates)):
    new_date = dates[i].strftime('%Y-%m-%d')
    new_dates.append(new_date)
    new_no2.append(np.mean(no2[i]))

df = pd.DataFrame({
    "date": new_dates,
    "NO2": new_no2
})

# Simpan ke CSV
df.to_csv("NO2_Nunukan_timeseries.csv", index=False)
```
## Hasil CSV

Pada tahap terakhir, kita memuat file CSV (CO, SO₂, dan NO₂) yang telah dirapikan menggunakan pustaka Pandas. Data ini sekarang sudah terstruktur sebagai dataset Time Series dan siap digunakan untuk analisis lanjutan. Berikut adalah cuplikan data tersebut:
1. CO

```{code-cell} ipython3
:tags: ["hide-input"]

import pandas as pd
import numpy as np
df = pd.read_csv("CO_Nunukan_timeseries.csv")
df.head(5)
```

2. SO2

```{code-cell} ipython3
:tags: ["hide-input"]

import pandas as pd
import numpy as np
df = pd.read_csv("SO2_Nunukan_timeseries.csv")
df.head(5)
```

3. NO2

```{code-cell} ipython3
:tags: ["hide-input"]

import pandas as pd
import numpy as np
df = pd.read_csv("NO2_Nunukan_timeseries.csv")
df.head(5)
```