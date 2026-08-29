/**
 * @file electricity_meter.h
 * @brief High-frequency synchronized AC power measurement class for ESP32.
 *
 * MEASUREMENT ARCHITECTURE:
 * - 1x ACS712 on GPIO 34 (ADC1_CH6) via 10k/15k voltage divider
 * - 1x ZMPT101B on GPIO 35 (ADC1_CH7)
 *
 * PHYSICAL SCOPE:
 * Sensors measure the AGGREGATE common neutral return / supply path.
 * They measure the instantaneous combined sum of all 4 loads.
 * Per-load current is NOT individually measurable with this hardware.
 *
 * CALIBRATION & PERSISTENCE:
 * Calibrated parameters (zero-offsets, voltage multiplier, current sensitivity)
 * are stored in ESP32 NVS flash (namespace "hems_cal") and survive reboots.
 */

#ifndef ELECTRICITY_METER_H
#define ELECTRICITY_METER_H

#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

struct PowerReading {
    float voltage_rms;
    float current_rms;
    float real_power_w;
    float apparent_power_va;
    float power_factor;
    float energy_accum_kwh;
    uint32_t sample_count;
    float achieved_rate_hz;
};

class ElectricityMeter {
public:
    ElectricityMeter(uint8_t pin_v, uint8_t pin_i);

    void begin();
    PowerReading sampleCycle();

    // Bench calibration methods
    void calibrateZeroOffsets(uint32_t calibration_duration_ms = 3000);

    void setVoltageZeroOffset(float offset);
    void setCurrentZeroOffset(float offset);
    void setVoltageCalFactor(float factor);
    void setCurrentSensitivity(float sensitivity);

    float getVoltageZeroOffset() const;
    float getCurrentZeroOffset() const;
    float getVoltageCalFactor() const;
    float getCurrentSensitivity() const;

    // NVS Calibration Persistence
    bool isCalibrated() const;
    String getCalStatus() const;
    void setCalStatus(const String &status);
    void saveCalibrationToNVS();
    void loadCalibrationFromNVS();
    void resetCalibrationNVS();

private:
    uint8_t _pin_voltage;
    uint8_t _pin_current;

    float _voltage_zero_offset;
    float _current_zero_offset;
    float _voltage_cal_factor;
    float _current_sensitivity;
    bool _is_calibrated;
    String _cal_status;

    float _accumulated_energy_kwh;
    unsigned long _last_sample_time_ms;
};

#endif // ELECTRICITY_METER_H
