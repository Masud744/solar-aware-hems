#!/usr/bin/env python3
"""Seed 200 test rows into Supabase sensor_readings.

This script inserts 200 consecutive hourly rows from the UCI load dataset's
test-set portion into the Supabase sensor_readings table for Phase 5
integration testing ONLY.

These rows are labeled with device_id="seed_test_data" to distinguish
them from future real ESP32 sensor data.

DO NOT use this data for:
- Model retraining
- Model evaluation / reported performance metrics
- Phase 6 hardware validation
"""

import os
import sys
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.database import get_supabase

# Project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOAD_DATA_PATH = os.path.join(PROJECT_ROOT, "ml", "load", "data", "load_processed_clean.csv")

DEVICE_ID = "seed_test_data"
SEED_START_IDX = None  # Will be computed from test set start
SEED_COUNT = 200


def main():
    print("=" * 60)
    print("SEED TEST DATA INSERTION")
    print("=" * 60)

    # Load the processed data
    print(f"\nLoading: {LOAD_DATA_PATH}")
    df = pd.read_csv(LOAD_DATA_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])

    # Find test set start (chronological split — same as Phase 2)
    test_start = pd.Timestamp("2010-01-27 19:00:00")
    start_idx = df[df["DateTime"] >= test_start].index[0]

    seed_block = df.iloc[start_idx : start_idx + SEED_COUNT].copy()
    print(f"Seed block: {seed_block['DateTime'].iloc[0]} to {seed_block['DateTime'].iloc[-1]}")
    print(f"Rows: {len(seed_block)}")

    # Verify no gaps
    diffs = seed_block["DateTime"].diff().dt.total_seconds() / 3600
    gaps = (diffs > 1.5).sum()
    print(f"Gaps > 1h: {gaps}")
    assert gaps == 0, "Seed block has gaps!"

    # Build sensor_readings rows
    rows = []
    for _, row in seed_block.iterrows():
        rows.append({
            "device_id": DEVICE_ID,
            "ts": row["DateTime"].isoformat(),
            "voltage_v": round(float(row["Voltage"]), 2),
            "current_a": round(float(row["Global_intensity"]), 2),
            "power_w": round(float(row["Global_active_power"]) * 1000, 2),  # kW → W
            "temperature_c": round(float(row["T2M"]), 2),
        })

    # Insert into Supabase
    sb = get_supabase()
    print(f"\nInserting {len(rows)} rows into sensor_readings (device_id='{DEVICE_ID}')...")

    # Insert in batches of 50
    batch_size = 50
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = sb.table("sensor_readings").insert(batch).execute()
        inserted += len(result.data)
        print(f"  Batch {i // batch_size + 1}: {len(result.data)} rows inserted")

    print(f"\nTotal inserted: {inserted}")
    print(f"Timestamp range: {rows[0]['ts']} to {rows[-1]['ts']}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"\nAll seed data is labeled with device_id='{DEVICE_ID}'")
    print(f"Real ESP32 data (Phase 6+) will use a different device_id.")

    # Verify lag coverage for the last 32 rows (predictable targets)
    print("\n--- Lag Coverage Verification ---")
    last_ts = pd.Timestamp(rows[-1]["ts"])
    lag_offsets = [1, 2, 3, 12, 24, 48, 168]
    all_ts = {r["ts"] for r in rows}

    for offset in lag_offsets:
        needed = (last_ts - pd.Timedelta(hours=offset)).isoformat()
        found = needed in all_ts
        print(f"  lag_{offset}: {needed} — {'✅ FOUND' if found else '❌ MISSING'}")

    print("\n✓ Seed data insertion complete.")


if __name__ == "__main__":
    main()
