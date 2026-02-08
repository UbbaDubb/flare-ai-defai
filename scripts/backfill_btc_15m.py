from flare_ai_defai.market_data.binance import backfill_history

out_path = "src/flare_ai_defai/crash_detection_system/data/btc_15m_data.csv"

df = backfill_history(symbol="BTCUSDT", interval="15m")
df.to_csv(out_path, index=False)

print("Saved rows:", len(df))
