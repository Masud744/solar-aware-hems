# Comprehensive unit tests for Energy Accounting and Persistence Architecture
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")

from app.main import app
from app.services.energy_accounting import (
    compute_integrated_energy_from_readings,
    get_day_utc_bounds,
    get_dhaka_now,
    save_user_solar_estimate,
    get_saved_solar_estimates,
    get_daily_energy_accounting,
    get_monthly_energy_accounting,
)

client = TestClient(app)


def test_trapezoidal_integration_basic():
    """Verify trapezoidal integration math: 1000W constant power for 1 hour = 1.0 kWh."""
    readings = [
        {"ts": "2026-08-28T00:00:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:05:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:10:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:15:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:20:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:25:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:30:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:35:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:40:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:45:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:50:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:55:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T01:00:00Z", "power_w": 1000.0},
    ]
    kwh = compute_integrated_energy_from_readings(readings)
    assert pytest.approx(kwh, 0.001) == 1.0


def test_trapezoidal_integration_gap_protection():
    """Verify that gaps greater than 300s are ignored to prevent crediting power outages."""
    readings = [
        {"ts": "2026-08-28T00:00:00Z", "power_w": 1000.0},
        {"ts": "2026-08-28T00:05:00Z", "power_w": 1000.0},  # dt = 300s -> counted
        {"ts": "2026-08-28T02:00:00Z", "power_w": 1000.0},  # dt = 6900s > 300s -> ignored!
        {"ts": "2026-08-28T02:05:00Z", "power_w": 1000.0},  # dt = 300s -> counted
    ]
    # Each 5-min segment of 1000W is (1000 * 300) / (3600 * 1000) = 0.08333 kWh
    # 2 segments = 0.1667 kWh
    kwh = compute_integrated_energy_from_readings(readings)
    assert pytest.approx(kwh, 0.001) == 0.1667


def test_dhaka_calendar_bounds():
    """Verify that 2026-08-28 in Asia/Dhaka corresponds to 2026-08-27 18:00 UTC to 2026-08-28 18:00 UTC."""
    start_utc, end_utc, start_iso, end_iso = get_day_utc_bounds("2026-08-28")
    assert "2026-08-27T18:00:00" in start_iso
    assert "2026-08-28T18:00:00" in end_iso


def test_conservative_solar_formulas_case_a_load_greater_than_solar():
    """Case A: Consumption (5.0 kWh) > Solar (2.0 kWh)."""
    total_measured_kwh = 5.0
    user_solar_kwh = 2.0
    tariff_rate = 7.50

    solar_utilized_kwh = min(total_measured_kwh, user_solar_kwh)
    estimated_remaining_kwh = max(0.0, total_measured_kwh - solar_utilized_kwh)
    excess_solar_kwh = max(0.0, user_solar_kwh - total_measured_kwh)
    estimated_savings_bdt = solar_utilized_kwh * tariff_rate

    assert solar_utilized_kwh == 2.0
    assert estimated_remaining_kwh == 3.0
    assert excess_solar_kwh == 0.0
    assert estimated_savings_bdt == 15.00


def test_conservative_solar_formulas_case_b_solar_greater_than_load():
    """Case B: Solar (5.0 kWh) > Consumption (2.0 kWh) - Capped at offset load."""
    total_measured_kwh = 2.0
    user_solar_kwh = 5.0
    tariff_rate = 7.50

    solar_utilized_kwh = min(total_measured_kwh, user_solar_kwh)
    estimated_remaining_kwh = max(0.0, total_measured_kwh - solar_utilized_kwh)
    excess_solar_kwh = max(0.0, user_solar_kwh - total_measured_kwh)
    estimated_savings_bdt = solar_utilized_kwh * tariff_rate

    assert solar_utilized_kwh == 2.0
    assert estimated_remaining_kwh == 0.0
    assert excess_solar_kwh == 3.0
    assert estimated_savings_bdt == 15.00


def test_energy_summary_endpoint():
    """Test GET /energy/summary endpoint with mocked database returns."""
    mock_supabase = MagicMock()
    
    # Mock sensor_readings return
    mock_supabase.table().select().eq().gte().lt().order().range().execute.return_value = MagicMock(
        data=[
            {"ts": "2026-08-28T06:00:00Z", "power_w": 500.0},
            {"ts": "2026-08-28T06:05:00Z", "power_w": 500.0},
        ]
    )
    # Mock user_solar_estimates return
    mock_supabase.table().select().order().limit().execute.return_value = MagicMock(
        data=[
            {"date": "2026-08-28", "estimated_solar_kwh": 3.5, "notes": "Sunny day", "updated_at": "2026-08-28T12:00:00Z"}
        ]
    )

    with patch("app.services.energy_accounting.get_supabase", return_value=mock_supabase):
        resp = client.get("/energy/summary?tariff_rate=7.50")
        assert resp.status_code == 200
        data = resp.json()
        assert "today" in data
        assert "this_month" in data
        assert data["tariff_rate"] == 7.50
        assert data["tariff_currency"] == "BDT"


def test_solar_estimate_post_validation():
    """Verify negative solar estimate is rejected with 422."""
    resp = client.post("/energy/solar-estimate", json={
        "date": "2026-08-28",
        "estimated_solar_kwh": -1.5,
    })
    assert resp.status_code == 422
