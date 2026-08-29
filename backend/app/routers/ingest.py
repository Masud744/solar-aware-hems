# Ingest router — /ingest (ESP32 sensor data)
from fastapi import APIRouter, Query
from app.models.schemas import IngestRequest, IngestResponse
from app.database import get_supabase

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_sensor_data(req: IngestRequest):
    """Ingest a sensor reading from ESP32 hardware.

    Stores voltage, current, power, power factor, energy, temperature,
    humidity, bank permission switches, relay state, and mismatch status.
    """
    sb = get_supabase()
    from datetime import datetime, timezone
    ts_val = req.ts if req.ts else datetime.now(timezone.utc)

    insert_data = {
        "device_id": req.device_id,
        "ts": ts_val.isoformat(),
        "voltage_v": req.voltage_v,
        "current_a": req.current_a,
        "power_w": req.power_w,
        "temperature_c": req.temperature_c,
    }
    if req.power_factor is not None:
        insert_data["power_factor"] = req.power_factor
    if req.energy_accum_kwh is not None:
        insert_data["energy_accum_kwh"] = req.energy_accum_kwh
    if req.humidity_pct is not None:
        insert_data["humidity_pct"] = req.humidity_pct
    if req.grid_bank_enabled is not None:
        insert_data["grid_bank_enabled"] = req.grid_bank_enabled
    if req.solar_bank_enabled is not None:
        insert_data["solar_bank_enabled"] = req.solar_bank_enabled
    if req.relay_commanded_state is not None:
        insert_data["relay_commanded_state"] = req.relay_commanded_state
    if req.cal_status is not None:
        insert_data["cal_status"] = req.cal_status
    if req.v_zero_offset is not None:
        insert_data["v_zero_offset"] = req.v_zero_offset
    if req.i_zero_offset is not None:
        insert_data["i_zero_offset"] = req.i_zero_offset
    if req.v_cal_factor is not None:
        insert_data["v_cal_factor"] = req.v_cal_factor
    if req.i_sensitivity is not None:
        insert_data["i_sensitivity"] = req.i_sensitivity

    # Reconcile confirmed hardware applied state with device_controls table in Supabase.
    # CRITICAL: Do NOT overwrite loads that have a pending unconfirmed dashboard command.
    # A pending command is cleared only when telemetry confirms the commanded value was applied.
    if req.relay_commanded_state and isinstance(req.relay_commanded_state, dict):
        from app.routers.device import pending_relay_commands
        from datetime import datetime as _dt, timezone as _tz

        pending_info = pending_relay_commands.get(req.device_id)
        pending_loads: dict = {}
        if pending_info:
            age_seconds = (_dt.now(_tz.utc) - pending_info["ts"]).total_seconds()
            if age_seconds > 15:
                # Auto-expire: ESP32 had enough time to process; clear stale pending
                pending_relay_commands.pop(req.device_id, None)
            else:
                pending_loads = pending_info.get("loads", {})

        ctrl_update = {
            "device_id": req.device_id,
            "updated_at": ts_val.isoformat(),
        }
        for k in ("load_1", "load_2", "load_3", "load_4"):
            ld_info = req.relay_commanded_state.get(k)
            if isinstance(ld_info, dict) and "applied_source" in ld_info:
                applied = ld_info["applied_source"].lower()
            elif isinstance(ld_info, str):
                applied = ld_info.lower()
            else:
                continue

            if k in pending_loads:
                # This load has a pending dashboard command
                if applied == pending_loads[k]:
                    # ESP32 confirmed the commanded value — reconcile and clear pending
                    ctrl_update[k] = applied
                    del pending_loads[k]
                # else: Don't reconcile — command is still pending, keep device_controls as-is
            else:
                # No pending command for this load — reconcile normally
                # (physical selector changes flow through this path)
                ctrl_update[k] = applied

        # If all pending loads are confirmed, clean up the pending entry
        if pending_info and not pending_loads:
            pending_relay_commands.pop(req.device_id, None)

        if len(ctrl_update) > 2:
            try:
                sb.table("device_controls").upsert(ctrl_update).execute()
            except Exception:
                pass

    # Clear pending calibration command only once telemetry confirms the new value was applied
    from app.routers.device import pending_calibration_commands
    if req.device_id in pending_calibration_commands:
        info = pending_calibration_commands[req.device_id]
        cmd = info.get("command")
        val = info.get("value")
        if cmd == "CAL_ZERO" and req.v_zero_offset and req.v_zero_offset != 2048.0:
            pending_calibration_commands.pop(req.device_id, None)
        elif cmd == "SET_VCAL" and val is not None and req.v_cal_factor is not None and abs(req.v_cal_factor - float(val)) < 1e-4:
            pending_calibration_commands.pop(req.device_id, None)
        elif cmd == "SET_SENS" and val is not None and req.i_sensitivity is not None and abs(req.i_sensitivity - float(val)) < 1e-4:
            pending_calibration_commands.pop(req.device_id, None)

    result = sb.table("sensor_readings").insert(insert_data).execute()

    row = result.data[0]
    return IngestResponse(
        id=row["id"],
        device_id=req.device_id,
        ts=ts_val,
    )


@router.get("/telemetry/latest")
async def get_latest_sensor_reading(device_id: str = Query("esp32_main")):
    """Return the latest measured telemetry row for the device; never fabricate a fallback."""
    sb = get_supabase()
    query = sb.table("sensor_readings").select("*").order("ts", desc=True).limit(1)
    if device_id:
        query = query.eq("device_id", device_id)
    result = query.execute()
    return {"reading": result.data[0] if result.data else None}


@router.get("/telemetry/history")
async def get_sensor_history(limit: int = Query(30, ge=1, le=200)):
    """Return recent measured telemetry for the dashboard audit table."""
    sb = get_supabase()
    result = (
        sb.table("sensor_readings")
        .select("*")
        .order("ts", desc=True)
        .limit(limit)
        .execute()
    )
    return {"readings": result.data}
