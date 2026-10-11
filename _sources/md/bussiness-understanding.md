# Business Understanding

## 1. Latar Belakang
Kualitas udara adalah indikator esensial bagi kesehatan publik dan kelestarian lingkungan. Seiring meningkatnya aktivitas warga, mobilitas transportasi, serta kegiatan ekonomi, risiko lonjakan gas polutan berbahaya di udara ikut membesar. Kabupaten Nunukan, sebagai wilayah yang terus berkembang di Kalimantan Utara, tentu tidak kebal terhadap potensi fluktuasi kualitas udara ini.

Tiga jenis gas polutan utama yang menjadi fokus pemantauan global meliputi:
* **Nitrogen Dioksida (NO₂):** Umumnya dipicu oleh emisi kendaraan bermotor dan operasional industri.
* **Karbon Monoksida (CO):** Gas beracun yang bersumber dari proses pembakaran tidak sempurna.
* **Belerang Dioksida (SO₂):** Polutan yang kerap muncul dari aktivitas vulkanik maupun pembakaran bahan bakar fosil yang mengandung sulfur.

Pemantauan polutan secara berkala sangat krusial untuk memetakan pola polusi di suatu kawasan. Dalam proyek ini, kita mendayagunakan teknologi satelit canggih Sentinel-5P dari *Copernicus Data Space Ecosystem* untuk mengobservasi kadar polutan udara di Kabupaten Nunukan. Data tersebut direkam dan disajikan dalam format deret waktu (*Time Series*) yang dimulai sejak akhir tahun 2023.

## 2. Rumusan Masalah
Fokus utama dari analisis data ini ditujukan untuk menjawab pertanyaan berikut:
* Bagaimana pergerakan tren harian konsentrasi gas polutan (NO₂, CO, dan SO₂) di wilayah Kabupaten Nunukan?
* Apakah ditemukan adanya siklus musiman, tren kenaikan jangka panjang, atau anomali lonjakan ekstrem pada tingkat polusi udara setempat?

## 3. Tujuan Proyek
Eksplorasi sains data ini dijalankan dengan tujuan:
* Membangun otomasi pengumpulan data citra satelit spasial (NetCDF) dan mentransformasikannya menjadi *dataset* tabular (CSV) yang siap dianalisis.
* Menjalankan Analisis Data Eksploratif (EDA) guna memahami karakteristik dan tren perubahan gas polutan dari waktu ke waktu.
* Menciptakan landasan data historis yang valid sebagai modal awal untuk keperluan pemodelan prediktif (*forecasting*) kualitas udara di masa depan.

## 4. Manfaat Proyek
*Insight* yang dihasilkan dari pengolahan data ini diharapkan mampu memberikan dampak positif bagi berbagai pihak:
* **Pemerintah & Pembuat Kebijakan:** Menyediakan *insight* berbasis data guna mendukung pengambilan keputusan strategis terkait regulasi lingkungan, manajemen lalu lintas, dan pengawasan emisi.
* **Masyarakat Umum:** Menjadi sarana informasi yang transparan untuk menumbuhkan kesadaran warga terhadap dinamika kualitas udara harian di lingkungan mereka.
* **Akademisi & Praktisi Data:** Menjadi studi kasus nyata (*use case*) yang menguji penerapan metodologi pengolahan data spasial beresolusi tinggi ke dalam pemodelan *Time Series*.