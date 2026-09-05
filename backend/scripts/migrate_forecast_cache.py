#!/usr/bin/env python3
"""Safe migration script: Migrates forecast cache from legacy user_solar_estimates (2099-12-31)
to dedicated system_persistent_cache table.

Safety rules enforced:
1. Verify system_persistent_cache table exists.
2. Read and validate legacy cached forecast from user_solar_estimates (2099-12-31).
3. Upsert validated forecast to system_persistent_cache.
4. Read back and verify from system_persistent_cache.
5. ONLY delete legacy 2099-12-31 row if verification succeeds completely.
"""

import os
import sys
import json
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_supabase
from app.config import settings

CACHE_KEY = "openmeteo_kaliakair_hourly_7d"


def migrate_cache() -> bool:
    sb = get_supabase()

    print("Step 1: Verifying system_persistent_cache table exists in Supabase...")
    try:
        res = sb.table("system_persistent_cache").select("cache_key").limit(1).execute()
        print("  [OK] system_persistent_cache table is accessible.")
    except Exception as e:
        print(f"  [FAIL] system_persistent_cache table not found or inaccessible: {e}")
        print("  Action required: Execute 'backend/scripts/migration_system_persistent_cache.sql' in Supabase SQL Editor first.")
        return False

    print("Step 2: Checking legacy sentinel row in user_solar_estimates (date = '2099-12-31')...")
    legacy_res = sb.table("user_solar_estimates").select("*").eq("date", "2099-12-31").limit(1).execute()
    if not legacy_res.data:
        print("  [INFO] No legacy sentinel row found in user_solar_estimates. Nothing to migrate.")
        return True

    legacy_row = legacy_res.data[0]
    raw_notes = legacy_row.get("notes")
    if not raw_notes:
        print("  [WARN] Legacy row exists but 'notes' is empty.")
        return False

    try:
        parsed_notes = json.loads(raw_notes)
        raw_data = parsed_notes.get("data")
        raw_fetched_at = parsed_notes.get("fetched_at")
        if not raw_data or not raw_fetched_at:
            print("  [FAIL] Legacy payload missing 'data' or 'fetched_at'.")
            return False
        print(f"  [OK] Found valid legacy forecast payload with {len(raw_data)} hours (fetched at {raw_fetched_at}).")
    except Exception as e:
        print(f"  [FAIL] Could not parse legacy notes JSON: {e}")
        return False

    print("Step 3: Upserting forecast into dedicated system_persistent_cache...")
    payload = {
        "metadata": {
            "latitude": settings.LATITUDE,
            "longitude": settings.LONGITUDE,
            "timezone": settings.TIMEZONE,
            "forecast_days": settings.FORECAST_DAYS,
            "fetched_at": raw_fetched_at,
            "source": "Open-Meteo forecast API",
        },
        "hourly": raw_data,
    }

    try:
        upsert_res = sb.table("system_persistent_cache").upsert({
            "cache_key": CACHE_KEY,
            "payload": payload,
            "fetched_at": raw_fetched_at,
            "updated_at": datetime.now().isoformat(),
        }, on_conflict="cache_key").execute()
        print(f"  [OK] Successfully upserted into system_persistent_cache.")
    except Exception as e:
        print(f"  [FAIL] Failed to upsert into system_persistent_cache: {e}")
        print("  Safety guarantee: Legacy 2099-12-31 row was NOT deleted.")
        return False

    print("Step 4: Reading back and verifying new cache entry from system_persistent_cache...")
    try:
        verify_res = sb.table("system_persistent_cache").select("*").eq("cache_key", CACHE_KEY).limit(1).execute()
        if not verify_res.data:
            print("  [FAIL] Verification read failed: row not found after upsert.")
            return False

        saved_row = verify_res.data[0]
        saved_payload = saved_row.get("payload", {})
        if not saved_payload.get("hourly") or len(saved_payload.get("hourly", {})) != len(raw_data):
            print("  [FAIL] Verification read failed: hourly record count mismatch.")
            return False
        print("  [OK] Read-back verification succeeded completely!")
    except Exception as e:
        print(f"  [FAIL] Verification error: {e}")
        print("  Safety guarantee: Legacy 2099-12-31 row was NOT deleted.")
        return False

    print("Step 5: Safely removing legacy 2099-12-31 sentinel row from user_solar_estimates...")
    try:
        del_res = sb.table("user_solar_estimates").delete().eq("date", "2099-12-31").execute()
        print("  [OK] Legacy sentinel row removed successfully. Migration complete!")
        return True
    except Exception as e:
        print(f"  [WARN] New cache is active, but could not delete legacy row: {e}")
        return True


if __name__ == "__main__":
    success = migrate_cache()
    sys.exit(0 if success else 1)
