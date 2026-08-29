# Solar Forecasting — ML Pipeline

> **Project:** Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework (Solar-Aware HEMS)  
> **Status:** ✅ Phase 1 Complete — Verification Gate PASSED

## Overview

This module trains and evaluates solar power forecasting models on Open-Meteo historical/reanalysis data for Kaliakair, Bangladesh (2020–2026, hourly).

**Target variable:** `solar_power_kW = GTI × 2.42 m² × 0.19 × 0.92 × 5 panels / 1000`

## Known Issues & Fixes (Applied)

### Target Leakage (Critical — PROJECT_MASTER_CONTEXT §4.1)
- **Problem:** Original notebook used `global_tilted_irradiance` (GTI) as both the basis for computing the target and as a model input feature — yielding near-perfect but meaningless R².
- **Fix applied:** Corrected models use only forecast-available features: `cloud_cover, temperature, relative_humidity, wind_speed, hour, month, day_of_year`. The leaky baseline is preserved as "RF Leaky Baseline" for documented comparison.
- **Evidence:** Leaky baseline R² = 1.0000; best corrected model (RF) R² = 0.9547 — clear, expected drop confirming leakage removal.

### Panel Count Inconsistency
- **Problem:** Code comment said "৫টি প্যানেলের জন্য" (5 panels) but `NUMBER_OF_PANELS = 10`.
- **Resolution:** Confirmed 5 panels is correct. Fixed to `NUMBER_OF_PANELS = 5` in the pipeline.

### Open-Meteo Data Source (Confirmed Limitation)
- **Confirmed:** `kaliakair_openmeteo_solar_raw.csv` is from the **historical/archive API** (reanalysis), not forecast. The dataset spans 6.6 years (2020–2026), far beyond any forecast window.
- **Implication:** σ_solar computed from this backtest represents a **lower bound** on real-world forecast uncertainty, since reanalysis data has less error than genuine live forecasts.
- **Disclosure:** Documented in `paper_assets/limitations_and_disclosures.md`.

### Datetime Continuity
- **Checked:** Timestamps vary by ±1 minute (59/60/61-minute intervals) — this is Open-Meteo rounding, not actual data gaps. **Zero multi-hour gaps found.** Data is effectively continuous hourly.

## Dataset Summary

| Property | Value |
|----------|-------|
| Rows | 58,056 |
| Date range | Jan 1, 2020 → Aug 15, 2026 |
| Frequency | Hourly (±1 min rounding) |
| Missing values | 0 |
| Target mean | 0.4315 kW |
| Target max | 2.0106 kW |
| Zero-power hours (nighttime) | 27,225 / 58,056 (46.9%) |

## Train/Test Split

| Set | Rows | Period |
|-----|------|--------|
| Train | 46,444 (80%) | Jan 2020 → Apr 2025 |
| Test | 11,612 (20%) | Apr 2025 → Aug 2026 |

Split: chronological (`shuffle=False`) ✅

## Model Comparison

| Model | MAE (kW) | RMSE (kW) | R² | MAPE (%) | Notes |
|-------|----------|-----------|-----|----------|-------|
| RF Leaky Baseline | 0.0001 | 0.0001 | 1.0000 | 0.03 | Intentionally circular — for comparison only |
| **Random Forest** | **0.0641** | **0.1244** | **0.9547** | 49.42 | **Best corrected model** |
| XGBoost | 0.0697 | 0.1265 | 0.9532 | 53.67 | Close second |
| Decision Tree | 0.0684 | 0.1326 | 0.9486 | 51.51 | Good, slightly less accurate |
| SVR | 0.0922 | 0.1516 | 0.9327 | 93.71 | Trained on 20k subsample (runtime) |
| Linear Regression | 0.3001 | 0.3837 | 0.5690 | 308.46 | Naive baseline — clearly insufficient |
| Physical Formula | 0.0000 | 0.0000 | 1.0000 | 0.00 | Identity (ceiling, not a model) |

### MAPE Note
High MAPE values (49–308%) are expected and **not** an accuracy concern: 46.9% of hours have zero or near-zero actual solar power (nighttime), where even tiny absolute predictions yield infinite/large percentage errors. MAE, RMSE, and R² are the reliable metrics here. MAPE is included for completeness but should be interpreted with this caveat in mind (standard issue in solar forecasting literature).

### Best Model Selection
**Random Forest** (corrected) selected as the best solar model for downstream phases (SHAP, risk module):
- Highest R² (0.9547) and lowest MAE (0.0641 kW) among corrected models
- Supports `TreeExplainer` for SHAP analysis

### Feature Importance (RF Corrected)
Top features: `hour` (0.51), `relative_humidity` (0.40), `temperature` (0.07), `cloud_cover` (0.02), `day_of_year` (0.01)

Physically sensible: hour captures solar geometry (sun angle), humidity inversely correlates with clear-sky irradiance, temperature reflects seasonal/daytime conditions.

## EDA Figures Generated

1. `eda_target_distribution.png` — right-skewed (many nighttime zeros)
2. `eda_timeseries_full.png` — weekly mean/max over 2020–2026
3. `eda_hourly_boxplot.png` — clear bell curve peaking at noon (hours 11–13)
4. `eda_monthly_boxplot.png` — seasonal pattern visible
5. `eda_correlation_heatmap.png` — GTI→target correlation = 1.00 (confirms leakage), corrected features show moderate correlations

## Per-Model Diagnostic Plots

For each model: `{model}_timeseries.png`, `{model}_scatter.png`, `{model}_residuals.png`, `{model}_residual_hist.png`, `{model}_feature_importance.png` (tree-based only).

Total: 38 plot files generated.

## Verification Gate Results

- [x] **Leaky vs corrected R² drop:** Leaky R² = 1.0000 → RF Corrected R² = 0.9547. Clear, expected drop. ✅
- [x] **Corrected accuracy is reasonable:** R² = 0.93–0.95 for tree models. Not suspiciously high, not poor. Consistent with using indirect forecast features (hour, humidity, cloud cover) to predict solar power. ✅
- [x] **Accuracy not poor enough to trigger diagnosis:** RF MAE = 0.064 kW against a mean of 0.43 kW (~15% relative error) — acceptable for this feature set. ✅
- [x] **All plots visually inspected:** No blank, corrupted, or mislabeled plots found. Axes labeled with units (kW), legends present, R² annotated on scatter plots. ✅
- [x] **RF scatter plot:** Points hug the y=x line with reasonable spread. Consistent with R² = 0.9547. No scaling bugs detected. ✅
- [x] **Linear scatter plot:** Clearly worse fit (R² = 0.5690), wide scatter — correctly reflects a naive linear model. ✅
- [x] **Leaky scatter plot:** Perfect straight line on y=x — confirms circular target reconstruction. ✅
- [x] **comparison_table.csv matches model_comparison_bar.png:** Cross-checked — values match. ✅
- [x] **Residual histogram (RF):** Centered near zero (mean = 0.0215 kW), slight positive skew — acceptable, no systematic bias. ✅
- [x] **Feature importance makes physical sense:** hour > humidity > temperature > cloud_cover — solar geometry and atmospheric conditions dominate, as expected. ✅
- [x] **Datetime continuity:** No actual gaps — only ±1 min timestamp rounding. ✅
- [x] **Open-Meteo source disclosed:** Historical/reanalysis confirmed and documented. ✅

## Artifacts

- `data/solar_processed.csv` — processed data with target variable
- `data/solar_test_predictions.csv` — test-set predictions from all models (for Phase 4)
- `models/` — 6 saved model files (.joblib)
- `results/metrics/` — 7 × (.csv + .json) metric files
- `results/plots/` — 38 plot files (.png)
- `results/comparison_table.csv` — all models side by side
- `results/comparison_table.json` — same, in JSON format
