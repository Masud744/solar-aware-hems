# Energy Accounting Service — Timestamp-based numerical integration & user solar tracking
import json
import zoneinfo
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.database import get_supabase
from app.config import settings

DHAKA_TZ = zoneinfo.ZoneInfo(settings.TIMEZONE)
DEFAULT_TARIFF_BDT_PER_KWH = 7.50


def get_dhaka_now() -> datetime:
    """Return current datetime in Asia/Dhaka."""
    return datetime.now(timezone.utc).astimezone(DHAKA_TZ)


def get_day_utc_bounds(date_str: str) -> tuple[datetime, datetime, str, str]:
    """Given 'YYYY-MM-DD', compute start and end UTC datetime and ISO strings.
    
    A calendar day in Asia/Dhaka (UTC+6) runs from 00:00:00 to 23:59:59.999 BST.
    In UTC, that is 18:00:00 UTC (previous day) to 17:59:59.999 UTC (current day).
    """
    local_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=DHAKA_TZ)
    local_end = local_start + timedelta(days=1)
    
    start_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)
    return start_utc, end_utc, start_utc.isoformat(), end_utc.isoformat()


def compute_integrated_energy_from_readings(readings: List[Dict[str, Any]]) -> float:
    """Numerically integrate power (W) over timestamped readings using the trapezoidal rule.
    
    Formula:
      E_kwh = sum( (P_{i-1} + P_i) / 2 * dt_sec / (3600 * 1000) )
    
    Caps dt at 300 seconds (5 mins) to prevent over-crediting offline/blackout intervals.
    """
    if len(readings) < 2:
        return 0.0
    
    # Sort chronologically
    sorted_readings = sorted(
        readings,
        key=lambda r: datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
    )
    
    total_kwh = 0.0
    for i in range(1, len(sorted_readings)):
        r_prev = sorted_readings[i - 1]
        r_curr = sorted_readings[i]
        
        t_prev = datetime.fromisoformat(r_prev["ts"].replace("Z", "+00:00"))
        t_curr = datetime.fromisoformat(r_curr["ts"].replace("Z", "+00:00"))
        
        dt_sec = (t_curr - t_prev).total_seconds()
        if 0 < dt_sec <= 300:  # Valid continuous segment
            p_prev = max(0.0, float(r_prev.get("power_w") or 0.0))
            p_curr = max(0.0, float(r_curr.get("power_w") or 0.0))
            avg_power_w = (p_prev + p_curr) / 2.0
            total_kwh += (avg_power_w * dt_sec) / (3600.0 * 1000.0)
            
    return round(total_kwh, 4)


def get_saved_solar_estimates() -> Dict[str, Dict[str, Any]]:
    """Retrieve all user solar estimates from Supabase.
    
    Tries dedicated table 'user_solar_estimates' first; falls back to 'user_actions'.
    Returns a dict mapping date string 'YYYY-MM-DD' -> {'kwh': float, 'ts': str, 'notes': str}.
    """
    sb = get_supabase()
    # 1. Try dedicated table 'user_solar_estimates'
    try:
        res = (
            sb.table("user_solar_estimates")
            .select("*")
            .order("date", desc=True)
            .limit(200)
            .execute()
        )
        if res.data is not None:
            estimates: Dict[str, Dict[str, Any]] = {}
            for row in res.data:
                d_str = str(row.get("date"))
                estimates[d_str] = {
                    "kwh": float(row.get("estimated_solar_kwh", 0.0)),
                    "ts": row.get("updated_at"),
                    "notes": row.get("notes", ""),
                }
            return estimates
    except Exception:
        pass

    # 2. Fallback to 'user_actions'
    try:
        res = (
            sb.table("user_actions")
            .select("*")
            .like("action", "solar_estimate:%")
            .order("ts", desc=True)
            .limit(200)
            .execute()
        )
        estimates: Dict[str, Dict[str, Any]] = {}
        for row in res.data:
            try:
                raw = row["action"].split("solar_estimate:", 1)[1]
                payload = json.loads(raw)
                d_str = payload.get("date")
                if d_str and d_str not in estimates:
                    estimates[d_str] = {
                        "kwh": float(payload.get("kwh", 0.0)),
                        "ts": row.get("ts"),
                        "notes": payload.get("notes", ""),
                    }
            except Exception:
                continue
        return estimates
    except Exception as e:
        print(f"Error fetching solar estimates: {e}")
        return {}


def save_user_solar_estimate(date_str: str, estimated_solar_kwh: float, notes: str = "") -> Dict[str, Any]:
    """Persist a user-entered solar contribution estimate into Supabase.
    
    Tries dedicated table 'user_solar_estimates' (upsert) first; falls back to 'user_actions'.
    Validates that estimated_solar_kwh >= 0.
    """
    if estimated_solar_kwh < 0.0:
        raise ValueError("Estimated solar energy cannot be negative.")
    
    sb = get_supabase()
    rounded_kwh = round(estimated_solar_kwh, 4)
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Try dedicated table 'user_solar_estimates'
    try:
        res = sb.table("user_solar_estimates").upsert({
            "date": date_str,
            "estimated_solar_kwh": rounded_kwh,
            "notes": notes,
            "updated_at": now_iso,
        }, on_conflict="date").execute()
        if res.data:
            return {
                "success": True,
                "date": date_str,
                "estimated_solar_kwh": rounded_kwh,
                "persisted_id": res.data[0].get("id"),
            }
    except Exception:
        pass

    # 2. Fallback to 'user_actions'
    payload = {
        "date": date_str,
        "kwh": rounded_kwh,
        "notes": notes,
    }
    action_str = f"solar_estimate:{json.dumps(payload)}"
    res = sb.table("user_actions").insert({"action": action_str}).execute()
    return {
        "success": True,
        "date": date_str,
        "estimated_solar_kwh": rounded_kwh,
        "persisted_id": res.data[0]["id"] if res.data else None,
    }


def get_daily_energy_accounting(date_str: Optional[str] = None, tariff_rate: float = DEFAULT_TARIFF_BDT_PER_KWH) -> Dict[str, Any]:
    """Get persistent energy accounting for a specific calendar date in Asia/Dhaka."""
    if not date_str:
        date_str = get_dhaka_now().strftime("%Y-%m-%d")
    
    _, _, start_iso, end_iso = get_day_utc_bounds(date_str)
    
    sb = get_supabase()
    # Fetch all esp32_main readings for this day
    all_readings = []
    offset = 0
    while True:
        res = (
            sb.table("sensor_readings")
            .select("ts, power_w")
            .eq("device_id", "esp32_main")
            .gte("ts", start_iso)
            .lt("ts", end_iso)
            .order("ts", desc=False)
            .range(offset, offset + 999)
            .execute()
        )
        if not res.data:
            break
        all_readings.extend(res.data)
        if len(res.data) < 1000:
            break
        offset += 1000

    total_measured_kwh = compute_integrated_energy_from_readings(all_readings)
    
    # Retrieve user solar estimate for this date
    all_estimates = get_saved_solar_estimates()
    user_estimate_info = all_estimates.get(date_str)
    
    has_estimate = user_estimate_info is not None
    user_solar_kwh = user_estimate_info["kwh"] if has_estimate else 0.0
    
    # Conservative solar accounting:
    # 1. Solar Utilized for Load = min(Total Measured Energy Used, User Estimated Solar Generation)
    # 2. Estimated Remaining Grid/Non-Solar Load = max(0, Total Measured Energy Used - Solar Utilized for Load)
    # 3. Estimated Excess Solar = max(0, User Estimated Solar Generation - Total Measured Energy Used)
    # 4. Estimated Savings = Solar Utilized for Load * Tariff
    solar_utilized_kwh = round(min(total_measured_kwh, user_solar_kwh), 4)
    estimated_remaining_kwh = round(max(0.0, total_measured_kwh - solar_utilized_kwh), 4)
    excess_solar_kwh = round(max(0.0, user_solar_kwh - total_measured_kwh), 4)
    estimated_savings_bdt = round(solar_utilized_kwh * tariff_rate, 2)
    
    first_ts = all_readings[0]["ts"] if all_readings else None
    last_ts = all_readings[-1]["ts"] if all_readings else None
    
    return {
        "date": date_str,
        "timezone": settings.TIMEZONE,
        "total_energy_kwh": total_measured_kwh,
        "user_solar_kwh": user_solar_kwh,
        "solar_utilized_kwh": solar_utilized_kwh,
        "has_user_solar_estimate": has_estimate,
        "estimated_savings_bdt": estimated_savings_bdt,
        "estimated_remaining_kwh": estimated_remaining_kwh,
        "excess_solar_kwh": excess_solar_kwh,
        "tariff_rate": tariff_rate,
        "reading_count": len(all_readings),
        "first_packet_ts": first_ts,
        "last_packet_ts": last_ts,
        "notes": user_estimate_info.get("notes", "") if user_estimate_info else "",
    }


def get_monthly_energy_accounting(month_str: Optional[str] = None, tariff_rate: float = DEFAULT_TARIFF_BDT_PER_KWH) -> Dict[str, Any]:
    """Get aggregated monthly energy accounting for 'YYYY-MM' via single batch query."""
    if not month_str:
        month_str = get_dhaka_now().strftime("%Y-%m")
    
    year, month = map(int, month_str.split("-"))
    first_day_local = datetime(year, month, 1, tzinfo=DHAKA_TZ)
    if month == 12:
        next_month_local = datetime(year + 1, 1, 1, tzinfo=DHAKA_TZ)
    else:
        next_month_local = datetime(year, month + 1, 1, tzinfo=DHAKA_TZ)
    
    start_utc_iso = first_day_local.astimezone(timezone.utc).isoformat()
    end_utc_iso = next_month_local.astimezone(timezone.utc).isoformat()
    
    sb = get_supabase()
    # Batch query all readings for the month
    all_readings = []
    offset = 0
    while True:
        res = (
            sb.table("sensor_readings")
            .select("ts, power_w")
            .eq("device_id", "esp32_main")
            .gte("ts", start_utc_iso)
            .lt("ts", end_utc_iso)
            .order("ts", desc=False)
            .range(offset, offset + 999)
            .execute()
        )
        if not res.data:
            break
        all_readings.extend(res.data)
        if len(res.data) < 1000:
            break
        offset += 1000
        
    # Group readings by Asia/Dhaka calendar date
    day_readings_map: Dict[str, List[Dict[str, Any]]] = {}
    for r in all_readings:
        try:
            dt = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(DHAKA_TZ)
            d_str = dt.strftime("%Y-%m-%d")
            if d_str not in day_readings_map:
                day_readings_map[d_str] = []
            day_readings_map[d_str].append(r)
        except Exception:
            continue
            
    saved_estimates = get_saved_solar_estimates()
    
    # Merge all active dates in this month
    all_active_dates = set(day_readings_map.keys())
    for d_est in saved_estimates.keys():
        if d_est.startswith(month_str):
            all_active_dates.add(d_est)
            
    daily_records = []
    total_measured_kwh = 0.0
    total_solar_kwh = 0.0
    total_solar_utilized_kwh = 0.0
    total_remaining_kwh = 0.0
    total_excess_solar_kwh = 0.0
    total_savings_bdt = 0.0
    
    for d_str in sorted(all_active_dates, reverse=True):
        readings_for_day = day_readings_map.get(d_str, [])
        measured_kwh = compute_integrated_energy_from_readings(readings_for_day)
        
        user_est = saved_estimates.get(d_str)
        has_est = user_est is not None
        solar_kwh = user_est["kwh"] if has_est else 0.0
        
        solar_utilized = round(min(measured_kwh, solar_kwh), 4)
        remaining_kwh = round(max(0.0, measured_kwh - solar_utilized), 4)
        excess_kwh = round(max(0.0, solar_kwh - measured_kwh), 4)
        savings_bdt = round(solar_utilized * tariff_rate, 2)
        
        daily_records.append({
            "date": d_str,
            "timezone": settings.TIMEZONE,
            "total_energy_kwh": measured_kwh,
            "user_solar_kwh": solar_kwh,
            "solar_utilized_kwh": solar_utilized,
            "has_user_solar_estimate": has_est,
            "estimated_savings_bdt": savings_bdt,
            "estimated_remaining_kwh": remaining_kwh,
            "excess_solar_kwh": excess_kwh,
            "tariff_rate": tariff_rate,
            "reading_count": len(readings_for_day),
            "first_packet_ts": readings_for_day[0]["ts"] if readings_for_day else None,
            "last_packet_ts": readings_for_day[-1]["ts"] if readings_for_day else None,
            "notes": user_est.get("notes", "") if user_est else "",
        })
        
        total_measured_kwh += measured_kwh
        total_solar_kwh += solar_kwh
        total_solar_utilized_kwh += solar_utilized
        total_remaining_kwh += remaining_kwh
        total_excess_solar_kwh += excess_kwh
        total_savings_bdt += savings_bdt
        
    return {
        "month": month_str,
        "timezone": settings.TIMEZONE,
        "total_energy_kwh": round(total_measured_kwh, 4),
        "total_solar_kwh": round(total_solar_kwh, 4),
        "total_solar_utilized_kwh": round(total_solar_utilized_kwh, 4),
        "total_savings_bdt": round(total_savings_bdt, 2),
        "total_remaining_kwh": round(total_remaining_kwh, 4),
        "total_excess_solar_kwh": round(total_excess_solar_kwh, 4),
        "days_recorded": len(daily_records),
        "tariff_rate": tariff_rate,
        "daily_records": daily_records,
    }
