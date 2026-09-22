# Phase 4 Verification Report: Experimental Setup and Data Provenance

**Document ID:** `Paper/04_Experimental_Setup/phase4_verification_report.md`  
**Phase:** Phase 4 — Experimental Setup and Data Provenance  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Verification Date:** September 2026  
**Status:** Complete — **Hard Stop: Awaiting Supervisor Approval**  

---

## 1. Executive Summary & Verification Scope

In strict compliance with `AGENTS.md`, `BUILD_PLAN.md`, and the Paper Workspace Operating Rules (`Paper/README.md`), this verification report documents the completion of **Phase 4: Experimental Setup and Data Provenance** for the IEEE journal manuscript.

Phase 4 establishes the empirical foundations of the research, documenting dataset provenance, gap-aware data cleaning, target leakage elimination, physical rooftop PV modeling, embedded edge testbed engineering, FreeRTOS dual-core metrology, machine learning hyperparameters, TreeSHAP explainer verification, and heteroskedastic uncertainty calibration protocols.

### Phase 4 Deliverables Completed:
1. **[`dataset_provenance_and_preprocessing.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/04_Experimental_Setup/dataset_provenance_and_preprocessing.md):**
   - Detailed specification of the UCI household electrical load dataset (Sceaux, France; $34,168$ raw records, $32,656$ clean records) and Open-Meteo solar meteorological reanalysis archive (Kaliakair, Bangladesh; $58,056$ quasi-hourly records across 2,419 days).
   - Complete gap inventory detailing 8 multi-hour missing data outages ($421\text{ missing hours}$ total, 123-hour maximum outage) and gap-aware filtering without artificial flatline interpolation.
   - Rigorous elimination of contemporaneous metrology leakage ($V_t, I_t$) and unshifted rolling lookaheads from load data, yielding the authoritative 16-feature vector ($\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$).
   - Formulation of the 5-panel monocrystalline rooftop solar installation ($A_{\text{panel}} = 2.42\text{ m}^2$, $A_{\text{total}} = 12.10\text{ m}^2$, $P_{\text{peak}} = 2.115\text{ kWp}$) and strict exclusion of GTI, establishing the non-circular feature vector ($\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$).
   - Methodological disclosure of the synthetic cross-regional pairing across 176 common calendar scenarios and the short-history cold-start fallback profile $\bar{\mathcal{F}}_{\text{fallback}}$.

2. **[`hardware_testbed_specification.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/04_Experimental_Setup/hardware_testbed_specification.md):**
   - Detailed specification of the ESP32 DevKit V1 physical edge node with dedicated ADC1 pinout allocation (GPIO 35 for ZMPT101B, GPIO 34 for ACS712-20A), avoiding the ESP32 ADC2/Wi-Fi hardware conflict.
   - Dual-core FreeRTOS task concurrency: Core 1 metrology (`loopTask`, priority 1, $200\text{ ms}$ burst at $1.5\text{--}2.0\text{ kHz}$ every $1000\text{ ms}$, 40 ms switch debounce) and Core 0 networking (`networkTask`, priority 1, 1500 ms poll, 3000 ms telemetry push) separate workload execution (without guaranteeing complete system-level isolation), synchronized via inter-core queue depth 16 (`remoteCommandQueue`) and binary mutex (`telemetryMutex`).
   - Signal conditioning safety analysis showing that the theoretical $10\text{k}\Omega / 15\text{k}\Omega$ resistor divider ($\alpha = 0.600$) steps down an assumed $5.0\text{ V}$ ACS712-20A peak to $3.00\text{ V} \le 3.30\text{ V}$ at the MCU pin, conditional on the stated maximum sensor-output assumption and verified divider circuit (without claiming experimentally proven physical overvoltage protection).
   - Discrete sampled RMS voltage and current integration equations with NVS flash parameter persistence (`"hems_cal"`).
   - Four-stage calibration status: empirical DC zero offsets ($V_{\text{zero}} = 2539.65, I_{\text{zero}} = 2537.18$), single-point voltage scaling factor ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual against 225.0V DMM reference), nominal ACS712-20A current sensitivity ($0.100\text{ V/A}$), and bench validation with Walton WTF9M3 fan ($60\text{ W rated}, 226\text{ V}, 0.28\text{ A}, S = 63.28\text{ VA}$).
   - 8-relay dual-bank matrix with software-enforced $300\text{ ms}$ break-before-make delay (`delay(300)` on Core 1), with explicit safety disclosure noting it is not a certified mechanical ATS.

3. **[`model_training_and_hyperparameters.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/04_Experimental_Setup/model_training_and_hyperparameters.md):**
   - Forecasting horizon taxonomy: direct multi-hour solar forecasting vs. offline one-step ahead ($h=1\text{ h}$) load benchmarking vs. operational recursive multi-step load rollout and 24-hour discrete scheduling search ($O(|\mathcal{T}| \cdot n_{\text{hours}})$).
   - Algorithmic formulations and exact hyperparameter tables for Random Forest (Champion), XGBoost, SVR, CART, OLS, and Naive Persistence baselines.
   - TreeSHAP explainer verification: exact mathematical additivity confirmed ($\Delta_{\text{additivity}} = 5.42 \times 10^{-14}\text{ kW}$ solar, $1.71 \times 10^{-13}\text{ kW}$ load, well below $10^{-6}\text{ kW}$ numerical tolerance); physical effect directions verified (cloud cover inhibitory, previous hour load positive persistence).
   - Condition-stratified heteroskedastic uncertainty quantification: solar cloud-cover standard deviations ($0.0851\text{ kW}$ clear sky to $0.1386\text{ kW}$ overcast) and load diurnal clock-hour standard deviations ($0.2662\text{ kW}$ night to $0.6075\text{ kW}$ evening).
   - Safety factor multiplier sweep ($k \in [0.5, 2.5]$) and empirical justification for the selected conservative operating point ($k = 1.0$).

4. **[`evaluation_metrics_and_protocols.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/04_Experimental_Setup/evaluation_metrics_and_protocols.md):**
   - Mathematical definitions of regression metrics: $R^2$, MAE, RMSE, and active-filtered MAPE ($\ge 0.05\text{ kW}$ for solar, $\ge 0.10\text{ kW}$ for load).
   - Uncertainty quantification metrics: empirical solar coverage rate, conservative load coverage rate, solar self-consumption utilization rate, and the Monotonicity Law.
   - Level-3 operational decision engine confusion matrix (Correct-ALLOW, Incorrect-ALLOW, Correct-DENY, Incorrect-DENY) and the core objective of Incorrect-ALLOW minimization.
   - Domestic electricity accounting under Bangladesh flat residential Tier-3 tariff ($7.50\text{ BDT/kWh}$).
   - Computational complexity profiling proving closed-form $O(1)$ Safe Surplus evaluation and real-time FreeRTOS timing boundaries.

5. **[`phase4_verification_report.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/04_Experimental_Setup/phase4_verification_report.md) (This Document):**
   - Phase 4 Verification Gate checklist, 5-stage claim traceability matrix, parameter alignment tables, and hard stop declaration.

---

## 2. Phase 4 Verification Gate Checklist

In strict adherence to `BUILD_PLAN.md` §PHASE 4 Verification Gate and `AGENTS.md` guidelines, all items have been systematically checked and verified:

- [x] **Gate 1: Monotonic Growth of Empirical Coverage Rate with Increasing $k$**
  - *Verification Result:* Confirmed strictly monotonic growth across all tested safety multiplier steps ($k = 0.5 \to 2.5$):
    - Solar Coverage: $89.12\% \; (k=0.5) \longrightarrow 93.92\% \; (k=1.0) \longrightarrow 96.05\% \; (k=1.5) \longrightarrow 97.36\% \; (k=2.0) \longrightarrow 98.32\% \; (k=2.5)$.
    - Load Coverage: $79.04\% \; (k=0.5) \longrightarrow 88.36\% \; (k=1.0) \longrightarrow 93.17\% \; (k=1.5) \longrightarrow 96.19\% \; (k=2.0) \longrightarrow 97.96\% \; (k=2.5)$.
    - Solar Utilization: Strictly monotonic decrease from $87.83\%$ ($k=0.5$) down to $64.75\%$ ($k=2.5$).
  - *Status:* **PASSED.**

- [x] **Gate 2: Non-Zero, Physically Sane Residual Standard Deviations ($\sigma_{\text{solar}}, \sigma_{\text{load}}$)**
  - *Verification Result:* Residual standard deviations evaluated on held-out test predictions are strictly non-zero and align with typical physical magnitudes:
    - Solar: Global $\sigma_{\text{solar}} = 0.1225\text{ kW}$ ($\text{RMSE} = 0.1244\text{ kW}$, mean daylight generation $0.8124\text{ kW}$);
    - Load: Global $\sigma_{\text{load}} = 0.4831\text{ kW}$ ($\text{RMSE} = 0.4838\text{ kW}$, mean active power $1.1092\text{ kW}$);
    - Neither value collapses to $\sim 0$ (confirming held-out out-of-sample residuals, not overfitted training residuals) nor exhibits runaway magnitude.
  - *Status:* **PASSED.**

- [x] **Gate 3: Meaningful Condition Stratification in Bucketed $\sigma$**
  - *Verification Result:* Confirmed that harder-to-predict, volatile condition buckets exhibit significantly higher standard deviation than predictable regimes:
    - Solar Stratification: Overcast skies exhibit $\sigma = 0.1386\text{ kW}$ ($+63\%$ higher than clear sky $\sigma = 0.0851\text{ kW}$);
    - Load Stratification: Evening peak hours exhibit $\sigma = 0.6075\text{ kW}$ ($2.28\times$ higher than nighttime baseload $\sigma = 0.2662\text{ kW}$).
  - *Status:* **PASSED.**

- [x] **Gate 4: Justified Selection of Operating Point ($k = 1.0$)**
  - *Verification Result:* Explicitly documented one-line justification:
    > *$k = 1.0$ is chosen as the conservative operating point because stepping from $k=0.5$ to $k=1.0$ yields the largest marginal coverage gain ($+4.80\text{ pp}$ solar, $+9.32\text{ pp}$ load) relative to utilization cost ($-6.33\text{ pp}$), delivering robust $93.92\%$ solar and $88.36\%$ load coverage while retaining $81.50\%$ solar self-consumption utilization.*
  - *Status:* **PASSED.**

- [x] **Gate 5: TreeSHAP Axiomatic Consistency & Mathematical Sanity**
  - *Verification Result:* Verified exact additivity:
    - Solar RF: $\max |f(\mathbf{x}) - (\phi_0 + \sum \phi_i)| = 5.42 \times 10^{-14}\text{ kW} < 10^{-6}\text{ kW}$;
    - Load RF: $\max |f(\mathbf{x}) - (\phi_0 + \sum \phi_i)| = 1.71 \times 10^{-13}\text{ kW} < 10^{-6}\text{ kW}$;
    - Effect directions physically verified (cloud cover inhibitory, humidity negative, previous load positive persistence).
  - *Status:* **PASSED.**

- [x] **Gate 6: Strict Preservation of Frozen Benchmarks & Repository Facts**
  - *Verification Result:*
    - Solar Champion (Random Forest, $N=11,612$): $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, $\text{RMSE} = 0.124356\text{ kW}$, $\text{MAPE} = 49.42\%$;
    - Load Champion (Random Forest, $N=6,532$): $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$, $\text{RMSE} = 0.483827\text{ kW}$, $\text{MAPE} = 42.59\%$;
    - Load Persistence Baseline: $R^2 = 0.350000$, $\text{MAE} = 0.441000\text{ kW}$ ($+69.39\%$ relative RF gain);
    - Feature counts: Solar $\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$, Load $\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$;
    - Solar Array Geometry: $N_{\text{panels}} = 5$, $A_{\text{panel}} = 2.42\text{ m}^2$, $A_{\text{total}} = 12.10\text{ m}^2$, $P_{\text{peak}} = 2.115\text{ kWp}$;
    - Terminology: "Discrete sampled RMS estimation" used throughout.
  - *Status:* **PASSED.**

- [x] **Gate 7: Hardware Metrology and Boundary Disclosures Maintained**
  - *Verification Result:*
    - Resistor divider calculation confirmed: $5.0\text{ V} \times 0.600 = 3.00\text{ V} \le 3.30\text{ V}$, explicitly conditional on the stated maximum sensor-output assumption and verified divider circuit (without claiming experimentally proven physical protection);
    - ADC1 exclusive allocation confirmed (GPIO 34 current, GPIO 35 voltage), avoiding the ESP32 ADC2/Wi-Fi hardware conflict; task pinning separates workload execution without claiming complete system-level isolation;
    - Single-point voltage calibration factor ($K_V = 0.619060\text{ V/count}$, $+1.40\%$ residual offset);
    - Current sensitivity disclosed as nominal ($0.100\text{ V/A}$) without multi-point calibration;
    - Software 300 ms break-before-make delay (`delay(300)`) disclosed as not a certified ATS;
    - Safe Surplus complexity characterized as closed-form $O(1)$ in the backend; empirical "<1 ms" omitted.
  - *Status:* **PASSED.**

- [x] **Gate 8: Zero Changes to Core Code, Datasets, Models, Firmware, or Thesis Files**
  - *Verification Result:* No files outside `Paper/04_Experimental_Setup/` were modified. Working tree confirms original pre-existing state preserved.
  - *Status:* **PASSED.**

---

## 3. End-to-End 5-Stage Claim Traceability Matrix for Phase 4

$$\text{CLAIM} \longrightarrow \text{SOURCE / DATA} \longrightarrow \text{METHOD / IMPLEMENTATION} \longrightarrow \text{EVIDENCE / RESULT} \longrightarrow \text{PAPER STATEMENT}$$

| Item # | Core Scientific Claim | Primary Source / Dataset | Method / Implementation Path | Quantitative Evidence / Test Result | Paper Statement & Academic Scope |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **C01** | UCI load data cleaned without flatline interpolation across 8 outages. | Raw UCI household load dataset (`main_data.csv`, 34,168 hourly rows). | Continuous hourly reindexing, NaN propagation, 168-hour boundary dropping. | $N_{\text{clean}} = 32,656$ non-interpolated records ($94.4\%$ retention); 421 missing hours filtered. | Gap-aware cleaning drops NaN cross-gap rows rather than fabricating artificial linear or forward-filled flatlines. |
| **C02** | Chronological 80/20 partitioning eliminates future-lookahead data leakage. | Cleaned UCI load ($32,656$) and Open-Meteo solar ($58,056$) datasets. | Forward sequential split with `shuffle=False` (`train_test_split`). | Solar: $46,444$ train / $11,612$ test; Load: $26,124$ train / $6,532$ test. Strict chronological ordering. | Strict chronological train/test partitioning provides chronological out-of-sample evaluation without intentional train/test temporal shuffling, preventing lookahead leakage while preserving the distinction between leakage prevention and generalization guarantees. |
| **C03** | Passive divider steps down assumed 5V ACS712 output to 3.00V at ESP32 pin. | Allegro ACS712-20A datasheet and ESP32 silicon electrical characteristics. | Passive resistor network: $R_1 = 10\text{ k}\Omega, R_2 = 15\text{ k}\Omega \to \alpha = 0.600$. | $V_{\text{pin, max}} = 5.00\text{ V} \times 0.600 = 3.00\text{ V} \le 3.30\text{ V}$; theoretical headroom $0.30\text{ V}$. Passed firmware pytest. | Passive resistor network steps down the sensor output to a calculated $3.00\text{ V}$, conditional on the stated $5.00\text{ V}$ maximum output assumption and verified divider circuit, rather than experimentally proven physical protection. |
| **C04** | Dual-core FreeRTOS task partitioning separates workloads; ADC1 avoids Wi-Fi ADC2 conflict. | ESP32 DevKit V1 Xtensa LX6 dual-core architecture. | Core 1: $200\text{ ms}$ burst RMS sampling @ 1.5–2.0 kHz; Core 0: HTTP push ($3\text{ s}$) and poll ($1.5\text{ s}$). Dedicated ADC1 channels (GPIO 34, 35). | 4/4 firmware simulation tests passed; queue depth 16; zero ADC contention on ADC1 (GPIO 34, 35). | FreeRTOS dual-core task pinning separates metrology execution from network tasks (though without guaranteeing complete system-level isolation), while dedicated ADC1 allocation avoids the ESP32 ADC2/Wi-Fi hardware conflict. |
| **C05** | TreeSHAP explainer satisfies exact local accuracy within floating tolerance. | Champion Solar and Load Random Forest model binaries. | `shap.TreeExplainer` evaluating test predictions against base value $\mathbb{E}[f(X)]$. | Solar max additivity error: $5.42 \times 10^{-14}\text{ kW}$; Load max error: $1.71 \times 10^{-13}\text{ kW}$ ($<10^{-6}\text{ kW}$). | TreeSHAP guarantees exact mathematical additivity between baseline expectations and local feature contributions. |
| **C06** | Condition-stratified $\sigma$ captures heteroskedastic atmospheric and demand variance. | Held-out test residuals ($11,612$ solar, $6,532$ load). | Solar stratified by cloud cover (3 buckets); Load stratified by clock hour (4 blocks). | Overcast solar $\sigma = 0.1386\text{ kW}$ ($+63\%$ vs clear sky $0.0851\text{ kW}$); Evening load $\sigma = 0.6075\text{ kW}$ ($2.28\times$ vs night). | Condition-bucketed uncertainty buffers dynamically capture heteroskedastic volatility across weather and diurnal regimes. |
| **C07** | Safety factor multiplier $k$ exhibits strictly monotonic coverage growth. | Condition-bucketed Safe Surplus evaluated across $k \in [0.5, 2.5]$. | Empirical coverage evaluated on held-out residual distributions. | Solar coverage grows $89.12\% \to 98.32\%$; Load coverage grows $79.04\% \to 97.96\%$; Utilization drops $87.83\% \to 64.75\%$. | Monotonic coverage scaling enables deterministic tuning of the safety-utilization trade-off in residential energy scheduling. |
| **C08** | Offline load benchmarking evaluates 1-step ahead, distinct from operational rollout. | Test set predictions ($N=6,532$) vs. backend recursive rollout service. | Offline benchmarking uses ground-truth lags; operational rollout recursively feeds $\hat{P}$. | Offline RF achieves $R^2 = 0.5929$; recursive rollout and 24-h discrete search explicitly disclosed. | Offline metrics reflect strictly one-step autoregressive accuracy; operational 24-h scheduling employs recursive rollout. |

---

## 4. Itemized Summary of Experimental Parameters and Repository Alignment

| Experimental Parameter | Value in Phase 4 Deliverables | Authoritative Repository Source | Alignment Status |
| :--- | :--- | :--- | :---: |
| **Solar Raw Dataset** | $58,056$ rows (2020–2026, 2,419 days) | `Dataset/kaliakair_openmeteo_solar_raw.csv` | **EXACT MATCH** |
| **Solar Train / Test Split** | Train: $46,444$ ($80\%$) / Test: $11,612$ ($20\%$) | `ml/solar/scripts/train_solar_models.py` | **EXACT MATCH** |
| **Load Raw / Clean Dataset** | Raw: $34,168$ rows / Clean: $32,656$ rows | `Dataset/main_data.csv`, `load_processed_clean.csv` | **EXACT MATCH** |
| **Load Train / Test Split** | Train: $26,124$ ($80\%$) / Test: $6,532$ ($20\%$) | `ml/load/scripts/train_load_models.py` | **EXACT MATCH** |
| **Load Outage Gaps** | 8 discrete gaps $\ge 12\text{ h}$, 421 missing hours | `Project_Report/final_report/chapters/Chapter3.tex` | **EXACT MATCH** |
| **Load Feature Dimensionality** | $\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$ (16 features) | `ml/load/scripts/train_load_models.py:318` | **EXACT MATCH** |
| **Solar Feature Dimensionality** | $\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$ (7 features, GTI purged) | `ml/solar/scripts/train_solar_models.py:171` | **EXACT MATCH** |
| **Solar Panel Area** | $A_{\text{panel}} = 2.42\text{ m}^2$, $A_{\text{total}} = 12.10\text{ m}^2$ | `PROJECT_MASTER_CONTEXT.md` §3.1 | **EXACT MATCH** |
| **Solar Peak DC Capacity** | $P_{\text{peak}} = 2.115\text{ kWp}$ ($N_{\text{panels}} = 5$) | `PROJECT_MASTER_CONTEXT.md` §3.1 | **EXACT MATCH** |
| **Solar RF Benchmark** | $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$ | `ml/solar/results/comparison_table.csv` | **EXACT MATCH** |
| **Load RF Benchmark** | $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$ | `ml/load/results/comparison_table.csv` | **EXACT MATCH** |
| **Load Persistence Benchmark** | $R^2 = 0.350000$, $\text{MAE} = 0.441000\text{ kW}$ | `ml/load/README.md:73` | **EXACT MATCH** |
| **Voltage Scale Factor** | $K_V = 0.619060\text{ V/count}$ ($1.40\%$ residual) | `firmware/config.h`, Supabase row #836 | **EXACT MATCH** |
| **Current Nominal Sensitivity** | $S_I = 0.100\text{ V/A}$ (ACS712-20A nominal) | `firmware/config.h`, ACS712 datasheet | **EXACT MATCH** |
| **Relay BBM Dead-Time** | $300\text{ ms}$ software blocking delay | `firmware/firmware.ino:318` (`delay(300)`) | **EXACT MATCH** |
| **FreeRTOS Concurrency** | Core 1 Priority 1, Core 0 Priority 1 | `firmware/firmware.ino:713-721` | **EXACT MATCH** |
| **Sampling Window / Cadence** | $200\text{ ms}$ window / $1000\text{ ms}$ burst cadence | `firmware/electricity_meter.cpp` | **EXACT MATCH** |
| **Telemetry Cadence / Timeout**| Ingest: $3000\text{ ms}$, Poll: $1500\text{ ms}$, TO: $1000\text{ ms}$ | `firmware/config.h:48-49` | **EXACT MATCH** |
| **Safe Surplus Complexity** | $\mathcal{O}(1)$ closed-form algebraic evaluation | `backend/app/services/decision_engine.py` | **EXACT MATCH** |
| **Anti-Chatter Protection** | $T_{\text{dwell}} = 180\text{ s}$, $\Delta P_{\text{hyst}} = 50\text{ W}$ | `backend/app/services/decision_engine.py` | **EXACT MATCH** |

---

## 5. Working Tree and Deliverable File Inventory

### 5.1 Phase 4 Deliverable Files in `Paper/04_Experimental_Setup/`:
```
Paper/04_Experimental_Setup/
├── dataset_provenance_and_preprocessing.md      (19,450 bytes)
├── hardware_testbed_specification.md            (18,720 bytes)
├── model_training_and_hyperparameters.md        (17,840 bytes)
├── evaluation_metrics_and_protocols.md          (14,980 bytes)
└── phase4_verification_report.md                (This file)
```

### 5.2 Working Tree Status:
- Current Commit HEAD: `4d2d815d3987560bb7e79421d18a624148e1b55a` (Phase 3 Deliverables Committed).
- Unstaged files preserved in original state: `firmware/config.h`, `firmware/firmware.ino` (pre-existing Sept 15 changes, untouched).
- All five Phase 4 deliverable files remain **untracked** in git under `Paper/04_Experimental_Setup/`.
- Zero changes to datasets, ML model binaries, backend code, firmware source code, or thesis reports.

---

## 6. Hard Stop and Supervisor Review Request

In strict compliance with `AGENTS.md` and `BUILD_PLAN.md`:

> **PHASE 4 COMPLETE — HARD STOP ENFORCED**  
> All five Phase 4 deliverables have been generated in `Paper/04_Experimental_Setup/`.
> Every item in the Phase 4 Verification Gate has been systematically verified and confirmed passing.
>
> All five Phase 4 files remain untracked in git. No modifications were made to datasets, models, backend, firmware, or thesis files.
>
> **Execution is now completely suspended.** Antigravity will NOT proceed to Phase 5 (Results and Discussion) until explicit supervisor review, confirmation, and administrative instructions (such as git commit instructions) are received.
