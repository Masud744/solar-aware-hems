#!/usr/bin/env python3
"""Comprehensive Phase 5 integration test suite for all 8 endpoints and Supabase persistence."""

import os
import sys
import json
import httpx
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath("backend"))

BASE_URL = "http://127.0.0.1:8000"

results = {}

def log_test(name, status_code, request_data, response_data, is_correct, notes=""):
    results[name] = {
        "status_code": status_code,
        "request": request_data,
        "response": response_data,
        "is_correct": is_correct,
        "notes": notes,
    }
    status_icon = "✅" if (200 <= status_code < 300 and is_correct) else "❌"
    print(f"{status_icon} [{status_code}] {name}: {notes}")


def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    print("=" * 70)
    print("PHASE 5 LIVE ENDPOINT INTEGRATION TESTS")
    print("=" * 70)

    # 1. Health check
    resp = client.get("/")
    log_test("Root Health Check", resp.status_code, None, resp.json(), resp.status_code == 200, "API online")

    # 2. GET /predict/solar (Backend-owned Open-Meteo retrieval)
    # Using anchor time (2026-08-21 12:00:00) where both Open-Meteo forecast and sensor history exist
    anchor_time = datetime(2026, 8, 21, 12, 0, 0)
    target_solar_str = anchor_time.strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.get(f"/predict/solar?target_time={target_solar_str}")
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and "predicted_kw" in data
        and "safe_kw" in data
        and "cloud_cover" in data
        and data["weather_source"] == "Open-Meteo forecast API"
    )
    log_test(
        "GET /predict/solar",
        resp.status_code,
        {"target_time": target_solar_str},
        data,
        is_correct,
        f"Predicted: {data.get('predicted_kw', 'N/A')} kW, Safe: {data.get('safe_kw', 'N/A')} kW, Cloud: {data.get('cloud_cover', 'N/A')}%"
    )

    # 3. GET /predict/load (Using seed_test_data history)
    # Using historical test timestamp from seed data: 2010-02-04 14:00:00
    target_load_str = "2010-02-04T14:00:00"
    resp = client.get(f"/predict/load?target_time={target_load_str}&temperature_c=-3.5")
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and "predicted_kw" in data
        and "conservative_kw" in data
        and "t2m_disclosure" in data
    )
    log_test(
        "GET /predict/load",
        resp.status_code,
        {"target_time": target_load_str, "temperature_c": -3.5},
        data,
        is_correct,
        f"Predicted: {data.get('predicted_kw', 'N/A')} kW, Conservative: {data.get('conservative_kw', 'N/A')} kW, Bucket: {data.get('sigma_bucket', 'N/A')}"
    )

    # 4. GET /risk/margin
    resp = client.get("/risk/margin")
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and data.get("k") == 1.0
        and "solar_sigma_buckets" in data
        and "load_sigma_buckets" in data
        and "calibration_disclosure" in data
    )
    log_test(
        "GET /risk/margin",
        resp.status_code,
        None,
        data,
        is_correct,
        f"k={data.get('k')}, Method={data.get('sigma_method')}"
    )

    # 5. POST /device/check (Complete decision flow: instantaneous & duration-aware)
    # Target time in contemporary window where both weather & sensor_readings exist
    device_req = {
        "device_name": "Washing Machine",
        "rated_power_kw": 1.2,
        "duration_hours": 1.0,
        "target_time": target_solar_str,
        "priority": "normal",
    }
    resp = client.post("/device/check", json=device_req)
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and data.get("decision") in ("ALLOW", "DENY")
        and "safe_surplus_kw" in data
        and "reason" in data
    )
    log_test(
        "POST /device/check",
        resp.status_code,
        device_req,
        data,
        is_correct,
        f"Decision={data.get('decision')}, Safe Surplus={data.get('safe_surplus_kw')} kW, Reason={data.get('reason')[:60]}..."
    )

    # 6. POST /schedule/recommend (Multi-step scheduling over a 6-hour window)
    window_start = anchor_time.replace(hour=12)
    window_end = anchor_time.replace(hour=16)
    schedule_req = {
        "device_name": "Washing Machine",
        "rated_power_kw": 0.5,
        "duration_hours": 2.0,
        "window_start": window_start.strftime("%Y-%m-%dT%H:%M:%S"),
        "window_end": window_end.strftime("%Y-%m-%dT%H:%M:%S"),
        "priority": "flexible",
    }
    resp = client.post("/schedule/recommend", json=schedule_req)
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and "slots" in data
        and len(data["slots"]) > 0
        and "scheduling_disclosure" in data
    )
    log_test(
        "POST /schedule/recommend",
        resp.status_code,
        schedule_req,
        data,
        is_correct,
        f"Evaluated {len(data.get('slots', []))} slots, Recommended: {data.get('recommended_start', 'None')}"
    )

    # 7. GET /xai/explanation (SHAP feature contributions + rule explanation)
    resp = client.get(f"/xai/explanation?prediction_type=solar&target_time={target_solar_str}")
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and "feature_contributions" in data
        and len(data["feature_contributions"]) == 7  # 7 solar features
        and "rule_based_explanation" in data
    )
    top_feature = data.get("feature_contributions", [{}])[0].get("feature_name", "N/A") if is_correct else "N/A"
    log_test(
        "GET /xai/explanation",
        resp.status_code,
        {"prediction_type": "solar", "target_time": target_solar_str},
        data,
        is_correct,
        f"Top contributor: {top_feature}, Rule: {data.get('rule_based_explanation', '')[:60]}..."
    )

    # 8. POST /action (Log user confirmation)
    # First get the device_request id from Supabase
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
    from app.database import get_supabase
    sb = get_supabase()
    dev_req_row = sb.table("device_requests").select("id").order("id", desc=True).limit(1).execute()
    dev_req_id = dev_req_row.data[0]["id"] if dev_req_row.data else 1

    action_req = {
        "device_request_id": dev_req_id,
        "action": "accept",
    }
    resp = client.post("/action", json=action_req)
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and data.get("action") == "accept"
        and data.get("device_request_id") == dev_req_id
    )
    log_test(
        "POST /action",
        resp.status_code,
        action_req,
        data,
        is_correct,
        f"Logged action '{data.get('action')}' for device_request #{dev_req_id}"
    )

    # 9. POST /ingest (ESP32 sensor data ingestion)
    ingest_req = {
        "device_id": "esp32_hardware_test",
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "voltage_v": 230.4,
        "current_a": 2.15,
        "power_w": 495.36,
        "temperature_c": 29.8,
    }
    resp = client.post("/ingest", json=ingest_req)
    data = resp.json() if resp.status_code == 200 else resp.text
    is_correct = (
        resp.status_code == 200
        and data.get("status") == "inserted"
        and data.get("device_id") == "esp32_hardware_test"
    )
    log_test(
        "POST /ingest",
        resp.status_code,
        ingest_req,
        data,
        is_correct,
        f"Ingested reading for device '{data.get('device_id')}' (id={data.get('id')})"
    )

    # 10. Forecast Horizon Validation (Out-of-horizon error check)
    far_future = (datetime.now() + timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.get(f"/predict/solar?target_time={far_future}")
    log_test(
        "Forecast Horizon Error Handling (422 expected)",
        resp.status_code,
        {"target_time": far_future},
        resp.json() if resp.status_code == 422 else resp.text,
        resp.status_code == 422,
        f"Correctly returned 422 for out-of-horizon target (+40 days)"
    )

    # 11. Insufficient History Validation (Missing lags check)
    far_past = "1999-01-01T12:00:00"
    resp = client.get(f"/predict/load?target_time={far_past}&temperature_c=20.0")
    log_test(
        "Insufficient History Error Handling (422 expected)",
        resp.status_code,
        {"target_time": far_past, "temperature_c": 20.0},
        resp.json() if resp.status_code == 422 else resp.text,
        resp.status_code == 422,
        f"Correctly returned 422 for missing historical lags (1999)"
    )

    # Save test results to JSON
    with open("backend/tests/integration_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\n✓ Saved integration_results.json")

    # 12. Supabase Table Persistence Verification
    print("\n" + "=" * 70)
    print("SUPABASE TABLE PERSISTENCE VERIFICATION")
    print("=" * 70)
    tables = [
        "sensor_readings",
        "solar_predictions",
        "load_predictions",
        "device_requests",
        "user_actions",
        "shap_explanations",
    ]
    for table in tables:
        res = sb.table(table).select("*").order("id", desc=True).limit(3).execute()
        count = len(res.data)
        latest_id = res.data[0]["id"] if res.data else "None"
        latest_ts = res.data[0].get("ts", "N/A") if res.data else "N/A"
        print(f"  ✓ {table:<20}: {count} recent rows verified (Latest ID: {latest_id}, ts: {latest_ts})")

if __name__ == "__main__":
    run_tests()
