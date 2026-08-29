# Load Forecasting — ML Pipeline

> **Project:** Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework (Solar-Aware HEMS)  
> **Status:** Phase 2 Complete — Verification Gate PASSED (with documented iterations)

## Overview

This module trains and evaluates household load forecasting models on UCI Individual Household Electric Power Consumption data (2006–2010, hourly).

**Target variable:** `Global_active_power` (kW)

## Known Issues & Fixes (Applied)

### Datetime Gaps (Critical — 8 real gaps, 421 missing hours)
- **Problem:** Raw `main_data.csv` has 8 multi-hour to multi-day gaps (meter outages in original UCI data). Ranging from 2 hours to 5 days.
- **Fix applied:** Gap-aware reindex to complete hourly grid → lag/rolling features computed on the grid → NaN rows dropped. No interpolation.
- **Row loss:** 1,933 rows (initial boundary: 48, gaps: 421, contamination windows: 1,464) → **32,656 clean rows retained (94.4%)**

### Rolling Feature Leakage (Critical — caught during Verification Gate)
- **Problem (Iteration 1):** Rolling features (`rolling_mean_3h`, etc.) were computed on the raw target, which includes the current row's value. This allowed perfect algebraic reconstruction: `power(t) = 3 × rolling_mean_3h - lag1 - lag2`, giving Linear Regression R²=1.0.
- **Diagnosis:** Linear Regression R²=1.0 flagged as suspicious. Algebraic leakage confirmed: reconstruction error < 1e-14 for 100% of rows.
- **Fix applied (Iteration 2):** Changed to `df[TARGET].shift(1).rolling(...)` — rolling windows now only use strictly past values.
- **Evidence:** After fix, Linear Regression R²=0.5313 — no longer suspiciously perfect.

### T2M (Temperature) Feature — Methodological Limitation
- **Source:** T2M is from NASA POWER, merged into `main_data.csv` at the **same timestamp** as the target (`Global_active_power`). It is hourly-resolution observed/reanalysis temperature — **not** a weather forecast.
- **Implication:** At prediction time *t*, T2M(*t*) would not yet be available in a real deployment. In production, a weather forecast value would be used instead, introducing additional forecast error.
- **Impact on reported metrics:** T2M's feature importance in RF is ~0.02 (3rd-tier feature, well behind `power_lag_1` at 0.59 and `hour` at 0.06). Replacing it with a forecast value would slightly degrade accuracy, but the effect is expected to be small since lag features dominate.
- **Disclosure:** T2M is retained as a feature for completeness but its same-timestamp nature is flagged as a methodological limitation for the paper. This same limitation applies to QV2M, WS10M, PRECTOTCORR, and ALLSKY_SFC_UV_INDEX (none of which are currently used as corrected features).

### Iteration Log

| Iteration | Change | Best R² (RF) | Notes |
|-----------|--------|-------------|-------|
| 1 (buggy) | Initial features, rolling on raw target | 0.9928 | Rolling leakage → inflated |
| 2 (fixed) | `.shift(1).rolling()`, added lag_12/168/rolling_168h | **0.5929** | Leakage-free |

## Dataset Summary

| Property | Value |
|----------|-------|
| Raw rows | 34,168 |
| Grid rows | 34,589 |
| Clean rows | 32,656 (94.4%) |
| Date range | Dec 23, 2006 → Nov 26, 2010 |
| Frequency | Hourly |
| Gaps | 8 (totalling 421 missing hours) |
| Target mean | ~1.1 kW |
| Target max | ~6.4 kW |

## Train/Test Split

| Set | Rows | Period |
|-----|------|--------|
| Train | 26,124 (80%) | Dec 2006 → Jan 2010 |
| Test | 6,532 (20%) | Jan 2010 → Nov 2010 |

Split: chronological (`shuffle=False`) on clean data ✅

## Model Comparison

| Model | MAE (kW) | RMSE (kW) | R² | MAPE (%) | Notes |
|-------|----------|-----------|-----|----------|-------|
| RF Leaky Baseline | 0.0159 | 0.0232 | 0.9993 | 2.29 | Circular (Voltage+Intensity) |
| **Random Forest** | **0.3321** | **0.4838** | **0.5929** | 42.59 | **Best corrected model** |
| XGBoost | 0.3424 | 0.4919 | 0.5792 | 44.04 | Close second |
| SVR | 0.3453 | 0.5117 | 0.5446 | 39.84 | 20k subsample |
| Linear Regression | 0.3682 | 0.5191 | 0.5313 | 47.99 | Expected lower |
| Decision Tree | 0.3711 | 0.5449 | 0.4837 | 45.52 | Simplest tree |

### Performance Context
- R²≈0.59 was the best performance obtained under the tested feature set and tuning attempts (lag features, rolling features, weekly lags, calendar features, T2M temperature, hyperparameter tuning over two iterations).
- The remaining unexplained variance is likely due to stochastic and unmodeled household-load variation (e.g., unpredictable appliance usage, occupancy changes, visitor events) that cannot be captured from the available feature set.
- **Naive persistence baseline (predict = lag_1 only): R²=0.35** → RF at 0.59 represents a significant improvement (+69%), confirming the model captures real signal beyond simple autoregression.

### MAPE Note
MAPE values (39–48%) are included for completeness but should be interpreted with caution: MAPE is sensitive to low/near-zero load values (e.g., nighttime standby consumption), where small absolute errors produce large percentage errors. **MAE, RMSE, and R² remain the primary evaluation metrics.** MAPE should not be interpreted as "the model is X% wrong on average."

### Feature Importance (RF Corrected)
Top features: `power_lag_1` (0.59), `hour` (0.06), `power_lag_168` (0.05), `power_lag_24` (0.03), `T2M` (0.02)

## Verification Gate Results

- [x] **Leaky vs corrected R² drop:** Leaky R² = 0.9993 → RF Corrected R² = 0.5929. Clear drop. ✅
- [x] **Rolling feature leakage caught & fixed:** LR R²=1.0 → diagnosed as algebraic leakage → fixed → LR R²=0.53. ✅
- [x] **Low-R² diagnosis performed:** Lag correctness verified (spot-checks), weekly features added, hyperparameters tuned. ✅
- [x] **Model beats naive persistence:** 0.59 vs 0.35 (+69%). ✅
- [x] **All plots visually inspected:** No blank, corrupted, or mislabeled images. ✅
- [x] **Scatter plots correct:** RF scatter shows moderate spread consistent with R²=0.59. Leaky scatter hugs y=x. ✅
- [x] **Comparison table matches bar chart:** Cross-checked. ✅
- [x] **Residual histogram (RF):** Centered near zero (mean=-0.027 kW). ✅
- [x] **Feature importance makes physical sense:** lag_1 dominates (0.59), hour is second (0.06). ✅
- [x] **Datetime gap handling:** 8 gaps inventoried, gap-aware NaN-drop, no interpolation. ✅
- [x] **Split order confirmed:** Chronological split performed AFTER cleaning. ✅
- [x] **T2M provenance flagged:** Same-timestamp observed (not forecast). Documented as methodological limitation. ✅

## Artifacts

- `data/load_processed_clean.csv` — gap-aware cleaned dataset
- `data/load_test_predictions.csv` — test-set predictions
- `models/` — 6 saved model files (.joblib)
- `results/metrics/` — 6 × (.csv + .json)
- `results/plots/` — 44+ plot files (.png)
- `results/comparison_table.csv` — all models side by side

---

## ML Forecasting Context and Short-History Demonstration Mode

### 1. Dataset & Case-Study Provenance
* **Training & Evaluation Dataset**: UCI Individual Household Electric Power Consumption dataset (Sceaux, France, 2006–2010), representing residential power consumption.
* **Physical Hardware Case Study**: Live ESP32 monitoring unit with voltage, current, and DHT22 sensors, deployed in Bangladesh.
* **Solar & Meteorological Input**: Open-Meteo hourly forecast API for Kaliakair, Bangladesh ($24.07^\circ\text{N}, 90.22^\circ\text{E}$).

### 2. The 168-Hour History Constraint
The corrected Random Forest model utilizes 16 input features, including historical lag offsets up to 168 hours ($\text{lag}_1, \text{lag}_2, \text{lag}_3, \text{lag}_{12}, \text{lag}_{24}, \text{lag}_{48}, \text{lag}_{168}$) and rolling statistics ($\text{mean}_{3h}, \text{mean}_{24h}, \text{std}_{24h}, \text{mean}_{168h}$). During initial deployment, test bench runs, or demonstration sessions, the hardware may not have accumulated 168 continuous hours of live telemetry.

### 3. Methodology for Short-History Demonstration Operation
To evaluate the end-to-end forecasting, explainability (SHAP), and risk-aware scheduling pipeline without waiting 7 days or synthesizing artificial rows:
1. **Deterministic Benchmark Profiles**: When real sensor history is incomplete, missing lags and rolling windows are populated from the empirical conditional distribution $\mathbb{E}[\text{Feature} \mid \text{month}, \text{day\_of\_week}, \text{hour}]$ precomputed from `load_processed_clean.csv`.
2. **Precedence for Real Telemetry**: Any real sensor readings recorded in the database take precedence over benchmark profile values.
3. **Automatic Mode Switching**:
   * Mode `benchmark_profile_fallback`: Active when $< 168\text{h}$ of live history exists.
   * Mode `real_history`: Automatically engaged as soon as full $\ge 168\text{h}$ unbroken telemetry is logged.
4. **Database Cleanliness**: Benchmark profile values are evaluated strictly in memory during feature construction; **no synthetic or benchmark rows are ever inserted into the live Supabase `sensor_readings` table.**

### 4. Layer Separation

* **Hardware Monitoring Layer**: Physical ESP32 readings (voltage, current, power, energy, relay states) are labeled `[MEASURED]` or `[CALCULATED]`.
* **ML Forecasting Layer**: Model outputs are labeled `[FORECAST]`, and Safe Surplus is labeled `[CALCULATED]`.

### 5. Mandatory Academic Disclosure
> *"The ML forecasting layer uses the UCI residential benchmark dataset for historical load context during short-history demonstration operation, while live ESP32 telemetry is independently used for hardware monitoring and validation."*

