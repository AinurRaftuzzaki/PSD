---
title: Preprocessing & Ekstraksi Fitur (Tugas 3)
---

# Preprocessing Sebelum Ekstraksi Fitur

Tahap ini melanjutkan data kualitas udara **Kabupaten Nunukan** (CO, NO2, SO2) yang
sudah dikumpulkan pada tugas sebelumnya. Sebelum data dipakai untuk ekstraksi fitur,
data perlu melalui tiga tahap preprocessing: **deteksi & perbaikan outlier**,
**imputasi missing value**, lalu **ekstraksi fitur** dengan TSFEL.

Seluruh data pada tahap ini sudah difilter sesuai wilayah Kabupaten Nunukan
(kecamatan/kabupaten masing-masing mahasiswa), mengikuti data yang sudah dikumpulkan
pada tugas crawling sebelumnya.

## 1. Deteksi & Perbaikan Outlier

Deteksi outlier dilakukan dengan **Isolation Forest** (asumsi 5% data adalah anomali),
lalu nilai yang terdeteksi sebagai outlier diganti `NaN` dan diisi ulang dengan
interpolasi linear terhadap waktu.

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

POLLUTANTS = ["CO", "NO2", "SO2"]
CONTAMINATION = 0.05

for pol in POLLUTANTS:
    # 1. Load data hasil imputasi missing value
    df = pd.read_csv(f"../csv/{pol}_Nunukan_Timeseries_imputed.csv")
    df = df.dropna(subset=[pol]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 2. Deteksi outlier dengan Isolation Forest
    model = IsolationForest(contamination=CONTAMINATION, random_state=42)
    pred = model.fit_predict(df[[pol]])
    df["anomaly"] = pred  # -1 = outlier, 1 = normal
    outliers = df[df["anomaly"] == -1]
    print(f"[{pol}] Jumlah outlier terdeteksi: {len(outliers)} dari {len(df)} data")

    # 3. Ganti outlier jadi NaN, lalu interpolasi
    df_fixed = df.copy()
    df_fixed.loc[df_fixed["anomaly"] == -1, pol] = np.nan
    df_fixed[pol] = df_fixed[pol].interpolate(method="linear").ffill().bfill()

    # 4. Plot sebelum vs sesudah
    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=True)
    axes[0].plot(df["date"], df[pol], label=f"{pol} (asli)", linewidth=1)
    axes[0].scatter(outliers["date"], outliers[pol], color="red",
                     marker="o", label="Outlier (Isolation Forest)", zorder=5)
    axes[0].set_title(f"Sebelum Perbaikan - Deteksi Outlier {pol}")
    axes[0].legend()

    axes[1].plot(df_fixed["date"], df_fixed[pol], color="green", linewidth=1,
                 label=f"{pol} (setelah outlier diganti & diinterpolasi)")
    axes[1].set_title(f"Sesudah Perbaikan Outlier {pol}")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(f"outlier_{pol}_before_after.png", dpi=150)

    df_fixed[["date", pol]].to_csv(f"../csv/{pol}_Nunukan_Timeseries_fixed.csv", index=False)
```

**Ringkasan outlier yang terdeteksi:**

| polutan   |   n_data |   n_outlier |   pct_outlier | tgl_outlier_pertama   | tgl_outlier_terakhir   |
|:----------|---------:|------------:|--------------:|:----------------------|:-----------------------|
| CO        |      366 |          19 |          5.19 | 2026-02-23            | 2026-08-31             |
| NO2       |      366 |          19 |          5.19 | 2025-09-04            | 2026-06-27             |
| SO2       |      366 |          19 |          5.19 | 2025-09-08            | 2026-08-09             |

### Grafik CO sebelum & sesudah perbaikan

![Grafik CO](../images/Grafik_CO.png)

> **Catatan tentang lonjakan CO di akhir Agustus 2026**
> Pada rentang 21–31 Agustus 2026, kadar CO naik tajam dan seluruhnya terdeteksi
> sebagai outlier oleh Isolation Forest, dengan nilai tertinggi sepanjang data
> tercatat pada 30–31 Agustus 2026. Lonjakan ini bertepatan dengan periode karhutla
> (kebakaran hutan dan lahan) yang meluas di berbagai wilayah Kalimantan pada
> Agustus 2026 akibat musim kemarau panjang yang diperparah El Niño. Asap kebakaran
> yang terbawa angin memicu kenaikan konsentrasi CO di udara meski jumlah titik
> panas di sekitar Nunukan (Kalimantan Utara) sendiri relatif lebih sedikit
> dibanding Kalimantan Tengah dan Kalimantan Barat. Karena nilainya jauh di luar
> pola historis, algoritma outlier tetap menandainya sebagai anomali, sehingga pada
> data yang sudah "fixed" lonjakan ini diratakan lewat interpolasi perlu dicatat
> di laporan bahwa event asap ini adalah kejadian nyata, bukan noise sensor.

### Grafik NO2 sebelum & sesudah perbaikan

![Grafik NO2](../images/Grafik_NO2.png)

### Grafik SO2 sebelum & sesudah perbaikan

![Grafik SO2](../images/Grafik_SO2.png)

## 2. Imputasi Missing Value

Missing value pada data mentah (166 hari kosong pada CO, 124 pada NO2, 55 pada SO2
dari total 366 hari) sudah diisi penuh pada tahap sebelumnya (file `*_imputed.csv`)
menggunakan interpolasi/forward-fill, sehingga tidak ada lagi nilai kosong yang
masuk ke tahap ekstraksi fitur.

## 3. Ekstraksi Fitur dengan TSFEL

Ekstraksi fitur memakai [TSFEL](https://tsfel.readthedocs.io/), menghasilkan
**68 fitur** dari 3 domain (statistical, temporal, spectral) untuk masing-masing
polutan. TSFEL versi terbaru memisahkan 6 fitur non-linear (`dfa`,
`higuchi_fractal_dimension`, `hurst_exponent`, `lempel_ziv`,
`maximum_fractal_length`, `petrosian_fractal_dimension`, `mse`) ke domain
*fractal* tersendiri; karena tugas ini hanya meminta 3 domain, fitur-fitur
tersebut digabungkan ke kelompok **Temporal** sesuai pengelompokan awal TSFEL.

```python
import pandas as pd
import numpy as np
import inspect
import tsfel.feature_extraction.features as tsfel_features

POLLUTANTS = ["CO", "NO2", "SO2"]
fs = 1  # 1 observasi per hari

FEATURE_LIST = """abs_energy auc autocorr average_power calc_centroid calc_max calc_mean
calc_median calc_min calc_std calc_var dfa distance ecdf ecdf_percentile ecdf_percentile_count
ecdf_slope entropy fundamental_frequency higuchi_fractal_dimension hist_mode human_range_energy
hurst_exponent interq_range kurtosis lempel_ziv lpcc max_frequency max_power_spectrum
maximum_fractal_length mean_abs_deviation mean_abs_diff mean_diff median_abs_deviation
median_abs_diff median_diff median_frequency mfcc mse negative_turning neighbourhood_peaks
petrosian_fractal_dimension pk_pk_distance positive_turning power_bandwidth rms skewness slope
spectral_centroid spectral_decrease spectral_distance spectral_entropy spectral_kurtosis
spectral_positive_turning spectral_roll_off spectral_roll_on spectral_skewness spectral_slope
spectral_spread spectral_variation spectrogram_mean_coeff sum_abs_diff wavelet_abs_mean
wavelet_energy wavelet_entropy wavelet_std wavelet_var zero_cross""".split()


def to_scalar(result):
    if isinstance(result, dict) and "values" in result:
        result = result["values"]
    if isinstance(result, (list, tuple, np.ndarray)):
        return float(np.nanmean(np.asarray(result, dtype=float)))
    return float(result)


def extract_one(fn_name, signal, fs):
    fn = getattr(tsfel_features, fn_name)
    params = inspect.signature(fn).parameters
    result = fn(signal, fs) if "fs" in params else fn(signal)
    return to_scalar(result)


for pol in POLLUTANTS:
    df = pd.read_csv(f"../csv/{pol}_Nunukan_Timeseries_fixed.csv")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df[pol] = pd.to_numeric(df[pol], errors="coerce")

    # safety check outlier tambahan (IQR) sebelum ekstraksi fitur
    Q1, Q3 = df[pol].quantile(0.25), df[pol].quantile(0.75)
    IQR = Q3 - Q1
    df.loc[(df[pol] < Q1 - 1.5*IQR) | (df[pol] > Q3 + 1.5*IQR), pol] = np.nan
    df_clean = df.set_index("date").interpolate(method="time").ffill().bfill()
    signal_1d = df_clean[pol].astype(float).values

    row = {fn_name: extract_one(fn_name, signal_1d, fs) for fn_name in FEATURE_LIST}
    pd.DataFrame([row]).to_csv(f"../csv/{pol}_Nunukan_TSFEL.csv", index=False)
```

### Hasil ekstraksi fitur per domain

**Statistical Domain (21 fitur)**

| Fitur                 |            CO |             NO2 |            SO2 |
|:----------------------|--------------:|----------------:|---------------:|
| abs_energy            |   0.27862     |     2.36373e-08 |    7.22931e-07 |
| average_power         |   0.000763342 |     6.47597e-11 |    1.98063e-09 |
| calc_max              |   0.0348969   |     1.50682e-05 |    0.00010691  |
| calc_mean             |   0.0274505   |     7.09712e-06 |   -2.04958e-06 |
| calc_median           |   0.0271924   |     6.97647e-06 |   -3.81442e-06 |
| calc_min              |   0.0208626   |    -9.81828e-07 |   -0.000112941 |
| calc_std              |   0.00277938  |     3.77011e-06 |    4.43962e-05 |
| calc_var              |   7.72493e-06 |     1.42137e-11 |    1.97102e-09 |
| ecdf                  |   0.0150273   |     0.0150273   |    0.0150273   |
| ecdf_percentile       |   0.027383    |     6.98326e-06 |   -2.05955e-06 |
| ecdf_percentile_count | 182.5         |   182.5         |  182.5         |
| ecdf_slope            | 113.63        | 95097.9         | 8678.75        |
| entropy               |   0.989321    |     0.996949    |    0.999358    |
| hist_mode             |   0.0257746   |     6.2407e-06  |   -1.40084e-05 |
| interq_range          |   0.00377363  |     5.13729e-06 |    5.45609e-05 |
| kurtosis              |  -0.315646    |    -0.603237    |   -0.113452    |
| mean_abs_deviation    |   0.00226385  |     3.05789e-06 |    3.46067e-05 |
| median_abs_deviation  |   0.00195732  |     2.56269e-06 |    2.66183e-05 |
| pk_pk_distance        |   0.0140343   |     1.60501e-05 |    0.000219851 |
| rms                   |   0.0275909   |     8.03634e-06 |    4.44435e-05 |
| skewness              |   0.184097    |    -0.0531476   |    0.0190117   |

**Temporal Domain (21 fitur, termasuk sub-kategori fraktal)**

| Fitur                       |            CO |           NO2 |           SO2 |
|:----------------------------|--------------:|--------------:|--------------:|
| auc                         |  10.0163      |   0.00258932  |   0.0103055   |
| autocorr                    |   7           |   2           |   1           |
| calc_centroid               | 187.754       | 200.32        | 180.522       |
| dfa                         |   1.09545     |   0.850275    |   0.719522    |
| distance                    | 365.001       | 365           | 365           |
| higuchi_fractal_dimension   |   1.79642     |   1.88136     |   1.94272     |
| hurst_exponent              |   0.868289    |   0.717144    |   0.701121    |
| lempel_ziv                  |   0.166667    |   0.188525    |   0.202186    |
| maximum_fractal_length      |  -0.245368    |  -2.95763     |  -1.80483     |
| mean_abs_diff               |   0.00123694  |   2.56689e-06 |   3.90704e-05 |
| mean_diff                   |  -5.29308e-07 |   2.33994e-09 |   2.08623e-07 |
| median_abs_diff             |   0.00067574  |   1.66529e-06 |   2.94622e-05 |
| median_diff                 |   2.16304e-05 |   0           |  -1.59603e-06 |
| mse                         |   1.12817     |   1.17814     |   1.35631     |
| negative_turning            |  59           |  76           |  93           |
| neighbourhood_peaks         |  15           |  17           |  20           |
| petrosian_fractal_dimension |   1.02132     |   1.0269      |   1.03269     |
| positive_turning            |  59           |  75           |  94           |
| slope                       |   6.19674e-06 |   7.2994e-09  |   1.87767e-08 |
| sum_abs_diff                |   0.451485    |   0.000936914 |   0.0142607   |
| zero_cross                  |   0           |  16           | 122           |

**Spectral Domain (26 fitur)**

| Fitur                     |              CO |          NO2 |          SO2 |
|:--------------------------|----------------:|-------------:|-------------:|
| fundamental_frequency     |     0.00819672  |  0.00273224  |  0.00273224  |
| human_range_energy        |     0           |  0           |  0           |
| lpcc                      |     0.917156    |  0.588063    |  0.0971075   |
| max_frequency             |     0.382514    |  0.456284    |  0.464481    |
| max_power_spectrum        |    49.0833      | 37.7626      | 12.4217      |
| median_frequency          |     0           |  0.112022    |  0.202186    |
| mfcc                      |     8.43143     | 36.2542      | 42.3883      |
| power_bandwidth           |     0.352459    |  0.382514    |  0.434426    |
| spectral_centroid         |     0.065298    |  0.159281    |  0.217667    |
| spectral_decrease         |    -8.90315     | -1.366       |  0.00925378  |
| spectral_distance         | -1124.99        | -0.442803    | -1.68649     |
| spectral_entropy          |     0.671061    |  0.833144    |  0.90735     |
| spectral_kurtosis         |     5.95697     |  2.15339     |  1.84302     |
| spectral_positive_turning |    54           | 57           | 64           |
| spectral_roll_off         |     0.382514    |  0.456284    |  0.464481    |
| spectral_roll_on          |     0           |  0           |  0.0163934   |
| spectral_skewness         |     2.00925     |  0.679461    |  0.269873    |
| spectral_slope            |    -0.0476622   | -0.02341     | -0.0083436   |
| spectral_spread           |     0.123825    |  0.15516     |  0.145901    |
| spectral_variation        |     0.850024    |  0.564399    |  0.204832    |
| spectrogram_mean_coeff    |     1.28763e-05 |  2.5104e-11  |  3.70916e-09 |
| wavelet_abs_mean          |     0.00169461  |  3.50057e-07 |  5.04035e-07 |
| wavelet_energy            |     0.00760351  |  5.42583e-06 |  5.59249e-05 |
| wavelet_entropy           |     2.08358     |  2.17228     |  2.18574     |
| wavelet_std               |     0.0073996   |  5.41274e-06 |  5.59222e-05 |
| wavelet_var               |     6.59076e-05 |  3.11213e-11 |  3.19528e-09 |


## Penjelasan Domain TSFEL

Pustaka TSFEL membagi 68 fitur deret waktu menjadi tiga domain utama: **Statistik (Statistical)**, **Waktu (Temporal)**, dan **Frekuensi (Spectral)**. Berikut adalah penjabaran lengkap untuk masing-masing fitur beserta rumusnya, serta hasil perhitungannya yang diterapkan pada polutan NO2 (dari `NO2_filed.csv`) yang disajikan pada hasil akhir (`NO2_Baron_TSFEL.csv`).

### 1. Domain Statistical
Domain statistik mengekstrak metrik kuantitatif dan karakteristik sebaran serta bentuk distribusi dari sinyal deret waktu. Domain ini terdiri dari 17 fitur utama yang fokus pada distribusi.

1. **`calc_max`**
   - **Penjelasan**: Nilai maksimum dari deret waktu.
   - **Rumus**: $\max(x)$
   - **Hasil (NO2)**: `5.51000e-05`

2. **`calc_min`**
   - **Penjelasan**: Nilai minimum dari deret waktu.
   - **Rumus**: $\min(x)$
   - **Hasil (NO2)**: `5.12000e-06`

3. **`calc_mean`**
   - **Penjelasan**: Rata-rata (mean) dari deret waktu.
   - **Rumus**: $\mu = \frac{1}{N} \sum_{i=1}^N x_i$
   - **Hasil (NO2)**: `2.84004e-05`

4. **`calc_median`**
   - **Penjelasan**: Nilai tengah (median) dari deret waktu.
   - **Rumus**: $\text{median}(x)$
   - **Hasil (NO2)**: `2.81250e-05`

5. **`calc_std`**
   - **Penjelasan**: Standar deviasi, mengukur tingkat penyebaran data.
   - **Rumus**: $\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^N (x_i - \mu)^2}$
   - **Hasil (NO2)**: `1.01280e-05`

6. **`calc_var`**
   - **Penjelasan**: Varians, kuadrat dari standar deviasi.
   - **Rumus**: $\sigma^2 = \frac{1}{N} \sum_{i=1}^N (x_i - \mu)^2$
   - **Hasil (NO2)**: `1.02577e-10`

7. **`ecdf`**
   - **Penjelasan**: Fungsi distribusi kumulatif empiris.
   - **Rumus**: $\hat{F}(t) = \frac{1}{N} \sum_{i=1}^N \mathbf{1}_{x_i \le t}$
   - **Hasil (NO2)**: `1.50273e-02`

8. **`ecdf_percentile`**
   - **Penjelasan**: Nilai ECDF pada persentil tertentu.
   - **Rumus**: $P_{perc}(\hat{F})$
   - **Hasil (NO2)**: `2.84000e-05`

9. **`ecdf_percentile_count`**
   - **Penjelasan**: Jumlah data yang berada di bawah persentil ECDF.
   - **Rumus**: $\sum \mathbf{1}_{x_i \le P_{perc}}$
   - **Hasil (NO2)**: `1.82500e+02`

10. **`ecdf_slope`**
   - **Penjelasan**: Kemiringan dari kurva ECDF.
   - **Rumus**: $\frac{\Delta y}{\Delta x} \text{ pada } \hat{F}(t)$
   - **Hasil (NO2)**: `3.47222e+04`

11. **`hist_mode`**
   - **Penjelasan**: Modus (nilai paling sering muncul) berdasarkan histogram.
   - **Rumus**: $\arg\max_j (\text{count}(bin_j))$
   - **Hasil (NO2)**: `2.76110e-05`

12. **`interq_range`**
   - **Penjelasan**: Jangkauan interkuartil (IQR), selisih Q3 dan Q1.
   - **Rumus**: $IQR = Q_3 - Q_1$
   - **Hasil (NO2)**: `1.45000e-05`

13. **`kurtosis`**
   - **Penjelasan**: Keruncingan (peakedness) dari distribusi data.
   - **Rumus**: $K = \frac{\frac{1}{N} \sum_{i=1}^N (x_i - \mu)^4}{\sigma^4} - 3$
   - **Hasil (NO2)**: `-4.15397e-01`

14. **`skewness`**
   - **Penjelasan**: Kemiringan (asimetri) dari distribusi data.
   - **Rumus**: $S = \frac{\frac{1}{N} \sum_{i=1}^N (x_i - \mu)^3}{\sigma^3}$
   - **Hasil (NO2)**: `1.02776e-01`

15. **`mean_abs_deviation`**
   - **Penjelasan**: Rata-rata simpangan absolut dari mean.
   - **Rumus**: $MAD = \frac{1}{N} \sum_{i=1}^N |x_i - \mu|$
   - **Hasil (NO2)**: `8.22498e-06`

16. **`median_abs_deviation`**
   - **Penjelasan**: Median dari simpangan absolut dari median.
   - **Rumus**: $\text{Median}(|x_i - \text{median}(x)|)$
   - **Hasil (NO2)**: `7.10833e-06`

17. **`rms`**
   - **Penjelasan**: Root Mean Square (energi kuadrat rata-rata).
   - **Rumus**: $RMS = \sqrt{\frac{1}{N} \sum_{i=1}^N x_i^2}$
   - **Hasil (NO2)**: `3.01523e-05`

### 2. Domain Temporal
Domain temporal mengevaluasi sinyal dari segi urutan waktunya. Terdiri dari 25 fitur yang mengukur dependensi, jarak, autokorelasi, dan kompleksitas waktu.

1. **`abs_energy`**
   - **Penjelasan**: Total energi absolut dari deret waktu.
   - **Rumus**: $E = \sum_{i=1}^N x_i^2$
   - **Hasil (NO2)**: `3.32752e-07`

2. **`auc`**
   - **Penjelasan**: Area di bawah kurva sinyal (Area Under Curve).
   - **Rumus**: $AUC = \sum_{i=1}^{N-1} \frac{x_i + x_{i+1}}{2}$
   - **Hasil (NO2)**: `1.03695e-02`

3. **`autocorr`**
   - **Penjelasan**: Autokorelasi sinyal, kesamaan sinyal dengan versi tertundanya.
   - **Rumus**: $R(\tau) = \sum_{i=1}^{N-\tau} x_i x_{i+\tau}$
   - **Hasil (NO2)**: `1.70000e+01`

4. **`average_power`**
   - **Penjelasan**: Daya rata-rata dari sinyal waktu.
   - **Rumus**: $P = \frac{1}{N} \sum_{i=1}^N x_i^2$
   - **Hasil (NO2)**: `9.11650e-10`

5. **`calc_centroid`**
   - **Penjelasan**: Titik pusat dari urutan waktu (Time Centroid).
   - **Rumus**: $C_t = \frac{\sum t_i \cdot x_i}{\sum x_i}$
   - **Hasil (NO2)**: `2.03671e+02`

6. **`dfa`**
   - **Penjelasan**: Detrended Fluctuation Analysis, untuk mengukur dependensi fraktal.
   - **Rumus**: $F(n) \propto n^\alpha$
   - **Hasil (NO2)**: `1.01119e+00`

7. **`distance`**
   - **Penjelasan**: Total jarak (panjang lintasan) antar titik-titik berturutan.
   - **Rumus**: $D = \sum_{i=1}^{N-1} \sqrt{1 + (x_{i+1} - x_i)^2}$
   - **Hasil (NO2)**: `3.65000e+02`

8. **`entropy`**
   - **Penjelasan**: Shannon Entropy, mengukur ketidakpastian sinyal.
   - **Rumus**: $H = -\sum p(x) \log p(x)$
   - **Hasil (NO2)**: `9.27850e-01`

9. **`higuchi_fractal_dimension`**
   - **Penjelasan**: Dimensi Fraktal Higuchi, mengukur kompleksitas bentuk.
   - **Rumus**: $L(k) \propto k^{-D}$
   - **Hasil (NO2)**: `1.84022e+00`

10. **`hurst_exponent`**
   - **Penjelasan**: Eksponen Hurst, indikasi memori jangka panjang waktu.
   - **Rumus**: $E[\frac{R(n)}{S(n)}] = C n^H$
   - **Hasil (NO2)**: `8.03093e-01`

11. **`lempel_ziv`**
   - **Penjelasan**: Kompleksitas Lempel-Ziv, mengukur tingkat kompresibilitas sinyal.
   - **Rumus**: $LZ = \frac{c(N)}{\frac{N}{\log N}}$
   - **Hasil (NO2)**: `1.72131e-01`

12. **`maximum_fractal_length`**
   - **Penjelasan**: Panjang maksimal fraktal di berbagai skala pengukuran.
   - **Rumus**: $L_{max} = \max_k (L(k))$
   - **Hasil (NO2)**: `-2.69521e+00`

13. **`mean_abs_diff`**
   - **Penjelasan**: Rata-rata dari perbedaan absolut titik berurutan.
   - **Rumus**: $\mu_{\Delta} = \frac{1}{N-1} \sum_{i=1}^{N-1} |x_{i+1} - x_i|$
   - **Hasil (NO2)**: `4.56367e-06`

14. **`mean_diff`**
   - **Penjelasan**: Rata-rata perbedaan antara titik berurutan.
   - **Rumus**: $\mu_{d} = \frac{1}{N-1} \sum_{i=1}^{N-1} (x_{i+1} - x_i)$
   - **Hasil (NO2)**: `1.20548e-08`

15. **`median_abs_diff`**
   - **Penjelasan**: Median perbedaan absolut berurutan.
   - **Rumus**: $\text{Median}(|x_{i+1} - x_i|)$
   - **Hasil (NO2)**: `2.50000e-06`

16. **`median_diff`**
   - **Penjelasan**: Median dari selisih titik berurutan.
   - **Rumus**: $\text{Median}(x_{i+1} - x_i)$
   - **Hasil (NO2)**: `4.00000e-07`

17. **`mse`**
   - **Penjelasan**: Mean Squared Error dari sinyal terhadap rata-ratanya.
   - **Rumus**: $MSE = \frac{1}{N} \sum_{i=1}^N (x_i - \mu)^2$
   - **Hasil (NO2)**: `1.28358e+00`

18. **`negative_turning`**
   - **Penjelasan**: Jumlah titik belok bergradien negatif (puncak yang turun).
   - **Rumus**: $\sum \mathbf{1}_{x_{i-1} < x_i > x_{i+1}}$
   - **Hasil (NO2)**: `6.70000e+01`

19. **`neighbourhood_peaks`**
   - **Penjelasan**: Jumlah puncak pada area bertetangga yang ditentukan.
   - **Rumus**: $\sum \text{Peaks}(x, \text{window})$
   - **Hasil (NO2)**: `1.60000e+01`

20. **`petrosian_fractal_dimension`**
   - **Penjelasan**: Dimensi Fraktal Petrosian.
   - **Rumus**: $D = \frac{\log_{10}(N)}{\log_{10}(N) + \log_{10}(\frac{N}{N + 0.4 N_{\Delta}})}$
   - **Hasil (NO2)**: `1.02404e+00`

21. **`pk_pk_distance`**
   - **Penjelasan**: Jarak dari puncak tertinggi ke lembah terendah (Peak-to-Peak).
   - **Rumus**: $P2P = \max(x) - \min(x)$
   - **Hasil (NO2)**: `4.99800e-05`

22. **`positive_turning`**
   - **Penjelasan**: Jumlah titik belok bergradien positif (lembah yang naik).
   - **Rumus**: $\sum \mathbf{1}_{x_{i-1} > x_i < x_{i+1}}$
   - **Hasil (NO2)**: `6.80000e+01`

23. **`slope`**
   - **Penjelasan**: Kemiringan tren regresi linier secara keseluruhan.
   - **Rumus**: $m = \frac{\sum (t_i - \bar{t})(x_i - \mu)}{\sum (t_i - \bar{t})^2}$
   - **Hasil (NO2)**: `2.85331e-08`

24. **`sum_abs_diff`**
   - **Penjelasan**: Total akumulasi perbedaan absolut titik berurutan.
   - **Rumus**: $SAD = \sum_{i=1}^{N-1} |x_{i+1} - x_i|$
   - **Hasil (NO2)**: `1.66574e-03`

25. **`zero_cross`**
   - **Penjelasan**: Jumlah titik perpotongan nol (zero-crossing).
   - **Rumus**: $\sum \mathbf{1}_{x_i \cdot x_{i+1} < 0}$
   - **Hasil (NO2)**: `0.00000e+00`

### 3. Domain Spectral
Domain spektral mentransformasi data ke domain frekuensi (melalui Fourier/Wavelet). Terdiri dari 26 fitur untuk mengukur sifat periodik, energi spektrum, dan rentang frekuensi.

1. **`fundamental_frequency`**
   - **Penjelasan**: Frekuensi dasar yang paling kuat pada spektrum.
   - **Rumus**: $f_0 = \arg\max_f (|X(f)|^2)$
   - **Hasil (NO2)**: `2.73224e-03`

2. **`max_frequency`**
   - **Penjelasan**: Frekuensi tertinggi pada analisis spektrum daya.
   - **Rumus**: $f_{max} = \max(f)$
   - **Hasil (NO2)**: `4.34426e-01`

3. **`median_frequency`**
   - **Penjelasan**: Frekuensi yang membagi spektrum daya (energi) menjadi dua bagian sama.
   - **Rumus**: $\int_0^{f_{med}} |X(f)|^2 df = \frac{1}{2} \int_0^\infty |X(f)|^2 df$
   - **Hasil (NO2)**: `4.09836e-02`

4. **`human_range_energy`**
   - **Penjelasan**: Energi sinyal pada jangkauan pendengaran manusia.
   - **Rumus**: $E_h = \sum_{f \in H} |X(f)|^2$
   - **Hasil (NO2)**: `0.00000e+00`

5. **`lpcc`**
   - **Penjelasan**: Koefisien Linear Prediction Cepstral (LPCC).
   - **Rumus**: $C_n = -a_n - \sum_{k=1}^{n-1} \frac{k}{n} C_k a_{n-k}$
   - **Hasil (NO2)**: `7.48200e-01`

6. **`mfcc`**
   - **Penjelasan**: Koefisien Mel-Frequency Cepstral (MFCC).
   - **Rumus**: $c_n = \sum_{k=1}^K (\log S_k) \cos\left[n(k-\frac{1}{2})\frac{\pi}{K}\right]$
   - **Hasil (NO2)**: `2.43670e+01`

7. **`max_power_spectrum`**
   - **Penjelasan**: Daya tertinggi dari seluruh rentang spektrum frekuensi.
   - **Rumus**: $\max_f (|X(f)|^2)$
   - **Hasil (NO2)**: `1.22004e+02`

8. **`power_bandwidth`**
   - **Penjelasan**: Lebar pita tempat akumulasi mayoritas kekuatan sinyal (daya).
   - **Rumus**: $BW = f_{upper} - f_{lower}$
   - **Hasil (NO2)**: `3.22404e-01`

9. **`spectral_centroid`**
   - **Penjelasan**: Pusat massa spektral (frekuensi rata-rata berbobot energi).
   - **Rumus**: $C_s = \frac{\sum f_k |X(f_k)|}{\sum |X(f_k)|}$
   - **Hasil (NO2)**: `1.20096e-01`

10. **`spectral_decrease`**
   - **Penjelasan**: Tingkat penurunan kekuatan spektral pada frekuensi yang meninggi.
   - **Rumus**: $D_s = \frac{\sum_{k=2}^K \frac{|X(f_k)| - |X(f_1)|}{k-1}}{\sum_{k=2}^K |X(f_k)|}$
   - **Hasil (NO2)**: `-2.52716e+00`

11. **`spectral_distance`**
   - **Penjelasan**: Jarak spektral, selisih antar kurva densitas spektrum.
   - **Rumus**: $D(X, Y) = \sqrt{\sum (X(f) - Y(f))^2}$
   - **Hasil (NO2)**: `-1.58982e+00`

12. **`spectral_entropy`**
   - **Penjelasan**: Entropi spektral, seberapa menyebar distribusi energi spektrum.
   - **Rumus**: $H_s = -\sum p_f \log p_f$
   - **Hasil (NO2)**: `6.21878e-01`

13. **`spectral_kurtosis`**
   - **Penjelasan**: Kurtosis dari kepadatan daya spektrum.
   - **Rumus**: $K_s = \frac{\sum (f - C_s)^4 |X(f)|^2}{(\sum (f - C_s)^2 |X(f)|^2)^2}$
   - **Hasil (NO2)**: `2.71723e+00`

14. **`spectral_positive_turning`**
   - **Penjelasan**: Titik belok positif pada kurva spektrum.
   - **Rumus**: $\sum \mathbf{1}_{|X(f_{i-1})| > |X(f_i)| < |X(f_{i+1})|}$
   - **Hasil (NO2)**: `6.10000e+01`

15. **`spectral_roll_off`**
   - **Penjelasan**: Frekuensi roll-off di mana sebagian besar energi spektral terkonsentrasi.
   - **Rumus**: $f_c \text{ dimana } \sum_{f=0}^{f_c} |X(f)|^2 = 0.95 \sum_{f} |X(f)|^2$
   - **Hasil (NO2)**: `4.34426e-01`

16. **`spectral_roll_on`**
   - **Penjelasan**: Frekuensi roll-on tempat sebagian kecil energi (misal 5%) terakumulasi.
   - **Rumus**: $f_c \text{ dimana } \sum_{f=0}^{f_c} |X(f)|^2 = 0.05 \sum_{f} |X(f)|^2$
   - **Hasil (NO2)**: `0.00000e+00`

17. **`spectral_skewness`**
   - **Penjelasan**: Skewness (kemiringan) dari kepadatan daya spektrum.
   - **Rumus**: $S_s = \frac{\sum (f - C_s)^3 |X(f)|^2}{(\sum (f - C_s)^2 |X(f)|^2)^{3/2}}$
   - **Hasil (NO2)**: `1.05467e+00`

18. **`spectral_slope`**
   - **Penjelasan**: Kemiringan dari spektrum daya yang dihitung menggunakan regresi linier.
   - **Rumus**: $m_s = \frac{\sum (f_i - \bar{f})(|X(f_i)| - \overline{|X(f)|})}{\sum (f_i - \bar{f})^2}$
   - **Hasil (NO2)**: `-3.35216e-02`

19. **`spectral_spread`**
   - **Penjelasan**: Sebaran spektrum atau varians frekuensi di sekeliling pusat massa.
   - **Rumus**: $V_s = \sqrt{\frac{\sum (f_k - C_s)^2 |X(f_k)|}{\sum |X(f_k)|}}$
   - **Hasil (NO2)**: `1.50384e-01`

20. **`spectral_variation`**
   - **Penjelasan**: Variasi atau jarak perubahan spektrum pada titik yang berdekatan.
   - **Rumus**: $V = 1 - \frac{\sum X_{t-1}(f) X_t(f)}{\sqrt{\sum X_{t-1}^2 \sum X_t^2}}$
   - **Hasil (NO2)**: `2.64122e-01`

21. **`spectrogram_mean_coeff`**
   - **Penjelasan**: Koefisien magnitudo rata-rata dari matriks spektrogram.
   - **Rumus**: $\frac{1}{T F} \sum_t \sum_f |S(t, f)|$
   - **Hasil (NO2)**: `1.21204e-10`

22. **`wavelet_abs_mean`**
   - **Penjelasan**: Rata-rata magnitudo absolut dari koefisien transformasi wavelet.
   - **Rumus**: $\mu_w = \frac{1}{N} \sum |W(a,b)|$
   - **Hasil (NO2)**: `1.83560e-06`

23. **`wavelet_energy`**
   - **Penjelasan**: Energi total yang terkandung di dalam koefisien wavelet.
   - **Rumus**: $E_w = \sum |W(a,b)|^2$
   - **Hasil (NO2)**: `1.42750e-05`

24. **`wavelet_entropy`**
   - **Penjelasan**: Entropi wavelet, ukuran distribusi sebaran energi di ruang waktu-frekuensi.
   - **Rumus**: $H_w = -\sum p_j \log p_j, p_j = \frac{E_j}{E_{tot}}$
   - **Hasil (NO2)**: `2.12394e+00`

25. **`wavelet_std`**
   - **Penjelasan**: Standar deviasi dari sebaran koefisien wavelet.
   - **Rumus**: $\sigma_w = \sqrt{\frac{1}{N} \sum (|W(a,b)| - \mu_w)^2}$
   - **Hasil (NO2)**: `1.41400e-05`

26. **`wavelet_var`**
   - **Penjelasan**: Varians dari koefisien dispersi wavelet.
   - **Rumus**: $\sigma_w^2$
   - **Hasil (NO2)**: `2.24529e-10`

## Ringkasan

| Tahap | Keterangan |
|---|---|
| Preprocessing | Data difilter sesuai Kabupaten Nunukan, missing value diimputasi penuh (0 nilai kosong tersisa dari 366 hari), outlier dideteksi dengan Isolation Forest (~5,19% data per polutan) dan diperbaiki lewat interpolasi waktu |
| Catatan khusus | Lonjakan CO akhir Agustus 2026 teridentifikasi sebagai outlier statistik, namun sebenarnya mencerminkan kejadian nyata (karhutla/asap Kalimantan), bukan kesalahan data |
| Ekstraksi fitur | 68 fitur time series diekstrak dengan TSFEL untuk tiap polutan, terbagi ke domain Statistical (21), Temporal (21, termasuk fraktal), dan Spectral (26) |