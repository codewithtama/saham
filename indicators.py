import numpy as np
import pandas as pd

# ============================================================
# KONSTANTA BURSA EFEK INDONESIA
# ============================================================
LOT_SIZE: int = 100          # 1 lot = 100 lembar saham di BEI
BROKER_FEE_BUY: float = 0.0015   # 0.15% biaya beli (typical IDX)
BROKER_FEE_SELL: float = 0.0025  # 0.25% biaya jual + levy (typical IDX)
STOP_LOSS_PCT: float = 0.07      # Stop-loss 7% di bawah harga beli


def hitung_ma(close: pd.Series, periode: int) -> pd.Series:
    return close.rolling(window=periode).mean()


def hitung_ema(close: pd.Series, periode: int) -> pd.Series:
    return close.ewm(span=periode, adjust=False).mean()


def hitung_rsi(close: pd.Series, periode: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's Smoothed Moving Average: EMA dengan alpha = 1/periode
    # Ini adalah standar industri (TradingView, Bloomberg, Reuters)
    # Berbeda dari SMA biasa yang akan menghasilkan nilai RSI yang berbeda
    avg_gain = gain.ewm(alpha=1 / periode, min_periods=periode, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / periode, min_periods=periode, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Kalau harga terus naik, loss bisa 0. Dalam kondisi itu RSI seharusnya 100.
    # Kalau harga benar-benar datar (avg_gain == 0 juga), anggap netral di 50.
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    rsi = rsi.fillna(50.0)
    return rsi


def hitung_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = hitung_ema(close, fast)
    ema_slow = hitung_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def hitung_bollinger(close: pd.Series, periode=20, num_std=2):
    ma = close.rolling(window=periode).mean()
    std = close.rolling(window=periode).std()
    upper = ma + std * num_std
    lower = ma - std * num_std
    return upper, ma, lower


def hitung_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_periode: int = 14,
    d_periode: int = 3,
) -> tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=k_periode).min()
    highest_high = high.rolling(window=k_periode).max()
    diff = highest_high - lowest_low
    # Hindari pembagian dengan nol jika harga benar-benar datar (diff == 0)
    k_line = np.where(
        diff == 0, 50.0, ((close - lowest_low) / diff.replace(0, np.nan)) * 100
    )
    k_line = pd.Series(k_line, index=close.index)
    d_line = k_line.rolling(window=d_periode).mean()
    return k_line, d_line


def hitung_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    obv = (direction * volume).cumsum()
    return obv


def hitung_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, periode: int = 14
) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periode).mean()
    return atr


def sinyal_teknikal(df: pd.DataFrame) -> dict:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi = hitung_rsi(close)
    ma20 = hitung_ma(close, 20)
    ma50 = hitung_ma(close, 50)
    macd, signal_line, _ = hitung_macd(close)
    k_line, d_line = hitung_stochastic(high, low, close)

    sinyal = {}

    # --- Sinyal RSI ---
    rsi_val = float(rsi.iloc[-1]) if len(rsi) > 0 else np.nan
    if pd.isna(rsi_val):
        sinyal["RSI"] = ("HOLD", "RSI: Data tidak cukup")
    elif rsi_val > 70:
        sinyal["RSI"] = ("SELL", f"RSI {rsi_val:.1f}: harga mulai terlihat terlalu panas")
    elif rsi_val < 30:
        sinyal["RSI"] = ("BUY", f"RSI {rsi_val:.1f}: harga mulai terlihat cukup murah")
    else:
        sinyal["RSI"] = ("HOLD", f"RSI {rsi_val:.1f}: masih wajar")

    # --- Sinyal MA Cross (deteksi Golden/Dead Cross + status tren) ---
    ma20_curr = float(ma20.iloc[-1]) if len(ma20) > 0 else np.nan
    ma50_curr = float(ma50.iloc[-1]) if len(ma50) > 0 else np.nan

    if pd.isna(ma20_curr) or pd.isna(ma50_curr):
        sinyal["MA Cross"] = ("HOLD", "MA Cross: Data tidak cukup")
    else:
        # Scan 5 bar terakhir untuk deteksi Golden/Dead Cross terbaru
        # Scan dari bar terbaru ke lama agar cross terbaru yang menang
        _CROSS_LOOKBACK = 5
        baru_golden = False
        baru_dead = False
        if len(ma20) > _CROSS_LOOKBACK and len(ma50) > _CROSS_LOOKBACK:
            for j in range(1, _CROSS_LOOKBACK + 1):
                pf = float(ma20.iloc[-j - 1])
                ps = float(ma50.iloc[-j - 1])
                cf = float(ma20.iloc[-j])
                cs = float(ma50.iloc[-j])
                if pf <= ps and cf > cs:
                    baru_golden = True
                    break
                if pf >= ps and cf < cs:
                    baru_dead = True
                    break

        if ma20_curr > ma50_curr:
            if baru_golden:
                sinyal["MA Cross"] = (
                    "BUY",
                    f"Golden Cross! MA20 ({ma20_curr:.0f}) baru saja melewati MA50 ({ma50_curr:.0f}) ke atas",
                )
            else:
                sinyal["MA Cross"] = (
                    "BUY",
                    f"Uptrend: MA20 ({ma20_curr:.0f}) di atas MA50 ({ma50_curr:.0f}) — tren jangka pendek lebih kuat",
                )
        else:
            if baru_dead:
                sinyal["MA Cross"] = (
                    "SELL",
                    f"Dead Cross! MA20 ({ma20_curr:.0f}) baru saja melewati MA50 ({ma50_curr:.0f}) ke bawah",
                )
            else:
                sinyal["MA Cross"] = (
                    "SELL",
                    f"Downtrend: MA20 ({ma20_curr:.0f}) di bawah MA50 ({ma50_curr:.0f}) — tren jangka pendek lebih lemah",
                )

    # --- Sinyal MACD (deteksi crossover terbaru + status momentum) ---
    macd_curr = float(macd.iloc[-1]) if len(macd) > 0 else np.nan
    signal_curr = float(signal_line.iloc[-1]) if len(signal_line) > 0 else np.nan

    if pd.isna(macd_curr) or pd.isna(signal_curr):
        sinyal["MACD"] = ("HOLD", "MACD: Data tidak cukup")
    else:
        baru_bullish = False
        baru_bearish = False
        if len(macd) >= 2 and len(signal_line) >= 2:
            prev_m = float(macd.iloc[-2])
            prev_s = float(signal_line.iloc[-2])
            if prev_m <= prev_s and macd_curr > signal_curr:
                baru_bullish = True
            elif prev_m >= prev_s and macd_curr < signal_curr:
                baru_bearish = True

        if macd_curr > signal_curr:
            if baru_bullish:
                sinyal["MACD"] = (
                    "BUY",
                    "MACD baru saja memotong Signal Line ke atas — momentum naik mulai menguat",
                )
            else:
                sinyal["MACD"] = (
                    "BUY",
                    f"MACD ({macd_curr:.3f}) di atas Signal — momentum naik sedang berlanjut",
                )
        else:
            if baru_bearish:
                sinyal["MACD"] = (
                    "SELL",
                    "MACD baru saja memotong Signal Line ke bawah — momentum turun mulai menguat",
                )
            else:
                sinyal["MACD"] = (
                    "SELL",
                    f"MACD ({macd_curr:.3f}) di bawah Signal — momentum turun sedang berlanjut",
                )

    # --- Sinyal Stochastic Oscillator ---
    stoch_k = float(k_line.iloc[-1]) if len(k_line) > 0 else np.nan
    stoch_d = float(d_line.iloc[-1]) if len(d_line) > 0 else np.nan
    if pd.isna(stoch_k) or pd.isna(stoch_d):
        sinyal["Stochastic"] = ("HOLD", "Stochastic: Data tidak cukup")
    elif stoch_k < 20 and stoch_k > stoch_d:
        sinyal["Stochastic"] = (
            "BUY",
            f"K({stoch_k:.1f}) mulai berbalik naik dari area rendah",
        )
    elif stoch_k > 80 and stoch_k < stoch_d:
        sinyal["Stochastic"] = (
            "SELL",
            f"K({stoch_k:.1f}) mulai melemah dari area tinggi",
        )
    else:
        sinyal["Stochastic"] = (
            "HOLD",
            f"Stochastic K({stoch_k:.1f}) / D({stoch_d:.1f}) masih netral",
        )

    return sinyal


def hitung_konsensus_sinyal(sinyal: dict) -> tuple[str, str, str]:
    buy_count = 0
    sell_count = 0
    hold_count = 0
    total_active = 0

    for nama, (arah, ket) in sinyal.items():
        # Jangan hitung jika data tidak cukup
        if "Data tidak cukup" in ket:
            continue
        total_active += 1
        if arah == "BUY":
            buy_count += 1
        elif arah == "SELL":
            sell_count += 1
        else:
            hold_count += 1

    if total_active == 0:
        return (
            "DATA BELUM CUKUP",
            "Data harga belum cukup panjang, jadi aplikasi belum bisa memberi gambaran yang cukup aman.",
            "#8b949e",
        )

    buy_ratio = buy_count / total_active
    sell_ratio = sell_count / total_active

    if buy_ratio >= 0.75:
        return (
            "PELUANG BELI KUAT",
            f"{buy_count} dari {total_active} tanda utama mengarah ke beli. Harga sedang terlihat cukup kuat, tapi tetap cek risiko dan jangan pakai seluruh modal sekaligus.",
            "#00e676",
        )
    elif buy_ratio >= 0.5:
        return (
            "CENDERUNG BISA BELI",
            f"{buy_count} dari {total_active} tanda utama mulai mendukung beli. Kalau tertarik masuk, lebih aman dicicil dan tetap siapkan batas rugi.",
            "#00ff00",
        )
    elif sell_ratio >= 0.75:
        return (
            "WASPADA, TEKANAN JUAL KUAT",
            f"{sell_count} dari {total_active} tanda utama mengarah ke jual. Kalau sudah punya saham ini, pertimbangkan untuk amankan untung atau batasi rugi.",
            "#ff1744",
        )
    elif sell_ratio >= 0.5:
        return (
            "CENDERUNG HATI-HATI",
            f"{sell_count} dari {total_active} tanda utama menunjukkan tekanan turun. Lebih baik jangan buru-buru masuk, atau kurangi posisi kalau risikonya terasa besar.",
            "#ff3333",
        )
    else:
        return (
            "TUNGGU DULU",
            f"Sinyalnya masih campur aduk. {hold_count} dari {total_active} tanda masih netral, jadi lebih aman tunggu arah harga lebih jelas.",
            "#ffa500",
        )

