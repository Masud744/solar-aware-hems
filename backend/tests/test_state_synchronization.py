# Tests for bi-directional state synchronization, command timestamp isolation, and pending command protection
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.routers.device import pending_relay_commands, last_command_timestamps

client = TestClient(app)

DEVICE_ID = "esp32_main"


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    """Clear in-memory command tracking state before each test."""
    pending_relay_commands.clear()
    last_command_timestamps.clear()
    yield
    pending_relay_commands.clear()
    last_command_timestamps.clear()


def _mock_supabase():
    """Create a mock Supabase client that accepts all operations."""
    mock = MagicMock()
    # For select().eq().execute() → returns existing device_controls row
    mock.table().select().eq().execute.return_value = MagicMock(
        data=[{"device_id": DEVICE_ID, "load_1": "off", "load_2": "off",
               "load_3": "off", "load_4": "off", "updated_at": None}]
    )
    # For upsert().execute() → succeeds
    mock.table().upsert().execute.return_value = MagicMock(data=[{}])
    # For insert().execute() → returns inserted row with id
    mock.table().insert().execute.return_value = MagicMock(
        data=[{"id": 999, "device_id": DEVICE_ID, "ts": "2026-08-28T12:00:00Z"}]
    )
    # For select().order().limit().execute() → returns empty
    mock.table().select().order().limit().execute.return_value = MagicMock(data=[])
    return mock


def test_pending_command_protected_from_old_telemetry():
    """Verify that a pending dashboard command is NOT overwritten by old telemetry,
    and IS cleared once confirmed by matching telemetry."""

    mock_sb = _mock_supabase()

    # 1. Issue a dashboard command: load_1 → solar
    with patch("app.routers.device.get_supabase", return_value=mock_sb):
        ctrl_res = client.post(
            "/api/device/control",
            json={"device_id": DEVICE_ID, "load_1": "solar"}
        )
    assert ctrl_res.status_code == 200
    command_ts = ctrl_res.json()["last_command_ts"]
    assert command_ts is not None

    # 2. Verify pending command was recorded
    assert DEVICE_ID in pending_relay_commands
    assert pending_relay_commands[DEVICE_ID]["loads"]["load_1"] == "solar"

    # 3. Simulate OLD telemetry (load_1 still reports grid — ESP32 hasn't processed command yet)
    with patch("app.routers.ingest.get_supabase", return_value=mock_sb):
        ingest_res = client.post("/ingest", json={
            "device_id": DEVICE_ID,
            "ts": "2026-08-28T12:00:00Z",
            "voltage_v": 225.0, "current_a": 0.28, "power_w": 60.0,
            "relay_commanded_state": {
                "load_1": {"name": "Load 1", "applied_source": "grid", "desired_source": "grid", "selector_source": "grid"},
                "load_2": {"name": "Load 2", "applied_source": "solar", "desired_source": "solar", "selector_source": "solar"},
            },
        })
    assert ingest_res.status_code == 200

    # 4. CRITICAL: Pending command must STILL be active (old telemetry must not clear it)
    assert DEVICE_ID in pending_relay_commands
    assert "load_1" in pending_relay_commands[DEVICE_ID]["loads"]
    assert pending_relay_commands[DEVICE_ID]["loads"]["load_1"] == "solar"

    # 5. last_command_ts must be untouched
    assert last_command_timestamps[DEVICE_ID] == command_ts

    # 6. Simulate CONFIRMED telemetry (load_1 now reports solar — ESP32 applied the command)
    with patch("app.routers.ingest.get_supabase", return_value=mock_sb):
        ingest_res2 = client.post("/ingest", json={
            "device_id": DEVICE_ID,
            "ts": "2026-08-28T12:00:05Z",
            "voltage_v": 225.0, "current_a": 0.28, "power_w": 60.0,
            "relay_commanded_state": {
                "load_1": {"name": "Load 1", "applied_source": "solar", "desired_source": "solar", "selector_source": "solar"},
                "load_2": {"name": "Load 2", "applied_source": "solar", "desired_source": "solar", "selector_source": "solar"},
            },
        })
    assert ingest_res2.status_code == 200

    # 7. Pending command should now be CLEARED (confirmed by hardware)
    assert DEVICE_ID not in pending_relay_commands


def test_new_dashboard_command_generates_fresh_timestamp():
    """Verify that a new dashboard command generates a fresh last_command_ts and pending entry."""
    mock_sb = _mock_supabase()

    with patch("app.routers.device.get_supabase", return_value=mock_sb):
        ctrl_res = client.post(
            "/api/device/control",
            json={"device_id": DEVICE_ID, "load_1": "grid"}
        )
    assert ctrl_res.status_code == 200
    new_cmd_ts = ctrl_res.json()["last_command_ts"]
    assert new_cmd_ts is not None

    # Verify in-memory state
    assert last_command_timestamps[DEVICE_ID] == new_cmd_ts
    assert DEVICE_ID in pending_relay_commands
    assert pending_relay_commands[DEVICE_ID]["loads"]["load_1"] == "grid"

    # Verify status endpoint returns the timestamp
    with patch("app.routers.device.get_supabase", return_value=mock_sb):
        status = client.get(f"/api/device/status?device_id={DEVICE_ID}").json()
    assert status["last_command_ts"] == new_cmd_ts


def test_physical_selector_change_reconciles_normally():
    """Verify that physical selector changes (no pending command) reconcile device_controls normally."""
    mock_sb = _mock_supabase()

    # No pending command — simulate physical selector changing load_3 from off to grid
    assert DEVICE_ID not in pending_relay_commands

    with patch("app.routers.ingest.get_supabase", return_value=mock_sb):
        ingest_res = client.post("/ingest", json={
            "device_id": DEVICE_ID,
            "ts": "2026-08-28T12:00:00Z",
            "voltage_v": 225.0, "current_a": 0.28, "power_w": 60.0,
            "relay_commanded_state": {
                "load_3": {"name": "Load 3", "applied_source": "grid", "desired_source": "grid", "selector_source": "grid"},
            },
        })
    assert ingest_res.status_code == 200

    # Verify the upsert was called (reconciliation proceeded)
    assert mock_sb.table().upsert.called
