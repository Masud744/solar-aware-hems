#!/usr/bin/env python3
"""Comprehensive test suite for Weather Cache Concurrency, Failure Backoff, Stale Preservation,
and /schedule/recommend 503 Clean Handling."""

import os
import sys
import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import httpx

sys.path.insert(0, os.path.abspath("backend"))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")

from app.services import weather
from app.routers import device
from app.models.schemas import ScheduleRecommendRequest
from fastapi import HTTPException


class TestWeatherCacheAndResilience(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset cache before each test
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

    async def test_cold_cache_concurrency_single_fetch(self):
        """Test C: Proves only ONE Open-Meteo fetch occurs when 20 coroutines hit cold cache simultaneously."""
        fetch_call_count = 0
        target_time = datetime(2026, 8, 30, 12, 0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")

        fake_forecast = {
            target_str: {
                "cloud_cover": 20,
                "temperature_2m": 28.5,
                "relative_humidity_2m": 65,
                "wind_speed_10m": 3.2,
            }
        }

        async def mock_fetch():
            nonlocal fetch_call_count
            fetch_call_count += 1
            await asyncio.sleep(0.05)  # Simulate network latency
            return fake_forecast

        with patch("app.services.weather._fetch_forecast", side_effect=mock_fetch):
            # Launch 20 concurrent requests for the same target time
            tasks = [weather.get_forecast_at(target_time) for _ in range(20)]
            results = await asyncio.gather(*tasks)

        # Assert all 20 coroutines received the correct data
        self.assertEqual(len(results), 20)
        for r in results:
            self.assertEqual(r["temperature"], 28.5)
            self.assertEqual(r["cloud_cover"], 20)

        # CRITICAL ASSERTION: Exactly 1 upstream fetch was executed despite 20 concurrent requests
        self.assertEqual(fetch_call_count, 1, f"Expected exactly 1 upstream fetch, got {fetch_call_count}")
        print(f"✅ Test C Passed: 20 concurrent requests resulted in exactly {fetch_call_count} upstream fetch.")

    async def test_upstream_failure_and_negative_cache_backoff(self):
        """Test D: Proves no retry storm occurs when upstream fails; backoff protects upstream."""
        fetch_call_count = 0
        target_time = datetime(2026, 8, 30, 14, 0)

        async def mock_failing_fetch():
            nonlocal fetch_call_count
            fetch_call_count += 1
            await asyncio.sleep(0.02)
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_failing_fetch):
            # Batch 1: 10 concurrent requests during failure
            tasks = [weather.get_forecast_at(target_time) for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All 10 must receive WeatherForecastError
            self.assertEqual(len(results), 10)
            for res in results:
                self.assertIsInstance(res, weather.WeatherForecastError)

            # Only 1 upstream fetch happened for Batch 1
            self.assertEqual(fetch_call_count, 1)

            # Batch 2: 10 immediate subsequent requests within the 60s negative TTL
            subsequent_tasks = [weather.get_forecast_at(target_time) for _ in range(10)]
            subsequent_results = await asyncio.gather(*subsequent_tasks, return_exceptions=True)

            for res in subsequent_results:
                self.assertIsInstance(res, weather.WeatherForecastError)
                self.assertIn("upstream backoff active", str(res))

            # CRITICAL ASSERTION: No additional upstream calls made during backoff
            self.assertEqual(fetch_call_count, 1, f"Upstream was called {fetch_call_count} times, expected 1.")
            print(f"✅ Test D Passed: 20 requests during upstream failure resulted in only {fetch_call_count} call (backoff active).")

    async def test_stale_cache_preservation_on_refresh_failure(self):
        """Proves last-known-good forecast data is preserved if refresh fails."""
        target_time = datetime(2026, 8, 30, 15, 0)
        target_str = target_time.strftime("%Y-%m-%dT%H:%M")

        # Initial successful cache entry from 2 hours ago (expired TTL)
        weather._cache["data"] = {
            target_str: {
                "cloud_cover": 40,
                "temperature_2m": 30.0,
                "relative_humidity_2m": 70,
                "wind_speed_10m": 2.5,
            }
        }
        weather._cache["fetched_at"] = datetime.now() - timedelta(seconds=7200)

        # Upstream refresh now fails
        async def mock_failing_refresh():
            raise weather.WeatherForecastError("Open-Meteo timeout")

        with patch("app.services.weather._fetch_forecast", side_effect=mock_failing_refresh):
            res = await weather.get_forecast_at(target_time)

        # Forecast is preserved and returned
        self.assertEqual(res["temperature"], 30.0)
        self.assertEqual(res["cloud_cover"], 40)
        self.assertTrue(weather._cache["is_stale"])
        print("✅ Stale Cache Preservation Passed: Expired cache returned last-known-good data on refresh failure.")

    async def test_schedule_recommend_clean_503_on_weather_failure(self):
        """Test E: Proves /schedule/recommend returns clean HTTP 503 instead of unhandled 500 when weather is unavailable."""
        now = datetime(2026, 8, 30, 10, 0)
        req = ScheduleRecommendRequest(
            device_name="Washing Machine",
            rated_power_kw=1.2,
            duration_hours=1.0,
            window_start=now,
            window_end=now + timedelta(hours=24),
        )

        async def mock_fail_weather(*args, **kwargs):
            raise weather.WeatherForecastError("Open-Meteo HTTP 429 Too Many Requests")

        with patch("app.services.weather.get_forecast_at", side_effect=mock_fail_weather):
            with self.assertRaises(HTTPException) as ctx:
                await device.schedule_recommend(req)

            # Assert clean HTTP 503
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("Weather forecast unavailable from Open-Meteo", ctx.exception.detail)
            print(f"✅ Test E Passed: schedule_recommend raised clean HTTP {ctx.exception.status_code}: {ctx.exception.detail[:60]}...")


if __name__ == "__main__":
    unittest.main()
