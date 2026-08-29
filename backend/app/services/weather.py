# Weather service — backend-owned Open-Meteo forecast retrieval
#
# The backend owns weather data retrieval. The frontend never needs
# provider-specific Open-Meteo logic.

import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Concurrency lock for forecast fetching
_fetch_lock: Optional[asyncio.Lock] = None


def _get_fetch_lock() -> asyncio.Lock:
    global _fetch_lock
    if _fetch_lock is None:
        _fetch_lock = asyncio.Lock()
    return _fetch_lock


# In-memory cache: stores the last fetched forecast
_cache: dict = {
    "fetched_at": None,          # datetime of last successful fetch
    "data": None,                # parsed hourly forecast dict
    "cache_ttl_seconds": 3600,   # 1 hour cache for successful responses
    "negative_ttl_seconds": 60,  # 60s backoff after a failed upstream fetch
    "last_error": None,          # string description of last fetch error
    "last_error_at": None,       # datetime of last fetch error
    "is_stale": False,           # True if serving cached data after a refresh failure
}


class WeatherForecastError(Exception):
    """Raised when Open-Meteo forecast retrieval fails."""
    pass


class ForecastHorizonError(Exception):
    """Raised when the requested time is outside the forecast horizon."""
    pass


async def _fetch_forecast() -> dict:
    """Fetch hourly forecast from Open-Meteo for Kaliakair, BD.

    Returns parsed JSON with hourly data keyed by ISO timestamp strings.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": settings.LATITUDE,
        "longitude": settings.LONGITUDE,
        "hourly": "cloud_cover,temperature_2m,relative_humidity_2m,wind_speed_10m",
        "forecast_days": settings.FORECAST_DAYS,
        "timezone": settings.TIMEZONE,
    }

    headers = {
        "User-Agent": "SolarMate-HEMS/0.1.1 (https://github.com/Masud744/solar-aware-hems; contact: hems-research@masud.dev)",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise WeatherForecastError(
            f"Weather forecast unavailable from Open-Meteo. "
            f"Cannot generate prediction without forecast features. "
            f"Error: {e}"
        )

    # Parse into a dict keyed by timestamp string for O(1) lookup
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    parsed = {}
    for i, ts_str in enumerate(times):
        parsed[ts_str] = {
            "cloud_cover": hourly["cloud_cover"][i],
            "temperature_2m": hourly["temperature_2m"][i],
            "relative_humidity_2m": hourly["relative_humidity_2m"][i],
            "wind_speed_10m": hourly["wind_speed_10m"][i],
        }

    return parsed


def _load_persisted_cache() -> bool:
    """Load persisted forecast from Supabase database to seed empty memory cache."""
    try:
        from app.database import get_supabase
        import json
        sb = get_supabase()
        res = sb.table("user_solar_estimates").select("*").eq("date", "2099-12-31").limit(1).execute()
        if res.data and res.data[0].get("notes"):
            payload = json.loads(res.data[0]["notes"])
            if payload.get("data") and payload.get("fetched_at"):
                _cache["data"] = payload["data"]
                _cache["fetched_at"] = datetime.fromisoformat(payload["fetched_at"])
                _cache["is_stale"] = True
                logger.info("Seeded weather cache from Supabase persistent store (fetched at %s).", _cache["fetched_at"])
                return True
    except Exception as e:
        logger.warning("Could not seed weather cache from Supabase: %s", e)
    return False


def _save_persisted_cache(data: dict, fetched_at: datetime):
    """Save latest forecast data to Supabase database for durability across reboots."""
    try:
        from app.database import get_supabase
        import json
        sb = get_supabase()
        payload = {
            "fetched_at": fetched_at.isoformat(),
            "data": data,
        }
        sb.table("user_solar_estimates").upsert({
            "date": "2099-12-31",
            "estimated_solar_kwh": 0.0,
            "notes": json.dumps(payload),
        }, on_conflict="date").execute()
    except Exception as e:
        logger.warning("Could not persist weather cache to Supabase: %s", e)


def _is_cache_fresh(now: datetime) -> bool:
    """Check if the cache has valid, fresh forecast data within the 1-hour TTL."""
    if _cache["data"] is None or _cache["fetched_at"] is None:
        return False
    return (now - _cache["fetched_at"]).total_seconds() <= _cache["cache_ttl_seconds"]


async def get_forecast_at(target_time: datetime) -> dict:
    """Get weather forecast values at the specified hour.

    Returns dict with keys: cloud_cover, temperature, relative_humidity, wind_speed
    (matching the model feature names, not the Open-Meteo variable names).

    Raises:
        ForecastHorizonError: if target_time is outside the available forecast
        WeatherForecastError: if Open-Meteo API is unreachable
    """
    global _cache

    now = datetime.now()

    # 1. Non-blocking check for fresh cache
    if not _is_cache_fresh(now):
        lock = _get_fetch_lock()
        async with lock:
            # Seed from database if memory cache is completely unpopulated
            if _cache["data"] is None:
                _load_persisted_cache()

            # 2. Re-check under lock (double-checked locking pattern)
            if not _is_cache_fresh(now):
                # Check negative cache / failure backoff if cache is empty
                if _cache["data"] is None and _cache["last_error_at"] is not None:
                    elapsed_err = (now - _cache["last_error_at"]).total_seconds()
                    if elapsed_err < _cache["negative_ttl_seconds"]:
                        remaining = int(_cache["negative_ttl_seconds"] - elapsed_err)
                        raise WeatherForecastError(
                            f"Weather forecast temporarily unavailable (upstream backoff active, retry in "
                            f"{remaining}s). Last error: {_cache['last_error']}"
                        )

                try:
                    new_data = await _fetch_forecast()
                    _cache["data"] = new_data
                    _cache["fetched_at"] = now
                    _cache["last_error"] = None
                    _cache["last_error_at"] = None
                    _cache["is_stale"] = False
                    _save_persisted_cache(new_data, now)
                except WeatherForecastError as e:
                    _cache["last_error"] = str(e)
                    _cache["last_error_at"] = now

                    # If we have last-known-good data, preserve it and serve stale
                    if _cache["data"] is not None:
                        _cache["is_stale"] = True
                        logger.warning(
                            "Open-Meteo refresh failed (%s). Serving last-known-good forecast from %s.",
                            e,
                            _cache["fetched_at"],
                        )
                    else:
                        raise

    forecast = _cache["data"]
    if forecast is None:
        raise WeatherForecastError(
            f"Weather forecast unavailable from Open-Meteo: {_cache.get('last_error', 'No forecast data')}"
        )

    # Build the lookup key — Open-Meteo returns timestamps like "2026-08-21T14:00"
    target_hour = target_time.replace(minute=0, second=0, microsecond=0)
    ts_key = target_hour.strftime("%Y-%m-%dT%H:%M")

    if ts_key not in forecast:
        available_times = sorted(forecast.keys())
        range_str = f"{available_times[0]} to {available_times[-1]}" if available_times else "empty"
        raise ForecastHorizonError(
            f"Target time {ts_key} is outside the available Open-Meteo forecast "
            f"horizon. Available range: {range_str} "
            f"({settings.FORECAST_DAYS}-day forecast from Kaliakair, BD). "
            f"Cannot generate prediction without forecast weather features."
        )

    wx = forecast[ts_key]

    return {
        "cloud_cover": wx["cloud_cover"],
        "temperature": wx["temperature_2m"],        # Solar model: 'temperature'
        "relative_humidity": wx["relative_humidity_2m"],
        "wind_speed": wx["wind_speed_10m"],
        "T2M": wx["temperature_2m"],                # Load model: 'T2M'
    }


def get_cache_diagnostics() -> dict:
    """Return cache diagnostics for observability and health checks."""
    now = datetime.now()
    return {
        "has_data": _cache["data"] is not None,
        "fetched_at": _cache["fetched_at"].isoformat() if _cache["fetched_at"] else None,
        "is_stale": _cache["is_stale"],
        "is_fresh": _is_cache_fresh(now),
        "last_error": _cache["last_error"],
        "last_error_at": _cache["last_error_at"].isoformat() if _cache["last_error_at"] else None,
    }


def get_t2m_disclosure() -> dict:
    """Standard T2M provenance disclosure included in every load prediction response."""
    return {
        "source": "Open-Meteo forecast API (temperature_2m)",
        "training_source": "NASA POWER reanalysis (T2M) for Sceaux, France",
        "provenance_note": (
            "The load model was trained on same-timestamp NASA POWER reanalysis T2M, "
            "not a genuine future weather forecast. Phase 2 reported metrics reflect "
            "performance with observed/reanalysis T2M, not forecast-sourced T2M. "
            "Additionally, the deployment location (Kaliakair, BD) differs from the "
            "training location (Sceaux, France). These provenance mismatches mean "
            "deployed performance may differ from reported backtest metrics."
        ),
    }
