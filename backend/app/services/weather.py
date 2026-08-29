# Weather service — backend-owned Open-Meteo forecast retrieval
#
# The backend owns weather data retrieval. The frontend never needs
# provider-specific Open-Meteo logic.

import httpx
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

# In-memory cache: stores the last fetched forecast
_cache: dict = {
    "fetched_at": None,  # datetime of last fetch
    "data": None,        # parsed hourly forecast dict
    "cache_ttl_seconds": 3600,  # 1 hour cache
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

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
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

    # Refresh cache if stale or empty
    if (
        _cache["data"] is None
        or _cache["fetched_at"] is None
        or (now - _cache["fetched_at"]).total_seconds() > _cache["cache_ttl_seconds"]
    ):
        _cache["data"] = await _fetch_forecast()
        _cache["fetched_at"] = now

    forecast = _cache["data"]

    # Build the lookup key — Open-Meteo returns timestamps like "2026-08-21T14:00"
    # Truncate to the hour
    target_hour = target_time.replace(minute=0, second=0, microsecond=0)
    ts_key = target_hour.strftime("%Y-%m-%dT%H:%M")

    if ts_key not in forecast:
        # Check if it's outside the horizon
        available_times = sorted(forecast.keys())
        raise ForecastHorizonError(
            f"Target time {ts_key} is outside the available Open-Meteo forecast "
            f"horizon. Available range: {available_times[0]} to {available_times[-1]} "
            f"({settings.FORECAST_DAYS}-day forecast from Kaliakair, BD). "
            f"Cannot generate prediction without forecast weather features."
        )

    wx = forecast[ts_key]

    # Map Open-Meteo variable names to model feature names
    return {
        "cloud_cover": wx["cloud_cover"],
        "temperature": wx["temperature_2m"],        # Solar model: 'temperature'
        "relative_humidity": wx["relative_humidity_2m"],
        "wind_speed": wx["wind_speed_10m"],
        "T2M": wx["temperature_2m"],                # Load model: 'T2M'
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
