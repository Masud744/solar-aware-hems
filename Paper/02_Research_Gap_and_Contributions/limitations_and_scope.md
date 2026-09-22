# Phase 2: Academic Limitations, Methodological Boundaries, and Scope Disclosures

**Document ID:** `Paper/02_Research_Gap_and_Contributions/limitations_and_scope.md`  
**Phase:** Phase 2 — Formal Research Gaps, Limitations, and Novelty Claims  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 1 & 6) and `Paper/00_Context_and_Audit/`  

---

## 1. Philosophy of Academic Transparency

In strict adherence to the Paper Workspace Operating Rules and the IEEE standards of reproducible engineering research, this document establishes the explicit methodological, empirical, and physical boundaries of the Solar-Aware HEMS project. 

Academic rigor requires that every system limitation be openly acknowledged, precisely bounded, and physically contextualized rather than concealed or overstated. The eight boundaries detailed below define the exact operating envelope of the presented research.

---

## 2. Exhaustive Disclosure of the Eight Methodological and System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE EIGHT SYSTEM BOUNDARIES & DISCLOSURES                │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ 1. Synthetic Cross-Regional Data │ 5. Software BBM Delay vs Hard Interlock  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ 2. ERA5-Land Reanalysis vs NWP   │ 6. Backend Execution vs Embedded Edge    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ 3. Single-Point Voltage Calib.   │ 7. Algebraic Logic vs Pareto Solvers     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ 4. Nominal ACS712-20A Current    │ 8. Flat Tariff Financial Accounting      │
└──────────────────────────────────┴──────────────────────────────────────────┘
```

---

### Boundary 1: Synthetic Cross-Regional Evaluation Pairing

- **Empirical Reality:** The experimental evaluation framework couples two independent public datasets originating from distinct geographical and temporal domains:
  1. *Household Load Dataset:* The UCI Individual Household Electric Power Consumption benchmark, recorded in **Sceaux, France** ($48.78^\circ\text{N}, 2.29^\circ\text{E}$) between December 2006 and November 2010 (34,168 raw hourly records; 32,656 clean records).
  2. *Solar Photovoltaic Dataset:* Atmospheric reanalysis weather and generation data synthesized for **Kaliakair, Gazipur, Bangladesh** ($24.07^\circ\text{N}, 90.22^\circ\text{E}$) across the period 2020–2026 (58,056 hourly records).
- **Methodological Coupling Protocol:** Because these datasets are not co-located in space or time, they are aligned across **176 unique common calendar operational scenarios** defined by matching diurnal hour ($h \in [0, 23]$) and annual month ($m \in [1, 12]$) indices.
- **Explicit Academic Disclosure:** This synthetic pairing is explicitly disclosed as a **cyber-physical academic evaluation testbed**. It does not represent empirical telemetry gathered simultaneously from a single physical dwelling. While it successfully demonstrates cross-regime algorithmic robustness, full real-world validation requires co-located longitudinal telemetry from operational households.

---

### Boundary 2: Weather Reanalysis Characteristics vs. Operational NWP

- **Empirical Reality:** The solar forecasting pipeline was trained and evaluated on historical reanalysis data (ERA5-Land reanalysis accessed via the Open-Meteo archive) rather than live, real-time Numerical Weather Prediction (NWP) operational feeds.
- **Physical Implications:** ERA5-Land provides reanalysis fields that assimilate global satellite and surface observations into a physically consistent numerical model. Consequently, historical reanalysis irradiance profiles exhibit lower high-frequency variance and smoother cloud transient dynamics than raw, live operational NWP predictions.
- **Explicit Academic Disclosure:** The empirical standard deviation observed in our solar holdout evaluations ($\sigma_{\text{solar}} = 0.1225\text{ kW}$) represents a **lower-bound error estimate**. When deployed against live operational weather APIs subject to forecast update delays and atmospheric micro-climatic modeling errors, residual forecast errors will be larger. System operators must recalibrate the condition-stratified uncertainty tables ($\sigma_{\text{solar}}$) using local real-time operational feeds upon deployment.

---

### Boundary 3: Discrete Voltage Metrology Single-Point Calibration

- **Empirical Reality:** Real-time AC mains voltage metrology on the ESP32 microcontroller utilizes a ZMPT101B active potential transformer module connected to analog pin ADC1_CH7 (GPIO 35).
- **Calibration Procedure & Calculation:** Metrology gain was determined via a single-point calibration session against a calibrated bench Digital Multimeter (DMM):
  $$K_V = \frac{V_{\text{ref}}}{\text{ADC}_{\text{RMS, raw}}} = \frac{225.00000\text{ V}}{363.45427\text{ counts}} = \mathbf{0.619060\text{ V/count}}$$
  calculated over 10 full AC cycles ($200\text{ ms}$ window at $50\text{ Hz}$, 2,000 samples) and persisted in NVS flash memory namespace `"hems_cal"`.
- **Physical Meaning and System-Level Interpretation:**
  $K_V$ represents the linear discrete scaling multiplier converting raw zero-subtracted ADC RMS count swings into True-RMS AC mains voltage ($V_{\text{RMS}} = K_V \times \text{ADC}_{\text{RMS}}$).
  Crucially, $K_V = 0.619060\text{ V/count}$ is a **system-level board calibration coefficient**—integrating the specific ZMPT101B transformer turns ratio, onboard operational-amplifier burden and trim potentiometer gain, filtering circuitry, and the ESP32 successive-approximation ADC transfer function for this individual hardware build at a $225.0\text{ V}$ operating point. It is **not** an inherent universal sensor constant or generic component specification of the ZMPT101B module itself.
- **Empirical Residual Disclosure:** Live telemetry logged an unadjusted ESP32 voltage reading of $V_{\text{ESP32, live}} = 228.16\text{ V}$, representing a **$+1.40\%$ calibration-session residual offset** relative to the $225.00\text{ V}$ reference ($0.96\%$ cross-session delta relative to a subsequent $\approx 226\text{ V}$ DMM check).
- **Explicit Academic Disclosure:** Single-point linear scaling does not correct for potential non-linearities in the ESP32 successive approximation register (SAR) ADC near saturation thresholds ($>250\text{ V}$) or magnetic core saturation in the ZMPT101B transformer. Multi-point polynomial calibration and thermal drift compensation remain future enhancements.

---

### Boundary 4: Current Sensing Nominal Datasheet Calibration

- **Empirical Reality:** Load current sensing is executed using an ACS712-20A Hall-effect current sensor module connected to ADC1_CH6 (GPIO 34) through a $10\text{ k}\Omega / 15\text{ k}\Omega$ precision resistor voltage divider ($\alpha = 0.600$).
- **Calibration Constants:** Firmware operates strictly under nominal manufacturer datasheet specifications:
  $$\text{Sensitivity} = 0.100\text{ V/A} \quad (100\text{ mV/A})$$
  with dynamic quiescent zero-offset tracking conducted during firmware initialization ($I_{\text{zero}} = 2537.18$ ADC counts).
- **Explicit Academic Disclosure:** The current measurement subsystem relies strictly on nominal datasheet sensitivity. No independent multi-point current-meter calibration against precision current shunts or laboratory standards has been completed across its full operational span ($\pm 20\text{ A}$). Furthermore, the inherent thermal drift of Hall-effect elements ($\approx 1.5\text{ mV/}^\circ\text{C}$) and environmental electromagnetic interference from adjacent relay coils are uncompensated in analog hardware. Current readings must be interpreted as functional operational metrics rather than utility-grade revenue-certified billing metrology.

---

### Boundary 5: Software Break-Before-Make Delay vs. Certified Hardware Interlock

- **Empirical Reality:** To prevent phase cross-conduction between unsynchronized AC mains and auxiliary inverter sources during transfer switching, ESP32 firmware enforces a **300 ms blocking delay** (`delay(300)`) between de-asserting the 4-Channel Grid Relay Bank (GPIO 16, 17, 18, 19) and asserting the 4-Channel Solar Relay Bank (GPIO 21, 22, 23, 13).
- **Explicit Academic Disclosure:** This 300 ms timing window is a **software-enforced implementation delay**, not a certified, fail-safe hardware mechanical interlock circuit.
  - *Mitigation Scope:* Under normal operating conditions, the 300 ms window exceeds the mechanical release time ($5\text{--}15\text{ ms}$) and contact arc extinction duration of the Songle SRD-05VDC relays, successfully mitigating contact arcing and cross-conduction during routine transfers.
  - *Failure Modes:* In the event of microcontroller firmware hangs, memory corruption, brownout resets, or physical relay contact mechanical welding caused by high inductive inrush currents, software logic cannot guarantee phase isolation. Industrial and commercial deployments require certified hardware-interlocked contactors or dedicated automatic transfer switches (ATS).

---

### Boundary 6: Decision Engine Execution Location (Backend vs. Embedded)

- **Empirical Reality:** The Safe Surplus algorithm, condition-stratified uncertainty lookups, and 24-hour duration-aware appliance admission engine execute within the **FastAPI cloud/local REST backend** (`backend/app/services/decision_engine.py`).
- **Physical Operational Role:** The physical ESP32 microcontroller functions strictly as an embedded real-time metrology acquisition, relay actuation, and network communication node. It periodically polls the backend (`/api/device/status`) to receive target relay states determined by the backend decision engine.
- **Explicit Academic Disclosure:** The paper must never state or imply that the Safe Surplus decision engine currently executes on the ESP32 microcontroller. The closed-form algebraic structure of the decision logic ($O(1)$ arithmetic complexity, zero external solver dependencies) was specifically designed to be structurally compatible with future microcontroller C++ porting, but operational execution in the evaluated prototype is backend-hosted.

---

### Boundary 7: Rule-Based Algebraic Decision Logic vs. Dynamic Solver Optimization

- **Empirical Reality:** The energy management controller employs an algebraic threshold rule ($S_{\text{safe}}(t) \ge P_{\text{device}}$) combined with a greedy 24-hour lookahead horizon search ($t^*$) to determine appliance admission.
- **Optimization Trade-Off:** This closed-form approach eliminates combinatorial solver overhead, avoids commercial solver licenses (CPLEX/Gurobi), and guarantees instantaneous deterministic decisions evaluated with $O(1)$ algorithmic complexity.
- **Explicit Academic Disclosure:** The framework does not solve a multi-objective mathematical programming problem (such as Mixed-Integer Linear Programming or Model Predictive Control). Consequently, it does not guarantee Pareto-optimal cost minimization under complex dynamic Time-of-Use (ToU) tariffs, battery electrochemical degradation constraints (C-rate limits, cycling fade), or multi-dwelling peer-to-peer energy trading markets.

---

### Boundary 8: Financial and Economic Accounting Scope

- **Empirical Reality:** Economic savings computations in the web dashboard and report assume a flat residential electricity tariff of **BDT 7.50 / kWh** (representative of standard domestic tier-3 rates in Bangladesh) applied to gross self-consumption:
  $$E_{\text{self}}(t) = \min\left(E_{\text{load}}(t), E_{\text{solar}}(t)\right)$$
  $$\text{Cost Savings} = E_{\text{self}} \times 7.50\text{ BDT/kWh}$$
- **Explicit Academic Disclosure:** Financial accounting assumes zero economic credit for curtailed or exported solar energy (absence of net-metering feed-in tariffs for residential micro-systems), includes no demand capacity charges, and does not model battery capital depreciation or inverter levelized cost of energy (LCOE).

---

## 3. Section Summary

These eight explicit disclosures establish an unassailable standard of academic honesty. By clearly defining what the system is—and what it is not—the paper protects itself against methodological criticism during peer review, anchoring every scientific contribution in verifiable empirical evidence.
