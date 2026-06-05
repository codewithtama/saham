# Analisa Saham BEI/IDX

Dashboard analisis saham Indonesia berbasis Streamlit. Data harga, profil perusahaan, laporan keuangan, dan histori dividen diambil dari Yahoo Finance melalui `yfinance`.

Dibuat sebagai alat bantu belajar dan analisa awal -- bukan rekomendasi investasi.

---

## Fitur Utama

- Melihat harga dan grafik saham BEI/IDX secara real-time
- Profil perusahaan: sektor, ringkasan bisnis, market cap, P/E, PBV, ROE, DER, beta, dividen
- Laporan keuangan tahunan (revenue dan net income) dalam bentuk grafik dan tabel
- Histori pembagian dividen
- Perbandingan sektoral dengan emiten di sektor yang sama
- Sinyal teknikal dari RSI, MA Cross, MACD, dan Stochastic
- Ringkasan konsensus sinyal dalam bahasa sederhana
- Membandingkan sampai 5 saham sekaligus dengan grafik yang dinormalisasi ke 100%
- Simulasi beli/jual berdasarkan data historis dengan laporan win rate, drawdown, dan Sharpe Ratio
- Kalkulator risiko dan jumlah lot berdasarkan modal, harga beli, dan batas risiko
- Ekspor data historis ke CSV
- Running text harga saham di bagian atas halaman
- Mode offline: jika tidak ada internet, data ditampilkan dari cache lokal terakhir

---

## Mode Analisa

### Single Saham

Analisis lengkap untuk satu emiten. Pengguna bisa memilih dari daftar atau mengetik ticker manual.

Yang ditampilkan:
- Profil dan ringkasan bisnis perusahaan
- Angka fundamental: market cap, P/E, PBV, ROE, DER, beta, dividen, 52-week high/low
- Laporan keuangan tahunan dan histori dividen
- Perbandingan sektoral dengan emiten sejenis
- Harga terakhir, tertinggi/terendah periode, volume, RSI
- Sinyal teknikal dan gambaran konsensus
- Grafik harga utama dengan alat bantu grafik pilihan
- Simulasi beli/jual (backtest)
- Kalkulator risiko dan lot
- Data historis 30 baris terakhir dengan ekspor CSV

### Bandingkan Saham

Membandingkan 2 sampai 5 saham sekaligus. Pengguna bisa memilih dari daftar blue-chip atau mengetik ticker manual (pisah koma, maks 5).

Yang ditampilkan:
- Grafik perbandingan perubahan harga, dinormalisasi ke basis 100%
- Tabel ringkasan perbandingan antar saham
- Grafik harga masing-masing saham di tab terpisah
- Detail lengkap masing-masing saham

---

## Periode Data

| Pilihan        | Interval Data  |
|----------------|----------------|
| 1 Hari         | 5 menit        |
| 1 Minggu       | 15 menit       |
| 1 Bulan        | Harian         |
| 3 Bulan        | Harian         |
| 6 Bulan        | Harian         |
| 1 Tahun        | Harian         |
| 2 Tahun        | Harian         |
| 5 Tahun        | Harian         |

Untuk simulasi beli/jual (backtest), gunakan periode minimal 6 Bulan agar indikator punya cukup data untuk membentuk sinyal yang valid.

---

## Jenis Grafik

| Jenis                    | Keterangan                                                     |
|--------------------------|----------------------------------------------------------------|
| Candlestick              | Grafik standar OHLC berbentuk lilin                            |
| Garis (Close)            | Garis harga penutupan saja                                     |
| OHLC / Batang            | Grafik batang standar bursa                                    |
| Heikin-Ashi              | Versi halus dari candlestick, lebih mudah baca tren            |
| Renko                    | Grafik berbasis pergerakan harga, bukan waktu                  |
| Point & Figure           | Hanya menampilkan pergerakan harga signifikan                  |

Grafik Renko dan Point & Figure tidak menampilkan volume dan beberapa garis bantu karena tidak berbasis sumbu waktu.

---

## Alat Bantu Grafik

| Alat               | Fungsi                                                                 |
|--------------------|------------------------------------------------------------------------|
| MA 20              | Rata-rata harga 20 hari -- arah jangka pendek                          |
| MA 50              | Rata-rata harga 50 hari -- arah jangka panjang                         |
| Bollinger Bands    | Pita batas atas/bawah -- harga terlalu tinggi atau terlalu rendah      |
| Garis Arah Harga   | Regresi linear -- kecenderungan harga naik, turun, atau datar          |
| RSI (14)           | Momentum 0-100 -- overbought di atas 70, oversold di bawah 30         |
| MACD (12,26,9)     | Kekuatan perubahan arah harga                                          |
| Naik-Turun Harian  | Volatilitas harga harian dalam persentase                              |
| Stochastic         | Potensi pembalikan arah di zona ekstrem                                |
| OBV                | Apakah volume mendukung pergerakan harga                               |
| ATR                | Lebar gerak harga rata-rata dalam periode tertentu                     |

---

## Sinyal Teknikal dan Gambaran Cepat

Sinyal teknikal dihitung dari RSI, MA Cross, MACD, dan Stochastic. Hasilnya digabungkan menjadi satu gambaran konsensus:

| Konsensus                  | Kondisi                                          |
|----------------------------|--------------------------------------------------|
| PELUANG BELI KUAT          | 75% atau lebih sinyal mengarah ke beli           |
| CENDERUNG BISA BELI        | 50% atau lebih sinyal mengarah ke beli           |
| TUNGGU DULU                | Sinyal campur aduk, mayoritas netral             |
| CENDERUNG HATI-HATI        | 50% atau lebih sinyal mengarah ke jual           |
| WASPADA, TEKANAN JUAL KUAT | 75% atau lebih sinyal mengarah ke jual           |
| DATA BELUM CUKUP           | Data harga belum cukup panjang untuk dihitung    |

Gambaran ini hanya alat bantu membaca grafik -- bukan jaminan arah harga.

---

## Simulasi Beli/Jual (Backtest)

Fitur ini mensimulasikan aturan beli/jual aplikasi pada data historis. Modal awal mengikuti nilai yang diisi di kalkulator risiko.

Cara kerja:
1. Aplikasi membaca data dari awal periode hingga akhir
2. Setiap hari, minimal 4 indikator dicek: RSI, MA position, MACD crossover, Stochastic
3. Jika minimal 2 tanda mengarah beli dan tidak ada tanda jual, posisi dibuka
4. Jika minimal 2 tanda mengarah jual dan tidak ada tanda beli, posisi ditutup
5. Stop-loss otomatis aktif jika harga turun 7% dari harga beli

Yang ditampilkan:
- Total return simulasi vs benchmark beli-tahan
- Jumlah transaksi dan win rate
- Penurunan terbesar selama simulasi (max drawdown)
- Sharpe Ratio (target > 1.0)
- Log transaksi beli dan jual

Biaya broker disertakan: 0.15% saat beli, 0.25% saat jual (standar BEI).

Simulasi masa lalu tidak menjamin hasil masa depan. Fitur ini untuk belajar dan memahami risiko, bukan untuk digunakan sebagai sinyal trading langsung.

---

## Kalkulator Risiko dan Lot

Input:
- Modal maksimal (Rp)
- Harga beli per lembar (Rp)
- Batas risiko (%)

Output otomatis:
- Jumlah lot maksimal yang bisa dibeli
- Total dana yang digunakan
- Harga stop-loss
- Risiko dalam Rupiah

Hasil berubah otomatis setiap kali input diubah, tanpa tombol kirim. Di mode Bandingkan Saham, pengguna bisa memilih saham mana yang dipakai untuk kalkulator ini.

---

## Mode Offline

Jika tidak ada koneksi internet, aplikasi tidak crash. Sebaliknya, data ditampilkan dari cache lokal terakhir dengan banner pemberitahuan di bagian atas.

Cache disimpan di folder `cache/` dalam format CSV dan JSON, dan diperbarui otomatis setiap kali aplikasi berhasil mengunduh data. File cache tidak masuk ke repository git.

Jenis data yang di-cache:
- Data harga historis per ticker dan periode (cache 5 menit)
- Data fundamental per ticker (cache 1 jam)
- Laporan keuangan tahunan (cache 1 jam)
- Histori dividen (cache 1 jam)
- Data marquee running text (cache 5 menit)

---

## Struktur File

```
app.py              -- Tampilan utama Streamlit, sidebar, dan alur rendering
data_loader.py      -- Pengambilan data dari yfinance dan manajemen cache lokal
config_saham.json   -- Daftar saham, pilihan periode, terjemahan sektor, ringkasan perusahaan
charts.py           -- Pembuatan grafik: candlestick, RSI, MACD, OBV, ATR, financial, dll
indicators.py       -- Perhitungan indikator teknikal, sinyal konsensus, dan backtest engine
requirements.txt    -- Daftar dependency Python
cache/              -- Folder cache lokal (otomatis dibuat, tidak masuk git)
README.md           -- Dokumentasi ini
```

---

## Cara Menjalankan

**1. Masuk ke folder project**

```bash
cd saham
```

**2. Install dependency**

```bash
pip install -r requirements.txt
```

**3. Jalankan aplikasi**

```bash
streamlit run app.py
```

Buka browser dan akses:

```
http://localhost:8501
```

---

## Sumber Data

Semua data bersumber dari Yahoo Finance melalui library `yfinance`. Tidak ada API key yang diperlukan.

Cadence pembaruan:
- Data harga dan marquee: setiap 5 menit
- Data fundamental, laporan keuangan, dan dividen: setiap 1 jam

Jika data tidak muncul, kemungkinan penyebabnya:
- Koneksi internet bermasalah (cek mode offline di atas)
- Kode ticker salah atau tidak tersedia di Yahoo Finance
- Yahoo Finance sedang lambat atau down
- Data saham tidak lengkap di Yahoo Finance

---

## Ticker Manual

Format ticker untuk saham BEI cukup dengan kode saham tanpa akhiran `.JK`. Sistem akan menambahkan `.JK` secara otomatis.

Contoh:
```
BBCA  -->  BBCA.JK
TLKM  -->  TLKM.JK
GOTO  -->  GOTO.JK
```

Untuk mode Bandingkan Saham dengan input manual, pisah ticker dengan koma:
```
BBCA, TLKM, BBRI, ASII
```

---

## Disclaimer

Aplikasi ini dibuat untuk keperluan belajar dan membantu membaca data saham. Seluruh keputusan beli, jual, atau tahan saham tetap menjadi tanggung jawab masing-masing pengguna. Tidak ada yang dijamin dari informasi yang ditampilkan aplikasi ini.
