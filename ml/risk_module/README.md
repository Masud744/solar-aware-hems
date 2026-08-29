# Risk Module — Uncertainty & Safety Margins

> **Project:** Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework (Solar-Aware HEMS)  

---

## 0. Sigma Method Disclosure

| Question | Answer |
|:---|:---|
| **Which σ method does the decision engine use?** | **Bucketed σ** — solar: per cloud-cover bucket; load: per hour-of-day block |
| **Which σ method does the k-sensitivity table use?** | Both reported; **bucketed σ is the primary basis** for k selection |
| **Which σ method does the synthetic decision matrix use?** | Both reported separately (`decision_evaluation_bucketed.png`, `decision_evaluation_global.png`) |
| **Why report both?** | Global σ is the baseline (BUILD_PLAN §6.2 option 1); bucketed σ is the recommended upgrade (§6.2 option 2). Reporting both satisfies Research Experiment §15.3 (global vs conditional σ comparison) |

---

## 1. Calibration / Evaluation Disclosure

> **Important:** Coverage metrics reported here are measured on the **same held-out backtest residual set** that was used to estimate σ. This is specified by the current project plan, but it means **coverage numbers should not be described as independent out-of-sample calibration results.** The residuals come from the chronological test splits established in Phases 1 and 2 (solar: 11,612 hourly test samples; load: 6,532 hourly test samples).

---

## 2. Global Sigma (Baseline)

| Quantity | Value | Context |
|:---|:---:|:---|
| σ_solar (global) | **0.1225 kW** | Solar RF residuals (n=11,612) |
| σ_load (global) | **0.4831 kW** | Load RF residuals (n=6,532) |
| Solar residual mean | +0.0215 kW | Slight underestimation bias |
| Load residual mean | −0.0270 kW | Slight overestimation bias |

**Sanity check:** Neither σ is near zero (ruling out training-set leakage) nor absurdly large relative to typical values (solar mean = 0.437 kW → σ/mean = 28.0%; load mean = 1.030 kW → σ/mean = 46.9%).

---

## 3. Bucketed Sigma (Intended Deployed Method)

### 3a. Solar — By Cloud-Cover Range

| Cloud Bucket | n | σ (kW) | Mean Residual (kW) | Mean Actual (kW) |
|:---|:---:|:---:|:---:|:---:|
| Clear (0–20%) | 4,166 | **0.0851** | −0.0023 | 0.438 |
| Partly Cloudy (21–60%) | 1,481 | **0.1317** | +0.0272 | 0.682 |
| Overcast (61–100%) | 5,965 | **0.1386** | +0.0368 | 0.376 |

**Expected pattern confirmed:** σ_overcast (0.1386) > σ_partly_cloudy (0.1317) > σ_clear (0.0851). No hard assertion was used — the ordering was inspected empirically and the expected differentiation is present.

**Solar bucket alignment:** Cloud-cover values joined by exact timestamp merge on the `time` column from `solar_processed.csv`. **11,612 / 11,612 matched (100%), 0 unmatched.** Row-order equivalence was not assumed; the join was performed by timestamp/index.

### 3b. Load — By Hour-of-Day Block

| Hour Block | n | σ (kW) | Mean Residual (kW) | Mean Actual (kW) |
|:---|:---:|:---:|:---:|:---:|
| Night (0–5) | 1,634 | **0.2662** | +0.0022 | 0.523 |
| Morning (6–11) | 1,626 | **0.4800** | −0.0220 | 1.218 |
| Afternoon (12–17) | 1,631 | **0.5114** | −0.0513 | 1.041 |
| Evening (18–23) | 1,641 | **0.6075** | −0.0370 | 1.339 |

**Expected pattern confirmed:** Evening (highest variability) = 2.3× night (stable baseload).

### 3c. Load — Per-Hour Sigma (24 values)

| Hour | σ (kW) | | Hour | σ (kW) | | Hour | σ (kW) | | Hour | σ (kW) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 00 | 0.365 | | 06 | 0.338 | | 12 | 0.592 | | 18 | 0.653 |
| 01 | 0.294 | | 07 | 0.541 | | 13 | 0.490 | | 19 | 0.611 |
| 02 | 0.263 | | 08 | 0.455 | | 14 | 0.543 | | 20 | 0.629 |
| 03 | 0.202 | | 09 | 0.448 | | 15 | 0.513 | | 21 | 0.666 |
| 04 | 0.207 | | 10 | 0.504 | | 16 | 0.441 | | 22 | 0.565 |
| 05 | 0.228 | | 11 | 0.545 | | 17 | 0.476 | | 23 | 0.508 |

---

## 4. K-Sensitivity Table (Bucketed σ — Primary)

| k | Solar Coverage (%) | Solar Utilization (%) | Solar Clipped (%) | Load Coverage (%) | Load Over-Provision (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 89.1 | 87.8 | 51.1 | 79.0 | 25.3 |
| 1.0 | 93.9 | 81.5 | 56.0 | 88.4 | 47.9 |
| 1.5 | 96.0 | 75.7 | 58.6 | 93.2 | 70.5 |
| 2.0 | 97.4 | 70.1 | 59.8 | 96.2 | 93.2 |
| 2.5 | 98.3 | 64.8 | 61.2 | 98.0 | 115.8 |

### K-Sensitivity Table (Global σ — Comparison)

| k | Solar Coverage (%) | Solar Utilization (%) | Solar Clipped (%) | Load Coverage (%) | Load Over-Provision (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 89.4 | 87.7 | 51.2 | 79.4 | 26.1 |
| 1.0 | 94.1 | 81.2 | 55.9 | 88.6 | 49.5 |
| 1.5 | 96.3 | 75.3 | 58.4 | 94.0 | 73.0 |
| 2.0 | 97.8 | 69.5 | 59.9 | 96.4 | 96.4 |
| 2.5 | 98.9 | 64.0 | 61.3 | 97.9 | 119.9 |

**Monotonicity:** ✓ Both solar and load coverage increase monotonically with k for both methods.

### Marginal Analysis (Bucketed σ)

| Step | Solar Cov Gain | Load Cov Gain | Solar Util Cost |
|:---|:---:|:---:|:---:|
| k 0.5→1.0 | +4.80 pp | +9.32 pp | −6.33 pp |
| k 1.0→1.5 | +2.13 pp | +4.81 pp | −5.81 pp |
| k 1.5→2.0 | +1.32 pp | +3.02 pp | −5.56 pp |
| k 2.0→2.5 | +0.96 pp | +1.78 pp | −5.38 pp |

The marginal coverage gain decreases with each step in k (diminishing returns), while the utilization cost remains roughly constant per step (~5.5–6.3 pp loss per +0.5 k). The largest coverage gain per unit cost occurs at the k 0.5→1.0 step.

### Safe Solar Clipping

| k | Samples Clipped to Zero | Clipped % |
|:---:|:---:|:---:|
| 0.5 | 5,938 | 51.1% |
| 1.0 | 6,507 | 56.0% |
| 1.5 | 6,801 | 58.6% |
| 2.0 | 6,946 | 59.8% |
| 2.5 | 7,109 | 61.2% |

The ~51% baseline at k=0.5 is dominated by nighttime hours (zero predicted solar). The incremental ~10 pp from k=0.5→2.5 represents low-generation daytime hours where the safety margin exceeds the prediction. This means that for all k values, at least half of all test samples have Safe Solar = 0 — a direct consequence of including nighttime hours where predicted solar ≈ 0 and `max(0, 0 − k·σ) = 0`.

---

## 5. Global vs Bucketed Comparison (Research Experiment §15.3)

Global and bucketed σ produce very similar aggregate coverage curves (within ≈0.5 pp for solar, within ≈1 pp for load). The bucketed approach's value is in producing **condition-appropriate** safety margins: tighter during clear-sky/nighttime, wider during overcast/evening periods.

---

## 6. Synthetic Combined Decision Evaluation

### Alignment Procedure

The solar and load datasets are **not temporally co-located**:
- **Solar:** Open-Meteo reanalysis data for Kaliakair, Bangladesh (~2020–2026)
- **Load:** UCI Household Electric Power Consumption, Sceaux, France (2006–2010)

**Method:** For each unique `(hour, month)` key in both test sets, randomly sample one solar and one load row (seed=42). Result: **176 aligned pairs** out of 288 possible (61%). Exactly 1 pair per key, no duplicates. Hours represented: 0, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18, 20, 21, 23 (16 of 24 hours). Months represented: 1–11 (11 of 12 months; December absent from one test set).

> **All decisions are a SYNTHETIC DECISION EVALUATION — not real-world co-located measurements.** Incorrect-ALLOW does not represent a measured real-world grid-usage event; it is the outcome of a synthetic experiment pairing non-co-located data. This evaluation is based on only **176 synthetically aligned pairs** and therefore is a **demonstration/evaluation of the decision logic**, NOT evidence of zero real-world grid-usage violations.

### 6a. Decision Matrix — Device = 0.5 kW (Bucketed σ)

| k | Correct-ALLOW | Incorrect-ALLOW | Correct-DENY | Incorrect-DENY | ALLOWs | ALLOW Rate | IA Rate | ID Rate |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 8 | 1 | 153 | 14 | 9 | 5.1% | 0.6% | 8.0% |
| 1.0 | 0 | 0 | 154 | 22 | **0** | 0.0% | 0.0% | 12.5% |
| 1.5 | 0 | 0 | 154 | 22 | **0** | 0.0% | 0.0% | 12.5% |
| 2.0 | 0 | 0 | 154 | 22 | **0** | 0.0% | 0.0% | 12.5% |
| 2.5 | 0 | 0 | 154 | 22 | **0** | 0.0% | 0.0% | 12.5% |

### 6b. Decision Matrix — Device = 1.2 kW (Bucketed σ)

| k | Correct-ALLOW | Incorrect-ALLOW | Correct-DENY | Incorrect-DENY | ALLOWs | ALLOW Rate | IA Rate | ID Rate |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 0 | 0 | 171 | 5 | **0** | 0.0% | 0.0% | 2.8% |
| 1.0 | 0 | 0 | 171 | 5 | **0** | 0.0% | 0.0% | 2.8% |
| 1.5 | 0 | 0 | 171 | 5 | **0** | 0.0% | 0.0% | 2.8% |
| 2.0 | 0 | 0 | 171 | 5 | **0** | 0.0% | 0.0% | 2.8% |
| 2.5 | 0 | 0 | 171 | 5 | **0** | 0.0% | 0.0% | 2.8% |

### 6c. Device-Power Sensitivity Summary (Bucketed σ)

| k | 0.5 kW ALLOWs | 0.5 kW IA | 1.2 kW ALLOWs | 1.2 kW IA |
|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 9 (8 CA, 1 IA) | 0.6% | 0 | 0.0% |
| 1.0 | 0 | 0.0% | 0 | 0.0% |
| 1.5 | 0 | 0.0% | 0 | 0.0% |
| 2.0 | 0 | 0.0% | 0 | 0.0% |
| 2.5 | 0 | 0.0% | 0 | 0.0% |

### 6d. Extreme-Conservatism Flag

> **⚠ At k ≥ 1.0, the system produces ZERO ALLOWs for BOTH 0.5 kW and 1.2 kW device powers.** Only k = 0.5 produces any ALLOWs, and only for the 0.5 kW device (9 ALLOWs: 8 correct, 1 incorrect). For the 1.2 kW device (the canonical worked-example device from §8.3), **no k value produces any ALLOWs at all** — the system denies every request across the full k range.

This is flagged as an **extreme-conservatism limitation** of the synthetic evaluation setting, not hidden. The structural cause is the compounding of both safety margins in `Safe Surplus = Safe Solar − Conservative Load`: with σ_load ≈ 0.48 kW and even a moderate k, the surplus requirement exceeds what this small (~2 kWp peak) synthetic solar system can typically provide above the synthetic household load.

### 6e. Interpretation

The synthetic decision matrix demonstrates the risk-aware framework's decision logic and confirms that:
1. Higher k → fewer ALLOWs (more conservative), as designed
2. The ALLOW precision at k=0.5 (88.9% for 0.5 kW) shows the decision engine correctly identifies viable windows when it does allow
3. The Incorrect-DENY counts (14–22 for 0.5 kW, 5 for 1.2 kW) show opportunities genuinely exist in the synthetic data but are missed by the conservative margins

The synthetic matrix **cannot alone determine the operating point**. The per-model coverage/utilization trade-off (Section 4) is the primary basis for k selection.

---

## 7. Selected Operating Point: k = 1.0

k = 1.0 is the **conservative operating point selected from the tested k values based on the empirical safety–utilization trade-off**. It is not described as mathematically optimal, statistically optimal, or as having a textbook confidence interpretation.

### Evidence Basis

| k | Solar Cov (B) | Solar Util (B) | Load Cov (B) | 0.5 kW ALLOWs | 0.5 kW IA | 1.2 kW ALLOWs |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.5 | 89.1% | 87.8% | 79.0% | 9 | 1 | 0 |
| **1.0** | **93.9%** | **81.5%** | **88.4%** | **0** | **0** | **0** |
| 1.5 | 96.0% | 75.7% | 93.2% | 0 | 0 | 0 |
| 2.0 | 97.4% | 70.1% | 96.2% | 0 | 0 | 0 |
| 2.5 | 98.3% | 64.8% | 98.0% | 0 | 0 | 0 |

*(B = bucketed σ; IA = Incorrect-ALLOW count; synthetic 176-pair evaluation)*

### Rationale

1. **Largest marginal coverage gain:** The k 0.5→1.0 step produces the biggest coverage improvement (+4.8 pp solar, +9.3 pp load) for the utilization cost (−6.3 pp). Beyond k=1.0, each +0.5 step yields diminishing coverage returns while continuing to lose ~5.5 pp utilization.
2. **Reasonable coverage levels:** Solar 93.9% and load 88.4% coverage (bucketed σ) provide substantial safety margins for the decision engine.
3. **Preserved usability:** 81.5% solar utilization avoids excessive conservatism.
4. **Safety-first principle:** The project prioritizes avoiding unsafe ALLOWs over maximizing utilization.

### Safety–Utilization Trade-off at k = 0.5

k = 0.5 is the **only operating point producing meaningful ALLOWs** in the synthetic evaluation (9 ALLOWs for 0.5 kW device, 8 correct / 1 incorrect = 88.9% precision). Its trade-off:
- **Advantage:** 87.8% solar utilization (highest) and 9 ALLOWs with 88.9% ALLOW precision
- **Disadvantage:** solar coverage only 89.1% (vs. 93.9% at k=1.0) and load coverage only 79.0% (vs. 88.4%) — meaning ~11% of solar predictions and ~21% of load predictions are not covered by the safety margin
- **Risk:** 1 Incorrect-ALLOW observed out of 176 synthetic pairs (0.6% rate)

k = 1.0 is selected over k = 0.5 because the coverage gains (+4.8 pp solar, +9.3 pp load) are substantial and the utilization loss (−6.3 pp) is acceptable, following the project's safety-first principle. However, this means **the system will produce zero ALLOWs in synthetic-evaluation-like conditions**, which is an acknowledged limitation.

### Limitations

- **Extreme-conservatism limitation:** At k = 1.0, the synthetic 176-pair evaluation produces **zero ALLOWs for BOTH 0.5 kW and 1.2 kW device powers**. This demonstrates extreme conservatism in the synthetic setting but is not evidence of how the system will behave with real co-located data where solar and load are from the same household at the same time.
- **Coverage is not independent:** Sigma estimation and coverage evaluation use the same held-out backtest residuals; the coverage figures are **not** an independent out-of-sample calibration result.
- **176-pair limitation:** The synthetic decision matrix is based on only 176 synthetically aligned solar/load pairs and is a demonstration/evaluation of the decision logic, NOT evidence of zero real-world grid-usage violations.
- **Validation required:** The chosen k should be validated on real co-located data (ESP32, Phase 8) before deployment.

> **Note:** No textbook confidence interpretation is applied to any k value. k = 1.0 is described as "the conservative operating point selected from the tested k values based on the empirical safety–utilization trade-off."

---

## 8. Artifact Index

### Data Files (`coverage_experiments/`)

| File | Description |
|:---|:---|
| `sigma_summary.json` | Global sigma values + calibration disclosure |
| `solar_bucketed_sigma.csv` | Per-cloud-cover-bucket sigma for solar |
| `load_bucketed_sigma.csv` | Per-hour-block sigma for load |
| `load_hourly_sigma.csv` | Per-hour (0–23) sigma for load |
| `k_sensitivity_solar_global.csv` | Solar coverage/utilization/clipping by k (global σ) |
| `k_sensitivity_solar_bucketed.csv` | Solar coverage/utilization/clipping by k (bucketed σ) |
| `k_sensitivity_load_global.csv` | Load coverage/over-provision by k (global σ) |
| `k_sensitivity_load_bucketed.csv` | Load coverage/over-provision by k (bucketed σ) |
| `k_sensitivity_combined.csv` | Synthetic combined decision metrics by k (both methods) |
| `full_k_sensitivity_summary.csv` | Master table: all metrics for all k values (both methods) |
| `synthetic_decision_matrix_bucketed.csv` | Synthetic decision evaluation — bucketed σ (both device powers) |
| `synthetic_decision_matrix_global.csv` | Synthetic decision evaluation — global σ (both device powers) |
| `device_power_sensitivity.csv` | Full device-power sensitivity results (0.5 kW + 1.2 kW × both σ methods) |
| `synthetic_aligned_pairs.csv` | The 176 synthetically aligned (hour, month) pairs |
| `synthetic_alignment_metadata.json` | Alignment procedure documentation |
| `solar_bucket_alignment_report.json` | Join verification: 11,612/11,612 matched |
| `k_selection.json` | k selection evidence, rationale, and limitations |

### Plot Files (`coverage_experiments/`)

| File | Description |
|:---|:---|
| `k_sensitivity_solar.png` | Solar: coverage vs utilization, global and bucketed |
| `k_sensitivity_load.png` | Load: coverage vs over-provision, global and bucketed |
| `k_sensitivity_combined.png` | Synthetic combined: bucketed (L) vs global (R) |
| `decision_evaluation_bucketed.png` | 5-panel heatmap — bucketed σ, 0.5 kW device |
| `decision_evaluation_global.png` | 5-panel heatmap — global σ, 0.5 kW device |
| `decision_evaluation_device_sensitivity.png` | 10-panel heatmap — 0.5 kW (top) vs 1.2 kW (bottom) |
| `bucketed_sigma.png` | Bar chart of bucketed σ (solar + load) |
| `safe_solar_clipping.png` | Clipping percentage by k |
| `residual_distributions.png` | Backtest residual histograms (solar + load) |
| `global_vs_bucketed_comparison.png` | Global vs bucketed σ coverage comparison |
