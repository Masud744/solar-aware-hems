-- Migration: Dedicated System Persistent Cache Table for External API Resilience
-- Execute this query in the Supabase Dashboard -> SQL Editor

CREATE TABLE IF NOT EXISTS system_persistent_cache (
    cache_key   VARCHAR(64) PRIMARY KEY,
    payload     JSONB NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookup by key
CREATE INDEX IF NOT EXISTS idx_system_persistent_cache_key ON system_persistent_cache(cache_key);

-- Comment documenting scientific data provenance
COMMENT ON TABLE system_persistent_cache IS 'Key-value cache for external API payloads (e.g. Open-Meteo weather forecasts) ensuring CP-HEMS resilience under upstream cloud outages and IP rate limits.';
