#!/usr/bin/env python3

"""
Build BTC/USD market snapshot and write it to shared/latest_update.json.

This script is the ONLY writer of the snapshot JSON.
It uses deterministic outputs from RiskEngine (NO LLM).
"""
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from flare_ai_defai.crash_detection_system.integration import RiskAnalysisIntegration
from flare_ai_defai.crash_detection_system.types import RiskAppetite
from flare_ai_defai.flare.flare_price import get_btc_usd_price
from flare_ai_defai.market_data.binance import update_latest


# ---------- helpers ----------




def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_json(path: Path, payload: dict) -> None:
    """
    Atomically write JSON so readers never see a partial file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# ---------- main snapshot build ----------

def main() -> None:
    # Strict mode: FAIL if BTC data is missing (no dummy numbers)
    ri = RiskAnalysisIntegration(strict_data=True)

    # Refresh local BTC candles from Binance before analysis (keeps CSV up-to-date)
    csv_path = Path("src/flare_ai_defai/crash_detection_system/data/btc_15m_data.csv")
    df = pd.read_csv(csv_path)
    df = update_latest(df)
    df.to_csv(csv_path, index=False)

    # Reload integration so it uses the refreshed file (simple + safe)
    ri = RiskAnalysisIntegration(strict_data=True)


    # Live price from Flare (FTSOv2), fallback to CSV close for demo resilience
    try:
        flare_px = get_btc_usd_price()
        current_price = float(flare_px.price)
        price_source = "flare-ftso-v2"
        price_timestamp = flare_px.timestamp
    except Exception:
        current_price = float(ri.data["close"].iloc[-1])
        price_source = "btc_15m_data.csv"
        price_timestamp = None


    # Deterministic demo defaults
    horizon_hours = 24
    risk_profile = RiskAppetite.MEDIUM

    # Run deterministic risk analysis
    result = ri.analyze_for_snapshot(
        risk_appetite=risk_profile,
        horizon_hours=horizon_hours,
    )

    snapshot = {
        "timestamp": now_iso(),
        "asset": "BTC-USD",
        "price": current_price,
        "price_source": price_source,        # "flare-ftso-v2" or fallback
        "price_timestamp": price_timestamp,  # oracle timestamp
        "risk": ri.to_snapshot_dict(
        result,
        risk_profile,
        horizon_hours,
        ),
    }


    out_path = Path("shared/latest_update.json")
    atomic_write_json(out_path, snapshot)

    print("✔ Wrote BTC snapshot to", out_path.resolve())


if __name__ == "__main__":
    main()
