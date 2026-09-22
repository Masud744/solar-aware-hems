# Predictive Machine Learning Forecasting Results and Comparative Benchmarking

**Document ID:** `Paper/05_Results_and_Discussion/predictive_forecasting_results.md`  
**Phase:** Phase 5 — Results and Discussion  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Executive Overview and Evaluation Protocol

This section reports the empirical predictive performance of candidate supervised machine learning algorithms across both solar photovoltaic generation and household electrical load demand. 

In strict accordance with the experimental protocols defined in Phase 4:
1. **Strict Chronological Holdout Splitting:** Models are evaluated on forward-chronological test partitions without shuffling (`shuffle=False`), ensuring out-of-sample forward evaluation;
2. **Leakage-Free Non-Circular Feature Sets:** Direct irradiance ($\text{GTI}$) is quarantined from solar models ($\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$), and contemporaneous physical metrology ($V_t, I_t$) as well as unshifted rolling windows are purged from load models ($\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$);
3. **Horizon and Execution Distinction:** Solar forecasts represent direct 24-hour ahead predictions driven by numerical weather features; offline load metrics represent strictly **one-step-ahead ($h = 1\text{ h}$)** predictions evaluated with ground-truth historical lags, distinct from operational recursive multi-step scheduling rollouts;
4. **Baseline Discipline:** Algorithms are rigorously benchmarked against linear models, single decision trees, physical formulas, naive persistence baselines, and intentionally constructed leaky baselines to quantify genuine predictive gains.

---

## 2. Solar Photovoltaic Generation Forecasting Performance

### 2.1 Benchmark Architecture Evaluation
The solar forecasting models were evaluated on the chronological holdout test partition ($N_{\text{test}} = 11,612$ hourly records spanning April 19, 2025 to August 15, 2026 for Kaliakair, Bangladesh). Input features consist strictly of non-circular meteorological and astronomical variables:
$$\mathbf{x}_{\text{solar}}(t) = \begin{bmatrix} \text{cloud\_cover}(t), \text{temperature}(t), \text{relative\_humidity}(t), \text{wind\_speed}(t), h_t, m_t, \text{day\_of\_year}_t \end{bmatrix}^T \in \mathbb{R}^7$$

Table 1 presents the comparative benchmark metrics across all evaluated architectures on the $2.115\text{ kWp}$ modeled rooftop array ($N_{\text{panels}} = 5$, $A_{\text{total}} = 12.10\text{ m}^2$).

### Table 1: Solar Generation Forecasting Performance Benchmark ($N_{\text{test}} = 11,612$)

| Model Architecture | MAE (kW) | RMSE (kW) | $R^2$ | MAPE (%) | Model Role / Evaluation Characterization |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Disclosed Leakage & Theoretical Baselines:** | | | | | |
| RF Leaky Baseline ($\text{GTI}$ Included) | $0.000068$ | $0.000126$ | $1.000000$ | $0.03\%$ | Target circularity: memorizes $P_{\text{PV}} = \text{GTI} \times 0.002115$ |
| Physical Deterministic Formula | $0.000000$ | $0.000000$ | $1.000000$ | $0.00\%$ | Theoretical identity: ground-truth target definition |
| **Corrected Non-Circular Models:** | | | | | |
| **Random Forest (Champion)** | **$0.064134$** | **$0.124356$** | **$0.954743$** | **$49.42\%$** | **Ensemble Bagging: Lowest MAE and RMSE; champion model** |
| Extreme Gradient Boosting (XGBoost) | $0.069685$ | $0.126488$ | $0.953178$ | $53.67\%$ | Gradient Boosting: Competitive; slightly higher transition variance |
| Decision Tree Regressor (CART) | $0.068377$ | $0.132579$ | $0.948560$ | $51.51\%$ | Single Tree: Fast inference; lacks ensemble variance reduction |
| Support Vector Regressor (SVR) | $0.092235$ | $0.151626$ | $0.932718$ | $93.71\%$ | RBF Kernel: Smooth diurnal envelope; sluggish on cloud spikes |
| Linear Regression (OLS Baseline) | $0.300105$ | $0.383743$ | $0.569044$ | $308.46\%$ | Linear Baseline: Inadequate for non-linear optical transitions |

### 2.2 Empirical Analysis of Solar Generation Behavior
1. **Random Forest Superiority:** The Champion Random Forest achieves $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, and $\text{RMSE} = 0.124356\text{ kW}$. Compared to standard multilinear regression (OLS, $R^2 = 0.569044$, $\text{MAE} = 0.300105\text{ kW}$), Random Forest delivers a **$78.63\%$ reduction in MAE** and a **$+0.3857$ absolute increase in $R^2$**, proving that non-linear feature bagging is essential to capture atmospheric optical interactions.
2. **Ensemble Comparison (RF vs. XGBoost):** XGBoost performs competitively ($R^2 = 0.953178$, $\text{MAE} = 0.069685\text{ kW}$), trailing Random Forest by only $0.0015$ in $R^2$. However, Random Forest exhibits lower residual dispersion during rapid monsoon cloud-cover transitions, making its error envelope more stable for downstream risk hedging.
3. **MAPE Denominator Artifact Disclosure:** While the nominal MAPE of the champion model is $49.42\%$, this elevated value is a well-documented mathematical artifact of near-zero denominators at dawn ($05:00\text{--}06:00$) and dusk ($18:00\text{--}19:00$). During twilight hours, actual solar generation is near zero ($0.01\text{--}0.02\text{ kW}$); an absolute residual of only $10\text{ W}$ ($0.01\text{ kW}$) produces an instantaneous percentage error of $100\%$, despite having negligible operational consequence for appliance scheduling. Night hours ($P_{\text{actual}} = 0\text{ kW}$) are excluded by standard convention to prevent division-by-zero, and MAE and RMSE remain the statistically rigorous metrics for solar generation evaluation.
4. **Target Leakage Contrast:** The intentionally circular leaky baseline ($\text{MAE} = 0.000068\text{ kW}, R^2 = 1.000000$) perfectly illustrates the vulnerability documented in published literature: models fed contemporaneous pyranometer irradiance learn trivial scaling arithmetic rather than meteorology. Purging $\text{GTI}$ drops $R^2$ to honest $0.9547$, establishing true operational generalization.

---

## 3. Household Electrical Load Demand Forecasting Performance

### 3.1 Benchmark Architecture Evaluation
The household load forecasting models were evaluated on the chronological holdout test partition ($N_{\text{test}} = 6,532$ hourly records spanning January 27, 2010 to November 26, 2010 from Sceaux, France). Input features consist strictly of 16 non-circular causal variables:
$$\mathbf{x}_{\text{load}}(t) = \begin{bmatrix} P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}, \\ \mu_{3\text{h}}(t), \mu_{24\text{h}}(t), \sigma_{24\text{h}}(t), \mu_{168\text{h}}(t), h_t, \text{DoW}_t, m_t, \mathbb{I}_{\text{weekend}}(t), T_{2\text{m}}(t) \end{bmatrix}^T \in \mathbb{R}^{16}$$

Table 2 presents the comparative evaluation metrics across all candidate algorithms alongside the naive persistence baseline.

### Table 2: Household Load Forecasting Performance Benchmark ($h = 1\text{ h}, N_{\text{test}} = 6,532$)

| Model Architecture | MAE (kW) | RMSE (kW) | $R^2$ | MAPE (%) | Model Role / Evaluation Characterization |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Disclosed Leakage & Persistence Baselines:** | | | | | |
| RF Leaky Baseline ($V_t, I_t, \text{Sub}_i$ Included) | $0.015906$ | $0.023158$ | $0.999335$ | $2.29\%$ | Target leakage: inverts $P \approx V \cdot I \cdot \cos\theta$ deterministically |
| Lag-1 Naive Persistence ($P_{t-1}$) | $0.441000$ | $0.638400$ | $0.350000$ | $58.20\%$ | Naive baseline: predicts $\hat{P}_t = P_{t-1}$; essential skill threshold |
| **Corrected Non-Circular Models:** | | | | | |
| **Random Forest (Champion)** | **$0.332060$** | **$0.483827$** | **$0.592867$** | **$42.59\%$** | **Ensemble Bagging: Highest $R^2$, lowest MAE/RMSE; champion model** |
| Extreme Gradient Boosting (XGBoost) | $0.342436$ | $0.491907$ | $0.579157$ | $44.04\%$ | Gradient Boosting: Strong tracking; slightly higher peak error |
| Support Vector Regressor (SVR) | $0.345344$ | $0.511676$ | $0.544650$ | $39.84\%$ | RBF Kernel: Good median fit; penalizes large sudden demand spikes |
| Linear Regression (OLS Baseline) | $0.368213$ | $0.519126$ | $0.531294$ | $48.00\%$ | Linear Autoregressive: Captures linear lags; misses non-linear shifts |
| Decision Tree Regressor (CART) | $0.371136$ | $0.544852$ | $0.483688$ | $45.52\%$ | Single Tree: High variance; susceptible to sub-daily regime shifts |

### 3.2 Empirical Analysis of Load Forecasting Gains
1. **Substantial Skill Over Naive Persistence:** The primary empirical requirement for autoregressive time-series forecasting is proving that an ML model captures genuine behavioral patterns beyond trivial persistence. In one-step-ahead benchmarking ($h=1\text{ h}$), the Champion Random Forest achieves $R^2 = 0.592867$ and $\text{MAE} = 0.332060\text{ kW}$, outperforming the naive persistence baseline ($R^2 = 0.350000, \text{MAE} = 0.441000\text{ kW}$) by an absolute $R^2$ improvement of **$+0.2429$** (a **$+69.39\%$ relative gain**) and reducing MAE by **$24.70\%$**.
2. **Ensemble Gain Over Single Trees:** Random Forest ($R^2 = 0.5929$) significantly outperforms an un-bagged CART decision tree ($R^2 = 0.4837$, $+0.1092$ gain) and multilinear regression ($R^2 = 0.5313$, $+0.0616$ gain). This demonstrates that ensemble bagging over randomized feature subsets effectively dampens the high variance inherent in individual residential appliance switching.
3. **Physical Metrology Leakage Remediation:** The intentionally leaky baseline trained with contemporaneous voltage and current intensity achieved an artificial $R^2 = 0.999335$ and $\text{MAE} = 0.015906\text{ kW}$. Contemporaneous current is physically unavailable prior to consumption; purging $V_t$ and $I_t$ reveals the true honest predictive ceiling ($R^2 = 0.5929$) achievable on this benchmark using purely historical inputs.

---

## 4. Cross-Domain Predictability Contrast and Methodological Boundaries

### 4.1 Disparate Predictability Bounds: Solar ($R^2 \approx 0.95$) vs. Load ($R^2 \approx 0.59$)
A critical scientific insight emerges from comparing the empirical performance ceilings across the two domains:
- **Solar PV Generation ($R^2 = 0.9547$):** Solar generation is fundamentally bounded by the deterministic astronomical trajectory of the Earth (solar zenith angle, declination, and diurnal cycle). While cloud cover introduces stochastic attenuation, the deterministic solar-position envelope accounts for the vast majority of diurnal variance. Consequently, empirical models easily achieve $R^2 > 0.95$.
- **Household Electrical Load ($R^2 = 0.5929$):** Domestic electricity consumption is driven by stochastic human volition (e.g., deciding spontaneously to turn on an electric oven, iron, or vacuum cleaner). Even with extensive autoregressive memory ($P_{t-1 \dots 168}$) and calendar encodings, individual household load profiles exhibit high unforced entropy. An $R^2$ of $0.5929$ represents an honest, state-of-the-art result for single-household forecasting without target leakage.

### 4.2 Explicit Methodological Disclosures and Limitations
In strict adherence to academic transparency, three structural limitations of the predictive results are explicitly disclosed:
1. **One-Step Horizon ($h=1\text{ h}$) vs. Recursive Operational Rollout:** The metrics in Table 2 strictly evaluate one-step-ahead predictions using true historical lags. In operational 24-hour scheduling, the system uses recursive rollout (feeding predicted load outputs into future lag slots). Open-loop recursive forecast accuracy decays over multi-hour horizons and was not independently benchmarked offline.
2. **Reanalysis vs. Operational Numerical Weather Predictions (NWP):** Solar models were trained on historical ERA5-Land reanalysis data. Reanalysis data provides spatially blended atmospheric profiles that are smoother than operational, turbulent live weather forecasts.
3. **Synthetic Cross-Regional Pairing:** The Sceaux load profile and Kaliakair solar profile are synthetically paired across 176 common $(h, m)$ calendar scenarios; they do not represent co-located physical microgrid measurements.
