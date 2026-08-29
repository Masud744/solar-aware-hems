#!/usr/bin/env python3
"""Seed 200 recent hourly sensor readings up to the current date/time into Supabase.

This enables the Load Prediction Random Forest model (which requires 168h of
historical sensor readings for lags: power_lag_1..power_lag_168 and rolling windows)
to operate even when the ESP32 hardware is not physically streaming live readings.
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.database import get_supabase

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOAD_DATA_PATH = os.path.join(PROJECT_ROOT, "ml", "load", "data", "load_processed_clean.csv")

DEVICE_ID = "simulated_buffer"
SEED_HOURS = 200


def main():
    print("=" * 60)
    print("SEEDING RECENT HOURLY SENSOR READINGS (UP TO CURRENT TIME)")
    print("=" * 60)

    # Load representative UCI load profiles
    print(f"Loading: {LOAD_DATA_PATH}")
    df = pd.read_csv(LOAD_DATA_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    
    # Pick a contiguous 200-hour slice from test set
    test_start = pd.Timestamp("2010-01-27 19:00:00")
    start_idx = df[df["DateTime"] >= test_start].index[0]
    sample_block = df.iloc[start_idx : start_idx + SEED_HOURS].copy().reset_index(drop=True)

    # Align timestamps to end at the current hour
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = now - timedelta(hours=SEED_HOURS - 1)

    rows = []
    for i, row in sample_block.iterrows():
        ts_i = start_time + timedelta(hours=i)
        rows.append({
            "device_id": DEVICE_ID,
            "ts": ts_i.isoformat(),
            "voltage_v": round(float(row["Voltage"]), 2),
            "current_a": round(float(row["Global_intensity"]), 2),
            "power_w": round(float(row["Global_active_power"]) * 1000, 2),
            "temperature_c": round(float(row["T2M"]), 2),
        })

    sb = get_supabase()
    print(f"\nInserting {len(rows)} rows into sensor_readings from {rows[0]['ts']} to {rows[-1]['ts']}...")

    # Insert in batches
    batch_size = 50
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = sb.table("sensor_readings").upsert(batch).execute()
        inserted += len(result.data)
        print(f"  Batch {i // batch_size + 1}: {len(result.data)} rows inserted/upserted")

    print(f"\n✓ Successfully seeded {inserted} recent sensor rows.")
    print("  Load RF model now has complete lag history for current live predictions!")


if __name__ == "__main__":
    main()
