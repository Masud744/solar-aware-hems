# Unit and integration tests for AI Conversational Assistant (SolarMate AI)
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-120b")

from app.main import app
from app.services import assistant_tools, assistant

client = TestClient(app)


def test_tool_get_live_telemetry():
    """Verify get_live_telemetry tool retrieves real sensor reading."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{
            "ts": "2026-08-29T12:00:00Z",
            "power_w": 420.5,
            "voltage_v": 230.1,
            "current_a": 1.83,
            "power_factor": 0.98,
            "temperature_c": 29.4,
            "humidity_pct": 71.0,
            "cal_status": "CALIBRATED",
        }]
    )
    with patch("app.services.assistant_tools.get_supabase", return_value=mock_supabase):
        res = asyncio.run(assistant_tools.tool_get_live_telemetry())
        assert res["status"] in ("live", "stale")
        assert res["power_w"] == 420.5
        assert res["temperature_c"] == 29.4
        assert res["humidity_pct"] == 71.0
        assert res["provenance"] == "[MEASURED]"


def test_tool_get_relay_status():
    """Verify get_relay_status tool returns 4 controlled circuits."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(
        data=[{
            "load_1": "grid",
            "load_2": "solar",
            "load_3": "solar",
            "load_4": "grid",
        }]
    )
    with patch("app.services.assistant_tools.get_supabase", return_value=mock_supabase):
        res = asyncio.run(assistant_tools.tool_get_relay_status())
        assert res["status"] == "success"
        assert "load_1" in res["circuits"]
        assert res["circuits"]["load_1"]["applied_source"] == "grid"
        assert res["circuits"]["load_2"]["applied_source"] == "solar"


def test_tool_appliance_safety_allow():
    """Verify check_appliance_safety executes decision engine logic."""
    with patch("app.routers.device.device_check") as mock_check:
        mock_check.return_value = MagicMock(
            decision="ALLOW",
            device_name="Rice Cooker",
            rated_power_kw=0.70,
            duration_hours=0.67,
            safe_solar_kw=1.35,
            conservative_load_kw=0.50,
            safe_surplus_kw=0.85,
            reason="Safe surplus (0.85 kW) exceeds 0.70 kW"
        )
        res = asyncio.run(assistant_tools.tool_check_appliance_safety("Rice Cooker", 0.70, 0.67))
        assert res["decision"] == "ALLOW"
        assert res["safe_surplus_kw"] == 0.85
        assert res["provenance"] == "[CALCULATED]"


def test_tool_solar_estimate_confirmation_flow():
    """Verify that update_user_solar_estimate requires confirmation before saving."""
    # Step 1: Without confirmation
    res_unconfirmed = asyncio.run(assistant_tools.tool_update_user_solar_estimate(
        estimated_solar_kwh=3.5,
        date_str="2026-08-29",
        confirmed=False
    ))
    assert res_unconfirmed["status"] == "confirmation_required"
    assert res_unconfirmed["requires_user_confirmation"] is True

    # Step 2: With confirmation
    with patch("app.services.energy_accounting.save_user_solar_estimate") as mock_save:
        mock_save.return_value = {"success": True, "date": "2026-08-29", "estimated_solar_kwh": 3.5}
        res_confirmed = asyncio.run(assistant_tools.tool_update_user_solar_estimate(
            estimated_solar_kwh=3.5,
            date_str="2026-08-29",
            confirmed=True
        ))
        assert res_confirmed["status"] == "saved"
        assert mock_save.called


def test_post_chat_endpoint_schema():
    """Test POST /chat endpoint validation, session_id propagation, and basic processing."""
    with patch("app.services.assistant.process_chat_message") as mock_proc:
        mock_proc.return_value = {
            "session_id": "test-session-uuid-123",
            "answer": "The current room temperature is 29.4°C [MEASURED].",
            "data_sources": ["[MEASURED]"],
            "tool_calls": ["get_live_telemetry"],
        }
        resp = client.post("/chat", json={
            "message": "What is the current temperature?",
            "session_id": "test-session-uuid-123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "test-session-uuid-123"
        assert "29.4°C" in data["answer"]
        assert "[MEASURED]" in data["data_sources"]
        assert "get_live_telemetry" in data["tool_calls"]


def test_chat_hardware_safety_no_relays_in_tools():
    """Verify that NO hardware switching or relay actuation tools exist in HEMS_TOOLS_SCHEMA."""
    tool_names = [t["function"]["name"] for t in assistant_tools.HEMS_TOOLS_SCHEMA]
    for prohibited in ["switch_relay", "turn_on_relay", "turn_off_relay", "actuate", "control_device", "set_relay"]:
        assert prohibited not in tool_names


def test_chat_history_get_and_delete_endpoints():
    """Verify GET /chat/history and DELETE /chat/history endpoints."""
    mock_history = [
        {"id": 1, "session_id": "sess-abc", "role": "user", "content": "Can I run a heater?", "created_at": "2026-08-29T10:00:00Z"},
        {"id": 2, "session_id": "sess-abc", "role": "assistant", "content": "Please specify power.", "created_at": "2026-08-29T10:00:05Z"}
    ]
    with patch("app.services.assistant.load_chat_history", return_value=mock_history), \
         patch("app.services.assistant.delete_chat_history", return_value=True):
        
        # Test GET /chat/history
        get_res = client.get("/chat/history?session_id=sess-abc")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["session_id"] == "sess-abc"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"

        # Test DELETE /chat/history
        del_res = client.delete("/chat/history?session_id=sess-abc")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "cleared"
