# Controlled Safe HEMS Tools for AI Assistant
import json
import zoneinfo
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.config import settings
from app.database import get_supabase
from app.services import ml_models, weather, decision_engine, features, energy_accounting

DHAKA_TZ = zoneinfo.ZoneInfo(settings.TIMEZONE)


def get_dhaka_now() -> datetime:
    """Return current datetime in Asia/Dhaka."""
    return datetime.now(timezone.utc).astimezone(DHAKA_TZ)


def parse_target_datetime(time_str: Optional[str] = None) -> datetime:
    """Parse time string into an Asia/Dhaka aware datetime.
    
    Accepts ISO strings, 'YYYY-MM-DDTHH:MM:SS', or defaults to next hour if None.
    """
    now = get_dhaka_now()
    if not time_str or time_str.strip().lower() in ("now", "current", "latest"):
        return now.replace(minute=0, second=0, microsecond=0)
    
    if time_str.strip().lower() == "next_hour":
        return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    try:
        # Try standard ISO parsing
        clean_str = time_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=DHAKA_TZ)
        else:
            dt = dt.astimezone(DHAKA_TZ)
        return dt.replace(minute=0, second=0, microsecond=0)
    except Exception:
        # Fallback to current hour
        return now.replace(minute=0, second=0, microsecond=0)


# ── 1. Live Telemetry Tool ─────────────────────────────────────────────

async def tool_get_live_telemetry() -> Dict[str, Any]:
    """Retrieve the latest real-time physical sensor telemetry from the ESP32 hardware."""
    try:
        sb = get_supabase()
        res = (
            sb.table("sensor_readings")
            .select("*")
            .eq("device_id", "esp32_main")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {
                "status": "unavailable",
                "message": "No sensor readings found in database for device 'esp32_main'.",
                "provenance": "[MEASURED]"
            }
        
        row = res.data[0]
        ts_utc = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
        ts_dhaka = ts_utc.astimezone(DHAKA_TZ)
        age_seconds = (datetime.now(timezone.utc) - ts_utc).total_seconds()
        is_live = age_seconds < 120  # Live within 2 minutes

        return {
            "status": "live" if is_live else "stale",
            "age_seconds": round(age_seconds, 1),
            "timestamp_bst": ts_dhaka.strftime("%Y-%m-%d %I:%M:%S %p BST"),
            "power_w": round(row.get("power_w") or 0.0, 1),
            "voltage_v": round(row.get("voltage_v") or 0.0, 1),
            "current_a": round(row.get("current_a") or 0.0, 2),
            "power_factor": round(row.get("power_factor") or 1.0, 2),
            "temperature_c": round(row["temperature_c"], 1) if row.get("temperature_c") is not None else None,
            "humidity_pct": round(row["humidity_pct"], 1) if row.get("humidity_pct") is not None else None,
            "dht22_status": "available" if row.get("temperature_c") is not None else "unavailable",
            "cal_status": row.get("cal_status", "CALIBRATED"),
            "provenance": "[MEASURED]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to query live telemetry: {str(e)}"}


# ── 2. Relay Status Tool ───────────────────────────────────────────────

async def tool_get_relay_status() -> Dict[str, Any]:
    """Retrieve the current hardware routing states for all 4 controlled appliance circuits."""
    try:
        sb = get_supabase()
        res = (
            sb.table("device_controls")
            .select("*")
            .eq("device_id", "esp32_main")
            .limit(1)
            .execute()
        )
        ctrl = res.data[0] if res.data else {}

        circuits = {
            "load_1": {"name": "Washing Machine", "rated_power_kw": 1.20, "applied_source": ctrl.get("load_1", "grid")},
            "load_2": {"name": "Water Pump", "rated_power_kw": 0.75, "applied_source": ctrl.get("load_2", "solar")},
            "load_3": {"name": "Refrigerator", "rated_power_kw": 0.15, "applied_source": ctrl.get("load_3", "solar")},
            "load_4": {"name": "Rice Cooker", "rated_power_kw": 0.70, "applied_source": ctrl.get("load_4", "grid")},
        }
        return {
            "status": "success",
            "circuits": circuits,
            "provenance": "[MEASURED]",
            "note": "Authoritative hardware relay routing states. Physical relay actuation is restricted to manual dashboard controls."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to retrieve relay states: {str(e)}"}


# ── 3. Solar Forecast Tool ────────────────────────────────────────────

async def tool_get_solar_forecast(target_time_iso: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve solar generation prediction and uncertainty bounds for a target time."""
    target_dt = parse_target_datetime(target_time_iso)
    try:
        wx = await weather.get_forecast_at(target_dt)
        solar_features = {
            "cloud_cover": wx["cloud_cover"],
            "temperature": wx["temperature"],
            "relative_humidity": wx["relative_humidity"],
            "wind_speed": wx["wind_speed"],
            "hour": target_dt.hour,
            "month": target_dt.month,
            "day_of_year": target_dt.timetuple().tm_yday,
        }
        predicted_kw = ml_models.predict_solar(solar_features)
        sigma_kw, sigma_bucket = decision_engine.solar_sigma_bucket(wx["cloud_cover"])
        safe_kw = max(0.0, predicted_kw - settings.SAFETY_K * sigma_kw)

        return {
            "status": "success",
            "target_time_bst": target_dt.strftime("%Y-%m-%d %I:%M %p BST"),
            "predicted_solar_kw": round(predicted_kw, 3),
            "safe_solar_kw": round(safe_kw, 3),
            "uncertainty_sigma_kw": round(sigma_kw, 3),
            "cloud_cover_pct": wx["cloud_cover"],
            "temperature_c": wx["temperature"],
            "relative_humidity_pct": wx["relative_humidity"],
            "wind_speed_ms": wx["wind_speed"],
            "weather_bucket": sigma_bucket,
            "k_multiplier": settings.SAFETY_K,
            "weather_source": "Open-Meteo API for Kaliakair, BD",
            "provenance": "[FORECAST]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to calculate solar forecast: {str(e)}"}


# ── 4. Load Forecast Tool ─────────────────────────────────────────────

async def tool_get_load_forecast(target_time_iso: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve household load prediction and conservative load bound for a target time."""
    target_dt = parse_target_datetime(target_time_iso)
    try:
        wx = await weather.get_forecast_at(target_dt)
        load_features, provenance = features.build_load_features(target_dt, t2m=wx["T2M"])
        predicted_kw = ml_models.predict_load(load_features)
        sigma_kw, sigma_bucket = decision_engine.load_sigma_bucket(target_dt.hour)
        conservative_kw = predicted_kw + settings.SAFETY_K * sigma_kw

        return {
            "status": "success",
            "target_time_bst": target_dt.strftime("%Y-%m-%d %I:%M %p BST"),
            "predicted_load_kw": round(predicted_kw, 3),
            "conservative_load_kw": round(conservative_kw, 3),
            "uncertainty_sigma_kw": round(sigma_kw, 3),
            "diurnal_time_bucket": sigma_bucket,
            "k_multiplier": settings.SAFETY_K,
            "history_mode": provenance.get("mode", "real_history"),
            "provenance": "[FORECAST]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to calculate load forecast: {str(e)}"}


# ── 5. 24-Hour Horizon Summary Tool ───────────────────────────────────

async def tool_get_24h_horizon_summary() -> Dict[str, Any]:
    """Retrieve a summary of solar surplus availability and safe operating windows over the next 24 hours."""
    from app.routers.device import schedule_recommend
    from app.models.schemas import ScheduleRecommendRequest

    now = get_dhaka_now().replace(minute=0, second=0, microsecond=0)
    end = now + timedelta(hours=24)

    req = ScheduleRecommendRequest(
        device_name="Horizon Summary",
        rated_power_kw=0.001,
        duration_hours=1.0,
        window_start=now,
        window_end=end,
    )
    try:
        res = await schedule_recommend(req)
        slots = res.slots
        safe_slots = [s for s in slots if s.safe_surplus_kw > 0.001]
        peak_solar = max((s.safe_solar_kw for s in slots), default=0.0)
        peak_surplus_slot = max(slots, key=lambda s: s.safe_surplus_kw) if slots else None

        safe_hours_list = [
            s.start_time.strftime("%I:%M %p")
            for s in safe_slots
        ]

        return {
            "status": "success",
            "horizon_start_bst": now.strftime("%Y-%m-%d %I:%M %p BST"),
            "total_hours_evaluated": len(slots),
            "safe_operating_windows_count": len(safe_slots),
            "peak_safe_solar_kw": round(peak_solar, 3),
            "peak_safe_surplus_kw": round(peak_surplus_slot.safe_surplus_kw, 3) if peak_surplus_slot else 0.0,
            "peak_surplus_time_bst": peak_surplus_slot.start_time.strftime("%I:%M %p BST") if peak_surplus_slot else "None",
            "safe_hours": safe_hours_list,
            "provenance": "[CALCULATED]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to compute 24-hour horizon summary: {str(e)}"}


# ── 6. Appliance Safety Checker Tool ──────────────────────────────────

async def tool_check_appliance_safety(
    device_name: str,
    rated_power_kw: float,
    duration_hours: float = 1.0,
    target_time_iso: Optional[str] = None
) -> Dict[str, Any]:
    """Evaluate whether an appliance can safely run on solar surplus without causing grid deficit."""
    from app.routers.device import device_check
    from app.models.schemas import DeviceCheckRequest

    target_dt = parse_target_datetime(target_time_iso)
    req = DeviceCheckRequest(
        device_name=device_name,
        rated_power_kw=max(0.01, float(rated_power_kw)),
        duration_hours=max(0.05, float(duration_hours)),
        target_time=target_dt,
    )
    try:
        res = await device_check(req)
        resulting_margin = res.safe_surplus_kw - res.rated_power_kw
        return {
            "status": "success",
            "decision": res.decision,
            "device_name": res.device_name,
            "rated_power_kw": res.rated_power_kw,
            "duration_hours": res.duration_hours,
            "target_time_bst": target_dt.strftime("%Y-%m-%d %I:%M %p BST"),
            "safe_solar_kw": res.safe_solar_kw,
            "conservative_load_kw": res.conservative_load_kw,
            "safe_surplus_kw": res.safe_surplus_kw,
            "resulting_margin_kw": round(resulting_margin, 3),
            "reason": res.reason,
            "provenance": "[CALCULATED]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Appliance safety check failed: {str(e)}"}


# ── 7. Schedule Recommendation Tool ───────────────────────────────────

async def tool_get_schedule_recommendation(
    device_name: str,
    rated_power_kw: float,
    duration_hours: float = 1.0,
    window_start_iso: Optional[str] = None,
    window_end_iso: Optional[str] = None
) -> Dict[str, Any]:
    """Find the optimal forecast start time for an appliance across a 24-hour horizon."""
    from app.routers.device import schedule_recommend
    from app.models.schemas import ScheduleRecommendRequest

    now = get_dhaka_now().replace(minute=0, second=0, microsecond=0)
    start_dt = parse_target_datetime(window_start_iso) if window_start_iso else now
    end_dt = parse_target_datetime(window_end_iso) if window_end_iso else start_dt + timedelta(hours=24)

    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=24)

    req = ScheduleRecommendRequest(
        device_name=device_name,
        rated_power_kw=max(0.01, float(rated_power_kw)),
        duration_hours=max(0.05, float(duration_hours)),
        window_start=start_dt,
        window_end=end_dt,
    )
    try:
        res = await schedule_recommend(req)
        cycle_kwh = req.rated_power_kw * req.duration_hours
        est_tariff_cost = round(cycle_kwh * 7.50, 2)

        return {
            "status": "success",
            "device_name": res.device_name,
            "rated_power_kw": res.rated_power_kw,
            "duration_hours": req.duration_hours,
            "recommended_start_bst": res.recommended_start.strftime("%Y-%m-%d %I:%M %p BST") if res.recommended_start else None,
            "is_window_found": res.recommended_start is not None,
            "estimated_cycle_kwh": round(cycle_kwh, 3),
            "estimated_cycle_tariff_cost_bdt": est_tariff_cost,
            "provenance": "[CALCULATED]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to compute schedule recommendation: {str(e)}"}


# ── 8. Configured Appliances List Tool ────────────────────────────────

def tool_get_configured_appliances() -> Dict[str, Any]:
    """Return the list and technical ratings of predefined configured appliances in the HEMS."""
    return {
        "status": "success",
        "appliances": [
            {
                "key": "load_1",
                "name": "Washing Machine",
                "rated_power_kw": 1.20,
                "duration_minutes": 45,
                "shiftable": True,
                "typical_use": "Shiftable laundry wash cycle"
            },
            {
                "key": "load_2",
                "name": "Water Pump",
                "rated_power_kw": 0.75,
                "duration_minutes": 30,
                "shiftable": True,
                "typical_use": "Shiftable rooftop water tank pumping"
            },
            {
                "key": "load_3",
                "name": "Refrigerator",
                "rated_power_kw": 0.15,
                "duration_minutes": 1440,
                "shiftable": False,
                "typical_use": "24/7 continuous essential baseload (excluded from shift scheduling)"
            },
            {
                "key": "load_4",
                "name": "Rice Cooker",
                "rated_power_kw": 0.70,
                "duration_minutes": 40,
                "shiftable": True,
                "typical_use": "Shiftable meal preparation cycle"
            }
        ],
        "provenance": "[CONFIGURED]"
    }


# ── 9. Energy & Cost Accounting Tool ──────────────────────────────────

async def tool_get_energy_summary(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve persistent energy accounting totals (measured energy, user solar, solar savings)."""
    try:
        dhaka_now = get_dhaka_now()
        target_date = date_str if date_str else dhaka_now.strftime("%Y-%m-%d")
        month_str = target_date[:7]

        daily_data = energy_accounting.get_daily_energy_accounting(target_date)
        monthly_data = energy_accounting.get_monthly_energy_accounting(month_str)

        return {
            "status": "success",
            "date": target_date,
            "month": month_str,
            "today": {
                "total_measured_energy_kwh": daily_data["total_energy_kwh"],
                "user_solar_estimate_kwh": daily_data["user_solar_kwh"],
                "solar_utilized_for_load_kwh": daily_data["solar_utilized_kwh"],
                "estimated_remaining_grid_load_kwh": daily_data["estimated_remaining_kwh"],
                "excess_solar_kwh": daily_data["excess_solar_kwh"],
                "estimated_solar_savings_bdt": daily_data["estimated_savings_bdt"],
                "has_user_solar_estimate": daily_data["has_user_solar_estimate"],
                "packets_integrated_count": daily_data["reading_count"],
            },
            "this_month": {
                "total_measured_energy_kwh": monthly_data["total_energy_kwh"],
                "total_user_solar_estimate_kwh": monthly_data["total_solar_kwh"],
                "total_solar_utilized_kwh": monthly_data["total_solar_utilized_kwh"],
                "total_estimated_savings_bdt": monthly_data["total_savings_bdt"],
                "days_recorded": monthly_data["days_recorded"],
            },
            "baseline_tariff_bdt_per_kwh": 7.50,
            "provenance": "[CALCULATED]",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to retrieve energy accounting: {str(e)}"}


# ── 10. User Solar Estimate Update Tool ────────────────────────────────

async def tool_update_user_solar_estimate(
    estimated_solar_kwh: float,
    date_str: Optional[str] = None,
    confirmed: bool = False,
    notes: str = ""
) -> Dict[str, Any]:
    """Persist or request confirmation to update daily user-estimated solar generation in Supabase."""
    dhaka_now = get_dhaka_now()
    target_date = date_str if date_str else dhaka_now.strftime("%Y-%m-%d")

    if estimated_solar_kwh < 0:
        return {
            "status": "error",
            "message": "Estimated solar generation cannot be negative."
        }

    if not confirmed:
        return {
            "status": "confirmation_required",
            "date": target_date,
            "estimated_solar_kwh": round(estimated_solar_kwh, 2),
            "message": f"Please confirm: Do you want me to save {estimated_solar_kwh:.2f} kWh as user-estimated solar generation for {target_date}?",
            "requires_user_confirmation": True
        }

    try:
        res = energy_accounting.save_user_solar_estimate(
            date_str=target_date,
            estimated_solar_kwh=estimated_solar_kwh,
            notes=notes
        )
        return {
            "status": "saved",
            "date": target_date,
            "estimated_solar_kwh": round(estimated_solar_kwh, 2),
            "message": f"Successfully saved {estimated_solar_kwh:.2f} kWh as user-estimated solar generation for {target_date} into Supabase.",
            "provenance": "[USER ESTIMATED]"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to save solar estimate: {str(e)}"}


# ── Tool Definitions Schema for Groq Function Calling ─────────────────

HEMS_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_live_telemetry",
            "description": "Get real-time physical sensor readings from the ESP32 (active power in W, voltage in V, current in A, power factor, DHT22 room temperature in °C, humidity in %, and telemetry age).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_relay_status",
            "description": "Get the current physical relay routing states (Grid vs Solar Bank vs Off) for the 4 controlled appliance circuits.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_solar_forecast",
            "description": "Get the ML solar generation forecast (kW), safe solar bound (kW), cloud cover (%), and weather conditions for a given hour or next hour.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_time_iso": {
                        "type": "string",
                        "description": "Optional ISO datetime string (e.g. '2026-08-29T14:00:00') or 'next_hour'. Defaults to next full hour.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_load_forecast",
            "description": "Get the ML household load forecast (kW) and conservative load bound (kW with k=1.0 uncertainty) for a given hour or next hour.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_time_iso": {
                        "type": "string",
                        "description": "Optional ISO datetime string (e.g. '2026-08-29T18:00:00') or 'next_hour'. Defaults to next full hour.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_24h_horizon_summary",
            "description": "Get the 24-hour horizon summary of peak solar generation, peak safe surplus, and list of all safe operating windows.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_appliance_safety",
            "description": "Check if an appliance can safely run on solar surplus without causing grid draw (ALLOW vs DENY verdict based on continuous surplus).",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the appliance (e.g., 'Heater', 'Washing Machine', 'Rice Cooker', 'EV Charger').",
                    },
                    "rated_power_kw": {
                        "type": "number",
                        "description": "Rated power consumption of the appliance in kilowatts (kW), e.g. 1.5 for 1500W.",
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Expected run duration in hours, e.g. 2.0 for 2 hours, 0.75 for 45 mins.",
                    },
                    "target_time_iso": {
                        "type": "string",
                        "description": "Optional start time in ISO format (e.g. '2026-08-29T12:00:00'). Defaults to current hour.",
                    },
                },
                "required": ["device_name", "rated_power_kw"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule_recommendation",
            "description": "Find the optimal forecast start time for an appliance across the next 24 hours to maximize solar surplus utilization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the appliance (e.g. 'Washing Machine', 'Water Pump', 'Space Heater').",
                    },
                    "rated_power_kw": {
                        "type": "number",
                        "description": "Rated power consumption in kW (e.g. 1.2).",
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Run duration in hours (e.g. 0.75 for 45 mins, 2.0 for 2 hours).",
                    },
                    "window_start_iso": {
                        "type": "string",
                        "description": "Optional earliest start time ISO string.",
                    },
                    "window_end_iso": {
                        "type": "string",
                        "description": "Optional latest end time ISO string.",
                    },
                },
                "required": ["device_name", "rated_power_kw"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_configured_appliances",
            "description": "Get the technical ratings and duration presets for the 4 configured residential appliances (Washing Machine, Water Pump, Refrigerator, Rice Cooker).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_energy_summary",
            "description": "Get persistent energy and tariff savings accounting (Total Energy Used in kWh, User-Estimated Solar Generation in kWh, Solar Utilized for Load in kWh, Remaining Grid Load, and Estimated Savings in BDT).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "Optional date string 'YYYY-MM-DD'. Defaults to today (Asia/Dhaka).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_solar_estimate",
            "description": "Update or save the user-reported solar generation estimate (kWh) for a calendar date in Supabase. Supports confirmation flow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "estimated_solar_kwh": {
                        "type": "number",
                        "description": "Estimated solar generation in kilowatt-hours (kWh), e.g. 3.0.",
                    },
                    "date_str": {
                        "type": "string",
                        "description": "Optional date in 'YYYY-MM-DD' format. Defaults to today.",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Set to True ONLY IF the user has explicitly confirmed the save/update action. If user hasn't explicitly confirmed yet, set to False.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes regarding weather or generation.",
                    },
                },
                "required": ["estimated_solar_kwh"],
            },
        },
    },
]


async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Execute a tool call safely and return structured result and data provenance tag."""
    if tool_name == "get_live_telemetry":
        res = await tool_get_live_telemetry()
        return res, "[MEASURED]"
    
    elif tool_name == "get_relay_status":
        res = await tool_get_relay_status()
        return res, "[MEASURED]"
    
    elif tool_name == "get_solar_forecast":
        res = await tool_get_solar_forecast(arguments.get("target_time_iso"))
        return res, "[FORECAST]"
    
    elif tool_name == "get_load_forecast":
        res = await tool_get_load_forecast(arguments.get("target_time_iso"))
        return res, "[FORECAST]"
    
    elif tool_name == "get_24h_horizon_summary":
        res = await tool_get_24h_horizon_summary()
        return res, "[CALCULATED]"
    
    elif tool_name == "check_appliance_safety":
        res = await tool_check_appliance_safety(
            device_name=arguments.get("device_name", "Appliance"),
            rated_power_kw=float(arguments.get("rated_power_kw", 1.0)),
            duration_hours=float(arguments.get("duration_hours", 1.0)),
            target_time_iso=arguments.get("target_time_iso")
        )
        return res, "[CALCULATED]"
    
    elif tool_name == "get_schedule_recommendation":
        res = await tool_get_schedule_recommendation(
            device_name=arguments.get("device_name", "Appliance"),
            rated_power_kw=float(arguments.get("rated_power_kw", 1.0)),
            duration_hours=float(arguments.get("duration_hours", 1.0)),
            window_start_iso=arguments.get("window_start_iso"),
            window_end_iso=arguments.get("window_end_iso")
        )
        return res, "[CALCULATED]"
    
    elif tool_name == "get_configured_appliances":
        res = tool_get_configured_appliances()
        return res, "[CONFIGURED]"
    
    elif tool_name == "get_energy_summary":
        res = await tool_get_energy_summary(arguments.get("date_str"))
        return res, "[CALCULATED]"
    
    elif tool_name == "update_user_solar_estimate":
        res = await tool_update_user_solar_estimate(
            estimated_solar_kwh=float(arguments.get("estimated_solar_kwh", 0.0)),
            date_str=arguments.get("date_str"),
            confirmed=bool(arguments.get("confirmed", False)),
            notes=arguments.get("notes", "")
        )
        return res, "[USER ESTIMATED]"
    
    else:
        return {"status": "error", "message": f"Unknown tool name '{tool_name}'"}, "[UNKNOWN]"
