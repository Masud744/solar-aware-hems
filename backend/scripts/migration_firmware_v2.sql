-- Migration for Firmware v2 & Dual-Bank System Integration

-- 1. Add new telemetry columns to sensor_readings table
ALTER TABLE sensor_readings 
ADD COLUMN IF NOT EXISTS power_factor REAL,
ADD COLUMN IF NOT EXISTS energy_accum_kwh REAL,
ADD COLUMN IF NOT EXISTS humidity_pct REAL,
ADD COLUMN IF NOT EXISTS grid_bank_enabled BOOLEAN,
ADD COLUMN IF NOT EXISTS solar_bank_enabled BOOLEAN,
ADD COLUMN IF NOT EXISTS relay_commanded_state JSONB,
ADD COLUMN IF NOT EXISTS mismatch_suspected BOOLEAN;

-- 2. Create device_controls table to store desired relay states for ESP32 polling
CREATE TABLE IF NOT EXISTS device_controls (
    device_id       TEXT PRIMARY KEY,
    load_1          TEXT NOT NULL DEFAULT 'off',
    load_2          TEXT NOT NULL DEFAULT 'off',
    load_3          TEXT NOT NULL DEFAULT 'off',
    load_4          TEXT NOT NULL DEFAULT 'off',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default device control state for main ESP32
INSERT INTO device_controls (device_id, load_1, load_2, load_3, load_4, updated_at)
VALUES ('esp32_main', 'off', 'off', 'off', 'off', NOW())
ON CONFLICT (device_id) DO NOTHING;
