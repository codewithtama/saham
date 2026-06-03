import warnings
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")

# Mekanisme Auto-Reload Modul Dinamis (Menghindari ImportError Caching)
import importlib
import sys

if "data_loader" in sys.modules:
    importlib.reload(sys.modules["data_loader"])
if "indicators" in sys.modules:
    importlib.reload(sys.modules["indicators"])
if "charts" in sys.modules:
    importlib.reload(sys.modules["charts"])

from charts import (
    buat_atr_chart,
    buat_candlestick,
    buat_compare_chart,
    buat_macd_chart,
    buat_obv_chart,
    buat_rsi_chart,
    buat_stochastic_chart,
    buat_volatilitas_chart,
)
from data_loader import (
    SAHAM_IDX,
    TIMEFRAME_OPTIONS,
    ambil_data,
    ambil_data_marquee,
    ambil_fundamental,
)
from indicators import (
    hitung_konsensus_sinyal,
    hitung_rsi,
    jalankan_backtest,
    sinyal_teknikal,
)

# ========================================
# KONFIGURASI HALAMAN
# ========================================
st.set_page_config(
    page_title="Dashboard Analisis Saham BEI/IDX",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS untuk tampilan gelap dengan warna hijau/merah yang mudah dibaca
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap');

    /* ==========================================================
       CSS STOCK TICKER MARQUEE (RUNNING TEXT)
       ========================================================== */
    @keyframes scroll-left {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    /* Header bawaan streamlit dijadikan transparan agar marquee menempel sempurna */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }

    .ticker-wrap {
        position: -webkit-sticky; /* Safari */
        position: sticky;
        top: 0;
        z-index: 999;
        width: 100vw;
        margin-left: calc(-50vw + 50%);
        overflow: hidden;
        background-color: #060606;
        border-top: 1px solid #1c1c1c;
        border-bottom: 1px solid #1c1c1c;
        padding: 8px 0;
        box-sizing: border-box;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.9);
    }
    .ticker-moving {
        display: flex;
        width: max-content;
        animation: scroll-left 45s linear infinite;
    }
    .ticker-moving:hover {
        animation-play-state: paused;
    }
    .ticker-list {
        display: flex;
        align-items: center;
    }
    .ticker-item {
        font-size: 11px;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        font-weight: bold;
        white-space: nowrap;
        margin-right: 40px;
    }

    /* ==========================================================
       KEBIJAKAN NOL LUAPAN (ZERO OVERFLOWED POLICY)
       ========================================================== */
    html, body, .stApp {
        overflow-x: hidden !important;
        max-width: 100vw;
    }

    /* Mencegah luapan kata/teks panjang di kontainer teks saja */
    p, li, h1, h2, h3 {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* Kunci metrik agar nilainya TIDAK PERNAH terpotong ke bawah (nowrap) */
    div[data-testid="metric-container"] * {
        white-space: nowrap !important;
    }

    /* Mencegah metrik menyusut berlebihan atau meluap */
    div[data-testid="column"] {
        min-width: 0 !important;
        overflow: hidden !important;
    }

    /* ==========================================================
       TAMPILAN GELAP DAN WARNA UTAMA
       ========================================================== */
    /* Background hitam solid */
    .stApp { background-color: #000000; }

    /* Sidebar hitam pekat, border tipis abu-abu gelap */
    section[data-testid="stSidebar"] {
        background-color: #080808;
        border-right: 1px solid #222222;
    }

    /* Kotak angka utama */
    .stMetric {
        background-color: #0a0a0a;
        border: 1px solid #333333;
        border-radius: 0px !important;
        padding: 10px;
        min-width: 0 !important;
    }
    div[data-testid="metric-container"] {
        background-color: #0a0a0a;
        border: 1px solid #333333;
        border-radius: 0px !important;
        padding: 10px;
        min-width: 0 !important;
    }

    /* Kotak tanda beli/jual/tunggu */
    .signal-box {
        padding: 6px 12px;
        border-radius: 0px;
        font-size: 12px;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        font-weight: bold;
        display: inline-block;
        margin: 3px;
    }
    .buy  { background: #002200; color: #00ff00; border: 1px solid #00ff00; }
    .sell { background: #220000; color: #ff3333; border: 1px solid #ff3333; }
    .hold { background: #221100; color: #ffa500; border: 1px solid #ffa500; }

    /* Font dan warna teks judul */
    h1, h2, h3 {
        color: #ffa500 !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        font-weight: bold !important;
    }

    .stDataFrame {
        background-color: #0a0a0a;
        border-radius: 0px !important;
    }

    hr { border-color: #222222; }

    /* ==========================================================
       PROTEKSI FONT DAN IKON SISTEM
       ========================================================== */
    /* Targetkan font monospace hanya ke konten teks saja secara spesifik */
    .stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp button,
    .stApp table, .stApp label, .stMetric *, div[data-testid="metric-container"] * {
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }
    .stApp p, .stApp li {
        color: #c9d1d9 !important;
    }

    /* Proteksi mutlak agar ikon sistem tidak terpengaruh font monospace */
    [class*="icon"], [class*="arrow"], [class*="caret"], [class*="Collapse"] *,
    span[data-testid="stWidgetLabel"] svg, button svg, svg, i {
        font-family: inherit !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ========================================
# FUNGSI PEMBANTU RENDER (MODULAR)
# ========================================
def tampilkan_profil_perusahaan(fundamental, ticker):
    if not fundamental:
        st.warning(f"Data profil untuk {ticker} tidak tersedia.")
        return

    st.markdown(f"### Tentang Perusahaan: {fundamental['nama']} ({ticker})")

    # Format Market Cap
    mc_val = fundamental["market_cap"]
    if mc_val:
        if mc_val >= 1e12:
            mc_str = f"Rp {mc_val / 1e12:.2f} T"
        elif mc_val >= 1e9:
            mc_str = f"Rp {mc_val / 1e9:.2f} M"
        else:
            mc_str = f"Rp {mc_val:,.0f}"
    else:
        mc_str = "Tidak tersedia"

    # Format P/E Ratio
    pe_val = fundamental["pe_ratio"]
    pe_str = f"{pe_val:.2f}x" if pe_val else "Tidak tersedia"

    # Format Dividend Yield (Keamanan Skala Persentase)
    div_val = fundamental["dividend_yield"]
    if div_val:
        div_persen = div_val if div_val > 1.0 else div_val * 100
        div_str = f"{div_persen:.2f}%"
    else:
        div_str = "Tidak tersedia"

    beta_val = fundamental["beta"]
    h52_val = fundamental["high_52w"]
    l52_val = fundamental["low_52w"]

    # Ringkasan angka utama dalam kotak sederhana
    st.markdown("**Angka Penting**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Nilai Perusahaan di Bursa", mc_str)
    m2.metric("P/E (Harga vs Laba)", pe_str)
    m3.metric("Dividen per Tahun", div_str)

    m4, m5, m6 = st.columns(3)
    m4.metric(
        "Naik Turun vs Pasar", f"{beta_val:.2f}" if beta_val else "Tidak tersedia"
    )
    m5.metric(
        "Harga Tertinggi 1 Tahun", f"Rp {h52_val:,.0f}" if h52_val else "Tidak tersedia"
    )
    m6.metric(
        "Harga Terendah 1 Tahun", f"Rp {l52_val:,.0f}" if l52_val else "Tidak tersedia"
    )

    # Ringkasan Bisnis Ekspander
    with st.expander("Cerita Singkat Perusahaan"):
        st.write(fundamental["ringkasan"])


def tampilkan_metrik_dan_sinyal(df, ticker, timeframe):
    harga_kini = float(df["Close"].iloc[-1])
    harga_prev = float(df["Close"].iloc[-2]) if len(df) > 1 else harga_kini
    perubahan = harga_kini - harga_prev
    pct_perubahan = (perubahan / harga_prev) * 100
    rsi_val = float(hitung_rsi(df["Close"]).iloc[-1])
    vol_terakhir = int(df["Volume"].iloc[-1])
    vol_avg = int(df["Volume"].mean())
    return_total = ((harga_kini / float(df["Close"].iloc[0])) - 1) * 100

    st.markdown(f"### Kondisi Harga Saat Ini: {ticker}")

    # Row 1 -- Metrik Harga Utama
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    r1_c1.metric(
        "Harga Terakhir",
        f"Rp {harga_kini:,.0f}",
        f"{perubahan:+,.0f} ({pct_perubahan:+.2f}%)",
    )
    r1_c2.metric("Tertinggi Periode", f"Rp {float(df['High'].max()):,.0f}")
    r1_c3.metric("Terendah Periode", f"Rp {float(df['Low'].min()):,.0f}")

    # Row 2 -- Metrik Volume & Sinyal
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    r2_c1.metric("Volume", f"{vol_terakhir:,}", f"Rata-rata: {vol_avg:,}")
    r2_c2.metric("Perubahan Selama Periode Ini", f"{return_total:+.2f}%")
    r2_c3.metric(
        "RSI (14)",
        f"{rsi_val:.1f}",
        "Jenuh Beli" if rsi_val > 70 else ("Jenuh Jual" if rsi_val < 30 else "Netral"),
    )

    # Sinyal sederhana dari beberapa indikator
    st.markdown("**Tanda dari Grafik**")
    sinyal = sinyal_teknikal(df)

    # Hitung dan tampilkan ringkasan sederhana
    konsensus_aksi, konsensus_ket, konsensus_warna = hitung_konsensus_sinyal(sinyal)
    st.markdown(
        f"""
    <div style="background-color: #0a0a0a; border: 1px solid {konsensus_warna}; padding: 12px 15px; margin-bottom: 15px; font-family: 'JetBrains Mono', monospace;">
        <span style="color: #ffffff; font-weight: bold;">GAMBARAN CEPAT:</span>
        <span style="color: {konsensus_warna}; font-weight: bold; margin-left: 8px; font-size: 14px;">{konsensus_aksi}</span>
        <div style="font-size: 11px; color: #8b949e; margin-top: 4px;">{konsensus_ket}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    cols_signal = st.columns(len(sinyal))
    for col, (nama, (arah, keterangan)) in zip(cols_signal, sinyal.items()):
        css_class = arah.lower()
        col.markdown(
            f'<div class="signal-box {css_class}"> {nama}: {arah} </div>'
            f'<div style="font-size:11px; color:#8b949e; margin-top:4px;">{keterangan}</div>',
            unsafe_allow_html=True,
        )


def tampilkan_data_historis(df, ticker):
    with st.expander(f"Lihat Data Historis {ticker} (30 baris terakhir)"):
        df_show = df[["Open", "High", "Low", "Close", "Volume"]].copy().tail(30)
        # Tentukan format tanggal/waktu secara otomatis (jika ada jam, gunakan format intraday)
        fmt = "%Y-%m-%d %H:%M" if not (df_show.index.hour == 0).all() else "%Y-%m-%d"
        df_show.index = df_show.index.strftime(fmt)
        df_show.columns = [
            "Pembukaan (Rp)",
            "Tertinggi (Rp)",
            "Terendah (Rp)",
            "Penutupan (Rp)",
            "Volume",
        ]
        st.dataframe(
            df_show.style.format(
                {
                    "Pembukaan (Rp)": "Rp {:,.0f}",
                    "Tertinggi (Rp)": "Rp {:,.0f}",
                    "Terendah (Rp)": "Rp {:,.0f}",
                    "Penutupan (Rp)": "Rp {:,.0f}",
                    "Volume": "{:,}",
                }
            ),
            use_container_width=True,
        )

        # Tombol ekspor data ke CSV
        csv_data = df_show.to_csv(index=True).encode("utf-8")
        st.download_button(
            label=f"Ekspor Data Historis {ticker} ke CSV",
            data=csv_data,
            file_name=f"histori_{ticker}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key=f"dl_{ticker}",
        )


def tampilkan_backtest_simulator(df, ticker, modal_awal):
    st.markdown(f"### Coba Simulasi Cara Beli/Jual: {ticker}")
    backtest = jalankan_backtest(df, modal_awal)

    # Grid metrik 3 kolom
    c1, c2, c3 = st.columns(3)

    # Col 1: Return Strategi vs Benchmark
    ret_strat = backtest["total_return"]
    ret_bench = backtest["benchmark_return"]
    c1.metric(
        "Hasil Cara Ini vs Beli & Simpan",
        f"{ret_strat:+.2f}%",
        f"Beli & simpan: {ret_bench:+.2f}%",
    )

    # Col 2: Win Rate
    win_rate = backtest["win_rate"]
    total_trades = backtest["total_trades"]
    c2.metric(
        "Transaksi yang Untung", f"{win_rate:.1f}%", f"Total Transaksi: {total_trades}x"
    )

    # Col 3: Max Drawdown (Penurunan Nilai Portofolio Terbesar)
    max_dd = backtest["max_drawdown"]
    c3.metric("Penurunan Terbesar", f"{max_dd:.2f}%", "Risiko terbesar dari simulasi")

    # Rangkuman deskriptif dalam Bahasa Indonesia
    if total_trades > 0:
        outperforms = "mengungguli" if ret_strat > ret_bench else "tertinggal dari"
        selisih = abs(ret_strat - ret_bench)
        st.markdown(
            f"""
        <div style="background-color: #0a0a0a; border: 1px solid #333333; padding: 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-bottom: 15px;">
            Dengan modal awal <span style="color: #ffa500; font-weight: bold;">Rp {modal_awal:,.0f}</span>, simulasi ini menunjukkan bahwa cara
            <span style="color: #00ff00; font-weight: bold;">GAMBARAN CEPAT</span> {outperforms} cara beli lalu simpan saja, dengan beda hasil
            <span style="color: #00ffff; font-weight: bold;">{selisih:.2f}%</span>. Dari total
            <span style="color: #ffffff; font-weight: bold;">{total_trades}</span> transaksi,
            <span style="color: #00ff00; font-weight: bold;">{win_rate:.1f}%</span> berakhir untung. Penurunan nilai terbesar selama simulasi adalah
            <span style="color: #ff3333; font-weight: bold;">{max_dd:.2f}%</span>.
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Expander Rincian Log Transaksi
        with st.expander(f"Lihat Catatan Beli/Jual Simulasi {ticker}"):
            trade_logs = []
            for idx, t in enumerate(backtest["trades"]):
                fmt_beli = t["tanggal_beli"].strftime("%Y-%m-%d")
                fmt_jual = t["tanggal_jual"].strftime("%Y-%m-%d")
                trade_logs.append(
                    {
                        "No": idx + 1,
                        "Tgl Beli": fmt_beli,
                        "Tgl Jual": fmt_jual,
                        "Harga Beli (Rp)": t["harga_beli"],
                        "Harga Jual (Rp)": t["harga_jual"],
                        "Return (%)": t["return_pct"],
                        "Profit/Loss (Rp)": t["profit_rp"],
                        "Volume Lot": int(t["lembar"] // 100),
                    }
                )
            df_logs = pd.DataFrame(trade_logs).set_index("No")
            st.dataframe(
                df_logs.style.format(
                    {
                        "Harga Beli (Rp)": "Rp {:,.0f}",
                        "Harga Jual (Rp)": "Rp {:,.0f}",
                        "Return (%)": "{:+.2f}%",
                        "Profit/Loss (Rp)": "Rp {:+,.0f}",
                        "Volume Lot": "{:,} Lot",
                    }
                ),
                use_container_width=True,
            )
    else:
        st.markdown(
            f"""
        <div style="background-color: #0a0a0a; border: 1px solid #333333; padding: 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-bottom: 15px;">
            <span style="color: #ffa500; font-weight: bold;">INFO:</span> Selama periode ini belum ada momen beli/jual yang cukup kuat menurut aturan aplikasi. Biasanya ini terjadi saat harga bergerak datar atau tandanya masih campur aduk.
        </div>
        """,
            unsafe_allow_html=True,
        )


# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown("## ANALISA SAHAM BEI/IDX")
    st.divider()

    mode = st.radio(
        "Mau lihat apa?", ["Single Saham", "Bandingkan Saham (Maks 5)"], horizontal=True
    )
    st.divider()

    # -- List Saham Terpilih --
    tickers = []
    if mode == "Single Saham":
        st.markdown("**Pilih Saham Utama**")
        opsi_list = list(SAHAM_IDX.keys()) + ["Input Ticker Manual"]
        pilihan1 = st.selectbox("Pilih Saham", opsi_list, key="s1")
        if pilihan1 == "Input Ticker Manual":
            raw_input = (
                st.text_input("Ticker (contoh: BBCA)", value="BBCA").upper().strip()
            )
            ticker1 = raw_input if raw_input.endswith(".JK") else raw_input + ".JK"
        else:
            ticker1 = SAHAM_IDX[pilihan1]
        tickers = [ticker1]
    else:
        st.markdown("**Pilih Saham Pembanding (Maks 5)**")
        opsi_input = st.selectbox(
            "Metode Pemilihan",
            ["Pilih dari Daftar Blue-Chip", "Ketik Ticker Manual (Pisah Koma)"],
        )

        if opsi_input == "Pilih dari Daftar Blue-Chip":
            pilihan_saham = st.multiselect(
                "Pilih Saham",
                options=list(SAHAM_IDX.keys()),
                default=[list(SAHAM_IDX.keys())[0], list(SAHAM_IDX.keys())[4]],
                max_selections=5,
            )
            tickers = [SAHAM_IDX[p] for p in pilihan_saham]
        else:
            raw_input = st.text_input(
                "Ticker Manual (maks 5, pisah koma. Contoh: BBCA, TLKM, BBRI)",
                value="BBCA, TLKM",
            )
            manual_list = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
            tickers = [t if t.endswith(".JK") else t + ".JK" for t in manual_list][:5]

    st.divider()
    st.markdown("**Timeframe**")
    timeframe = st.selectbox("Periode", list(TIMEFRAME_OPTIONS.keys()), index=2)

    st.divider()
    st.markdown("**Tampilan Grafik**")
    opsi_grafik = {
        "Candlestick": "candle",
        "Garis (Close)": "line",
        "OHLC / Batang": "ohlc",
        "Heikin-Ashi (Tren Halus)": "heikin_ashi",
        "Renko (Bata Tren)": "renko",
        "Point & Figure (P&F)": "pnf",
    }
    pilihan_grafik = st.selectbox(
        "Tipe Grafik Utama", list(opsi_grafik.keys()), index=0
    )
    tipe_grafik = opsi_grafik[pilihan_grafik]

    st.divider()
    st.markdown("**Alat Bantu Grafik**")
    show_ma20 = st.checkbox(
        "MA 20",
        value=True,
        help="Garis rata-rata harga 20 hari. Berguna untuk melihat arah harga jangka pendek.",
    )
    show_ma50 = st.checkbox(
        "MA 50",
        value=True,
        help="Garis rata-rata harga 50 hari. Berguna untuk melihat arah harga yang lebih panjang.",
    )
    show_bb = st.checkbox(
        "Bollinger Bands",
        value=False,
        help="Pita batas atas dan bawah untuk melihat apakah harga sedang terlalu tinggi atau terlalu rendah dari kebiasaannya.",
    )
    show_regression = st.checkbox(
        "Garis Arah Harga",
        value=False,
        help="Garis bantu untuk melihat kecenderungan harga: naik, turun, atau datar.",
    )
    show_rsi = st.checkbox(
        "RSI (14)",
        value=True,
        help="Membantu melihat apakah saham mulai terlalu ramai dibeli atau terlalu banyak dijual.",
    )
    show_macd = st.checkbox(
        "MACD (12,26,9)",
        value=True,
        help="Membantu melihat perubahan kekuatan arah harga.",
    )
    show_vol = st.checkbox(
        "Naik-Turun Harian",
        value=False,
        help="Menampilkan seberapa besar harga biasa naik atau turun setiap hari.",
    )
    show_stoch = st.checkbox(
        "Stochastic",
        value=False,
        help="Alat bantu untuk melihat potensi harga mulai berbalik arah.",
    )
    show_obv = st.checkbox(
        "OBV (Volume)",
        value=False,
        help="Membantu melihat apakah volume perdagangan ikut mendukung pergerakan harga.",
    )
    show_atr = st.checkbox(
        "ATR (Lebar Gerak Harga)",
        value=False,
        help="Menunjukkan seberapa lebar gerak harga belakangan ini.",
    )

    st.divider()
    st.caption("Data: Yahoo Finance (yfinance)")
    st.caption("Disclaimer: Bukan rekomendasi investasi.")

# ========================================
# MAIN -- AMBIL DATA
# ========================================
st.title("ANALISA SAHAM BEI/IDX")

# Ambil data bursa marquee secara efisien (konkuren & cached)
# Dibungkus try/except tambahan sebagai lapisan perlindungan terakhir agar
# kegagalan atau timeout di sini tidak pernah menghentikan render halaman.
try:
    marquee_data = ambil_data_marquee()
except Exception:
    marquee_data = None

if marquee_data:
    ticker_html_items = []
    for item in marquee_data:
        arrow = "▲" if item["change"] > 0 else ("▼" if item["change"] < 0 else "■")
        color_hex = (
            "#00ff00"
            if item["change"] > 0
            else ("#ff3333" if item["change"] < 0 else "#8b949e")
        )

        ticker_html_items.append(
            f'<span class="ticker-item">'
            f'<span style="color:#ffffff;">{item["kode"]}</span> '
            f'<span style="color:#ffa500; margin-left: 4px;">{item["harga"]:,.0f}</span> '
            f'<span style="color:{color_hex}; margin-left: 4px;">{arrow} {item["change"]:+.2f}%</span>'
            f"</span>"
        )

    ticker_string = "".join(ticker_html_items)

    st.markdown(
        f"""
    <div class="ticker-wrap">
        <div class="ticker-moving">
            <div class="ticker-list">
                {ticker_string}
            </div>
            <div class="ticker-list">
                {ticker_string}
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# Tarik data harga historis & data fundamental secara dinamis untuk seluruh tickers
periode_kode = TIMEFRAME_OPTIONS[timeframe]
dfs = []
fundamentals = []
valid_tickers = []

for t in tickers:
    with st.spinner(f"Mengambil data {t}..."):
        df_t = ambil_data(t, periode_kode)
        fund_t = ambil_fundamental(t)
        if df_t is not None and not df_t.empty:
            dfs.append(df_t)
            fundamentals.append(fund_t)
            valid_tickers.append(t)

if not dfs:
    st.error(
        "Tidak ada data saham yang berhasil diunduh. Pastikan ticker valid dan berakhiran .JK"
    )
    st.stop()


# ========================================
# RENDER KALKULATOR RISIKO DI SIDEBAR (DENGAN DATA AKTIF)
# ========================================
with st.sidebar:
    st.divider()
    st.markdown("### HITUNG RISIKO & LOT")

    # Pilih saham untuk dikalkulasi jika dalam mode perbandingan
    if len(valid_tickers) > 1:
        calc_ticker = st.selectbox(
            "Pilih Saham Kalkulator", valid_tickers, key="sb_calc_ticker_sel"
        )
        idx_calc = valid_tickers.index(calc_ticker)
        df_calc = dfs[idx_calc]
    else:
        calc_ticker = valid_tickers[0]
        df_calc = dfs[0]

    harga_kini = float(df_calc["Close"].iloc[-1])

    # Input parameter kalkulator di sidebar
    modal = st.number_input(
        "Modal Maksimal (Rp)",
        min_value=100000.0,
        value=10000000.0,
        step=100000.0,
        format="%.0f",
        key="sb_calc_modal_val",
    )
    harga_masuk = st.number_input(
        "Harga Beli (Rp)",
        min_value=1.0,
        value=harga_kini,
        step=50.0,
        format="%.0f",
        key="sb_calc_masuk_val",
    )
    persen_risk = st.number_input(
        "Batas Risiko (%)",
        min_value=0.5,
        max_value=25.0,
        value=5.0,
        step=0.5,
        format="%.1f",
        key="sb_calc_risk_val",
    )

    # Kalkulasi Matematika Money Management
    rupiah_risk = modal * (persen_risk / 100)
    harga_stop_loss = harga_masuk * (1 - persen_risk / 100)
    selisih_harga = harga_masuk - harga_stop_loss

    if selisih_harga > 0:
        lembar_saham = rupiah_risk / selisih_harga
        max_lembar_modal = modal / harga_masuk
        lembar_saham = min(lembar_saham, max_lembar_modal)

        lot_saham = int(lembar_saham // 100)
        lembar_riil = lot_saham * 100
        dana_terpakai = lembar_riil * harga_masuk
    else:
        lot_saham = 0
        lembar_riil = 0
        dana_terpakai = 0

    # Tampilkan hasil hitung lot dan risiko di sidebar
    st.markdown(
        f"""
    <div style="background-color: #0a0a0a; border: 1px solid #333333; padding: 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px;">
        <div style="margin-bottom: 6px;"><span style="color:#ffa500; font-weight:bold;">Maks Beli:</span> <span style="color:#00ff00; font-weight:bold;">{lot_saham:,} Lot</span> ({lembar_riil:,} Lbr)</div>
        <div style="margin-bottom: 6px;"><span style="color:#ffa500; font-weight:bold;">Dana Pakai:</span> <span style="color:#ffffff;">Rp {dana_terpakai:,.0f}</span></div>
        <div style="margin-bottom: 6px;"><span style="color:#ffa500; font-weight:bold;">Stop Loss:</span> <span style="color:#ff3333; font-weight:bold;">Rp {harga_stop_loss:,.0f}</span></div>
        <div><span style="color:#ffa500; font-weight:bold;">Resiko Rp:</span> <span style="color:#ffffff;">Rp {rupiah_risk:,.0f} ({persen_risk:.1f}%)</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ========================================
# RENDERING HALAMAN UTAMA
# ========================================

if mode == "Bandingkan Saham (Maks 5)" and len(valid_tickers) > 1:
    # ----------------------------------------
    # MODE BANDINGKAN MULTI SAHAM (Sistem Simetris Dinamis)
    # ----------------------------------------
    st.subheader("Bandingkan Pergerakan Saham")

    # 1. Grafik perbandingan perubahan harga
    fig_cmp = buat_compare_chart(valid_tickers, dfs)
    st.pyplot(fig_cmp, use_container_width=True)
    plt.close(fig_cmp)

    # 2. Tabel ringkasan perbandingan
    st.subheader("Ringkasan Perbandingan")

    def ringkasan(d, ticker, f_data):
        ret = d["Close"].pct_change().dropna()

        mc_v = f_data.get("market_cap")
        if mc_v:
            mc_s = (
                f"Rp {mc_v / 1e12:.2f}T"
                if mc_v >= 1e12
                else (f"Rp {mc_v / 1e9:.2f}M" if mc_v >= 1e9 else f"Rp {mc_v:,.0f}")
            )
        else:
            mc_s = "Tidak tersedia"

        pe_v = f_data.get("pe_ratio")
        pe_s = f"{pe_v:.2f}x" if pe_v else "Tidak tersedia"

        rsi_val = float(hitung_rsi(d["Close"]).iloc[-1]) if len(d) > 0 else np.nan

        return {
            "Ticker": ticker,
            "Nama Perusahaan": f_data.get("nama", ticker.split(".")[0]),
            "Sektor": f_data.get("sektor", "N/A"),
            "Nilai Perusahaan di Bursa": mc_s,
            "P/E (Harga vs Laba)": pe_s,
            "Harga Terakhir (Rp)": f"{float(d['Close'].iloc[-1]):,.0f}",
            "Perubahan Periode Ini": f"{((float(d['Close'].iloc[-1]) / float(d['Close'].iloc[0])) - 1) * 100:+.2f}%",
            "Naik-Turun Harian": f"{float(ret.std()) * 100:.2f}%",
            "Naik-Turun Tahunan": f"{float(ret.std()) * np.sqrt(252) * 100:.2f}%",
            "Skor Risiko/Untung": f"{(float(ret.mean()) / float(ret.std())):.3f}"
            if float(ret.std()) > 0
            else "N/A",
            "RSI Terkini": f"{rsi_val:.1f}" if not pd.isna(rsi_val) else "N/A",
        }

    stats_rows = []
    for t, d, f in zip(valid_tickers, dfs, fundamentals):
        stats_rows.append(ringkasan(d, t, f))
    df_tbl = pd.DataFrame(stats_rows).set_index("Ticker").T
    st.dataframe(df_tbl, use_container_width=True)

    st.divider()

    # 3. Grafik utama per saham
    st.subheader("Grafik Harga Utama")
    tab_charts = st.tabs([f"Grafik {t}" for t in valid_tickers])
    for tab_c, t, d in zip(tab_charts, valid_tickers, dfs):
        with tab_c:
            fig_t = buat_candlestick(
                d, t, show_ma20, show_ma50, show_bb, tipe_grafik, show_regression
            )
            st.pyplot(fig_t, use_container_width=True)
            plt.close(fig_t)

    st.divider()

    # 4. Detail tiap saham
    st.subheader("Detail Masing-masing Saham")
    tab_details = st.tabs([f"Detail {t}" for t in valid_tickers])
    for tab_d, t, d, f in zip(tab_details, valid_tickers, dfs, fundamentals):
        with tab_d:
            # Profil & Statistik
            tampilkan_profil_perusahaan(f, t)
            st.divider()

            # Metrik & Sinyal
            tampilkan_metrik_dan_sinyal(d, t, timeframe)
            st.divider()

            # Simulator Backtesting
            tampilkan_backtest_simulator(d, t, modal)
            st.divider()

            # Alat bantu grafik yang dipilih
            if show_rsi:
                st.subheader("RSI -- Apakah Saham Mulai Terlalu Mahal/Murah?")
                fig_rsi = buat_rsi_chart(d)
                st.pyplot(fig_rsi, use_container_width=True)
                plt.close(fig_rsi)
                st.divider()

            if show_macd:
                st.subheader("MACD")
                fig_macd = buat_macd_chart(d)
                st.pyplot(fig_macd, use_container_width=True)
                plt.close(fig_macd)
                st.divider()

            if show_vol:
                st.subheader("Naik-Turun Harga Harian")
                fig_v = buat_volatilitas_chart(d, t)
                st.pyplot(fig_v, use_container_width=True)
                plt.close(fig_v)
                st.divider()

            if show_stoch:
                st.subheader("Stochastic -- Tanda Harga Mulai Berbalik")
                fig_stoch = buat_stochastic_chart(d)
                st.pyplot(fig_stoch, use_container_width=True)
                plt.close(fig_stoch)
                st.divider()

            if show_obv:
                st.subheader("OBV -- Dukungan dari Volume")
                fig_obv = buat_obv_chart(d)
                st.pyplot(fig_obv, use_container_width=True)
                plt.close(fig_obv)
                st.divider()

            if show_atr:
                st.subheader("ATR -- Lebar Gerak Harga")
                fig_atr = buat_atr_chart(d)
                st.pyplot(fig_atr, use_container_width=True)
                plt.close(fig_atr)
                st.divider()

            # Data Historis
            tampilkan_data_historis(d, t)

else:
    # ----------------------------------------
    # MODE SINGLE SAHAM
    # ----------------------------------------
    t_utama = valid_tickers[0]
    df_utama = dfs[0]
    fund_utama = fundamentals[0]

    tampilkan_profil_perusahaan(fund_utama, t_utama)
    st.divider()
    tampilkan_metrik_dan_sinyal(df_utama, t_utama, timeframe)
    st.divider()

    # Simulator Backtesting
    tampilkan_backtest_simulator(df_utama, t_utama, modal)
    st.divider()

    st.subheader("Grafik Utama")
    fig_candle = buat_candlestick(
        df_utama, t_utama, show_ma20, show_ma50, show_bb, tipe_grafik, show_regression
    )
    st.pyplot(fig_candle, use_container_width=True)
    plt.close(fig_candle)

    if show_rsi:
        st.subheader("RSI -- Apakah Saham Mulai Terlalu Mahal/Murah?")
        fig_rsi = buat_rsi_chart(df_utama)
        st.pyplot(fig_rsi, use_container_width=True)
        plt.close(fig_rsi)

    if show_macd:
        st.subheader("MACD")
        fig_macd = buat_macd_chart(df_utama)
        st.pyplot(fig_macd, use_container_width=True)
        plt.close(fig_macd)

    if show_vol:
        st.subheader("Naik-Turun Harga Harian")
        fig_v = buat_volatilitas_chart(df_utama, t_utama)
        st.pyplot(fig_v, use_container_width=True)
        plt.close(fig_v)

    if show_stoch:
        st.subheader("Stochastic -- Tanda Harga Mulai Berbalik")
        fig_stoch = buat_stochastic_chart(df_utama)
        st.pyplot(fig_stoch, use_container_width=True)
        plt.close(fig_stoch)

    if show_obv:
        st.subheader("OBV -- Dukungan dari Volume")
        fig_obv = buat_obv_chart(df_utama)
        st.pyplot(fig_obv, use_container_width=True)
        plt.close(fig_obv)

    if show_atr:
        st.subheader("ATR -- Lebar Gerak Harga")
        fig_atr = buat_atr_chart(df_utama)
        st.pyplot(fig_atr, use_container_width=True)
        plt.close(fig_atr)

    tampilkan_data_historis(df_utama, t_utama)

# ========================================
# FOOTER
# ========================================
st.divider()
st.caption(
    "Dibuat dengan Python -- Streamlit + Pandas + NumPy + Matplotlib + mplfinance + yfinance"
)
waktu_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
st.caption(
    f"Data diperbarui setiap 5 menit -- Terakhir diambil: {waktu_wib.strftime('%d %b %Y %H:%M WIB')}"
)
