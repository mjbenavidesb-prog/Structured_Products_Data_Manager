import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Map from internal ticker names to yfinance symbols
TICKER_MAP = {
    "SPX": "^GSPC",
    "SX5E": "^STOXX50E",
    "NDX": "^NDX",
    "RTY": "^RUT",
    "INDU Index": "^DJI",
    "INDU": "^DJI",
    "SX7E": "^SX7E",
    "EAFE": "EFA",
    "CDX HY S37": None,  # credit index, not available in yfinance
}


def resolve_ticker(ticker: str) -> str | None:
    if not ticker or pd.isna(ticker) or str(ticker).strip() == "":
        return None
    t = str(ticker).strip()
    return TICKER_MAP.get(t, t)


def get_current_price(ticker: str) -> float | None:
    yf_ticker = resolve_ticker(ticker)
    if not yf_ticker:
        return None
    try:
        data = yf.Ticker(yf_ticker)
        hist = data.history(period="5d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


def get_prices_batch(tickers: list[str]) -> dict:
    """Returns {original_ticker: price}"""
    unique = {t: resolve_ticker(t) for t in tickers if t and not pd.isna(t) and str(t).strip()}
    yf_tickers = [v for v in unique.values() if v]

    if not yf_tickers:
        return {}

    try:
        data = yf.download(yf_tickers, period="5d", auto_adjust=True, progress=False)
        if data.empty:
            return {}

        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]
            closes.columns = yf_tickers

        latest = closes.iloc[-1]

        result = {}
        for orig, yf_sym in unique.items():
            if yf_sym and yf_sym in latest.index:
                val = latest[yf_sym]
                result[orig] = round(float(val), 2) if not pd.isna(val) else None
            else:
                result[orig] = None
        return result
    except Exception:
        return {}


def get_historical_prices(ticker: str, period: str = "1y") -> pd.DataFrame:
    yf_ticker = resolve_ticker(ticker)
    if not yf_ticker:
        return pd.DataFrame()
    try:
        data = yf.Ticker(yf_ticker)
        hist = data.history(period=period)
        return hist[["Close"]].rename(columns={"Close": ticker})
    except Exception:
        return pd.DataFrame()


def get_correlation_matrix(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    resolved = {t: resolve_ticker(t) for t in tickers if t and not pd.isna(t)}
    yf_syms = [v for v in resolved.values() if v]
    if len(yf_syms) < 2:
        return pd.DataFrame()
    try:
        data = yf.download(yf_syms, period=period, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data
        returns = closes.pct_change().dropna()
        corr = returns.corr()
        # rename columns back to original tickers
        inv_map = {v: k for k, v in resolved.items()}
        corr = corr.rename(index=inv_map, columns=inv_map)
        return corr
    except Exception:
        return pd.DataFrame()


def refresh_product_spots(df_products: pd.DataFrame) -> dict:
    """
    Given the products dataframe, fetch current prices for all underlyings.
    Returns {product_id: {spot_1: val, spot_2: val, ...}}
    """
    all_tickers = set()
    for col in ["underlying_1", "underlying_2", "underlying_3", "underlying_4"]:
        if col in df_products.columns:
            all_tickers.update(df_products[col].dropna().unique())

    all_tickers = {t for t in all_tickers if t and str(t).strip() not in ("", "nan")}
    prices = get_prices_batch(list(all_tickers))

    updates = {}
    for _, row in df_products.iterrows():
        pid = row["id"]
        spot_updates = {}
        for i, col in enumerate(["underlying_1", "underlying_2", "underlying_3", "underlying_4"], 1):
            ticker = row.get(col)
            if ticker and str(ticker).strip() not in ("", "nan") and ticker in prices:
                new_price = prices[ticker]
                if new_price is not None:
                    spot_updates[f"spot_{i}"] = new_price
        if spot_updates:
            updates[pid] = spot_updates
    return updates
