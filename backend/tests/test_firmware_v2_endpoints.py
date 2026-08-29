# Unit tests for Firmware v2 telemetry ingestion and device control/status endpoints

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from pytest import approx
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")

from app.main import app

client = TestClient(app)


def test_firmware_v2_telemetry_ingest_mocked():
    """Verify that Ingest endpoint accepts rich telemetry payload matching Firmware v2."""
    v2_payload = {
        "device_id": "esp32_main",
        "ts": "2026-08-24T02:00:00+06:00",
        "voltage_v": 228.40,
        "current_a": 1.850,
        "power_w": 422.50,
        "power_factor": 0.980,
        "energy_accum_kwh": 0.03271,
        "temperature_c": 33.20,
        "humidity_pct": 71.0,
        "grid_bank_enabled": True,
        "solar_bank_enabled": True,
        "relay_commanded_state": {
            "load_1": {"name": "Load 1", "desired_source": "grid", "applied_source": "grid"},
            "load_2": {"name": "Load 2", "desired_source": "solar", "applied_source": "solar"},
            "load_3": {"name": "Load 3", "desired_source": "solar", "applied_source": "solar"},
            "load_4": {"name": "Load 4", "desired_source": "grid", "applied_source": "grid"}
        },
        "mismatch_suspected": False
    }

    mock_supabase = MagicMock()
    mock_supabase.table().insert().execute.return_value = MagicMock(
        data=[{"id": 999, "device_id": "esp32_main", "ts": "2026-08-24T02:00:00+06:00"}]
    )

    with patch("app.routers.ingest.get_supabase", return_value=mock_supabase):
        resp = client.post("/ingest", json=v2_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 999
        assert data["device_id"] == "esp32_main"


def test_device_status_endpoint():
    """Verify GET /api/device/status returns expected relay states."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().execute.return_value = MagicMock(
        data=[{
            "device_id": "esp32_main",
            "load_1": "grid",
            "load_2": "solar",
            "load_3": "solar",
            "load_4": "grid",
            "updated_at": "2026-08-24T02:00:00+06:00"
        }]
    )

    with patch("app.routers.device.get_supabase", return_value=mock_supabase):
        resp = client.get("/api/device/status?device_id=esp32_main")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "esp32_main"
        assert data["load_1"] == "grid"
        assert data["load_2"] == "solar"
        assert data["load1"] == "grid"
        assert data["load2"] == "solar"


def test_device_control_endpoint():
    """Verify POST /api/device/control updates relay state."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().execute.return_value = MagicMock(
        data=[{
            "device_id": "esp32_main",
            "load_1": "grid",
            "load_2": "solar",
            "load_3": "solar",
            "load_4": "grid"
        }]
    )
    mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{}])

    with patch("app.routers.device.get_supabase", return_value=mock_supabase):
        resp = client.post("/api/device/control", json={
            "device_id": "esp32_main",
            "load_1": "solar",
            "load_3": "off"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["load_1"] == "solar"
        assert data["load_2"] == "solar"
        assert data["load_3"] == "off"
        assert data["load_4"] == "grid"
        assert data["status"] == "updated"


def test_device_calibrate_endpoint():
    """Verify POST /api/device/calibrate queues calibration command for ESP32 polling."""
    resp = client.post("/api/device/calibrate", json={
        "device_id": "esp32_main",
        "command": "CAL_ZERO"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["command"] == "CAL_ZERO"
    assert data["status"] == "queued"

    # Status endpoint should now reflect the pending CAL_ZERO command
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().execute.return_value = MagicMock(data=[{}])
    with patch("app.routers.device.get_supabase", return_value=mock_supabase):
        status_resp = client.get("/api/device/status?device_id=esp32_main")
        assert status_resp.status_code == 200
        assert status_resp.json()["cal_command"] == "CAL_ZERO"

    # Test SET_VCAL
    resp_vcal = client.post("/api/device/calibrate", json={
        "device_id": "esp32_main",
        "command": "SET_VCAL",
        "value": 0.1785
    })
    assert resp_vcal.status_code == 200
    assert resp_vcal.json()["command"] == "SET_VCAL"

    with patch("app.routers.device.get_supabase", return_value=mock_supabase):
        status_resp2 = client.get("/api/device/status?device_id=esp32_main")
        assert status_resp2.json()["cal_command"] == "SET_VCAL 0.1785"


def test_calibrated_telemetry_ingest():
    """Verify that Ingest endpoint accepts calibration status and constants."""
    payload = {
        "device_id": "esp32_main",
        "ts": "2026-08-27T12:00:00+06:00",
        "voltage_v": 229.1,
        "current_a": 0.000,
        "power_w": 0.0,
        "cal_status": "CALIBRATED",
        "v_zero_offset": 2048.25,
        "i_zero_offset": 1535.80,
        "v_cal_factor": 0.178500,
        "i_sensitivity": 0.1000
    }

    mock_supabase = MagicMock()
    mock_supabase.table().insert().execute.return_value = MagicMock(
        data=[{"id": 1001, "device_id": "esp32_main", "ts": "2026-08-27T12:00:00+06:00"}]
    )

    with patch("app.routers.ingest.get_supabase", return_value=mock_supabase):
        resp = client.post("/ingest", json=payload)
        assert resp.status_code == 200
        assert resp.json()["id"] == 1001
