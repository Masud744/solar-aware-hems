-- Phase 8 Remote Hardware Calibration Schema Migration
-- Run this in the Supabase SQL Editor to support persistent calibration tracking.

-- 1. Add calibration telemetry fields to sensor_readings table
ALTER TABLE sensor_readings
ADD COLUMN IF NOT EXISTS cal_status TEXT,
ADD COLUMN IF NOT EXISTS v_zero_offset REAL,
ADD COLUMN IF NOT EXISTS i_zero_offset REAL,
ADD COLUMN IF NOT EXISTS v_cal_factor REAL,
ADD COLUMN IF NOT EXISTS i_sensitivity REAL;

-- 2. Add calibration command queue field to device_controls
ALTER TABLE device_controls
ADD COLUMN IF NOT EXISTS cal_command TEXT DEFAULT 'NONE';
