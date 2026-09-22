# Explainable AI (XAI) Attribution, Interpretability, and Axiomatic Verification

**Document ID:** `Paper/05_Results_and_Discussion/xai_attribution_and_interpretability.md`  
**Phase:** Phase 5 — Results and Discussion  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Introduction and Decoupled Dual-Layer Explainability Paradigm

Machine learning ensembles deployed in energy management are often criticized as opaque "black-box" models. To establish transparent, audit-ready accountability, this research couples the champion Random Forest predictive models with **TreeSHAP** (`shap.TreeExplainer`), evaluating exact cooperative game-theoretic feature attributions.

Crucially, the architecture enforces a **decoupled dual-layer explainability design**:
- **Layer 1 (Mathematical Model Attribution):** Evaluates exact Shapley values ($\boldsymbol{\phi} \in \mathbb{R}^M$) rooted in cooperative game theory, providing machine learning engineers with a provably additive breakdown of internal model mechanics;
- **Layer 2 (Deterministic Causal Translation):** Translates physical power deficits ($S_{\text{safe}} - P_{\text{device}}$) and optimal scheduling recommendations ($t^*$) into actionable, plain-language guidance for non-technical residential occupants, without falsely conflating statistical regression weights with physical control causality.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DECOUPLED DUAL-LAYER EXPLAINABILITY                             │
├───────────────────────────────────────────────────┬────────────────────────────────────┤
│ LAYER 1: Mathematical Model Attribution (TreeSHAP)│ LAYER 2: Deterministic Causal NL   │
│ • Axiomatic Properties: Efficiency, Missingness,  │ • Target: Non-Technical Occupant   │
│   Consistency, Symmetry                           │ • Input: Physical Energy Deficit   │
│ • Exact Additive Reconstruction:                  │   (S_safe - P_device, kW)          │
│   f(x) = E[f(X)] + sum(phi_i)                     │ • Actionable Lookahead: Rec. Slot  │
│ • Target: ML Engineers & System Auditors          │   t* via Duration-Aware Gating     │
│ • Max Empirical Error: 1.71 x 10^-13 kW << 10^-6  │ • Guardrail: Prevents Hallucinated │
│ • Identifies Global/Local Driving Predictors      │   Causal Over-Interpretation       │
└───────────────────────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Programmatic Verification of Mathematical Additivity

### 2.1 The Efficiency Axiom Reconstruction Audit
The fundamental efficiency axiom of Shapley value theory dictates that the sum of local feature attributions must exactly equal the difference between the model's instantaneous prediction $f(\mathbf{x})$ and the dataset expected base value $\phi_0 = \mathbb{E}[f(\mathbf{X})]$:

$$\Delta_{\text{reconstruction}}^{(j)} = \left| f\left(\mathbf{x}^{(j)}\right) - \left( \phi_0 + \sum_{i=1}^M \phi_i\left(\mathbf{x}^{(j)}\right) \right) \right|$$

In strict accordance with `BUILD_PLAN.md` Verification Gate requirements, this mathematical property was programmatically audited across every instance of the held-out test partitions:
- **Solar Forecasting:** Audited across all $N_{\text{test}} = 11,612$ chronological predictions;
- **Load Forecasting:** Audited across all $N_{\text{test}} = 6,532$ chronological predictions;
- **Total Audit Corpus:** $18,144$ individual test predictions.

Table 1 summarizes the empirical reconstruction error statistics.

### Table 1: Programmatic TreeSHAP Efficiency Axiom Verification ($N_{\text{total}} = 18,144$)

| Model Architecture | Base Value $\phi_0$ (kW) | Test Samples Audited | Mean Absolute Error (kW) | Maximum Absolute Error (kW) | Pass Rate ($< 10^{-6}\text{ kW}$) | Verification Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Solar RF Champion** | $0.430403$ | $11,612$ | $7.50 \times 10^{-15}$ | $\mathbf{5.42 \times 10^{-14}}$ | $100.0\%$ ($11,612 / 11,612$) | **PASSED** |
| **Load RF Champion** | $1.109187$ | $6,532$ | $1.16 \times 10^{-14}$ | $\mathbf{1.71 \times 10^{-13}}$ | $100.0\%$ ($6,532 / 6,532$) | **PASSED** |

Across all $18,144$ audited instances, the maximum reconstruction discrepancy is $1.71 \times 10^{-13}\text{ kW}$—a value bounded strictly within standard IEEE 754 double-precision floating-point limits and several orders of magnitude below the numerical tolerance threshold ($10^{-6}\text{ kW}$). This confirms exact mathematical additivity across both domains.

---

## 3. Global Feature Attribution and Physical Consistency

### 3.1 Solar PV Generation Global Attributions
Table 2 details the global feature importance rankings, mean absolute Shapley values ($|\text{SHAP}|$), and Pearson correlation coefficients ($r$) between feature values and local Shapley contributions for the solar forecasting pipeline.

### Table 2: Solar Generation Global Feature Attribution Rankings ($N_{\text{test}} = 11,612$)

| Rank | Feature Name | Mean $|\text{SHAP}|$ (kW) | Correlation ($r$) | Directional Impact | Physical & Meteorological Mechanism |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `hour` | **$0.324798$** | $-0.0401$ | Non-linear Diurnal Arc | Extraterrestrial solar geometry; peaks at noon ($+0.70\text{ kW}$), negative at night ($-0.60\text{ kW}$). |
| **2** | `relative_humidity` | **$0.194987$** | **$-0.9066$** | Strong Negative | High atmospheric moisture content, overcast haze, and monsoon precipitation attenuating downwelling solar flux. |
| **3** | `temperature` | **$0.084178$** | **$+0.7110$** | Strong Positive | Strong thermodynamic correlation with unshaded, clear-sky daytime conditions in tropical South Asia. |
| **4** | `cloud_cover` | **$0.031786$** | **$-0.7576$** | Strong Negative | Direct optical obstruction of solar rays; higher cloud fractions suppress predicted generation. |
| **5** | `day_of_year` | **$0.010832$** | $+0.2305$ | Positive | Seasonal variations in solar declination angle across the annual astronomical cycle. |
| **6** | `wind_speed` | **$0.003000$** | $-0.1409$ | Weak Negative | Minor atmospheric turbulence correlation; secondary convective modulation. |
| **7** | `month` | **$0.000561$** | $+0.0575$ | Neutral ($\approx 0$) | Largely subsumed by the higher-resolution `day_of_year` seasonal encoding. |

#### Empirical Discovery: The $10.2\times$ Importance Gap
A fundamental structural insight revealed by TreeSHAP is the **$10.2\times$ importance gap** between the primary astronomical geometric predictor (`hour`, Mean $|\text{SHAP}| = 0.3248\text{ kW}$) and the leading direct atmospheric cloud predictor (`cloud_cover`, Mean $|\text{SHAP}| = 0.0318\text{ kW}$):
1. **The Deterministic Envelope:** Solar elevation angle strictly governs the upper envelope of physical generation. At latitude $24.07^\circ\text{N}$, nearly $47\%$ of annual hours are nighttime ($P_{\text{solar}} = 0\text{ kW}$), and daytime follows a smooth bell curve peaking between 11:00 and 13:00. This fixed geometric pattern explains the vast majority of raw variance in hourly solar timeseries;
2. **Atmospheric Attenuation as a Fractional Modulation:** Meteorological variables (`relative_humidity`, `cloud_cover`, `temperature`) act as secondary attenuation filters that modulate generation downward from the clear-sky astronomical envelope;
3. **Humidity as Cloud-Thickness Proxy:** `relative_humidity` ($|\text{SHAP}| = 0.1950\text{ kW}$, Rank 2) exhibits over $6\times$ the importance of `cloud_cover`. In tropical reanalysis datasets, bulk cloud cover ($0\text{--}100\%$) lacks vertical cloud optical depth information; column relative humidity acts as a superior continuous proxy for optical opacity.

### 3.2 Household Electrical Load Global Attributions
Table 3 documents the global feature attribution rankings and directional correlations for the 16-feature household load model.

### Table 3: Household Load Global Feature Attribution Rankings ($N_{\text{test}} = 6,532$)

| Rank | Feature Name | Mean $|\text{SHAP}|$ (kW) | Correlation ($r$) | Directional Impact | Operational / Human Behavioral Mechanism |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `power_lag_1` | **$0.450085$** | **$+0.9795$** | Strong Positive | Immediate autoregressive persistence; previous hour load is the dominant predictor of ongoing appliance runtime. |
| **2** | `hour` | **$0.106258$** | $+0.4590$ | Positive | Diurnal human routine; captures elevated morning ($07:00\text{--}09:00$) and major evening ($19:00\text{--}22:00$) peaks. |
| **3** | `power_lag_168` | **$0.070510$** | $+0.8782$ | Strong Positive | Weekly lifestyle periodicity; aligns identical-hour behavior on the same day of the preceding week. |
| **4** | `power_lag_24` | **$0.040809$** | $+0.8314$ | Strong Positive | Diurnal 24-hour periodicity; yesterday's consumption at the identical hour. |
| **5** | `power_lag_2` | **$0.038319$** | **$-0.6905$** | Negative | Second-order difference/momentum correction against `power_lag_1`, stabilizing short-term spikes. |
| **6** | `T2M` (Temp) | **$0.025336$** | **$-0.8262$** | Strong Negative | Thermodynamic space and water heating demand; lower winter temperatures increase electrical heating load. |
| **7** | `power_lag_48` | **$0.024726$** | $+0.8358$ | Positive | 48-hour lag pattern (consumption two days prior). |
| **8** | `power_lag_12` | **$0.024241$** | $+0.7739$ | Positive | Semi-diurnal 12-hour activity cycle. |
| **9** | `power_lag_3` | **$0.015877$** | $-0.1109$ | Negative | Autoregressive damping over extended continuous runtime. |
| **10** | `rolling_mean_3h` | **$0.013957$** | $-0.5372$ | Negative | Short-term trend baseline adjustment (past values only). |
| **11** | `rolling_mean_168h` | $0.010365$ | $+0.4971$ | Positive | Weekly macro baseload tracking. |
| **12** | `day_of_week` | $0.009183$ | $+0.3060$ | Positive | Day-of-week shift aligning weekday vs. weekend routines. |
| **13** | `rolling_std_24h` | $0.008072$ | $+0.3244$ | Positive | 24-hour demand volatility expansion. |
| **14** | `rolling_mean_24h` | $0.006910$ | $+0.0139$ | Neutral ($\approx 0$) | 24-hour moving baseline. |
| **15** | `month` | $0.005377$ | $+0.0306$ | Neutral ($\approx 0$) | Annual seasonal trend. |
| **16** | `is_weekend` | $0.004490$ | $+0.6271$ | Positive | Weekend daytime domestic occupancy increase. |

#### Empirical Discovery: Autoregressive State Dominance
The single dominant predictor for domestic load is immediate historical persistence (`power_lag_1`, $|\text{SHAP}| = 0.4501\text{ kW}$), representing **$44.8\%$ of total model attribution mass**. The strong negative correlation of `T2M` ($r = -0.8262$) confirms that the model captures physical space heating thermodynamics in Western Europe, while contributing only $2.5\%$ of total attribution mass, verifying that exogenous weather provides legitimate seasonal correlation without introducing target leakage.

---

## 4. Local Explanations and Contrasting Case Studies

Local TreeSHAP waterfall decompositions demonstrate exact additive attribution for contrasting operating regimes across both models.

```
High Solar Generation (Test Row 8601: Noon, Clear Sky, RH 23%, Temp 36°C)
Base E[f(X)]: 0.430 kW
  + hour=12              (+0.71 kW)  ───► [Midday Astronomical Peak]
  + rel_humidity=23%     (+0.50 kW)  ───► [Dry Atmosphere / Minimal Haze]
  + temp=36.0°C          (+0.22 kW)  ───► [Clear-Sky Thermal Convection]
  + cloud_cover=0%       (+0.09 kW)  ───► [Zero Optical Obstruction]
Predicted Output: 1.958 kW (Actual: 1.711 kW)

─────────────────────────────────────────────────────────────────────────

Low Solar Generation (Test Row 0: Night, Overcast, RH 94%, Temp 21.9°C)
Base E[f(X)]: 0.430 kW
  - hour=3               (-0.21 kW)  ───► [Astronomical Night Horizon]
  - rel_humidity=94%     (-0.14 kW)  ───► [Saturated Atmospheric Moisture]
  - temp=21.9°C          (-0.05 kW)  ───► [Cool Night Baseline]
  - cloud_cover=100%     (-0.03 kW)  ───► [Complete Cloud Shield]
Predicted Output: 0.000 kW (Actual: 0.000 kW)
```

```
High Evening Peak Load (Test Row 72: Sat 19:00, lag_1 = 5.14 kW, T2M = -4.13°C)
Base E[f(X)]: 1.109 kW
  + power_lag_1=5.14 kW  (+2.38 kW)  ───► [Ongoing Heavy Appliance Runtime]
  + hour=19              (+0.16 kW)  ───► [Domestic Evening Peak Hours]
  + power_lag_168=3.61 kW(+0.07 kW)  ───► [Saturday Evening Routine]
  + T2M=-4.13°C          (+0.06 kW)  ───► [Sub-Zero Space Heating Demand]
Predicted Output: 3.883 kW (Actual: 2.715 kW)

─────────────────────────────────────────────────────────────────────────

Low Baseload Dawn Load (Test Row 5162: Mon 05:00, lag_1 = 0.195 kW)
Base E[f(X)]: 1.109 kW
  - power_lag_1=0.195 kW (-0.73 kW)  ───► [Quiescent Sleeping Baseload]
  - hour=5               (-0.07 kW)  ───► [Pre-Dawn Inactive Routine]
  - power_lag_24=0.197 kW(-0.02 kW)  ───► [Identical Dawn Quiescence Yesterday]
Predicted Output: 0.274 kW (Actual: 0.279 kW)
```

---

## 5. Dual-Layer Operational Translation and Safety Guardrails

In the runtime HEMS platform, raw Shapley values are not presented directly to residential users, as non-technical occupants can easily misinterpret feature attributions (e.g., assuming `power_lag_1` represents an appliance that can be turned off to save energy).

Instead, the **Layer 2 deterministic translation engine** operationalizes explanations:
1. **Deficit Communication:** If a $1.20\text{ kW}$ washing machine is denied admission because $S_{\text{safe}} = 0.775\text{ kW}$, the engine computes the physical power deficit:
   $$\Delta P_{\text{deficit}} = P_{\text{device}} - S_{\text{safe}} = 1.200\text{ kW} - 0.775\text{ kW} = \mathbf{0.425\text{ kW}}$$
   The user receives: *"Request Denied: 0.425 kW safe solar deficit. Retained on commercial grid."*
2. **Actionable Horizon Scheduling:** The system executes the duration-aware lookahead search to locate the earliest continuous slot $t^*$ where $S_{\text{window}}(t^*, n_{\text{hours}}) \ge P_{\text{device}}$, advising: *"Recommended Schedule: Shift activation to 13:00 (projected safe surplus: 1.450 kW)."*
3. **Conversational AI Boundary:** When queried via SolarMate AI, the LLM converts these physical numbers into conversational explanations grounded strictly in tool responses, with zero authority to actuate physical relays.
