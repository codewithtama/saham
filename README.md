# Analisa Saham BEI/IDX

Dashboard analisis saham Indonesia berbasis Streamlit. Data harga, profil perusahaan, laporan keuangan, dan histori dividen diambil langsung dari Yahoo Finance melalui library `yfinance`. Aplikasi ini dioptimalkan dengan pemrosesan paralel (multithreading) dan mekanisme cache lokal yang cerdas.

---

## Fitur Utama

- **Running Marquee Ticker (Header)**: Running text harga saham real-time di bagian atas halaman yang telah diselaraskan desainnya. Menampilkan kurs **USD/IDR**, indeks pasar (**IHSG** dan **LQ45**), serta pergerakan saham blue-chip dengan pemisah garis pemisah (`ticker-divider`) yang seragam.
- **Analisis Saham Komprehensif (Mode Single)**:
  - Profil dan ringkasan bisnis perusahaan.
  - Angka fundamental: Market Cap, P/E Ratio, PBV, ROE, DER, Beta, dan Dividend Yield.
  - Grafik laporan keuangan tahunan (Revenue vs Net Income) dan riwayat dividen.
  - **Jadwal Dividen Terkini**: Menampilkan *Ex-Dividend Date* dan *Payment Date* dengan format tanggal lokal WIB.
  - **Berita Terbaru Saham**: Menampilkan artikel berita terhangat dengan mekanisme pertahanan bertingkat (*multi-stage fallback*) dari keyword search hingga berita pasar umum IHSG (`^JKSE`).
  - **Sinyal Teknikal & Konsensus**: Konsensus sinyal instan (Beli Kuat, Beli, Tunggu, Hati-hati, Jual) berdasarkan akumulasi indikator RSI, MA Cross, MACD, dan Stochastic.
  - Grafik interaktif (Candlestick, Line, OHLC, Heikin-Ashi, Renko, P&F) dengan support & resistance otomatis dari swing high/low.
- **Bandingkan Saham (Maks 5)**:
  - Grafik harga ternormalisasi ke basis 100% untuk membandingkan performa pergerakan.
  - Tabel ringkasan perbandingan metrik fundamental dan volatilitas risiko.
  - **Korelasi Return Harian**: Heatmap matriks korelasi return harian antar saham pilihan untuk analisis diversifikasi portofolio.
- **Stock Screener**: Saringan saham IDX berdasarkan kriteria fundamental (Sektor, Batas Maks P/E, Min ROE %, Maks DER %, Min Div Yield %, dan Min Market Cap). Berjalan instan (<10ms) menggunakan data fundamental mentah yang di-cache.
- **Watchlist**: Simpan saham favorit Anda ke penyimpanan lokal (`watchlist.json`). Tab Watchlist menampilkan tabel harga terakhir dan persentase perubahan harian yang dimuat secara konkuren menggunakan thread pool.
- **Portfolio Tracker**: 
  - Catat transaksi lot, harga beli, dan tanggal beli Anda.
  - Menghitung modal awal, nilai portofolio terkini, unrealized P/L (Rp & %), dan rasio posisi untung secara otomatis.
  - **Kebijakan Nol Luapan (Zero Overflowed Policy)**: Ukuran font metrik utama (Total Modal, Nilai Portofolio Kini, P/L) dikunci dengan font `JetBrains Mono` yang ramah resolusi agar tidak merusak tata letak/overflow.
  - **Ekspor Portfolio ke CSV**: Unduh ringkasan transaksi portofolio Anda ke file CSV secara instan.
- **Mode Offline**: Deteksi hilangnya koneksi internet secara otomatis dan menampilkan data cadangan dari cache lokal (`cache/`) dengan banner notifikasi waktu cache.

---

## Periode Data

| Pilihan        | Interval Data  | Deskripsi |
|----------------|----------------|---|
| 1 Hari         | 5 menit        | Intraday pendek |
| 1 Minggu       | 15 menit       | Intraday menengah |
| 1 Bulan        | Harian         | Data penutupan harian |
| 3 Bulan        | Harian         | Data penutupan harian |
| 6 Bulan        | Harian         | Data penutupan harian |
| 1 Tahun        | Harian         | Data penutupan harian |
| 2 Tahun        | Harian         | Data penutupan harian |
| 5 Tahun        | Harian         | Data penutupan harian |

---

## Jenis Grafik Utama

- **Candlestick**: Lilin standar pembukaan, tertinggi, terendah, dan penutupan.
- **Garis (Close)**: Garis sederhana harga penutupan.
- **OHLC / Batang**: Grafik batang penentu pergerakan harga.
- **Heikin-Ashi**: Lilin dengan nilai rata-rata untuk menyaring kebisingan tren.
- **Renko & Point & Figure**: Grafik berbasis pergerakan harga murni tanpa sumbu waktu (volume dan indikator sumbu waktu dinonaktifkan secara otomatis).

---

## Alat Bantu Grafik & Indikator Teknikal

- **MA 20 & MA 50**: Rata-rata pergerakan 20 & 50 hari untuk melacak tren.
- **Bollinger Bands**: Mengukur tingkat kejenuhan harga (oversold/overbought) dari standar deviasi.
- **Garis Arah Harga**: Garis regresi linear untuk memetakan tren harga keseluruhan.
- **RSI (14)**: Indikator momentum kekuatan harga.
- **MACD (12,26,9)**: Momentum kekuatan arah harga dari selisih EMA.
- **Stochastic (14,3)**: Menunjukkan posisi harga penutupan relatif terhadap rentang harga tertinggi-terendah.
- **OBV**: Akumulasi volume beli-jual untuk melihat dukungan volume.
- **ATR**: Indikator volatilitas rentang gerak harga harian.

---

## Struktur File

```
app.py              -- Tampilan UI Streamlit, penanganan layout, dan logika tab halaman
data_loader.py      -- Pemuatan data yfinance, integrasi kurs USD/IDR, indeks bursa, dan cache manager
config_saham.json   -- Konfigurasi daftar emiten, pilihan periode, dan terjemahan sektor
charts.py           -- Modul visualisasi matplotlib (Candlestick, RSI, MACD, Heatmap korelasi, dll)
indicators.py       -- Perhitungan indikator teknikal (RSI, Stochastic, OBV, ATR) dan sinyal konsensus
features.py         -- Logika Stock Screener, Support & Resistance, Watchlist, dan Portfolio Tracker
requirements.txt    -- Dependency library python yang dibutuhkan
cache/              -- Folder cache lokal data CSV/JSON (dibuat otomatis, diabaikan oleh git)
data/               -- Folder penyimpanan data watchlist dan portofolio ( watchlist.json & portfolio.json )
README.md           -- Dokumentasi ini
```

---

## Cara Menjalankan

**1. Masuk ke folder project**
```bash
cd saham
```

**2. Instal dependency**
```bash
pip install -r requirements.txt
```

**3. Jalankan aplikasi**
```bash
streamlit run app.py
```

Aplikasi dapat diakses melalui browser pada alamat:
`http://localhost:8501`

---

## Ticker Manual

Untuk mencari saham yang tidak ada dalam menu drop-down *Blue-Chip*, gunakan **Input Ticker Manual**. Cukup masukkan kode saham 4 huruf tanpa perlu menulis `.JK`. Sistem akan mendeteksi dan menambahkannya secara otomatis.
- `BBCA` menjadi `BBCA.JK`
- `TLKM` menjadi `TLKM.JK`

Untuk membandingkan saham manual, pisahkan dengan tanda koma, contoh:
`BBCA, TLKM, BBNI, BMRI`

---

## Disclaimer

Aplikasi ini dibuat murni untuk tujuan edukasi dan sarana visualisasi data bursa. Seluruh keputusan investasi, transaksi beli, jual, atau simpan saham merupakan tanggung jawab pribadi masing-masing pengguna. Penulis tidak menjamin keakuratan atau keberlanjutan data yang diperoleh dari pihak ketiga.
