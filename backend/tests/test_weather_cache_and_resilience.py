#!/usr/bin/env python3
"""Comprehensive test suite for Weather Forecast Resilience & Stale Fallback.

Tests T1 through T9:
- T1: Fresh cache -> normal response (is_stale=False, 0 upstream calls)
- T2: 25h old cache + target inside horizon -> 200 + is_stale=True
- T3: 25h old cache + target outside horizon -> clean ForecastHorizonError
- T4: 429 -> exponential backoff retry -> recovery (is_stale=False)
- T5: Repeated 429 -> negative TTL active -> no upstream calls during TTL
- T6: Concurrency under 429 -> exactly 1 upstream attempt sequence under lock
- T7: Malformed/incomplete cached forecast -> rejected by validator, no misleading 200
- T8: Supabase unavailable + valid memory cache -> memory cache served gracefully
- T9: Both upstream and cache unavailable -> clean HTTP 503 (no synthetic zeros)
"""

import os
import sys
import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

sys.path.insert(0, os.path.abspath("backend"))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")

from app.services import weather, decision_engine, assistant_tools
from app.routers import device, predict
from app.models.schemas import DeviceCheckRequest, ScheduleRecommendRequest
from fastapi import HTTPException


class TestWeatherCacheAndResilience(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset in-memory cache before each test
        weather._cache = {
            "fetched_at": None,
            "data": None,
            "cache_ttl_seconds": 3600,
            "negative_ttl_seconds": 60,
            "last_error": None,
            "last_error_at": None,
            "is_stale": False,
        }
        weather._fetch_lock = None

        # Patch sensor readings to return empty dict (benchmark profile fallback)
        self.sensor_patcher = patch("app.services.features._query_sensor_readings", return_value={})
        self.sensor_patcher.start()
        self.addCleanup(self.sensor_patcher.stop)

    def _generate_valid_forecast(self, base_time: datetime, days: int = 7) -> dict:
        """Generate a valid 7-day hourly forecast dictionary."""
        forecast = {}
        for h in range(days * 24):
            dt = base_time + timedelta(hours=h)
            ts_str = dt.strftime("%Y-%m-%dT%H:%M")
            forecast[ts_str] = {
                "cloud_cover": 30.0,
                "temperature_2m": 28.0,
                "relative_humidity_2m": 70.0,
                "wind_speed_10m": 4.5,
            }
        return forecast

    # ── T1: Fresh Cache ──────────────────────────────────────────────
    async def test_t1_fresh_cache_serves_live(self):
        """T1: Proves fresh cache within 1h TTL serves immediately with is_stale=False and 0 upstream calls."""
        now = datetime.now()
        target_time = now + timedelta(hours=2)
        target_str = target_time.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")

        weather._cache["data"] = self._generate_valid_forecast(now.replace(minute=0, second=0, microsecond=0))
        weather._cache["fetched_at"] = now - timedelta(minutes=5)  # 5 minutes old (fresh)
        weather._cache["is_stale"] = False

        with patch("app.services.weather._fetch_forecast") as mock_fetch:
            res = await weather.get_forecast_at(target_time)
            mock_fetch.assert_not_called()

        self.assertEqual(res["cloud_cover"], 30.0)
        self.assertEqual(res["temperature"], 28.0)
        self.assertFalse(res["is_stale"])
        self.assertEqual(res["data_source"], "live_upstream_forecast")
        print("PASS: T1 Fresh Cache verified.")

    # ── T2: Stale Cache 25h Old (Inside Horizon) ─────────────────────
    async def test_t2_stale_cache_25h_old_served_inside_horizon(self):
        """T2: Proves 25h old cache covering target hour is served as is_stale=True (24h hard-drop removed)."""
        now = datetime.now()
        base_time = (now - timedelta(hours=25)).replace(minute=0, second=0, microsecond=0)
        # 7-day forecast from 25 hours ago covers up to 143 hours into the future
        valid_7d_forecast = self._generate_valid_forecast(base_time, days=7)

        weather._cache["data"] = valid_7d_forecast
        weather._cache["fetched_at"] = now - timedelta(hours=25)  # 25h old (expired TTL)

        target_time = now + timedelta(hours=3)  # Target is within the 7-day horizon

        # Upstream refresh fails with 429
        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream):
            res = await weather.get_forecast_at(target_time)

        self.assertIsNotNone(res)
        self.assertEqual(res["temperature"], 28.0)
        self.assertTrue(res["is_stale"])
        self.assertEqual(res["data_source"], "cached_persisted_forecast")
        self.assertIn("Cached Fallback", res["weather_source"])
        print("PASS: T2 Stale Cache (25h old, inside horizon) verified.")

    # ── T3: Stale Cache (Outside Horizon) ────────────────────────────
    async def test_t3_stale_cache_target_outside_horizon_fails_cleanly(self):
        """T3: Proves requesting a time beyond the cached forecast horizon raises ForecastHorizonError."""
        now = datetime.now()
        base_time = (now - timedelta(hours=25)).replace(minute=0, second=0, microsecond=0)
        valid_7d_forecast = self._generate_valid_forecast(base_time, days=7)

        weather._cache["data"] = valid_7d_forecast
        weather._cache["fetched_at"] = now - timedelta(hours=25)

        # Target is 8 days ahead (outside 7-day horizon of base_time)
        target_time = now + timedelta(days=8)

        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream):
            with self.assertRaises(weather.ForecastHorizonError) as ctx:
                await weather.get_forecast_at(target_time)

        self.assertIn("outside the available Open-Meteo forecast horizon", str(ctx.exception))
        print("PASS: T3 Outside Horizon clean failure verified.")

    # ── T4: 429 -> Retry -> Recovery ─────────────────────────────────
    async def test_t4_429_retry_and_recovery(self):
        """T4: Proves 429 on first attempt triggers jittered backoff retry and succeeds on attempt 1."""
        now = datetime.now()
        target_time = now.replace(minute=0, second=0, microsecond=0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")

        attempt_count = 0

        # Create mock HTTP responses
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "0.1"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "hourly": {
                "time": [target_str],
                "cloud_cover": [45.0],
                "temperature_2m": [31.5],
                "relative_humidity_2m": [60.0],
                "wind_speed_10m": [5.0],
            }
        }

        async def mock_get(url, params=None, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                # First attempt: raise 429
                err = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=resp_429)
                raise err
            # Second attempt: succeed with 200 OK
            return resp_200

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                res = await weather.get_forecast_at(target_time)
                mock_sleep.assert_called_once()

        self.assertEqual(attempt_count, 2)
        self.assertEqual(res["temperature"], 31.5)
        self.assertFalse(res["is_stale"])
        print("PASS: T4 429 Retry and Recovery verified.")

    # ── T5: Repeated 429 -> Negative TTL Active ──────────────────────
    async def test_t5_repeated_429_activates_negative_ttl(self):
        """T5: Proves repeated 429 failure activates 60s negative TTL backoff, blocking upstream calls."""
        now = datetime.now()
        target_time = now.replace(minute=0, second=0, microsecond=0)

        fetch_calls = 0

        async def mock_failing_fetch():
            nonlocal fetch_calls
            fetch_calls += 1
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_failing_fetch):
            # First request: fails upstream and sets negative TTL
            with self.assertRaises(weather.WeatherForecastError):
                await weather.get_forecast_at(target_time)

            self.assertEqual(fetch_calls, 1)

            # Next 5 requests within negative TTL: fast-fail with backoff message, 0 upstream calls
            for _ in range(5):
                with self.assertRaises(weather.WeatherForecastError) as ctx:
                    await weather.get_forecast_at(target_time)
                self.assertIn("upstream backoff active", str(ctx.exception))

            # Upstream was still called only once during active negative TTL
            self.assertEqual(fetch_calls, 1)

            # BOUNDARY CHECK: advance time beyond 60s negative TTL
            weather._cache["last_error_at"] = datetime.now() - timedelta(seconds=65)
            with self.assertRaises(weather.WeatherForecastError) as ctx:
                await weather.get_forecast_at(target_time)

            # Upstream retry is now permitted again
            self.assertEqual(fetch_calls, 2)

        print("PASS: T5 Negative TTL active & boundary expiration verified.")

    # ── T6: Concurrency Under 429 ─────────────────────────────────────
    async def test_t6_concurrency_under_429_single_sequence(self):
        """T6: Proves 15 concurrent requests hitting cold cache under 429 execute exactly 1 fetch sequence."""
        target_time = datetime(2026, 8, 30, 14, 0)
        fetch_call_count = 0

        async def mock_failing_fetch():
            nonlocal fetch_call_count
            fetch_call_count += 1
            await asyncio.sleep(0.02)  # Simulate in-flight lock hold
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_failing_fetch):
            tasks = [weather.get_forecast_at(target_time) for _ in range(15)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        self.assertEqual(len(results), 15)
        for r in results:
            self.assertIsInstance(r, weather.WeatherForecastError)

        # CRITICAL: Exactly 1 upstream fetch execution under lock
        self.assertEqual(fetch_call_count, 1)
        print("PASS: T6 Concurrency Under 429 verified.")

    # ── T7: Malformed Cached Forecast Rejected ───────────────────────
    def test_t7_malformed_cache_rejected_by_validator(self):
        """T7: Proves malformed or out-of-bounds cached forecast is rejected by physical validator."""
        # 1. Missing required key
        invalid_entry_missing = {
            "temperature_2m": 25.0,
            "relative_humidity_2m": 50.0,
            "wind_speed_10m": 3.0,
            # cloud_cover missing
        }
        self.assertFalse(weather.validate_forecast_entry(invalid_entry_missing))

        # 2. Out-of-bounds temperature (> 55°C)
        invalid_entry_temp = {
            "cloud_cover": 20.0,
            "temperature_2m": 999.0,
            "relative_humidity_2m": 50.0,
            "wind_speed_10m": 3.0,
        }
        self.assertFalse(weather.validate_forecast_entry(invalid_entry_temp))

        # 3. Valid entry
        valid_entry = {
            "cloud_cover": 20.0,
            "temperature_2m": 29.5,
            "relative_humidity_2m": 65.0,
            "wind_speed_10m": 4.0,
        }
        self.assertTrue(weather.validate_forecast_entry(valid_entry))

        # 4. Invalid metadata (wrong coordinates for Kaliakair)
        invalid_payload_coords = {
            "metadata": {
                "latitude": 48.85,  # Paris, not Kaliakair
                "longitude": 2.35,
                "timezone": "Asia/Dhaka",
                "fetched_at": datetime.now().isoformat(),
            },
            "hourly": {"2026-09-06T12:00": valid_entry},
        }
        self.assertFalse(weather.validate_cached_payload(invalid_payload_coords))
        print("PASS: T7 Malformed Cache Validation verified.")

    # ── T8: Supabase Down + Valid Memory Cache ────────────────────────
    async def test_t8_supabase_down_serves_valid_memory_cache(self):
        """T8: Proves memory cache serves gracefully when Supabase client raises exception."""
        now = datetime.now()
        target_time = now.replace(minute=0, second=0, microsecond=0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")

        weather._cache["data"] = {
            target_str: {
                "cloud_cover": 15.0,
                "temperature_2m": 27.5,
                "relative_humidity_2m": 60.0,
                "wind_speed_10m": 3.0,
            }
        }
        weather._cache["fetched_at"] = now - timedelta(minutes=10)

        with patch("app.database.get_supabase", side_effect=RuntimeError("Supabase connection refused")):
            res = await weather.get_forecast_at(target_time)

        self.assertEqual(res["temperature"], 27.5)
        self.assertFalse(res["is_stale"])
        print("PASS: T8 Supabase Down + Valid Memory Cache verified.")

    # ── T9: Both Upstream & Cache Down -> Clean 503 ───────────────────
    async def test_t9_both_upstream_and_cache_down_clean_503(self):
        """T9: Proves /schedule/recommend raises clean HTTP 503 when both upstream and cache are down."""
        now = datetime(2026, 8, 30, 10, 0)
        req = ScheduleRecommendRequest(
            device_name="Water Pump",
            rated_power_kw=0.75,
            duration_hours=1.0,
            window_start=now,
            window_end=now + timedelta(hours=24),
        )

        async def mock_fail_all(*args, **kwargs):
            raise weather.WeatherForecastError("Open-Meteo HTTP 503 Service Unavailable")

        with patch("app.services.weather.get_forecast_at", side_effect=mock_fail_all):
            with self.assertRaises(HTTPException) as ctx:
                await device.schedule_recommend(req)

            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("Weather forecast unavailable from Open-Meteo", ctx.exception.detail)

        print("PASS: T9 Both Upstream and Cache Down -> Clean 503 verified.")

    # ── T10: Cooldown with Stale Cache Available (Polling Storm Prevention) ──
    async def test_t10_stale_cache_under_429_activates_cooldown_blocking_upstream_polling(self):
        """T10: Proves that when stale cached data exists, a 429 upstream failure activates cooldown
        such that repeated rapid requests serve stale cache immediately with 0 additional upstream calls."""
        now = datetime.now()
        target_time = now.replace(minute=0, second=0, microsecond=0)
        base_time = (now - timedelta(hours=25)).replace(minute=0, second=0, microsecond=0)
        valid_7d_forecast = self._generate_valid_forecast(base_time, days=7)

        # Seed in-memory cache with 25h-old valid forecast
        weather._cache["data"] = valid_7d_forecast
        weather._cache["fetched_at"] = now - timedelta(hours=25)
        weather._cache["negative_ttl_seconds"] = 60
        weather._cache["cooldown_seconds"] = None
        weather._cache["last_error_at"] = None

        fetch_call_count = 0
        should_recover = False

        async def mock_failing_fetch():
            nonlocal fetch_call_count
            fetch_call_count += 1
            if not should_recover:
                raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests", status_code=429)
            # Recovery: return fresh forecast
            return self._generate_valid_forecast(now.replace(minute=0, second=0, microsecond=0), days=7)

        with patch("app.services.weather._fetch_forecast", side_effect=mock_failing_fetch):
            # Request 1: cache expired, calls upstream, fails with 429, sets 60s cooldown, serves stale
            res1 = await weather.get_forecast_at(target_time)
            self.assertEqual(fetch_call_count, 1)
            self.assertTrue(res1["is_stale"])
            self.assertEqual(res1["data_source"], "cached_persisted_forecast")
            self.assertIsNotNone(weather._cache["last_error_at"])
            self.assertEqual(weather._cache["cooldown_seconds"], 60)

            # Requests 2 through 10 (simulating frontend polling every 5 seconds):
            # Cooldown is active -> MUST serve stale immediately without calling upstream!
            for _ in range(9):
                res = await weather.get_forecast_at(target_time)
                self.assertTrue(res["is_stale"])
                self.assertEqual(res["data_source"], "cached_persisted_forecast")

            # CRITICAL VERIFICATION: Upstream was called ONLY ONCE across 10 requests!
            self.assertEqual(fetch_call_count, 1)

            # BOUNDARY CHECK: Advance time beyond 60s cooldown window
            weather._cache["last_error_at"] = datetime.now() - timedelta(seconds=65)
            should_recover = True

            # Request 11: Cooldown expired -> attempts fresh fetch, recovers successfully!
            res_recovered = await weather.get_forecast_at(target_time)
            self.assertEqual(fetch_call_count, 2)
            self.assertFalse(res_recovered["is_stale"])
            self.assertEqual(res_recovered["data_source"], "live_upstream_forecast")
            self.assertIsNone(weather._cache["cooldown_seconds"])

        print("PASS: T10 Stale Cache Cooldown & Polling Storm Prevention verified.")

    # ── T11: Retry-After Header Respected on 429 ──────────────────────
    async def test_t11_retry_after_header_controls_cooldown_duration(self):
        """T11: Proves that upstream Retry-After header sets cooldown duration and is respected."""
        now = datetime.now()
        target_time = now.replace(minute=0, second=0, microsecond=0)
        base_time = (now - timedelta(hours=25)).replace(minute=0, second=0, microsecond=0)
        valid_7d_forecast = self._generate_valid_forecast(base_time, days=7)

        weather._cache["data"] = valid_7d_forecast
        weather._cache["fetched_at"] = now - timedelta(hours=25)
        weather._cache["cooldown_seconds"] = None
        weather._cache["last_error_at"] = None

        fetch_call_count = 0

        async def mock_fetch_with_retry_after():
            nonlocal fetch_call_count
            fetch_call_count += 1
            # HTTP 429 with Retry-After: 120
            raise weather.WeatherForecastError("Open-Meteo HTTP 429", status_code=429, retry_after=120.0)

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fetch_with_retry_after):
            res = await weather.get_forecast_at(target_time)
            self.assertEqual(fetch_call_count, 1)
            self.assertTrue(res["is_stale"])
            # Cooldown should be exactly 120s from Retry-After
            self.assertEqual(weather._cache["cooldown_seconds"], 120)

            # At 65s (which would exceed default 60s), cooldown must STILL be active
            weather._cache["last_error_at"] = datetime.now() - timedelta(seconds=65)
            res_still_cooling = await weather.get_forecast_at(target_time)
            self.assertEqual(fetch_call_count, 1)
            self.assertTrue(res_still_cooling["is_stale"])

            # At 125s (exceeding Retry-After 120s), cooldown expires and upstream is retried
            weather._cache["last_error_at"] = datetime.now() - timedelta(seconds=125)
            res_retried = await weather.get_forecast_at(target_time)
            self.assertEqual(fetch_call_count, 2)
            self.assertTrue(res_retried["is_stale"])

        print("PASS: T11 Retry-After Header Cooldown Duration verified.")

    # ── Admission Policy Tests (Tests 1 - 7) ──────────────────────────

    # Test 1: Stale forecast + positive safe surplus -> DENY
    def test_admission_1_stale_forecast_positive_surplus_denied(self):
        """Test 1: Proves stale forecast with positive safe surplus results in DENY with suspended reason."""
        cached_time = datetime(2026, 3, 5, 12, 0)
        res = decision_engine.compute_decision(
            predicted_solar_kw=2.0,
            sigma_solar=0.0851,
            predicted_load_kw=0.5,
            sigma_load=0.5114,
            device_power_kw=0.2,
            k=1.0,
            is_stale=True,
            cached_at=cached_time,
        )
        self.assertAlmostEqual(res.safe_solar, 1.9149, places=4)
        self.assertAlmostEqual(res.conservative_load, 1.0114, places=4)
        self.assertAlmostEqual(res.safe_surplus, 0.9035, places=4)
        self.assertEqual(res.decision, "DENY")
        self.assertIn("DENY: Forecast features are stale (cached at 2026-03-05T12:00:00). Automated solar admission authority is suspended.", res.reason)
        print("PASS: Test 1 Stale Forecast + Positive Safe Surplus -> DENY verified.")

    # Test 2: Same numerical conditions with fresh forecast -> ALLOW
    def test_admission_2_fresh_forecast_positive_surplus_allowed(self):
        """Test 2: Proves identical numerical inputs under fresh forecast (is_stale=False) preserve ALLOW."""
        res = decision_engine.compute_decision(
            predicted_solar_kw=2.0,
            sigma_solar=0.0851,
            predicted_load_kw=0.5,
            sigma_load=0.5114,
            device_power_kw=0.2,
            k=1.0,
            is_stale=False,
        )
        self.assertAlmostEqual(res.safe_solar, 1.9149, places=4)
        self.assertAlmostEqual(res.conservative_load, 1.0114, places=4)
        self.assertAlmostEqual(res.safe_surplus, 0.9035, places=4)
        self.assertEqual(res.decision, "ALLOW")
        self.assertIn("Safe surplus (0.903 kW) >= device power (0.200 kW)", res.reason)
        print("PASS: Test 2 Fresh Forecast + Same Conditions -> ALLOW preserved.")

    # Test 3: /device/check cannot persist an ALLOW for solar when forecast is stale
    async def test_admission_3_device_check_cannot_persist_allow_when_stale(self):
        """Test 3: Proves /device/check cannot persist an ALLOW in device_requests when forecast is stale."""
        now = datetime.now()
        target_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")
        cached_time = now - timedelta(hours=28)

        weather._cache["data"] = {
            target_str: {
                "cloud_cover": 5.0,
                "temperature_2m": 32.0,
                "relative_humidity_2m": 45.0,
                "wind_speed_10m": 2.5,
            }
        }
        weather._cache["fetched_at"] = cached_time
        weather._cache["is_stale"] = True

        inserted_records = []
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()

        def fake_insert(rec):
            inserted_records.append(rec)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[{"id": 101, **rec}])
            return m

        mock_insert.side_effect = fake_insert
        mock_table.insert = mock_insert
        mock_sb.table.return_value = mock_table

        req = DeviceCheckRequest(
            device_name="Refrigerator",
            rated_power_kw=0.15,
            duration_hours=1.0,
            target_time=target_time,
        )

        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"), \
             patch("app.services.ml_models.predict_solar", return_value=2.5), \
             patch("app.services.ml_models.predict_load", return_value=0.4), \
             patch("app.routers.device.get_supabase", return_value=mock_sb):
            res = await device.device_check(req)

        self.assertEqual(len(inserted_records), 1)
        persisted = inserted_records[0]
        self.assertEqual(persisted["decision"], "DENY")
        self.assertGreater(persisted["safe_surplus_kw"], 0.15)
        self.assertIn("Automated solar admission authority is suspended", persisted["reason"])

        self.assertEqual(res.decision, "DENY")
        self.assertTrue(res.is_stale)
        self.assertGreater(res.safe_surplus_kw, 0.15)
        print("PASS: Test 3 /device/check cannot persist ALLOW when stale verified.")

    # Test 4: /schedule/recommend returns no recommended_start when all candidate slots are stale
    async def test_admission_4_schedule_recommend_no_recommended_start_when_all_slots_stale(self):
        """Test 4: Proves /schedule/recommend returns recommended_start=None when all candidate slots are stale."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        cached_time = now - timedelta(hours=29)

        forecast = self._generate_valid_forecast(now, days=2)
        weather._cache["data"] = forecast
        weather._cache["fetched_at"] = cached_time
        weather._cache["is_stale"] = True

        req = ScheduleRecommendRequest(
            device_name="Water Pump",
            rated_power_kw=0.75,
            duration_hours=1.0,
            window_start=now,
            window_end=now + timedelta(hours=12),
        )

        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"):
            res = await device.schedule_recommend(req)

        self.assertIsNone(res.recommended_start)
        self.assertTrue(res.is_stale)
        self.assertEqual(len(res.slots), 13)
        for slot in res.slots:
            self.assertEqual(slot.decision, "DENY")
            self.assertTrue(slot.is_stale)
            self.assertIsInstance(slot.safe_surplus_kw, float)
            self.assertIsInstance(slot.predicted_solar_kw, float)
        print("PASS: Test 4 /schedule/recommend returns None for recommended_start when stale verified.")

    # Test 5: Alternate control/admission paths cannot bypass the stale gate
    async def test_admission_5_alternate_paths_cannot_bypass_stale_gate(self):
        """Test 5: Proves multi-hour runs, assistant tools, and extreme surplus cannot bypass the stale policy gate."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        cached_time = now - timedelta(hours=30)
        forecast = self._generate_valid_forecast(now, days=2)
        weather._cache["data"] = forecast
        weather._cache["fetched_at"] = cached_time
        weather._cache["is_stale"] = True

        mock_sb = MagicMock()
        inserted_records = []

        def fake_insert(rec):
            inserted_records.append(rec)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[{"id": 202, **rec}])
            return m

        mock_sb.table.return_value.insert.side_effect = fake_insert

        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        # 5a: Multi-hour duration-aware check
        req_multi = DeviceCheckRequest(
            device_name="Washing Machine",
            rated_power_kw=0.5,
            duration_hours=3.0,
            target_time=now + timedelta(hours=1),
        )
        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"), \
             patch("app.services.ml_models.predict_solar", return_value=3.0), \
             patch("app.services.ml_models.predict_load", return_value=0.5), \
             patch("app.routers.device.get_supabase", return_value=mock_sb):
            res_multi = await device.device_check(req_multi)

        self.assertEqual(res_multi.decision, "DENY")
        self.assertEqual(inserted_records[-1]["decision"], "DENY")
        self.assertIn("Automated solar admission authority is suspended", res_multi.reason)

        # 5b: Assistant tool path
        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"), \
             patch("app.routers.device.get_supabase", return_value=mock_sb):
            tool_safety = await assistant_tools.tool_check_appliance_safety(
                device_name="Rice Cooker",
                rated_power_kw=0.7,
                duration_hours=1.0,
                target_time_iso=(now + timedelta(hours=2)).isoformat(),
            )
        self.assertEqual(tool_safety["decision"], "DENY")
        self.assertIn("Automated solar admission authority is suspended", tool_safety["reason"])

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"):
            tool_sched = await assistant_tools.tool_get_schedule_recommendation(
                device_name="Rice Cooker",
                rated_power_kw=0.7,
                duration_hours=1.0,
                window_start_iso=now.isoformat(),
                window_end_iso=(now + timedelta(hours=6)).isoformat(),
            )
        self.assertIsNone(tool_sched["recommended_start_bst"])
        self.assertFalse(tool_sched["is_window_found"])

        # 5c: Extreme surplus (10 kW surplus vs 0.05 kW device) cannot bypass gate
        res_extreme = decision_engine.compute_decision(
            predicted_solar_kw=10.0,
            sigma_solar=0.0851,
            predicted_load_kw=0.1,
            sigma_load=0.2,
            device_power_kw=0.05,
            k=1.0,
            is_stale=True,
            cached_at="2026-03-05T12:00:00",
        )
        self.assertEqual(res_extreme.decision, "DENY")
        self.assertIn("Automated solar admission authority is suspended", res_extreme.reason)
        print("PASS: Test 5 Alternate Paths Blocked by Stale Gate verified.")

    # Test 6: Unavailable forecast + no valid cache remains blocked with existing error behavior
    async def test_admission_6_unavailable_forecast_no_valid_cache_blocked_with_error(self):
        """Test 6: Proves unavailable forecast with no valid cache fails with HTTP 503/422 without synthetic data."""
        weather._cache["data"] = None
        weather._cache["fetched_at"] = None
        weather._cache["is_stale"] = False

        async def mock_fail_upstream(*args, **kwargs):
            raise weather.WeatherForecastError("Weather forecast unavailable from Open-Meteo")

        req = DeviceCheckRequest(
            device_name="Water Pump",
            rated_power_kw=0.75,
            duration_hours=1.0,
            target_time=datetime.now() + timedelta(hours=2),
        )

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream):
            with patch("app.services.weather._load_persisted_cache", return_value=False):
                with self.assertRaises(HTTPException) as ctx:
                    await device.device_check(req)
                self.assertEqual(ctx.exception.status_code, 503)
                self.assertIn("Weather forecast unavailable", ctx.exception.detail)
        print("PASS: Test 6 Unavailable Forecast Blocked with Clean Error verified.")

    # Test 7: Stale forecast still produces valid dashboard/advisory prediction data and metadata
    async def test_admission_7_stale_forecast_produces_valid_predictions_and_metadata(self):
        """Test 7: Proves stale forecast serves valid continuous predictions and metadata for advisory display."""
        now = datetime.now()
        target_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")
        cached_time = now - timedelta(hours=27)

        weather._cache["data"] = {
            target_str: {
                "cloud_cover": 20.0,
                "temperature_2m": 31.0,
                "relative_humidity_2m": 60.0,
                "wind_speed_10m": 3.8,
            }
        }
        weather._cache["fetched_at"] = cached_time
        weather._cache["is_stale"] = True

        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        async def mock_fail_upstream():
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fail_upstream), \
             patch("app.services.weather._save_persisted_cache"), \
             patch("app.routers.predict.get_supabase", return_value=mock_sb):
            solar_res = await predict._handle_solar_prediction(target_time)
            load_res = await predict._handle_load_prediction(target_time)

        self.assertTrue(solar_res.is_stale)
        self.assertEqual(solar_res.cached_at, cached_time)
        self.assertGreater(solar_res.predicted_kw, 0.0)
        self.assertGreater(solar_res.safe_kw, 0.0)

        self.assertTrue(load_res.is_stale)
        self.assertEqual(load_res.cached_at, cached_time)
        self.assertGreater(load_res.predicted_kw, 0.0)
        self.assertGreater(load_res.conservative_kw, 0.0)
        print("PASS: Test 7 Stale Forecast Produces Valid Predictions & Metadata verified.")


if __name__ == "__main__":
    unittest.main()
