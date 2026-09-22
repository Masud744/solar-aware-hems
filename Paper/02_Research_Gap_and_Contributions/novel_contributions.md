# Phase 2: Novel Scientific and Technical Contributions

**Document ID:** `Paper/02_Research_Gap_and_Contributions/novel_contributions.md`  
**Phase:** Phase 2 — Formal Research Gaps, Limitations, and Novelty Claims  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 1 & 2) and `Paper/01_Literature_Review/`  

---

## 1. Overview of Scientific Novelty and Value Proposition

To overcome the systemic fragmentation identified in the 58-paper literature survey, this research develops **Solar-Aware HEMS**—an end-to-end cyber-physical energy management architecture that achieves full **Triad Convergence**. 

The fundamental value proposition of this work is proving that:
> *Residential demand-side energy management does not require computationally intractable mathematical solvers, opaque deep reinforcement learning policies, or expensive industrial pyranometers. Instead, high-accuracy, leak-free machine learning forecasters coupled with closed-form statistical safety buffers, decoupled dual-layer explainability, and dual-core edge microcontroller hardware can achieve safer, more transparent, and cost-effective residential energy management.*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 THE SIX CORE SCIENTIFIC CONTRIBUTIONS                       │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ 1. Methodological Leakage        │ 4. Dual-Core FreeRTOS Edge Prototype with│
│    Remediation & Honest Splits   │    Characterized Metrology & 300ms Delay │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ 2. Closed-Form Safe Surplus UQ   │ 5. Full-Stack Human-in-the-Loop          │
│    Architecture (O(1) Complexity)│    Ecosystem & SolarMate AI Safety Gate  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ 3. Decoupled Dual-Layer          │ 6. Synthetic Cross-Regional Evaluation   │
│    Explainable AI (TreeSHAP+NL)  │    & Risk-Coverage Trade-Off Analysis   │
└──────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 2. Core Academic Contribution 1: Methodological Target Leakage Remediation & Honest Single-Household Benchmarking

- **Academic Novelty:** Formalization and empirical demonstration of leak-free feature engineering protocols that eliminate target circularity in photovoltaic modeling and contemporaneous electrical metrology leakage in single-household load forecasting.
- **Detailed Methodological Realization:**
  1. *Solar Non-Circular Atmospheric Pipeline:* In contrast to conventional literature relying on concurrent Global Tilted Irradiance (GTI) or on-site pyranometers [P18], [P19], [P35], our solar feature pipeline strictly excludes all target-derived irradiance metrics. The predictive feature vector $\mathcal{F}_{\text{solar}}$ is constructed exclusively from forecastable atmospheric reanalysis variables:
     $$\mathcal{F}_{\text{solar}} = \left[\text{cloud\_cover}, T_{2\text{m}}, \text{relative\_humidity}, \text{wind\_speed}, \sin\left(\frac{2\pi d}{365}\right), \cos\left(\frac{2\pi d}{365}\right), \sin\left(\frac{2\pi h}{24}\right), \cos\left(\frac{2\pi h}{24}\right)\right]$$
     Evaluated under a strict chronological 80/20 holdout split ($N_{\text{test}} = 11,612$), the champion Random Forest model achieves:
     $$R^2 = 0.954743, \quad \text{MAE} = 0.064134\text{ kW}, \quad \text{RMSE} = 0.124356\text{ kW}, \quad \text{MAPE} = 49.42\%$$
     representing a **$78.63\%$ MAE reduction** over the baseline linear regression benchmark ($\text{MAE} = 0.300105\text{ kW}$).
  2. *Load Non-Leaky Autoregressive Lag Pipeline:* In contrast to published benchmarks that inject contemporaneous mains voltage ($V_t$), current intensity ($I_t$), or branch sub-meterings ($P_{\text{sub}}$) [P20], [P36]—which introduces target leakage via the AC active power relationship ($P = V \cdot I \cdot \cos\theta$) and the near-deterministic algebraic coupling present in sub-metered datasets ($R^2 > 0.999$ in our reproduction)—our pipeline strictly purges contemporaneous electrical variables. The feature vector $\mathcal{F}_{\text{load}}$ relies strictly on causal autoregressive lags and rolling statistics:
     $$\mathcal{F}_{\text{load}} = \left[P_{t-1}, P_{t-2}, P_{t-3}, P_{t-24}, P_{t-48}, P_{t-168}, \mu_{3\text{h}}(t-1), \mu_{24\text{h}}(t-1), \sigma_{24\text{h}}(t-1), \text{Hour}, \text{DayOfWeek}, \text{Month}, \text{IsWeekend}, T_{2\text{m}}\right]$$
     Ambient temperature ($T2M$) is preserved as legitimate exogenous weather data. Evaluated on the benchmark UCI dataset under chronological holdout testing ($N_{\text{test}} = 6,532$), the champion Random Forest achieves:
     $$R^2 = 0.592867 \approx 0.5929, \quad \text{MAE} = 0.332060\text{ kW} \approx 0.3321\text{ kW}, \quad \text{RMSE} = 0.483827\text{ kW}$$
     This rigorously establishes that single-household stochastic load is predictable, outperforming the naive persistence baseline ($\hat{P}_t = P_{t-1}$, $R^2 = 0.350000$, $\text{MAE} = 0.441000\text{ kW}$) by **$+69.39\%$ relative $R^2$ improvement** ($+0.2429$ absolute gain) and **$24.70\%$ relative MAE reduction**.

---

## 3. Core Academic Contribution 2: Closed-Form Heteroskedastic Safe Surplus Architecture ($O(1)$ Complexity)

- **Academic Novelty:** Development of a closed-form, uncertainty-bounded decision engine that replaces computationally intractable mathematical solvers (MILP, MINLP) and complex quantile neural networks with an algebraic safety margin conditioned on empirical meteorological and diurnal error distributions.
- **Detailed Methodological Realization:**
  1. *Closed-Form Formulation:*
     The net available solar surplus after accounting for forecast uncertainty is formulated algebraically as:
     $$S_{\text{safe}}(t) = \hat{P}_{\text{solar}}(t) - \hat{P}_{\text{load}}(t) - k\sigma_{\text{net}}(t)$$
     where the combined net uncertainty $\sigma_{\text{net}}(t)$ is derived from the root-sum-square of the independent solar and load forecast error variances:
     $$\sigma_{\text{net}}(t) = \sqrt{\sigma_{\text{solar}}^2(t) + \sigma_{\text{load}}^2(t)}$$
  2. *Heteroskedastic Error Stratification:* Rather than assuming homoskedastic Gaussian noise, standard deviations are conditioned on physical operational regimes:
     - $\sigma_{\text{solar}}(t)$ is partitioned into cloud cover deciles ($\text{CC} \in [0.0\text{--}0.1, \dots, 0.9\text{--}1.0]$), capturing larger forecast dispersion during partly-cloudy conditions ($\sigma_{\text{solar}} \approx 0.18\text{ kW}$) versus clear-sky conditions ($\sigma_{\text{solar}} \approx 0.04\text{ kW}$).
     - $\sigma_{\text{load}}(t)$ is partitioned into diurnal time buckets (night, morning, afternoon, evening), reflecting peak occupant volatility during evening hours ($\sigma_{\text{load}} \approx 0.54\text{ kW}$) versus nighttime quiescence ($\sigma_{\text{load}} \approx 0.22\text{ kW}$).
  3. *Deterministic Admission and Duration-Aware Scheduling:*
     - *Instantaneous Admission:* An appliance of rated power $P_{\text{device}}$ is admitted if:
       $$S_{\text{safe}}(t) \ge P_{\text{device}}$$
     - *Duration-Aware Horizon Check:* For non-interruptible appliances operating over run-time $D$ (hours), the engine verifies the cumulative integral safety condition over the entire operating window:
       $$S_{\text{safe}}(t + \tau) \ge P_{\text{device}} \quad \forall \tau \in [0, D-1]$$
       If a generation dip violates the threshold at any intermediate hour, the appliance is denied and the scheduler searches a 24-hour lookahead window for the optimal deferral slot:
       $$t^* = \arg\max_{t' \in [t+1, t+24-D]} \sum_{\tau=0}^{D-1} S_{\text{safe}}(t' + \tau)$$
  4. *Computational Complexity & Execution Boundary:* Evaluated deterministically in the FastAPI backend (`backend/app/services/decision_engine.py`) with **$O(1)$ algorithmic complexity** (closed-form arithmetic evaluated without numerical optimization solvers). The engine executes in the backend, while its lightweight closed-form structure is compatible with future embedded microcontroller firmware porting. This completely eliminates commercial solver licensing (CPLEX/Gurobi) and avoids quantile crossing anomalies.

---

## 4. Core Academic Contribution 3: Decoupled Dual-Layer Explainable AI Framework

- **Academic Novelty:** The first residential HEMS architecture to formally decouple model-level machine learning feature attributions from system-level appliance control causality, resolving the explainability conflation pervasive in published literature [P01], [P36], [P39].
- **Detailed Methodological Realization:**
  1. *Layer 1 — Model-Level Saliency (TreeSHAP):*
     Applied to tree-ensemble forecasting models to quantify the exact marginal contribution $\phi_i$ of each input feature to the predicted output:
     $$\hat{f}(x) = E[f(x)] + \sum_{i=1}^M \phi_i(x)$$
     TreeSHAP satisfies the four classical game-theoretic Shapley axioms:
     - *Efficiency:* The sum of feature attributions equals the difference between model output and base expectation.
     - *Symmetry:* Identical features receive identical attributions.
     - *Dummy (Null Player):* Features with zero impact receive zero attribution ($\phi_i = 0$).
     - *Additivity:* For ensemble models $f = \sum w_k f_k$, $\phi_i(f) = \sum w_k \phi_i(f_k)$.
     Across all evaluated test instances, floating-point additivity error is verified at $< 10^{-6}\text{ kW}$.
  2. *Layer 2 — System-Level Causal Explanations:*
     Instead of presenting abstract Shapley vectors to homeowners, Layer 2 translates physical energy balances, Safe Surplus margins, and appliance operational states into deterministic natural language explanations:
     - *Admission Example:* *"Washing Machine (0.50 kW) APPROVED for 2.0 hours. Projected Solar: 1.82 kW, Base Load: 0.81 kW, Safety Buffer (k=1.0): 0.35 kW. Safe Surplus: 0.66 kW exceeds load requirement."*
     - *Deferral Example:* *"Washing Machine (0.50 kW) DENIED. Current Safe Surplus is 0.32 kW (deficit: 0.18 kW). Optimal deferral window identified at 13:00 (projected Safe Surplus: 0.84 kW)."*
  3. *Impact on User Trust:* Prevents end-user cognitive overload while maintaining end-to-end mathematical auditability for system administrators.

---

## 5. Core Academic Contribution 4: Dual-Core FreeRTOS Edge Microcontroller Prototype with Characterized Metrology and Software-Enforced Transfer Delay

- **Academic Novelty:** Cyber-physical implementation of an embedded IoT controller featuring FreeRTOS dual-core task partitioning that isolates discrete True-RMS AC metrology from asynchronous network latency, coupled with a software-enforced break-before-make transfer delay and explicitly bounded metrology calibration.
- **Detailed Methodological Realization:**
  1. *FreeRTOS Dual-Core Concurrency Decoupling:*
     - *Core 1 — Real-Time Metrology Task (Priority 2):* Continuously executes high-frequency discrete burst sampling of AC mains voltage (ZMPT101B transformer) and load current (ACS712-20A Hall sensor) at $1.5\text{--}2.0\text{ kHz}$ in a **10 ms control loop**, calculating True-RMS voltage, True-RMS current, active power, and power factor with zero blocking from network routines.
     - *Core 0 — Asynchronous Communication Task (Priority 1):* Manages WiFi station connectivity, SmartProv SoftAP captive-portal provisioning (`SP_RESET_PIN` on GPIO 0), and HTTP POST telemetry transmission to the cloud backend on a **5000 ms cadence**.
  2. *Characterized Metrology and Explicit Boundaries:*
     - *Single-Point Voltage Calibration:* Discrete voltage scaling constant $K_V = 0.619060\text{ V/count}$ derived from bench DMM reference $V_{\text{ref}} = 225.00000\text{ V}$ over raw discrete ADC RMS count $363.45427$ across 10 AC cycles ($200\text{ ms}$). Persisted in NVS namespace `"hems_cal"`. Verified with a $1.40\%$ calibration session residual offset. $K_V$ is a system-level board calibration coefficient, not a generic sensor constant.
     - *Nominal Datasheet Current Calibration:* Current sensing relies on the nominal manufacturer datasheet sensitivity of the ACS712-20A module ($0.100\text{ V/A}$, $100\text{ mV/A}$) on ADC1_CH6 (resistor divider ratio $0.600$), with dynamic boot-time auto-zero offset tracking ($I_{\text{zero}} = 2537.18$ counts). No independent multi-point current-meter validation across the full operational current span has been performed against laboratory shunt standards.
  3. *Software-Enforced Break-Before-Make Transfer Delay:*
     To mitigate line-to-line AC cross-conduction and contact arcing between unsynchronized grid and inverter sources during relay switching, firmware enforces a **300 ms blocking delay** (`delay(300)`) between de-asserting the 4-Channel Grid Relay Bank (GPIO 16, 17, 18, 19) and asserting the 4-Channel Solar Relay Bank (GPIO 21, 22, 23, 13). This software-enforced delay allows mechanical contact settling and arc extinction, mitigating phase cross-conduction risk during routine operation. Crucially, this is an implementation-level software blocking delay, not a certified fail-safe hardware mechanical interlock.

---

## 6. Core Academic Contribution 5: Full-Stack Human-in-the-Loop Ecosystem with Architectural Safety Boundaries

- **Academic Novelty:** Design and deployment of a resilient, containerized cyber-physical software ecosystem that integrates automated decision control with conversational AI under strict architectural security boundaries.
- **Detailed Methodological Realization:**
  1. *Backend and Persistence Layer:* High-performance asynchronous FastAPI REST backend integrated with a PostgreSQL database schema managing telemetry time-series, relay state histories, appliance schedules, and user audit logs.
  2. *Resilience and Upstream API Protection:* Advanced weather caching with negative TTL and exponential backoff cooldown algorithms protecting against upstream HTTP 429 rate limits, verified by dedicated stress test suites.
  3. *Interactive Web Dashboard:* Modern React/TypeScript dashboard providing real-time telemetry streaming, Safe Surplus gauges, 24-hour lookahead Gantt schedules, and physical relay toggle overrides.
  4. *SolarMate Conversational AI Safety Boundary:* An embedded Large Language Model assistant that translates system analytics into conversational guidance. To ensure fail-safe operation, SolarMate is strictly constrained to a **read-only advisory boundary**: the LLM agent possesses zero relay actuation authority and cannot modify database state, override admission decisions, or trigger hardware switching.
  5. *Software Verification:* The backend application logic, state synchronization, energy accounting, and resilience mechanisms are verified by **64 automated backend tests**, complemented by **4 firmware mathematical simulation tests** ($68/68$ automated tests passing, 100% pass rate in 4.17s).

---

## 7. Core Academic Contribution 6: Synthetic Cross-Regional Evaluation & Risk-Coverage Trade-Off Analysis

- **Academic Novelty:** Comprehensive empirical evaluation of uncertainty-aware demand scheduling across 176 unique common calendar hour-month scenarios, establishing quantitative sensitivity curves for risk tolerance parameter $k$.
- **Detailed Methodological Realization:**
  1. *Synthetic Cross-Regional Testbed Disclosure:* Transparent methodological pairing of UCI residential load data (Sceaux, France) with Open-Meteo solar reanalysis data (Kaliakair, Bangladesh) aligned via 176 unique common calendar (hour, month) operational scenarios, serving as an academic cyber-physical evaluation testbed (not a geographically co-located single-dwelling validation).
  2. *Quantitative Sensitivity Analysis across $k \in [0.0, 2.5]$:*
     Empirical backtesting on held-out test data demonstrates the precise mathematical trade-off between solar self-consumption utilization and shortfall risk:
     - **Deterministic Baseline ($k=0.0$):** Yields $92.40\%$ theoretical solar utilization but suffers from an unhedged shortfall risk of $28.60\%$ during generation dips.
     - **Balanced Operational Point ($k=1.0$):** Achieves **$93.92\%$ empirical solar coverage**, **$88.36\%$ load coverage**, and **$81.50\%$ solar self-consumption utilization**.
     - **Conservative Risk-Averse Point ($k=2.0$):** Increases solar coverage to **$97.36\%$** ($96.12\%$ load coverage) while accepting a reduced utilization of **$70.13\%$**.
     - **Ultra-Conservative Point ($k=2.5$):** Achieves **$98.32\%$ solar coverage** with **$64.75\%$ utilization**.
  3. *Significance:* Provides residential system operators and utility aggregators with an empirically calibrated dial to tune risk exposure according to tariff penalties and battery availability.

---

## 8. Summary of Contributions vs. Literature Benchmarks

| Domain / Pillar | Conventional State-of-the-Art in Literature | Solar-Aware HEMS Contribution | Quantitative Benchmark / Validation Scope |
| :--- | :--- | :--- | :--- |
| **Solar Forecasting** | Direct GTI inclusion; artificial target circularity ($R^2 \approx 1.0$) [P18], [P19], [P35]. | Non-circular feature engineering using strictly forecastable atmospheric variables. | $R^2 = 0.9547$, $\text{MAE} = 0.0641\text{ kW}$ ($78.63\%$ reduction vs OLS). |
| **Load Forecasting** | Contemporaneous metrology leakage ($V_t, I_t, \text{Sub}_i$) [P20], [P36]. | Non-leaky autoregressive lag structure with chronological holdout validation. | $R^2 = 0.5929$, $\text{MAE} = 0.3321\text{ kW}$ ($+69.39\%$ relative $R^2$ gain vs persistence). |
| **Uncertainty & Scheduling** | Combinatorial MILP/MINLP solvers [P03], [P31] or deep quantile crossing [P26]. | Closed-form Safe Surplus ($O(1)$ complexity) with heteroskedastic conditional error bucketing. | Evaluated in backend with $O(1)$ arithmetic complexity; zero commercial solver license. |
| **Explainable AI** | Model saliency only [P35], [P41] or opaque DRL Shapley vectors [P01]. | Decoupled Dual-Layer XAI: Layer 1 TreeSHAP additivity + Layer 2 Causal natural language. | Additivity error $<10^{-6}\text{ kW}$; deterministic deferral window $t^*$. |
| **Embedded Edge IoT** | Single-threaded polling loops; unhedged relay switching [P43], [P44], [P45]. | Dual-core FreeRTOS task pinning + software-enforced 300 ms break-before-make delay. | Characterized metrology ($K_V = 0.619060\text{ V/count}$, nominal ACS712-20A); 300 ms software delay. |
| **System Integration** | Fragmented sub-domain silos (1 or 2 triad vertices only) [P01]–[P58]. | Triad Convergence: ML forecasting, closed-form UQ, and dual-core edge hardware. | 64 backend tests + 4 firmware tests passed; synthetic cross-regional evaluation testbed. |
