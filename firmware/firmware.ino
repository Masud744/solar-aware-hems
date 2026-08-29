/**
 * @file firmware.ino
 * @brief Solar-Integrated HEMS — Phase 8 Hardware Firmware v2.
 *        Dual-Core FreeRTOS Decoupled Source Selection + Aggregate AC Metering
 *        with Remote Safe Web Calibration & NVS Persistence.
 *
 * FREERTOS TASK ARCHITECTURE:
 * - Core 1 (Control Task / loop()): Physical switch polling (40 ms debounce),
 *   local edge detection, single-owner relay transitions with 300 ms break-before-make,
 *   remote calibration routine execution, AC cycle sampling, and Serial CLI diagnostics.
 * - Core 0 (Network Task): Non-blocking Wi-Fi maintenance, background HTTP polling
 *   (/status, 1000 ms timeout), HTTP telemetry push (/ingest, 1000 ms timeout),
 *   and reconnect state synchronization.
 *
 * CALIBRATION CAPABILITIES:
 * - Supports both USB Serial CLI and Remote Web Calibration via backend.
 * - Auto CAL_ZERO checks/forces all loads to OFF before sampling.
 * - Zero-offsets, voltage multiplier, and sensitivity persist in NVS flash.
 *
 * TIMING SPECIFICATION:
 * Expected minimum response path = approximately 40 ms debounce + <1 ms processing
 * + 300 ms break-before-make dead-time, subject to actual hardware measurement.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <DHT.h>
#include <time.h>
#include <SmartProv.h>

#include "config.h"
#include "control_switches.h"
#include "relay_controller.h"
#include "electricity_meter.h"

// ---------------------------------------------------------------------------
// Hardware & Global Objects
// ---------------------------------------------------------------------------
RelayController relays;
ControlSwitches controlSwitches;
ElectricityMeter meter(PIN_VOLTAGE_SENSOR, PIN_ACS712_CURRENT);
DHT dht(PIN_DHT22, DHT_TYPE);
Preferences prefs;

// Wi-Fi credentials populated by SmartProv at boot from NVS "smartprov"
char provisioned_ssid[64]     = {0};
char provisioned_password[64] = {0};

// NTP server configuration (Bangladesh UTC+6)
const char* ntp_server = "pool.ntp.org";
const long gmt_offset_sec = 6 * 3600;
const int daylight_offset_sec = 0;

// Sensor cache (Initialized to NAN: unmeasured / pending reading)
float cached_temp_c = NAN;
float cached_humidity_pct = NAN;
bool dht_valid = false;
unsigned long lastDhtMs = 0;
unsigned long lastSerialTelemMs = 0;

char current_cal_status[32] = "UNCALIBRATED";

// ---------------------------------------------------------------------------
// FreeRTOS Inter-Task Communication Data Structures
// ---------------------------------------------------------------------------
enum CommandType : uint8_t {
    CMD_RELAY_SOURCE = 0,
    CMD_CAL_ZERO = 1,
    CMD_SET_VCAL = 2,
    CMD_SET_SENS = 3,
    CMD_RESET_CAL = 4
};

struct RemoteCommand {
    CommandType type;
    uint8_t load_idx;
    SourceState source;
    float value;
};

struct TelemetrySnapshot {
    PowerReading reading;
    float temp_c;
    float humidity_pct;
    SourceState selector_source[NUM_LOADS];
    SourceState desired_source[NUM_LOADS];
    SourceState applied_source[NUM_LOADS];
    bool mismatch_suspected;
    char cal_status[32];
    float v_zero_offset;
    float i_zero_offset;
    float v_cal_factor;
    float i_sensitivity;
};

QueueHandle_t remoteCommandQueue = NULL;
SemaphoreHandle_t telemetryMutex = NULL;
TelemetrySnapshot sharedTelemetrySnapshot;
volatile bool g_relayStateChangedEvent = false;

// ---------------------------------------------------------------------------
// Helper: ISO-8601 Timestamp String
// ---------------------------------------------------------------------------
String getIsoTimestamp() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return "2026-08-25T00:00:00+06:00";
    }
    char buf[35];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S+06:00", &timeinfo);
    return String(buf);
}

// ---------------------------------------------------------------------------
// Persistence (NVS) — Executed exclusively on Core 1
// ---------------------------------------------------------------------------
void saveDesiredStates() {
    prefs.begin("hems", false);
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        String key = "load" + String(i);
        prefs.putUChar(key.c_str(), (uint8_t)relays.getDesiredSource(i));
    }
    prefs.end();
}

// ---------------------------------------------------------------------------
// Network Helpers (Thread-safe status query)
// ---------------------------------------------------------------------------
bool isOnline() {
    return WiFi.status() == WL_CONNECTED;
}

// ---------------------------------------------------------------------------
// Network Task (Pinned to Core 0, Priority 1)
// ---------------------------------------------------------------------------
SourceState parseSourceToken(const String &body, const char* key1, const char* key2 = nullptr) {
    int keyPos = body.indexOf(key1);
    if (keyPos < 0 && key2 != nullptr) {
        keyPos = body.indexOf(key2);
    }
    if (keyPos < 0) return SRC_OFF;

    int colon = body.indexOf(':', keyPos);
    int quote1 = body.indexOf('"', colon + 1);
    int quote2 = body.indexOf('"', quote1 + 1);
    if (colon < 0 || quote1 < 0 || quote2 < 0) return SRC_OFF;
    String val = body.substring(quote1 + 1, quote2);
    val.toLowerCase();
    if (val == "grid") return SRC_GRID;
    if (val == "solar") return SRC_SOLAR;
    if (val == "off") return SRC_OFF;
    return SRC_OFF;
}

String parseCalCommandToken(const String &body) {
    int keyPos = body.indexOf("\"cal_command\"");
    if (keyPos < 0) return "";
    int colon = body.indexOf(':', keyPos);
    int quote1 = body.indexOf('"', colon + 1);
    int quote2 = body.indexOf('"', quote1 + 1);
    if (colon < 0 || quote1 < 0 || quote2 < 0) return "";
    return body.substring(quote1 + 1, quote2);
}

String parseLastCommandTimestamp(const String &body) {
    int keyPos = body.indexOf("\"last_command_ts\"");
    if (keyPos < 0) return "";
    int colon = body.indexOf(':', keyPos);
    if (colon < 0) return "";
    int nullPos = body.indexOf("null", colon);
    if (nullPos >= 0 && nullPos < colon + 10) return "";
    int quote1 = body.indexOf('"', colon + 1);
    int quote2 = body.indexOf('"', quote1 + 1);
    if (quote1 < 0 || quote2 < 0) return "";
    return body.substring(quote1 + 1, quote2);
}

void pollBackendCommandNetwork() {
    if (!isOnline()) return;

    WiFiClientSecure client;
    client.setInsecure(); // Explicitly bypass CA validation for Cloudflare tunnel
    HTTPClient http;
    http.setTimeout(4000); // 4-second timeout for TLS handshake over mobile hotspot
    http.begin(client, String(ACTION_POLL_ENDPOINT) + "?device_id=" + DEVICE_ID);
    int code = http.GET();

    static unsigned long lastPollLogMs = 0;
    static String lastAppliedCommandTs = "";
    static bool initialCommandBaselineEstablished = false;
    unsigned long now = millis();

    if (code == 200) {
        String body = http.getString();
        String currentCommandTs = parseLastCommandTimestamp(body);

        if (now - lastPollLogMs >= 10000) {
            lastPollLogMs = now;
            Serial.printf("[NET] Poll /api/device/status -> HTTP 200 OK | Body: %s\n", body.c_str());
        }

        // 1. Relay commands: ONLY dispatch when a genuinely new last_command_ts is received from the dashboard
        if (!initialCommandBaselineEstablished) {
            lastAppliedCommandTs = currentCommandTs;
            initialCommandBaselineEstablished = true;
            Serial.printf("[NET] Initial boot command baseline locked (last_command_ts: '%s') -> No stale commands executed\n",
                          currentCommandTs.c_str());
        } else if (currentCommandTs.length() > 0 && currentCommandTs != lastAppliedCommandTs) {
            lastAppliedCommandTs = currentCommandTs;
            Serial.printf("[NET] New remote dashboard command detected (last_command_ts: '%s') -> Dispatching to Core 1\n",
                          currentCommandTs.c_str());

            for (uint8_t i = 0; i < NUM_LOADS; i++) {
                String key1 = "\"load_" + String(i + 1) + "\"";
                String key2 = "\"load" + String(i + 1) + "\"";
                SourceState remoteTarget = parseSourceToken(body, key1.c_str(), key2.c_str());

                RemoteCommand cmd = {CMD_RELAY_SOURCE, i, remoteTarget, 0.0f};
                xQueueSend(remoteCommandQueue, &cmd, 0);
            }
        }

        // 2. Remote calibration commands
        String calCmd = parseCalCommandToken(body);
        if (calCmd.length() > 0 && !calCmd.equalsIgnoreCase("NONE")) {
            Serial.printf("[NET] Poll received active cal_command: %s\n", calCmd.c_str());
            if (calCmd.equalsIgnoreCase("CAL_ZERO")) {
                RemoteCommand cmd = {CMD_CAL_ZERO, 0, SRC_OFF, 0.0f};
                xQueueSend(remoteCommandQueue, &cmd, 0);
            }
            else if (calCmd.startsWith("SET_VCAL ")) {
                float val = calCmd.substring(9).toFloat();
                if (val > 0.0f) {
                    RemoteCommand cmd = {CMD_SET_VCAL, 0, SRC_OFF, val};
                    xQueueSend(remoteCommandQueue, &cmd, 0);
                }
            }
            else if (calCmd.startsWith("SET_SENS ")) {
                float val = calCmd.substring(9).toFloat();
                if (val > 0.0f) {
                    RemoteCommand cmd = {CMD_SET_SENS, 0, SRC_OFF, val};
                    xQueueSend(remoteCommandQueue, &cmd, 0);
                }
            }
            else if (calCmd.equalsIgnoreCase("RESET_CAL")) {
                RemoteCommand cmd = {CMD_RESET_CAL, 0, SRC_OFF, 0.0f};
                xQueueSend(remoteCommandQueue, &cmd, 0);
            }
        }
    } else {
        if (now - lastPollLogMs >= 10000) {
            lastPollLogMs = now;
            Serial.printf("[NET] Poll /api/device/status ERROR -> HTTP Code: %d (%s) | Target: %s\n",
                          code, http.errorToString(code).c_str(), ACTION_POLL_ENDPOINT);
        }
    }
    http.end();
}

void pushTelemetryNetwork(bool isSyncEvent) {
    if (!isOnline()) return;

    TelemetrySnapshot snap;
    if (xSemaphoreTake(telemetryMutex, pdMS_TO_TICKS(20)) == pdTRUE) {
        snap = sharedTelemetrySnapshot;
        xSemaphoreGive(telemetryMutex);
    } else {
        return; // Skip cycle if mutex is momentarily held
    }

    String payload = "{";
    payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
    payload += "\"ts\":\"" + getIsoTimestamp() + "\",";
    payload += "\"voltage_v\":" + String(snap.reading.voltage_rms, 2) + ",";
    payload += "\"current_a\":" + String(snap.reading.current_rms, 3) + ",";
    payload += "\"power_w\":" + String(snap.reading.real_power_w, 2) + ",";
    payload += "\"power_factor\":" + String(snap.reading.power_factor, 3) + ",";
    payload += "\"energy_accum_kwh\":" + String(snap.reading.energy_accum_kwh, 5) + ",";
    payload += "\"temperature_c\":" + (isnan(snap.temp_c) ? "null" : String(snap.temp_c, 2)) + ",";
    payload += "\"humidity_pct\":" + (isnan(snap.humidity_pct) ? "null" : String(snap.humidity_pct, 1)) + ",";

    // Calibration telemetry fields
    payload += "\"cal_status\":\"" + String(snap.cal_status) + "\",";
    payload += "\"v_zero_offset\":" + String(snap.v_zero_offset, 2) + ",";
    payload += "\"i_zero_offset\":" + String(snap.i_zero_offset, 2) + ",";
    payload += "\"v_cal_factor\":" + String(snap.v_cal_factor, 6) + ",";
    payload += "\"i_sensitivity\":" + String(snap.i_sensitivity, 4) + ",";

    // Four physical source-selector states
    payload += "\"source_selectors\":{";
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (i > 0) payload += ",";
        payload += "\"load_" + String(i + 1) + "\":\"" + String(RelayController::sourceToStr(snap.selector_source[i])) + "\"";
    }
    payload += "},";

    // Three-state model per load
    payload += "\"relay_commanded_state\":{";
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (i > 0) payload += ",";
        payload += "\"load_" + String(i + 1) + "\":{";
        payload += "\"name\":\"" + String(relays.getLoadName(i)) + "\",";
        payload += "\"selector_source\":\"" + String(RelayController::sourceToStr(snap.selector_source[i])) + "\",";
        payload += "\"desired_source\":\"" + String(RelayController::sourceToStr(snap.desired_source[i])) + "\",";
        payload += "\"applied_source\":\"" + String(RelayController::sourceToStr(snap.applied_source[i])) + "\"";
        payload += "}";
    }
    payload += "},";

    payload += "\"physical_switch_feedback_available\":false,";
    payload += "\"mismatch_suspected\":" + String(snap.mismatch_suspected ? "true" : "false");
    payload += "}";

    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;
    http.setTimeout(4000);
    http.begin(client, INGEST_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(payload);

    static unsigned long lastIngestLogMs = 0;
    unsigned long now = millis();

    if (code == 200) {
        String resp = http.getString();
        if (now - lastIngestLogMs >= 10000 || isSyncEvent) {
            lastIngestLogMs = now;
            Serial.printf("[NET] Ingest /ingest -> HTTP 200 OK | Resp: %s\n", resp.c_str());
        }
    } else {
        if (now - lastIngestLogMs >= 10000) {
            lastIngestLogMs = now;
            Serial.printf("[NET] Ingest /ingest ERROR -> HTTP Code: %d (%s) | Target: %s\n",
                          code, http.errorToString(code).c_str(), INGEST_ENDPOINT);
        }
    }
    http.end();
}

void networkTask(void *pvParameters) {
    unsigned long lastPollMs = 0;
    unsigned long lastIngestMs = 0;
    unsigned long lastWiFiRetryMs = 0;
    const unsigned long WIFI_RETRY_INTERVAL_MS = 10000;
    bool wasOnline = false;

    // Wi-Fi is already connected by SmartProv boot-gate.
    // NTP sync and reconnect use the provisioned credentials.
    configTime(gmt_offset_sec, daylight_offset_sec, ntp_server);

    while (true) {
        unsigned long now = millis();
        bool currentlyOnline = isOnline();

        if (!currentlyOnline) {
            // Rate-limited non-blocking reconnection attempt
            if (now - lastWiFiRetryMs >= WIFI_RETRY_INTERVAL_MS) {
                lastWiFiRetryMs = now;
                WiFi.mode(WIFI_STA);
                WiFi.begin(provisioned_ssid, provisioned_password);
            }
        } else {
            // STATE SYNCHRONIZATION ON RECONNECT
            if (!wasOnline) {
                Serial.println(F("\n======================= NETWORK CONNECTED ======================="));
                Serial.printf("  SSID            : %s\n", provisioned_ssid);
                Serial.printf("  ESP32 Local IP  : %s\n", WiFi.localIP().toString().c_str());
                Serial.printf("  Gateway IP      : %s\n", WiFi.gatewayIP().toString().c_str());
                Serial.printf("  DNS IP          : %s\n", WiFi.dnsIP().toString().c_str());
                Serial.printf("  Target Backend  : %s\n", BACKEND_HOST);
                Serial.printf("  HTTPS Client    : WiFiClientSecure (setInsecure = true)\n");
                Serial.println(F("=================================================================\n"));
                pushTelemetryNetwork(true);
            }

            // Event-driven immediate fast telemetry push on relay state change
            if (g_relayStateChangedEvent) {
                g_relayStateChangedEvent = false;
                Serial.println(F("[NET] Relay transition event detected -> Immediate fast telemetry push"));
                pushTelemetryNetwork(true);
                lastIngestMs = now;
            }

            // Periodic backend poll (every 1500 ms)
            if (now - lastPollMs >= POLL_INTERVAL_MS) {
                lastPollMs = now;
                pollBackendCommandNetwork();
            }

            // Periodic telemetry push (every 3000 ms)
            if (now - lastIngestMs >= INGEST_INTERVAL_MS) {
                lastIngestMs = now;
                pushTelemetryNetwork(false);
            }
        }

        wasOnline = currentlyOnline;
        vTaskDelay(pdMS_TO_TICKS(50)); // Yield to allow IDLE task execution on Core 0
    }
}

// ---------------------------------------------------------------------------
// Serial Diagnostics on Core 1
// ---------------------------------------------------------------------------
void printSystemStatus() {
    PowerReading r = meter.sampleCycle();
    Serial.println(F("\n======================= HEMS SYSTEM STATUS ======================="));
    Serial.printf("  WiFi Status      : %s (SSID: %s)\n", isOnline() ? "CONNECTED" : "OFFLINE", provisioned_ssid);
    Serial.printf("  Timestamp (UTC+6): %s\n", getIsoTimestamp().c_str());
    Serial.printf("  Calibration State: %s (NVS Persisted: %s)\n", current_cal_status, meter.isCalibrated() ? "YES" : "NO (Defaults)");
    Serial.println(F("------------------------------------------------------------------"));
    Serial.println(F("  PHYSICAL SOURCE-SELECTOR GPIO DIAGNOSTICS:"));
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        uint8_t pin = controlSwitches.getPin(i);
        bool raw = controlSwitches.getRawState(i);
        SourceState debounced = controlSwitches.getSelectorSource(i);
        Serial.printf("    Load %d: GPIO %-2d -> Raw Level: %d (%-4s) | Debounced State: %-5s\n",
                      i + 1, pin, raw ? 1 : 0, raw ? "HIGH" : "LOW",
                      RelayController::sourceToStr(debounced));
    }
    Serial.println(F("------------------------------------------------------------------"));
    Serial.println(F("  LOAD | SELECTOR (PHYS) | DESIRED (SYS) | APPLIED (RELAY) | GRID PIN | SOLAR PIN"));
    Serial.println(F("  -----+-----------------+---------------+-----------------+----------+----------"));
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        Serial.printf("   L%d  |     %-10s  |    %-10s |    %-11s  | GPIO %-3d | GPIO %-3d\n",
                      i + 1,
                      RelayController::sourceToStr(relays.getSelectorSource(i)),
                      RelayController::sourceToStr(relays.getDesiredSource(i)),
                      RelayController::sourceToStr(relays.getAppliedSource(i)),
                      relays.getGridPin(i),
                      relays.getSolarPin(i));
    }
    Serial.println(F("------------------------------------------------------------------"));
    Serial.println(F("  [NOTE] Downstream Manual AC Switches: No sensing feedback"));
    Serial.println(F("  [NOTE] ACS712 / ZMPT101B: Aggregate common measurement only"));
    Serial.printf("  Voltage RMS      : %.2f V  (Zero: %.1f | CalFactor: %.6f)\n", r.voltage_rms, meter.getVoltageZeroOffset(), meter.getVoltageCalFactor());
    Serial.printf("  Current RMS      : %.3f A  (Zero: %.1f | Sens: %.1f mV/A)\n", r.current_rms, meter.getCurrentZeroOffset(), meter.getCurrentSensitivity() * 1000.0f);
    Serial.printf("  True Real Power  : %.2f W\n", r.real_power_w);
    Serial.printf("  Apparent Power   : %.2f VA\n", r.apparent_power_va);
    Serial.printf("  Power Factor     : %.3f\n", r.power_factor);
    Serial.printf("  Accum. Energy    : %.5f kWh\n", r.energy_accum_kwh);
    if (dht_valid && !isnan(cached_temp_c) && !isnan(cached_humidity_pct)) {
        Serial.printf("  Temperature      : %.1f °C | Humidity: %.1f %%\n", cached_temp_c, cached_humidity_pct);
    } else {
        Serial.println(F("  Temperature      : SENSOR ERROR (NaN / Check GPIO 4 & 10k pull-up)"));
        Serial.println(F("  Humidity         : SENSOR ERROR (NaN / Check GPIO 4 & 10k pull-up)"));
    }
    Serial.println(F("==================================================================\n"));
}

void handleSerialCLI() {
    if (!Serial.available()) return;

    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() == 0) return;

    if (cmd.equalsIgnoreCase("STATUS") || cmd.equalsIgnoreCase("READ")) {
        printSystemStatus();
    }
    else if (cmd.equalsIgnoreCase("CAL_ZERO")) {
        Serial.println(F("[CAL] Verifying all loads are OFF before zero calibration..."));
        if (relays.anyLoadEnergized()) {
            relays.allOff();
            saveDesiredStates();
            delay(400);
        }
        strncpy(current_cal_status, "CALIBRATING", sizeof(current_cal_status));
        meter.calibrateZeroOffsets(3000);
        strncpy(current_cal_status, "CALIBRATED", sizeof(current_cal_status));
        Serial.printf("  -> Voltage Zero Offset : %.2f ADC counts\n", meter.getVoltageZeroOffset());
        Serial.printf("  -> Current Zero Offset : %.2f ADC counts\n", meter.getCurrentZeroOffset());
        Serial.println(F("[CAL] Zero calibration complete. Persisted to NVS flash."));
    }
    else if (cmd.startsWith("SET_VCAL ")) {
        float factor = cmd.substring(9).toFloat();
        if (factor > 0.0f) {
            meter.setVoltageCalFactor(factor);
            meter.setCalStatus("VOLTAGE_CALIBRATED");
            meter.saveCalibrationToNVS();
            strncpy(current_cal_status, "VOLTAGE_CALIBRATED", sizeof(current_cal_status));
            Serial.printf("[CAL] Voltage cal factor set and persisted: %.6f (Status: VOLTAGE_CALIBRATED)\n", meter.getVoltageCalFactor());
        }
    }
    else if (cmd.startsWith("SET_SENS ")) {
        float sens = cmd.substring(9).toFloat();
        if (sens > 0.0f) {
            meter.setCurrentSensitivity(sens);
            if (meter.getVoltageCalFactor() != VOLTAGE_CAL_FACTOR || meter.getCalStatus() == "VOLTAGE_CALIBRATED") {
                meter.setCalStatus("FULLY_CALIBRATED");
                strncpy(current_cal_status, "FULLY_CALIBRATED", sizeof(current_cal_status));
            } else {
                meter.setCalStatus("CURRENT_CALIBRATED");
                strncpy(current_cal_status, "CURRENT_CALIBRATED", sizeof(current_cal_status));
            }
            meter.saveCalibrationToNVS();
            Serial.printf("[CAL] ACS712 Sensitivity set and persisted: %.1f mV/A (Status: %s)\n", meter.getCurrentSensitivity() * 1000.0f, current_cal_status);
        }
    }
    else if (cmd.equalsIgnoreCase("RESET_CAL")) {
        meter.resetCalibrationNVS();
        strncpy(current_cal_status, "UNCALIBRATED", sizeof(current_cal_status));
        Serial.println(F("[CAL] Calibration cleared from NVS flash. Reset to defaults."));
    }
    else if (cmd.startsWith("RELAY ")) {
        int firstSpace = cmd.indexOf(' ');
        int secondSpace = cmd.indexOf(' ', firstSpace + 1);
        if (secondSpace > 0) {
            int loadIdx = cmd.substring(firstSpace + 1, secondSpace).toInt() - 1;
            String srcStr = cmd.substring(secondSpace + 1);
            srcStr.toLowerCase();
            SourceState src = SRC_OFF;
            if (srcStr == "grid") src = SRC_GRID;
            else if (srcStr == "solar") src = SRC_SOLAR;

            if (loadIdx >= 0 && loadIdx < NUM_LOADS) {
                Serial.printf("[CLI] Manual override: Load %d desired_source = %s\n",
                              loadIdx + 1, srcStr.c_str());
                relays.setDesiredSource((uint8_t)loadIdx, src);
                saveDesiredStates();
                relays.update();
            }
        }
    }
    else if (cmd.equalsIgnoreCase("ALL_OFF")) {
        relays.allOff();
        saveDesiredStates();
    }
    else if (cmd.equalsIgnoreCase("HELP")) {
        Serial.println(F("\n=== ESP32 HEMS FIRMWARE v2 CLI COMMANDS ==="));
        Serial.println(F("  STATUS                  : Display full 3-state load table & AC telemetry"));
        Serial.println(F("  RELAY <1-4> <off|grid|solar> : Simulate remote backend command"));
        Serial.println(F("  ALL_OFF                 : Force all loads to OFF immediately"));
        Serial.println(F("  CAL_ZERO                : Run zero-offset calibration (3s burst, auto-OFF loads)"));
        Serial.println(F("  SET_VCAL <factor>       : Set voltage scaling factor (persists to NVS)"));
        Serial.println(F("  SET_SENS <volts/amp>    : Set ACS712 sensitivity (persists to NVS)"));
        Serial.println(F("  RESET_CAL               : Reset calibration constants in NVS to defaults"));
        Serial.println(F("  HELP                    : Show this menu"));
        Serial.println(F("===========================================\n"));
    }
}

// ---------------------------------------------------------------------------
// Setup (Core 1)
// ---------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(200);

    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // =========================================================================
    // PHASE 0: SmartProv Wi-Fi Provisioning Boot-Gate
    // =========================================================================
    // SmartProv runs EXCLUSIVELY here in setup(). It either:
    //   A) Finds stored credentials in NVS "smartprov" → connects in STA mode
    //   B) No credentials → starts AP captive portal → user enters Wi-Fi →
    //      saves to NVS → ESP.restart() → re-enters setup(), takes path A
    //
    // SmartProv is dynamically allocated and destroyed after connection to
    // reclaim heap. After this block, SmartProv has no retained references,
    // callbacks, or runtime dependencies.
    // =========================================================================
    {
        Serial.println(F("\n[BOOT] SmartProv Wi-Fi provisioning boot-gate starting..."));

        SmartProv* prov = new SmartProv();
        prov->begin(SP_RESET_PIN, SP_LED_PIN);

        // Block here until SmartProv establishes a Wi-Fi connection.
        // If provisioning is needed (no stored credentials), SmartProv runs
        // an AP captive portal. After the user submits credentials,
        // SmartProv saves them and calls ESP.restart() — this function
        // never returns in that case.
        while (!prov->isConnected()) {
            prov->update();
            yield();  // Feed watchdog during provisioning loop
        }

        // Wi-Fi is connected. Extract the active credentials for
        // the HEMS networkTask reconnection logic.
        String ssid = prov->getSSID();
        strncpy(provisioned_ssid, ssid.c_str(), sizeof(provisioned_ssid) - 1);

        // SmartProv stores credentials in NVS "smartprov". Retrieve the
        // password from the storage layer for reconnection use.
        {
            SP_Storage& storage = prov->getStorage();
            SPConfig cfg = storage.load();
            SPWiFiEntry firstNet = storage.getFirstNetwork(cfg);
            strncpy(provisioned_password, firstNet.password, sizeof(provisioned_password) - 1);
        }

        Serial.printf("[BOOT] SmartProv connected — SSID: %s | IP: %s\n",
                      provisioned_ssid, prov->getIP().c_str());

        // =====================================================================
        // SAFE DESTRUCTION: SmartProv has no persistent background tasks,
        // no FreeRTOS tasks, no ISRs, and no retained callbacks after
        // reaching SP_APP_CONNECTED. The WebServer and DNSServer were never
        // started (stored credentials path). The WiFi STA connection persists
        // independently of the SmartProv object. delete is safe.
        // =====================================================================
        delete prov;
        prov = nullptr;
        Serial.printf("[BOOT] SmartProv released — Free heap: %u bytes\n",
                      ESP.getFreeHeap());
    }

    // 1. Initialize FreeRTOS Queues and Mutexes
    remoteCommandQueue = xQueueCreate(16, sizeof(RemoteCommand));
    telemetryMutex = xSemaphoreCreateMutex();

    // 2. Initialize hardware modules (Core 1 is single owner of relay GPIOs)
    relays.begin();
    controlSwitches.begin();
    meter.begin();
    dht.begin();
    pinMode(PIN_DHT22, INPUT_PULLUP);
    delay(50); // Allow DHT22 line to stabilize

    // Check calibration status from NVS
    strncpy(current_cal_status, meter.getCalStatus().c_str(), sizeof(current_cal_status));

    // 3. BOOT PRECEDENCE: Physical Selector Position > Previous NVS State
    Serial.println(F("\n[BOOT] Sampling physical source selectors for initial baseline (Physical > NVS)..."));
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        SourceState init_phys = controlSwitches.getSelectorSource(i);
        relays.setSelectorSource(i, init_phys);
        relays.setDesiredSource(i, init_phys);
        Serial.printf("  -> Load %d (%s): Physical Switch = %s -> Initial desired_source = %s\n",
                      i + 1, relays.getLoadName(i),
                      RelayController::sourceToStr(init_phys),
                      RelayController::sourceToStr(init_phys));
    }
    saveDesiredStates();

    // Apply initial relay states with break-before-make
    relays.update();

    // 4. Launch Network Task on Core 0 (Low Priority: 1)
    //    Wi-Fi is ALREADY connected by SmartProv. networkTask handles
    //    reconnection, polling, and telemetry push from here.
    xTaskCreatePinnedToCore(
        networkTask,
        "NetworkTask",
        12288,
        NULL,
        1,
        NULL,
        0
    );

    Serial.println(F("\n=============================================================="));
    Serial.println(F("  Solar-Integrated Risk-Aware HEMS — Firmware v2 Initialized"));
    Serial.println(F("  Wi-Fi Provisioning: SmartProv v2.1.3 (Boot-Gate)"));
    Serial.println(F("  Dual-Core FreeRTOS Decoupled Control + Source Selection"));
    Serial.println(F("=============================================================="));
}

// ---------------------------------------------------------------------------
// Main Control Loop (Core 1, High Priority)
// ---------------------------------------------------------------------------
void loop() {
    // 0. Handle Serial CLI commands
    handleSerialCLI();

    // 1. Poll physical source-selector switches (40 ms debounce)
    controlSwitches.pollAndDebounce();

    // 2. Check for physical switch edge events (Local Hardware Override)
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        SourceState current_phys = controlSwitches.getSelectorSource(i);
        relays.setSelectorSource(i, current_phys);

        if (controlSwitches.hasEdgeChanged(i)) {
            // Local physical toggle overrides desired_source immediately
            Serial.printf("[EDGE] Load %d (%s): Physical switch flipped to %s -> Local override of desired_source\n",
                          i + 1, relays.getLoadName(i), RelayController::sourceToStr(current_phys));
            relays.setDesiredSource(i, current_phys);
            controlSwitches.clearEdgeFlag(i);
            saveDesiredStates();
        }
    }

    // 3. Drain incoming remote commands from Network Task (Core 0 -> Core 1)
    RemoteCommand cmd;
    while (xQueueReceive(remoteCommandQueue, &cmd, 0) == pdTRUE) {
        if (cmd.type == CMD_RELAY_SOURCE) {
            if (cmd.load_idx < NUM_LOADS) {
                // Apply backend command if different from current desired_source
                if (cmd.source != relays.getDesiredSource(cmd.load_idx)) {
                    Serial.printf("[BACKEND] Load %d (%s): Remote command applied -> desired_source = %s (selector remains %s)\n",
                                  cmd.load_idx + 1, relays.getLoadName(cmd.load_idx),
                                  RelayController::sourceToStr(cmd.source),
                                  RelayController::sourceToStr(relays.getSelectorSource(cmd.load_idx)));
                    relays.setDesiredSource(cmd.load_idx, cmd.source);
                    saveDesiredStates();
                }
            }
        }
        else if (cmd.type == CMD_CAL_ZERO) {
            Serial.println(F("[CAL] Remote CAL_ZERO received. Verifying all loads are OFF..."));
            if (relays.anyLoadEnergized()) {
                Serial.println(F("[CAL] Some loads active -> Forcing ALL_OFF before zero calibration."));
                relays.allOff();
                saveDesiredStates();
                delay(400);
            }
            Serial.println(F("[CAL] All loads OFF (contacts settled)."));
            Serial.println(F("[CAL] Sampling physical ADC inputs started (3000 ms burst)..."));
            strncpy(current_cal_status, "CALIBRATING", sizeof(current_cal_status));
            meter.calibrateZeroOffsets(3000);
            meter.setCalStatus("ZERO_CALIBRATED");
            meter.saveCalibrationToNVS();
            strncpy(current_cal_status, "ZERO_CALIBRATED", sizeof(current_cal_status));
            Serial.println(F("[CAL] Sampling completed across 3000 ms."));
            Serial.printf("[CAL] V_ZERO = %.2f ADC counts (measured mean)\n", meter.getVoltageZeroOffset());
            Serial.printf("[CAL] I_ZERO = %.2f ADC counts (measured mean)\n", meter.getCurrentZeroOffset());
            Serial.println(F("[CAL] Calibration status updated -> ZERO_CALIBRATED (Partially Calibrated)."));
        }
        else if (cmd.type == CMD_SET_VCAL) {
            if (cmd.value > 0.0f) {
                meter.setVoltageCalFactor(cmd.value);
                meter.setCalStatus("VOLTAGE_CALIBRATED");
                meter.saveCalibrationToNVS();
                strncpy(current_cal_status, "VOLTAGE_CALIBRATED", sizeof(current_cal_status));
                Serial.printf("[CAL] Remote SET_VCAL applied: %.6f -> Status: VOLTAGE_CALIBRATED\n", meter.getVoltageCalFactor());
            }
        }
        else if (cmd.type == CMD_SET_SENS) {
            if (cmd.value > 0.0f) {
                meter.setCurrentSensitivity(cmd.value);
                if (meter.getVoltageCalFactor() != VOLTAGE_CAL_FACTOR || meter.getCalStatus() == "VOLTAGE_CALIBRATED") {
                    meter.setCalStatus("FULLY_CALIBRATED");
                    strncpy(current_cal_status, "FULLY_CALIBRATED", sizeof(current_cal_status));
                } else {
                    meter.setCalStatus("CURRENT_CALIBRATED");
                    strncpy(current_cal_status, "CURRENT_CALIBRATED", sizeof(current_cal_status));
                }
                meter.saveCalibrationToNVS();
                Serial.printf("[CAL] Remote SET_SENS applied: %.4f V/A (%.1f mV/A) -> Status: %s\n",
                              meter.getCurrentSensitivity(), meter.getCurrentSensitivity() * 1000.0f, current_cal_status);
            }
        }
        else if (cmd.type == CMD_RESET_CAL) {
            meter.resetCalibrationNVS();
            strncpy(current_cal_status, "UNCALIBRATED", sizeof(current_cal_status));
            Serial.println(F("[CAL] Remote RESET_CAL applied. Reset to uncalibrated defaults."));
        }
    }

    // 4. Apply any pending relay transitions via software break-before-make (300 ms dead-time)
    if (relays.update()) {
        g_relayStateChangedEvent = true;
    }

    unsigned long now = millis();

    // 5. Periodic DHT22 read (every 2.5s)
    if (now - lastDhtMs >= 2500) {
        lastDhtMs = now;
        float t = dht.readTemperature();
        float h = dht.readHumidity();
        if (!isnan(t)) {
            cached_temp_c = t;
        }
        if (!isnan(h)) {
            cached_humidity_pct = h;
        }
        if (!isnan(t) && !isnan(h)) {
            dht_valid = true;
        }
    }

    // 6. Periodic Meter Sampling & Serial Telemetry (every 1000 ms on Core 1)
    static unsigned long lastMeterSampleMs = 0;
    static PowerReading cachedReading;
    if (now - lastMeterSampleMs >= 1000 || g_relayStateChangedEvent) {
        lastMeterSampleMs = now;
        cachedReading = meter.sampleCycle();
    }

    if (now - lastSerialTelemMs >= 5000) {
        lastSerialTelemMs = now;
        bool anyCommandedOn = relays.anyLoadEnergized();
        bool mismatch = anyCommandedOn && (cachedReading.current_rms < MISMATCH_CURRENT_THRESHOLD_A);

        if (dht_valid && !isnan(cached_temp_c) && !isnan(cached_humidity_pct)) {
            Serial.printf("[TELEM] T=%.1fC H=%.1f%% | V=%.1fV I=%.3fA P=%.1fW PF=%.2f | L1:%s L2:%s L3:%s L4:%s | Cal:%s | Mismatch:%d | WiFi:%d\n",
                          cached_temp_c, cached_humidity_pct,
                          cachedReading.voltage_rms, cachedReading.current_rms, cachedReading.real_power_w, cachedReading.power_factor,
                          RelayController::sourceToStr(relays.getAppliedSource(0)),
                          RelayController::sourceToStr(relays.getAppliedSource(1)),
                          RelayController::sourceToStr(relays.getAppliedSource(2)),
                          RelayController::sourceToStr(relays.getAppliedSource(3)),
                          current_cal_status, mismatch, isOnline());
        } else {
            Serial.printf("[TELEM] T=SENSOR_ERROR H=SENSOR_ERROR | V=%.1fV I=%.3fA P=%.1fW PF=%.2f | L1:%s L2:%s L3:%s L4:%s | Cal:%s | Mismatch:%d | WiFi:%d\n",
                          cachedReading.voltage_rms, cachedReading.current_rms, cachedReading.real_power_w, cachedReading.power_factor,
                          RelayController::sourceToStr(relays.getAppliedSource(0)),
                          RelayController::sourceToStr(relays.getAppliedSource(1)),
                          RelayController::sourceToStr(relays.getAppliedSource(2)),
                          RelayController::sourceToStr(relays.getAppliedSource(3)),
                          current_cal_status, mismatch, isOnline());
        }
    }

    // 7. Update shared telemetry snapshot for Core 0 Network Task
    if (xSemaphoreTake(telemetryMutex, 0) == pdTRUE) {
        sharedTelemetrySnapshot.reading = cachedReading;
        sharedTelemetrySnapshot.temp_c = cached_temp_c;
        sharedTelemetrySnapshot.humidity_pct = cached_humidity_pct;
        for (uint8_t i = 0; i < NUM_LOADS; i++) {
            sharedTelemetrySnapshot.selector_source[i] = relays.getSelectorSource(i);
            sharedTelemetrySnapshot.desired_source[i] = relays.getDesiredSource(i);
            sharedTelemetrySnapshot.applied_source[i] = relays.getAppliedSource(i);
        }
        bool anyCommandedOn = relays.anyLoadEnergized();
        sharedTelemetrySnapshot.mismatch_suspected = anyCommandedOn &&
            (sharedTelemetrySnapshot.reading.current_rms < MISMATCH_CURRENT_THRESHOLD_A);

        strncpy(sharedTelemetrySnapshot.cal_status, current_cal_status, sizeof(sharedTelemetrySnapshot.cal_status));
        sharedTelemetrySnapshot.v_zero_offset = meter.getVoltageZeroOffset();
        sharedTelemetrySnapshot.i_zero_offset = meter.getCurrentZeroOffset();
        sharedTelemetrySnapshot.v_cal_factor = meter.getVoltageCalFactor();
        sharedTelemetrySnapshot.i_sensitivity = meter.getCurrentSensitivity();

        xSemaphoreGive(telemetryMutex);
    }

    // 8. Update status LED
    digitalWrite(PIN_STATUS_LED, isOnline() ? HIGH : LOW);
}
