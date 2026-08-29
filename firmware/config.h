/**
 * @file config.h
 * @brief Configuration and calibration parameters for ESP32 HEMS Firmware v2.
 *
 * ARCHITECTURE (Dual-Bank Independent Source Selection + Aggregate Metering):
 * Controls 4 household loads, each independently selectable between a Grid
 * source and a represented Solar source.
 *
 * SAFETY & DISCLOSURE NOTES:
 * 1. "Solar" is a grid-derived representation used to validate transfer-switching
 *    logic. Never describe this prototype as demonstrating real solar power delivery.
 * 2. Break-before-make interlock (300 ms) is SOFTWARE-enforced only. It is NOT
 *    a certified mechanical ATS interlock. Software cannot protect against welded
 *    contacts or relay mechanical failures.
 * 3. The 4 downstream manual AC switches are purely mechanical cutoff switches
 *    with NO connection and NO sensing feedback to ESP32.
 * 4. Calibration constants are placeholder defaults. Real bench calibration is
 *    PENDING HARDWARE CALIBRATION.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ==============================================================================
// 1. NETWORK & BACKEND ENDPOINTS
// ==============================================================================
// Wi-Fi credentials are managed entirely by SmartProv captive portal provisioning.
// No hardcoded credentials exist in source code. Credentials are stored in
// NVS namespace "smartprov" and populated at boot via the SmartProv boot-gate.

// SmartProv configuration (must be defined before #include <SmartProv.h>)
#define SP_LED_PIN            2       // Shared with PIN_STATUS_LED (onboard LED)
#define SP_RESET_PIN          0       // GPIO 0 (BOOT button) for factory reset
#define SP_AP_PREFIX          "HEMS"  // AP name prefix: "HEMS_XXXX"

#define BACKEND_HOST          "https://share-affiliates-program-palm.trycloudflare.com"
#define INGEST_ENDPOINT       BACKEND_HOST "/ingest"
#define ACTION_POLL_ENDPOINT  BACKEND_HOST "/api/device/status"

#define INGEST_INTERVAL_MS    3000   // Telemetry push interval (3 seconds)
#define POLL_INTERVAL_MS      1500   // Backend command poll interval (1.5 seconds)

#define DEVICE_ID             "esp32_main"

// ==============================================================================
// 2. HARDWARE PIN DEFINITIONS (ESP32 30-Pin DevKit V1)
// ==============================================================================

// --- Digital & Analog Sensors ---
#define PIN_DHT22             4      // DHT22 Data (10k pull-up to 3.3V)
#define DHT_TYPE              DHT22

#define PIN_STATUS_LED        2      // Onboard status LED (Active-HIGH, WiFi indicator)

// Analog sensor pins — ADC1 only (ADC2 conflicts with WiFi radio use)
#define PIN_ACS712_CURRENT    34     // ADC1_CH6 (Input-only, via 10k/15k divider)
#define PIN_VOLTAGE_SENSOR    35     // ADC1_CH7 (Input-only, ZMPT101B AC transformer)

// --- Grid Relay Bank (Active-LOW, Songle SRD-05VDC-SL-C on external 5V supply) ---
#define PIN_GRID_RELAY_LOAD1  16
#define PIN_GRID_RELAY_LOAD2  17
#define PIN_GRID_RELAY_LOAD3  18
#define PIN_GRID_RELAY_LOAD4  19

// --- Represented-Solar Relay Bank (Active-LOW, Songle SRD-05VDC-SL-C on external 5V supply) ---
#define PIN_SOLAR_RELAY_LOAD1 21
#define PIN_SOLAR_RELAY_LOAD2 22
#define PIN_SOLAR_RELAY_LOAD3 23
#define PIN_SOLAR_RELAY_LOAD4 13

// --- Low-Voltage Source Selector Switches (ESP32 Inputs Only, NEVER AC) ---
// Wired: 3.3V -> Switch -> GPIO, with external 10k pull-down to GND.
// LOW (0V) = GRID, HIGH (3.3V) = SOLAR.
#define PIN_SOURCE_SELECTOR_LOAD1 26
#define PIN_SOURCE_SELECTOR_LOAD2 27
#define PIN_SOURCE_SELECTOR_LOAD3 32
#define PIN_SOURCE_SELECTOR_LOAD4 33

#define NUM_LOADS             4

// Load display names
#define LOAD1_NAME  "Load 1"
#define LOAD2_NAME  "Load 2"
#define LOAD3_NAME  "Load 3"
#define LOAD4_NAME  "Load 4"

// ==============================================================================
// 3. SOURCE-SELECTION & SAFETY TIMING
// ==============================================================================
// Break-before-make dead-time delay (ms)
// Guarantees both relays for a load are de-energized before the opposite relay turns ON.
#define BREAK_BEFORE_MAKE_MS  300

// Debounce duration for physical low-voltage toggle switches (ms)
#define SELECTOR_DEBOUNCE_MS  40

// ==============================================================================
// 4. ELECTRICAL SAMPLING & CALIBRATION (PENDING HARDWARE CALIBRATION)
// ==============================================================================
#define MAINS_FREQUENCY_HZ    50
#define SAMPLING_WINDOW_MS    200    // 10 full 50Hz cycles

#define ADC_RESOLUTION_BITS   12
#define ADC_MAX_VALUE         4095.0f
#define ADC_REF_VOLTAGE       3.30f

// ACS712 Voltage Divider Scaling:
// R1 = 10k (series), R2 = 15k (to GND) -> Ratio = 15 / (10 + 15) = 0.600
// Nominally scales 5V sensor output down to approx 3.0V for safe ESP32 ADC input.
#define ACS712_DIVIDER_RATIO  0.600f

// ACS712 Sensitivities per model (V/A at 5V sensor output):
//   ACS712-05B (5A)  : 0.185 V/A
//   ACS712-20A (20A) : 0.100 V/A
//   ACS712-30A (30A) : 0.066 V/A
// Default: ACS712-20A (0.100 V/A). Must be confirmed from physical module.
#define ACS712_SENSITIVITY    0.100f

// Calibration constants — MUST be established via physical bench calibration
// (CAL_ZERO / SET_VCAL / SET_SENS). Marked as PENDING HARDWARE CALIBRATION.
#define ACS712_ZERO_OFFSET    2048.0f   // Uncalibrated ADC zero-current placeholder
#define VOLTAGE_ZERO_OFFSET   2048.0f   // Uncalibrated ADC zero-voltage placeholder
#define VOLTAGE_CAL_FACTOR    0.1785f   // Uncalibrated voltage scaling placeholder

#define NOISE_CURRENT_CUTOFF  0.05f     // Amps, treated as zero below this threshold

// ==============================================================================
// 5. COMMANDED-VS-MEASURED MISMATCH DETECTION
// ==============================================================================
// If at least one load has a relay commanded ON (applied_source != OFF) but the
// aggregate measured current is below this threshold, a mismatch is suspected
// (e.g. downstream manual AC switch is physically OFF or load disconnected).
#define MISMATCH_CURRENT_THRESHOLD_A  0.10f

#endif // CONFIG_H
