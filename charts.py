import matplotlib.pyplot as plt
import mplfinance as mpf
import mplfinance._utils as mpf_utils
import numpy as np
import pandas as pd


# Monkey-patch untuk memperbaiki bug internal KeyError di mplfinance pada Pandas 2.0+ (Issue #686)
def patched_calculate_atr(atr_length, highs, lows, closes):
    if atr_length < 1:
        raise ValueError("Specified atr_length may not be less than 1")
    elif atr_length >= len(closes):
        raise ValueError(
            "Specified atr_length is larger than the length of the dataset: "
            + str(len(closes))
        )

    # Konversi Series ke Numpy Array agar aman dari KeyError index non-integer di Pandas baru
    if hasattr(highs, "values"):
        highs = highs.values
    if hasattr(lows, "values"):
        lows = lows.values
    if hasattr(closes, "values"):
        closes = closes.values

    atr = 0
    for i in range(len(highs) - atr_length, len(highs)):
        high = highs[i]
        low = lows[i]
        close_prev = closes[i - 1]
        tr = max(abs(high - low), abs(high - close_prev), abs(low - close_prev))
        atr += tr
    return atr / atr_length


mpf_utils._calculate_atr = patched_calculate_atr

from indicators import (
    hitung_atr,
    hitung_bollinger,
    hitung_ma,
    hitung_macd,
    hitung_obv,
    hitung_rsi,
    hitung_stochastic,
)


def buat_candlestick(
    df: pd.DataFrame,
    ticker: str,
    show_ma20: bool,
    show_ma50: bool,
    show_bb: bool,
    tipe_grafik: str = "candle",
    show_regression: bool = False,
) -> plt.Figure:
    # Warna utama grafik: hijau untuk naik, merah untuk turun
    mc = mpf.make_marketcolors(
        up="#00e676",
        down="#ff1744",
        edge={"up": "#00e676", "down": "#ff1744"},
        wick={"up": "#00e676", "down": "#ff1744"},
        volume={"up": "#00e676", "down": "#ff1744"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        base_mpf_style="nightclouds",
        gridcolor="#121212",
        gridstyle="-",
        figcolor="#000000",
        facecolor="#000000",
        edgecolor="#222222",
        rc={
            "font.size": 8,
            "axes.labelcolor": "#ffa500",  # Amber
            "xtick.color": "#8b949e",
            "ytick.color": "#8b949e",
        },
    )

    # 1. Penanganan Heikin-Ashi (Kalkulasi Lilin Tren Halus)
    if tipe_grafik == "heikin_ashi":
        df_plot = df.copy()
        ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0

        ha_open = np.zeros(len(df))
        ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2.0

        df_plot["Close"] = ha_close
        df_plot["Open"] = ha_open
        df_plot["High"] = np.maximum(np.maximum(df["High"], ha_open), ha_close)
        df_plot["Low"] = np.minimum(np.minimum(df["Low"], ha_open), ha_close)
        tipe_plot = "candle"
    else:
        df_plot = df
        tipe_plot = tipe_grafik

    addplots = []
    # 2. Garis rata-rata harga 20 hari
    if show_ma20 and tipe_grafik not in ["renko", "pnf"]:
        ma20 = hitung_ma(df["Close"], 20)
        if not ma20.isnull().all():
            addplots.append(
                mpf.make_addplot(ma20, color="#ffa500", width=1.4)
            )  # Core line
            addplots.append(
                mpf.make_addplot(ma20, color="#ffa500", width=3.5, alpha=0.25)
            )  # Inner glow
            addplots.append(
                mpf.make_addplot(ma20, color="#ffa500", width=7.0, alpha=0.10)
            )  # Outer glow

    # 3. Garis rata-rata harga 50 hari
    if show_ma50 and tipe_grafik not in ["renko", "pnf"]:
        ma50 = hitung_ma(df["Close"], 50)
        if not ma50.isnull().all():
            addplots.append(
                mpf.make_addplot(ma50, color="#00ffff", width=1.4)
            )  # Core line
            addplots.append(
                mpf.make_addplot(ma50, color="#00ffff", width=3.5, alpha=0.25)
            )  # Inner glow
            addplots.append(
                mpf.make_addplot(ma50, color="#00ffff", width=7.0, alpha=0.10)
            )  # Outer glow

    # 4. Batas atas/bawah harga
    if show_bb and tipe_grafik not in ["renko", "pnf"]:
        upper, mid, lower = hitung_bollinger(df["Close"])
        if (
            not upper.isnull().all()
            and not mid.isnull().all()
            and not lower.isnull().all()
        ):
            # Upper Band (Magenta)
            addplots.append(
                mpf.make_addplot(upper, color="#ff00ff", width=1.0, linestyle="--")
            )
            addplots.append(
                mpf.make_addplot(
                    upper, color="#ff00ff", width=3.0, alpha=0.15, linestyle="--"
                )
            )
            # Mid Band (Soft Magenta)
            addplots.append(
                mpf.make_addplot(mid, color="#ff00ff", width=0.8, linestyle=":")
            )
            # Lower Band (Magenta)
            addplots.append(
                mpf.make_addplot(lower, color="#ff00ff", width=1.0, linestyle="--")
            )
            addplots.append(
                mpf.make_addplot(
                    lower, color="#ff00ff", width=3.0, alpha=0.15, linestyle="--"
                )
            )

    # 5. Garis bantu arah harga
    if show_regression and tipe_grafik not in ["renko", "pnf"]:
        x = np.arange(len(df_plot))
        y = df_plot["Close"].values
        if len(y) > 1:
            slope, intercept = np.polyfit(x, y, 1)
            reg_line = slope * x + intercept
            residuals = y - reg_line
            std_dev = np.std(residuals)
            upper_reg = reg_line + 2 * std_dev
            lower_reg = reg_line - 2 * std_dev

            reg_series = pd.Series(reg_line, index=df_plot.index)
            upper_series = pd.Series(upper_reg, index=df_plot.index)
            lower_series = pd.Series(lower_reg, index=df_plot.index)

            # Tengah (Cyan)
            addplots.append(mpf.make_addplot(reg_series, color="#00ffff", width=1.4))
            addplots.append(
                mpf.make_addplot(reg_series, color="#00ffff", width=3.5, alpha=0.20)
            )
            # Atas (+2 SD - Magenta)
            addplots.append(
                mpf.make_addplot(
                    upper_series, color="#ff00ff", width=1.0, linestyle="--"
                )
            )
            addplots.append(
                mpf.make_addplot(
                    upper_series, color="#ff00ff", width=3.0, alpha=0.15, linestyle="--"
                )
            )
            # Bawah (-2 SD - Hijau)
            addplots.append(
                mpf.make_addplot(
                    lower_series, color="#00e676", width=1.0, linestyle="--"
                )
            )
            addplots.append(
                mpf.make_addplot(
                    lower_series, color="#00e676", width=3.0, alpha=0.15, linestyle="--"
                )
            )

    kwargs = dict(
        type=tipe_plot,
        style=style,
        figsize=(13, 6),
        returnfig=True,
        tight_layout=True,
        ylabel="Harga (Rp)",
    )

    # Proteksi: Grafik non-kronologis (Renko, P&F) tidak mendukung volume & overlay secara matematis
    if tipe_grafik not in ["renko", "pnf"]:
        kwargs["volume"] = True
        kwargs["ylabel_lower"] = "Volume"
        if addplots:
            kwargs["addplot"] = addplots
    else:
        kwargs["volume"] = False

    fig, axes = mpf.plot(df_plot, **kwargs)
    fig.patch.set_facecolor("#000000")

    # Legenda manual jika garis bantu ditampilkan
    legend_items = []
    if tipe_grafik not in ["renko", "pnf"]:
        if show_ma20 and "ma20" in locals() and not ma20.isnull().all():
            legend_items.append(
                plt.Line2D(
                    [0], [0], color="#ffa500", linewidth=1.5, label="MA20 (Glow)"
                )
            )
        if show_ma50 and "ma50" in locals() and not ma50.isnull().all():
            legend_items.append(
                plt.Line2D(
                    [0], [0], color="#00ffff", linewidth=1.5, label="MA50 (Glow)"
                )
            )
        if show_bb and "upper" in locals() and not upper.isnull().all():
            legend_items.append(
                plt.Line2D(
                    [0],
                    [0],
                    color="#ff00ff",
                    linewidth=1.0,
                    linestyle="--",
                    label="Bollinger Bands",
                )
            )
        if show_regression and "reg_series" in locals():
            legend_items.append(
                plt.Line2D(
                    [0], [0], color="#00ffff", linewidth=1.5, label="Regresi (Tengah)"
                )
            )
            legend_items.append(
                plt.Line2D(
                    [0],
                    [0],
                    color="#ff00ff",
                    linewidth=1.0,
                    linestyle="--",
                    label="Regresi +2 SD (Atas)",
                )
            )
            legend_items.append(
                plt.Line2D(
                    [0],
                    [0],
                    color="#00e676",
                    linewidth=1.0,
                    linestyle="--",
                    label="Regresi -2 SD (Bawah)",
                )
            )

        if legend_items:
            axes[0].legend(
                handles=legend_items,
                loc="upper left",
                fontsize=8,
                labelcolor="#ffffff",
                framealpha=0.5,
                facecolor="#080808",
                edgecolor="#333333",
            )

    label_tipe = {
        "candle": "Candlestick",
        "line": "Garis",
        "ohlc": "OHLC",
        "heikin_ashi": "Heikin-Ashi",
        "renko": "Renko",
        "pnf": "Point & Figure",
    }.get(tipe_grafik, "Utama")
    axes[0].set_title(
        f"{ticker} -- Grafik Harga ({label_tipe})",
        color="#ffa500",
        fontsize=11,
        loc="left",
        pad=8,
        fontweight="bold",
    )
    return fig


def buat_rsi_chart(df: pd.DataFrame) -> plt.Figure:
    rsi = hitung_rsi(df["Close"])
    fig, ax = plt.subplots(figsize=(13, 2.8), facecolor="#000000")
    ax.set_facecolor("#000000")

    # Garis RSI dengan efek pendar neon amber
    ax.plot(df.index, rsi, color="#ffa500", linewidth=1.5, label="RSI(14)")
    ax.plot(df.index, rsi, color="#ffa500", linewidth=3.5, alpha=0.25)
    ax.plot(df.index, rsi, color="#ffa500", linewidth=7.0, alpha=0.10)

    # Batas Jenuh Beli & Jual
    ax.axhline(
        70, color="#ff1744", linewidth=1.0, linestyle="--", alpha=0.8
    )  # Neon Rose
    ax.axhline(
        30, color="#00e676", linewidth=1.0, linestyle="--", alpha=0.8
    )  # Neon Green
    ax.axhline(50, color="#333333", linewidth=0.8, linestyle=":", alpha=0.6)

    # Area isi pendar transparan untuk area ekstrim
    ax.fill_between(df.index, rsi, 70, where=(rsi >= 70), alpha=0.15, color="#ff1744")
    ax.fill_between(df.index, rsi, 30, where=(rsi <= 30), alpha=0.15, color="#00e676")

    ax.set_ylim(0, 100)
    ax.text(
        df.index[-1],
        72,
        "Mulai terlalu ramai dibeli (70)",
        color="#ff1744",
        fontsize=7.5,
        ha="right",
        va="bottom",
        fontweight="bold",
    )
    ax.text(
        df.index[-1],
        28,
        "Mulai banyak dijual (30)",
        color="#00e676",
        fontsize=7.5,
        ha="right",
        va="top",
        fontweight="bold",
    )
    ax.set_ylabel("RSI", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.set_title(
        "RSI -- Cek apakah harga mulai terlalu mahal atau murah",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)

    plt.tight_layout()
    return fig


def buat_macd_chart(df: pd.DataFrame) -> plt.Figure:
    macd_line, signal_line, histogram = hitung_macd(df["Close"])
    # Cyber neon bar colors
    colors = ["#00e676" if v >= 0 else "#ff1744" for v in histogram]

    fig, ax = plt.subplots(figsize=(13, 2.8), facecolor="#000000")
    ax.set_facecolor("#000000")

    # MACD Histogram dengan pendar
    ax.bar(df.index, histogram, color=colors, alpha=0.45, width=0.8, label="Histogram")

    # Garis MACD (Cyan) & Sinyal (Amber) dengan pendar
    ax.plot(df.index, macd_line, color="#00ffff", linewidth=1.4, label="MACD(12,26)")
    ax.plot(df.index, macd_line, color="#00ffff", linewidth=3.5, alpha=0.25)

    ax.plot(df.index, signal_line, color="#ffa500", linewidth=1.4, label="Signal(9)")
    ax.plot(df.index, signal_line, color="#ffa500", linewidth=3.5, alpha=0.25)

    ax.axhline(0, color="#333333", linewidth=0.8)

    ax.set_ylabel("MACD", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.set_title(
        "MACD -- Cek perubahan tenaga naik/turun",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    ax.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
    )

    plt.tight_layout()
    return fig


def buat_compare_chart(tickers: list[str], dfs: list[pd.DataFrame]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(13, 4.5), facecolor="#000000")
    ax.set_facecolor("#000000")

    # Warna pembeda untuk maksimal 5 saham
    colors = ["#00ffff", "#00e676", "#ff00ff", "#ffa500", "#ff1744"]

    for df, ticker, color in zip(dfs, tickers, colors):
        # Tentukan basis awal yang valid (bukan NaN dan bukan nol)
        first_close = df["Close"].iloc[0]
        if pd.isna(first_close) or first_close == 0:
            valid_closes = df["Close"].dropna()
            first_close = valid_closes.iloc[0] if len(valid_closes) > 0 else 1.0

        norm = (df["Close"] / float(first_close)) * 100

        # Garis dengan efek pendar neon ganda
        ax.plot(df.index, norm, color=color, linewidth=1.6, label=ticker)
        ax.plot(df.index, norm, color=color, linewidth=3.5, alpha=0.20)
        ax.plot(df.index, norm, color=color, linewidth=7.0, alpha=0.08)

    ax.axhline(
        100, color="#8b949e", linewidth=0.8, linestyle="--", alpha=0.5
    )  # Base line
    ax.set_ylabel("Perubahan (%)", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.legend(
        fontsize=9,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
        loc="upper left",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    ax.set_title(
        "Perbandingan Perubahan Harga (awal disamakan = 100)",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    plt.tight_layout()
    return fig


def buat_volatilitas_chart(df: pd.DataFrame, ticker: str) -> plt.Figure:
    returns = df["Close"].pct_change().dropna()
    rolling_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100

    fig, axes = plt.subplots(2, 1, figsize=(13, 5), facecolor="#000000", sharex=True)
    fig.subplots_adjust(hspace=0.08)

    ax1 = axes[0]
    ax1.set_facecolor("#000000")
    colors = ["#00e676" if v >= 0 else "#ff1744" for v in returns]
    ax1.bar(returns.index, returns * 100, color=colors, alpha=0.6, width=0.8)
    ax1.set_ylabel("Naik/Turun Harian (%)", color="#ffa500", fontsize=9)
    ax1.set_title(
        f"{ticker} -- Naik-Turun Harga Harian dan Gerak 20 Hari",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )
    ax1.tick_params(colors="#8b949e", labelsize=8)
    ax1.axhline(0, color="#333333", linewidth=0.8)

    for spine in ax1.spines.values():
        spine.set_color("#222222")
    ax1.grid(color="#121212", linestyle="-", linewidth=0.8)

    ax2 = axes[1]
    ax2.set_facecolor("#000000")
    # Garis besarnya gerak harga
    ax2.plot(
        rolling_vol.index,
        rolling_vol,
        color="#ffa500",
        linewidth=1.5,
        label="Besarnya gerak harga 20 hari",
    )
    ax2.plot(rolling_vol.index, rolling_vol, color="#ffa500", linewidth=3.5, alpha=0.25)
    ax2.plot(rolling_vol.index, rolling_vol, color="#ffa500", linewidth=7.0, alpha=0.10)

    ax2.fill_between(rolling_vol.index, rolling_vol, alpha=0.08, color="#ffa500")
    ax2.set_ylabel("Gerak Harga (%)", color="#ffa500", fontsize=9)
    ax2.tick_params(colors="#8b949e", labelsize=8)
    ax2.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
    )

    for spine in ax2.spines.values():
        spine.set_color("#222222")
    ax2.grid(color="#121212", linestyle="-", linewidth=0.8)

    plt.tight_layout()
    return fig


def buat_stochastic_chart(df: pd.DataFrame) -> plt.Figure:
    k_line, d_line = hitung_stochastic(df["High"], df["Low"], df["Close"])
    fig, ax = plt.subplots(figsize=(13, 2.8), facecolor="#000000")
    ax.set_facecolor("#000000")

    # Garis %K (Amber) dengan pendar
    ax.plot(df.index, k_line, color="#ffa500", linewidth=1.4, label="%K (Cepat)")
    ax.plot(df.index, k_line, color="#ffa500", linewidth=3.5, alpha=0.20)

    # Garis %D (Cyan) dengan pendar
    ax.plot(df.index, d_line, color="#00ffff", linewidth=1.4, label="%D (Lambat)")
    ax.plot(df.index, d_line, color="#00ffff", linewidth=3.5, alpha=0.20)

    # Batas Jenuh
    ax.axhline(80, color="#ff1744", linewidth=1.0, linestyle="--", alpha=0.8)
    ax.axhline(20, color="#00e676", linewidth=1.0, linestyle="--", alpha=0.8)

    # Area pendar ekstrim
    ax.fill_between(
        df.index, k_line, 80, where=(k_line >= 80), alpha=0.15, color="#ff1744"
    )
    ax.fill_between(
        df.index, k_line, 20, where=(k_line <= 20), alpha=0.15, color="#00e676"
    )

    ax.set_ylim(-5, 105)
    ax.set_ylabel("Stochastic", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.set_title(
        "Stochastic -- Cek tanda harga mulai berbalik",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    ax.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
    )

    plt.tight_layout()
    return fig


def buat_obv_chart(df: pd.DataFrame) -> plt.Figure:
    obv = hitung_obv(df["Close"], df["Volume"])
    fig, ax = plt.subplots(figsize=(13, 2.8), facecolor="#000000")
    ax.set_facecolor("#000000")

    # OBV dengan pendar neon lime-green
    ax.plot(
        df.index, obv, color="#00e676", linewidth=1.5, label="OBV (Volume Laju Saldo)"
    )
    ax.plot(df.index, obv, color="#00e676", linewidth=3.5, alpha=0.25)
    ax.plot(df.index, obv, color="#00e676", linewidth=7.0, alpha=0.10)

    ax.fill_between(df.index, obv, alpha=0.08, color="#00e676")

    ax.set_ylabel("Volume Kumulatif", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.set_title(
        "OBV -- Cek apakah volume mendukung arah harga",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    ax.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
    )

    plt.tight_layout()
    return fig


def buat_atr_chart(df: pd.DataFrame) -> plt.Figure:
    atr = hitung_atr(df["High"], df["Low"], df["Close"])
    fig, ax = plt.subplots(figsize=(13, 2.8), facecolor="#000000")
    ax.set_facecolor("#000000")

    # ATR dengan pendar neon magenta
    ax.plot(df.index, atr, color="#ff00ff", linewidth=1.5, label="ATR(14)")
    ax.plot(df.index, atr, color="#ff00ff", linewidth=3.5, alpha=0.25)
    ax.plot(df.index, atr, color="#ff00ff", linewidth=7.0, alpha=0.10)

    ax.fill_between(df.index, atr, alpha=0.08, color="#ff00ff")

    ax.set_ylabel("Lebar Gerak Harga (Rp)", color="#ffa500", fontsize=9)
    ax.tick_params(colors="#8b949e", labelsize=8)
    ax.set_title(
        "ATR -- Seberapa lebar harga bergerak",
        color="#ffa500",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    ax.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333",
    )

    plt.tight_layout()
    return fig


def buat_financial_chart(df_fin: pd.DataFrame, ticker: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(13, 4.5), facecolor="#000000")
    ax.set_facecolor("#000000")
    
    # Indeks adalah tanggal laporan (biasanya datetime). Format ke Tahun.
    years = [str(date)[:4] for date in df_fin.index]
    
    raw_rev = df_fin["Revenue"]
    raw_net = df_fin["Net_Income"]
    
    # Cari nilai maksimum untuk menentukan skala
    max_val = max(raw_rev.abs().max(), raw_net.abs().max())
    if max_val >= 1e12:
        divisor = 1e12
        unit = "Rp Triliun"
    elif max_val >= 1e9:
        divisor = 1e9
        unit = "Rp Miliar"
    else:
        divisor = 1.0
        unit = "Rupiah"
        
    revenue = raw_rev / divisor
    net_income = raw_net / divisor
    
    x = np.arange(len(years))
    width = 0.35
    
    # Bar Chart dengan warna neon orange dan hijau
    rects1 = ax.bar(x - width/2, revenue, width, label="Pendapatan (Revenue)", color="#ffa500", alpha=0.85)
    rects2 = ax.bar(x + width/2, net_income, width, label="Laba Bersih (Net Income)", color="#00e676", alpha=0.85)
    
    # Tambahkan angka di atas setiap bar
    for r in rects1:
        h = r.get_height()
        sign = 1 if h >= 0 else -1
        offset = 3 if h >= 0 else -10
        ax.annotate(f"{h:.1f}",
                    xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, offset),  # 3 points vertical offset
                    textcoords="offset points",
                    ha="center", va="bottom" if h >= 0 else "top", color="#ffa500", fontsize=7.5)
                    
    for r in rects2:
        h = r.get_height()
        sign = 1 if h >= 0 else -1
        offset = 3 if h >= 0 else -10
        ax.annotate(f"{h:.1f}",
                    xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, offset),
                    textcoords="offset points",
                    ha="center", va="bottom" if h >= 0 else "top", color="#00e676", fontsize=7.5)
    
    ax.set_ylabel(f"Nilai ({unit})", color="#ffa500", fontsize=9)
    ax.set_title(f"{ticker} -- Tren Laporan Keuangan Tahunan (Revenue vs Net Income)", color="#ffa500", fontsize=11, fontweight="bold", loc="left", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.tick_params(colors="#8b949e", labelsize=8)
    
    for spine in ax.spines.values():
        spine.set_color("#222222")
    ax.grid(color="#121212", linestyle="-", linewidth=0.8)
    
    ax.legend(
        loc="upper left",
        fontsize=8,
        labelcolor="#ffffff",
        framealpha=0.5,
        facecolor="#080808",
        edgecolor="#333333"
    )
    
    plt.tight_layout()
    return fig
