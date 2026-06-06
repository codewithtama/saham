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
import features
import indicators

importlib.reload(charts)
importlib.reload(data_loader)
importlib.reload(features)
importlib.reload(indicators)

from charts import (
    buat_atr_chart,
    buat_candlestick,
    buat_compare_chart,
    buat_korelasi_chart,
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
    ambil_indeks_pasar,
    ambil_kurs_usd_idr,
)
from features import (
    baca_portfolio,
    baca_watchlist,
    hapus_dari_watchlist,
    hitung_portfolio_summary,
    hitung_support_resistance,
    jalankan_screener,
    simpan_portfolio,
    tambah_ke_watchlist,
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


@st.cache_data(ttl=3600)
def _ambil_sektor_list() -> list[str]:
    """Bangun daftar sektor unik dari semua ticker SAHAM_IDX. Di-cache 1 jam."""
    from features import ambil_semua_fundamental_raw
    df = ambil_semua_fundamental_raw()
    if not df.empty and "Sektor" in df.columns:
        sektors = df["Sektor"].dropna().unique()
        return ["Semua"] + sorted([s for s in sektors if s and s != "N/A"])
    return ["Semua"]



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
        border-top: 1px solid #2a2a2a;
        border-bottom: 1px solid #2a2a2a;
        padding: 11px 0;
        box-sizing: border-box;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.95);
    }
    .ticker-moving {
        display: flex;
        width: max-content;
        animation: scroll-left 55s linear infinite;
    }
    .ticker-moving:hover {
        animation-play-state: paused;
    }
    .ticker-list {
        display: flex;
        align-items: center;
    }
    .ticker-item {
        font-size: 12px;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        font-weight: bold;
        white-space: nowrap;
        display: inline-block;
        vertical-align: middle;
    }
    .ticker-divider {
        width: 1px;
        height: 14px;
        background: #333;
        margin: 0 26px;
        display: inline-block;
        vertical-align: middle;
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
    /* Mengatasi luapan font pada metric (Zero Overflowed Policy) */
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #8b949e !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
        font-family: 'JetBrains Mono', monospace !important;
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

    /* Style link berita */
    .news-card-link {
        color: #ffa500 !important;
        text-decoration: none !important;
        transition: color 0.15s ease-in-out;
    }
    .news-card-link:hover {
        color: #ffb732 !important;
        text-decoration: underline !important;
    }


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
    m1.metric(
        "Nilai Perusahaan di Bursa",
        mc_str,
        help="Market Capitalization — total nilai seluruh saham perusahaan dikalikan harga saat ini. Semakin besar, semakin besar ukuran perusahaannya.",
    )
    m2.metric(
        "P/E (Harga vs Laba)",
        pe_str,
        help="Price-to-Earnings Ratio — berapa kali lipat harga saham dibanding laba per lembarnya. Angka tinggi bisa berarti saham mahal atau pasar optimis terhadap pertumbuhan.",
    )
    m3.metric(
        "Dividen per Tahun",
        div_str,
        help="Dividend Yield — persentase dividen tahunan dibanding harga saham. Makin tinggi, makin besar uang tunai yang diterima investor tiap tahun.",
    )

    m4, m5, m6 = st.columns(3)
    m4.metric(
        "Naik Turun vs Pasar",
        f"{beta_val:.2f}" if beta_val else "Tidak tersedia",
        help="Beta — ukuran seberapa liar saham ini bergerak dibanding pasar (IHSG). Beta > 1 = bergerak lebih ekstrem dari pasar. Beta < 1 = lebih stabil.",
    )
    m5.metric(
        "Harga Tertinggi 1 Tahun",
        f"Rp {h52_val:,.0f}" if h52_val else "Tidak tersedia",
        help="52-Week High — harga tertinggi yang pernah dicapai saham ini dalam 12 bulan terakhir.",
    )
    m6.metric(
        "Harga Terendah 1 Tahun",
        f"Rp {l52_val:,.0f}" if l52_val else "Tidak tersedia",
        help="52-Week Low — harga terendah yang pernah dicapai saham ini dalam 12 bulan terakhir.",
    )

    m7, m8, m9 = st.columns(3)
    m7.metric(
        "P/B Ratio (PBV)",
        pbv_str,
        help="Price-to-Book Value — perbandingan harga saham vs nilai buku aset bersih perusahaan. PBV < 1 bisa berarti saham diperdagangkan di bawah nilai asetnya.",
    )
    m8.metric(
        "Return on Equity (ROE)",
        roe_str,
        help="Seberapa efisien perusahaan menghasilkan laba dari modal yang dimiliki pemegang saham. Makin tinggi makin baik — ROE > 15% umumnya dianggap bagus.",
    )
    m9.metric(
        "Debt to Equity (DER)",
        der_str,
        help="Rasio utang terhadap modal sendiri. Makin tinggi, makin besar utang perusahaan dibanding modalnya. DER < 100% umumnya dianggap aman.",
    )

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
        
        # Format ex-dividend dan payment date
        def format_epoch(epoch_val):
            if not epoch_val:
                return "-"
            if isinstance(epoch_val, (datetime, pd.Timestamp)):
                return epoch_val.strftime("%d %b %Y")
            try:
                val = float(epoch_val)
                if val > 2e11: 
                    val = val / 1000
                return datetime.fromtimestamp(val, tz=ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y")
            except Exception:
                return str(epoch_val)
        
        ex_date_formatted = format_epoch(fundamental.get("ex_dividend_date"))
        pay_date_formatted = format_epoch(fundamental.get("dividend_date"))
        
        col_po, col_dates = st.columns([1, 2])
        col_po.metric(
            "Dividend Payout Ratio (DPR)",
            po_str,
            help="Persentase laba bersih yang dibagikan sebagai dividen. DPR tinggi berarti perusahaan bagi-bagi lebih banyak ke pemegang saham, tapi menyisakan lebih sedikit untuk reinvestasi.",
        )
        
        with col_dates:
            st.markdown(
                f"""
                <div style="background-color: #0d0d0d; border: 1px solid #333333; padding: 10px; border-radius: 0px; font-family: 'JetBrains Mono', monospace; font-size: 11px;">
                    <div style="color: #ffa500; font-weight: bold; margin-bottom: 5px;">📅 JADWAL DIVIDEN TERKINI</div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                        <span style="color: #8b949e;">Ex-Dividend Date:</span>
                        <span style="color: #ffffff; font-weight: bold;">{ex_date_formatted}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #8b949e;">Payment Date:</span>
                        <span style="color: #ffffff; font-weight: bold;">{pay_date_formatted}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.write("") # Spacer
        
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
        help="Harga penutupan terakhir beserta perubahan dari sesi sebelumnya.",
    )
    r1_c2.metric(
        "Tertinggi Periode",
        f"Rp {float(df['High'].max()):,.0f}",
        help="Harga tertinggi yang dicapai saham ini selama periode yang dipilih (timeframe).",
    )
    r1_c3.metric(
        "Terendah Periode",
        f"Rp {float(df['Low'].min()):,.0f}",
        help="Harga terendah yang dicapai saham ini selama periode yang dipilih (timeframe).",
    )

    # Row 2 -- Metrik Volume & Sinyal
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    r2_c1.metric(
        "Volume",
        f"{vol_terakhir:,}",
        f"Rata-rata: {vol_avg:,}",
        help="Jumlah lembar saham yang diperdagangkan pada sesi terakhir dibanding rata-rata periode ini. Volume tinggi mengkonfirmasi kekuatan pergerakan harga.",
    )
    r2_c2.metric(
        "Perubahan Selama Periode Ini",
        f"{return_total:+.2f}%",
        help="Total persentase kenaikan atau penurunan harga dari awal hingga akhir periode yang dipilih.",
    )
    r2_c3.metric(
        "RSI (14)",
        f"{rsi_val:.1f}",
        "Jenuh Beli" if rsi_val > 70 else ("Jenuh Jual" if rsi_val < 30 else "Netral"),
        help="Relative Strength Index — indikator momentum 0–100. Di atas 70 berarti saham mulai jenuh beli (overbought), di bawah 30 berarti jenuh jual (oversold). Zona aman: 30–70.",
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
        "Mau lihat apa?",
        ["Single Saham", "Bandingkan Saham (Maks 5)"],
        horizontal=True,
        help="Pilih 'Single Saham' untuk analisis lengkap satu emiten, atau 'Bandingkan' untuk melihat performa beberapa saham secara berdampingan.",
    )
    st.divider()

    # -- List Saham Terpilih --
    tickers = []
    if mode == "Single Saham":
        st.markdown("**Pilih Saham Utama**")
        opsi_list = list(SAHAM_IDX.keys()) + ["Input Ticker Manual"]
        pilihan1 = st.selectbox(
            "Pilih Saham",
            opsi_list,
            key="s1",
            help="Pilih salah satu emiten BEI dari daftar, atau pilih 'Input Ticker Manual' untuk memasukkan kode saham sendiri (format: KODE tanpa .JK).",
        )
        if pilihan1 == "Input Ticker Manual":
            raw_input = (
                st.text_input(
                    "Ticker (contoh: BBCA)",
                    value="BBCA",
                    help="Masukkan kode saham BEI tanpa akhiran .JK — contoh: BBCA, TLKM, GOTO. Sistem akan otomatis menambahkan .JK.",
                ).upper().strip()
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
            help="Pilih cara memilih saham pembanding: dari daftar blue-chip yang sudah tersedia, atau ketik sendiri kode saham yang ingin dibandingkan.",
        )

        if opsi_input == "Pilih dari Daftar Blue-Chip":
            pilihan_saham = st.multiselect(
                "Pilih Saham",
                options=list(SAHAM_IDX.keys()),
                default=[list(SAHAM_IDX.keys())[0], list(SAHAM_IDX.keys())[4]],
                max_selections=5,
                help="Pilih 2–5 saham untuk dibandingkan. Grafik akan menampilkan pergerakan harga semua saham dalam satu tampilan yang dinormalisasi ke 100%.",
            )
            tickers = [SAHAM_IDX[p] for p in pilihan_saham]
        else:
            raw_input = st.text_input(
                "Ticker Manual (maks 5, pisah koma. Contoh: BBCA, TLKM, BBRI)",
                value="BBCA, TLKM",
                help="Ketik kode saham BEI yang ingin dibandingkan, pisah dengan koma. Maksimal 5 saham. Contoh: BBCA, TLKM, BBRI, ASII, GOTO",
            )
            manual_list = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
            tickers = [t if t.endswith(".JK") else t + ".JK" for t in manual_list][:5]

    st.divider()
    st.markdown("**Timeframe**")
    timeframe = st.selectbox(
        "Periode",
        list(TIMEFRAME_OPTIONS.keys()),
        index=2,
        help="Rentang waktu data historis yang ditampilkan. '1 Hari' dan '5 Hari' menampilkan data per jam/menit (intraday). '1 Bulan' ke atas menggunakan data harian.",
    )

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
        "Tipe Grafik Utama",
        list(opsi_grafik.keys()),
        index=0,
        help="Candlestick: batang lilin standar (Open/High/Low/Close). Heikin-Ashi: versi halus untuk melihat tren. Renko: grafik berbasis pergerakan harga bukan waktu. P&F: hanya menampilkan perubahan harga signifikan.",
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
    show_sr = st.checkbox(
        "Support & Resistance",
        value=False,
        help="Garis support (harga bawah kuat) dan resistance (harga atas kuat) yang dihitung otomatis dari swing high/low data historis.",
    )

    st.divider()
    st.caption("Data: Yahoo Finance (yfinance)")

# ========================================
# MAIN -- AMBIL DATA
# ========================================
st.title("ANALISA SAHAM BEI/IDX")

# Ambil data bursa marquee, kurs USD/IDR, dan indeks pasar secara paralel
marquee_data = ambil_data_marquee()
kurs_data = ambil_kurs_usd_idr()
indeks_data = ambil_indeks_pasar()

if marquee_data:
    ticker_html_items = []

    # -- Chip kurs USD/IDR di posisi pertama --
    if kurs_data:
        kurs_val = kurs_data["kurs"]
        kurs_chg = kurs_data["change_pct"]
        kurs_arrow = "+" if kurs_chg > 0 else ("-" if kurs_chg < 0 else "~")
        # Rupiah melemah = dolar naik = merah untuk investor saham
        kurs_color = "#ff3333" if kurs_chg > 0 else ("#00ff00" if kurs_chg < 0 else "#8b949e")
        ticker_html_items.append(
            f'<span class="ticker-item">'
            f'<span style="color:#ffffff;">USD/IDR</span> '
            f'<span style="color:#ffa500; margin-left:4px;">{kurs_val:,.0f}</span> '
            f'<span style="color:{kurs_color}; margin-left:4px;">{kurs_arrow} {abs(kurs_chg):.2f}%</span>'
            f'</span>'
            f'<span class="ticker-divider"></span>'
        )

    # -- Chip IHSG dan LQ45 --
    for idx_item in indeks_data:
        idx_chg = idx_item["change_pct"]
        idx_arrow = "+" if idx_chg > 0 else ("-" if idx_chg < 0 else "~")
        idx_color = "#00ff00" if idx_chg > 0 else ("#ff3333" if idx_chg < 0 else "#8b949e")
        ticker_html_items.append(
            f'<span class="ticker-item">'
            f'<span style="color:#ffffff;">{idx_item["kode"]}</span> '
            f'<span style="color:#ffa500; margin-left:4px;">{idx_item["harga"]:,.0f}</span> '
            f'<span style="color:{idx_color}; margin-left:4px;">{idx_arrow} {abs(idx_chg):.2f}%</span>'
            f'</span>'
            f'<span class="ticker-divider"></span>'
        )

    for item in marquee_data:
        arrow = "+" if item["change"] > 0 else ("-" if item["change"] < 0 else "~")
        color_hex = (
            "#00ff00"
            if item["change"] > 0
            else ("#ff3333" if item["change"] < 0 else "#8b949e")
        )

        ticker_html_items.append(
            f'<span class="ticker-item">'
            f'<span style="color:#ffffff;">{item["kode"]}</span> '
            f'<span style="color:#ffa500; margin-left:4px;">{item["harga"]:,.0f}</span> '
            f'<span style="color:{color_hex}; margin-left:4px;">{arrow} {abs(item["change"]):.2f}%</span>'
            f'</span>'
            f'<span class="ticker-divider"></span>'
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
# BANNER MODE OFFLINE
# ========================================
if st.session_state.get("offline_mode"):
    sources = st.session_state.get("offline_sources", [])
    cache_times = st.session_state.get("offline_cache_times", {})

    # Ambil timestamp cache terlama untuk ditampilkan
    oldest_ts = None
    for ts in cache_times.values():
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                if oldest_ts is None or dt < oldest_ts:
                    oldest_ts = dt
            except Exception:
                pass

    ts_str = oldest_ts.strftime("%d %b %Y %H:%M") if oldest_ts else "waktu tidak diketahui"

    sumber_str = ", ".join(sources) if sources else "beberapa sumber"
    st.markdown(
        f"""
    <div style="
        background-color: #1a1200;
        border: 1px solid #ffa500;
        border-left: 4px solid #ffa500;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    ">
        <span style="color: #ffa500; font-weight: bold; font-size: 13px;">[OFFLINE]</span>
        <span style="color: #c9d1d9; margin-left: 10px;">Tidak ada koneksi internet — menampilkan data cache terakhir.</span>
        <div style="color: #8b949e; margin-top: 5px;">
            Cache dari: <span style="color: #ffa500;">{ts_str} WIB</span>
            &nbsp;|&nbsp; Sumber: {sumber_str}
        </div>
        <div style="color: #8b949e; margin-top: 3px; font-size: 11px;">
            Hubungkan internet lalu refresh browser untuk mendapatkan data terbaru.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ========================================
# NAVIGASI TAB UTAMA
# ========================================
tab_analisa, tab_screener, tab_watchlist, tab_portfolio = st.tabs(
    ["Analisa Saham", "Stock Screener", "Watchlist", "Portfolio"]
)

with tab_analisa:
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

        # 2b. Korelasi antar saham
        st.subheader("Korelasi Return Harian")
        fig_corr = buat_korelasi_chart(valid_tickers, dfs)
        st.pyplot(fig_corr, use_container_width=True)
        plt.close(fig_corr)
        st.caption("Dihitung dari return harian (pct_change) dalam periode yang dipilih. Diagonal selalu 1.00 (korelasi saham dengan dirinya sendiri).")

        st.divider()

        # 3. Grafik utama per saham
        st.subheader("Grafik Harga Utama")
        tab_charts = st.tabs([f"Grafik {t}" for t in valid_tickers])
        for tab_c, t, d in zip(tab_charts, valid_tickers, dfs):
            with tab_c:
                sr = hitung_support_resistance(d) if show_sr else None
                fig_t = buat_candlestick(
                    d, t, show_ma20, show_ma50, show_bb, tipe_grafik, show_regression, sr
                )
                st.pyplot(fig_t, use_container_width=True)
                plt.close(fig_t)

        st.divider()

        # 4. Detail tiap saham
        st.subheader("Detail Masing-masing Saham")
        tab_details = st.tabs([f"Detail {t}" for t in valid_tickers])
        for tab_d, t, d, f in zip(tab_details, valid_tickers, dfs, fundamentals):
            with tab_d:
                tampilkan_profil_perusahaan(f, t)
                st.divider()
                tampilkan_metrik_dan_sinyal(d, t, timeframe)
                st.divider()
                tampilkan_analisis_fundamental_tambahan(t, f)
                st.divider()


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

        tampilkan_metrik_dan_sinyal(df_utama, t_utama, timeframe)
        st.divider()

        # Tombol Watchlist
        wl_kini = baca_watchlist()
        if t_utama in wl_kini:
            if st.button(f"Hapus {t_utama.replace('.JK','')} dari Watchlist", key="btn_wl_hapus"):
                hapus_dari_watchlist(t_utama)
                st.success(f"{t_utama.replace('.JK','')} dihapus dari Watchlist.")
                st.rerun()
        else:
            if st.button(f"Tambah {t_utama.replace('.JK','')} ke Watchlist", key="btn_wl_tambah"):
                tambah_ke_watchlist(t_utama)
                st.success(f"{t_utama.replace('.JK','')} ditambahkan ke Watchlist.")
                st.rerun()

        st.divider()
        st.subheader("Grafik Utama")
        sr_utama = hitung_support_resistance(df_utama) if show_sr else None
        fig_candle = buat_candlestick(
            df_utama, t_utama, show_ma20, show_ma50, show_bb, tipe_grafik, show_regression, sr_utama
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
# TAB STOCK SCREENER
# ========================================
with tab_screener:
    st.subheader("Stock Screener")
    st.caption("Filter saham dari daftar SAHAM_IDX berdasarkan kriteria fundamental.")

    # Bangun daftar sektor dari cache (tidak re-fetch setiap render)
    opsi_sektor = _ambil_sektor_list()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sektor_filter = st.selectbox("Sektor", opsi_sektor, key="scr_sektor")
        pe_max = st.number_input(
            "P/E Maks (0 = abaikan)", min_value=0.0, value=0.0, step=5.0, key="scr_pe",
            help="Contoh: 20 untuk menyaring saham dengan P/E di bawah 20x. Isi 0 untuk menonaktifkan."
        )
    with col_f2:
        roe_min = st.number_input(
            "ROE Min (%)", min_value=0.0, value=0.0, step=1.0, key="scr_roe",
            help="Contoh: 15 untuk hanya menampilkan saham dengan ROE minimal 15%."
        )
        der_max = st.number_input(
            "DER Maks (%)", min_value=0.0, value=999.0, step=10.0, key="scr_der",
            help="Contoh: 100 untuk menyaring saham dengan rasio utang tidak lebih dari 100% modal."
        )
    with col_f3:
        div_min = st.number_input(
            "Div Yield Min (%)", min_value=0.0, value=0.0, step=0.5, key="scr_div",
            help="Contoh: 2.0 untuk hanya menampilkan saham dengan dividend yield minimal 2%."
        )
        mc_min_t = st.number_input(
            "Market Cap Min (Triliun Rp)", min_value=0.0, value=0.0, step=5.0, key="scr_mc",
            help="Contoh: 10 untuk hanya menampilkan saham dengan nilai perusahaan minimal Rp 10 Triliun."
        )

    if st.button("Cari Saham", key="btn_screener", type="primary"):
        with st.spinner("Mengambil data fundamental semua saham..."):
            df_hasil = jalankan_screener(
                sektor_filter=sektor_filter,
                pe_max=pe_max,
                roe_min=roe_min,
                der_max=der_max,
                div_min=div_min,
                mc_min_t=mc_min_t,
            )

        if df_hasil.empty:
            st.warning("Tidak ada saham yang memenuhi kriteria filter tersebut.")
        else:
            st.success(f"{len(df_hasil)} saham ditemukan.")
            st.dataframe(df_hasil, use_container_width=True, hide_index=True)


# ========================================
# TAB WATCHLIST
# ========================================
with tab_watchlist:
    st.subheader("Watchlist")
    st.caption("Daftar saham yang kamu simpan. Tambahkan dari tab Analisa Saham (mode Single).")

    wl = baca_watchlist()

    if not wl:
        st.info("Watchlist masih kosong. Buka tab Analisa Saham, pilih saham, lalu klik 'Tambah ke Watchlist'.")
    else:
        wl_rows = []
        with st.spinner("Memuat harga terkini watchlist..."):
            # Fetch data secara paralel untuk mempercepat pemuatan watchlist
            def _fetch_wl_item(t):
                df_wl = ambil_data(t, "1mo")
                fund_wl = ambil_fundamental(t)
                return t, df_wl, fund_wl
            
            wl_results = {}
            with ThreadPoolExecutor(max_workers=min(8, len(wl))) as executor:
                future_wl = {executor.submit(_fetch_wl_item, t): t for t in wl}
                for future in as_completed(future_wl):
                    t = future_wl[future]
                    try:
                        _, df_wl, fund_wl = future.result()
                        wl_results[t] = (df_wl, fund_wl)
                    except Exception:
                        wl_results[t] = (None, None)

            for _tick_wl in wl:
                _kode_wl = _tick_wl.replace(".JK", "")
                _df_wl, _fund_wl = wl_results.get(_tick_wl, (None, None))
                _harga = f"Rp {float(_df_wl['Close'].iloc[-1]):,.0f}" if _df_wl is not None and not _df_wl.empty else "N/A"
                _chg = "N/A"
                if _df_wl is not None and len(_df_wl) >= 2:
                    _h_kini = float(_df_wl["Close"].iloc[-1])
                    _h_prev = float(_df_wl["Close"].iloc[-2])
                    _chg = f"{((_h_kini - _h_prev) / _h_prev * 100):+.2f}%"
                wl_rows.append({
                    "Kode": _kode_wl,
                    "Nama": _fund_wl.get("nama", _kode_wl) if _fund_wl else _kode_wl,
                    "Sektor": _fund_wl.get("sektor", "N/A") if _fund_wl else "N/A",
                    "Harga Terakhir": _harga,
                    "Perubahan": _chg,
                })


        df_wl_tbl = pd.DataFrame(wl_rows)
        st.dataframe(df_wl_tbl, use_container_width=True, hide_index=True)

        st.markdown("**Hapus dari Watchlist:**")
        kode_hapus = st.selectbox(
            "Pilih saham yang ingin dihapus",
            [t.replace(".JK", "") for t in wl],
            key="wl_hapus_select"
        )
        if st.button("Hapus", key="btn_wl_hapus_tab"):
            hapus_dari_watchlist(kode_hapus + ".JK")
            st.success(f"{kode_hapus} dihapus dari watchlist.")
            st.rerun()


# ========================================
# TAB PORTFOLIO TRACKER
# ========================================
with tab_portfolio:
    st.subheader("Portfolio Tracker")
    st.caption("Catat posisi saham kamu dan lihat unrealized P/L secara otomatis.")

    portfolio = baca_portfolio()

    # -- Form tambah posisi baru --
    with st.expander("Tambah Posisi Baru", expanded=not bool(portfolio)):
        opsi_saham_pf = list(SAHAM_IDX.keys()) + ["Input Ticker Manual"]
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            pilihan_pf = st.selectbox("Saham", opsi_saham_pf, key="pf_saham")
            if pilihan_pf == "Input Ticker Manual":
                raw_pf = st.text_input("Ticker (contoh: BBCA)", key="pf_manual").upper().strip()
                ticker_pf = raw_pf if raw_pf.endswith(".JK") else raw_pf + ".JK"
            else:
                ticker_pf = SAHAM_IDX[pilihan_pf]
            lot_pf = st.number_input(
                "Jumlah Lot", min_value=1, value=1, step=1, key="pf_lot",
                help="1 lot = 100 lembar saham di BEI."
            )
        with col_p2:
            harga_beli_pf = st.number_input(
                "Harga Beli per Lembar (Rp)", min_value=1, value=1000, step=10, key="pf_harga",
                help="Harga beli rata-rata per lembar saham."
            )
            tgl_pf = st.date_input("Tanggal Beli", key="pf_tgl")

        if st.button("Simpan Posisi", key="btn_pf_tambah", type="primary"):
            if ticker_pf and lot_pf > 0 and harga_beli_pf > 0:
                portfolio.append({
                    "ticker": ticker_pf,
                    "lot": lot_pf,
                    "harga_beli": harga_beli_pf,
                    "tanggal_beli": str(tgl_pf),
                })
                simpan_portfolio(portfolio)
                st.success(f"Posisi {ticker_pf.replace('.JK','')} ({lot_pf} lot @ Rp {harga_beli_pf:,}) disimpan.")
                st.rerun()
            else:
                st.error("Lengkapi semua field sebelum menyimpan.")

    # -- Tabel posisi + summary --
    if not portfolio:
        st.info("Portfolio masih kosong. Tambahkan posisi pertama kamu di atas.")
    else:
        with st.spinner("Menghitung P/L terkini..."):
            df_pf = hitung_portfolio_summary(portfolio)

        if not df_pf.empty:
            total_modal = df_pf["_modal_raw"].sum()
            total_nilai = df_pf["_nilai_kini_raw"].sum()
            total_pl = df_pf["_pl_rp_raw"].sum()
            total_pl_pct = (total_pl / total_modal * 100) if total_modal > 0 else 0.0
            posisi_untung = int((df_pf["_pl_rp_raw"] > 0).sum())

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric(
                "Total Modal", f"Rp {total_modal:,.0f}",
                help="Total modal yang diinvestasikan termasuk biaya beli broker 0.15%."
            )
            mc2.metric(
                "Nilai Portfolio Kini", f"Rp {total_nilai:,.0f}",
                help="Estimasi nilai jika semua posisi dijual sekarang (setelah biaya jual 0.25%)."
            )
            mc3.metric(
                "Unrealized P/L", f"Rp {total_pl:+,.0f}",
                delta=f"{total_pl_pct:+.2f}%",
                help="Total keuntungan atau kerugian belum terealisasi dari seluruh posisi."
            )
            mc4.metric(
                "Posisi Untung", f"{posisi_untung} / {len(df_pf)}",
                help="Jumlah posisi yang saat ini berada di atas harga beli."
            )

            st.divider()

            tampil_cols = [
                "Ticker", "Lot", "Harga Beli (Rp)", "Harga Kini (Rp)",
                "Modal (Rp)", "Nilai Kini (Rp)", "P/L (Rp)", "P/L (%)", "Tgl Beli"
            ]
            st.dataframe(df_pf[tampil_cols], use_container_width=True, hide_index=True)

            # Export portfolio ke CSV
            csv_data = df_pf[tampil_cols].to_csv(index=False).encode('utf-8')
            now_str = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y%m%d")
            st.download_button(
                label="📥 Export Portfolio ke CSV",
                data=csv_data,
                file_name=f"portfolio_{now_str}.csv",
                mime="text/csv",
                key="btn_pf_export"
            )

            st.divider()
            st.markdown("**Hapus Posisi:**")
            idx_hapus = st.selectbox(
                "Pilih posisi yang ingin dihapus",
                options=list(range(len(portfolio))),
                format_func=lambda i: (
                    f"{portfolio[i]['ticker'].replace('.JK','')} -- "
                    f"{portfolio[i]['lot']} lot @ Rp {portfolio[i]['harga_beli']:,} "
                    f"({portfolio[i].get('tanggal_beli', '')})"
                ),
                key="pf_hapus_select"
            )
            if st.button("Hapus Posisi", key="btn_pf_hapus"):
                portfolio.pop(idx_hapus)
                simpan_portfolio(portfolio)
                st.success("Posisi dihapus.")
                st.rerun()


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
if st.session_state.get("offline_mode"):
    st.caption("[OFFLINE] Data yang ditampilkan berasal dari cache lokal, bukan data real-time.")
else:
    st.caption(
        f"Data diperbarui setiap 5 menit -- Terakhir diambil: {waktu_wib.strftime('%d %b %Y %H:%M WIB')}"
    )
