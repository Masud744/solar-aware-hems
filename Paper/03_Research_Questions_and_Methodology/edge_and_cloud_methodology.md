# Phase 3: Edge and Cloud Implementation Methodology

**Document ID:** `Paper/03_Research_Questions_and_Methodology/edge_and_cloud_methodology.md`  
**Phase:** Phase 3 — Research Questions, System Architecture & Mathematical Formulation  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 4, 5) and `firmware/` / `backend/`  

---

## 1. Overview of Edge-Cloud Cyber-Physical Integration

The Solar-Aware HEMS framework bridges embedded physical metrology and actuation with cloud-based machine learning intelligence, statistical risk calibration, and conversational explainability. This document provides the comprehensive engineering specification for the **ESP32 Edge Microcontroller Node** and the **FastAPI Cloud Backend**, detailing pinout configurations, FreeRTOS task concurrency, network synchronization, database security, and cyber-physical safety boundaries.

---

## 2. Embedded Edge Hardware Engineering (ESP32 DevKit V1)

### 2.1 Microcontroller Specifications & Pin Allocation
The edge computing platform is built around an **ESP32 DevKit V1** (30-pin variant) powered by a dual-core 32-bit Tensilica Xtensa LX6 microprocessor operating at a clock frequency of $240\text{ MHz}$ with $520\text{ KB}$ internal SRAM and $4\text{ MB}$ external SPI flash memory.

#### Complete Authoritative 30-Pin GPIO Pinout Table:
| Pin Function / Identifier | Physical GPIO | Hardware Interface | Circuit Connection & Conditioning | Operational Role / Subsystem |
| :--- | :---: | :--- | :--- | :--- |
| **Voltage Sensor (ZMPT101B)** | **GPIO 35** | ADC1_CH7 | Direct from active op-amp filter (1.65V DC bias) | Periodic AC mains voltage burst sampling (discrete sampled RMS) |
| **Current Sensor (ACS712-20A)**| **GPIO 34** | ADC1_CH6 | Passive divider: $R_1=10\text{k}\Omega, R_2=15\text{k}\Omega$ ($\alpha=0.600$) | Periodic load current burst sampling (discrete sampled RMS) |
| **Indoor Ambient Sensor (DHT22)**| **GPIO 4** | Digital (1-Wire) | $10\text{ k}\Omega$ pull-up resistor to 3.3V bus | Temperature and humidity telemetry |
| **Grid Relay 1 (Washer)** | **GPIO 16** | Digital Output | Active-LOW coil driver via optocoupler | Primary grid connection for Load Channel 1 |
| **Grid Relay 2 (Pump)** | **GPIO 17** | Digital Output | Active-LOW coil driver via optocoupler | Primary grid connection for Load Channel 2 |
| **Grid Relay 3 (Fridge)** | **GPIO 18** | Digital Output | Active-LOW coil driver via optocoupler | Primary grid connection for Load Channel 3 |
| **Grid Relay 4 (Cooker)** | **GPIO 19** | Digital Output | Active-LOW coil driver via optocoupler | Primary grid connection for Load Channel 4 |
| **Solar Relay 1 (Washer)** | **GPIO 21** | Digital Output | Active-LOW coil driver via optocoupler | Auxiliary solar connection for Load Channel 1 |
| **Solar Relay 2 (Pump)** | **GPIO 22** | Digital Output | Active-LOW coil driver via optocoupler | Auxiliary solar connection for Load Channel 2 |
| **Solar Relay 3 (Fridge)** | **GPIO 23** | Digital Output | Active-LOW coil driver via optocoupler | Auxiliary solar connection for Load Channel 3 |
| **Solar Relay 4 (Cooker)** | **GPIO 13** | Digital Output | Active-LOW coil driver via optocoupler | Auxiliary solar connection for Load Channel 4 |
| **Manual Selector Switch 1** | **GPIO 25** | Digital Input | Internal pull-up; external SPDT toggle | Manual source override for Load Channel 1 |
| **Manual Selector Switch 2** | **GPIO 26** | Digital Input | Internal pull-up; external SPDT toggle | Manual source override for Load Channel 2 |
| **Manual Selector Switch 3** | **GPIO 27** | Digital Input | Internal pull-up; external SPDT toggle | Manual source override for Load Channel 3 |
| **Manual Selector Switch 4** | **GPIO 14** | Digital Input | Internal pull-up; external SPDT toggle | Manual source override for Load Channel 4 |
| **Status Indicator LED** | **GPIO 2** | Digital Output | Onboard blue LED with current-limiting resistor | Visual heartbeat and Wi-Fi provisioning status |
| **SmartProv Factory Reset** | **GPIO 0** | Digital Input | BOOT button (active-LOW) with debounce | Hold 3s to wipe Wi-Fi NVS credentials |

*ADC Subsystem Isolation Note:* All analog sensing is strictly restricted to **ADC1** channels (GPIO 34 and 35). ADC2 channels are permanently avoided because the internal ESP32 Wi-Fi radio driver commandeers ADC2, causing runtime hardware conflicts and corrupting analog readings during active RF transmission.

---

## 3. FreeRTOS Dual-Core Concurrency & Task Partitioning

To resolve [Gap 5](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-5-hardware-task-concurrency-contention-in-single-threaded-polling-loops) (Hardware Task Concurrency Contention), firmware execution is structurally decoupled across the two physical processing cores under FreeRTOS:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ESP32 DUAL-CORE FREERTOS TASK PARTITIONING                  │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ CORE 1: METROLOGY & CONTROL          │ CORE 0: ASYNCHRONOUS TELEMETRY & COMMS│
│ • Execution: loop() at Priority 1    │ • Execution: networkTask at Pri 1    │
│ • Period: Non-blocking Control Loop  │ • Period: Asynchronous Network Task  │
│ • Tasks:                             │ • Tasks:                             │
│   1. 200 ms Sampled RMS Burst (1000ms│   1. Wi-Fi Station Reconnection Loop │
│   2. 40 ms Switch Debounce Logic     │   2. HTTP POST Ingest (3000 ms)      │
│   3. 300 ms BBM Relay Transfer Delay │   3. HTTP GET Status Poll (1500 ms)  │
│   4. Local Relay State Machine Mgmt  │   4. SmartProv SoftAP Portal Server  │
├──────────────────────────────────────┴──────────────────────────────────────┤
│ THREAD-SAFE SYNCHRONIZATION:                                                │
│ • remoteCommandQueue (FreeRTOS Queue, depth 16, items: RemoteCommand)       │
│ • telemetryMutex (FreeRTOS Binary Mutex protecting shared snapshot memory)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Core 1: Real-Time Metrology and Control Loop
- **Analog Acquisition:** Executes discrete sampled RMS burst estimation across GPIO 35 (voltage) and GPIO 34 (current) over a $200\text{ ms}$ sampling window ($10$ full $50\text{ Hz}$ AC cycles, $M \approx 300\text{--}400$ samples, burst sampled at $1.5\text{--}2.0\text{ kHz}$) periodically every 1000 ms or upon relay state changes.
- **Switch Polling:** Polls the four manual selector toggle switches (GPIO 25, 26, 27, 14) with a software debouncing window of $40\text{ ms}$. If a physical switch transition is confirmed, Core 1 overrides the cloud schedule and asserts local control.
- **Relay State Sequencing:** Enforces single-owner relay transitions. When switching a channel between Grid and Solar sources, Core 1 commands the active relay OFF, pauses via a blocking `delay(300)` call, and energizes the target relay ON.

### 3.2 Core 0: Asynchronous Telemetry & Network Communication
- **Wi-Fi Connectivity:** Manages station connection, tracking RSSI and handling reconnect exponential backoffs.
- **Telemetry Ingestion Push:** Serializes the latest thread-safe metrology snapshot and sends an HTTP POST request to `/ingest` every **3000 ms** (`INGEST_INTERVAL_MS = 3000`, $4000\text{ ms}$ socket timeout).
- **Command Polling:** Sends an HTTP GET request to `/api/device/status` every **1500 ms** (`POLL_INTERVAL_MS = 1500`) to retrieve pending cloud relay commands.
- **SmartProv Captive Portal:** If credentials are lost or the BOOT button (GPIO 0) is held for 3 seconds, Core 0 launches a local Wi-Fi Access Point (`HEMS_XXXX`) with a captive portal, allowing users to enter new SSID and password credentials that are persisted in NVS flash namespace `"smartprov"`.

### 3.3 Thread-Safe Inter-Core Synchronization Primitives
1. **Remote Command Dispatch Queue (`remoteCommandQueue`):** Core 0 pushes incoming HTTP commands into a FreeRTOS queue (`depth = 16`, type `RemoteCommand`). Core 1 drains this queue using non-blocking `xQueueReceive(remoteCommandQueue, &cmd, 0)` calls, guaranteeing zero stalls.
2. **Telemetry Mutex (`telemetryMutex`):** A binary mutex (`xSemaphoreCreateMutex()`) protects the shared memory structure `TelemetrySnapshot`. Core 1 acquires the mutex to update calculated RMS values; Core 0 acquires it briefly with a 20 ms timeout to copy data for JSON serialization.

---

## 4. Cloud Backend Microservices Architecture (FastAPI)

The middleware tier is implemented using **FastAPI** running under an asynchronous ASGI `uvicorn` architecture on Python 3.10.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FASTAPI ASYNCHRONOUS BACKEND ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. INGESTION SERVICE (POST /ingest)                                         │
│    • Ingests 3s edge telemetry (Vrms, Irms, Pactive, Eaccum, RelayStates)   │
│    • Enforces 15s application-level state-reconciliation holdoff            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. STATUS POLLING SERVICE (GET /api/device/status)                          │
│    • Polled by ESP32 Core 0 every 1500 ms                                   │
│    • Returns pending target relay states and calibration constant updates   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. DECISION & RISK SERVICE (POST /risk)                                     │
│    • Queries condition-bucketed heteroskedastic standard deviations         │
│    • Computes Conservative Net Safe Surplus S_safe(t) in O(1) complexity    │
│    • Evaluates instantaneous & duration-aware admission (Algorithm 1)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. UPSTREAM RESILIENCE & CACHING ENGINE                                     │
│    • In-memory cache for Open-Meteo weather reanalysis forecasts            │
│    • Negative TTL caching on 429/503 errors preventing polling storms       │
│    • Exponential backoff cooldown governed by upstream Retry-After headers  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. EXPLAINABILITY SERVICE (POST /xai/explain)                               │
│    • Layer 1: Evaluates TreeSHAP exact feature attributions (<10⁻⁶ kW error) │
│    • Layer 2: Rule-based natural language causal translation                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 6. SOLARMATE CONVERSATIONAL AI (POST /chat)                                 │
│    • Powered by Groq Llama-3.3-70B API service                              │
│    • Structured JSON tool-calling: get_live_telemetry, get_hourly_forecasts │
│    • Strict read-only advisory safety gate (zero relay actuation authority) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Weather Caching, Cooldown & Upstream Resilience
To prevent external API failures from crashing real-time decision loops:
1. **Positive and Negative TTL Caching:** Successful Open-Meteo weather forecasts are cached for 60 minutes. If the external API responds with HTTP 429 (Rate Limited) or HTTP 503 (Service Unavailable), the backend sets a **negative TTL marker** (5–15 minutes). Subsequent inference queries read the valid cached historical forecast rather than attempting redundant network calls.
2. **Upstream Cooldown Engine:** An automatic cooldown state machine parses upstream `Retry-After` headers. During cooldown, external polling is completely suspended, protecting system stability and preventing upstream IP bans.

---

## 5. Cloud Database Schema and Application-Level State-Reconciliation Holdoff

Persistent storage is hosted on **Supabase Cloud PostgreSQL** featuring Row-Level Security (RLS) and schema-level security triggers:

### 5.1 Primary Relational Tables Schema
1. `sensor_readings`: Stores time-series edge telemetry ($V_{\text{RMS}}, I_{\text{RMS}}, P_{\text{active}}$, accumulated energy, ambient temperature, humidity, zero offsets).
2. `device_controls`: Tracks current and target states for all 8 relay coils, source selector switch states, and application-level state-reconciliation holdoff timestamps.
3. `solar_predictions`: Stores 24-hour hourly solar forecasts with condition-bucketed $\sigma_{\text{solar}}$ values.
4. `load_predictions`: Stores 24-hour hourly load forecasts with diurnal-bucketed $\sigma_{\text{load}}$ values.
5. `device_requests`: Full audit log of all appliance admission requests, recorded Safe Surplus values, deficit margins, and refusal causality.
6. `profiles`: Manages user credentials, contact details, and role-based permissions (`admin` vs `user`).
7. `chat_messages`: Stores private conversational interactions with SolarMate AI, isolated per user via RLS tied to `auth.users(id)`.

### 5.2 Application-Level State-Reconciliation Holdoff (15-Second Window)
When a user toggles an appliance state on the React web dashboard, network transit latencies introduce race conditions where stale incoming ESP32 telemetry could overwrite the user's intent. To prevent this:
- The dashboard command updates `device_controls` with target relay states and registers an application-level state-reconciliation holdoff timestamp (`NOW() + INTERVAL '15 seconds'`).
- The `/ingest` service checks this holdoff: if the incoming telemetry timestamp is older than the active holdoff window, the telemetry relay state is accepted for logging but discarded from active control state, preserving user intent during the edge round trip.

### 5.3 Quarantine-by-Default Access Control Lifecycle
To secure high-voltage switching equipment against unauthorized access:
- Self-registered users are assigned `status = 'pending'` by default.
- While pending, all requests to actuate relays or update appliance parameters are rejected with **HTTP 403 (Forbidden)**.
- An administrator must manually approve the account via the `/admin` portal.
- A PostgreSQL security trigger (`protect_profile_privileges`) prevents non-admin users from escalating roles via direct SQL injection or API spoofing.

---

## 6. SolarMate Conversational AI Safety Architecture

To provide an intuitive natural-language interface without compromising cyber-physical safety, **SolarMate AI** is designed with a strict **read-only advisory architecture**:

```
                              [ User Chat Query ]
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   SolarMate AI Service    │
                        │   (Groq Llama-3.3-70B)    │
                        └─────────────┬─────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
    [ Structured Tool Call ]                        [ Actuation Attempt ]
    Allowed Read-Only Tools:                        "Turn ON the washing machine"
    • get_live_telemetry                                      │
    • get_hourly_forecasts                                    ▼
    • get_schedule_recommendation                   [ HARDWARE SAFETY GATE ]
    • get_appliance_safety_allow                     Actuation Endpoints EXCLUDED
              │                                     from LLM Tool Schema
              ▼                                               │
    FastAPI Read-Only DB Introspect                           ▼
              │                                     [ REFUSAL RESPONSE ]
              ▼                                     "I can analyze power margins,
    Plain-Language Guidance                         but I cannot toggle relays.
    with Deficit & Deferral Time                    Please use the physical switch."
```

### 6.1 Tool-Calling Schema Boundaries
SolarMate AI interfaces with backend intelligence strictly through declarative JSON function schemas:
- `get_live_telemetry`: Inspects current RMS voltage, current, active power, and current power source.
- `get_hourly_forecasts`: Queries 24-hour lookahead curves for solar generation, baseload demand, and Safe Surplus.
- `get_schedule_recommendation`: Queries the duration-aware search engine to find the optimal start hour $t^*$ for a requested appliance.

### 6.2 Exclusion of Actuation Endpoints
The LLM tool schema **strictly excludes all relay toggle and actuation endpoints**. The conversational agent possesses zero write authority to the database and zero communication channels to the ESP32. If a user asks the assistant to toggle an appliance, the model generates a polite refusal and directs the user to the manual dashboard toggle switch.

---

## 7. Explicit Academic Disclosure of the 8 Project Boundaries

To ensure complete transparency and intellectual honesty across future manuscript phases, the system methodology adheres to the **Eight Authoritative Project Boundaries**:

| # | Project Boundary | Empirical System Reality | Mandatory Academic Disclosure Statement |
| :-: | :--- | :--- | :--- |
| **1** | **Synthetic Cross-Regional Evaluation** | Evaluates UCI load (Sceaux, France) paired with Open-Meteo solar (Kaliakair, Bangladesh) across 176 common scenarios. | Explicitly disclosed as an academic evaluation testbed; not presented as a single geographically co-located household measurement. |
| **2** | **Reanalysis vs. Operational NWP** | Offline solar models trained on historical ERA5-Land reanalysis data. | Disclosed that reanalysis irradiance exhibits lower transient volatility than live operational NWP; empirical $\sigma_{\text{solar}}$ represents a lower-bound error estimate. |
| **3** | **Single-Point Voltage Calibration** | ZMPT101B calibrated at $225.00\text{ V}$ ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual). | Characterized as a system-level board calibration coefficient integrating transformer ratio, op-amp gain, and ESP32 ADC transfer function; not a universal sensor constant. |
| **4** | **Nominal ACS712-20A Current Sensitivity** | ACS712-20A operates under nominal datasheet sensitivity ($0.100\text{ V/A}$). | Disclosed that current sensing relies on nominal datasheet ratings without independent multi-point calibration against laboratory shunt standards across operational span. |
| **5** | **Software 300 ms Delay vs. Hardware Interlock** | Firmware enforces a software blocking delay (`delay(300)`) between relay bank toggles. | Explicitly disclosed as an implementation software delay mitigating routine contact arcing; not a certified fail-safe hardware mechanical interlock circuit. |
| **6** | **Decision Engine Execution Location** | Safe Surplus algorithm and 24-hour scheduling engine execute in the FastAPI backend. | Disclosed that the decision engine currently executes in the cloud/local backend; not on the ESP32 microcontroller (though structurally compatible with future C++ porting). |
| **7** | **Rule-Based Algebraic Logic vs. Dynamic Solvers**| Algebraic threshold inequality ($S_{\text{safe}} \ge P_{\text{device}}$) with $O(1)$ algorithmic complexity. | Disclosed that the system eliminates solver licenses but does not guarantee Pareto-optimal cost minimization under dynamic multi-tier ToU tariffs or battery degradation models. |
| **8** | **Financial Accounting Scope** | Savings computed from gross self-consumption at flat tier-3 rate ($7.50\text{ BDT/kWh}$). | Disclosed that financial accounting assumes zero export credit (no net-metering feed-in tariffs) and models no battery capital depreciation or inverter levelized costs. |

---

## 8. Section Summary

This engineering specification establishes the cyber-physical realization of Solar-Aware HEMS:
1. Dual-core FreeRTOS task partitioning isolating periodic sampled RMS metrology on Core 1 from 3000 ms Wi-Fi telemetry on Core 0.
2. Complete 30-pin GPIO allocation utilizing ADC1 channels exclusively.
3. Resilient FastAPI middleware with negative TTL caching and exponential backoff cooldown.
4. Supabase PostgreSQL persistence with 15-second application-level state-reconciliation holdoff and quarantine-by-default RBAC.
5. Strict read-only advisory architecture for SolarMate AI.
6. Transparent academic disclosure of all 8 project boundaries.

The complete mathematical proofs and formalisms governing predictive modeling, TreeSHAP explainability, and Safe Surplus decision logic are detailed in [`mathematical_formulation.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/03_Research_Questions_and_Methodology/mathematical_formulation.md).
