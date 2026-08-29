# Firmware v2 — ESP32 Dual-Bank Grid/Solar Source Selection Controller

> **Project:** Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework (Solar-Aware HEMS)  
> **Hardware Verification Status:** 
> - **VERIFIED ON PHYSICAL HARDWARE:** FreeRTOS dual-core task separation, SmartProv v2.1.3 captive-portal Wi-Fi provisioning (zero plaintext credentials, NVS storage, automatic STA reconnect, transient heap recovery), local source-selector debouncing and immediate switching (both online and offline), all 8 relay channels (Grid L1–L4 on GPIO 16/17/18/19, Solar L1–L3 on GPIO 21/22/23, Solar L4 on GPIO 13), 300 ms break-before-make dead-time interlock, DHT22 live temperature/humidity telemetry on GPIO 4, and rate-limited Wi-Fi state synchronization.
> - **PENDING HARDWARE CALIBRATION:** ACS712 current sensor variant & zero-offset calibration, ZMPT101B AC voltage transformer calibration, and full live-load AC power metering tests under 230V mains.

---

## 1. FreeRTOS Dual-Core Task Architecture

To prevent network operations (HTTP polling, telemetry uploads, DNS lookups, or router disconnects) from introducing latency into local physical switch operations, the firmware executes across both ESP32 Xtensa dual-core processors:

```
                  ┌──────────────────────────────────────────────────────────┐
                  │                 ESP32 DUAL-CORE ARCHITECTURE             │
                  └──────────────────────────────────────────────────────────┘
                                 │                                          │
            CORE 1 (Local Control Task)                    CORE 0 (Network & Telemetry Task)
             Priority: High (Priority 2)                     Priority: Low (Priority 1)
         ┌───────────────────────────────────┐          ┌───────────────────────────────────┐
         │ • Source Selector Polling         │          │ • Wi-Fi Maintenance (10s backoff) │
         │ • 40 ms Debounce & Edge Detect    │          │ • HTTP Backend Poll (/status)     │
         │ • Local Physical Overrides        │          │   (http.setTimeout = 1000 ms)     │
         │ • Check Network Command Queue     │          │ • HTTP Telemetry Push (/ingest)   │
         │ • SOLE OWNER: Relay GPIOs         │          │   (http.setTimeout = 1000 ms)     │
         │ • 300 ms Break-Before-Make        │          │ • Reconnect State Synchronization │
         │ • AC Metering & Serial CLI        │          │   (Zero direct relay GPIO access) │
         └───────────────────────────────────┘          └───────────────────────────────────┘
                           │                                          │
                           │ <──── [FreeRTOS Command Queue] ──────────┤
                           │       (16 items, Remote -> Local)        │
                           │                                          │
                           ├─────> [Telemetry Mutex Snapshot] ───────>│
                           │       (Live States -> Telemetry POST)    │
```

### Core Responsibilities:
1. **Core 1 — Local Hardware & Relay Control Task (`loop()`):**
   - **Single Owner Principle:** Core 1 is the **sole authority** that writes to relay GPIO pins (16, 17, 18, 19, 21, 22, 23, 13). Core 0 has zero access to relay GPIOs.
   - Polling of low-voltage source selectors on GPIO 26, 27, 32, 33 with a 40 ms debounce window.
   - Immediate edge detection: flipping a physical toggle switch immediately overrides `desired_source` on that load.
   - Draining remote commands from `remoteCommandQueue` without blocking.
   - Executing sequential 300 ms break-before-make transitions.
   - AC cycle sampling (`meter.sampleCycle()`) and DHT22 2.5-second reads.
   - Interactive Serial CLI diagnostics (`STATUS`, `RELAY`, `CAL_ZERO`, `HELP`).

2. **Core 0 — Network & Telemetry Task (`networkTask`):**
   - Pinned to Core 0 with priority 1 (stack size: 8192 bytes).
   - Manages Wi-Fi connection with a 10-second non-blocking retry rate limiter.
   - Periodically polls the backend for remote dispatch commands (`/status`, interval: 3000 ms, timeout: 1000 ms).
   - Periodically streams live system telemetry to `/ingest` (interval: 5000 ms, timeout: 1000 ms).
   - Reconnect state synchronization: pushes live ESP32 state upon reconnecting.

### Inter-Task Communication & Thread Safety:
- **Remote Command Queue (`remoteCommandQueue`):** A FreeRTOS queue (`16` items capacity, `sizeof(RemoteCommand) = 2 bytes`). Core 0 parses backend JSON and posts commands non-blockingly (`xQueueSend(..., 0)`). Core 1 drains pending commands on every loop iteration.
- **Telemetry State Mutex (`telemetryMutex`):** Protects the `sharedTelemetrySnapshot` struct. Core 1 updates the snapshot; Core 0 acquires the mutex with a 20 ms timeout, performs a fast memory copy ($< 1\ \mu\text{s}$), releases the mutex, and executes the HTTP POST. Core 1 is never blocked by network latency.

---

## 2. Low-Voltage Source Selectors (x4)

Four independent toggle switches provide local manual source selection (3.3V logic only).

> [!CAUTION]
> **ELECTRICAL ISOLATION REQUIREMENT:**
> Source selector switches are **LOW-VOLTAGE DC INPUTS ONLY**.
> They must **NEVER** connect to 230V AC mains, Grid AC, Solar AC, or relay output contacts.

- **Load 1 Selector:** GPIO 26 (`INPUT_PULLDOWN`, external 10kΩ pull-down to GND)
- **Load 2 Selector:** GPIO 27 (`INPUT_PULLDOWN`, external 10kΩ pull-down to GND)
- **Load 3 Selector:** GPIO 32 (`INPUT_PULLDOWN`, external 10kΩ pull-down to GND)
- **Load 4 Selector:** GPIO 33 (`INPUT_PULLDOWN`, external 10kΩ pull-down to GND)

### Logic & Edge Detection:
- `0V (LOW)` = **GRID**
- `3.3V (HIGH)` = **SOLAR**
- **Boot Baseline:** `ControlSwitches::begin()` configures `INPUT_PULLDOWN`, waits a 50 ms settling window, and establishes the settled baseline into both `raw_last` and `stable_state` with `edge_detected = false`. Startup initialization can never fire a false edge.
- **Debounce Window:** 40 ms debounce timer prevents contact bounce from generating multiple transitions.
- **Physical Edge Override:** When a human flips a toggle switch, the debounced transition immediately overrides `desired_source` on Core 1 without waiting for network acknowledgement.

---

## 3. Three-State Model per Load & Wi-Fi Reconnect Policy

For each load $i \in \{1, 2, 3, 4\}$, the firmware maintains:

1. **`selector_source`** $\in \{\text{GRID}, \text{SOLAR}\}$:
   - Live debounced physical toggle switch position.
2. **`desired_source`** $\in \{\text{GRID}, \text{SOLAR}, \text{OFF}\}$:
   - Target commanded state (from physical edge, backend command, or emergency OFF).
3. **`applied_source`** $\in \{\text{GRID}, \text{SOLAR}, \text{OFF}\}$:
   - Currently energized relay coil state following break-before-make.

### Operational Rules:
- **Boot Precedence:** `Physical Selector Position > Previous NVS State`. At boot, the settled physical toggle switch position sets the initial `desired_source` for each load.
- **Physical Edge Override:** A physical toggle transition immediately overrides `desired_source` to match the new physical position.
- **Remote / Backend Control:** Backend commands update `desired_source` when online without rewriting `selector_source`. Mismatches remain visible in telemetry.
- **OFF State:** An explicit `desired_source = OFF` keeps the load de-energized even if the physical switch remains at GRID or SOLAR.
- **Wi-Fi Reconnect Policy:** **STATE SYNCHRONIZATION, NOT AUTOMATIC OVERRIDE.**
  - When Wi-Fi reconnects, the currently applied relay states remain unchanged.
  - The live `selector_source`, `desired_source`, and `applied_source` are pushed immediately to `/ingest`.
  - Stale pre-disconnect backend commands are never automatically applied to the hardware. Only a subsequent explicit backend command can change the relay state.

---

## 4. Software Relay Interlock & Break-Before-Make

```
[Software Break-Before-Make Transition Sequence]
1. Current Active Relay -> Driven HIGH (De-energized / OFF)
2. Enforce Mandatory Safety Dead-Time -> 300 ms (Both Grid and Solar coils OFF)
3. Target Relay -> Driven LOW (Energized / ON) -> applied_source updated
```

> [!WARNING]
> **Safety Disclosure:** The 300 ms break-before-make interlock is a **software-only safety timing mechanism** implemented in firmware. It does **NOT** provide certified mechanical ATS interlocking or physical isolation between live AC sources.

---

## 5. Hardware Pinout Allocation (ESP32 30-Pin DevKit V1)

| Peripheral / Channel | ESP32 GPIO | Pin Mode | Logic / Electrical Level | Hardware Destination / Notes |
|---|---|---|---|---|
| **DHT22 Data** | **GPIO 4** | `INPUT` | Digital 1-Wire, 3.3V | External 10kΩ pull-up to 3.3V (**Verified**) |
| **Grid Relay — Load 1** | **GPIO 16** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Grid Board IN1 (**Verified**) |
| **Grid Relay — Load 2** | **GPIO 17** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Grid Board IN2 (**Verified**) |
| **Grid Relay — Load 3** | **GPIO 18** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Grid Board IN3 (**Verified**) |
| **Grid Relay — Load 4** | **GPIO 19** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Grid Board IN4 (**Verified**) |
| **Solar Relay — Load 1** | **GPIO 21** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Solar Board IN1 (**Verified**) |
| **Solar Relay — Load 2** | **GPIO 22** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Solar Board IN2 (**Verified**) |
| **Solar Relay — Load 3** | **GPIO 23** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Solar Board IN3 (**Verified**) |
| **Solar Relay — Load 4** | **GPIO 13** | `OUTPUT` | Active-LOW (LOW=ON, HIGH=OFF) | Solar Board IN4 (**Verified — Reassigned from GPIO 25**) |
| **Source Selector — Load 1** | **GPIO 26** | `INPUT_PULLDOWN` | 0V=GRID, 3.3V=SOLAR | 10kΩ pull-down to GND (**Verified**) |
| **Source Selector — Load 2** | **GPIO 27** | `INPUT_PULLDOWN` | 0V=GRID, 3.3V=SOLAR | 10kΩ pull-down to GND (**Verified**) |
| **Source Selector — Load 3** | **GPIO 32** | `INPUT_PULLDOWN` | 0V=GRID, 3.3V=SOLAR | 10kΩ pull-down to GND (**Verified**) |
| **Source Selector — Load 4** | **GPIO 33** | `INPUT_PULLDOWN` | 0V=GRID, 3.3V=SOLAR | 10kΩ pull-down to GND (**Verified**) |
| **ACS712 Current Sensor** | **GPIO 34** | `INPUT` (ADC1_6) | Analog (via 10k/15k divider) | Aggregate neutral return (**Pending Calibration**) |
| **ZMPT101B Voltage Sensor** | **GPIO 35** | `INPUT` (ADC1_7) | Analog (0–3.3V) | Aggregate AC mains transformer (**Pending Calibration**) |
| **Status LED** | **GPIO 2** | `OUTPUT` | Active-HIGH (3.3V = ON) | Onboard LED, Wi-Fi status indicator (**Verified**) |

---

## 6. Sensor Status, Remote Calibration & NVS Persistence

### A. DHT22 Temperature & Humidity Sensor (Verified):
- **Pin:** GPIO 4 (1-Wire bus, sampled every 2.5 seconds on Core 1).
- **Status:** **Verified on physical hardware.** Temperature and humidity readings are successfully received and displayed in the Serial Monitor, frontend dashboard, and telemetry payload.
- **Validity Handling:** `dht_valid` flag tracks sensor health. If a read returns `NAN`, the firmware reports `SENSOR ERROR` without fabricating default placeholder values.

### B. Remote Safe Calibration Architecture (ACS712 & ZMPT101B):
Calibration can be performed **remotely via the browser dashboard** or locally via Serial CLI. 

1. **Auto Zero-Offset Calibration (`CAL_ZERO`):**
   - When triggered, Core 1 checks if any relay is energized. If loads are active, it **automatically commands all loads to OFF (`relays.allOff()`)** and delays 400 ms to guarantee a true $I = 0.000\text{ A}$ no-load condition before taking the 3-second ADC sample burst.
   - Calculates quiescent DC bias for ZMPT101B ($V_{\text{zero}} \approx 2048$) and ACS712 ($I_{\text{zero}} \approx 1536$).
2. **Voltage Scaling Calibration (`SET_VCAL`):**
   - The user inputs the reference True-RMS voltage measured with a multimeter (e.g. $227.5\text{ V}$). The dashboard/firmware computes $K_V = \frac{V_{\text{multimeter}}}{V_{\text{raw\_rms\_swing}}}$ and sets the multiplier.
3. **ACS712 Physical Variant Configuration (`SET_SENS`):**
   - Allows selecting the physical variant rating:
     - **ACS712-05B:** $185\text{ mV/A}$ ($0.185\text{ V/A}$)
     - **ACS712-20A:** $100\text{ mV/A}$ ($0.100\text{ V/A}$)
     - **ACS712-30A:** $66\text{ mV/A}$ ($0.066\text{ V/A}$)
     - Or custom sensitivity for other Hall-effect variants.

### C. NVS Flash Persistence Behavior:
- **Namespace:** `"hems_cal"`
- **Persisted Keys:** `v_zero` (float), `i_zero` (float), `v_cal` (float), `i_sens` (float), `calibrated` (bool).
- **Reboot Behavior:** On boot, `ElectricityMeter::begin()` checks NVS flash. If calibrated, it automatically restores calibrated parameters and sets `cal_status = "CALIBRATED"`. If no NVS record exists, it loads safe default placeholders and marks `cal_status = "UNCALIBRATED"`.
- **Reset Command (`RESET_CAL`):** Clears the `"hems_cal"` NVS namespace and restores uncalibrated defaults.

---

## 7. Step-by-Step Bench Calibration Workflow (For Assembled Hardware)

Follow these 4 steps in order on the dashboard (`Live Operations -> Remote Sensor Calibration` panel):

| Step | Operation | Condition Required | Physical Action |
|---|---|---|---|
| **Step 1** | **`CAL_ZERO` (Zero-Offset)** | **No-Load Condition** ($I = 0\text{ A}$) | Click **"Run 3s Zero-Offset Calibration"**. The system automatically forces all 4 relays to `OFF`. The ESP32 measures the quiescent zero-current and zero-voltage bias levels for 3000 ms and persists them to NVS. |
| **Step 2** | **`SET_VCAL` (Voltage Scaling)** | **Live 230V Mains Reference** | Measure true AC mains voltage with a calibrated True-RMS Multimeter at the wall socket (e.g. $226.5\text{ V}$). Enter this value in the **Step 2** field and click **"Apply"**. The calibrated $K_V$ is saved to NVS. |
| **Step 3** | **`SET_SENS` (Sensor Variant)** | **Sensor Identification** | Check the silkscreen / part number on your physical ACS712 module (e.g. `ACS712ELCTR-20A-T`). Click the matching button (**5A**, **20A**, or **30A**), or enter custom $\text{V/A}$, and click **"Set"**. |
| **Step 4** | **Known-Load Verification** | **Known Reference Load** | Turn ON a single known appliance (e.g. 60W incandescent bulb or 500W heater) on Load 1. Enter the rated reference wattage in **Step 4**. The dashboard computes Error $\% = \frac{\|P_{\text{ESP32}} - P_{\text{Ref}}\|}{P_{\text{Ref}}} \times 100\%$. Verify that Error $< 10\%$. |

---

## 8. Summary of Verification Status

| Subsystem / Feature | Implementation Status | Physical Hardware Status |
|---|---|---|
| **FreeRTOS Dual-Core Decoupling** | Implemented (`firmware.ino`) | **VERIFIED** (Zero network latency on physical switch toggling) |
| **Grid Relays L1–L4 (GPIO 16, 17, 18, 19)** | Implemented (`relay_controller.cpp`) | **VERIFIED** (Physical switching confirmed) |
| **Solar Relays L1–L3 (GPIO 21, 22, 23)** | Implemented (`relay_controller.cpp`) | **VERIFIED** (Physical switching confirmed) |
| **Solar Relay L4 (GPIO 13)** | Implemented (`relay_controller.cpp`) | **VERIFIED** (Physical switching confirmed on GPIO 13) |
| **300 ms Break-Before-Make Dead-Time** | Implemented (`relay_controller.cpp`) | **VERIFIED** (Software delay enforced between relay states) |
| **Source Selectors L1–L4 (GPIO 26, 27, 32, 33)** | Implemented (`control_switches.cpp`) | **VERIFIED** (40 ms debounce, boot settling, immediate override) |
| **DHT22 Temperature & Humidity (GPIO 4)** | Implemented (`firmware.ino`) | **VERIFIED** (Live readings: $32.5^{\circ}\text{C}$, $83.4\%$ humidity) |
| **Wi-Fi HTTPS Cloudflare Tunnel & Dual-Core Ingest** | Implemented (`firmware.ino`) | **VERIFIED** (Reliable remote telemetry & status dispatch) |
| **NVS Flash Calibration Persistence** | Implemented (`electricity_meter.cpp`) | **VERIFIED** (Survives reboot, restored from `"hems_cal"`) |
| **Zero-Offset Calibration (Stage 1)** | Implemented (`CAL_ZERO`) | **VERIFIED** ($V_{\text{zero}} = 2539.65$, $I_{\text{zero}} = 2537.18$ counts) |
| **ZMPT101B True-RMS Voltage Calibration (Stage 2)** | Implemented (`SET_VCAL`) | **VERIFIED** ($K_V = 0.619060$, $V_{\text{RMS}} = 228.16\text{ V}$ vs $225\text{V}$ ref) |
| **ACS712 Current & Known-Load Calibration (Stage 3/4)** | Implemented (`SET_SENS`) | **PARTIALLY VERIFIED / PENDING PHYSICAL KNOWN-LOAD BENCH TEST** (System in `VOLTAGE_CALIBRATED` state) |

---

## 9. Serial CLI Commands for Local Verification

Open the Arduino Serial Monitor at **115200 baud**:

| Command | Action |
|---|---|
| `STATUS` / `READ` | Displays formatted table of all 4 loads (`selector_source`, `desired_source`, `applied_source`), raw/debounced selector GPIO levels, AC measurements, calibration state, and DHT22 readings. |
| `RELAY <1-4> <off|grid|solar>` | Simulates a remote backend command on Load 1–4. |
| `ALL_OFF` | Forces all loads to OFF immediately. |
| `CAL_ZERO` | Runs 3-second zero-offset calibration (auto-forces loads OFF). Persists to NVS. |
| `SET_VCAL <factor>` | Updates voltage calibration factor and persists to NVS. |
| `SET_SENS <volts/amp>` | Updates ACS712 current sensitivity and persists to NVS. |
| `RESET_CAL` | Clears calibration namespace in NVS flash and restores defaults. |
| `HELP` | Shows command menu. |

---

## 10. Wi-Fi Provisioning — SmartProv Integration

Wi-Fi credentials are managed at runtime by the [SmartProv](https://github.com/Masud744/SmartProv) captive-portal provisioning library (v2.1.3). No hardcoded credentials exist in source code.

**Boot-gate flow:** On each boot, SmartProv checks NVS (`"smartprov"` namespace) for stored credentials. If found, it connects in STA mode and proceeds to normal HEMS operation. If not found, it starts an AP named `HEMS_XXXX` with a captive portal for the user to enter Wi-Fi credentials, then reboots.

SmartProv is dynamically allocated in `setup()` and safely destroyed after connection to reclaim heap. It has no runtime footprint after boot.

**Compiler-verified integration report:** See [`docs/SMARTPROV_INTEGRATION_REPORT.md`](../docs/SMARTPROV_INTEGRATION_REPORT.md) for the full before/after flash and RAM comparison, safe destruction analysis, and subsystem compatibility verification.
