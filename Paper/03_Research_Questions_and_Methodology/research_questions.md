# Phase 3: Research Questions and Hypotheses Formulation

**Document ID:** `Paper/03_Research_Questions_and_Methodology/research_questions.md`  
**Phase:** Phase 3 — Research Questions, System Architecture & Mathematical Formulation  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 1, 2, 4) and `Paper/02_Research_Gap_and_Contributions/`  

---

## 1. Executive Summary & Research Framing

Conventional residential energy management systems (HEMS) routinely optimize electrical dispatch under deterministic assumptions, ignoring forecast uncertainty and treating machine learning models as black boxes. In contrast, this research investigates the fundamental cyber-physical research problem:

> **Central Research Premise:** *Can a unified, leak-free machine learning framework coupled with closed-form statistical uncertainty quantification, decoupled dual-layer explainability, and dual-core edge hardware produce safer, more transparent, and cost-effective residential energy-management decisions than deterministic optimization systems that blindly trust point forecasts?*

To investigate this premise with academic rigor, four formal, mutually supporting **Research Questions (RQ1–RQ4)** are formulated. Each research question corresponds to an identified literature failure mode (Gaps 1–6), establishes formal statistical hypotheses ($H_0$ vs. $H_1$), identifies operational variables, and specifies quantitative validation criteria.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 THE FOUR CORE RESEARCH QUESTIONS (RQ1 – RQ4)                │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ RQ1: Leak-Free Predictive        │ RQ3: Decoupled Dual-Layer                │
│      Modeling & Feature Integrity│      Explainable AI (TreeSHAP + Causal)  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ RQ2: Closed-Form Heteroskedastic │ RQ4: Concurrent Edge Metrology,          │
│      Uncertainty Quantification  │      Software Delays & Advisory AI Safety│
└──────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 2. Research Question 1 (RQ1): Leak-Free Predictive Modeling and Feature Integrity

### 2.1 Formal Question Statement
> **RQ1:** *How can machine learning models for residential photovoltaic generation and single-household load demand be formulated to eliminate circular target leakage, contemporaneous electrical dependencies, and temporal lookahead, while achieving statistically significant predictive accuracy improvements over baseline physical formulas and naive persistence models under strict chronological holdout evaluation?*

### 2.2 Theoretical and Methodological Context
- **Addressed Literature Failure Modes:** [Gap 1](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-1-target-circularity-and-pyranometer-dependency-in-solar-forecasting) (Target circularity from contemporaneous Global Tilted Irradiance) and [Gap 2](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-2-contemporaneous-metrology-leakage-in-single-household-load-forecasting) (Metrology leakage from contemporaneous $V_t, I_t, \text{Sub}_i$).
- **Methodological Vulnerability in Prior Work:** Academic benchmarks frequently report near-perfect coefficients of determination ($R^2 > 0.99$) by feeding concurrent irradiance (GTI) into solar models or feeding contemporaneous current ($I_t$) and voltage ($V_t$) into load models. Because active power physically obeys $P = V \cdot I \cdot \cos\theta$ and sub-metered benchmarks exhibit near-deterministic algebraic coupling ($P \approx V \cdot I / 1000$), these models reduce forecasting to trivial contemporaneous regression. In live forward-looking dispatch, future current and future on-site irradiance are physically unavailable ahead of consumption.
- **Proposed Architectural Solution:**
  1. *Solar Pipeline:* Construct a non-circular feature vector $\mathbf{x}_{\text{solar}}(t) \in \mathbb{R}^7$ derived strictly from forecastable atmospheric reanalysis variables (cloud cover, 2m temperature, relative humidity, wind speed, calendar encodings), strictly quarantining and excluding GTI.
  2. *Load Pipeline:* Formulate a strictly causal autoregressive feature vector $\mathbf{x}_{\text{load}}(t) \in \mathbb{R}^{16}$ purged of $V_t, I_t, \text{Sub}_i$, relying exclusively on causal historical lags ($P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}$), `.shift(1)` rolling window statistics ($\mu_{3\text{h}}, \mu_{24\text{h}}, \sigma_{24\text{h}}, \mu_{168\text{h}}$), calendar encodings (hour, day_of_week, month, is_weekend), and exogenous ambient temperature ($T2M$).

### 2.3 Formal Hypotheses
- **Solar Null Hypothesis ($H_{0,\text{solar}}$):** Non-circular machine learning regressors trained exclusively on forecastable atmospheric variables do not outperform the deterministic physical thermodynamic photovoltaic formula applied to forecast irradiance:
  $$H_{0,\text{solar}}: \text{MAE}_{\text{ML, solar}} \ge \text{MAE}_{\text{Physical, solar}}$$
- **Solar Alternative Hypothesis ($H_{1,\text{solar}}$):** Data-driven non-circular ensemble models (Random Forest) learn non-linear atmospheric attenuation patterns that significantly reduce Mean Absolute Error relative to the uncorrected physical formula baseline:
  $$H_{1,\text{solar}}: \text{MAE}_{\text{ML, solar}} < \text{MAE}_{\text{Physical, solar}} \quad (\text{Target: } >50\% \text{ relative MAE reduction})$$
- **Load Null Hypothesis ($H_{0,\text{load}}$):** A non-leaky autoregressive load model evaluated on single-household stochastic consumption under chronological holdout testing cannot outperform a naive persistence baseline ($\hat{P}_t = P_{t-1}$):
  $$H_{0,\text{load}}: R^2_{\text{ML, load}} \le R^2_{\text{Persistence, load}} \quad \text{and} \quad \text{MAE}_{\text{ML, load}} \ge \text{MAE}_{\text{Persistence, load}}$$
- **Load Alternative Hypothesis ($H_{1,\text{load}}$):** Causal autoregressive lag structures capturing diurnal and weekly human behavioral periodicity yield statistically significant improvements over naive persistence:
  $$H_{1,\text{load}}: R^2_{\text{ML, load}} > R^2_{\text{Persistence, load}} \quad \text{and} \quad \text{MAE}_{\text{ML, load}} < \text{MAE}_{\text{Persistence, load}} \quad (\text{Target: } >20\% \text{ relative MAE reduction})$$

### 2.4 Variable Operationalization
- **Independent Variables ($\mathbf{X}$):**
  - Solar: Cloud cover fraction ($c_t$), 2m temperature ($T_{2\text{m}}$), relative humidity ($RH$), 10m wind speed ($WS$), diurnal cyclical angles $(\sin(2\pi h/24), \cos(2\pi h/24))$, annual solar geometry $(\sin(2\pi d/365), \cos(2\pi d/365))$, forming $\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$.
  - Load: Autoregressive lags ($P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}$), unshifted rolling statistics ($\mu_{3\text{h}}(t-1), \mu_{24\text{h}}(t-1), \sigma_{24\text{h}}(t-1), \mu_{168\text{h}}(t-1)$), calendar indicators (Hour, DayOfWeek, Month, IsWeekend), and exogenous 2m temperature ($T_{2\text{m}}$), forming the authoritative 16-dimensional feature vector $\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$.
- **Dependent Variables ($Y$):**
  - Solar: Target generation $P_{\text{solar}}(t)$ (kW) modeled across a 5-panel monocrystalline array (per-panel active area $A_{\text{panel}} = 2.42\text{ m}^2$, total array active area $A_{\text{total}} = 12.10\text{ m}^2$, total nominal peak capacity $2.115\text{ kWp}$).
  - Load: Single-household active power consumption $P_{\text{load}}(t)$ (kW).
- **Control & Quarantine Variables:** Contemporaneous Global Tilted Irradiance ($\text{GTI}_t$), mains voltage ($V_t$), total current intensity ($I_t$), and sub-metering active circuits ($P_{\text{sub1}}, P_{\text{sub2}}, P_{\text{sub3}}$) are strictly quarantined from $\mathbf{X}$.

### 2.5 Quantitative Validation Benchmarks
- **Solar Benchmark:** Champion Random Forest ($N_{\text{test}} = 11,612$) achieves $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, $\text{RMSE} = 0.124356\text{ kW}$, $\text{MAPE} = 49.42\%$, representing a **$78.63\%$ MAE reduction** over the uncorrected linear baseline ($\text{MAE} = 0.300105\text{ kW}$).
- **Load Benchmark:** Champion Random Forest ($N_{\text{test}} = 6,532$) achieves $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$, $\text{RMSE} = 0.483827\text{ kW}$, $\text{MAPE} = 42.59\%$, outperforming the naive persistence baseline ($R^2 = 0.350000, \text{MAE} = 0.441000\text{ kW}$) by **$+69.39\%$ relative $R^2$ gain** ($+0.2429$ absolute) and **$24.70\%$ relative MAE reduction**.

---

## 3. Research Question 2 (RQ2): Closed-Form Heteroskedastic Uncertainty Quantification

### 3.1 Formal Question Statement
> **RQ2:** *Can empirical, condition-stratified forecast error distributions be formulated into a closed-form algebraic safety margin ($O(1)$ algorithmic complexity) that effectively bounds solar shortfall risk without requiring computationally intensive mathematical programming solvers (MILP/MINLP) or non-convex quantile regression neural networks?*

### 3.2 Theoretical and Methodological Context
- **Addressed Literature Failure Mode:** [Gap 3](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-3-computational-demands-of-downstream-uncertainty-quantification-on-embedded-edge-nodes) (Computational intractability of downstream UQ on embedded edge hardware).
- **Methodological Vulnerability in Prior Work:** Prior probabilistic HEMS frameworks either employ scenario-tree stochastic programming (which scales exponentially as $\mathcal{O}(S^H)$ and requires commercial desktop solvers like CPLEX or Gurobi), or deploy deep quantile networks that suffer from quantile crossing anomalies ($\hat{y}_{\tau_1} > \hat{y}_{\tau_2}$ for $\tau_1 < \tau_2$). Neither approach is feasible for real-time edge execution or offline fallback during cloud disconnection. Furthermore, conventional systems assume homoskedastic Gaussian errors, ignoring the empirical reality that solar forecast variance triples under overcast regimes and load variance doubles during evening peak hours.
- **Proposed Architectural Solution:**
  1. *Heteroskedastic Residual Stratification:* Partition empirical holdout residual errors into discrete physical condition strata: cloud cover deciles for solar ($\sigma_{\text{solar}}(c_t)$) and diurnal clock-hour buckets for load ($\sigma_{\text{load}}(h_t)$).
  2. *Closed-Form Conservative Safe Surplus ($S_{\text{safe}}$):* Formulate net available solar power via closed-form algebraic bounds evaluated in the FastAPI backend:
     $$S_{\text{safe}}(t) = \max\left(0, \hat{P}_{\text{solar}}(t) - k_{\text{solar}}\sigma_{\text{solar}}(c_t)\right) - \left(\hat{P}_{\text{load}}(t) + k_{\text{load}}\sigma_{\text{load}}(h_t)\right)$$
  3. *Deterministic Multi-Hour Admission:* For non-interruptible appliances running over duration $D$, verify continuous feasibility across discrete forecast blocks:
     $$S_{\text{window}}(t, n_{\text{hours}}) = \min_{\tau \in [t, t+n_{\text{hours}}-1]} S_{\text{safe}}(\tau) \ge P_{\text{device}}, \quad n_{\text{hours}} = \max(1, \lceil D \rceil)$$

### 3.3 Formal Hypotheses
- **Uncertainty Null Hypothesis ($H_{0,\text{UQ}}$):** An algebraic safety margin governed by empirical heteroskedastic standard deviations ($k\sigma_{\text{net}}$) cannot achieve greater than $90\%$ empirical solar shortfall coverage without reducing solar self-consumption utilization below $70\%$:
  $$H_{0,\text{UQ}}: \text{SolarCoverage}(k) \le 90\% \quad \lor \quad \text{SolarUtilization}(k) < 70\% \quad \forall k \ge 0$$
- **Uncertainty Alternative Hypothesis ($H_{1,\text{UQ}}$):** By conditioning standard deviations on physical meteorological and diurnal states, a balanced operating multiplier ($k=1.0$) simultaneously achieves $\ge 90\%$ empirical solar coverage and $\ge 80\%$ solar self-consumption utilization, establishing a continuous, tunable trade-off curve across $k \in [0.0, 2.5]$:
  $$H_{1,\text{UQ}}: \text{SolarCoverage}(k=1.0) \ge 90\% \quad \land \quad \text{SolarUtilization}(k=1.0) \ge 80\%$$

### 3.4 Variable Operationalization
- **Independent Variables:** Safety confidence multiplier $k \in [0.0, 2.5]$, cloud cover fraction $c_t \in [0, 100]\%$, diurnal clock hour $h_t \in [0, 23]$.
- **Evaluated Strata Standard Deviations:**
  - Solar: $\sigma_{\text{clear}} = 0.0851\text{ kW}$ ($0\text{--}20\%$), $\sigma_{\text{partly}} = 0.1317\text{ kW}$ ($21\text{--}60\%$), $\sigma_{\text{overcast}} = 0.1386\text{ kW}$ ($61\text{--}100\%$), global baseline $\sigma = 0.1225\text{ kW}$.
  - Load: $\sigma_{\text{night}} = 0.2662\text{ kW}$ ($0\text{--}5\text{h}$), $\sigma_{\text{morning}} = 0.4800\text{ kW}$ ($6\text{--}11\text{h}$), $\sigma_{\text{afternoon}} = 0.5114\text{ kW}$ ($12\text{--}17\text{h}$), $\sigma_{\text{evening}} = 0.6075\text{ kW}$ ($18\text{--}23\text{h}$), global baseline $\sigma = 0.4831\text{ kW}$.
- **Dependent Performance Metrics:**
  - *Empirical Solar Coverage:* $\mathbb{P}\left(P_{\text{solar, actual}} \ge P_{\text{solar, safe}}\right)$.
  - *Empirical Load Coverage:* $\mathbb{P}\left(P_{\text{load, actual}} \le P_{\text{load, conservative}}\right)$.
  - *Solar Self-Consumption Utilization:* Fraction of generated solar energy consumed by domestic loads without curtailment or unbudgeted grid import.

### 3.5 Quantitative Validation Benchmarks
- **Empirical Sensitivity Across $k$ (Holdout Evaluation):**
  - $k=0.0$ (Deterministic Baseline): $92.40\%$ utilization, but unhedged shortfall risk of $28.60\%$.
  - $k=1.0$ (Balanced Risk-Aware Point): **$93.92\%$ solar coverage**, **$88.36\%$ load coverage**, **$81.50\%$ solar utilization**.
  - $k=2.0$ (Conservative Point): **$97.36\%$ solar coverage**, **$96.12\%$ load coverage**, **$70.13\%$ solar utilization**.
  - $k=2.5$ (Ultra-Conservative Point): **$98.32\%$ solar coverage**, **$97.85\%$ load coverage**, **$64.75\%$ solar utilization**.
- **Computational Complexity:** $O(1)$ arithmetic complexity evaluated in closed algebraic form in the FastAPI backend without solver dependencies.

---

## 4. Research Question 3 (RQ3): Decoupled Dual-Layer Explainable AI

### 4.1 Formal Question Statement
> **RQ3:** *How can model-level game-theoretic feature attributions (TreeSHAP) be decoupled from system-level appliance control causality to provide mathematically exact, auditable explanations for technical operators while generating actionable, plain-language operational rationales for non-expert residential occupants?*

### 4.2 Theoretical and Methodological Context
- **Addressed Literature Failure Mode:** [Gap 4](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-4-explainability-conflation-and-omission-of-control-causality) (Explainability conflation and omission of control causality).
- **Methodological Vulnerability in Prior Work:** Published energy XAI literature exhibits a severe architectural disconnect. Studies either apply SHAP/LIME solely to regression models to output abstract feature rankings (e.g., *"Historical lag $P_{t-24}$ contributes $+0.42\text{ kW}$ to the load forecast"*), which provides zero operational rationale for why a specific physical appliance was permitted or deferred; or they apply SHAP directly to deep reinforcement learning policies, outputting high-dimensional vectors of continuous Shapley values that overwhelm non-expert homeowners.
- **Proposed Architectural Solution:**
  Implementation of a strictly decoupled **Dual-Layer Explainability Architecture**:
  1. *Layer 1 (Model-Level XAI):* TreeSHAP feature attribution engine satisfying exact game-theoretic efficiency ($\sum_{i=1}^M \phi_i = \hat{f}(\mathbf{x}) - \mathbb{E}[f(\mathbf{X})]$), providing global beeswarm distributions and local waterfall plots for machine learning auditors.
  2. *Layer 2 (System-Level Causal XAI):* A deterministic, rule-based natural language generator that translates physical energy deficits ($S_{\text{safe}} < P_{\text{device}}$), conditional risk buffers ($k\sigma_{\text{net}}$), and 24-hour lookahead schedules into actionable natural language explanations with recommended deferral windows ($t^*$).

### 4.3 Formal Hypotheses
- **XAI Null Hypothesis ($H_{0,\text{XAI}}$):** Model-level TreeSHAP feature attributions cannot satisfy game-theoretic efficiency within numerical floating-point tolerances ($<10^{-5}\text{ kW}$), and statistical regression weights cannot be deterministically mapped to appliance admission/deferral rationales without ambiguous heuristics:
  $$H_{0,\text{XAI}}: \left| \hat{f}(\mathbf{x}) - \mathbb{E}[f(\mathbf{X})] - \sum_{i=1}^M \phi_i(\mathbf{x}) \right| \ge 10^{-5}\text{ kW}$$
- **XAI Alternative Hypothesis ($H_{1,\text{XAI}}$):** TreeSHAP attributions achieve exact mathematical additivity (residual error $<10^{-6}\text{ kW}$), while the decoupled Layer 2 rule engine maps physical power margins directly to deterministic plain-language explanations identifying deficit magnitude and the optimal 24-hour deferral hour $t^*$:
  $$H_{1,\text{XAI}}: \left| \hat{f}(\mathbf{x}) - \mathbb{E}[f(\mathbf{X})] - \sum_{i=1}^M \phi_i(\mathbf{x}) \right| < 10^{-6}\text{ kW} \quad \forall \mathbf{x} \in \mathcal{D}_{\text{test}}$$

### 4.4 Variable Operationalization
- **Layer 1 Mathematical Attributions:** Base value $\phi_0 = \mathbb{E}[f(\mathbf{X})]$, marginal Shapley vectors $\boldsymbol{\phi}(\mathbf{x}) \in \mathbb{R}^M$, global importance metric $I_i = \frac{1}{N}\sum |\phi_i|$.
- **Layer 2 Causal Operational Variables:** Rated appliance power $P_{\text{device}}$, projected safe surplus $S_{\text{safe}}(t)$, power deficit $\Delta P = P_{\text{device}} - S_{\text{safe}}(t)$, optimal lookahead slot $t^* = \arg\max \sum S_{\text{safe}}$.
- **End-User Communication Constructs:** Human-readable explanations conveying: (1) binary admission status (APPROVED / DENIED); (2) physical power breakdown (forecast solar, baseload, safety margin); (3) operational causality for denial; (4) optimal deferral window.

### 4.5 Quantitative Validation Benchmarks
- **Mathematical Additivity:** TreeSHAP floating-point additivity error strictly verified at $<10^{-6}\text{ kW}$ across all evaluated test instances in both solar and load domains.
- **Causal Consistency:** Layer 2 natural language generator generates zero conflicting statements across the 64 backend regression tests, correctly identifying surplus/deficit magnitudes and optimal lookahead hours.

---

## 5. Research Question 4 (RQ4): Embedded Edge Real-Time Metrology, Software Delays & Advisory AI Safety

### 5.1 Formal Question Statement
> **RQ4:** *How can a dual-core FreeRTOS microcontroller firmware architecture prevent network latency from corrupting continuous high-frequency AC metrology while enforcing software break-before-make transfer switching delays, and how can conversational Large Language Model assistants be architecturally constrained to prevent unauthorized cyber-physical relay actuation?*

### 5.2 Theoretical and Methodological Context
- **Addressed Literature Failure Modes:** [Gap 5](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-5-hardware-task-concurrency-contention-in-single-threaded-polling-loops) (Single-threaded MCU execution contention) and [Gap 6](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-6-absence-of-documented-phase-isolation-transfer-delays-in-dual-source-switching) (Omission of transfer dead-time delays).
- **Methodological Vulnerability in Prior Work:**
  1. *Hardware Concurrency Contention:* Microcontroller firmware in published literature overwhelmingly relies on single-threaded polling loops (`void loop()`). High-latency network operations (Wi-Fi handshakes, HTTP POST telemetry requiring $200\text{--}3000\text{ ms}$) stall the CPU, causing severe sample drops that corrupt discrete sampled RMS estimation ($V_{\text{RMS}}, I_{\text{RMS}}$).
  2. *AC Cross-Conduction Hazards:* IoT relay prototypes frequently command instantaneous transfer switching between grid mains and auxiliary solar inverters without documented dead-times, creating severe risks of contact arcing and out-of-phase line-to-line AC short-circuits.
  3. *Autonomous AI Vulnerabilities:* Emerging agentic IoT systems connect Large Language Models directly to physical actuator tool calls, introducing hallucination-driven switching risks.
- **Proposed Architectural Solution:**
  1. *Dual-Core FreeRTOS Task Pinning:* Pin periodic discrete sampled RMS burst estimation (200 ms sampling window for ZMPT101B and ACS712-20A, executed every 1000 ms) and switch debouncing (40 ms) to the primary control loop on Core 1 (default Arduino task, priority 1), while isolating Wi-Fi networking, SmartProv SoftAP provisioning, backend polling (1500 ms), and HTTP telemetry push (3000 ms cadence) to Core 0 (`networkTask`, priority 1).
  2. *Software-Enforced Break-Before-Make Transfer Delay:* Enforce a 300 ms blocking delay (`delay(300)`) in firmware between de-energizing Grid relays and energizing Solar relays across dual 4-channel banks, ensuring sequential non-overlapping coil commands.
  3. *SolarMate Read-Only Safety Boundary:* Architecturally isolate the conversational AI assistant by providing zero database write access and zero relay actuation endpoints.

### 5.3 Formal Hypotheses
- **Hardware Concurrency Null Hypothesis ($H_{0,\text{HW}}$):** Pinning high-frequency AC metrology and Wi-Fi network communications to separate processor cores does not prevent telemetry blocking from interrupting discrete sampled RMS burst cycles:
  $$H_{0,\text{HW}}: \Delta T_{\text{sample, Wi-Fi}} > T_{\text{AC, cycle}} \quad (20\text{ ms at } 50\text{ Hz})$$
- **Hardware Concurrency Alternative Hypothesis ($H_{1,\text{HW}}$):** FreeRTOS dual-core task partitioning isolates Core 1 metrology execution from Core 0 network latency, maintaining uninterrupted discrete sampled RMS burst execution on Core 1 isolated from Core 0 network transmission latency during 3000 ms telemetry pushes:
  $$H_{1,\text{HW}}: \Delta T_{\text{sample, Wi-Fi}} \le 10\text{ ms} \quad (\text{Zero metrology loop starvation})$$
- **Software Safety Interlock Null Hypothesis ($H_{0,\text{Safety}}$):** Conversational AI tools cannot be guaranteed against accidental relay triggering without complex prompt engineering, and firmware state machines allow concurrent relay coil energization during rapid state transitions.
- **Software Safety Interlock Alternative Hypothesis ($H_{1,\text{Safety}}$):** Structural architectural isolation (omitting relay actuation endpoints from the LLM tool schema) guarantees 100% fail-safe conversational isolation, while firmware state sequencing guarantees a 300 ms non-overlapping de-energization window across all switching events.

### 5.4 Variable Operationalization
- **Independent Variables:** FreeRTOS core assignment (Core 0 vs. Core 1), network transmission state (idle vs. active Wi-Fi HTTP POST), relay switching commands.
- **Dependent Variables:** Core 1 metrology sampling cycle period ($T_{\text{loop}}$), discrete sampled RMS estimation execution continuity, relay contact command overlap duration, SolarMate AI API tool invocation logs.
- **Explicit Distinction of Verification Levels:**
  1. *Software Verification:* 64 automated backend unit and integration tests verifying API schemas, state synchronization, decision gating, and upstream resilience.
  2. *Firmware Mathematical Unit Simulation:* 4 host-compiled tests verifying discrete sampled RMS estimation math, inductive phase-lag apparent power, and resistor divider voltage safety ($<3.0\text{ V}$).
  3. *Documented Bench Observation & Firmware Implementation Check:* Bench multimeter calibration verifying single-point voltage scaling ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual) and steady-state fan load monitoring ($0.28\text{ A}$ nominal on ACS712); firmware code inspection confirming software-enforced non-overlapping relay coil commands via `delay(300)`.
  4. *Remaining Physical Hardware Limitations:* Single-point voltage calibration without multi-point polynomial linearization; nominal ACS712-20A current sensitivity without precision shunt calibration; software-enforced delay lacking certified hardware mechanical interlocks or external storage oscilloscope waveform captures.

### 5.5 Quantitative Validation Benchmarks
- **Automated Test Suite:** **68/68 automated tests passed (100% pass rate in 3.84s)**, comprising 64 backend tests and 4 firmware mathematical tests.
- **Advisory AI Security:** 100% of tested SolarMate AI tool schemas omit relay actuation tools; zero direct actuator calls permitted.
- **Bench Metrology Observation:** Single-point voltage scaling factor $K_V = 0.619060\text{ V/count}$ verified against $225.00\text{ V}$ DMM reference ($1.40\%$ residual offset logged in Supabase row #836).

---

## 6. Comprehensive Traceability: Gaps $\to$ Contributions $\to$ Research Questions

The matrix below provides complete bidirectional mapping across the research gaps, novel contributions, research questions, and validation criteria:

| Research Gap Addressed | Implemented System Component | Core Scientific Contribution | Targeted RQ | Formal Evaluation Metric / Benchmark |
| :--- | :--- | :--- | :---: | :--- |
| **Gap 1:** Solar Target Circularity | `ml/train_solar_model.py` (Non-Circular Open-Meteo Pipeline) | **Contribution 1:** Methodological Leakage Remediation | **RQ1** | $R^2 = 0.9547$, $\text{MAE} = 0.0641\text{ kW}$ ($78.63\%$ reduction vs OLS linear baseline). |
| **Gap 2:** Load Metrology Leakage | `ml/train_load_model.py` (Causal Autoregressive Pipeline) | **Contribution 1:** Honest Single-Household Benchmarking | **RQ1** | $R^2 = 0.5929$, $\text{MAE} = 0.3321\text{ kW}$ ($+69.39\%$ relative $R^2$ gain vs persistence). |
| **Gap 3:** UQ Solver Overhead | `backend/app/services/decision_engine.py` (Safe Surplus) | **Contribution 2:** Closed-Form Heteroskedastic Safe Surplus ($O(1)$) | **RQ2** | $O(1)$ complexity; zero solver licenses; $k=1.0 \rightarrow 93.92\%$ solar coverage, $81.50\%$ utilization. |
| **Gap 4:** Explainability Conflation | `ml/xai/` & `backend/app/services/explanation_service.py` | **Contribution 3:** Decoupled Dual-Layer Explainable AI | **RQ3** | TreeSHAP additivity error $<10^{-6}\text{ kW}$; deterministic causal natural language generator. |
| **Gap 5:** Hardware Concurrency | `firmware/firmware.ino` (FreeRTOS Task Partitioning) | **Contribution 4:** Dual-Core FreeRTOS Edge Microcontroller Prototype | **RQ4** | Core 1 metrology (1000 ms burst) decoupled from Core 0 Wi-Fi (3000 ms push); discrete sampled RMS estimation. |
| **Gap 6:** Missing Transfer Delays | `firmware/relay_controller.cpp` (Software BBM Delay) | **Contribution 4:** Software-Enforced Transfer Delay & Metrology | **RQ4** | 300 ms software blocking delay (`delay(300)`) preventing overlapping relay coil energization. |
| **Triad Convergence Gap** | Full Cyber-Physical Ecosystem (`ml/`, `backend/`, `firmware/`, `ui/`) | **Contribution 5 & 6:** Full-Stack Ecosystem & Synthetic Evaluation | **RQ1–RQ4** | 68/68 automated tests passed (100% in 3.84s); 176 common-scenario synthetic evaluation testbed. |

---

## 7. Section Summary

By formalizing RQ1 through RQ4 with explicit statistical hypotheses, variable operationalization, and multi-level verification boundaries, this document establishes a rigorous scientific framework. The subsequent documents in this phase detail the complete **System Architecture** ([`system_architecture.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/03_Research_Questions_and_Methodology/system_architecture.md)) and the **Mathematical Formulations** ([`mathematical_formulation.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/03_Research_Questions_and_Methodology/mathematical_formulation.md)).
