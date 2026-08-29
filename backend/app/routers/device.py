# Device routers — /device/check, /schedule/recommend, /device/status, /device/control
import math
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    DeviceCheckRequest, DeviceCheckResponse,
    ScheduleRecommendRequest, ScheduleRecommendResponse, HourlySlot,
    DeviceStatusResponse, DeviceControlRequest, DeviceControlResponse,
    CalibrateRequest, CalibrateResponse,
)
from app.services import ml_models, weather, decision_engine, features
from app.config import settings
from app.database import get_supabase

router = APIRouter(tags=["device"])


async def _predict_at_hour(target_time, predicted_loads=None):
    """Internal: get solar + load predictions + decision result for one hour.

    Args:
        target_time: datetime for the target hour
        predicted_loads: optional dict of {iso_ts: kw} for recursive forecasting

    Returns:
        (solar_pred, load_pred, sigma_solar, sigma_load,
         solar_bucket, load_bucket, wx, provenance)
    """
    target_hour = target_time.replace(minute=0, second=0, microsecond=0)

    # Fetch weather
    wx = await weather.get_forecast_at(target_hour)

    # Solar prediction
    solar_features = {
        "cloud_cover": wx["cloud_cover"],
        "temperature": wx["temperature"],
        "relative_humidity": wx["relative_humidity"],
        "wind_speed": wx["wind_speed"],
        "hour": target_hour.hour,
        "month": target_hour.month,
        "day_of_year": target_hour.timetuple().tm_yday,
    }
    solar_pred = ml_models.predict_solar(solar_features)

    # Load prediction
    if predicted_loads:
        load_feats, provenance = features.build_load_features_recursive(
            target_hour, t2m=wx["T2M"], predicted_loads=predicted_loads
        )
    else:
        load_feats, provenance = features.build_load_features(target_hour, t2m=wx["T2M"])
    load_pred = ml_models.predict_load(load_feats)

    sigma_solar, solar_bucket = decision_engine.solar_sigma_bucket(wx["cloud_cover"])
    sigma_load, load_bucket = decision_engine.load_sigma_bucket(target_hour.hour)

    return (solar_pred, load_pred, sigma_solar, sigma_load,
            solar_bucket, load_bucket, wx, provenance)


@router.post("/device/check", response_model=DeviceCheckResponse)
async def device_check(req: DeviceCheckRequest):
    """Check if a device can run safely at the given time (§8.1/§8.2).

    For single-hour devices: instantaneous check (§8.1).
    For multi-hour devices: duration-aware check (§8.2).
    k is NOT user-controllable — uses production SAFETY_K.
    """
    k = settings.SAFETY_K
    target_hour = req.target_time.replace(minute=0, second=0, microsecond=0)
    n_hours = max(1, math.ceil(req.duration_hours))

    try:
        if n_hours == 1:
            # §8.1 Instantaneous check
            (solar_pred, load_pred, sigma_solar, sigma_load,
             solar_bucket, load_bucket, wx, provenance) = await _predict_at_hour(target_hour)

            result = decision_engine.compute_decision(
                predicted_solar_kw=solar_pred,
                sigma_solar=sigma_solar,
                predicted_load_kw=load_pred,
                sigma_load=sigma_load,
                device_power_kw=req.rated_power_kw,
                k=k,
            )

            final_decision = result.decision
            final_reason = result.reason
            safe_surplus = result.safe_surplus
            first_provenance = provenance
        else:
            # §8.2 Duration-aware check
            hourly_results = []
            predicted_loads = {}
            first_solar_pred = first_load_pred = 0.0
            first_sigma_solar = first_sigma_load = 0.0
            first_wx = {}
            first_provenance = None

            for h in range(n_hours):
                hour_t = target_hour + timedelta(hours=h)
                (solar_pred, load_pred, sigma_solar, sigma_load,
                 solar_bucket, load_bucket, wx, provenance) = await _predict_at_hour(
                    hour_t,
                    predicted_loads=predicted_loads if h > 0 else None,
                )

                result_h = decision_engine.compute_decision(
                    predicted_solar_kw=solar_pred,
                    sigma_solar=sigma_solar,
                    predicted_load_kw=load_pred,
                    sigma_load=sigma_load,
                    device_power_kw=req.rated_power_kw,
                    k=k,
                )
                hourly_results.append(result_h)

                # Store predicted load for recursive forecasting
                predicted_loads[hour_t.isoformat()] = load_pred

                if h == 0:
                    first_solar_pred = solar_pred
                    first_load_pred = load_pred
                    first_sigma_solar = sigma_solar
                    first_sigma_load = sigma_load
                    first_wx = wx
                    first_provenance = provenance

            final_decision, final_reason, safe_surplus = (
                decision_engine.compute_duration_aware_decision(
                    hourly_results, req.rated_power_kw
                )
            )

            # Use first-hour values for the response summary
            solar_pred = first_solar_pred
            load_pred = first_load_pred
            sigma_solar = first_sigma_solar
            sigma_load = first_sigma_load
            wx = first_wx

    except weather.ForecastHorizonError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except weather.WeatherForecastError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except features.InsufficientHistoryError as e:
        raise HTTPException(status_code=422, detail=str(e))

    safe_solar = max(0.0, solar_pred - k * sigma_solar)
    conservative_load = load_pred + k * sigma_load

    # Save to Supabase
    sb = get_supabase()
    insert_result = sb.table("device_requests").insert({
        "ts": target_hour.isoformat(),
        "device_name": req.device_name,
        "rated_power_kw": req.rated_power_kw,
        "duration_hours": req.duration_hours,
        "priority": req.priority,
        "decision": final_decision,
        "safe_surplus_kw": round(safe_surplus, 6),
        "reason": final_reason,
    }).execute()

    inserted_row = insert_result.data[0]
    return DeviceCheckResponse(
        id=inserted_row["id"],
        decision=final_decision,
        device_name=req.device_name,
        rated_power_kw=req.rated_power_kw,
        duration_hours=req.duration_hours,
        priority=req.priority,
        target_time=target_hour,
        predicted_solar_kw=round(solar_pred, 6),
        safe_solar_kw=round(safe_solar, 6),
        solar_sigma_kw=round(sigma_solar, 6),
        predicted_load_kw=round(load_pred, 6),
        conservative_load_kw=round(conservative_load, 6),
        load_sigma_kw=round(sigma_load, 6),
        safe_surplus_kw=round(safe_surplus, 6),
        k=k,
        reason=final_reason,
        history_mode=first_provenance.get("mode", "benchmark_profile_fallback") if first_provenance else "benchmark_profile_fallback",
        feature_provenance=first_provenance,
        t2m_disclosure=weather.get_t2m_disclosure(),
    )


@router.post("/schedule/recommend", response_model=ScheduleRecommendResponse)
async def schedule_recommend(req: ScheduleRecommendRequest):
    """Recommend the best start time for a device within a time window (§9).

    Evaluates each hour in [window_start, window_end] and returns the slot
    with the highest safe surplus (if any ALLOW exists).

    Uses recursive forecasting for multi-hour duration devices.
    k is NOT user-controllable — uses production SAFETY_K.
    """
    k = settings.SAFETY_K
    window_start = req.window_start.replace(minute=0, second=0, microsecond=0)
    window_end = req.window_end.replace(minute=0, second=0, microsecond=0)

    if window_end <= window_start:
        raise HTTPException(
            status_code=422,
            detail="window_end must be after window_start",
        )

    # Generate hourly slots
    slots = []
    best_slot = None
    best_surplus = float("-inf")
    current = window_start

    n_hours = max(1, math.ceil(req.duration_hours))

    # Shared cache of predicted loads for multi-step recursive forecasting across the window
    recursive_load_cache: dict[str, float] = {}
    primary_history_mode = "real_history"

    while current <= window_end:
        try:
            if n_hours == 1:
                (solar_pred, load_pred, sigma_solar, sigma_load,
                 _, _, _, provenance) = await _predict_at_hour(
                    current,
                    predicted_loads=recursive_load_cache if recursive_load_cache else None,
                )

                result = decision_engine.compute_decision(
                    predicted_solar_kw=solar_pred,
                    sigma_solar=sigma_solar,
                    predicted_load_kw=load_pred,
                    sigma_load=sigma_load,
                    device_power_kw=req.rated_power_kw,
                    k=k,
                )
                slot_surplus = result.safe_surplus
                slot_decision = result.decision
                sp, lp, ss, sl = solar_pred, load_pred, sigma_solar, sigma_load
                slot_mode = provenance.get("mode", "benchmark_profile_fallback")
                if slot_mode == "benchmark_profile_fallback":
                    primary_history_mode = "benchmark_profile_fallback"

                # Cache prediction for next steps
                recursive_load_cache[current.isoformat()] = load_pred
            else:
                # Duration-aware: check all hours in the run
                hourly_results = []
                step_predicted_loads = dict(recursive_load_cache)
                first_solar = first_load = 0.0
                first_sigma_s = first_sigma_l = 0.0
                first_mode = "real_history"

                for h in range(n_hours):
                    hour_t = current + timedelta(hours=h)
                    (sp_h, lp_h, ss_h, sl_h, _, _, _, prov_h) = await _predict_at_hour(
                        hour_t,
                        predicted_loads=step_predicted_loads if step_predicted_loads else None,
                    )
                    r = decision_engine.compute_decision(sp_h, ss_h, lp_h, sl_h, req.rated_power_kw, k)
                    hourly_results.append(r)
                    step_predicted_loads[hour_t.isoformat()] = lp_h

                    if h == 0:
                        first_solar = sp_h
                        first_load = lp_h
                        first_sigma_s = ss_h
                        first_sigma_l = sl_h
                        first_mode = prov_h.get("mode", "benchmark_profile_fallback")

                slot_decision, _, slot_surplus = (
                    decision_engine.compute_duration_aware_decision(
                        hourly_results, req.rated_power_kw
                    )
                )
                sp, lp, ss, sl = first_solar, first_load, first_sigma_s, first_sigma_l
                slot_mode = first_mode
                if slot_mode == "benchmark_profile_fallback":
                    primary_history_mode = "benchmark_profile_fallback"
                # Update main cache with the first hour prediction
                recursive_load_cache[current.isoformat()] = first_load

            safe_solar = max(0.0, sp - k * ss)
            conservative_load = lp + k * sl

            slot = HourlySlot(
                start_time=current,
                safe_surplus_kw=round(slot_surplus, 6),
                decision=slot_decision,
                predicted_solar_kw=round(sp, 6),
                safe_solar_kw=round(safe_solar, 6),
                predicted_load_kw=round(lp, 6),
                conservative_load_kw=round(conservative_load, 6),
                history_mode=slot_mode,
            )
            slots.append(slot)

            if slot_decision == "ALLOW" and slot_surplus > best_surplus:
                best_surplus = slot_surplus
                best_slot = current

        except weather.WeatherForecastError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Weather forecast unavailable from Open-Meteo. Cannot generate schedule without forecast features. Error: {e}",
            )
        except (weather.ForecastHorizonError, features.InsufficientHistoryError):
            # Skip this slot if forecast horizon or sensor history is unavailable
            pass

        current += timedelta(hours=1)

    if not slots:
        raise HTTPException(
            status_code=422,
            detail=(
                "No valid time slots in the requested window. "
                "Target horizon is outside available forecast window or insufficient sensor history."
            ),
        )

    diag = weather.get_cache_diagnostics()

    return ScheduleRecommendResponse(
        recommended_start=best_slot,
        device_name=req.device_name,
        rated_power_kw=req.rated_power_kw,
        slots=slots,
        history_mode=primary_history_mode,
        scheduling_disclosure={
            "method": "recursive_forecasting",
            "limitations": [
                "Load predictions beyond t+1 use recursively predicted values "
                "for recent lag features, not actual observations. Forecast error "
                "compounds with each additional step.",
                "Rolling mean/std features are computed from actual historical "
                "readings or benchmark profiles and are NOT updated with recursive predictions.",
                "T2M is from Open-Meteo forecast for all horizons.",
                "Per-horizon uncertainty growth is NOT modeled — the same bucketed "
                "sigma is applied at every horizon. This understates uncertainty "
                "at longer horizons (e.g. t+4 vs t+1).",
            ],
        },
        t2m_disclosure=weather.get_t2m_disclosure(),
        is_stale=diag.get("is_stale", False),
        cached_at=datetime.fromisoformat(diag["fetched_at"]) if diag.get("fetched_at") else None,
    )


# In-memory store for remote calibration commands and distinct dashboard command timestamps
pending_calibration_commands: dict[str, dict] = {}
last_command_timestamps: dict[str, str] = {}

# Pending relay commands: tracks per-load commanded values that haven't been confirmed by ESP32 telemetry.
# Structure: {device_id: {"loads": {"load_1": "solar", ...}, "ts": datetime}}
# Cleared per-load when ingest telemetry confirms applied_source matches the pending value.
# Auto-expires after 15 seconds (fallback for cases where physical selector blocks the command).
pending_relay_commands: dict[str, dict] = {}


@router.get("/api/device/status", response_model=DeviceStatusResponse)
@router.get("/device/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str = Query("esp32_main")):
    """Return active desired source states, distinct last_command_ts, and any pending calibration command."""
    sb = get_supabase()
    try:
        result = sb.table("device_controls").select("*").eq("device_id", device_id).execute()
        if result.data:
            row = result.data[0]
            l1 = row.get("load_1", "off")
            l2 = row.get("load_2", "off")
            l3 = row.get("load_3", "off")
            l4 = row.get("load_4", "off")
            up_at = row.get("updated_at")
        else:
            l1 = l2 = l3 = l4 = "off"
            up_at = None
    except Exception:
        # If database table not yet queried or connection issue, return safe default
        l1 = l2 = l3 = l4 = "off"
        up_at = None

    last_cmd_ts = last_command_timestamps.get(device_id)

    # Check for pending calibration command (active for up to 60s)
    cal_cmd = "NONE"
    if device_id in pending_calibration_commands:
        info = pending_calibration_commands[device_id]
        queued_at = info.get("queued_at")
        if queued_at and (datetime.now(timezone.utc) - queued_at).total_seconds() > 60:
            pending_calibration_commands.pop(device_id, None)
        else:
            cmd = info.get("command", "")
            val = info.get("value")
            if cmd == "CAL_ZERO":
                cal_cmd = "CAL_ZERO"
            elif cmd == "RESET_CAL":
                cal_cmd = "RESET_CAL"
            elif cmd in ("SET_VCAL", "SET_SENS") and val is not None:
                cal_cmd = f"{cmd} {val}"
            else:
                cal_cmd = cmd

    return DeviceStatusResponse(
        device_id=device_id,
        load_1=l1,
        load_2=l2,
        load_3=l3,
        load_4=l4,
        load1=l1,
        load2=l2,
        load3=l3,
        load4=l4,
        cal_command=cal_cmd,
        last_command_ts=last_cmd_ts,
        updated_at=up_at,
    )


@router.post("/api/device/control", response_model=DeviceControlResponse)
@router.post("/device/control", response_model=DeviceControlResponse)
async def update_device_control(req: DeviceControlRequest):
    """Update desired relay source state (grid/solar/off) for one or more loads with a unique last_command_ts."""
    sb = get_supabase()
    now = datetime.now(timezone.utc)
    command_ts_iso = now.isoformat()

    valid_sources = {"grid", "solar", "off"}
    for k, v in [("load_1", req.load_1), ("load_2", req.load_2), ("load_3", req.load_3), ("load_4", req.load_4)]:
        if v is not None and v.lower() not in valid_sources:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid source '{v}' for {k}. Must be 'grid', 'solar', or 'off'.",
            )

    current_data = {
        "load_1": "off",
        "load_2": "off",
        "load_3": "off",
        "load_4": "off",
    }
    try:
        existing = sb.table("device_controls").select("*").eq("device_id", req.device_id).execute()
        if existing.data:
            current_data.update(existing.data[0])
    except Exception:
        pass

    if req.load_1 is not None:
        current_data["load_1"] = req.load_1.lower()
    if req.load_2 is not None:
        current_data["load_2"] = req.load_2.lower()
    if req.load_3 is not None:
        current_data["load_3"] = req.load_3.lower()
    if req.load_4 is not None:
        current_data["load_4"] = req.load_4.lower()

    last_command_timestamps[req.device_id] = command_ts_iso

    # Track the specific loads that were commanded as pending until ESP32 confirms
    pending_loads = {}
    if req.load_1 is not None:
        pending_loads["load_1"] = req.load_1.lower()
    if req.load_2 is not None:
        pending_loads["load_2"] = req.load_2.lower()
    if req.load_3 is not None:
        pending_loads["load_3"] = req.load_3.lower()
    if req.load_4 is not None:
        pending_loads["load_4"] = req.load_4.lower()
    if pending_loads:
        pending_relay_commands[req.device_id] = {
            "loads": pending_loads,
            "ts": now,
        }

    upsert_data = {
        "device_id": req.device_id,
        "load_1": current_data["load_1"],
        "load_2": current_data["load_2"],
        "load_3": current_data["load_3"],
        "load_4": current_data["load_4"],
        "updated_at": command_ts_iso,
    }
    try:
        sb.table("device_controls").upsert(upsert_data).execute()
    except Exception:
        pass

    return DeviceControlResponse(
        device_id=req.device_id,
        load_1=current_data["load_1"],
        load_2=current_data["load_2"],
        load_3=current_data["load_3"],
        load_4=current_data["load_4"],
        status="updated",
        last_command_ts=command_ts_iso,
        updated_at=now,
    )


@router.post("/api/device/calibrate", response_model=CalibrateResponse)
@router.post("/device/calibrate", response_model=CalibrateResponse)
async def queue_calibration_command(req: CalibrateRequest):
    """Queue a remote calibration command for the ESP32 (polled via /api/device/status)."""
    now = datetime.now(timezone.utc)
    cmd = req.command.upper().strip()

    valid_commands = {"CAL_ZERO", "SET_VCAL", "SET_SENS", "RESET_CAL"}
    if cmd not in valid_commands:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid calibration command '{req.command}'. Must be one of {valid_commands}.",
        )

    if cmd in ("SET_VCAL", "SET_SENS"):
        if req.value is None or req.value <= 0:
            raise HTTPException(
                status_code=422,
                detail=f"Command '{cmd}' requires a positive numeric 'value' parameter.",
            )

    pending_calibration_commands[req.device_id] = {
        "command": cmd,
        "value": req.value,
        "queued_at": now,
    }

    return CalibrateResponse(
        device_id=req.device_id,
        command=cmd,
        value=req.value,
        status="queued",
        message=f"Calibration command '{cmd}' queued for ESP32 dispatch.",
        updated_at=now,
    )

