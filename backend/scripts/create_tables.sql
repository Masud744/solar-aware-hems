-- Phase 5 Supabase Table Schema
-- Run this in the Supabase SQL Editor to create all required tables.

-- 1. sensor_readings (ESP32 / seed test data)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id                      BIGSERIAL PRIMARY KEY,
    device_id               TEXT NOT NULL,
    ts                      TIMESTAMPTZ NOT NULL,
    voltage_v               REAL,
    current_a               REAL,
    power_w                 REAL,
    temperature_c           REAL,
    power_factor            REAL,
    energy_accum_kwh        REAL,
    humidity_pct            REAL,
    grid_bank_enabled       BOOLEAN,
    solar_bank_enabled      BOOLEAN,
    relay_commanded_state   JSONB,
    mismatch_suspected      BOOLEAN
);

-- 1b. device_controls (ESP32 desired relay source state)
CREATE TABLE IF NOT EXISTS device_controls (
    device_id               TEXT PRIMARY KEY,
    load_1                  TEXT NOT NULL DEFAULT 'off',
    load_2                  TEXT NOT NULL DEFAULT 'off',
    load_3                  TEXT NOT NULL DEFAULT 'off',
    load_4                  TEXT NOT NULL DEFAULT 'off',
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. solar_predictions
CREATE TABLE IF NOT EXISTS solar_predictions (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL,
    predicted_kw    REAL NOT NULL,
    safe_kw         REAL NOT NULL,
    sigma           REAL NOT NULL,
    model_version   TEXT NOT NULL
);

-- 3. load_predictions
CREATE TABLE IF NOT EXISTS load_predictions (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL,
    predicted_kw    REAL NOT NULL,
    conservative_kw REAL NOT NULL,
    sigma           REAL NOT NULL,
    model_version   TEXT NOT NULL
);

-- 4. device_requests
CREATE TABLE IF NOT EXISTS device_requests (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_name     TEXT NOT NULL,
    rated_power_kw  REAL NOT NULL,
    duration_hours  REAL NOT NULL,
    priority        TEXT,
    decision        TEXT NOT NULL,
    safe_surplus_kw REAL NOT NULL,
    reason          TEXT NOT NULL
);

-- 5. user_actions
CREATE TABLE IF NOT EXISTS user_actions (
    id                  BIGSERIAL PRIMARY KEY,
    device_request_id   BIGINT REFERENCES device_requests(id),
    ts                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action              TEXT NOT NULL
);

-- 6. shap_explanations
CREATE TABLE IF NOT EXISTS shap_explanations (
    id                  BIGSERIAL PRIMARY KEY,
    prediction_id       BIGINT NOT NULL,
    prediction_type     TEXT NOT NULL,
    feature_name        TEXT NOT NULL,
    contribution_value  REAL NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_ts ON sensor_readings(ts);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_device_ts ON sensor_readings(device_id, ts);
CREATE INDEX IF NOT EXISTS idx_solar_predictions_ts ON solar_predictions(ts);
CREATE INDEX IF NOT EXISTS idx_load_predictions_ts ON load_predictions(ts);
CREATE INDEX IF NOT EXISTS idx_device_requests_ts ON device_requests(ts);
