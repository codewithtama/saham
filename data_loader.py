import json
import os

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

WIB_TIMEZONE = "Asia/Jakarta"

# ========================================
# DINAMIS CONFIG LOADER (BEBAS HARDCODE)
# ========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_saham.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _config = json.load(f)
except Exception as e:
    st.error(f"Gagal memuat konfigurasi {CONFIG_PATH}: {e}")
    _config = {}

SAHAM_IDX = _config.get("SAHAM_IDX", {})
TIMEFRAME_OPTIONS = _config.get("TIMEFRAME_OPTIONS", {})
RINGKASAN_SAHAM_BEI = _config.get("RINGKASAN_SAHAM_BEI", {})
TERJEMAHAN_SEKTOR = _config.get("terjemahan_sektor", {})


# ========================================
# FUNGSI AMBIL DATA
# ========================================
@st.cache_data(ttl=300)
def ambil_data(ticker: str, periode: str) -> pd.DataFrame | None:
    try:
        # Tentukan interval secara otomatis berdasarkan periode
        if periode == "1d":
            intv = "5m"
        elif periode == "5d":
            intv = "15m"
        else:
            intv = "1d"

        df = yf.download(
            ticker, period=periode, interval=intv, auto_adjust=True, progress=False
        )
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Pastikan seluruh kolom standar bursa tersedia guna mencegah KeyError
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                df[col] = np.nan

        # Isi volume kosong dengan 0 agar tidak terbuang saat pembersihan data
        df["Volume"] = df["Volume"].fillna(0)

        # Bersihkan hanya jika harga utama (Open, High, Low, Close) tidak lengkap
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(
            subset=["Open", "High", "Low", "Close"]
        )
        index = pd.DatetimeIndex(df.index)
        if index.tz is not None:
            index = index.tz_convert(WIB_TIMEZONE).tz_localize(None)
        df.index = index
        return df.sort_index()
    except Exception as e:
        st.error(f"Error ambil data {ticker}: {e}")
        return None


@st.cache_data(ttl=3600)  # Caching fundamental data selama 1 jam
def ambil_fundamental(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return {}

        # Ubah nama sektor ke Bahasa Indonesia supaya lebih mudah dibaca
        sektor_en = info.get("sector", "Tidak diketahui")
        industri_en = info.get("industry", "Tidak diketahui")

        sektor_id = TERJEMAHAN_SEKTOR.get(sektor_en, sektor_en)

        # Buat ringkasan perusahaan dengan bahasa yang lebih sederhana
        ringkasan_en = info.get("longBusinessSummary")
        if ticker in RINGKASAN_SAHAM_BEI:
            ringkasan_id = RINGKASAN_SAHAM_BEI[ticker]
        elif ringkasan_en:
            nama = info.get("longName", ticker.split(".")[0])
            ringkasan_id = (
                f"{nama} adalah perusahaan yang sahamnya tercatat di Bursa Efek Indonesia (BEI). "
                f"Perusahaan ini masuk sektor {sektor_id} dan bergerak di bidang {industri_en}. "
                f"Singkatnya, ini gambaran bisnis perusahaan berdasarkan data Yahoo Finance:\n\n{ringkasan_en}"
            )
        else:
            ringkasan_id = "Belum ada cerita singkat perusahaan untuk saham ini."

        return {
            "nama": info.get("longName", ticker.split(".")[0]),
            "sektor": sektor_id,
            "industri": industri_en,
            "ringkasan": ringkasan_id,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "beta": info.get("beta"),
            "dividend_yield": info.get("dividendYield"),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "low_52w": info.get("fiftyTwoWeekLow"),
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def ambil_data_marquee() -> list:
    tickers = list(SAHAM_IDX.values())
    tickers_str = " ".join(tickers)
    try:
        # Download data 2 hari terakhir untuk semua ticker sekaligus
        df_all = yf.download(tickers_str, period="2d", auto_adjust=True, progress=False)
        if df_all.empty:
            return []

        marquee_items = []
        for name, ticker in SAHAM_IDX.items():
            code = name.split(" -- ")[0]
            try:
                # Jika yf.download mengembalikan MultiIndex columns
                if isinstance(df_all.columns, pd.MultiIndex):
                    if ticker in df_all.columns.levels[0]:
                        df_ticker = df_all[ticker].dropna()
                    elif ticker in df_all.columns.levels[1]:
                        df_ticker = df_all.xs(ticker, axis=1, level=1).dropna()
                    else:
                        continue
                else:
                    df_ticker = df_all.dropna()

                if len(df_ticker) >= 1:
                    harga_kini = float(df_ticker["Close"].iloc[-1])
                    if len(df_ticker) >= 2:
                        harga_prev = float(df_ticker["Close"].iloc[-2])
                    else:
                        harga_prev = harga_kini

                    perubahan = harga_kini - harga_prev
                    pct_perubahan = (
                        (perubahan / harga_prev) * 100 if harga_prev > 0 else 0.0
                    )

                    marquee_items.append(
                        {"kode": code, "harga": harga_kini, "change": pct_perubahan}
                    )
            except Exception:
                continue
        return marquee_items
    except Exception:
        return []
