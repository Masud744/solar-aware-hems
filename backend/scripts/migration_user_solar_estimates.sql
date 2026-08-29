-- Migration: Dedicated User Solar Estimates Table for Persistent Energy & Cost Tracking
-- Execute this query in the Supabase Dashboard -> SQL Editor

CREATE TABLE IF NOT EXISTS user_solar_estimates (
    id                  BIGSERIAL PRIMARY KEY,
    date                DATE NOT NULL UNIQUE,
    estimated_solar_kwh REAL NOT NULL DEFAULT 0.0,
    notes               TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for high-speed chronological queries
CREATE INDEX IF NOT EXISTS idx_user_solar_estimates_date ON user_solar_estimates(date);

-- Comment documenting scientific data provenance
COMMENT ON TABLE user_solar_estimates IS 'Stores user-reported estimated solar generation (kWh) by calendar date. Used to derive estimated solar savings against baseline electricity tariff (৳7.50/kWh).';
