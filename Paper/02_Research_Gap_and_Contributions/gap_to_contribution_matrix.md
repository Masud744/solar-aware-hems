# Phase 2: Systematic Gap-to-Contribution Mapping Matrix

**Document ID:** `Paper/02_Research_Gap_and_Contributions/gap_to_contribution_matrix.md`  
**Phase:** Phase 2 — Formal Research Gaps, Limitations, and Novelty Claims  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Table 2.6 / Table F) and `Paper/01_Literature_Review/`  

---

## 1. Traceability Architecture

This matrix provides the formal, bidirectional traceability chain linking each identified literature failure mode to our implemented engineering solution, academic contribution, empirical validation, and primary research question:

$$\text{Literature Gap} \longrightarrow \text{Cited Studies} \longrightarrow \text{Architectural Solution} \longrightarrow \text{Implemented Component} \longrightarrow \text{Core Contribution} \longrightarrow \text{Empirical Evidence} \longrightarrow \text{Research Question}$$

---

## 2. Master Gap-to-Contribution Mapping Matrix

| Gap ID & Thematic Pillar | Prevailing Literature Limitation / Failure Mode | Key Literature Studies | Proposed Architectural Solution | Implemented Repository Component | Core Academic Contribution | Quantitative Empirical Evidence | RQ Addressed | Boundary Disclosure / Scope Limitation |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **Gap 1**<br>Solar PV Forecasting | **Target Circularity & Pyranometer Over-Reliance:** Academic models include contemporaneous GTI/GHI as inputs, yielding trivial identity inversion ($R^2 \approx 1.0$) that obscures cloud transient errors. On-site pyranometers ($>\$1,500$) are cost-prohibitive for homes. | Brester et al. [P18], Hossain et al. [P19], Aduama et al. [P35] | Non-circular feature engineering relying strictly on forecastable atmospheric reanalysis variables (cloud cover, temperature, humidity, wind). | `ml/solar/` training pipeline & Open-Meteo feature extractor | **Contribution 1:** Methodological Leakage Remediation & Honest Benchmarking | Test holdout ($N=11,612$): $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, $\text{RMSE} = 0.124356\text{ kW}$ ($78.63\%$ reduction vs OLS). | **RQ1** | Trained on historical ERA5-Land reanalysis data; operational live NWP validation remains future work. |
| **Gap 2**<br>Load Demand Forecasting | **Contemporaneous Metrology Leakage:** Inclusion of same-hour voltage ($V_t$), current ($I_t$), or branch sub-meterings ($P_{\text{sub}}$) introduces target leakage via the AC active power relationship ($P = V \cdot I \cdot \cos\theta$) and the near-deterministic algebraic coupling present in sub-metered datasets ($R^2 > 0.999$ in our reproduction), producing models that cannot execute forward in time. | G R et al. [P20], Irankhah et al. [P22], Forootani et al. [P25], Devanathan et al. [P36] | Causal autoregressive lag architecture ($P_{t-1 \dots 168}$), `.shift(1)` rolling stats ($\mu_{3\text{h}}, \mu_{24\text{h}}, \sigma_{24\text{h}}$), calendar encodings, and exogenous temperature ($T2M$). | `ml/load/` training pipeline & lag feature generator | **Contribution 1:** Methodological Leakage Remediation & Honest Benchmarking | Test holdout ($N=6,532$): $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$ vs persistence baseline ($R^2=0.3500$, $\text{MAE}=0.4410\text{ kW}$); $+69.39\%$ relative $R^2$ gain. | **RQ1** | Evaluated on single-dwelling benchmark (UCI); multi-dwelling transferability requires future empirical trials. Ambient $T2M$ is legitimate weather data. |
| **Gap 3**<br>Uncertainty Quantification | **Combinatorial Solver Overhead & Edge Infeasibility:** Stochastic MILP, CVaR, and MPC require commercial desktop solvers (CPLEX/GAMS) with exponential scenario tree scaling $\mathcal{O}(S^H)$. Deep quantile networks suffer from quantile crossing ($\hat{y}_{0.10} > \hat{y}_{0.90}$). | Sesay et al. [P26], Suresh et al. [P27], Cai et al. [P28], Yang et al. [P29], Javadi et al. [P31], van der Meer et al. [P32] | Closed-form Safe Surplus decision engine ($S_{\text{safe}} = \hat{P}_{\text{solar}} - \hat{P}_{\text{load}} - k\sigma_{\text{net}}$) with heteroskedastic conditional error bucketing (cloud deciles, diurnal hours). | `backend/app/services/decision_engine.py` | **Contribution 2:** Closed-Form Heteroskedastic Safe Surplus Architecture ($O(1)$ Complexity) | Algorithmic evaluation with $O(1)$ complexity; zero solver licenses; $k=1.0 \rightarrow 93.92\%$ solar coverage, $88.36\%$ load coverage, $81.50\%$ utilization. | **RQ2** | Evaluated algebraically in FastAPI backend; closed-form arithmetic structure is compatible with future microcontroller porting. |
| **Gap 4**<br>Explainable AI (XAI) | **Explainability Conflation:** Applying SHAP/LIME solely to regression models without explaining downstream relay actions, or outputting high-dimensional raw Shapley vectors from DRL policies, confusing non-expert homeowners. | Nejati Amiri et al. [P01], Aduama et al. [P35], Devanathan et al. [P36], Teixeira et al. [P39], Bhandary et al. [P41], Machlev et al. [P58] | Decoupled Dual-Layer XAI: Layer 1 computes TreeSHAP feature attributions; Layer 2 translates energy deficits, risk buffers, and lookahead into causal natural language explanations ($t^*$). | `ml/xai/` TreeSHAP module & `backend/app/services/explanation_service.py` | **Contribution 3:** Decoupled Dual-Layer Explainable AI Framework | TreeSHAP exact additivity discrepancy $<10^{-6}\text{ kW}$ across all test instances; deterministic deferral recommendations. | **RQ3** | Layer 1 serves system engineers and auditors; Layer 2 serves non-expert residential occupants. |
| **Gap 5**<br>Hardware Concurrency | **Single-Threaded Telemetry Latency:** In surveyed prototypes [P43], [P45], firmware relies on single-threaded loops where synchronous network communications introduce latency; no implementation detail regarding task concurrency was identified in the inspected material. | Pradhan et al. [P43], Singh et al. [P44], Siregar et al. [P45] | Dual-core FreeRTOS firmware partitioning: Core 1 pins discrete True-RMS AC sampling (10 ms, Priority 2); Core 0 pins asynchronous WiFi and telemetry (5000 ms, Priority 1). | `firmware/firmware.ino` & `firmware/config.h` | **Contribution 4:** Dual-Core FreeRTOS Edge Prototype with Characterized Metrology and Software-Enforced Transfer Delay | Continuous discrete sampling loop runs with no observable blocking interruption during 5000 ms telemetry transmission. | **RQ4** | Discrete sampling frequency $1.5\text{--}2.0\text{ kHz}$ across 10 AC cycles ($200\text{ ms}$). Single-point voltage calibration ($K_V = 0.619060\text{ V/count}$). |
| **Gap 6**<br>Relay Safety Interlock | **Absence of Documented Transfer Dead-Times:** In surveyed dual-source prototypes [P42], [P44], [P45], no implementation detail regarding transfer switching dead-times or phase-isolation interlocks was identified in the inspected material. | de Sousa et al. [P42], Singh et al. [P44], Siregar et al. [P45], Franco et al. [P47] | Software-enforced 300 ms break-before-make blocking delay (`delay(300)`) between de-asserting Grid relays and asserting Solar relays across dual 4-channel banks. | `firmware/firmware.ino` (`switchRelayChannel`) | **Contribution 4:** Dual-Core FreeRTOS Edge Prototype with Characterized Metrology and Software-Enforced Transfer Delay | Software-enforced 300 ms de-energization window confirmed in firmware state sequencing; eliminates software-commanded concurrent coil energization. | **RQ4** | Software-enforced blocking delay, not a certified hardware safety interlock circuit. |
| **Triad Convergence Gap** | **Disciplinary Fragmentation:** Academic literature operates in isolated silos—studies excel in ML forecasting OR mathematical optimization OR IoT hardware; within the reviewed 58-paper corpus, no study was identified that unifies all three domains into a cohesive, verified framework. | All 58 Surveyed Core Studies and Foundational Reviews ([P01]–[P58]) | Integrated cyber-physical HEMS unifying leak-free ML forecasting, closed-form heteroskedastic UQ, decoupled dual-layer XAI, dual-core FreeRTOS edge firmware, and a full-stack web platform. | Full repository ecosystem (`ml/`, `backend/`, `firmware/`, `frontend/`) | **Contribution 5 & 6:** Full-Stack Ecosystem & Synthetic Cross-Regional Evaluation | End-to-end operational pipeline validated by 64 backend tests + 4 firmware tests (100% pass rate in 4.17s). | **RQ1–RQ4** | Synthetic cross-regional pairing of French load data with Bangladesh solar data aligned across 176 common hour-month scenarios. |

---

## 3. Mapping of Research Questions to Empirical Evidence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RESEARCH QUESTIONS ALIGNMENT                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ RQ1: Leak-Free Predictive Modeling ──► Contributions 1 & 6 ──► Gaps 1 & 2   │
│      Evidence: Solar R² = 0.9547; Load R² = 0.5929 (+69.39% vs Persistence) │
├─────────────────────────────────────────────────────────────────────────────┤
│ RQ2: Heteroskedastic Risk & UQ   ──► Contribution 2        ──► Gap 3        │
│      Evidence: Closed-form O(1) Safe Surplus; k=1.0 -> 93.92% Solar Coverage│
├─────────────────────────────────────────────────────────────────────────────┤
│ RQ3: Decoupled Explainability    ──► Contribution 3        ──► Gap 4        │
│      Evidence: TreeSHAP Additivity < 1e-6 kW; Causal Natural Language Text  │
├─────────────────────────────────────────────────────────────────────────────┤
│ RQ4: Embedded Real-Time Safety   ──► Contributions 4 & 5   ──► Gaps 5 & 6   │
│      Evidence: FreeRTOS Core Decoupling; 300 ms BBM Delay; Bench Validation │
└─────────────────────────────────────────────────────────────────────────────┘
```

### RQ1: Leak-Free Predictive Modeling
- **Formal Question:** *How can solar PV generation and residential load forecasting models be formulated to eliminate circular target leakage and contemporaneous feature dependencies on standard benchmark datasets?*
- **Primary Source / Evidence:** Holdout test results on Open-Meteo solar archive ($N=11,612$) and UCI load repository ($N=6,532$).
- **Methodological Solution:** Purged GTI from $\mathcal{F}_{\text{solar}}$ and purged $V_t, I_t, \text{Sub}_i$ from $\mathcal{F}_{\text{load}}$.
- **Verified Result:** Solar RF achieves $R^2 = 0.954743$ ($\text{MAE} = 0.064134\text{ kW}$); Load RF achieves $R^2 = 0.592867$ ($\text{MAE} = 0.332060\text{ kW}$), representing $+69.39\%$ relative $R^2$ improvement over the naive persistence baseline ($R^2=0.350000$).

### RQ2: Statistical Uncertainty Quantification
- **Formal Question:** *How do empirical heteroskedastic forecast error margins ($k \cdot \sigma$) trade off solar self-consumption utilization against shortfall risk across varying operational confidence multipliers?*
- **Primary Source / Evidence:** Residual error distributions across cloud cover deciles and diurnal hours.
- **Methodological Solution:** Formulated closed-form Safe Surplus inequality $S_{\text{safe}}(t) = \hat{P}_{\text{solar}} - \hat{P}_{\text{load}} - k\sigma_{\text{net}} \ge P_{\text{device}}$.
- **Verified Result:** Evaluated sweep of $k \in [0.0, 2.5]$: $k=0.0 \rightarrow 92.40\%$ utilization (unhedged); $k=1.0 \rightarrow 93.92\%$ solar coverage, $88.36\%$ load coverage, $81.50\%$ utilization; $k=2.0 \rightarrow 97.36\%$ solar coverage, $70.13\%$ utilization; $k=2.5 \rightarrow 98.32\%$ solar coverage, $64.75\%$ utilization.

### RQ3: Decoupled Explainability
- **Formal Question:** *How can model-level game-theoretic feature attributions (TreeSHAP) be cleanly decoupled from system-level natural language causal explanations to provide actionable decision transparency?*
- **Primary Source / Evidence:** TreeExplainer evaluations on champion models and rule-based natural language generation engine.
- **Methodological Solution:** Strict two-layer architecture separating model regression drivers from appliance admission causality.
- **Verified Result:** Exact TreeSHAP additivity ($\sum \phi_i = \hat{f}(x) - E[f(x)]$) with floating-point discrepancy $< 10^{-6}\text{ kW}$ across all test instances; deterministic natural language explanations providing Safe Surplus margins, deficit magnitude, and optimal deferral slots ($t^*$).

### RQ4: Embedded Real-Time Safety
- **Formal Question:** *How can dual-core FreeRTOS microcontroller firmware achieve concurrent discrete RMS metrology and network telemetry while enforcing software break-before-make dead-time delays across dual-bank physical relay circuits?*
- **Primary Source / Evidence:** ESP32 DevKit firmware implementation (`firmware/firmware.ino`), automated unit test suites (`backend/tests/`, `firmware/tests/`), and bench multimeter calibration readings.
- **Methodological Solution:** Pinned continuous True-RMS AC sampling to Core 1 (10 ms control loop, Priority 2); pinned asynchronous WiFi/HTTP telemetry to Core 0 (5000 ms loop, Priority 1); implemented `delay(300)` blocking dead-time between relay banks.
- **Verification Levels and Explicit Distinction:**
  1. *Software Verification:* 64 automated backend tests validate API endpoints, state synchronization, decision logic, and rate-limiting resilience.
  2. *Firmware Mathematical Tests:* 4 unit simulation tests validate discrete RMS math, inductive load phase lag, and voltage divider boundaries in host-simulated environments.
  3. *Documented Bench Observation & Firmware Implementation Check:* Bench testing documented single-point voltage calibration ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual) and steady-state load operation with a Walton table fan ($0.28\text{ A}$ nominal on uncalibrated ACS712-20A). Firmware inspection confirmed software-enforced non-overlapping relay state sequencing via blocking delay(300); physical contact arcing and phase isolation under asynchronous AC sources were not instrumented with an oscilloscope on this prototype.
  4. *Remaining Hardware Limitations:* Metrology is constrained by single-point voltage calibration ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual) and nominal ACS712-20A sensitivity ($0.100\text{ V/A}$) without multi-point current calibration; the 300 ms delay is a software-enforced blocking call, not a certified fail-safe hardware mechanical interlock.

---

## 4. Section Summary

This systematic mapping establishes an unbroken chain of academic traceability. Every research gap directly corresponds to a documented literature failure mode, an implemented software or firmware module in this repository, an authoritative quantitative test result, and a core academic contribution.
