# Weather service — backend-owned Open-Meteo forecast retrieval
#
# The backend owns weather data retrieval. The frontend never needs
# provider-specific Open-Meteo logic.

import asyncio
import logging
import random
import httpx
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Concurrency lock for forecast fetching
_fetch_lock: Optional[asyncio.Lock] = None

PERSISTENT_CACHE_KEY = "openmeteo_kaliakair_hourly_7d"


def _get_fetch_lock() -> asyncio.Lock:
    global _fetch_lock
    if _fetch_lock is None:
        _fetch_lock = asyncio.Lock()
    return _fetch_lock


# In-memory cache: stores the last fetched forecast
_cache: dict = {
    "fetched_at": None,                  # datetime of last successful fetch
    "data": None,                        # parsed hourly forecast dict
    "cache_ttl_seconds": 3600,           # 1 hour cache for successful responses
    "negative_ttl_seconds": 60,          # 60s backoff after non-429 upstream fetch errors
    "rate_limit_cooldown_seconds": 300, # 300s (5m) backoff after HTTP 429 rate limit
    "cooldown_until": None,              # datetime until which upstream calls are blocked
    "last_error": None,                  # string description of last fetch error
    "last_error_at": None,               # datetime of last fetch error
    "is_stale": False,                   # True if serving cached data after a refresh failure
}


class WeatherForecastError(Exception):
    """Raised when Open-Meteo forecast retrieval fails."""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[float] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after



class ForecastHorizonError(Exception):
    """Raised when the requested time is outside the forecast horizon."""
    pass


def validate_cached_payload(payload: dict) -> bool:
    """Validate structural integrity and geographical provenance of cached forecast payload."""
    if not isinstance(payload, dict):
        return False

    meta = payload.get("metadata", {})
    hourly = payload.get("hourly")

    # If payload wraps metadata and hourly (new schema)
    if isinstance(hourly, dict) and hourly:
        lat = meta.get("latitude", 0.0)
        lon = meta.get("longitude", 0.0)
        if abs(lat - settings.LATITUDE) > 0.05 or abs(lon - settings.LONGITUDE) > 0.05:
            logger.warning(
                "Cached forecast rejected: coordinates (%s, %s) do not match settings (%s, %s).",
                lat, lon, settings.LATITUDE, settings.LONGITUDE
            )
            return False
        if meta.get("timezone") != settings.TIMEZONE:
            logger.warning("Cached forecast rejected: timezone '%s' != '%s'.", meta.get("timezone"), settings.TIMEZONE)
            return False
        fetched_at_str = meta.get("fetched_at")
        if not fetched_at_str:
            return False
        try:
            fetched_dt = datetime.fromisoformat(fetched_at_str)
            if fetched_dt > datetime.now() + timedelta(minutes=5):
                logger.warning("Cached forecast rejected: fetched_at is in the future (%s).", fetched_dt)
                return False
        except (ValueError, TypeError):
            return False
        return True

    # Legacy payload format (direct hourly dict)
    legacy_data = payload.get("data")
    if isinstance(legacy_data, dict) and legacy_data:
        return True

    return False


def validate_forecast_entry(entry: dict) -> bool:
    """Validate that a single hourly forecast record contains all required features within physical bounds."""
    if not isinstance(entry, dict):
        return False

    required_keys = ("cloud_cover", "temperature_2m", "relative_humidity_2m", "wind_speed_10m")
    for k in required_keys:
        if k not in entry or entry[k] is None:
            return False
        if not isinstance(entry[k], (int, float)):
            return False

    # Physical range sanity checks for Kaliakair meteorological domain
    if not (0.0 <= float(entry["cloud_cover"]) <= 100.0):
        return False
    if not (-10.0 <= float(entry["temperature_2m"]) <= 55.0):
        return False
    if not (0.0 <= float(entry["relative_humidity_2m"]) <= 100.0):
        return False
    if not (0.0 <= float(entry["wind_speed_10m"]) <= 150.0):
        return False

    return True


def _get_cooldown_until() -> Optional[datetime]:
    """Return the datetime when upstream cooldown expires, or None."""
    if _cache.get("last_error_at") is None or _cache.get("cooldown_seconds") is None:
        return None
    return _cache["last_error_at"] + timedelta(seconds=_cache["cooldown_seconds"])


def _is_cooldown_active(now: datetime) -> bool:
    """Check if upstream fetch cooldown is currently active.

    A cooldown is active when a previous upstream fetch failed and the elapsed
    time since last_error_at is less than cooldown_seconds (or negative_ttl_seconds).
    """
    err_at = _cache.get("last_error_at")
    if err_at is None:
        return False
    e_at = err_at.replace(tzinfo=None) if err_at.tzinfo else err_at
    n = now.replace(tzinfo=None) if now.tzinfo else now
    cooldown_secs = _cache.get("cooldown_seconds") or _cache.get("negative_ttl_seconds", 60)
    return (n - e_at).total_seconds() < cooldown_secs


def _get_remaining_cooldown_seconds(now: datetime) -> int:
    """Return remaining cooldown seconds, or 0 if inactive."""
    if not _is_cooldown_active(now):
        return 0
    err_at = _cache["last_error_at"]
    e_at = err_at.replace(tzinfo=None) if err_at.tzinfo else err_at
    n = now.replace(tzinfo=None) if now.tzinfo else now
    cooldown_secs = _cache.get("cooldown_seconds") or _cache.get("negative_ttl_seconds", 60)
    return max(1, int(cooldown_secs - (n - e_at).total_seconds()))


def _extract_cooldown_seconds(e: WeatherForecastError) -> int:
    """Determine upstream cooldown duration based on error and Retry-After header.

    Policy:
    1. If the upstream HTTP response provided a 'Retry-After' header with a positive value,
       respect it (bounded between 5s and 3600s).
    2. Otherwise, enforce the configured negative TTL backoff window
       (default: _cache['negative_ttl_seconds'] = 60s).
    """
    retry_after = getattr(e, "retry_after", None)
    if retry_after is not None and retry_after > 0:
        return int(min(3600.0, max(5.0, retry_after)))
    return _cache.get("negative_ttl_seconds", 60)



async def _fetch_forecast() -> dict:
    """Fetch hourly forecast from Open-Meteo for Kaliakair, BD.

    Uses exponential backoff with jitter and Retry-After support to gracefully
    handle HTTP 429 rate-limiting without spawning request storms.

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

    max_retries = 2  # Total of 3 attempts
    data = None

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                break
        except httpx.HTTPStatusError as e:
            ra_header = e.response.headers.get("Retry-After")
            retry_after = None
            if ra_header:
                try:
                    retry_after = float(ra_header)
                except (ValueError, TypeError):
                    pass

            if e.response.status_code == 429 and attempt < max_retries:
                # 1. Check for Retry-After header
                wait_time = None
                if retry_after is not None and 0 < retry_after <= 5.0:
                    wait_time = retry_after

                # 2. Bounded exponential backoff with additive jitter (Attempt 0: ~1.1-1.4s, Attempt 1: ~2.1-2.4s, Cap: 4.0s)
                if wait_time is None:
                    base_backoff = 1.0 * (2 ** attempt)
                    wait_time = min(4.0, base_backoff) + random.uniform(0.1, 0.4)

                logger.warning(
                    "Open-Meteo returned 429 Too Many Requests (attempt %d/%d). "
                    "Applying exponential backoff with jitter: waiting %.2fs...",
                    attempt + 1, max_retries + 1, wait_time
                )
                await asyncio.sleep(wait_time)
                continue

            raise WeatherForecastError(
                f"Weather forecast unavailable from Open-Meteo. "
                f"Cannot generate prediction without forecast features. "
                f"Error: {e}",
                status_code=e.response.status_code,
                retry_after=retry_after,
            )
        except httpx.HTTPError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise WeatherForecastError(
                f"Weather forecast unavailable from Open-Meteo. "
                f"Cannot generate prediction without forecast features. "
                f"Error: {e}",
                status_code=status_code,
            )

    if data is None:
        raise WeatherForecastError("Weather forecast unavailable from Open-Meteo: empty response.")

    # Parse into a dict keyed by timestamp string for O(1) lookup
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    parsed = {}
    for i, ts_str in enumerate(times):
        entry = {
            "cloud_cover": hourly["cloud_cover"][i],
            "temperature_2m": hourly["temperature_2m"][i],
            "relative_humidity_2m": hourly["relative_humidity_2m"][i],
            "wind_speed_10m": hourly["wind_speed_10m"][i],
        }
        if validate_forecast_entry(entry):
            parsed[ts_str] = entry

    if not parsed:
        raise WeatherForecastError("Open-Meteo response contained no valid hourly forecast points.")

    return parsed


def _load_persisted_cache() -> bool:
    """Load persisted forecast from Supabase database to seed empty memory cache.

    Checks dedicated 'system_persistent_cache' table first; falls back to legacy
    'user_solar_estimates' (date = '2099-12-31') if table is not yet created.
    """
    try:
        from app.database import get_supabase
        import json
        sb = get_supabase()

        # 1. Primary path: dedicated system_persistent_cache table
        try:
            res = sb.table("system_persistent_cache").select("*").eq("cache_key", PERSISTENT_CACHE_KEY).limit(1).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                payload = row.get("payload")
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict) and validate_cached_payload(payload):
                    hourly = payload.get("hourly", {})
                    fetched_at_str = row.get("fetched_at") or payload.get("metadata", {}).get("fetched_at")
                    if hourly and fetched_at_str:
                        dt = datetime.fromisoformat(fetched_at_str)
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
                        _cache["data"] = hourly
                        _cache["fetched_at"] = dt
                        _cache["is_stale"] = True
                        logger.info(
                            "Seeded weather cache from system_persistent_cache (fetched at %s, %d hours).",
                            _cache["fetched_at"], len(hourly)
                        )
                        return True
        except Exception as e:
            logger.debug("Could not read from system_persistent_cache (may not exist yet): %s", e)

        # 2. Legacy fallback path: user_solar_estimates sentinel row
        try:
            res = sb.table("user_solar_estimates").select("*").eq("date", "2099-12-31").limit(1).execute()
            if res.data and res.data[0].get("notes"):
                payload = json.loads(res.data[0]["notes"])
                if isinstance(payload, dict) and validate_cached_payload(payload):
                    legacy_data = payload.get("data") or payload.get("hourly")
                    legacy_fetched_at = payload.get("fetched_at") or payload.get("metadata", {}).get("fetched_at")
                    if legacy_data and legacy_fetched_at:
                        dt = datetime.fromisoformat(legacy_fetched_at)
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
                        _cache["data"] = legacy_data
                        _cache["fetched_at"] = dt
                        _cache["is_stale"] = True
                        logger.info(
                            "Seeded weather cache from legacy user_solar_estimates sentinel store (fetched at %s).",
                            _cache["fetched_at"]
                        )
                        return True
        except Exception as e:
            logger.warning("Could not seed weather cache from legacy Supabase store: %s", e)

    except Exception as e:
        logger.warning("Could not seed weather cache from Supabase: %s", e)

    return False


def _save_persisted_cache(data: dict, fetched_at: datetime):
    """Save latest forecast data to Supabase database for durability across reboots.

    Writes to dedicated 'system_persistent_cache' table first; falls back to legacy
    'user_solar_estimates' (date = '2099-12-31') if table does not exist.
    """
    try:
        from app.database import get_supabase
        import json
        sb = get_supabase()

        payload = {
            "metadata": {
                "latitude": settings.LATITUDE,
                "longitude": settings.LONGITUDE,
                "timezone": settings.TIMEZONE,
                "forecast_days": settings.FORECAST_DAYS,
                "fetched_at": fetched_at.isoformat(),
                "source": "Open-Meteo forecast API",
            },
            "hourly": data,
        }

        # 1. Primary write to dedicated system_persistent_cache
        try:
            sb.table("system_persistent_cache").upsert({
                "cache_key": PERSISTENT_CACHE_KEY,
                "payload": payload,
                "fetched_at": fetched_at.isoformat(),
                "updated_at": datetime.now().isoformat(),
            }, on_conflict="cache_key").execute()
            logger.info("Persisted forecast cache to system_persistent_cache.")
            return
        except Exception as e:
            logger.debug("Could not write to system_persistent_cache (will attempt legacy fallback): %s", e)

        # 2. Fallback write to user_solar_estimates sentinel row
        sb.table("user_solar_estimates").upsert({
            "date": "2099-12-31",
            "estimated_solar_kwh": 0.0,
            "notes": json.dumps(payload),
        }, on_conflict="date").execute()
        logger.info("Persisted forecast cache to legacy user_solar_estimates.")
    except Exception as e:
        logger.warning("Could not persist weather cache to Supabase: %s", e)


def _is_cache_fresh(now: datetime) -> bool:
    """Check if the cache has valid, fresh forecast data within the 1-hour TTL."""
    if _cache["data"] is None or _cache["fetched_at"] is None:
        return False
    cached_at = _cache["fetched_at"]
    if cached_at.tzinfo is not None:
        cached_at = cached_at.replace(tzinfo=None)
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return (now - cached_at).total_seconds() <= _cache["cache_ttl_seconds"]


async def get_forecast_at(target_time: datetime) -> dict:
    """Get weather forecast values at the specified hour.

    Returns dict with keys: cloud_cover, temperature, relative_humidity, wind_speed
    (matching the model feature names, not the Open-Meteo variable names).

    Raises:
        ForecastHorizonError: if target_time is outside the available forecast
        WeatherForecastError: if Open-Meteo API is unreachable and no valid cache exists
    """
    global _cache

    now = datetime.now()

    # Fast path 1: Fresh in-memory cache (within 1-hour TTL)
    # Fast path 2: Stale in-memory cache AND upstream cooldown is active
    # In both cases, do not acquire lock and do not call upstream!
    if not _is_cache_fresh(now):
        # If cooldown is active and we already have cached forecast data,
        # immediately bypass upstream and serve the stale forecast.
        if _cache["data"] is not None and _is_cooldown_active(now):
            pass  # Fast path: proceed directly to forecast extraction below
        else:
            lock = _get_fetch_lock()
            async with lock:
                # Seed from database if memory cache is completely unpopulated
                if _cache["data"] is None:
                    _load_persisted_cache()

                # Re-check under lock (double-checked locking pattern)
                if not _is_cache_fresh(now):
                    # Check if cooldown is active (e.g. set by another concurrent coroutine)
                    if _is_cooldown_active(now):
                        if _cache["data"] is None:
                            remaining = _get_remaining_cooldown_seconds(now)
                            raise WeatherForecastError(
                                f"Weather forecast temporarily unavailable (upstream backoff active, retry in "
                                f"{remaining}s). Last error: {_cache['last_error']}"
                            )
                        # Else: we have cached data, bypass upstream fetch and serve stale
                    else:
                        try:
                            new_data = await _fetch_forecast()
                            _cache["data"] = new_data
                            _cache["fetched_at"] = now
                            _cache["last_error"] = None
                            _cache["last_error_at"] = None
                            _cache["cooldown_seconds"] = None
                            _cache["is_stale"] = False
                            _save_persisted_cache(new_data, now)
                        except WeatherForecastError as e:
                            _cache["last_error"] = str(e)
                            _cache["last_error_at"] = now
                            cooldown_secs = _extract_cooldown_seconds(e)
                            _cache["cooldown_seconds"] = cooldown_secs

                            # If we have last-known-good data, preserve it and serve stale (NO 24H HARD DROP)
                            if _cache["data"] is not None:
                                _cache["is_stale"] = True
                                c_until = _get_cooldown_until()
                                c_until_str = c_until.strftime("%Y-%m-%d %H:%M:%S") if c_until else "unknown"
                                logger.warning(
                                    "Open-Meteo refresh failed (%s). Serving last-known-good forecast from %s. "
                                    "Upstream cooldown active for %ds until %s.",
                                    e,
                                    _cache["fetched_at"],
                                    cooldown_secs,
                                    c_until_str,
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

    if not validate_forecast_entry(wx):
        raise WeatherForecastError(
            f"Cached forecast entry for {ts_key} failed physical feature validation: {wx}"
        )

    return {
        "cloud_cover": wx["cloud_cover"],
        "temperature": wx["temperature_2m"],        # Solar model: 'temperature'
        "relative_humidity": wx["relative_humidity_2m"],
        "wind_speed": wx["wind_speed_10m"],
        "T2M": wx["temperature_2m"],                # Load model: 'T2M'
        "is_stale": _cache.get("is_stale", False),
        "cached_at": _cache.get("fetched_at"),
        "data_source": "cached_persisted_forecast" if _cache.get("is_stale", False) else "live_upstream_forecast",
        "weather_source": (
            "Open-Meteo forecast API (Cached Fallback)"
            if _cache.get("is_stale", False)
            else "Open-Meteo forecast API"
        ),
    }


def get_cache_diagnostics() -> dict:
    """Return cache diagnostics for observability and health checks."""
    now = datetime.now()
    cooldown_until = _get_cooldown_until()
    cooldown_active = _is_cooldown_active(now)
    remaining_cooldown = _get_remaining_cooldown_seconds(now)
    return {
        "has_data": _cache["data"] is not None,
        "fetched_at": _cache["fetched_at"].isoformat() if _cache["fetched_at"] else None,
        "is_stale": _cache["is_stale"],
        "is_fresh": _is_cache_fresh(now),
        "cooldown_active": cooldown_active,
        "cooldown_remaining_seconds": remaining_cooldown,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
        "last_error": _cache["last_error"],
        "last_error_at": _cache["last_error_at"].isoformat() if _cache["last_error_at"] else None,
        "entry_count": len(_cache["data"]) if _cache["data"] else 0,
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
