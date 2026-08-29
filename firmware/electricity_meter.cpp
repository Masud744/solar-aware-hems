/**
 * @file electricity_meter.cpp
 * @brief Implementation of synchronized AC power measurement for ESP32 with NVS persistence.
 */

#include "electricity_meter.h"
#include <math.h>

ElectricityMeter::ElectricityMeter(uint8_t pin_v, uint8_t pin_i)
    : _pin_voltage(pin_v),
      _pin_current(pin_i),
      _voltage_zero_offset(VOLTAGE_ZERO_OFFSET),
      _current_zero_offset(ACS712_ZERO_OFFSET),
      _voltage_cal_factor(VOLTAGE_CAL_FACTOR),
      _current_sensitivity(ACS712_SENSITIVITY),
      _is_calibrated(false),
      _cal_status("UNCALIBRATED"),
      _accumulated_energy_kwh(0.0f),
      _last_sample_time_ms(0) {}

void ElectricityMeter::begin() {
    pinMode(_pin_voltage, INPUT);
    pinMode(_pin_current, INPUT);
    analogReadResolution(ADC_RESOLUTION_BITS);
    _last_sample_time_ms = millis();

    // Load persisted calibration from NVS flash
    loadCalibrationFromNVS();
}

void ElectricityMeter::loadCalibrationFromNVS() {
    Preferences prefs;
    prefs.begin("hems_cal", true); // read-only mode

    if (prefs.isKey("calibrated") && prefs.getBool("calibrated", false)) {
        _voltage_zero_offset = prefs.getFloat("v_zero", VOLTAGE_ZERO_OFFSET);
        _current_zero_offset = prefs.getFloat("i_zero", ACS712_ZERO_OFFSET);
        _voltage_cal_factor = prefs.getFloat("v_cal", VOLTAGE_CAL_FACTOR);
        _current_sensitivity = prefs.getFloat("i_sens", ACS712_SENSITIVITY);
        _cal_status = prefs.getString("cal_status", "ZERO_CALIBRATED");
        _is_calibrated = true;
        Serial.printf("[NVS] Loaded persisted calibration from flash: Status=%s (V_zero=%.2f, I_zero=%.2f, V_cal=%.6f, I_sens=%.4f)\n",
                      _cal_status.c_str(), _voltage_zero_offset, _current_zero_offset, _voltage_cal_factor, _current_sensitivity);
    } else {
        _is_calibrated = false;
        _cal_status = "UNCALIBRATED";
        Serial.println(F("[NVS] No persisted calibration found in flash. Using default uncalibrated placeholders."));
    }
    prefs.end();
}

void ElectricityMeter::saveCalibrationToNVS() {
    Preferences prefs;
    prefs.begin("hems_cal", false); // read-write mode
    prefs.putFloat("v_zero", _voltage_zero_offset);
    prefs.putFloat("i_zero", _current_zero_offset);
    prefs.putFloat("v_cal", _voltage_cal_factor);
    prefs.putFloat("i_sens", _current_sensitivity);
    prefs.putString("cal_status", _cal_status);
    prefs.putBool("calibrated", true);
    prefs.end();
    _is_calibrated = true;
    Serial.printf("[NVS] Saved calibration constants to flash successfully (Status: %s).\n", _cal_status.c_str());
}

void ElectricityMeter::resetCalibrationNVS() {
    Preferences prefs;
    prefs.begin("hems_cal", false);
    prefs.clear();
    prefs.end();

    _voltage_zero_offset = VOLTAGE_ZERO_OFFSET;
    _current_zero_offset = ACS712_ZERO_OFFSET;
    _voltage_cal_factor = VOLTAGE_CAL_FACTOR;
    _current_sensitivity = ACS712_SENSITIVITY;
    _is_calibrated = false;
    _cal_status = "UNCALIBRATED";
    Serial.println(F("[NVS] Cleared calibration from flash. Reset to defaults."));
}

String ElectricityMeter::getCalStatus() const { return _cal_status; }
void ElectricityMeter::setCalStatus(const String &status) { _cal_status = status; }

PowerReading ElectricityMeter::sampleCycle() {
    unsigned long start_time = micros();
    unsigned long window_us = SAMPLING_WINDOW_MS * 1000UL;

    double sum_v_sq = 0.0;
    double sum_i_sq = 0.0;
    double sum_p_inst = 0.0;
    uint32_t sample_count = 0;

    // Voltage divider scaling factor: R2 / (R1 + R2) = 15k / (10k + 15k) = 0.600
    // Scales 5V sensor output down to ~3.0V at ESP32 ADC pin
    float adc_to_volts = ADC_REF_VOLTAGE / ADC_MAX_VALUE;
    float current_scale = adc_to_volts / (ACS712_DIVIDER_RATIO * _current_sensitivity);

    while ((micros() - start_time) < window_us) {
        int raw_v = analogRead(_pin_voltage);
        int raw_i = analogRead(_pin_current);

        float v_inst = ((float)raw_v - _voltage_zero_offset) * _voltage_cal_factor;
        float i_inst = ((float)raw_i - _current_zero_offset) * current_scale;

        sum_v_sq += (double)(v_inst * v_inst);
        sum_i_sq += (double)(i_inst * i_inst);
        sum_p_inst += (double)(v_inst * i_inst);
        sample_count++;
    }

    unsigned long elapsed_us = micros() - start_time;
    float achieved_rate = (elapsed_us > 0) ? ((float)sample_count / ((float)elapsed_us / 1000000.0f)) : 0.0f;

    PowerReading reading;
    reading.sample_count = sample_count;
    reading.achieved_rate_hz = achieved_rate;

    if (sample_count > 0) {
        reading.voltage_rms = (float)sqrt(sum_v_sq / (double)sample_count);
        reading.current_rms = (float)sqrt(sum_i_sq / (double)sample_count);
        reading.real_power_w = (float)(sum_p_inst / (double)sample_count);

        // Noise floor cutoff
        if (reading.current_rms < NOISE_CURRENT_CUTOFF) {
            reading.current_rms = 0.0f;
            reading.real_power_w = 0.0f;
        }

        reading.apparent_power_va = reading.voltage_rms * reading.current_rms;

        if (reading.apparent_power_va > 0.001f) {
            reading.power_factor = reading.real_power_w / reading.apparent_power_va;
            if (reading.power_factor > 1.0f) reading.power_factor = 1.0f;
            if (reading.power_factor < -1.0f) reading.power_factor = -1.0f;
        } else {
            reading.power_factor = 1.0f;
        }
    } else {
        reading.voltage_rms = 0.0f;
        reading.current_rms = 0.0f;
        reading.real_power_w = 0.0f;
        reading.apparent_power_va = 0.0f;
        reading.power_factor = 1.0f;
    }

    // Energy integration (trapezoidal accumulation)
    unsigned long now_ms = millis();
    if (_last_sample_time_ms > 0) {
        float dt_hours = (float)(now_ms - _last_sample_time_ms) / 3600000.0f;
        if (dt_hours > 0.0f && dt_hours < 1.0f) {
            _accumulated_energy_kwh += (reading.real_power_w * dt_hours) / 1000.0f;
        }
    }
    _last_sample_time_ms = now_ms;
    reading.energy_accum_kwh = _accumulated_energy_kwh;

    return reading;
}

void ElectricityMeter::calibrateZeroOffsets(uint32_t calibration_duration_ms) {
    unsigned long start_ms = millis();
    double sum_v = 0.0;
    double sum_i = 0.0;
    double sum_v_sq = 0.0;
    double sum_i_sq = 0.0;
    int min_v = 4095, max_v = 0;
    int min_i = 4095, max_i = 0;
    uint32_t count = 0;

    while ((millis() - start_ms) < calibration_duration_ms) {
        int v = analogRead(_pin_voltage);
        int i = analogRead(_pin_current);

        sum_v += (double)v;
        sum_i += (double)i;
        sum_v_sq += (double)(v * v);
        sum_i_sq += (double)(i * i);

        if (v < min_v) min_v = v;
        if (v > max_v) max_v = v;
        if (i < min_i) min_i = i;
        if (i > max_i) max_i = i;

        count++;
        delay(1);
    }

    if (count > 0) {
        double mean_v = sum_v / (double)count;
        double mean_i = sum_i / (double)count;
        double var_v = (sum_v_sq / (double)count) - (mean_v * mean_v);
        double var_i = (sum_i_sq / (double)count) - (mean_i * mean_i);
        double std_v = (var_v > 0.0) ? sqrt(var_v) : 0.0;
        double std_i = (var_i > 0.0) ? sqrt(var_i) : 0.0;

        _voltage_zero_offset = (float)mean_v;
        _current_zero_offset = (float)mean_i;

        Serial.println(F("\n================= RAW ZERO-OFFSET SAMPLING AUDIT ================="));
        Serial.printf("  Duration         : %u ms | Total Samples: %u\n", calibration_duration_ms, count);
        Serial.printf("  Voltage (GPIO %d) : Min=%d, Max=%d, Range=%d, Mean=%.2f, StdDev=%.2f\n",
                      _pin_voltage, min_v, max_v, max_v - min_v, mean_v, std_v);
        Serial.printf("  Current (GPIO %d) : Min=%d, Max=%d, Range=%d, Mean=%.2f, StdDev=%.2f\n",
                      _pin_current, min_i, max_i, max_i - min_i, mean_i, std_i);
        Serial.println(F("==================================================================\n"));

        saveCalibrationToNVS();
    }
}

void ElectricityMeter::setVoltageZeroOffset(float offset) { 
    _voltage_zero_offset = offset; 
    saveCalibrationToNVS();
}

void ElectricityMeter::setCurrentZeroOffset(float offset) { 
    _current_zero_offset = offset; 
    saveCalibrationToNVS();
}

void ElectricityMeter::setVoltageCalFactor(float factor) { 
    _voltage_cal_factor = factor; 
    saveCalibrationToNVS();
}

void ElectricityMeter::setCurrentSensitivity(float sensitivity) { 
    _current_sensitivity = sensitivity; 
    saveCalibrationToNVS();
}

float ElectricityMeter::getVoltageZeroOffset() const { return _voltage_zero_offset; }
float ElectricityMeter::getCurrentZeroOffset() const { return _current_zero_offset; }
float ElectricityMeter::getVoltageCalFactor() const { return _voltage_cal_factor; }
float ElectricityMeter::getCurrentSensitivity() const { return _current_sensitivity; }
bool ElectricityMeter::isCalibrated() const { return _is_calibrated; }
