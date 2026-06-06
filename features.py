"""
features.py -- Logika untuk fitur tambahan:
  - Stock Screener
  - Support & Resistance otomatis
  - Watchlist (persistensi JSON lokal)
  - Portfolio Tracker (persistensi JSON lokal)
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# PATH SETUP
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

WATCHLIST_PATH = os.path.join(DATA_DIR, "watchlist.json")
PORTFOLIO_PATH = os.path.join(DATA_DIR, "portfolio.json")


# ============================================================
# SUPPORT & RESISTANCE OTOMATIS
# ============================================================
def hitung_support_resistance(
    df: pd.DataFrame, lookback: int = 10, max_levels: int = 3
) -> list[dict]:
    """
    Deteksi swing high (resistance) dan swing low (support) dari OHLC.
    Menggunakan sliding window -- bar dianggap swing jika ia high/low tertinggi
    dalam [i-lookback, i+lookback]. Mengembalikan list dict:
      {"harga": float, "jenis": "R"|"S", "label": "R1"/"S1"/...}
    Diurutkan: resistance dari tertinggi, support dari terendah ke atas.
    """
    if len(df) < lookback * 2 + 1:
        return []

    highs = df["High"].values
    lows = df["Low"].values
    close_last = float(df["Close"].iloc[-1])

    swing_highs: list[float] = []
    swing_lows: list[float] = []

    for i in range(lookback, len(df) - lookback):
        window_h = highs[i - lookback : i + lookback + 1]
        window_l = lows[i - lookback : i + lookback + 1]
        if highs[i] == window_h.max():
            swing_highs.append(float(highs[i]))
        if lows[i] == window_l.min():
            swing_lows.append(float(lows[i]))

    # Cluster level yang terlalu berdekatan (dalam 0.5% satu sama lain)
    def cluster(levels: list[float], threshold_pct: float = 0.005) -> list[float]:
        if not levels:
            return []
        levels = sorted(set(levels))
        clustered: list[float] = [levels[0]]
        for lv in levels[1:]:
            if abs(lv - clustered[-1]) / clustered[-1] > threshold_pct:
                clustered.append(lv)
        return clustered

    resistances = sorted(
        [lv for lv in cluster(swing_highs) if lv > close_last], reverse=True
    )[:max_levels]
    supports = sorted(
        [lv for lv in cluster(swing_lows) if lv < close_last]
    )[::-1][:max_levels]  # closest support first

    result: list[dict] = []
    for i, lv in enumerate(resistances, 1):
        result.append({"harga": lv, "jenis": "R", "label": f"R{i}"})
    for i, lv in enumerate(supports, 1):
        result.append({"harga": lv, "jenis": "S", "label": f"S{i}"})

    return result


# ============================================================
# STOCK SCREENER
# ============================================================
def _fetch_fundamental_for_screener(ticker: str, nama: str) -> dict | None:
    """Fetch fundamental satu ticker -- dijalankan di thread pool."""
    from data_loader import ambil_fundamental
    fund = ambil_fundamental(ticker)
    if not fund:
        return None
    kode = ticker.replace(".JK", "")
    mc = fund.get("market_cap")
    if mc and mc >= 1e12:
        mc_str = f"Rp {mc / 1e12:.1f} T"
    elif mc and mc >= 1e9:
        mc_str = f"Rp {mc / 1e9:.1f} M"
    else:
        mc_str = "N/A"

    div_val = fund.get("dividend_yield")
    div_pct = (div_val if div_val and div_val > 1.0 else (div_val * 100 if div_val else 0.0))

    return {
        "Kode": kode,
        "Nama": fund.get("nama", kode),
        "Sektor": fund.get("sektor", "N/A"),
        "Market Cap": mc_str,
        "_market_cap": mc or 0.0,
        "P/E": round(fund.get("pe_ratio") or 0.0, 2),
        "PBV": round(fund.get("pbv") or 0.0, 2),
        "ROE (%)": round((fund.get("roe") or 0.0) * 100, 2),
        "DER (%)": round(fund.get("der") or 0.0, 2),
        "Div Yield (%)": round(div_pct, 2),
        "_ticker": ticker,
    }


@st.cache_data(ttl=3600)
def ambil_semua_fundamental_raw() -> pd.DataFrame:
    """
    Mengambil data fundamental untuk seluruh ticker SAHAM_IDX secara paralel
    dan mengembalikannya sebagai DataFrame mentah. Di-cache selama 1 jam.
    """
    from data_loader import SAHAM_IDX
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(_fetch_fundamental_for_screener, ticker, name): ticker
            for name, ticker in SAHAM_IDX.items()
        }
        for future in as_completed(futures):
            try:
                row = future.result()
                if row:
                    results.append(row)
            except Exception:
                continue
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results)


def jalankan_screener(
    sektor_filter: str | None,
    pe_max: float,
    roe_min: float,
    der_max: float,
    div_min: float,
    mc_min_t: float,  # dalam Triliun Rp
) -> pd.DataFrame:
    """
    Filter data fundamental yang sudah di-cache berdasarkan parameter input.
    Sangat cepat karena tidak ada I/O network.
    """
    df = ambil_semua_fundamental_raw()
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Terapkan filter
    if sektor_filter and sektor_filter != "Semua":
        df = df[df["Sektor"] == sektor_filter]
    if pe_max > 0:
        df = df[(df["P/E"] > 0) & (df["P/E"] <= pe_max)]
    if roe_min > 0:
        df = df[df["ROE (%)"] >= roe_min]
    if der_max < 999:
        df = df[(df["DER (%)"] >= 0) & (df["DER (%)"] <= der_max)]
    if div_min > 0:
        df = df[df["Div Yield (%)"] >= div_min]
    if mc_min_t > 0:
        df = df[df["_market_cap"] >= mc_min_t * 1e12]

    # Buang kolom internal
    df = df.drop(columns=["_market_cap", "_ticker"], errors="ignore")
    df = df.sort_values("ROE (%)", ascending=False).reset_index(drop=True)
    return df


# ============================================================
# WATCHLIST
# ============================================================
def baca_watchlist() -> list[str]:
    """Baca daftar ticker dari watchlist.json. Kembalikan list kosong jika tidak ada."""
    if not os.path.exists(WATCHLIST_PATH):
        return []
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def simpan_watchlist(tickers: list[str]) -> None:
    """Tulis list ticker ke watchlist.json."""
    try:
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(tickers, f, indent=2)
    except Exception:
        pass


def tambah_ke_watchlist(ticker: str) -> bool:
    """Tambah ticker ke watchlist. Return True jika baru ditambahkan."""
    wl = baca_watchlist()
    if ticker not in wl:
        wl.append(ticker)
        simpan_watchlist(wl)
        return True
    return False


def hapus_dari_watchlist(ticker: str) -> None:
    """Hapus ticker dari watchlist."""
    wl = baca_watchlist()
    wl = [t for t in wl if t != ticker]
    simpan_watchlist(wl)


# ============================================================
# PORTFOLIO TRACKER
# ============================================================
def baca_portfolio() -> list[dict]:
    """
    Baca entri portfolio dari portfolio.json.
    Setiap entri: {ticker, lot, harga_beli, tanggal_beli}
    """
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    try:
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def simpan_portfolio(entries: list[dict]) -> None:
    """Tulis list entri ke portfolio.json."""
    try:
        with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)
    except Exception:
        pass


def hitung_portfolio_summary(entries: list[dict]) -> pd.DataFrame:
    """
    Ambil harga terkini tiap ticker di portfolio secara concurrent,
    hitung unrealized P/L. Kembalikan DataFrame ringkasan posisi.
    """
    from data_loader import ambil_data

    LOT_SIZE = 100
    BROKER_BUY = 0.0015
    BROKER_SELL = 0.0025

    def _get_price(ticker: str) -> float | None:
        # Gunakan "1mo" (data harian) bukan "5d" (intraday 15m yang bisa kosong diluar jam bursa)
        df = ambil_data(ticker, "1mo")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])

    # Kumpulkan ticker unik
    tickers_unik = list({e["ticker"] for e in entries if e.get("ticker")})
    harga_kini_map: dict[str, float] = {}

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_get_price, t): t for t in tickers_unik}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                harga = future.result()
                if harga:
                    harga_kini_map[ticker] = harga
            except Exception:
                pass

    rows: list[dict] = []
    for entry in entries:
        ticker = entry.get("ticker", "")
        lot = int(entry.get("lot", 0))
        harga_beli = float(entry.get("harga_beli", 0))
        tgl = entry.get("tanggal_beli", "")
        lembar = lot * LOT_SIZE

        harga_sekarang = harga_kini_map.get(ticker)
        modal = lembar * harga_beli * (1 + BROKER_BUY)

        if harga_sekarang:
            nilai_kini = lembar * harga_sekarang * (1 - BROKER_SELL)
            pl_rp = nilai_kini - modal
            pl_pct = (pl_rp / modal) * 100 if modal > 0 else 0.0
        else:
            nilai_kini = None
            pl_rp = None
            pl_pct = None

        rows.append({
            "Ticker": ticker.replace(".JK", ""),
            "_ticker_full": ticker,
            "Lot": lot,
            "Harga Beli (Rp)": f"{harga_beli:,.0f}",
            "Harga Kini (Rp)": f"{harga_sekarang:,.0f}" if harga_sekarang else "N/A",
            "Modal (Rp)": f"{modal:,.0f}",
            "Nilai Kini (Rp)": f"{nilai_kini:,.0f}" if nilai_kini is not None else "N/A",
            "P/L (Rp)": f"{pl_rp:+,.0f}" if pl_rp is not None else "N/A",
            "P/L (%)": f"{pl_pct:+.2f}%" if pl_pct is not None else "N/A",
            "_pl_rp_raw": pl_rp or 0.0,
            "_modal_raw": modal,
            "_nilai_kini_raw": nilai_kini or 0.0,
            "Tgl Beli": tgl,
        })

    return pd.DataFrame(rows)
