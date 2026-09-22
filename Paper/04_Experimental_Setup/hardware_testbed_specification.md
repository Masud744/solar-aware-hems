# Physical Edge Testbed Specification and Embedded Metrology Setup

**Document ID:** `Paper/04_Experimental_Setup/hardware_testbed_specification.md`  
**Phase:** Phase 4 — Experimental Setup and Data Provenance  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Physical Edge Computing Architecture

The physical cyber-physical interface is anchored by an embedded Internet-of-Things (IoT) edge node responsible for continuous AC power metrology, environmental sensing, local fail-safe relay switching, and bidirectional cloud telemetry synchronization.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         ESP32 DUAL-CORE HARDWARE TESTBED                               │
├───────────────────────────────────────────────────┬────────────────────────────────────┤
│ CORE 1: Metrology, Control & Actuation            │ CORE 0: Networking & Provisioning  │
│ • Task: loopTask (Priority 1)                     │ • Task: networkTask (Priority 1)   │
│ • Execution: Free-running unthrottled burst       │ • HTTP Polling: /api/device/status │
│ • AC Sample Window: 200 ms (10 cycles @ 50 Hz)    │   (Interval: 1500 ms, TO: 1000 ms) │
│ • Cadence: Periodic 1000 ms or on relay event     │ • HTTP Ingestion: POST /ingest     │
│ • Achieved Sampling Rate: 1.5–2.0 kHz             │   (Interval: 3000 ms, TO: 1000 ms) │
│ • ADC Allocation: ADC1 Only (GPIO 34, GPIO 35)    │ • SmartProv: SoftAP Captive Portal │
│ • Switch Debounce: 40 ms software filter          │ • Wi-Fi Station Reconnect FSM      │
│ • Relay Interlock: 300 ms Software BBM Delay      │ • ADC Avoidance: ADC2 Disconnected │
└─────────────────────────┬─────────────────────────┴──────────────────┬─────────────────┘
                          │                                            │
                          ▼                                            ▼
             ┌──────────────────────────────────────────────────────────────┐
             │ Inter-Core Thread-Safe Synchronization Primitives            │
             │ • FreeRTOS QueueHandle_t remoteCommandQueue (Depth = 16)     │
             │ • FreeRTOS SemaphoreHandle_t telemetryMutex (Binary Mutex)   │
             │ • Flash Storage: NVS Namespace "hems_cal"                    │
             └──────────────────────────────────────────────────────────────┘
```

### 1.1 Microcontroller Silicon Specifications
- **Processing Silicon:** Espressif Systems ESP32 DevKit V1 (30-pin development board);
- **Processor Architecture:** Dual-core 32-bit Xtensa LX6 microprocessors running at $240\text{ MHz}$ clock frequency;
- **On-Chip Memory:** $520\text{ KB}$ internal SRAM, $448\text{ KB}$ ROM;
- **Non-Volatile Storage:** $4\text{ MB}$ external SPI flash memory (persisting FreeRTOS firmware, captive portal assets, and NVS calibration constants);
- **Wireless Subsystem:** Integrated $802.11\text{ b/g/n}$ Wi-Fi baseband ($2.4\text{ GHz}$) and Bluetooth v4.2 BR/EDR/BLE;
- **Real-Time Kernel:** FreeRTOS Kernel operating with pre-emptive priority scheduling and symmetric multiprocessing (SMP).

### 1.2 FreeRTOS Dual-Core Task Partitioning and Inter-Core Concurrency
To separate workload execution and mitigate metrology scheduling jitter caused by non-deterministic network latency, task execution is partitioned across physical cores under FreeRTOS (while noting that task pinning separates workloads but does not guarantee complete system-level isolation):

1. **Core 1 — Metrology, Control, and Relay Actuation (`loopTask`):**
   - **Task Priority:** Assigned Priority 1 (normal application priority);
   - **Metrology Burst Window:** Executes unthrottled burst sampling over a $200\text{ ms}$ continuous window, spanning exactly 10 complete AC cycles at $50\text{ Hz}$;
   - **Burst Execution Cadence:** Triggered periodically every **$1000\text{ ms}$** or immediately upon any relay actuation event to capture dynamic switching transients;
   - **Achieved Sampling Rate:** $1.5\text{--}2.0\text{ kHz}$ effective sampling rate across dual channels, capturing $300\text{--}400$ synchronized voltage-current sample pairs per cycle;
   - **Switch Debouncing:** Software debouncing across four manual single-pole double-throw (SPDT) source-selector switches evaluated at a $40\text{ ms}$ scan interval;
   - **Relay Actuation Ownership:** Exclusive single-task ownership of all relay GPIO registers, enforcing a software-enforced $300\text{ ms}$ break-before-make blocking delay (`delay(300)`).

2. **Core 0 — Network Management, Telemetry Ingestion, and Provisioning (`networkTask`):**
   - **Task Priority:** Assigned Priority 1;
   - **Cloud Command Polling:** Issues HTTP GET requests to `/api/device/status` at a **$1500\text{ ms}$ polling cadence** (`POLL_INTERVAL_MS = 1500`) with a $1000\text{ ms}$ socket timeout;
   - **Telemetry Streaming:** Dispatches JSON telemetry payloads to the cloud `/ingest` endpoint at a **$3000\text{ ms}$ push cadence** (`INGEST_INTERVAL_MS = 3000`) with a $1000\text{ ms}$ socket timeout;
   - **SmartProv SoftAP Provisioning:** Hosts an on-demand SoftAP HTTP captive portal (`192.168.4.1`) for initial Wi-Fi credential provisioning into NVS flash without hardcoding plaintext credentials;
   - **Wi-Fi Health Monitor:** Manages automatic exponential backoff reconnection if the Wi-Fi link drops.

3. **Thread-Safe Inter-Core Synchronization Primitives:**
   - **Command Dispatch Queue (`remoteCommandQueue`):** Asynchronous commands received by Core 0 from the cloud polling service are dispatched to Core 1 via a FreeRTOS `QueueHandle_t` with a queue depth of **16 items** of type `RemoteCommand`;
   - **Telemetry Snapshot Mutex (`telemetryMutex`):** Live RMS metrology snapshots computed by Core 1 are copied into a shared global structure protected by a FreeRTOS binary mutex (`xSemaphoreCreateMutex()`), eliminating read-after-write tearing during JSON serialization on Core 0.

---

## 2. Transducer Interfacing and Authoritative GPIO Pinout Allocation

Table 1 details the authoritative 30-pin hardware wiring and GPIO pinout assignments for the ESP32 edge node.

### Table 1: ESP32 DevKit V1 Authoritative 30-Pin Hardware Pinout Allocation

| GPIO Pin | Peripheral Type | Functional Role / Hardware Subsystem | Operating Voltage | Safety Notes & Isolation Rules |
| :---: | :--- | :--- | :---: | :--- |
| **GPIO 35** | **ADC1_CH7** | **ZMPT101B AC Voltage Sensor** | $0\text{--}3.3\text{ V Analog}$ | Dedicated ADC1; transformer optoisolation ($230\text{V}_{\text{AC}}$) |
| **GPIO 34** | **ADC1_CH6** | **ACS712-20A AC Current Sensor** | $0\text{--}3.0\text{ V Analog}$ | Dedicated ADC1; $10\text{k}\Omega/15\text{k}\Omega$ divider ($\alpha=0.600$) |
| **GPIO 4** | Digital I/O | **DHT22 Ambient Temp / Humidity** | $3.3\text{ V Digital}$ | Single-wire bus; $4.7\text{ k}\Omega$ external pull-up resistor |
| **GPIO 16** | Output (Low-Active) | **Relay Channel 1 — Grid Coil (Load 1)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 17** | Output (Low-Active) | **Relay Channel 2 — Grid Coil (Load 2)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 18** | Output (Low-Active) | **Relay Channel 3 — Grid Coil (Load 3)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 19** | Output (Low-Active) | **Relay Channel 4 — Grid Coil (Load 4)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 21** | Output (Low-Active) | **Relay Channel 5 — Solar Coil (Load 1)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 22** | Output (Low-Active) | **Relay Channel 6 — Solar Coil (Load 2)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 23** | Output (Low-Active) | **Relay Channel 7 — Solar Coil (Load 3)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 13** | Output (Low-Active) | **Relay Channel 8 — Solar Coil (Load 4)** | $5.0\text{ V Logic}$ | Songle SRD-05VDC; optocoupler isolated driver |
| **GPIO 25** | Input (Pull-Up) | **Manual Source Switch 1 (Load 1)** | $3.3\text{ V Digital}$ | SPDT toggle switch; $40\text{ ms}$ software debounce |
| **GPIO 26** | Input (Pull-Up) | **Manual Source Switch 2 (Load 2)** | $3.3\text{ V Digital}$ | SPDT toggle switch; $40\text{ ms}$ software debounce |
| **GPIO 27** | Input (Pull-Up) | **Manual Source Switch 3 (Load 3)** | $3.3\text{ V Digital}$ | SPDT toggle switch; $40\text{ ms}$ software debounce |
| **GPIO 14** | Input (Pull-Up) | **Manual Source Switch 4 (Load 4)** | $3.3\text{ V Digital}$ | SPDT toggle switch; $40\text{ ms}$ software debounce |
| **GPIO 2** | Output | **Status LED — Wi-Fi Connectivity** | $3.3\text{ V Digital}$ | Onboard Blue LED; blinks on disconnect, solid on link |
| **GPIO 15** | Output | **Status LED — System Operational** | $3.3\text{ V Digital}$ | External Green LED; illuminates when metrology ready |
| **GND** | Power Ground | **Common System Reference Plane** | $0.0\text{ V}$ | Star-grounding between analog ADC and relay board |
| **5V / VIN** | Power Input | **Primary DC Power Rail** | $5.0\text{ V DC}$ | Powers ACS712, relay coils, and ESP32 AMS1117 LDO |
| **3V3** | Power Output | **Regulated Sensor Power Rail** | $3.3\text{ V DC}$ | Powers DHT22, pull-up resistors, and status LEDs |

### 2.1 Critical ADC Pin Allocation Rule
The ESP32 features two internal 12-bit SAR ADCs: ADC1 (8 channels: GPIO 32–39) and ADC2 (10 channels: GPIO 0, 2, 4, 12–15, 25–27). On ESP32 silicon, **ADC2 is shared with the Wi-Fi radio baseband**. Whenever the Wi-Fi module transmits or receives RF packets, the hardware arbiter locks ADC2, causing calls to `analogRead()` on ADC2 pins to fail or return corrupted values.

To avoid the hardware conflict with the Wi-Fi subsystem, **all analog transducers are exclusively allocated to ADC1 channels**:
- Voltage sensing is mapped to **GPIO 35 (ADC1 Channel 7)**;
- Current sensing is mapped to **GPIO 34 (ADC1 Channel 6)**.

Dedicated ADC1 allocation avoids the ESP32 ADC2/Wi-Fi hardware arbiter conflict, while task pinning separates workload execution without claiming complete system-level isolation. ADC2 pins are used strictly for non-critical digital I/O or avoided entirely.

---

## 3. Analog Front-End Circuits and Metrology Signal Conditioning

### 3.1 Voltage Transducer Circuit (ZMPT101B)
Mains terminal voltage ($230\text{ V AC}, 50\text{ Hz}$) is conditioned using an active ZMPT101B micro-precision potential transformer module:
- **Galvanic Isolation:** High-permeability toroidal core providing $>4000\text{ V}$ dielectric breakdown isolation between high-voltage mains and low-voltage MCU circuitry;
- **Onboard Signal Conditioning:** Features an LM358 operational amplifier configured in an active inverting amplification and DC bias injection topology;
- **Dynamic Voltage Range:** Attenuates the $230\text{ V}_{\text{AC}}$ sinusoidal waveform and injects a regulated DC midpoint offset:
  $$V_{\text{out}}(t) = V_{\text{bias}} + G_v \cdot v_{\text{mains}}(t) \approx 1.65\text{ V} + \hat{V}_{\text{inst}}\sin(100\pi t)$$
- **ADC Dynamic Range Matching:** Peak-to-peak AC output voltage under $250\text{ V AC RMS}$ remains comfortably within $0.5\text{ V}$ to $2.8\text{ V}$, well within the ESP32 ADC linear span ($0\text{--}3.1\text{ V}$ with $11\text{ dB}$ attenuation).

### 3.2 Current Transducer Circuit (ACS712-20A) and Divider Safety Proof
AC load current is captured using an Allegro ACS712ELCTR-20A-T Hall-effect current sensor module:
- **Measurement Principle:** Low-resistance primary copper conduction path ($1.2\text{ m}\Omega$) located near a monolithic Hall sensor IC with $>2.1\text{ kV}_{\text{RMS}}$ galvanic isolation;
- **Power Supply Rail:** Operates from the $5.0\text{ V DC}$ power rail with a nominal quiescent midpoint voltage of:
  $$V_{\text{zero, nom}} = \frac{V_{\text{CC}}}{2} = \frac{5.00\text{ V}}{2} = 2.50\text{ V}$$
- **Nominal Sensitivity:** Rated by manufacturer at $S_{\text{nom}} = 0.100\text{ V/A}$ ($100\text{ mV/A}$).

#### The 5V Transducer Voltage Safety Hazard
Because the ACS712 operates on $5.0\text{ V}$, during large positive AC current swings, its analog output can swing up to $5.0\text{ V}$. Because ESP32 GPIO pins have an absolute maximum rating of $3.6\text{ V}$, connecting the ACS712 output directly to an ESP32 ADC pin risks permanent dielectric breakdown of the input gate oxide.

#### Resistor Divider Mathematical Proof
A passive resistive voltage divider ($R_1 = 10\text{ k}\Omega \pm 1\%$ series, $R_2 = 15\text{ k}\Omega \pm 1\%$ to ground) steps down the sensor output:
$$\alpha_{\text{divider}} = \frac{R_2}{R_1 + R_2} = \frac{15\text{ k}\Omega}{10\text{ k}\Omega + 15\text{ k}\Omega} = \mathbf{0.600}$$

Under the operating assumption of a maximum sensor output of $V_{\text{out, max}} = 5.00\text{ V}$, the verified passive divider scales the pin voltage to:
$$V_{\text{pin, max}} = 5.00\text{ V} \times 0.600 = \mathbf{3.00\text{ V}} \le 3.30\text{ V}$$
This provides a calculated positive margin of $0.30\text{ V}$ below the $3.30\text{ V}$ operating rail and $0.60\text{ V}$ below the $3.60\text{ V}$ absolute maximum rating.

*Circuit Safety Disclosure:* This calculation is strictly conditional on the stated maximum sensor-output assumption ($5.00\text{ V}$) and the actual verified divider circuit ($R_1 = 10\text{ k}\Omega, R_2 = 15\text{ k}\Omega$); it is an analytical circuit calculation and is not claimed as an experimentally proven physical overvoltage protection guarantee under catastrophic fault conditions.

The nominal quiescent zero-current DC voltage at the ESP32 ADC pin is:
$$V_{\text{pin, zero}} = 2.50\text{ V} \times 0.600 = \mathbf{1.50\text{ V}} \quad (\approx 1,861\text{ nominal ADC counts})$$

---

## 4. Discrete Sampled RMS Metrology Mathematics

During each $200\text{ ms}$ sampling burst ($M \approx 300\text{--}400$ sample pairs), Core 1 executes discrete root-mean-square integration over sampled AC waveforms.

```
       200 ms Continuous Sampling Window (10 Full 50 Hz Cycles)
├──────────────────────────────────────────────────────────────────────┤
│  raw_v[k] ──> subtract V_zero ──> scale by K_V      ──> v_inst[k]   │
│  raw_i[k] ──> subtract I_zero ──> scale by S_eff    ──> i_inst[k]   │
│  Accumulate:  sum(v_inst^2), sum(i_inst^2), sum(v_inst * i_inst)    │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
         Discrete-Time Sampled Root-Mean-Square Integration:
         • V_RMS = sqrt( (1/M) * sum(v_inst^2) )
         • I_RMS = sqrt( (1/M) * sum(i_inst^2) )
         • P_real = (1/M) * sum(v_inst * i_inst)
         • S_apparent = V_RMS * I_RMS
         • Power Factor (PF) = P_real / S_apparent
```

### 4.1 Discrete Mathematical Formulations

1. **Discrete Sampled RMS Voltage ($V_{\text{RMS}}$):**
   $$V_{\text{RMS}} = \sqrt{\frac{1}{M} \sum_{m=1}^M \left( \text{ADC}_v[m] - V_{\text{zero}} \right)^2} \times K_V$$
   where $\text{ADC}_v[m]$ is the raw 12-bit ADC reading ($0\text{--}4095$), $V_{\text{zero}}$ is the empirical zero-crossing DC offset (counts), and $K_V$ is the calibrated voltage scaling coefficient ($\text{V/count}$).

2. **Discrete Sampled RMS Current ($I_{\text{RMS}}$):**
   $$I_{\text{RMS}} = \frac{\sqrt{\frac{1}{M} \sum_{m=1}^M \left( \text{ADC}_i[m] - I_{\text{zero}} \right)^2} \times \left(\frac{V_{\text{ADC\_REF}}}{4095 \times \alpha_{\text{divider}}}\right)}{S_{\text{ACS712}}}$$
   where $V_{\text{ADC\_REF}} = 3.30\text{ V}$, $\alpha_{\text{divider}} = 0.600$, and $S_{\text{ACS712}} = 0.100\text{ V/A}$ ($100\text{ mV/A}$). The effective current conversion factor is:
   $$K_I = \frac{3.30\text{ V}}{4095 \times 0.600 \times 0.100\text{ V/A}} = \mathbf{0.013431}\text{ A/count} \quad (13.43\text{ mA/count})$$

3. **Discrete Active Real Power ($P_{\text{real}}$):**
   $$P_{\text{real}} = \frac{1}{M} \sum_{m=1}^M v_{\text{inst}}[m] \cdot i_{\text{inst}}[m] \quad \text{[Watts]}$$
   where $v_{\text{inst}}[m] = (\text{ADC}_v[m] - V_{\text{zero}}) \times K_V$ and $i_{\text{inst}}[m] = (\text{ADC}_i[m] - I_{\text{zero}}) \times K_I$. This synchronized instantaneous product naturally accounts for the phase displacement angle $\cos(\theta)$ without requiring separate phase estimation.

4. **Apparent Power ($S$) and Displacement Power Factor ($\text{PF}$):**
   $$S = V_{\text{RMS}} \times I_{\text{RMS}} \quad \text{[Volt-Amperes]}$$
   $$\text{PF} = \frac{P_{\text{real}}}{S} \quad \left(\text{clamped to } [-1.0, +1.0]\right)$$

5. **Accumulated Electrical Energy ($E_{\text{accum}}$):**
   $$E_{\text{accum}}(t) = E_{\text{accum}}(t-1) + \frac{P_{\text{real}}(t) \times \Delta t_{\text{hours}}}{1000} \quad [\text{kWh}]$$

---

## 5. Multi-Stage Bench Calibration and NVS Flash Persistence

Due to hardware manufacturing tolerances in low-cost sensors and passive resistors, factory calibration is essential. A four-stage calibration state machine establishes empirical offsets and coefficients, summarized in Table 2.

### Table 2: Multi-Stage Hardware Metrology Calibration Execution Status

| Calibration Stage | Firmware Protocol | Reference Instrument / Condition | Empirical Parameter / Value | Verification Status |
| :---: | :--- | :--- | :--- | :---: |
| **Stage 1** | Zero-Offset (`CAL_ZERO`) | All relays OFF ($I = 0\text{ A}$), 400 ms settling | $V_{\text{zero}} = 2539.65, I_{\text{zero}} = 2537.18\text{ counts}$ | **[MEASURED ON HARDWARE]** |
| **Stage 2** | Voltage Scale (`SET_VCAL`) | Fluke DMM reference ($V_{\text{ref}} = 225.00\text{ V AC}$) | $K_V = 0.619060\text{ V/count}$ ($1.40\%$ residual) | **[CALIBRATED AGAINST DMM]** |
| **Stage 3** | Current Sens (`SET_SENS`) | Manufacturer nominal specification | $S_{\text{nom}} = 0.100\text{ V/A}$ ($100\text{ mV/A}$) | **[NOMINAL SENSITIVITY]** |
| **Stage 4** | Known-Load Validation | Walton WTF9M3 Stand Fan ($60\text{ W rated}$) | $V \approx 226\text{ V}, I \approx 0.28\text{ A}$ ($S = 63.28\text{ VA}$) | **[BENCH LOAD OBSERVED]** |

### 5.1 Stage 1: Zero-Offset Calibration (`CAL_ZERO`)
- **Safety Interlock:** Automatically commands all eight relay channels `OFF` with a $400\text{ ms}$ settling delay to guarantee zero current flow ($I = 0.00\text{ A}$);
- **Burst Acquisition:** Core 1 executes a continuous $3000\text{ ms}$ burst, collecting $2,840$ raw ADC sample pairs;
- **Empirical Measured Offsets:**
  $$V_{\text{zero}} = \mathbf{2539.65\text{ counts}} \quad (2.046\text{ V DC at pin})$$
  $$I_{\text{zero}} = \mathbf{2537.18\text{ counts}} \quad (2.044\text{ V DC at pin})$$
- **State Transition:** Offsets are committed to NVS flash; system state transitions to `ZERO_CALIBRATED`.

### 5.2 Stage 2: Voltage Scale Factor Derivation (`SET_VCAL`)
- **Calibration Reference Instrument:** A calibrated True-RMS digital multimeter (DMM) measured steady-state AC mains voltage at the wall receptacle during the calibration session:
  $$V_{\text{ref, cal}} = \mathbf{225.00\text{ V AC RMS}}$$
- **Scale Factor Derivation (Exact Reproducibility):**
  - Pre-calibration test factor in firmware: $K_{V\text{, test}} = 0.781622\text{ V/count}$;
  - Unrounded raw test measurement: $V_{\text{measured, raw}} = 284.08388\text{ V AC RMS}$ (displayed on serial monitor as rounded $284.08\text{ V}$);
  - Raw RMS ADC count swing across 200 ms:
    $$\text{ADC}_{\text{RMS\_swing}} = \frac{284.08388\text{ V}}{0.781622\text{ V/count}} = 363.45427\text{ counts RMS}$$
  - Calibrated system-level voltage scaling coefficient:
    $$K_V = \frac{V_{\text{ref, cal}}}{\text{ADC}_{\text{RMS\_swing}}} = \frac{225.00000\text{ V}}{363.45427\text{ counts}} = \mathbf{0.619060\text{ V/count}}$$
- **Live Validation Telemetry:** Live ESP32 reading recorded $V_{\text{ESP32, live}} = \mathbf{228.16\text{ V AC RMS}}$ (persisted in Supabase row #836);
- **Measurement Error Disclosures:**
  - **Calibration-Session Residual Offset (Session 1):**
    $$\Delta V_{\text{cal}} = \frac{|228.16\text{ V} - 225.00\text{ V}|}{225.00\text{ V}} \times 100\% = \mathbf{1.40\%}$$
  - **Cross-Session Observational Comparison (Session 2):**
    $$\Delta V_{\text{val}} = \frac{|228.16\text{ V} - 226.00\text{ V}|}{226.00\text{ V}} \times 100\% = \mathbf{0.96\%}$$
- **Academic Characterization:** $K_V = 0.619060\text{ V/count}$ is characterized as a **system-level board calibration coefficient** capturing op-amp gain and resistor tolerances, rather than an idealized theoretical sensor constant.

### 5.3 Stage 3: Current Sensitivity Parameterization (`SET_SENS`)
- **Parameter Value:** Configured with manufacturer nominal sensitivity $S_I = 0.100\text{ V/A}$ ($100\text{ mV/A}$) for the ACS712-20A Hall-effect module;
- **Mandatory Academic Disclosure:** Current sensitivity remains nominal/datasheet-based. No independent multi-point calibration curve against a precision laboratory current source has been conducted across the 0–20A operational span.

### 5.4 Stage 4: Physical Appliance Bench Validation
- **Reference Appliance:** Walton WTF9M3 domestic stand fan connected to Load Channel 1 (GPIO 16);
- **Manufacturer Nameplate Specification:** Rated active power $P_{\text{rated}} = 60.0\text{ W}$;
- **Directly Measured Physical Evidence (Bench Multimeter):**
  - AC mains voltage observation: $V_{\text{DMM}} \approx 226.00\text{ V AC RMS}$;
  - Steady-state load current: $I_{\text{DMM}} \approx 0.28\text{ A AC RMS}$;
- **Deterministic Derived Quantities:**
  - Measured Apparent Power: $S_{\text{bench}} = 226.00\text{ V} \times 0.28\text{ A} = \mathbf{63.28\text{ VA}}$;
  - Comparison Ratio: $\frac{60.0\text{ W}}{63.28\text{ VA}} \approx 0.948$ (theoretical comparison between rated active power and measured apparent power; operating power factor was not measured via oscilloscope waveform phase shift);
  - Quantization Resolution: Measuring $0.28\text{ A}$ on a 20A module with $13.43\text{ mA/count}$ yields an excursion of $\pm 29.5\text{ ADC counts}$ swing across the 4096 full-scale range. While safely above the firmware $50\text{ mA}$ software noise cutoff, sub-ampere loads operate in a quantized regime.

### 5.5 NVS Flash Parameter Persistence
The four calibration parameters are permanently committed to the ESP32 Non-Volatile Storage (NVS) flash partition under the dedicated namespace `"hems_cal"`:
```c
// NVS Calibration Namespace: "hems_cal"
preferences.putFloat("v_zero", 2539.65);
preferences.putFloat("i_zero", 2537.18);
preferences.putFloat("v_cal",  0.619060);
preferences.putFloat("i_sens", 0.100000);
```
During system boot, Core 1 automatically reads the `"hems_cal"` partition, restoring calibrated metrology constants across power cycles without requiring manual recalibration.

---

## 6. Relay Switching Matrix and Break-Before-Make Safety Topology

### 6.1 Dual-Bank Independent Source Selection
The HEMS edge prototype incorporates an 8-channel electromechanical relay board (Songle SRD-05VDC-SL-C) configured in a **dual-bank independent source selection topology** for four domestic load circuits:
- **Grid Bank (Relays 1–4):** Mapped to GPIO 16, 17, 18, 19, switching commercial utility grid mains ($230\text{ V AC}$) to Loads 1–4;
- **Solar Bank (Relays 5–8):** Mapped to GPIO 21, 22, 23, 13, switching local solar inverter output to Loads 1–4.

Each relay channel provides optocoupler isolation, a flyback clamping diode across the coil, and a transistorized low-side driver actuated by active-LOW logic from the ESP32.

### 6.2 300 ms Software Break-Before-Make (BBM) Sequence
Connecting two unsynchronized AC sources (the commercial utility grid and an unsynchronized solar inverter) to the same appliance simultaneously causes a catastrophic dead short-circuit, potentially destroying inverter MOSFETs and triggering branch breakers.

To prevent overlapping cross-conduction, the firmware enforces a strict **Break-Before-Make (BBM) transfer-switching sequence** implemented on Core 1:

```
  Transition Command: Transfer Load i from Grid to Solar
  ───────────────────────────────────────────────────────────────────
  Step 1: De-energize active Grid relay coil (Relay_Grid -> OFF)
          GPIO write: HIGH (de-assert active-LOW relay)
          │
          ▼
  Step 2: Software-enforced blocking dead-time delay:
          delay(300);  // 300 ms dead-time on Core 1
          (Exceeds 10 ms nominal relay contact release time)
          │
          ▼
  Step 3: Energize target Solar relay coil (Relay_Solar -> ON)
          GPIO write: LOW (assert active-LOW relay)
  ───────────────────────────────────────────────────────────────────
```

### 6.3 Mandatory Academic Safety Disclosures
1. **Software vs. Hardware Interlock:** The $300\text{ ms}$ BBM dead-time is **software-enforced only** via a blocking `delay(300)` call on Core 1. It does **not** constitute a certified mechanical Automatic Transfer Switch (ATS) or hardware-interlocked contactor pair.
2. **Contact Welding Vulnerability:** A software interlock cannot detect mechanically welded contacts or physical relay contact bounce. In commercial residential installations, certified mechanical interlocks and anti-islanding relays are strictly required.
3. **No Waveform Arcing Validation:** No oscilloscope current/voltage waveforms or contact arcing durations were measured during relay switching; the 300 ms delay is an engineering design choice exceeding the relay's $10\text{ ms}$ nominal mechanical release time.

---

## 7. Appliance Load Configuration and Anti-Chattering Hysteresis

### 7.1 Domestic Load Parameterization
The HEMS prototype manages four discrete domestic load channels parameterized in accordance with verified repository configurations (`assistant_tools.py`), detailed in Table 3.

### Table 3: Physical Appliance Load Parameterization and Scheduling Classification

| Load Channel | Appliance Description | Rated Power ($P_{\text{rated}}$) | Nominal Cycle Duration | Hourly Block ($n_{\text{hours}}$) | Scheduling Flexibility |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **Load 1** | **Washing Machine** (Laundry) | $1.20\text{ kW}$ ($1,200\text{ W}$) | $45\text{ minutes}$ ($0.75\text{ h}$) | $n_{\text{hours}} = 1$ | Deferrable / Shiftable |
| **Load 2** | **Water Pump** (Rooftop Tank) | $0.75\text{ kW}$ ($750\text{ W}$) | $30\text{ minutes}$ ($0.50\text{ h}$) | $n_{\text{hours}} = 1$ | Deferrable / Shiftable |
| **Load 3** | **Refrigerator** (Compressor) | $0.15\text{ kW}$ ($150\text{ W}$) | Continuous $24/7$ | Excluded | Inflexible Baseload |
| **Load 4** | **Electric Rice Cooker** (Cooking) | $0.70\text{ kW}$ ($700\text{ W}$) | $40\text{ minutes}$ ($\approx 0.67\text{ h}$) | $n_{\text{hours}} = 1$ | Deferrable / Shiftable |

### 7.2 Anti-Chattering Dwell-Time and Power Hysteresis Protection
Under fluctuating cloud cover, solar generation can oscillate rapidly around an appliance's rated threshold. Rapid cycling degrades relay contacts and damages inductive motor compressors.

The cloud decision engine enforces two protection mechanisms:
1. **Minimum Dwell-Time ($T_{\text{dwell}} = 180\text{ seconds}$):** Once an appliance channel is switched to Solar, it cannot be transferred back to Grid (or vice versa) for at least 3 minutes, preventing chatter from transient cloud shadows;
2. **Power Hysteresis Band ($\Delta P_{\text{hyst}} = 50\text{ W}$):**
   - **Admission Threshold:** Solar Safe Surplus must exceed $P_{\text{device}} + 50\text{ W}$ to trigger transfer to solar;
   - **Shedding Threshold:** Solar Safe Surplus must fall below $P_{\text{device}} - 50\text{ W}$ before the system initiates shedding back to the commercial grid.
