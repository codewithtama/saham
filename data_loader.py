import json
import os
from datetime import datetime

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
CACHE_DIR = os.path.join(BASE_DIR, "cache")

# Pastikan folder cache selalu ada
os.makedirs(CACHE_DIR, exist_ok=True)

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
# HELPER CACHE INTERNAL
# ========================================
def _cache_path(nama_file: str) -> str:
    """Kembalikan path absolut ke file cache."""
    return os.path.join(CACHE_DIR, nama_file)


def _set_offline(sumber: str, ticker: str = "") -> None:
    """Tandai bahwa app sedang berjalan dalam mode offline."""
    if "offline_mode" not in st.session_state or not st.session_state["offline_mode"]:
        st.session_state["offline_mode"] = True
        st.session_state["offline_sources"] = []
    label = f"{ticker} ({sumber})" if ticker else sumber
    if label not in st.session_state.get("offline_sources", []):
        st.session_state.setdefault("offline_sources", []).append(label)


def _simpan_cache_csv(df: pd.DataFrame, nama_file: str) -> None:
    """Simpan DataFrame ke CSV cache. Tulis timestamp di metadata sidecar."""
    try:
        path = _cache_path(nama_file)
        df.to_csv(path)
        # Simpan timestamp kapan terakhir di-cache
        meta_path = path + ".meta"
        with open(meta_path, "w") as mf:
            json.dump({"cached_at": datetime.now().isoformat()}, mf)
    except Exception:
        pass  # Cache write failure tidak boleh crash app


def _baca_cache_csv(nama_file: str) -> tuple[pd.DataFrame | None, str | None]:
    """
    Baca DataFrame dari CSV cache.
    Returns: (DataFrame atau None, timestamp string atau None)
    """
    path = _cache_path(nama_file)
    if not os.path.exists(path):
        return None, None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        cached_at = None
        meta_path = path + ".meta"
        if os.path.exists(meta_path):
            with open(meta_path) as mf:
                meta = json.load(mf)
                cached_at = meta.get("cached_at")
        return df, cached_at
    except Exception:
        return None, None


def _simpan_cache_json(data: dict | list, nama_file: str) -> None:
    """Simpan dict/list ke JSON cache dengan timestamp."""
    try:
        path = _cache_path(nama_file)
        payload = {"cached_at": datetime.now().isoformat(), "data": data}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _baca_cache_json(nama_file: str) -> tuple[dict | list | None, str | None]:
    """
    Baca dict/list dari JSON cache.
    Returns: (data atau None, timestamp string atau None)
    """
    path = _cache_path(nama_file)
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("data"), payload.get("cached_at")
    except Exception:
        return None, None


# ========================================
# FUNGSI AMBIL DATA
# ========================================
@st.cache_data(ttl=300)
def ambil_data(ticker: str, periode: str) -> pd.DataFrame | None:
    cache_file = f"price_{ticker.replace('.', '_')}_{periode}.csv"
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
            raise ValueError("Data kosong dari yfinance")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Pastikan seluruh kolom standar bursa tersedia
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                df[col] = np.nan

        df["Volume"] = df["Volume"].fillna(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(
            subset=["Open", "High", "Low", "Close"]
        )
        index = pd.DatetimeIndex(df.index)
        if index.tz is not None:
            index = index.tz_convert(WIB_TIMEZONE).tz_localize(None)
        df.index = index
        df = df.sort_index()

        # Berhasil online -> simpan ke cache
        _simpan_cache_csv(df, cache_file)
        return df

    except Exception as e:
        # Gagal online -> coba baca cache
        df_cache, cached_at = _baca_cache_csv(cache_file)
        if df_cache is not None and not df_cache.empty:
            _set_offline(f"data harga {periode}", ticker)
            if "offline_cache_times" not in st.session_state:
                st.session_state["offline_cache_times"] = {}
            st.session_state["offline_cache_times"][ticker] = cached_at
            return df_cache
        # Tidak ada cache sama sekali
        st.error(f"Error ambil data {ticker}: {e} — tidak ada cache tersedia.")
        return None


@st.cache_data(ttl=3600)
def ambil_fundamental(ticker: str) -> dict:
    cache_file = f"fundamental_{ticker.replace('.', '_')}.json"
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            raise ValueError("info kosong dari yfinance")

        sektor_en = info.get("sector", "Tidak diketahui")
        industri_en = info.get("industry", "Tidak diketahui")
        sektor_id = TERJEMAHAN_SEKTOR.get(sektor_en, sektor_en)

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

        result = {
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
            "pbv": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "der": info.get("debtToEquity"),
            "eps": info.get("trailingEps"),
            "bvps": info.get("bookValue"),
            "payout_ratio": info.get("payoutRatio"),
        }

        # Berhasil online -> simpan ke cache
        _simpan_cache_json(result, cache_file)
        return result

    except Exception as exc:
        # Gagal online -> coba baca cache
        data_cache, _ = _baca_cache_json(cache_file)
        if data_cache:
            _set_offline("fundamental", ticker)
            return data_cache
        st.warning(f"Data fundamental {ticker} tidak tersedia: {type(exc).__name__}")
        return {}


@st.cache_data(ttl=3600)
def ambil_financial_history(ticker: str) -> pd.DataFrame | None:
    cache_file = f"financial_{ticker.replace('.', '_')}.csv"
    try:
        t = yf.Ticker(ticker)
        df_fin = t.financials
        if df_fin is None or df_fin.empty:
            raise ValueError("financials kosong")

        df_t = df_fin.T

        rev_col = None
        net_col = None
        for col in df_t.columns:
            col_lower = str(col).lower()
            if "total revenue" in col_lower or "operating revenue" in col_lower or col_lower == "revenue":
                rev_col = col
            if "net income" in col_lower and "continuous" not in col_lower:
                net_col = col

        if not rev_col:
            for col in df_t.columns:
                if "revenue" in str(col).lower():
                    rev_col = col
                    break
        if not net_col:
            for col in df_t.columns:
                if "net income" in str(col).lower():
                    net_col = col
                    break

        if rev_col and net_col:
            res = df_t[[rev_col, net_col]].copy()
            res.columns = ["Revenue", "Net_Income"]
            res = res.sort_index(ascending=True)
            # Berhasil online -> simpan ke cache
            _simpan_cache_csv(res, cache_file)
            return res
        raise ValueError("Kolom Revenue/Net Income tidak ditemukan")

    except Exception:
        df_cache, _ = _baca_cache_csv(cache_file)
        if df_cache is not None and not df_cache.empty:
            _set_offline("laporan keuangan", ticker)
            return df_cache
        return None


@st.cache_data(ttl=3600)
def ambil_dividend_history(ticker: str) -> pd.DataFrame | None:
    cache_file = f"dividend_{ticker.replace('.', '_')}.csv"
    try:
        t = yf.Ticker(ticker)
        divs = t.dividends
        if divs is None or divs.empty:
            raise ValueError("dividen kosong")

        df_div = pd.DataFrame(divs)
        df_div.columns = ["Dividen"]
        df_div = df_div.sort_index(ascending=False)

        # Berhasil online -> simpan ke cache
        _simpan_cache_csv(df_div, cache_file)
        return df_div

    except Exception:
        df_cache, _ = _baca_cache_csv(cache_file)
        if df_cache is not None and not df_cache.empty:
            _set_offline("histori dividen", ticker)
            return df_cache
        return None


@st.cache_data(ttl=300)
def ambil_data_marquee() -> list:
    cache_file = "marquee.json"
    tickers = list(SAHAM_IDX.values())
    tickers_str = " ".join(tickers)
    try:
        df_all = yf.download(tickers_str, period="2d", auto_adjust=True, progress=False)
        if df_all.empty:
            raise ValueError("Data marquee kosong")

        marquee_items = []
        for name, ticker in SAHAM_IDX.items():
            code = name.split(" -- ")[0]
            try:
                if isinstance(df_all.columns, pd.MultiIndex):
                    all_tickers_in_cols = df_all.columns.get_level_values(1).unique()
                    all_fields_in_cols = df_all.columns.get_level_values(0).unique()
                    if ticker in all_tickers_in_cols:
                        df_ticker = df_all.xs(ticker, axis=1, level=1).dropna(how="all")
                    elif ticker in all_fields_in_cols:
                        df_ticker = df_all.xs(ticker, axis=1, level=0).dropna(how="all")
                    else:
                        continue
                else:
                    df_ticker = df_all.dropna(how="all")

                if len(df_ticker) >= 1:
                    harga_kini = float(df_ticker["Close"].iloc[-1])
                    harga_prev = float(df_ticker["Close"].iloc[-2]) if len(df_ticker) >= 2 else harga_kini
                    perubahan = harga_kini - harga_prev
                    pct_perubahan = (perubahan / harga_prev) * 100 if harga_prev > 0 else 0.0
                    marquee_items.append(
                        {"kode": code, "harga": harga_kini, "change": pct_perubahan}
                    )
            except Exception:
                continue

        if marquee_items:
            # Berhasil online -> simpan ke cache
            _simpan_cache_json(marquee_items, cache_file)
        return marquee_items

    except Exception:
        data_cache, _ = _baca_cache_json(cache_file)
        if data_cache:
            _set_offline("marquee ticker")
            return data_cache
        return []


@st.cache_data(ttl=300)
def ambil_kurs_usd_idr() -> dict | None:
    """Ambil kurs USD/IDR dari Yahoo Finance. Returns dict {kurs, change_pct} atau None."""
    cache_file = "kurs_usdidr.json"
    try:
        df = yf.download("USDIDR=X", period="2d", interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError("Data kurs kosong")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close"])
        if df.empty:
            raise ValueError("Kolom Close kurs kosong")

        kurs_kini = float(df["Close"].iloc[-1])
        kurs_prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else kurs_kini
        change_pct = ((kurs_kini - kurs_prev) / kurs_prev) * 100 if kurs_prev > 0 else 0.0

        result = {"kurs": kurs_kini, "change_pct": change_pct}
        _simpan_cache_json(result, cache_file)
        return result

    except Exception:
        data_cache, _ = _baca_cache_json(cache_file)
        if data_cache:
            _set_offline("kurs USD/IDR")
            return data_cache
        return None
