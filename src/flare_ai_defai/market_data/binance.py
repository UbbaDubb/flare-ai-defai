from __future__ import annotations
import time
import requests
import pandas as pd

BINANCE_URL = "https://api.binance.com/api/v3/klines"

COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

def fetch_klines(
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 1000,
) -> pd.DataFrame:
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    if start_time_ms is not None:
        params["startTime"] = int(start_time_ms)
    if end_time_ms is not None:
        params["endTime"] = int(end_time_ms)

    r = requests.get(BINANCE_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if not data:
        return pd.DataFrame(columns=COLUMNS)

    return pd.DataFrame(data, columns=COLUMNS)


def update_latest(
    df: pd.DataFrame,
    symbol: str = "BTCUSDT",
    interval: str = "15m",
) -> pd.DataFrame:
    last_open = int(df["open_time"].iloc[-1])
    new = fetch_klines(symbol, interval, last_open + 1)
    if not new.empty:
        df = pd.concat([df, new], ignore_index=True)
        df = (
            df.drop_duplicates("open_time")
              .sort_values("open_time")
              .reset_index(drop=True)
        )
    return df

def backfill_history(
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    max_batches: int | None = None,  # safety
) -> pd.DataFrame:
    """
    Backfill full historical klines by paging BACKWARDS using endTime.
    """
    all_frames: list[pd.DataFrame] = []
    end_time_ms: int | None = None
    batches = 0

    while True:
        df = fetch_klines(
            symbol=symbol,
            interval=interval,
            end_time_ms=end_time_ms,
            limit=1000,
        )

        if df.empty:
            break

        all_frames.append(df)

        # move window backwards: set endTime just before the earliest candle we got
        end_time_ms = int(df["open_time"].iloc[0]) - 1
        batches += 1

        time.sleep(0.15)

        if len(df) < 1000:
            break
        if max_batches and batches >= max_batches:
            break

    return (
        pd.concat(all_frames, ignore_index=True)
        .drop_duplicates("open_time")
        .sort_values("open_time")
        .reset_index(drop=True)
    )
