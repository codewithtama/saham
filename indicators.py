import numpy as np
import pandas as pd


def hitung_ma(close: pd.Series, periode: int) -> pd.Series:
    return close.rolling(window=periode).mean()


def hitung_ema(close: pd.Series, periode: int) -> pd.Series:
    return close.ewm(span=periode, adjust=False).mean()


def hitung_rsi(close: pd.Series, periode: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=periode).mean()
    avg_loss = loss.rolling(window=periode).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Kalau harga terus naik, loss bisa 0. Dalam kondisi itu RSI seharusnya 100,
    # bukan netral. Kalau harga benar-benar datar, baru kita anggap netral di 50.
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

    # Sinyal RSI
    rsi_val = float(rsi.iloc[-1]) if len(rsi) > 0 else np.nan
    if pd.isna(rsi_val):
        sinyal["RSI"] = ("HOLD", "RSI: Data tidak cukup")
    elif rsi_val > 70:
        sinyal["RSI"] = (
            "SELL",
            f"RSI {rsi_val:.1f}: harga mulai terlihat terlalu panas",
        )
    elif rsi_val < 30:
        sinyal["RSI"] = ("BUY", f"RSI {rsi_val:.1f}: harga mulai terlihat cukup murah")
    else:
        sinyal["RSI"] = ("HOLD", f"RSI {rsi_val:.1f}: masih wajar")

    # Sinyal MA Cross
    ma20_val = float(ma20.iloc[-1]) if len(ma20) > 0 else np.nan
    ma50_val = float(ma50.iloc[-1]) if len(ma50) > 0 else np.nan
    if pd.isna(ma20_val) or pd.isna(ma50_val):
        sinyal["MA Cross"] = ("HOLD", "MA Cross: Data tidak cukup")
    elif ma20_val > ma50_val:
        sinyal["MA Cross"] = (
            "BUY",
            "Rata-rata harga pendek ada di atas rata-rata panjang",
        )
    else:
        sinyal["MA Cross"] = (
            "SELL",
            "Rata-rata harga pendek ada di bawah rata-rata panjang",
        )

    # Sinyal MACD
    macd_val = float(macd.iloc[-1]) if len(macd) > 0 else np.nan
    signal_val = float(signal_line.iloc[-1]) if len(signal_line) > 0 else np.nan
    if pd.isna(macd_val) or pd.isna(signal_val):
        sinyal["MACD"] = ("HOLD", "MACD: Data tidak cukup")
    elif macd_val > signal_val:
        sinyal["MACD"] = ("BUY", f"MACD ({macd_val:.2f}) menunjukkan tenaga naik")
    else:
        sinyal["MACD"] = ("SELL", f"MACD ({macd_val:.2f}) menunjukkan tekanan turun")

    # Sinyal Stochastic Oscillator
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


def jalankan_backtest(df: pd.DataFrame, initial_capital: float = 10000000.0) -> dict:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # Hitung seluruh indikator harian
    rsi = hitung_rsi(close)
    ma20 = hitung_ma(close, 20)
    ma50 = hitung_ma(close, 50)
    macd, signal_line, _ = hitung_macd(close)
    k_line, d_line = hitung_stochastic(high, low, close)

    # Temukan indeks pertama di mana seluruh indikator penting terhitung (bukan NaN)
    start_idx = 0
    for i in range(len(df)):
        if not (
            pd.isna(ma50.iloc[i])
            or pd.isna(rsi.iloc[i])
            or pd.isna(macd.iloc[i])
            or pd.isna(k_line.iloc[i])
            or pd.isna(d_line.iloc[i])
        ):
            start_idx = i
            break
    if start_idx == 0:
        start_idx = min(50, len(df) - 1) if len(df) > 50 else 0

    capital = initial_capital
    shares = 0
    in_position = False
    buy_price = 0.0
    buy_date = None
    trades = []

    equity_history = []

    for i in range(start_idx, len(df)):
        buy_indicators = 0
        sell_indicators = 0

        # 1. RSI
        r_val = rsi.iloc[i]
        if r_val < 30:
            buy_indicators += 1
        elif r_val > 70:
            sell_indicators += 1

        # 2. MA Cross
        ma20_val = ma20.iloc[i]
        ma50_val = ma50.iloc[i]
        if ma20_val > ma50_val:
            buy_indicators += 1
        elif ma20_val < ma50_val:
            sell_indicators += 1

        # 3. MACD
        m_val = macd.iloc[i]
        s_val = signal_line.iloc[i]
        if m_val > s_val:
            buy_indicators += 1
        elif m_val < s_val:
            sell_indicators += 1

        # 4. Stochastic
        st_k = k_line.iloc[i]
        st_d = d_line.iloc[i]
        if st_k < 20 and st_k > st_d:
            buy_indicators += 1
        elif st_k > 80 and st_k < st_d:
            sell_indicators += 1

        # Aturan sederhana: beli/jual hanya kalau minimal ada 2 tanda yang searah
        daily_signal = "HOLD"
        if buy_indicators >= 2 and sell_indicators == 0:
            daily_signal = "BUY"
        elif sell_indicators >= 2 and buy_indicators == 0:
            daily_signal = "SELL"

        close_price = float(df["Close"].iloc[i])

        # Eksekusi Simulasi Transaksi (LONG)
        if not in_position and daily_signal == "BUY":
            lot_saham = int(capital // (close_price * 100))
            if lot_saham > 0:
                shares = lot_saham * 100
                buy_price = close_price
                buy_date = df.index[i]
                capital -= shares * buy_price
                in_position = True
        elif in_position and daily_signal == "SELL":
            sell_price = close_price
            revenue = shares * sell_price
            capital += revenue
            profit_loss_pct = ((sell_price - buy_price) / buy_price) * 100
            profit_loss_rp = revenue - (shares * buy_price)

            trades.append(
                {
                    "tanggal_beli": buy_date,
                    "tanggal_jual": df.index[i],
                    "harga_beli": buy_price,
                    "harga_jual": sell_price,
                    "return_pct": profit_loss_pct,
                    "profit_rp": profit_loss_rp,
                    "lembar": shares,
                }
            )
            shares = 0
            in_position = False

        # Rekam ekuitas harian
        current_equity = capital + (shares * close_price if in_position else 0)
        equity_history.append(current_equity)

    # Valuasi Portofolio Terakhir
    final_close = float(df["Close"].iloc[-1])
    final_equity = capital + (shares * final_close if in_position else 0)

    total_return = ((final_equity / initial_capital) - 1) * 100

    start_price = float(df["Close"].iloc[start_idx]) if len(df) > start_idx else 1.0
    benchmark_return = ((final_close / start_price) - 1) * 100

    profit_trades = [t for t in trades if t["return_pct"] > 0]
    win_rate = (len(profit_trades) / len(trades)) * 100 if len(trades) > 0 else 0.0

    max_dd = 0.0
    if equity_history:
        eq_series = pd.Series(equity_history)
        peaks = eq_series.cummax()
        drawdowns = (eq_series - peaks) / peaks * 100
        max_dd = float(drawdowns.min())

    return {
        "total_return": total_return,
        "benchmark_return": benchmark_return,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "final_value": final_equity,
        "total_trades": len(trades),
        "trades": trades,
        "initial_capital": initial_capital,
    }
