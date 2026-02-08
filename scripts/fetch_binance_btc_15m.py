import requests
import time
import pandas as pd

BASE_URL = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 1000  # max per request

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

def fetch_all_klines(start_time_ms: int | None = None):
    all_rows = []
    while True:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "limit": LIMIT,
        }
        if start_time_ms:
            params["startTime"] = start_time_ms

        r = requests.get(BASE_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data:
            break

        all_rows.extend(data)
        start_time_ms = data[-1][0] + 1

        # be nice to API
        time.sleep(0.1)

        if len(data) < LIMIT:
            break

    return pd.DataFrame(all_rows, columns=COLUMNS)


if __name__ == "__main__":
    df = fetch_all_klines()
    df.to_csv(
        "src/flare_ai_defai/crash_detection_system/data/btc_15m_data.csv",
        index=False,
        header=True,
    )
    print(f"Saved {len(df)} rows")
