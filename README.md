# Analisa Saham BEI/IDX

Analisa Saham BEI/IDX adalah aplikasi Streamlit untuk membantu membaca data saham Indonesia dengan bahasa yang lebih mudah dipahami. Data harga dan profil perusahaan diambil dari Yahoo Finance melalui `yfinance`.

Aplikasi ini dibuat sebagai alat bantu belajar dan analisa awal, bukan sebagai rekomendasi investasi resmi.

## Yang Bisa Dilakukan Aplikasi Ini

Dengan aplikasi ini, pengguna bisa:

- melihat harga saham BEI/IDX,
- membaca ringkasan singkat perusahaan,
- melihat grafik harga saham,
- membandingkan sampai 5 saham sekaligus,
- membaca tanda sederhana dari beberapa indikator grafik,
- mencoba simulasi cara beli/jual berdasarkan data lama,
- menghitung risiko, stop loss, dan jumlah lot secara otomatis.

## Tampilan Utama

Aplikasi memiliki tampilan gelap dengan warna hijau untuk kondisi naik dan merah untuk kondisi turun. Di bagian atas halaman ada running text harga saham agar pengguna bisa cepat melihat saham yang sedang bergerak naik atau turun.

Di sidebar kiri, pengguna bisa mengatur saham, periode data, jenis grafik, alat bantu grafik, dan kalkulator risiko. Jika mode perbandingan dipakai, pengguna juga bisa memilih saham mana yang ingin dihitung di kalkulator risiko.

## Mode Analisa

### 1. Single Saham

Mode ini dipakai untuk melihat satu saham secara lebih detail. Pengguna bisa memilih saham dari daftar yang tersedia atau mengetik ticker manual.

Yang ditampilkan antara lain:

- cerita singkat perusahaan,
- nilai perusahaan di bursa,
- P/E atau perbandingan harga saham dengan laba,
- dividen per tahun jika tersedia,
- harga terakhir,
- harga tertinggi dan terendah selama periode yang dipilih,
- volume perdagangan,
- perubahan harga selama periode,
- gambaran cepat dari beberapa indikator,
- simulasi cara beli/jual,
- grafik harga dan alat bantu grafik.

### 2. Bandingkan Saham

Mode ini dipakai untuk membandingkan beberapa saham sekaligus, maksimal 5 saham.

Pengguna bisa memilih saham dari daftar yang tersedia di aplikasi atau mengetik ticker manual, misalnya:

```text
BBCA, BBRI, TLKM
```

Jika ticker manual tidak memakai `.JK`, aplikasi akan menambahkannya otomatis. Ini berlaku di mode Single Saham dan Bandingkan Saham.

Contoh:

```text
BBCA
```

akan dibaca sebagai:

```text
BBCA.JK
```

Di mode ini, aplikasi menampilkan:

- grafik perbandingan perubahan harga,
- ringkasan perbandingan antar saham,
- grafik harga masing-masing saham,
- detail masing-masing saham di tab terpisah.

## Periode Data

Pilihan periode data tersedia di sidebar:

- 1 Hari dengan data 5 menit,
- 1 Minggu dengan data 15 menit,
- 1 Bulan,
- 3 Bulan,
- 6 Bulan,
- 1 Tahun,
- 2 Tahun,
- 5 Tahun.

Untuk membaca simulasi beli/jual, sebaiknya gunakan periode yang lebih panjang seperti 6 Bulan, 1 Tahun, 2 Tahun, atau 5 Tahun. Periode yang terlalu pendek sering belum cukup untuk membentuk sinyal.

## Jenis Grafik

Aplikasi menyediakan beberapa jenis grafik:

- Candlestick,
- Garis harga penutupan,
- OHLC atau batang,
- Heikin-Ashi,
- Renko,
- Point & Figure.

Untuk pengguna awam, grafik garis dan candlestick biasanya paling mudah dipahami.

Grafik Renko dan Point & Figure tidak memakai alur waktu seperti grafik biasa. Karena itu, volume dan beberapa garis bantu otomatis tidak ditampilkan pada dua jenis grafik tersebut.

## Alat Bantu Grafik

Beberapa alat bantu yang tersedia:

### MA 20 dan MA 50

Garis rata-rata harga. MA 20 melihat arah harga jangka pendek, sedangkan MA 50 melihat arah harga yang lebih panjang.

### Bollinger Bands

Pita batas atas dan bawah untuk melihat apakah harga mulai terlalu tinggi atau terlalu rendah dibanding kebiasaannya.

### Garis Arah Harga

Garis bantu untuk melihat kecenderungan harga, apakah lebih condong naik, turun, atau datar.

### RSI

Membantu melihat apakah saham mulai terlalu ramai dibeli atau terlalu banyak dijual.

### MACD

Membantu melihat perubahan tenaga naik atau turun.

### Naik-Turun Harian

Menampilkan seberapa besar harga biasa naik atau turun setiap hari.

### Stochastic

Membantu melihat tanda awal apakah harga berpotensi mulai berbalik arah.

### OBV

Membantu melihat apakah volume perdagangan mendukung arah harga.

### ATR

Menunjukkan seberapa lebar harga bergerak belakangan ini.

## Gambaran Cepat

Bagian Gambaran Cepat menggabungkan beberapa tanda dari grafik dan menampilkannya dalam bahasa sederhana.

Kemungkinan hasilnya:

- `PELUANG BELI KUAT`,
- `CENDERUNG BISA BELI`,
- `TUNGGU DULU`,
- `CENDERUNG HATI-HATI`,
- `WASPADA, TEKANAN JUAL KUAT`,
- `DATA BELUM CUKUP`.

Gambaran ini hanya alat bantu membaca grafik. Hasilnya bukan jaminan harga akan naik atau turun.

## Coba Simulasi Cara Beli/Jual

Fitur ini digunakan untuk melihat bagaimana hasil aturan beli/jual aplikasi jika diterapkan pada data harga masa lalu. Modal awal simulasi mengikuti nilai `Modal Maksimal (Rp)` yang diisi di bagian `HITUNG RISIKO & LOT`.

Cara kerjanya sederhana:

1. Aplikasi membaca data harga dari awal periode sampai akhir periode.
2. Setiap hari, aplikasi mengecek beberapa tanda dari grafik.
3. Jika minimal 2 tanda mengarah ke beli dan tidak ada tanda jual, aplikasi pura-pura membeli saham.
4. Jika minimal 2 tanda mengarah ke jual dan tidak ada tanda beli, aplikasi pura-pura menjual saham.
5. Di akhir periode, aplikasi menghitung hasilnya.

Bagian ini menampilkan:

- hasil cara simulasi,
- perbandingan dengan beli lalu simpan,
- jumlah transaksi,
- persentase transaksi yang untung,
- penurunan terbesar selama simulasi,
- catatan beli dan jual jika ada transaksi.

Jika tidak ada transaksi, artinya selama periode tersebut aplikasi tidak menemukan momen beli/jual yang cukup kuat berdasarkan aturan yang dipakai.

Simulasi masa lalu tidak menjamin hasil masa depan. Fitur ini lebih cocok dipakai untuk belajar dan memahami risiko.

## Hitung Risiko dan Lot

Di sidebar ada bagian `HITUNG RISIKO & LOT`.

Input yang tersedia:

- Modal Maksimal,
- Harga Beli,
- Batas Risiko.

Hasil yang ditampilkan:

- Maks Beli,
- Dana Pakai,
- Stop Loss,
- Risiko dalam Rupiah.

Bagian ini tidak memakai tombol. Hasil akan berubah otomatis setiap kali pengguna mengubah angka modal, harga beli, atau batas risiko. Pada mode Bandingkan Saham, pengguna bisa memilih saham yang mau dihitung melalui pilihan `Pilih Saham Kalkulator`.

## Data Historis

Di bagian bawah detail saham, pengguna bisa membuka data historis 30 baris terakhir. Data ini juga bisa diekspor ke CSV melalui tombol download yang tersedia di aplikasi.

## Struktur File

```bash
├── app.py              # Tampilan utama Streamlit dan alur aplikasi
├── data_loader.py      # Ambil data harga, profil perusahaan, dan konfigurasi
├── config_saham.json   # Daftar saham, pilihan periode, sektor, dan cerita perusahaan
├── charts.py           # Pembuatan grafik harga dan alat bantu grafik
├── indicators.py       # Hitungan indikator, gambaran cepat, dan simulasi beli/jual
├── requirements.txt    # Daftar library yang dibutuhkan
└── README.md           # Dokumentasi aplikasi
```

## Cara Menjalankan

### 1. Masuk ke folder project

```bash
cd saham
```

### 2. Install dependency

```bash
pip install -r requirements.txt
```

### 3. Jalankan aplikasi

```bash
streamlit run app.py
```

Setelah berjalan, aplikasi biasanya bisa dibuka di browser melalui:

```text
http://localhost:8501
```

## Catatan Data

Data diambil dari Yahoo Finance melalui `yfinance`.

Aplikasi memakai cache agar pengambilan data tidak terlalu sering:

- data harga diperbarui sekitar 5 menit sekali,
- data profil perusahaan diperbarui sekitar 1 jam sekali.

Jika data tidak muncul, kemungkinan penyebabnya:

- koneksi internet bermasalah,
- ticker salah,
- Yahoo Finance sedang lambat,
- data saham tidak lengkap,
- saham tidak tersedia di Yahoo Finance.

## Disclaimer

Aplikasi ini dibuat untuk belajar dan membantu membaca data saham. Semua keputusan beli, jual, atau tahan saham tetap menjadi tanggung jawab masing-masing pengguna.
