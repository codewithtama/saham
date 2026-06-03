import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Hanya suppress warning yang sudah diketahui tidak relevan — bukan semua warning
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="yfinance")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

import importlib
import charts
import data_loader
import indicators

importlib.reload(charts)
importlib.reload(data_loader)
importlib.reload(indicators)

from charts import (
    buat_atr_chart,
    buat_candlestick,
    buat_compare_chart,
    buat_macd_chart,
    buat_obv_chart,
    buat_rsi_chart,
    buat_stochastic_chart,
    buat_volatilitas_chart,
    buat_financial_chart,
)
from data_loader import (
    SAHAM_IDX,
    TIMEFRAME_OPTIONS,
    ambil_data,
    ambil_data_marquee,
    ambil_fundamental,
    ambil_financial_history,
    ambil_dividend_history,
)
from indicators import (
    hitung_konsensus_sinyal,
    hitung_rsi,
    sinyal_teknikal,
)

# ========================================
# FUNGSI FETCH (didefinisikan lebih awal agar tidak re-define tiap sidebar rerun)
# ========================================
def _fetch_ticker(ticker: str, periode: str) -> tuple[str, object, dict]:
    """Fetch data harga + fundamental untuk satu ticker. Dijalankan di thread pool."""
    df_t = ambil_data(ticker, periode)
    fund_t = ambil_fundamental(ticker)
    return ticker, df_t, fund_t


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

    pbv_val = fundamental.get("pbv")
    pbv_str = f"{pbv_val:.2f}x" if pbv_val is not None else "Tidak tersedia"

    roe_val = fundamental.get("roe")
    roe_str = f"{roe_val * 100:.2f}%" if roe_val is not None else "Tidak tersedia"

    der_val = fundamental.get("der")
    der_str = f"{der_val:.2f}%" if der_val is not None else "Tidak tersedia"

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

    m7, m8, m9 = st.columns(3)
    m7.metric("P/B Ratio (PBV)", pbv_str)
    m8.metric("Return on Equity (ROE)", roe_str)
    m9.metric("Debt to Equity (DER)", der_str)

    # Ringkasan Bisnis Ekspander
    with st.expander("Cerita Singkat Perusahaan"):
        st.write(fundamental["ringkasan"])


def tampilkan_analisis_fundamental_tambahan(ticker, fundamental):
    if not fundamental:
        return
        
    st.markdown("### Kinerja Keuangan & Dividen")
    
    df_fin = ambil_financial_history(ticker)
    
    tab_fin, tab_div = st.tabs(["Laporan Keuangan Tahunan", "Histori Dividen"])
    
    with tab_fin:
        if df_fin is not None and not df_fin.empty:
            fig_fin = buat_financial_chart(df_fin, ticker)
            st.pyplot(fig_fin, use_container_width=True)
            plt.close(fig_fin)
            
            df_fin_show = df_fin.copy()
            df_fin_show.index = [str(date)[:4] for date in df_fin_show.index]
            df_fin_show.columns = ["Pendapatan (Revenue)", "Laba Bersih (Net Income)"]
            st.dataframe(
                df_fin_show.style.format("Rp {:,.0f}"),
                use_container_width=True
            )
        else:
            st.info("Data laporan keuangan tahunan tidak tersedia untuk emiten ini.")
            
    with tab_div:
        df_div = ambil_dividend_history(ticker)
        
        po_val = fundamental.get("payout_ratio")
        po_str = f"{po_val * 100:.2f}%" if po_val is not None else "Tidak tersedia"
        
        col_po, _ = st.columns([1, 2])
        col_po.metric("Dividend Payout Ratio (DPR)", po_str)
        
        if df_div is not None and not df_div.empty:
            df_div_show = df_div.head(10).copy()
            df_div_show.index = df_div_show.index.strftime("%Y-%m-%d")
            df_div_show.columns = ["Nilai Dividen (per Lembar)"]
            st.dataframe(
                df_div_show.style.format("Rp {:,.2f}"),
                use_container_width=True
            )
        else:
            st.info("Histori pembagian dividen tidak tersedia untuk emiten ini.")


def tampilkan_peer_group_analysis(ticker, fundamental):
    sektor = fundamental.get("sektor")
    if not sektor:
        return
        
    st.markdown(f"### Perbandingan Sektoral ({sektor})")
    
    peers = []
    for nama_saham, tick in SAHAM_IDX.items():
        if tick == ticker:
            continue
        fund = ambil_fundamental(tick)
        if fund and fund.get("sektor") == sektor:
            peers.append((tick, fund))
            if len(peers) >= 4:
                break
                
    all_peers = [(ticker, fundamental)] + peers
    
    rows = []
    for tick, f in all_peers:
        mc_val = f.get("market_cap")
        mc_str = f"Rp {mc_val / 1e12:.2f} T" if mc_val and mc_val >= 1e12 else (f"Rp {mc_val / 1e9:.2f} M" if mc_val and mc_val >= 1e9 else "N/A")
        
        pe_val = f.get("pe_ratio")
        pe_str = f"{pe_val:.2f}x" if pe_val else "N/A"
        
        pbv_val = f.get("pbv")
        pbv_str = f"{pbv_val:.2f}x" if pbv_val is not None else "N/A"
        
        roe_val = f.get("roe")
        roe_str = f"{roe_val * 100:.2f}%" if roe_val is not None else "N/A"
        
        der_val = f.get("der")
        der_str = f"{der_val:.2f}%" if der_val is not None else "N/A"
        
        div_val = f.get("dividend_yield")
        div_persen = div_val if div_val and div_val > 1.0 else (div_val * 100 if div_val else 0)
        div_str = f"{div_persen:.2f}%" if div_val else "N/A"
        
        display_ticker = tick.split(".JK")[0]
        if tick == ticker:
            display_ticker = f"{display_ticker} (Aktif)"
            
        rows.append({
            "Kode": display_ticker,
            "Perusahaan": f.get("nama", tick.split(".JK")[0]),
            "Market Cap": mc_str,
            "P/E Ratio": pe_str,
            "PBV Ratio": pbv_str,
            "ROE": roe_str,
            "DER": der_str,
            "Div Yield": div_str
        })
        
    df_peers = pd.DataFrame(rows)
    st.dataframe(df_peers.set_index("Kode"), use_container_width=True)


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
marquee_data = ambil_data_marquee()
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


# Tarik data harga historis & data fundamental secara paralel untuk seluruh tickers
periode_kode = TIMEFRAME_OPTIONS[timeframe]
dfs = []
fundamentals = []
valid_tickers = []


with st.spinner(f"Mengambil data {', '.join(tickers)}..."):
    fetch_results: dict[str, tuple] = {}
    with ThreadPoolExecutor(max_workers=min(5, len(tickers))) as executor:
        future_map = {
            executor.submit(_fetch_ticker, t, periode_kode): t for t in tickers
        }
        for future in as_completed(future_map):
            try:
                ticker_r, df_t, fund_t = future.result()
                fetch_results[ticker_r] = (df_t, fund_t)
            except Exception as exc:
                st.error(f"Gagal ambil data {future_map[future]}: {exc}")

# Susun ulang sesuai urutan asli pilihan user
for t in tickers:
    if t in fetch_results:
        df_t, fund_t = fetch_results[t]
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

            # Fundamental tambahan & Peer group
            tampilkan_analisis_fundamental_tambahan(t, f)
            st.divider()
            tampilkan_peer_group_analysis(t, f)
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
    tampilkan_analisis_fundamental_tambahan(t_utama, fund_utama)
    st.divider()
    tampilkan_peer_group_analysis(t_utama, fund_utama)
    st.divider()
    tampilkan_metrik_dan_sinyal(df_utama, t_utama, timeframe)
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
st.caption(
    "Sumber Data Keuangan, Dividen, dan Marquee: Yahoo Finance (yfinance) | Indikator Teknikal: Dihitung Mandiri (Pandas/NumPy)"
)
waktu_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
st.caption(
    f"Data diperbarui setiap 5 menit -- Terakhir diambil: {waktu_wib.strftime('%d %b %Y %H:%M WIB')}"
)
