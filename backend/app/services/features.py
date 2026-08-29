# Feature construction service — builds model input vectors from sensor_readings
#
# CRITICAL MATCHING RULES:
# 1. Lag timestamps: EXACT hourly match on live sensor readings when available.
# 2. Rolling windows: shift(1) semantics — windows cover [target-Nh-1, target-1h],
#    i.e., power(t-1) through power(t-N), never including the target hour itself.
# 3. rolling_std_24h uses ddof=1 (pandas default: sample standard deviation).
# 4. Feature vector order must EXACTLY match model.feature_names_in_.
# 5. Timezone convention: target_time arrives as naive local (Asia/Dhaka) datetime.
#    sensor_readings stores timestamps in UTC. This module converts between the two
#    so that lag lookup keys are always in naive local time.
# 6. Benchmark Profile Fallback: When live 168h history is incomplete (e.g. during lab/demo
#    runs where continuous 7-day mains logging is unavailable), missing lag and rolling
#    features are filled deterministically from the UCI benchmark conditional distribution
#    (grouped by month, day-of-week, hour). Live sensor readings always take precedence.
#    No synthetic rows are ever inserted into the Supabase database.

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.database import get_supabase

# Timezone constants — deployment location
LOCAL_TZ = ZoneInfo("Asia/Dhaka")
UTC_TZ = ZoneInfo("UTC")


class InsufficientHistoryError(Exception):
    """Raised when required historical sensor readings are missing and fallback is disabled."""
    pass


# Required lag offsets (hours before target)
LAG_OFFSETS = [1, 2, 3, 12, 24, 48, 168]

# Rolling window sizes (hours) — shift(1) means we use [target - N*h, target - 1h]
# which is power(t-1), power(t-2), ..., power(t-N)
ROLLING_WINDOWS = {
    "rolling_mean_3h": 3,
    "rolling_mean_24h": 24,
    "rolling_std_24h": 24,
    "rolling_mean_168h": 168,
}

# ── Load and Precompute Benchmark Profile Table ──────────────────────────
_BENCHMARK_PROFILE_TABLE = None
_BENCHMARK_OVERALL_MEAN = None

def _get_benchmark_profile():
    """Load and cache the deterministic UCI benchmark profile matrix."""
    global _BENCHMARK_PROFILE_TABLE, _BENCHMARK_OVERALL_MEAN
    if _BENCHMARK_PROFILE_TABLE is not None:
        return _BENCHMARK_PROFILE_TABLE, _BENCHMARK_OVERALL_MEAN

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    data_path = os.path.join(
        project_root, "ml", "load", "data", "load_processed_clean.csv"
    )

    if not os.path.exists(data_path):
        raise RuntimeError(
            f"Benchmark dataset not found at {data_path}. Cannot initialize fallback."
        )

    df = pd.read_csv(data_path)
    feature_cols = [
        "power_lag_1", "power_lag_2", "power_lag_3", "power_lag_12",
        "power_lag_24", "power_lag_48", "power_lag_168",
        "rolling_mean_3h", "rolling_mean_24h", "rolling_std_24h",
        "rolling_mean_168h",
    ]

    _BENCHMARK_PROFILE_TABLE = df.groupby(["month", "day_of_week", "hour"])[feature_cols].mean()
    _BENCHMARK_OVERALL_MEAN = df[feature_cols].mean()

    return _BENCHMARK_PROFILE_TABLE, _BENCHMARK_OVERALL_MEAN


def _query_sensor_readings(start_local: datetime, end_local: datetime) -> dict[str, float]:
    """Query sensor_readings from Supabase in [start_local, end_local] range.

    Args:
        start_local: Naive datetime in local (Asia/Dhaka) time — start of range.
        end_local:   Naive datetime in local (Asia/Dhaka) time — end of range.

    Returns:
        dict mapping naive-local ISO timestamp string (truncated to hour) → power_kw.
        Keys are in Asia/Dhaka local time so they match lag keys computed from
        the naive-local target_hour.
    """
    sb = get_supabase()

    # Convert naive local boundaries to UTC for the Supabase query,
    # because sensor_readings.ts is stored as timestamptz in UTC.
    start_utc = start_local.replace(tzinfo=LOCAL_TZ).astimezone(UTC_TZ)
    end_utc = end_local.replace(tzinfo=LOCAL_TZ).astimezone(UTC_TZ)

    start_str = start_utc.isoformat()
    end_str = end_utc.isoformat()

    result = (
        sb.table("sensor_readings")
        .select("ts, power_w")
        .eq("device_id", "esp32_main")
        .gte("ts", start_str)
        .lte("ts", end_str)
        .order("ts")
        .execute()
    )

    readings = {}
    for row in result.data:
        ts = row["ts"]
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00") if ts.endswith("Z") else ts)
        else:
            dt = ts

        # Convert UTC DB timestamp to local (Asia/Dhaka) time, then truncate to hour
        if dt.tzinfo is not None:
            dt_local = dt.astimezone(LOCAL_TZ)
        else:
            dt_local = dt.replace(tzinfo=UTC_TZ).astimezone(LOCAL_TZ)

        hour_key = dt_local.replace(minute=0, second=0, microsecond=0, tzinfo=None)
        key_str = hour_key.isoformat()

        power_w = row["power_w"]
        if power_w is not None:
            readings[key_str] = power_w / 1000.0  # W → kW

    return readings


def build_load_features(target_time: datetime, t2m: float) -> tuple[dict, dict]:
    """Build the complete 16-feature vector for the load RF model.

    Checks real sensor readings first. If any historical lag or rolling window is
    missing due to short live history (< 168h), deterministically falls back to
    conditional benchmark expectations derived from the UCI dataset.

    Args:
        target_time: The future hour to predict load for.
        t2m: Temperature at 2m (°C) for the target hour.

    Returns:
        tuple (features_dict, provenance_dict)
    """
    target_hour = target_time.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    profile_table, overall_mean = _get_benchmark_profile()

    m = target_hour.month
    dow = target_hour.weekday()
    h = target_hour.hour

    if (m, dow, h) in profile_table.index:
        profile_row = profile_table.loc[(m, dow, h)]
    else:
        profile_row = overall_mean

    # Query the 168-hour history window from Supabase
    window_start = target_hour - timedelta(hours=168)
    window_end = target_hour - timedelta(hours=1)
    readings = _query_sensor_readings(window_start, window_end)

    lag_values = {}
    real_lags = []
    benchmark_lags = []

    for offset in LAG_OFFSETS:
        lag_time = target_hour - timedelta(hours=offset)
        lag_key = lag_time.isoformat()
        col_name = f"power_lag_{offset}"

        if lag_key in readings:
            lag_values[col_name] = readings[lag_key]
            real_lags.append(col_name)
        else:
            # Deterministic benchmark fallback: conditional mean from UCI training distribution
            lag_values[col_name] = float(profile_row[col_name])
            benchmark_lags.append(col_name)

    # Rolling features: Compute from actual readings if complete, else fallback
    rolling_values = {}
    real_rolling = []
    benchmark_rolling = []

    for feature_name, window_size in ROLLING_WINDOWS.items():
        window_vals = []
        for step in range(1, window_size + 1):
            val_time = target_hour - timedelta(hours=step)
            val_key = val_time.isoformat()
            if val_key in readings:
                window_vals.append(readings[val_key])

        if len(window_vals) == window_size:
            arr = np.array(window_vals)
            if "mean" in feature_name:
                rolling_values[feature_name] = float(arr.mean())
            elif "std" in feature_name:
                rolling_values[feature_name] = float(arr.std(ddof=1))
            real_rolling.append(feature_name)
        else:
            # Fallback to benchmark expectation
            rolling_values[feature_name] = float(profile_row[feature_name])
            benchmark_rolling.append(feature_name)

    # Calendar features
    calendar = {
        "hour": h,
        "day_of_week": dow,
        "month": m,
        "is_weekend": 1 if dow >= 5 else 0,
    }

    # Assemble in exact model feature order
    features = {
        **lag_values,
        **rolling_values,
        **calendar,
        "T2M": t2m,
    }

    history_mode = "real_history" if (len(benchmark_lags) == 0 and len(benchmark_rolling) == 0) else "benchmark_profile_fallback"
    provenance = {
        "mode": history_mode,
        "real_lags_used": real_lags,
        "benchmark_lags_used": benchmark_lags,
        "real_rolling_used": real_rolling,
        "benchmark_rolling_used": benchmark_rolling,
        "benchmark_dataset": "UCI Individual Household Electric Power Consumption (Sceaux, France)",
        "method": "Conditional expectation matrix E[Feature | month, day_of_week, hour] derived from load_processed_clean.csv",
    }

    return features, provenance


def build_load_features_recursive(
    target_time: datetime,
    t2m: float,
    predicted_loads: dict[str, float],
) -> tuple[dict, dict]:
    """Build load features for multi-step recursive forecasting.

    Merges real sensor readings + previously predicted recursive step loads, with
    benchmark profile fallback for any still-missing history offsets.

    Args:
        target_time: The future hour to predict load for.
        t2m: Temperature at 2m (°C).
        predicted_loads: Dict mapping ISO timestamp strings to predicted kW values.

    Returns:
        tuple (features_dict, provenance_dict)
    """
    target_hour = target_time.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    profile_table, overall_mean = _get_benchmark_profile()

    m = target_hour.month
    dow = target_hour.weekday()
    h = target_hour.hour

    if (m, dow, h) in profile_table.index:
        profile_row = profile_table.loc[(m, dow, h)]
    else:
        profile_row = overall_mean

    # Query history from Supabase
    window_start = target_hour - timedelta(hours=168)
    window_end = target_hour - timedelta(hours=1)
    readings = _query_sensor_readings(window_start, window_end)

    # Merge recursive predictions (predictions take precedence for future simulated steps)
    merged = dict(readings)
    if predicted_loads:
        merged.update(predicted_loads)

    lag_values = {}
    real_lags = []
    recursive_lags = []
    benchmark_lags = []

    for offset in LAG_OFFSETS:
        lag_time = target_hour - timedelta(hours=offset)
        lag_key = lag_time.isoformat()
        col_name = f"power_lag_{offset}"

        if lag_key in merged:
            lag_values[col_name] = merged[lag_key]
            if predicted_loads and lag_key in predicted_loads:
                recursive_lags.append(col_name)
            else:
                real_lags.append(col_name)
        else:
            lag_values[col_name] = float(profile_row[col_name])
            benchmark_lags.append(col_name)

    rolling_values = {}
    real_rolling = []
    benchmark_rolling = []

    for feature_name, window_size in ROLLING_WINDOWS.items():
        window_vals = []
        for step in range(1, window_size + 1):
            val_time = target_hour - timedelta(hours=step)
            val_key = val_time.isoformat()
            if val_key in merged:
                window_vals.append(merged[val_key])

        if len(window_vals) == window_size:
            arr = np.array(window_vals)
            if "mean" in feature_name:
                rolling_values[feature_name] = float(arr.mean())
            elif "std" in feature_name:
                rolling_values[feature_name] = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            real_rolling.append(feature_name)
        else:
            rolling_values[feature_name] = float(profile_row[feature_name])
            benchmark_rolling.append(feature_name)

    calendar = {
        "hour": h,
        "day_of_week": dow,
        "month": m,
        "is_weekend": 1 if dow >= 5 else 0,
    }

    features = {
        **lag_values,
        **rolling_values,
        **calendar,
        "T2M": t2m,
    }

    history_mode = "real_history" if (len(benchmark_lags) == 0 and len(benchmark_rolling) == 0) else "benchmark_profile_fallback"
    provenance = {
        "mode": history_mode,
        "real_lags_used": real_lags,
        "recursive_lags_used": recursive_lags,
        "benchmark_lags_used": benchmark_lags,
        "real_rolling_used": real_rolling,
        "benchmark_rolling_used": benchmark_rolling,
        "benchmark_dataset": "UCI Individual Household Electric Power Consumption (Sceaux, France)",
    }

    return features, provenance

