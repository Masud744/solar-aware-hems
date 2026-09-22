# Phase 2: Formal Research Gaps and Theoretical Synthesis

**Document ID:** `Paper/02_Research_Gap_and_Contributions/research_gaps.md`  
**Phase:** Phase 2 — Formal Research Gaps, Limitations, and Novelty Claims  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 1 & 2) and `Paper/01_Literature_Review/`  

---

## 1. The Double Stochasticity Challenge in Residential Energy Management

The global transition toward decentralized, low-carbon power systems has accelerated the integration of behind-the-meter residential photovoltaic (PV) systems. However, autonomous demand-side energy management in consumer dwellings is governed by the physical reality of **double stochasticity**:

$$\text{Net Power Flow: } P_{\text{net}}(t) = P_{\text{PV}}(t) - P_{\text{load}}(t)$$

1. **Non-Dispatchable Renewable Generation Volatility ($P_{\text{PV}}$):** Solar generation exhibits severe non-stationarity driven by shifting cloud cover, ambient temperature dynamics, diurnal solar geometry, and local atmospheric aerosol variations [P14], [P18], [P19]. Micro-climatic cloud transients can induce power drops of up to $80\%$ within minutes.
2. **Single-Household Load Stochasticity ($P_{\text{load}}$):** Unlike aggregate utility-scale or substation load curves that benefit from spatial smoothing governed by the Law of Large Numbers, individual household power demand is characterized by high Peak-to-Average Ratios (PAR), non-periodic appliance cycling, and uncoordinated occupant behavioral dynamics [P20], [P22], [P25].

To orchestrate these stochastic flows, intelligent Home Energy Management Systems (HEMS) must schedule flexible appliance loads, modulate battery storage, and coordinate grid interactions. However, an exhaustive audit of 58 peer-reviewed publications reveals critical methodological, mathematical, and cyber-physical gaps in existing literature.

---

## 2. Exhaustive Audit of the Six Research Gaps

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      THE SIX CORE RESEARCH GAPS                             │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ Gap 1: Solar Target Circularity  │ Gap 4: Explainability Conflation         │
│   (GTI Identity Inversion)       │   (Model Weights vs Control Causality)   │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ Gap 2: Load Metrology Leakage    │ Gap 5: Hardware Task Concurrency         │
│   (Contemporaneous V/I Features) │   (Single-Threaded Telemetry Blocking)   │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ Gap 3: High UQ Complexity        │ Gap 6: Relay Transfer Switching Dead-Time│
│   (Solver Overhead / Quantiles)  │   (Absence of Documented Phase Isolation)│
└──────────────────────────────────┴──────────────────────────────────────────┘
```

---

### Gap 1: Target Circularity and Pyranometer Over-Reliance in Solar Forecasting

- **Context in Literature:** A prevalent paradigm in academic solar PV forecasting involves training machine learning regressors (neural networks, support vector machines, gradient boosted trees) using on-site Global Horizontal Irradiance (GHI) or Global Tilted Irradiance (GTI) as contemporaneous input predictors [P18], [P19], [P35].
- **Specific Theoretical and Empirical Failure Mode:**
  Because photovoltaic power generation physically adheres to the photoelectric conversion formula:
  $$P_{\text{PV}} = A \cdot \eta \cdot \text{PR} \cdot \text{GTI}$$
  where $A$ is array area, $\eta$ is module efficiency, and $\text{PR}$ is performance ratio, feeding concurrent pyranometer irradiance as an input variable reduces machine learning to a trivial identity regression:
  $$f_{\text{ML}}(\text{GTI}_t, \dots) \approx (A \cdot \eta \cdot \text{PR}) \cdot \text{GTI}_t$$
  This causes severe **target circularity**, yielding artificially near-perfect metrics ($R^2 \approx 1.0000$, $\text{MAE} \approx 0.000\text{ kW}$).
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  As observed by Brester et al. (2023) [P18], real-world operational forecasting systems cannot obtain on-site pyranometer measurements in advance; they must operate strictly on forecastable Numerical Weather Prediction (NWP) parameters. In the absence of advance irradiance logs, circular models completely fail to anticipate rapid weather transitions and cloud-induced generation drops. Furthermore, installing high-precision ground pyranometers at residential sites introduces prohibitive capital expenditures ($>\$1,500$) that negate the economic justification for residential HEMS.
- **Formal Gap Statement:**
  *Existing solar forecasting benchmarks frequently rely on non-deployable on-site irradiance sensors or contemporaneous target-derived irradiance, masking true operational forecasting errors and failing to establish reproducible, leak-free feature engineering protocols based solely on forecastable meteorological variables.*
- **Proposed Architectural Resolution:**
  Establishment of a strictly non-circular solar forecasting pipeline trained exclusively on forecastable atmospheric reanalysis variables (cloud cover, 2m temperature, relative humidity, wind speed) from the Open-Meteo archive. Contemporaneous irradiance (GTI) is strictly quarantined and excluded from predictive features, yielding an honest, robust champion Random Forest model ($R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$ on $N_{\text{test}} = 11,612$).

---

### Gap 2: Contemporaneous Metrology Leakage in Single-Household Load Forecasting

- **Context in Literature:** Residential short-term load forecasting benchmarks frequently evaluate machine learning algorithms on benchmark sub-metered datasets (e.g., the UCI Individual Household Electric Power Consumption dataset) [P20], [P22], [P25], [P36].
- **Specific Theoretical and Empirical Failure Mode:**
  Multiple surveyed studies incorporate contemporaneous electrical measurements—specifically mains RMS voltage ($V_t$), current intensity ($I_t$), or branch sub-metering active power circuits ($P_{\text{sub1}}, P_{\text{sub2}}$)—directly into the predictive feature vector $\mathcal{F}_{\text{load}}$.
  To understand why this corrupts predictive validity, three distinct concepts must be separated:
  1. *Physical AC Electrical Relationship:* In alternating-current circuits, active instantaneous and average power physically adheres to:
     $$P_{\text{load}}(t) = V(t) \cdot I(t) \cdot \cos(\theta(t))$$
     where $\cos(\theta(t))$ represents the operational power factor.
  2. *Dataset-Specific Deterministic Coupling:* In benchmark sub-metered repositories such as the UCI dataset, `Global_active_power` (kW) exhibits an explicit, near-deterministic algebraic coupling with contemporaneous `Global_intensity` (total current in A) and `Voltage` ($P \approx V \cdot I / 1000$ adjusted for power factor), as well as direct additive composition with branch sub-meterings ($P_{\text{sub1}}, P_{\text{sub2}}, P_{\text{sub3}}$).
  3. *Verified Target Leakage in Empirical Benchmarks:* In our controlled reproduction experiment, feeding same-hour current intensity ($I_t$), voltage ($V_t$), and sub-metering power into a Random Forest regressor reduces time-series forecasting to an algebraic reconstruction of the target, yielding an artificially inflated $R^2 = 0.999335$ and $\text{MAE} = 0.015906\text{ kW}$.
  In an operational deployment, future current intensity ($I_{t+1}$) and future sub-meterings are physically unknowable ahead of time, rendering such leaky models entirely non-operational for forward-looking dispatch.
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  G R et al. (2025) [P20] and Forootani et al. (2022) [P25] note that invasive sub-metering current transformers are rarely installed on individual branch circuits in consumer residences. Furthermore, models relying on unshifted rolling statistics (e.g., computing a rolling mean that includes the current hour) violate temporal causality, leading to catastrophic prediction errors when deployed online.
- **Formal Gap Statement:**
  *Residential load forecasting literature suffers from pervasive data leakage caused by contemporaneous electrical metrology ($V_t, I_t$) and improper rolling-window construction, leading to misleading academic benchmark claims that cannot function in real-time edge control.*
- **Proposed Architectural Resolution:**
  Formulation of a strictly non-leaky autoregressive load feature pipeline. All contemporaneous electrical features ($V_t, I_t, \text{Sub}_i$) are purged. The predictive feature vector $\mathcal{F}_{\text{load}}$ relies strictly on causal historical autoregressive lags ($P_{t-1}, P_{t-2}, P_{t-3}, P_{t-24}, P_{t-48}, P_{t-168}$), `.shift(1)` rolling statistics ($\mu_{3\text{h}}, \mu_{24\text{h}}, \sigma_{24\text{h}}$), cyclical calendar encodings, and exogenous ambient temperature ($T2M$). Under strict chronological 80/20 holdout testing ($N_{\text{test}} = 6,532$), this leak-free Random Forest achieves $R^2 = 0.592867$ and $\text{MAE} = 0.332060\text{ kW}$, outperforming the naive persistence baseline ($R^2 = 0.350000$) by $+69.39\%$ relative $R^2$ improvement and $24.70\%$ MAE reduction. Ambient temperature ($T2M$) is legitimate exogenous meteorological information and is not target leakage.

---

### Gap 3: Computational Demands of Downstream Uncertainty Quantification on Embedded Edge Nodes

- **Context in Literature:** Recognizing the vulnerability of deterministic point forecasts, advanced HEMS literature incorporates probabilistic forecasting and Uncertainty Quantification (UQ) [P26], [P27], [P28], [P29], [P31], [P32].
- **Specific Theoretical and Empirical Failure Mode:**
  Existing UQ formulations fall into three categories, each presenting insurmountable barriers for consumer residential deployment:
  1. *Quantile Regression Neural Networks:* Independent pinball loss networks [P26], [P29] frequently suffer from **quantile crossing anomalies** ($\hat{y}_{\tau_1} > \hat{y}_{\tau_2}$ for $\tau_1 < \tau_2$), requiring non-convex monotonicity penalties and intensive GPU compute unsuitable for microcontrollers.
  2. *Conformal Prediction:* Non-parametric Adaptive Conformal Inference (ACI) [P27] provides theoretical finite-sample marginal coverage, but lacks an established mapping from prediction bands into real-time discrete multi-relay load scheduling logic.
  3. *Stochastic Programming & CVaR Optimization:* Scenario-tree models [P31], [P32] discretize probability distributions into $S$ scenarios over horizon $H$, causing the decision space to scale exponentially as $\mathcal{O}(S^H)$. Solving these formulations requires commercial desktop optimization solvers (GAMS, CPLEX, Gurobi) running on high-power workstations.
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  Sesay et al. (2026) [P26] explicitly highlight quantile crossing vulnerabilities and the need for GPU servers. Javadi et al. (2021) [P31] and van der Meer et al. (2021) [P32] demonstrate that stochastic MILP and CVaR models require solve times ranging from several seconds to minutes on desktop computers, precluding autonomous local execution on edge microcontrollers during internet or cloud outages.
- **Formal Gap Statement:**
  *Existing probabilistic energy management frameworks rely on computationally intensive mathematical programming, commercial solver licenses, or complex deep quantile networks that cannot execute on resource-constrained consumer edge hardware, preventing real-time, autonomous local risk hedging.*
- **Proposed Architectural Resolution:**
  Development of an algebraic, closed-form **Safe Surplus** decision engine governed by empirical, heteroskedastic forecast error standard deviations:
  $$S_{\text{safe}}(t) = \hat{P}_{\text{solar}}(t) - \hat{P}_{\text{load}}(t) - k\sqrt{\sigma_{\text{solar}}^2(t) + \sigma_{\text{load}}^2(t)}$$
  where $\sigma_{\text{solar}}(t)$ and $\sigma_{\text{load}}(t)$ are pre-computed empirical residual standard deviations conditioned on physical meteorological strata (cloud cover deciles) and diurnal hours. Evaluated deterministically in the FastAPI backend (`backend/app/services/decision_engine.py`) with **$O(1)$ algorithmic complexity** (closed-form arithmetic evaluated without numerical optimization solvers), this formulation eliminates mathematical optimization solvers while its lightweight closed-form structure is compatible with future microcontroller firmware porting.

---

### Gap 4: Explainability Conflation and Omission of Control Causality

- **Context in Literature:** To mitigate the opacity of machine learning and Deep Reinforcement Learning (DRL) in energy systems, recent studies integrate Explainable AI (XAI) frameworks, predominantly SHAP (Shapley Additive exPlanations) and LIME (Local Interpretable Model-agnostic Explanations) [P01], [P35], [P36], [P39], [P41], [P58].
- **Specific Theoretical and Empirical Failure Mode:**
  Existing literature exhibits a severe architectural disconnect termed **explainability conflation**:
  1. *Model-Level Saliency without Operational Grounding:* Studies apply SHAP or LIME strictly to regression models to identify global feature importances (e.g., *"Historical lag $P_{t-24}$ contributes $+0.42\text{ kW}$ to the load forecast"*) [P35], [P36], [P41]. These statistical attributions provide zero explanation for why a specific physical appliance was permitted or deferred by the downstream controller.
  2. *Direct DRL Policy Saliency:* Conversely, studies applying SHAP directly to DRL control policies [P01] output high-dimensional vectors of Shapley values for continuous state variables, which are incomprehensible to non-expert homeowners.
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  Devanathan et al. (2025) [P36] and Teixeira et al. (2025) [P39] emphasize that presenting raw mathematical feature attributions to residential occupants fails to engender trust and does not provide actionable operational guidance. When an automated controller denies an appliance, the homeowner requires causal, deterministic answers (e.g., *"Why was my load denied, how large was the solar deficit, and when can I run it?"*) rather than regression feature weights.
- **Formal Gap Statement:**
  *Energy XAI literature conflates statistical forecasting feature attributions with system-level control causality, failing to provide actionable, human-interpretable explanations that link model drivers directly to physical relay switching decisions.*
- **Proposed Architectural Resolution:**
  Implementation of a strictly decoupled **Dual-Layer XAI Architecture**:
  - *Layer 1 (Model-Level XAI):* TreeSHAP feature attributions satisfying exact Shapley additivity ($\sum \phi_i = \hat{f}(x) - E[f(x)]$), providing audited insight into meteorological and autoregressive drivers for system operators.
  - *Layer 2 (System-Level Causal XAI):* Deterministic rule-based natural language generator that translates Safe Surplus deficits ($S_{\text{safe}} < P_{\text{device}}$), conditional risk buffers ($k\sigma_{\text{net}}$), and 24-hour lookahead schedules into actionable consumer explanations with recommended deferral windows ($t^*$).

---

### Gap 5: Hardware Task Concurrency Contention in Single-Threaded Polling Loops

- **Context in Literature:** Low-cost Internet of Things (IoT) microcontroller platforms (e.g., ESP32, Arduino) are increasingly deployed as embedded smart meters and residential relay controllers [P42], [P43], [P44], [P45].
- **Specific Theoretical and Empirical Failure Mode:**
  Microcontroller firmware implementations in published literature overwhelmingly rely on the standard single-threaded Arduino polling architecture (`void loop()`). In a single-threaded loop, high-latency network operations—such as WiFi reconnection handshakes, DNS resolution, and synchronous HTTP POST telemetry requests (which require $200\text{--}3000\text{ ms}$)—stall the entire CPU.
  Because True-RMS AC metrology requires continuous, uninterrupted discrete sampling of sinusoidal voltage and current waveforms across full $20\text{ ms}$ AC cycles ($50\text{ Hz}$):
  $$V_{\text{RMS}} = \sqrt{\frac{1}{N}\sum_{n=1}^N (v[n] - V_{\text{zero}})^2}$$
  blocking network routines cause severe sample drops and timing jitter. When the CPU stalls during network waits, discrete integration is corrupted, leading to erroneous power and energy calculations.
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  In surveyed microcontroller prototypes [P43], [P45], firmware relies on single-threaded loops where synchronous network communications introduce latency; no implementation detail regarding task concurrency was identified in the inspected material. While some studies attempt to mitigate this by deploying Linux single-board computers (Raspberry Pi) [P08], [P51], full operating systems introduce significant quiescent power consumption ($3\text{--}7\text{ W}$) and non-deterministic kernel scheduling jitter.
- **Formal Gap Statement:**
  *Microcontroller-based HEMS prototypes suffer from execution concurrency contention in single-threaded firmware, where blocking network communication stalls high-frequency analog metrology and disrupts continuous True-RMS AC integration.*
- **Proposed Architectural Resolution:**
  Implementation of a **Dual-Core FreeRTOS Firmware Architecture** on an ESP32 microcontroller:
  - *Core 1 (Real-Time Metrology Task, Priority 2):* Dedicated strictly to continuous True-RMS voltage (ZMPT101B) and current (ACS712-20A) burst sampling in a **10 ms** periodic loop, achieving continuous discrete integration with zero blocking interference from network routines.
  - *Core 0 (Asynchronous Telemetry Task, Priority 1):* Dedicated to WiFi connection management, SmartProv SoftAP captive-portal provisioning, and HTTP POST telemetry transmission on a **5000 ms** cadence.

---

### Gap 6: Absence of Documented Phase-Isolation Transfer Delays in Dual-Source Switching

- **Context in Literature:** Cyber-physical residential energy management systems frequently deploy multi-channel relay modules to switch heavy household circuits between primary grid mains and auxiliary solar inverter sources [P42], [P44], [P45], [P47].
- **Specific Theoretical and Empirical Failure Mode:**
  Published IoT relay controllers frequently command instantaneous relay toggling between grid and solar circuits without enforcing break-before-make transfer switching dead-times in firmware.
  Electromechanical relay armatures possess mechanical transit times ($5\text{--}15\text{ ms}$) and generate electrical contact arcing upon opening under inductive loads. If a solar relay is energized before the grid relay contact arc has completely extinguished, an instantaneous line-to-line AC cross-conduction occurs between the unsynchronized grid and inverter phases:
  $$V_{\text{fault}}(t) = V_{\text{grid}}(t) - V_{\text{inverter}}(t)$$
  This out-of-phase short-circuit induces severe current surges, welded relay contacts, inverter bridge destruction, and upstream circuit breaker tripping.
- **Corpus-Bounded Evidence & Author-Stated Limitations:**
  In surveyed dual-source microcontroller prototypes [P42], [P44], [P45], no implementation detail regarding transfer switching dead-times or phase-isolation interlocks was identified in the inspected material.
- **Formal Gap Statement:**
  *Published dual-source IoT relay testbeds omit documented break-before-make transfer switching delays in firmware, creating critical operational risks of contact arcing, AC cross-conduction, and inverter damage during grid-to-solar transfers.*
- **Proposed Architectural Resolution:**
  Implementation of a software-enforced **300 ms break-before-make blocking delay** (`delay(300)`) in ESP32 firmware between de-asserting the 4-channel Grid relay bank (GPIO 16, 17, 18, 19) and asserting the 4-channel Solar relay bank (GPIO 21, 22, 23, 13). This delay is explicitly an implementation-level software blocking delay that allows relay armatures to settle and contact arcs to extinguish before opposing contacts energize, mitigating cross-conduction risk during transfer switching (explicitly disclosed as an implementation software delay rather than a certified hardware safety interlock).

---

## 3. The Triad Convergence Gap: The Cyber-Physical-Predictive Disconnect

A comprehensive meta-synthesis of the 58-paper literature corpus reveals that existing studies operate almost exclusively within isolated sub-domains. We formalize this fundamental literature failure mode as the **Triad Convergence Gap**.

```
                           [ Vertex 1 ]
                    LEAK-FREE PREDICTIVE AI
                   (Non-Circular Solar & Load)
                             ▲     ▲
                            /       \
                           /         \
   [ Literature Disconnect ]         [ Literature Disconnect ]
                         /             \
                        /   OUR WORK:   \
                       /   CONVERGED     \
                      ▼   TRIAD HEMS      ▼
           [ Vertex 2 ] ◄───────────────► [ Vertex 3 ]
       CLOSED-FORM UQ &               EMBEDDED EDGE IOT
     CAUSAL EXPLAINABILITY           & SAFE RELAY CONTROL
    (O(1) Safe Surplus, kσ)        (Dual-Core FreeRTOS, 300ms)
```

### The Three Necessary Vertices of Viable Residential HEMS:
1. **Vertex 1 — Leak-Free Predictive Intelligence:** High-accuracy machine learning forecasting models formulated without target circularity (no contemporaneous GTI) and without metrology leakage (no contemporaneous $V_t, I_t$), evaluated under chronological holdout testing.
2. **Vertex 2 — Computationally Feasible, Risk-Calibrated Optimization & Causal XAI:** Uncertainty-bounded appliance admission that executes in closed algebraic form ($O(1)$ arithmetic complexity) without commercial solver licenses, coupled with decoupled causal explanations for end-user trust.
3. **Vertex 3 — Real-Time, Concurrency-Safe Embedded Edge Hardware:** Embedded microcontroller implementations with dual-core task isolation preventing telemetry blocking from stalling metrology, and physical relay transfer switching delays mitigating AC cross-conduction.

### Corpus Distribution Across the Triad Vertices ($N=58$):

| Triad Domain Coverage | Representative Literature Studies | Critical Missing Vertex / Architectural Vulnerability |
| :--- | :--- | :--- |
| **Vertex 1 Only** (Predictive AI Only) | Brester [P18], Hossain [P19], G R [P20], Irankhah [P22], Forootani [P25], Aduama [P35] | No downstream control, no uncertainty quantification, no physical hardware realization. |
| **Vertex 2 Only** (Theoretical Optimization / UQ) | Sesay [P26], Suresh [P27], Cai [P28], Yang [P29], Javadi [P31], van der Meer [P32] | Pure simulation; relies on desktop solvers (CPLEX/Gurobi); assumes idealized point forecasts or ignores hardware execution. |
| **Vertex 3 Only** (Hardware / IoT Prototyping) | Pradhan [P43], Singh [P44], Siregar [P45], Franco [P47] | No predictive capability; no uncertainty awareness; single-threaded firmware loops without phase isolation dead-times. |
| **Vertices 1 + 2** (Predictive + Optimization / XAI) | Nejati Amiri [P01], Yuan [P03], Real [P04], Dinh [P11], Teixeira [P39] | Offline desktop simulations; assumes idealized instantaneous actuators; zero embedded microcontroller or firmware testing. |
| **Vertices 1 + 3** (Predictive + IoT Hardware) | Devanathan [P02], Huy [P08], de Sousa [P42], Rivkin [P51] | Deterministic point-forecast scheduling without statistical risk buffers; high-cost SBCs (Raspberry Pi) or single-threaded MCU loops. |
| **Vertices 2 + 3** (Optimization + Hardware) | Wang [P06], Nakıp [P07] | Opaque rule sets without model-level XAI; lacks leak-free forecasting integration; no break-before-make phase isolation. |
| **TRIAD CONVERGENCE** (Vertices 1 + 2 + 3) | **Proposed Solar-Aware HEMS Framework** | **Within the reviewed 58-paper corpus, no study was identified that unifies leak-free ML forecasting, closed-form UQ, decoupled XAI, and dual-core edge hardware into an integrated cyber-physical architecture.** |

---

## 4. Section Summary

The systematic formulation of Gaps 1 through 6 and the Triad Convergence Gap establishes the formal academic foundation for the proposed research. Rather than proposing incremental improvements to isolated algorithmic or hardware blocks, this study delivers a unified, cyber-physically validated framework that directly overcomes each identified failure mode.
