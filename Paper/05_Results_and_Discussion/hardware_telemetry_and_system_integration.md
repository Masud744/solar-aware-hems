# Physical Hardware Implementation, Edge Telemetry, and Full-Stack Integration Verification

**Document ID:** `Paper/05_Results_and_Discussion/hardware_telemetry_and_system_integration.md`  
**Phase:** Phase 5 — Results and Discussion  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Executive Overview and Cyber-Physical Integration

A major deficiency identified in residential energy management literature is the disconnect between theoretical machine learning formulations and practical cyber-physical implementation. Algorithms validated solely in simulation often fail when deployed on embedded hardware subject to analog sensor noise, ADC quantization non-linearities, task scheduling contention, and network latency.

To bridge this gap, the Solar-Aware HEMS framework unites its risk-aware forecasting models with a physical embedded edge computing node, an 8-channel electromechanical transfer-switching matrix, and a database-backed cloud platform. This document reports the empirical verification of the physical hardware metrology, FreeRTOS dual-core task concurrency, software-enforced transfer switching, automated multi-level test suite, and cloud telemetry integration.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   CYBER-PHYSICAL SYSTEM VERIFICATION ARCHITECTURE                      │
├───────────────────────────────────────────────────┬────────────────────────────────────┤
│ 1. Physical Edge Metrology (ESP32 DevKit V1)      │ 2. Dual-Core Task Concurrency      │
│ • Quiescent DC Zero Offsets:                      │ • Core 1: loopTask (Priority 1)    │
│   V_zero = 2539.65, I_zero = 2537.18 counts       │   200 ms burst @ 1.5–2.0 kHz       │
│ • Voltage Gain Factor: K_V = 0.619060 V/count     │   40 ms switch debounce            │
│   (1.40% calibration residual vs. 225.0V DMM)     │   Single-task relay ownership      │
│ • Nominal Current Sensitivity: 0.100 V/A          │ • Core 0: networkTask (Priority 1) │
│ • Current Quantization: 13.43 mA/count, 50 mA cut │   1500 ms poll, 3000 ms push       │
│ • Reference Load Validation: Walton 60W Fan       │ • Thread Safety: Queue depth 16,   │
│   V ≈ 226 V, I ≈ 0.28 A, S = 63.28 VA             │   binary mutex, NVS "hems_cal"     │
├───────────────────────────────────────────────────┼────────────────────────────────────┤
│ 3. Transfer Switching & Relay Protection          │ 4. Cloud Platform & Test Suite     │
│ • Dual-bank 8-relay matrix (4 Grid, 4 Solar)      │ • 68/68 automated tests passing    │
│ • Software BBM Delay: 300 ms dead-time on Core 1  │   (64 backend + 4 firmware math)   │
│ • Anti-Chattering: 180 s dwell-time, ±50 W hyst   │ • 15 s state-reconciliation holdoff│
│ • Bounded Disclosure: Software sequence, not ATS  │ • 5,244 live packets (0.3329 kWh)  │
└───────────────────────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Automated Multi-Level Test Suite Verification

### 2.1 Complete Repository Test Corpus
To ensure algorithmic correctness, data integrity, and operational safety before hardware commissioning, the full repository software stack was evaluated under an automated regression test suite executed via Pytest. 

The test suite achieves a **100.0% pass rate** across all **68 collected test cases** with an execution time of **3.84 seconds**:
- **Backend Application Software Suite:** 64 tests collected across 7 test files (`backend/tests/`);
- **Firmware Mathematical Simulation Suite:** 4 unit tests collected in `firmware/tests/test_firmware_math.py`.

Table 1 details the file-wise test collection, functional role, and execution status.

### Table 1: File-Wise Automated Regression Test Suite Breakdown ($N_{\text{total}} = 68$)

| # | Test File Path | Subsystem / Component Under Test | Collected Tests | Pass Rate | Execution Time |
| :-: | :--- | :--- | :---: | :---: | :---: |
| 1 | `backend/tests/test_assistant_chat.py` | SolarMate AI Chat Safety, Read-Only Boundary, Tool Schemas | **7** | 100% (7/7) | ~0.85s |
| 2 | `backend/tests/test_auth_and_admin.py` | JWT Auth, Pending User Gating, Admin Role & User Isolation | **6** | 100% (6/6) | ~0.45s |
| 3 | `backend/tests/test_decision_engine.py` | Worked Example, Boundary Conditions, Sigma Buckets, Stale-Gating | **17** | 100% (17/17) | ~0.55s |
| 4 | `backend/tests/test_energy_accounting.py` | Trapezoidal Integration, Gap Protection, Calendar Bounds, Dhaka Time | **8** | 100% (8/8) | ~0.40s |
| 5 | `backend/tests/test_firmware_v2_endpoints.py` | Ingest Telemetry, Status Poll, Relay Control, Calibration Endpoint | **5** | 100% (5/5) | ~0.35s |
| 6 | `backend/tests/test_state_synchronization.py` | Command Freshness, Race Prevention, Physical Selector Reconciliation | **3** | 100% (3/3) | ~0.25s |
| 7 | `backend/tests/test_weather_cache_and_resilience.py` | Upstream 429 Resilience, Negative TTL, Stale-Serving, Cooldown Timers | **18** | 100% (18/18) | ~0.90s |
| — | **Subtotal: Backend Software Suite** | **Full Backend Application Layer** | **64** | **100% (64/64)** | **~3.75s** |
| 8 | `firmware/tests/test_firmware_math.py` | Discrete True-RMS Math, Inductive Lag, Divider Safety, Sample Count | **4** | 100% (4/4) | ~0.09s |
| **TOTAL** | **Full Repository Test Suite** | **Integrated Software and Firmware Math Verification** | **68** | **100% (68/68)** | **3.84s** |

### 2.2 Category-Wise Functional Coverage and Arithmetic Reconciliation
The automated test suite exercises 8 distinct functional categories across the cyber-physical stack:

1. **SolarMate Advisory AI Chat Safety (7 tests):** Enforces strict read-only tool access (live telemetry and relay status queries), valid natural-language causal reasoning, and hardware safety isolation by explicitly verifying that physical relay actuation commands are excluded from the conversational AI schema.
2. **Authentication, Role-Based Access Control, and Isolation (6 tests):** Verifies registration quarantine-by-default, HTTP 403 Forbidden blocks on unapproved pending accounts, JWT token expiration, administrative approval workflows, and per-user chat history database isolation.
3. **Safe Surplus Decision Engine and Risk Gating (17 tests):** Validates the Section 8.3 worked mathematical derivation ($S_{\text{safe}} = -0.47\text{ kW}$, resulting in an unambiguous DENY), exact boundary conditions ($S_{\text{safe}} = P_{\text{device}}$), negative surplus fail-safe behavior, heteroskedastic sigma lookups across all cloud-cover and diurnal bins, and stale-forecast rejection.
4. **Energy Accounting and Self-Consumption Integration (8 tests):** Tests numerical trapezoidal energy integration, a 15-minute gap threshold that disallows energy accumulation across telemetry dropouts, calendar boundary clamping, and conservative solar self-consumption formulas.
5. **Firmware v2 IoT Ingestion Endpoints (5 tests):** Validates the `/ingest` telemetry pipeline, `/api/device/status` polling response formatting, manual relay override validation, and NVS calibration constant ingestion.
6. **State Synchronization and Switch Arbitration (3 tests):** Verifies timestamp-based command freshness, prevention of race conditions between web toggles and incoming telemetry, and physical SPDT switch override reconciliation.
7. **Weather Caching and Upstream Resilience (18 tests):** Evaluates API admission policies under stale, fresh, and unavailable forecast states (7 tests); tests graceful handling of upstream HTTP 429 Too Many Requests, exponential backoff cooldowns, Retry-After header parsing, negative TTL caching, concurrency request coalescing, and in-memory cache failover (11 tests).
8. **Firmware Discrete Mathematics and Front-End Safety (4 tests):** Tests discrete sampled RMS active power integration under unity power factor, inductive phase-lag apparent versus real power computation, passive $10\text{ k}\Omega / 15\text{ k}\Omega$ resistor divider voltage stepping ($V_{\text{pin}} \le 3.00\text{ V} \le 3.30\text{ V}$), and a discrete 2,000-sample count across 10 AC cycles.

*Arithmetic Reconciliation:* An earlier draft summary displayed category counts summing to 54 ($2 + 17 + 8 + 5 + 3 + 19 = 54$). This was traced to an omission of the 7 SolarMate safety tests, a truncation of the 6 auth tests to 2, and an off-by-one labeling of weather resilience ($18 \to 19$). The audited breakdown of 64 backend tests and 4 firmware simulation tests sums precisely to 68 items.

---

## 3. Physical Metrology Calibration and Empirical Bench Validation

### 3.1 Multi-Stage Calibration State Machine
Due to manufacturing tolerances in passive component networks and sensor transducers, empirical calibration is mandatory. A 4-stage calibration protocol was executed on the physical ESP32 edge testbed, with results summarized in Table 2.

### Table 2: Physical Edge Metrology Calibration and Bench Validation Summary

| Stage | Calibration Procedure | Reference Instrument / Load | Calibrated Parameter / Empirical Value | Verification Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Quiescent Zero-Offset (`CAL_ZERO`) | All relays OFF ($I = 0\text{ A}$), 400 ms settle | $V_{\text{zero}} = 2539.65, I_{\text{zero}} = 2537.18\text{ counts}$ | **[MEASURED ON HARDWARE]** |
| **2** | Voltage Scale Factor (`SET_VCAL`) | Fluke DMM reference ($V_{\text{ref}} = 225.00\text{ V}$) | $K_V = 0.619060\text{ V/count}$ ($1.40\%$ residual) | **[CALIBRATED AGAINST DMM]** |
| **3** | Current Sensitivity (`SET_SENS`) | Manufacturer datasheet specification | $S_{\text{nom}} = 0.100\text{ V/A}$ ($100\text{ mV/A}$) | **[NOMINAL SENSITIVITY]** |
| **4** | Known-Load Bench Validation | Walton WTF9M3 Fan ($60\text{ W rated}$) | $V \approx 226\text{ V}, I \approx 0.28\text{ A}, S = 63.28\text{ VA}$ | **[BENCH LOAD OBSERVED]** |

### 3.2 Stage 1: Quiescent DC Zero-Offset Acquisition
With all 8 relay channels de-energized ($I_{\text{actual}} = 0.00\text{ A}$) and a 400 ms settling period to eliminate contact transients, Core 1 executed a $3000\text{ ms}$ high-resolution acquisition burst collecting 2,840 raw ADC sample pairs across ADC1_CH7 (GPIO 35) and ADC1_CH6 (GPIO 34).

The empirical quiescent mid-point biases were computed as:
$$V_{\text{zero}} = \mathbf{2539.65\text{ counts}} \quad (2.046\text{ V DC at MCU pin})$$
$$I_{\text{zero}} = \mathbf{2537.18\text{ counts}} \quad (2.044\text{ V DC at MCU pin})$$

These values account for operational amplifier DC offset, resistor network tolerances, and the internal ESP32 ADC reference shift. Both offsets were permanently committed to ESP32 Non-Volatile Storage (NVS) flash under the namespace `"hems_cal"`.

### 3.3 Stage 2: AC Voltage Scaling Calibration and Residual Error Benchmarking
The AC voltage front-end (ZMPT101B potential transformer module) converts high-voltage mains into a scaled sinusoidal AC waveform centered at $V_{\text{zero}}$. 

1. **Reference Instrument:** A calibrated bench Digital Multimeter (DMM) measured steady-state AC mains terminal voltage during the calibration session:
   $$V_{\text{ref, cal}} = \mathbf{225.00\text{ V AC RMS}}$$
2. **Discrete Count Swing:** Across a $200\text{ ms}$ sampling burst (10 full $50\text{ Hz}$ cycles, $M \approx 300\text{--}400$ synchronized sample pairs), the raw unrounded ADC RMS swing was recorded as:
   $$\text{ADC}_{\text{RMS\_swing}} = \frac{V_{\text{measured, raw}}}{K_{V\text{, test}}} = \frac{284.08388\text{ V}}{0.781622\text{ V/count}} = \mathbf{363.45427\text{ counts RMS}}$$
3. **Calibrated Scaling Coefficient:** The system-level voltage calibration coefficient $K_V$ was computed as:
   $$K_V = \frac{V_{\text{ref, cal}}}{\text{ADC}_{\text{RMS\_swing}}} = \frac{225.00000\text{ V}}{363.45427\text{ counts}} = \mathbf{0.619060\text{ V/count}}$$
   This coefficient was committed to NVS flash (`preferences.putFloat("v_cal", 0.619060)`).
4. **Live Telemetry Residual Analysis:** During subsequent live verification, the edge node recorded an RMS terminal voltage of $V_{\text{ESP32, live}} = 228.16\text{ V AC RMS}$ (persisted in Supabase row #836). This establishes:
   - **Calibration Residual Offset:**
     $$\Delta V_{\text{cal}} = \frac{|228.16\text{ V} - 225.00\text{ V}|}{225.00\text{ V}} \times 100\% = \mathbf{1.40\%}$$
   - **Cross-Session Observational Delta:** Relative to an independent bench check observing $V_{\text{DMM}} \approx 226.00\text{ V}$, the observational deviation is $0.96\%$.
5. **Academic Metrology Characterization:** $K_V = 0.619060\text{ V/count}$ represents a **single-point bench calibration coefficient** capturing op-amp gain and resistor divider tolerances. It is explicitly characterized as an empirical calibration residual rather than an independently certified full-range metrological accuracy rating across thermal drift and grid harmonic distortion.

### 3.4 Stage 3: Current Sensitivity and Quantization Floor
The current measurement subsystem utilizes an Allegro ACS712-20A Hall-effect sensor connected to ADC1_CH6 through a passive $10\text{ k}\Omega / 15\text{ k}\Omega$ resistive divider ($\alpha = 0.600$).

1. **Nominal Sensitivity Parameterization:** In accordance with the manufacturer datasheet, current sensitivity was configured to $S_{\text{nom}} = 0.100\text{ V/A}$ ($100\text{ mV/A}$).
2. **Theoretical Nominal Quantization Resolution:**
   $$\Delta I_{\text{step}} = \frac{V_{\text{ADC\_REF}} / 4096}{S_{\text{nom}} \times \alpha} = \frac{3.300\text{ V} / 4096}{0.100\text{ V/A} \times 0.600} \approx \mathbf{0.01343\text{ A/count}} \quad (13.43\text{ mA/count})$$
3. **Software Noise Cutoff Threshold:** Due to thermal noise in the Hall-effect transducer and ADC non-linearities at low input amplitudes, sub-ampere readings can introduce spurious non-zero power integration during idle periods. The firmware implements a software-enforced noise floor:
   $$I_{\text{noise\_cutoff}} = \mathbf{50\text{ mA}} \quad (0.050\text{ A})$$
   Measured current values satisfying $I_{\text{RMS}} < 50\text{ mA}$ are clamped strictly to $0.00\text{ A}$ and $0.00\text{ W}$, preventing phantom energy accumulation.
4. **Metrological Boundary Disclosure:** ACS712 current sensing relies strictly on datasheet nominal sensitivity. No independent multi-point calibration curve against a precision reference current source was conducted across the 0–20A operational span.

### 3.5 Stage 4: Physical Reference Load Bench Observation
Physical electrical operation was verified using a domestic inductive reference appliance—a Walton WTF9M3 electric table fan rated at $60\text{ W}$ nameplate power connected to Load Channel 1 (GPIO 16).

Discrete RMS AC waveform sampling over a $200\text{ ms}$ window (10 full $50\text{ Hz}$ cycles at $1.5\text{--}2.0\text{ kHz}$) on Core 1 recorded:
$$V_{\text{RMS}} \approx 226.00\text{ V AC}, \quad I_{\text{RMS}} \approx 0.28\text{ A AC}$$
$$S_{\text{apparent}} = V_{\text{RMS}} \times I_{\text{RMS}} = 226.00\text{ V} \times 0.28\text{ A} = \mathbf{63.28\text{ VA}}$$

- **Quantization Context:** Measuring $0.28\text{ A}$ on a 20A sensor with $13.43\text{ mA/count}$ corresponds to an excursion of approximately $\pm 29.5\text{ ADC counts}$ around $I_{\text{zero}}$. While comfortably above the $50\text{ mA}$ cutoff ($\approx 3.7\text{ counts}$), sub-ampere loads operate in a coarsely quantized regime.
- **Instrument Limitation:** The $0.28\text{ A}$ current reading represents an uncalibrated firmware telemetry observation. True active power ($P$) and power factor ($\cos\theta$) were unmeasured on the bench due to the lack of dedicated phase-angle instrumentation.

---

## 4. FreeRTOS Dual-Core Concurrency and Transfer-Switching Verification

### 4.1 Dual-Core Workload Separation
To prevent network communication blocking from injecting jitter into high-frequency AC cycle sampling, task execution is partitioned across physical cores under FreeRTOS:

```
                  ESP32 XTENSA DUAL-CORE CONCURRENCY
  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
  │     CORE 1 (loopTask, Pri 1)    │   │   CORE 0 (networkTask, Pri 1)   │
  │ • AC Sampling: 200 ms burst     │   │ • HTTP Polling: /device/status  │
  │   1.5–2.0 kHz (300–400 samples) │   │   Interval: 1500 ms             │
  │ • Periodic Cadence: 1000 ms     │   │ • HTTP Ingestion: POST /ingest  │
  │ • Switch Debounce: 40 ms filter │   │   Interval: 3000 ms             │
  │ • Exclusive Relay Write Access  │   │ • SmartProv SoftAP & Captive    │
  │ • Enforces delay(300) on BBM    │   │ • Manages Wi-Fi Reconnect FSM   │
  └────────────────┬────────────────┘   └────────────────┬────────────────┘
                   │                                     │
                   ▼                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │        Thread-Safe Inter-Core Primitives               │
        │ • QueueHandle_t remoteCommandQueue (Depth = 16)        │
        │ • SemaphoreHandle_t telemetryMutex (Binary Mutex)      │
        │ • Dedicated ADC1 Pins (GPIO 34, 35) Avoid ADC2/Wi-Fi   │
        └────────────────────────────────────────────────────────┘
```

1. **Core 1 Execution (`loopTask`):** Executes metrology sampling, SPDT manual switch debouncing ($40\text{ ms}$), and relay switching. Dedicated allocation to ADC1 channels (GPIO 34, 35) avoids the silicon-level conflict with the Wi-Fi baseband on ADC2.
2. **Core 0 Execution (`networkTask`):** Manages outbound JSON telemetry streaming to `/ingest` ($3000\text{ ms}$ cadence) and inbound cloud command polling from `/api/device/status` ($1500\text{ ms}$ cadence).
3. **Inter-Core Synchronization:** Thread-safe communication is enforced via a FreeRTOS command queue (`remoteCommandQueue`, depth 16) and a binary mutex (`telemetryMutex`), preventing read-after-write tearing during JSON serialization.
4. **Workload Separation Boundary:** As established in Phase 4, dual-core task pinning separates application workload execution, but does not guarantee complete system-level isolation under hardware DMA or shared bus memory contention.

### 4.2 Software Break-Before-Make (BBM) Relay Switching
The physical testbed employs an 8-channel relay board configured as two independent 4-channel banks:
- **Grid Bank (Relays 1–4):** GPIO 16, 17, 18, 19 switching $230\text{ V}$ utility grid power;
- **Solar Bank (Relays 5–8):** GPIO 21, 22, 23, 13 switching local solar inverter output.

Simultaneous conduction of both relays on a single load channel connects two unsynchronized AC sources, resulting in a severe dead short-circuit. To guarantee non-overlapping conduction, the firmware executes a software-enforced **Break-Before-Make (BBM)** transfer sequence on Core 1:

```
  Transfer Load Channel i: Grid Source ───> Solar Source
  ─────────────────────────────────────────────────────────────────────────────
  Step 1: De-energize active Grid relay coil (Relay_Grid -> OFF)
          GPIO write: HIGH (active-LOW driver released)
          │
          ▼
  Step 2: Software-enforced blocking dead-time:
          delay(300);  // 300 ms dead-time on Core 1
          (Provides ~30x margin over Songle SRD 10 ms release time)
          │
          ▼
  Step 3: Energize target Solar relay coil (Relay_Solar -> ON)
          GPIO write: LOW (active-LOW driver asserted)
  ─────────────────────────────────────────────────────────────────────────────
```

### 4.3 Academic Safety and Metrology Disclosures
1. **Software vs. Certified Hardware Interlock:** The $300\text{ ms}$ dead-time is **software-enforced only** through a blocking `delay(300)` call on Core 1. It does **not** constitute a certified mechanical Automatic Transfer Switch (ATS) or hardware-interlocked contactor topology.
2. **Contact Welding Vulnerability:** A software delay cannot detect mechanically welded relay contacts or physical contact bounce. Commercial deployment requires certified mechanical interlocks and anti-islanding protection in compliance with IEEE 1547.
3. **No Waveform Arcing Instrumentation:** Oscilloscope current/voltage waveforms and contact arcing durations were not instrumented during switching; the $300\text{ ms}$ delay represents an engineering buffer exceeding the nominal $10\text{ ms}$ mechanical contact release time.

---

## 5. Cloud Platform, Telemetry Ingestion, and Persistent Energy Accounting

### 5.1 Application-Level State-Reconciliation Holdoff
In a distributed cyber-physical system, network latency creates a race condition: a user toggles an appliance relay on the web dashboard, but subsequent telemetry packets transmitted by the edge node before receiving the command report the old relay state, causing the web UI to revert ("rubber-band").

To eliminate this vulnerability without introducing complex distributed transactions, the backend implements a **15-second application-level state-reconciliation holdoff** on `device_controls`:
- When a user issues a toggle command via the dashboard, the cloud API updates `device_controls` with the target relay state and stamps a holdoff expiration timestamp (`NOW() + 15 seconds`);
- When incoming telemetry arrives at `/ingest`, the ingestion handler compares the telemetry timestamp against the active holdoff window;
- If an incoming telemetry packet carries an older relay state during an active holdoff window, the packet's metrology data is ingested for historical logging, but its reported relay state is discarded from active control state, preserving user intent during the round trip.

This mechanism is validated by automated regression tests in `backend/tests/test_state_synchronization.py`.

### 5.2 Anti-Chattering Dwell-Time and Power Hysteresis Protection
Under volatile cloud conditions, solar power can oscillate around an appliance's power rating. Rapid cycling of electromechanical relays causes arcing, contact degradation, and motor compressor failure.

The cloud decision engine enforces dual hysteresis safeguards:
1. **Minimum Dwell-Time ($T_{\text{dwell}} = 180\text{ seconds}$):** Once an appliance channel is transferred to Solar, it cannot be transferred back to Grid (or vice versa) for at least 3 minutes, filtering out transient cloud shadows;
2. **Power Hysteresis Band ($\Delta P_{\text{hyst}} = 50\text{ W}$):**
   - **Admission Threshold:** Safe Surplus must satisfy $S_{\text{safe}}(t) \ge P_{\text{device}} + 50\text{ W}$ to trigger solar transfer;
   - **Shedding Threshold:** Safe Surplus must fall below $P_{\text{device}} - 50\text{ W}$ before initiating transfer back to the utility grid.

### 5.3 Persistent Numerical Energy Accounting
The cloud platform provides persistent electrical energy accounting by numerically integrating live active power readings stored in Supabase PostgreSQL:

$$E_{\text{accum}} = \sum_{i=1}^{N-1} \frac{P_i + P_{i+1}}{2} \times \frac{\Delta t_i}{3600 \times 1000} \quad [\text{kWh}]$$

where $P_i$ is instantaneous active power (W) and $\Delta t_i = t_{i+1} - t_i$ is the inter-packet time interval (seconds).

```
         Trapezoidal Numerical Integration over Live Hardware Stream
   Power (W)
      ▲
      │       P_i          P_{i+1}
      │        ┌──────────────┐
      │        │              │  Area = ((P_i + P_{i+1}) / 2) * Δt_i
      │        │              │  (Clamped if Δt_i > 15 minutes)
      │        │              │
      └────────┴──────────────┴──────────► Time (s)
              t_i           t_{i+1}
```

1. **Gap Protection:** To prevent gross over-accumulation if the edge node loses internet connectivity for hours, the integration algorithm enforces a **15-minute maximum gap threshold** ($\Delta t_{\text{max}} = 900\text{ s}$). Intervals exceeding 15 minutes are treated as discontinuous outages and accumulate zero energy.
2. **Empirical Telemetry Dataset Verification:** As documented in thesis Chapter 5, the energy accounting engine was verified across an uninterrupted stream of **$5,244$ live hardware telemetry packets**:
   - **Integrated Consumption:** Accumulated electrical active energy was numerically integrated at **$0.3329\text{ kWh}$**;
   - **Theoretical Self-Consumption Allocation:** Evaluated against an estimated daily rooftop solar yield of $7.00\text{ kWh}$, confirming that the integrated active load falls well within modeled daily generation;
   - **Avoided-Cost Energy Accounting Calculation:** Evaluated under the flat Bangladesh residential Tier-3 tariff rate ($7.50\text{ BDT/kWh}$), the theoretical avoided grid cost is calculated as:
     $$\text{Avoided Cost} = 0.3329\text{ kWh} \times 7.50\text{ BDT/kWh} = 2.49675\text{ BDT} \approx \mathbf{2.50\text{ BDT}}$$
   - *Operational Evidence Qualification:* This figure represents an **energy-accounting observation and theoretical avoided-cost derivation** under assumed full solar self-consumption. On the physical bench testbed, the reference fan load was energized from utility AC mains through the relay board; this metric verifies the backend numerical integration and tariff-calculation pipeline rather than representing an independently audited physical financial saving from live PV.

### 5.4 Duration-Aware Scheduling and Safe Surplus Gating
In addition to instantaneous power checks, the decision engine evaluates multi-step duration feasibility before approving shiftable domestic loads:
$$\min_{\tau \in [t^*, t^* + n_{\text{hours}} - 1]} S_{\text{safe}}(\tau) \ge P_{\text{device}}$$

In an empirical validation test using the $1.20\text{ kW}$ laundry washing machine ($D = 45\text{ min}$, $n_{\text{hours}} = 1$), the decision engine evaluated 24-hour lookahead surplus trajectories. Because afternoon cloud volatility depressed $S_{\text{safe}}$ below $1.20\text{ kW}$ across all continuous candidate windows, the system correctly denied immediate activation and generated an advisory notification:
> *"No Continuous Safe Solar Window in Next 24 Hours — Recommendation: Defer to Grid Baseload."*

This confirms that the mathematical duration-aware gating formulated in Phase 3 functions correctly within the live full-stack software environment.

---

## 6. Chapter Summary and Cyber-Physical Insights

The empirical hardware and system integration results demonstrate the viability and constraints of the Solar-Aware HEMS:

1. **Rigorous Test Coverage:** 68 automated regression tests (64 backend + 4 firmware mathematical simulation) verify 100% functional correctness across decision logic, energy integration, and API resilience;
2. **Calibrated Physical Edge Node:** Zero-offset calibration ($V_{\text{zero}} = 2539.65, I_{\text{zero}} = 2537.18$) and single-point voltage scaling ($K_V = 0.619060\text{ V/count}$) achieve a $1.40\%$ calibration residual offset on physical mains;
3. **Software-Enforced Safe Switching:** FreeRTOS dual-core task concurrency separates sampling from networking, enforcing a $300\text{ ms}$ BBM dead-time delay to prevent cross-conduction;
4. **Cloud Persistence and Accounting:** Validated across $5,244$ live hardware packets ($0.3329\text{ kWh}$ integrated consumption), combined with a 15-second state-reconciliation holdoff and anti-chattering hysteresis ($180\text{ s}, 50\text{ W}$).
