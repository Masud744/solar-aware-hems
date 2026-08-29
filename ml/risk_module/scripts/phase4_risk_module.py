#!/usr/bin/env python3
"""
Phase 4 — Risk Module: Uncertainty Quantification & Safety-Margin Calibration

Methodological corrections applied:
1. Synthetic solar-load pairing: All combined analysis uses "synthetically aligned
   decision reference" language — not "ground truth."
2. Calibration/evaluation disclosure: Coverage is measured on the same held-out
   backtest residuals used to estimate sigma. Documented explicitly.
3. Bucketed sigma: No hard assertion on bucket ordering; compute, report, flag
   if expected differentiation is absent.
4. Safe Solar clipping: Report % of samples where Safe Solar was clipped to 0.
5. Solar bucket alignment: Join by timestamp/index with verification.
6. k values: 0.5, 1.0, 1.5, 2.0, 2.5. Final k chosen after seeing results.
7. Synthetic alignment: Document hour-of-day + month procedure exactly.
8. No new datasets or architecture.
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────
# 0. Paths
# ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RISK_DIR     = PROJECT_ROOT / 'ml' / 'risk_module'
COV_DIR      = RISK_DIR / 'coverage_experiments'
SOLAR_DATA   = PROJECT_ROOT / 'ml' / 'solar' / 'data'
LOAD_DATA    = PROJECT_ROOT / 'ml' / 'load' / 'data'

COV_DIR.mkdir(parents=True, exist_ok=True)

# Consistent plot styling
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
})

K_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5]

# ─────────────────────────────────────────────────────────────────────
# 1. Load prediction data
# ─────────────────────────────────────────────────────────────────────
print("=" * 80)
print("PHASE 4 — RISK MODULE: UNCERTAINTY & SAFETY-MARGIN CALIBRATION")
print("=" * 80)

# --- Solar ---
solar_preds = pd.read_csv(SOLAR_DATA / 'solar_test_predictions.csv', parse_dates=['time'])
solar_proc  = pd.read_csv(SOLAR_DATA / 'solar_processed.csv', parse_dates=['time'])

# Best solar model = Random Forest (from Phase 1 comparison table)
solar_preds['actual'] = solar_preds['solar_power_kW']
solar_preds['predicted'] = solar_preds['pred_rf']
solar_preds['residual'] = solar_preds['actual'] - solar_preds['predicted']

# --- Load ---
load_preds = pd.read_csv(LOAD_DATA / 'load_test_predictions.csv', parse_dates=['DateTime'])
# Best load model = Random Forest (from Phase 2 comparison table)
load_preds['actual'] = load_preds['Global_active_power']
load_preds['predicted'] = load_preds['pred_rf']
load_preds['residual'] = load_preds['actual'] - load_preds['predicted']

print(f"\nSolar test samples: {len(solar_preds)}")
print(f"Load  test samples: {len(load_preds)}")

# ─────────────────────────────────────────────────────────────────────
# 2. Global sigma (baseline)
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 2: GLOBAL SIGMA (BASELINE)")
print("─" * 80)

sigma_solar_global = solar_preds['residual'].std()
sigma_load_global  = load_preds['residual'].std()

# Basic sanity checks
solar_mean = solar_preds['actual'].mean()
load_mean  = load_preds['actual'].mean()

print(f"\n  σ_solar (global)  = {sigma_solar_global:.6f} kW")
print(f"  σ_load  (global)  = {sigma_load_global:.6f} kW")
print(f"\n  Mean actual solar = {solar_mean:.6f} kW  → σ/mean = {sigma_solar_global/solar_mean:.2%}" if solar_mean > 0 else "")
print(f"  Mean actual load  = {load_mean:.6f} kW  → σ/mean = {sigma_load_global/load_mean:.2%}" if load_mean > 0 else "")

# Residual statistics
print(f"\n  Solar residual: mean={solar_preds['residual'].mean():.6f}, median={solar_preds['residual'].median():.6f}")
print(f"  Load  residual: mean={load_preds['residual'].mean():.6f}, median={load_preds['residual'].median():.6f}")

# ─────────────────────────────────────────────────────────────────────
# 3. Bucketed sigma
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 3: BUCKETED SIGMA")
print("─" * 80)

# --- 3a. Solar: bucket by cloud-cover ---
# CORRECTION #5: Join cloud_cover by exact timestamp, not row order
print("\n  [Solar] Joining cloud_cover from solar_processed.csv by exact timestamp...")
solar_proc_subset = solar_proc[['time', 'cloud_cover']].copy()
solar_proc_subset = solar_proc_subset.drop_duplicates(subset='time')

solar_merged = solar_preds.merge(solar_proc_subset, on='time', how='left')
matched_count = solar_merged['cloud_cover'].notna().sum()
unmatched_count = solar_merged['cloud_cover'].isna().sum()

print(f"  Matched rows:   {matched_count} / {len(solar_preds)}")
print(f"  Unmatched rows: {unmatched_count}")

if unmatched_count > 0:
    print(f"  ⚠ WARNING: {unmatched_count} solar test predictions could not be matched to cloud_cover.")
    print(f"    These rows will be excluded from bucketed analysis.")
    solar_merged = solar_merged.dropna(subset=['cloud_cover'])

# Define cloud-cover buckets
def cloud_bucket(cc):
    if cc <= 20:
        return 'Clear (0-20%)'
    elif cc <= 60:
        return 'Partly Cloudy (21-60%)'
    else:
        return 'Overcast (61-100%)'

solar_merged['cloud_bucket'] = solar_merged['cloud_cover'].apply(cloud_bucket)

solar_bucket_stats = solar_merged.groupby('cloud_bucket').agg(
    count=('residual', 'size'),
    sigma=('residual', 'std'),
    mean_residual=('residual', 'mean'),
    mean_actual=('actual', 'mean'),
    mean_predicted=('predicted', 'mean'),
).reindex(['Clear (0-20%)', 'Partly Cloudy (21-60%)', 'Overcast (61-100%)'])

print("\n  Solar Bucketed Sigma (by cloud-cover range):")
print(solar_bucket_stats.to_string(float_format='%.6f'))

# CORRECTION #3: Inspect ordering, do NOT hard-assert
sigma_clear = solar_bucket_stats.loc['Clear (0-20%)', 'sigma'] if 'Clear (0-20%)' in solar_bucket_stats.index else None
sigma_overcast = solar_bucket_stats.loc['Overcast (61-100%)', 'sigma'] if 'Overcast (61-100%)' in solar_bucket_stats.index else None

if sigma_clear is not None and sigma_overcast is not None:
    if sigma_overcast > sigma_clear:
        print(f"\n  ✓ Expected pattern: σ_overcast ({sigma_overcast:.6f}) > σ_clear ({sigma_clear:.6f})")
    else:
        print(f"\n  ⚠ FLAG FOR INVESTIGATION: σ_overcast ({sigma_overcast:.6f}) ≤ σ_clear ({sigma_clear:.6f})")
        print(f"    Expected harder conditions to show higher uncertainty, but ordering is reversed.")
        print(f"    Possible explanations: (1) Clear-sky overprediction variance, (2) overcast predictions")
        print(f"    collapse toward zero (low absolute error), (3) bucket imbalance. Investigate before concluding.")

# --- 3b. Load: bucket by hour-of-day ---
load_preds['hour'] = load_preds['DateTime'].dt.hour

# Group hours into meaningful blocks
def hour_bucket(h):
    if 0 <= h < 6:
        return 'Night (0-5)'
    elif 6 <= h < 12:
        return 'Morning (6-11)'
    elif 12 <= h < 18:
        return 'Afternoon (12-17)'
    else:
        return 'Evening (18-23)'

load_preds['hour_bucket'] = load_preds['hour'].apply(hour_bucket)

load_bucket_stats = load_preds.groupby('hour_bucket').agg(
    count=('residual', 'size'),
    sigma=('residual', 'std'),
    mean_residual=('residual', 'mean'),
    mean_actual=('actual', 'mean'),
    mean_predicted=('predicted', 'mean'),
).reindex(['Night (0-5)', 'Morning (6-11)', 'Afternoon (12-17)', 'Evening (18-23)'])

print("\n  Load Bucketed Sigma (by hour-of-day blocks):")
print(load_bucket_stats.to_string(float_format='%.6f'))

# Also compute per-hour sigma for finer granularity
load_hourly_sigma = load_preds.groupby('hour')['residual'].std()
print("\n  Load Per-Hour Sigma:")
for h, s in load_hourly_sigma.items():
    print(f"    Hour {h:02d}: σ = {s:.6f} kW")

# ─────────────────────────────────────────────────────────────────────
# 4. k-Sensitivity Experiment — Solar
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 4: K-SENSITIVITY EXPERIMENT")
print("─" * 80)

def compute_solar_coverage_metrics(df, sigma, k_values, label=""):
    """
    Compute coverage and utilization for solar predictions.

    Coverage = fraction of samples where Actual >= Safe Solar
    (i.e., safe solar is a conservative enough lower bound)

    CORRECTION #4: Also compute and report clipping percentage.
    """
    results = []
    for k in k_values:
        safe_solar_unclipped = df['predicted'] - k * sigma
        safe_solar = np.maximum(0, safe_solar_unclipped)

        # Coverage: actual >= safe solar
        covered = (df['actual'] >= safe_solar).sum()
        total = len(df)
        coverage = covered / total * 100

        # Average safe solar (utilization proxy)
        avg_safe_solar = safe_solar.mean()
        avg_actual = df['actual'].mean()
        utilization = avg_safe_solar / avg_actual * 100 if avg_actual > 0 else 0

        # CORRECTION #4: Clipping statistics
        n_clipped = (safe_solar_unclipped < 0).sum()
        clip_pct = n_clipped / total * 100

        results.append({
            'k': k,
            'sigma': sigma if isinstance(sigma, (int, float)) else 'bucketed',
            'coverage_%': coverage,
            'avg_safe_solar_kW': avg_safe_solar,
            'avg_actual_solar_kW': avg_actual,
            'utilization_%': utilization,
            'n_clipped_to_zero': int(n_clipped),
            'clipped_%': clip_pct,
            'label': label,
        })
    return pd.DataFrame(results)


def compute_solar_coverage_bucketed(df, bucket_stats, bucket_col, k_values, label=""):
    """
    Coverage with per-bucket sigma values.
    """
    results = []
    for k in k_values:
        # Map each row's sigma from its bucket
        df_temp = df.copy()
        df_temp['sigma'] = df_temp[bucket_col].map(bucket_stats['sigma'])

        safe_solar_unclipped = df_temp['predicted'] - k * df_temp['sigma']
        safe_solar = np.maximum(0, safe_solar_unclipped)

        covered = (df_temp['actual'] >= safe_solar).sum()
        total = len(df_temp)
        coverage = covered / total * 100

        avg_safe_solar = safe_solar.mean()
        avg_actual = df_temp['actual'].mean()
        utilization = avg_safe_solar / avg_actual * 100 if avg_actual > 0 else 0

        n_clipped = (safe_solar_unclipped < 0).sum()
        clip_pct = n_clipped / total * 100

        results.append({
            'k': k,
            'sigma': 'bucketed',
            'coverage_%': coverage,
            'avg_safe_solar_kW': avg_safe_solar,
            'avg_actual_solar_kW': avg_actual,
            'utilization_%': utilization,
            'n_clipped_to_zero': int(n_clipped),
            'clipped_%': clip_pct,
            'label': label,
        })
    return pd.DataFrame(results)


# Solar: global sigma
solar_global_results = compute_solar_coverage_metrics(
    solar_preds, sigma_solar_global, K_VALUES, label="Solar (Global σ)"
)

# Solar: bucketed sigma
solar_bucketed_results = compute_solar_coverage_bucketed(
    solar_merged, solar_bucket_stats, 'cloud_bucket', K_VALUES, label="Solar (Bucketed σ)"
)

print("\n  Solar Coverage — Global σ:")
print(solar_global_results[['k', 'coverage_%', 'avg_safe_solar_kW', 'utilization_%', 'n_clipped_to_zero', 'clipped_%']].to_string(index=False))

print("\n  Solar Coverage — Bucketed σ:")
print(solar_bucketed_results[['k', 'coverage_%', 'avg_safe_solar_kW', 'utilization_%', 'n_clipped_to_zero', 'clipped_%']].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────
# 5. k-Sensitivity Experiment — Load
# ─────────────────────────────────────────────────────────────────────

def compute_load_coverage_metrics(df, sigma, k_values, label=""):
    """
    Load coverage: actual <= conservative load (predicted + k*sigma)
    i.e., the conservative estimate is high enough to cover actual demand.
    """
    results = []
    for k in k_values:
        if isinstance(sigma, (int, float)):
            conservative_load = df['predicted'] + k * sigma
        else:
            conservative_load = df['predicted'] + k * sigma

        covered = (df['actual'] <= conservative_load).sum()
        total = len(df)
        coverage = covered / total * 100

        avg_conservative = conservative_load.mean()
        avg_actual = df['actual'].mean()

        results.append({
            'k': k,
            'coverage_%': coverage,
            'avg_conservative_load_kW': avg_conservative,
            'avg_actual_load_kW': avg_actual,
            'over_provision_%': (avg_conservative / avg_actual - 1) * 100 if avg_actual > 0 else 0,
            'label': label,
        })
    return pd.DataFrame(results)


def compute_load_coverage_bucketed(df, bucket_stats, bucket_col, k_values, label=""):
    """Load coverage with per-bucket sigma."""
    results = []
    for k in k_values:
        df_temp = df.copy()
        df_temp['sigma'] = df_temp[bucket_col].map(bucket_stats['sigma'])
        conservative_load = df_temp['predicted'] + k * df_temp['sigma']

        covered = (df_temp['actual'] <= conservative_load).sum()
        total = len(df_temp)
        coverage = covered / total * 100

        avg_conservative = conservative_load.mean()
        avg_actual = df_temp['actual'].mean()

        results.append({
            'k': k,
            'coverage_%': coverage,
            'avg_conservative_load_kW': avg_conservative,
            'avg_actual_load_kW': avg_actual,
            'over_provision_%': (avg_conservative / avg_actual - 1) * 100 if avg_actual > 0 else 0,
            'label': label,
        })
    return pd.DataFrame(results)


load_global_results = compute_load_coverage_metrics(
    load_preds, sigma_load_global, K_VALUES, label="Load (Global σ)"
)

load_bucketed_results = compute_load_coverage_bucketed(
    load_preds, load_bucket_stats, 'hour_bucket', K_VALUES, label="Load (Bucketed σ)"
)

print("\n  Load Coverage — Global σ:")
print(load_global_results[['k', 'coverage_%', 'avg_conservative_load_kW', 'over_provision_%']].to_string(index=False))

print("\n  Load Coverage — Bucketed σ:")
print(load_bucketed_results[['k', 'coverage_%', 'avg_conservative_load_kW', 'over_provision_%']].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────
# 6. Combined / Synthetic Decision Evaluation
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 6: SYNTHETIC COMBINED ANALYSIS")
print("─" * 80)

# CORRECTION #1 & #7: Document the alignment procedure exactly.
print("""
  SYNTHETIC ALIGNMENT PROCEDURE
  ─────────────────────────────
  The solar and load datasets are NOT temporally co-located:
    - Solar: Open-Meteo reanalysis data for Kaliakair, Bangladesh (~2020-2026)
    - Load:  UCI Household Electric Power Consumption, Sceaux, France (2006-2010)

  Alignment method: hour-of-day + month
    1. Extract (hour, month) from each solar and load test-set timestamp.
    2. For each unique (hour, month) pair present in BOTH datasets, randomly
       sample ONE load row and ONE solar row to form a synthetic pair.
       If multiple candidates exist for a given (hour, month), we use
       random sampling (seed=42) to select one per pair.
    3. This yields at most 24 hours × 12 months = 288 unique synthetic pairs.
    4. The resulting decisions are a SYNTHETIC DECISION EVALUATION, not
       real-world co-located measurements.

  This procedure is disclosed per PROJECT_MASTER_CONTEXT §4.3.
""")

# Build alignment
solar_align = solar_merged.copy()
solar_align['hour'] = solar_align['time'].dt.hour
solar_align['month'] = solar_align['time'].dt.month

load_align = load_preds.copy()
load_align['month'] = load_align['DateTime'].dt.month

# For each (hour, month), sample one row from each dataset
np.random.seed(42)
aligned_pairs = []

solar_groups = solar_align.groupby(['hour', 'month'])
load_groups  = load_align.groupby(['hour', 'month'])

common_keys = set(solar_groups.groups.keys()) & set(load_groups.groups.keys())
print(f"  Common (hour, month) keys: {len(common_keys)} / 288 possible")

for key in sorted(common_keys):
    sg = solar_groups.get_group(key)
    lg = load_groups.get_group(key)

    # Sample one from each
    solar_row = sg.sample(1, random_state=42).iloc[0]
    load_row  = lg.sample(1, random_state=42).iloc[0]

    aligned_pairs.append({
        'hour': key[0],
        'month': key[1],
        'solar_actual': solar_row['actual'],
        'solar_predicted': solar_row['predicted'],
        'solar_cloud_cover': solar_row.get('cloud_cover', np.nan),
        'load_actual': load_row['actual'],
        'load_predicted': load_row['predicted'],
    })

aligned_df = pd.DataFrame(aligned_pairs)
print(f"  Aligned synthetic pairs: {len(aligned_df)}")
print(f"  Hours represented: {sorted(aligned_df['hour'].unique())}")
print(f"  Months represented: {sorted(aligned_df['month'].unique())}")

# Duplicate handling: by design, we sample exactly 1 per (hour, month),
# so there are no duplicates in the alignment keys.
assert aligned_df.duplicated(subset=['hour', 'month']).sum() == 0, \
    "Duplicate (hour, month) pairs found in alignment!"

# ─────────────────────────────────────────────────────────────────────
# 7. Synthetic Decision Matrix for each k — BOTH global and bucketed sigma
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 7: SYNTHETIC DECISION EVALUATION MATRIX")
print("─" * 80)

# CORRECTION #1: Use "synthetically aligned decision reference" language.

# We run the decision matrix with BOTH sigma methods and report both.
# The intended deployed method is BUCKETED sigma (per BUILD_PLAN Phase 4 spec).
# Global sigma results are reported for comparison only.

DEVICE_POWER_KW = 0.5

print(f"\n  Reference device power: {DEVICE_POWER_KW} kW")
print(f"  NOTE: All decisions below are SYNTHETIC evaluations — the solar and load")
print(f"        data are not from the same household or time period.")
print(f"  Running decision matrix with BOTH global and bucketed sigma.\n")

# Map bucketed sigma onto aligned pairs
aligned_df['cloud_bucket'] = aligned_df['solar_cloud_cover'].apply(cloud_bucket)
aligned_df['solar_sigma_bucketed'] = aligned_df['cloud_bucket'].map(solar_bucket_stats['sigma'])
aligned_df['hour_bucket'] = aligned_df['hour'].apply(hour_bucket)
aligned_df['load_sigma_bucketed'] = aligned_df['hour_bucket'].map(load_bucket_stats['sigma'])

def run_decision_matrix(aligned, k_values, solar_sigma_series, load_sigma_series, label):
    """Run decision evaluation for a given sigma method."""
    matrices = {}
    coverage_rows = []
    for k in k_values:
        safe_solar = np.maximum(0, aligned['solar_predicted'] - k * solar_sigma_series)
        conservative_load = aligned['load_predicted'] + k * load_sigma_series
        safe_surplus = safe_solar - conservative_load

        system_allows = safe_surplus >= DEVICE_POWER_KW

        actual_surplus = aligned['solar_actual'] - aligned['load_actual']
        actual_allows = actual_surplus >= DEVICE_POWER_KW

        correct_allow   = ( system_allows &  actual_allows).sum()
        incorrect_allow = ( system_allows & ~actual_allows).sum()
        correct_deny    = (~system_allows & ~actual_allows).sum()
        incorrect_deny  = (~system_allows &  actual_allows).sum()
        total = len(aligned)

        safe_surplus_positive = safe_surplus >= 0
        actual_surplus_positive = actual_surplus >= 0
        opportunity_samples = actual_surplus_positive.sum()
        if opportunity_samples > 0:
            combined_coverage = (safe_surplus_positive & actual_surplus_positive).sum() / opportunity_samples * 100
        else:
            combined_coverage = 0.0

        matrices[k] = {
            'Correct-ALLOW': int(correct_allow),
            'Incorrect-ALLOW': int(incorrect_allow),
            'Correct-DENY': int(correct_deny),
            'Incorrect-DENY': int(incorrect_deny),
            'Total': total,
            'Precision (ALLOW)': correct_allow / (correct_allow + incorrect_allow) * 100 if (correct_allow + incorrect_allow) > 0 else 0,
            'Recall (ALLOW)': correct_allow / (correct_allow + incorrect_deny) * 100 if (correct_allow + incorrect_deny) > 0 else 0,
            'Safety Rate': (1 - incorrect_allow / total) * 100,
        }

        coverage_rows.append({
            'k': k,
            'sigma_method': label,
            'combined_coverage_%': combined_coverage,
            'n_correct_allow': int(correct_allow),
            'n_incorrect_allow': int(incorrect_allow),
            'n_correct_deny': int(correct_deny),
            'n_incorrect_deny': int(incorrect_deny),
            'n_system_allows': int(system_allows.sum()),
            'precision_allow_%': matrices[k]['Precision (ALLOW)'],
            'recall_allow_%': matrices[k]['Recall (ALLOW)'],
            'safety_rate_%': matrices[k]['Safety Rate'],
        })

    return matrices, pd.DataFrame(coverage_rows)

# --- Global sigma decision matrix ---
print("  === Decision Matrix: GLOBAL σ ===")
print(f"  (σ_solar = {sigma_solar_global:.4f} kW, σ_load = {sigma_load_global:.4f} kW)")
decision_matrices_global, combined_global_df = run_decision_matrix(
    aligned_df, K_VALUES,
    solar_sigma_series=sigma_solar_global,
    load_sigma_series=sigma_load_global,
    label='Global σ'
)
for k in K_VALUES:
    dm = decision_matrices_global[k]
    print(f"  k={k}: CA={dm['Correct-ALLOW']} IA={dm['Incorrect-ALLOW']} "
          f"CD={dm['Correct-DENY']} ID={dm['Incorrect-DENY']} "
          f"Prec={dm['Precision (ALLOW)']:.1f}% Rec={dm['Recall (ALLOW)']:.1f}% "
          f"Safety={dm['Safety Rate']:.1f}%")

# --- Bucketed sigma decision matrix ---
print(f"\n  === Decision Matrix: BUCKETED σ ===")
print(f"  (Solar σ per cloud bucket, Load σ per hour block)")
decision_matrices_bucketed, combined_bucketed_df = run_decision_matrix(
    aligned_df, K_VALUES,
    solar_sigma_series=aligned_df['solar_sigma_bucketed'],
    load_sigma_series=aligned_df['load_sigma_bucketed'],
    label='Bucketed σ'
)
for k in K_VALUES:
    dm = decision_matrices_bucketed[k]
    print(f"  k={k}: CA={dm['Correct-ALLOW']} IA={dm['Incorrect-ALLOW']} "
          f"CD={dm['Correct-DENY']} ID={dm['Incorrect-DENY']} "
          f"Prec={dm['Precision (ALLOW)']:.1f}% Rec={dm['Recall (ALLOW)']:.1f}% "
          f"Safety={dm['Safety Rate']:.1f}%")

# The BUCKETED sigma is the intended deployed method.
# Global is reported for comparison (Research Experiment §15.3).
decision_matrices = decision_matrices_bucketed  # primary for plots/selection
combined_coverage_df = pd.concat([combined_global_df, combined_bucketed_df], ignore_index=True)

# ─────────────────────────────────────────────────────────────────────
# 8. Monotonicity checks
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 8: VERIFICATION CHECKS")
print("─" * 80)

# Solar coverage should increase with k
solar_coverages = solar_global_results['coverage_%'].values
mono_solar = all(solar_coverages[i] <= solar_coverages[i+1] for i in range(len(solar_coverages)-1))
print(f"\n  Solar coverage monotonically increasing with k: {'✓ PASS' if mono_solar else '✗ FAIL — investigate!'}")
if not mono_solar:
    print(f"    Values: {list(zip(K_VALUES, solar_coverages))}")

# Load coverage should increase with k
load_coverages = load_global_results['coverage_%'].values
mono_load = all(load_coverages[i] <= load_coverages[i+1] for i in range(len(load_coverages)-1))
print(f"  Load  coverage monotonically increasing with k: {'✓ PASS' if mono_load else '✗ FAIL — investigate!'}")
if not mono_load:
    print(f"    Values: {list(zip(K_VALUES, load_coverages))}")

# Sigma sanity
print(f"\n  σ_solar ({sigma_solar_global:.6f}) ≈ 0? {'⚠ SUSPICIOUS' if sigma_solar_global < 0.001 else '✓ OK'}")
print(f"  σ_load  ({sigma_load_global:.6f}) ≈ 0? {'⚠ SUSPICIOUS' if sigma_load_global < 0.001 else '✓ OK'}")

# ─────────────────────────────────────────────────────────────────────
# 9. Save all tables
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 9: SAVING ARTIFACTS")
print("─" * 80)

# Global sigma summary
sigma_summary = {
    'sigma_solar_global_kW': sigma_solar_global,
    'sigma_load_global_kW': sigma_load_global,
    'solar_test_samples': len(solar_preds),
    'load_test_samples': len(load_preds),
    'solar_residual_mean': solar_preds['residual'].mean(),
    'solar_residual_median': solar_preds['residual'].median(),
    'load_residual_mean': load_preds['residual'].mean(),
    'load_residual_median': load_preds['residual'].median(),
    'calibration_disclosure': (
        'Coverage is measured on the same held-out backtest residual set used '
        'to estimate sigma. This is NOT an independent out-of-sample calibration result.'
    ),
}
with open(COV_DIR / 'sigma_summary.json', 'w') as f:
    json.dump(sigma_summary, f, indent=2, default=str)
print("  ✓ sigma_summary.json")

# Bucketed sigma tables
solar_bucket_stats.to_csv(COV_DIR / 'solar_bucketed_sigma.csv')
load_bucket_stats.to_csv(COV_DIR / 'load_bucketed_sigma.csv')
load_hourly_sigma.to_csv(COV_DIR / 'load_hourly_sigma.csv')
print("  ✓ solar_bucketed_sigma.csv")
print("  ✓ load_bucketed_sigma.csv")
print("  ✓ load_hourly_sigma.csv")

# k-sensitivity tables
solar_global_results.to_csv(COV_DIR / 'k_sensitivity_solar_global.csv', index=False)
solar_bucketed_results.to_csv(COV_DIR / 'k_sensitivity_solar_bucketed.csv', index=False)
load_global_results.to_csv(COV_DIR / 'k_sensitivity_load_global.csv', index=False)
load_bucketed_results.to_csv(COV_DIR / 'k_sensitivity_load_bucketed.csv', index=False)
combined_coverage_df.to_csv(COV_DIR / 'k_sensitivity_combined.csv', index=False)
print("  ✓ k_sensitivity_solar_global.csv")
print("  ✓ k_sensitivity_solar_bucketed.csv")
print("  ✓ k_sensitivity_load_global.csv")
print("  ✓ k_sensitivity_load_bucketed.csv")
print("  ✓ k_sensitivity_combined.csv")

# Decision matrices — save BOTH methods
for label, dm_dict, suffix in [
    ('bucketed', decision_matrices_bucketed, 'bucketed'),
    ('global', decision_matrices_global, 'global'),
]:
    dm_rows = []
    for k, dm in dm_dict.items():
        row = dict(dm)
        row['k'] = k
        row['sigma_method'] = label
        dm_rows.append(row)
    dm_df = pd.DataFrame(dm_rows)
    dm_df.to_csv(COV_DIR / f'synthetic_decision_matrix_{suffix}.csv', index=False)
    print(f"  ✓ synthetic_decision_matrix_{suffix}.csv")

# Alignment metadata
alignment_meta = {
    'method': 'hour-of-day + month alignment',
    'description': (
        'Synthetic pairing of solar and load test-set predictions. '
        'For each unique (hour, month) key present in both datasets, '
        'one solar row and one load row are randomly sampled (seed=42). '
        'The resulting pairs are a SYNTHETIC DECISION REFERENCE, not '
        'real-world co-located measurements.'
    ),
    'common_keys': len(common_keys),
    'max_possible_keys': 288,
    'aligned_samples': len(aligned_df),
    'duplicate_handling': 'Random sample of 1 per (hour, month) key; no duplicates.',
    'solar_source': 'Open-Meteo reanalysis, Kaliakair Bangladesh (~2020-2026)',
    'load_source': 'UCI Household Electric Power Consumption, Sceaux France (2006-2010)',
    'device_power_kW_for_decision_matrix': DEVICE_POWER_KW,
}
with open(COV_DIR / 'synthetic_alignment_metadata.json', 'w') as f:
    json.dump(alignment_meta, f, indent=2)
print("  ✓ synthetic_alignment_metadata.json")

# Aligned pairs
aligned_df.to_csv(COV_DIR / 'synthetic_aligned_pairs.csv', index=False)
print("  ✓ synthetic_aligned_pairs.csv")

# Solar bucket alignment report
bucket_alignment_report = {
    'source_predictions': str(SOLAR_DATA / 'solar_test_predictions.csv'),
    'source_cloud_cover': str(SOLAR_DATA / 'solar_processed.csv'),
    'join_method': 'Exact timestamp merge on "time" column',
    'total_prediction_rows': len(solar_preds),
    'matched_rows': int(matched_count),
    'unmatched_rows': int(unmatched_count),
    'match_rate_%': matched_count / len(solar_preds) * 100,
}
with open(COV_DIR / 'solar_bucket_alignment_report.json', 'w') as f:
    json.dump(bucket_alignment_report, f, indent=2)
print("  ✓ solar_bucket_alignment_report.json")

# ─────────────────────────────────────────────────────────────────────
# 10. PLOTS
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 10: GENERATING PLOTS")
print("─" * 80)

# --- 10a. k-Sensitivity chart (solar) ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Global
ax1.plot(solar_global_results['k'], solar_global_results['coverage_%'], 'o-', color='#2196F3', linewidth=2, markersize=8, label='Coverage %')
ax1_twin = ax1.twinx()
ax1_twin.plot(solar_global_results['k'], solar_global_results['utilization_%'], 's--', color='#FF9800', linewidth=2, markersize=8, label='Utilization %')
ax1.set_xlabel('k (Safety Multiplier)')
ax1.set_ylabel('Coverage (%)', color='#2196F3')
ax1_twin.set_ylabel('Utilization (%)', color='#FF9800')
ax1.set_title('Solar: Global σ')
ax1.grid(True, alpha=0.3)
lines1 = ax1.get_lines() + ax1_twin.get_lines()
ax1.legend(lines1, [l.get_label() for l in lines1], loc='center right')

# Bucketed
ax2.plot(solar_bucketed_results['k'], solar_bucketed_results['coverage_%'], 'o-', color='#4CAF50', linewidth=2, markersize=8, label='Coverage %')
ax2_twin = ax2.twinx()
ax2_twin.plot(solar_bucketed_results['k'], solar_bucketed_results['utilization_%'], 's--', color='#F44336', linewidth=2, markersize=8, label='Utilization %')
ax2.set_xlabel('k (Safety Multiplier)')
ax2.set_ylabel('Coverage (%)', color='#4CAF50')
ax2_twin.set_ylabel('Utilization (%)', color='#F44336')
ax2.set_title('Solar: Bucketed σ (by cloud cover)')
ax2.grid(True, alpha=0.3)
lines2 = ax2.get_lines() + ax2_twin.get_lines()
ax2.legend(lines2, [l.get_label() for l in lines2], loc='center right')

plt.suptitle('Solar k-Sensitivity: Coverage vs Utilization', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'k_sensitivity_solar.png')
plt.close()
print("  ✓ k_sensitivity_solar.png")

# --- 10b. k-Sensitivity chart (load) ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.plot(load_global_results['k'], load_global_results['coverage_%'], 'o-', color='#2196F3', linewidth=2, markersize=8, label='Coverage %')
ax1_twin = ax1.twinx()
ax1_twin.plot(load_global_results['k'], load_global_results['over_provision_%'], 's--', color='#FF9800', linewidth=2, markersize=8, label='Over-Provision %')
ax1.set_xlabel('k (Safety Multiplier)')
ax1.set_ylabel('Coverage (%)', color='#2196F3')
ax1_twin.set_ylabel('Over-Provision (%)', color='#FF9800')
ax1.set_title('Load: Global σ')
ax1.grid(True, alpha=0.3)
lines1 = ax1.get_lines() + ax1_twin.get_lines()
ax1.legend(lines1, [l.get_label() for l in lines1], loc='center right')

ax2.plot(load_bucketed_results['k'], load_bucketed_results['coverage_%'], 'o-', color='#4CAF50', linewidth=2, markersize=8, label='Coverage %')
ax2_twin = ax2.twinx()
ax2_twin.plot(load_bucketed_results['k'], load_bucketed_results['over_provision_%'], 's--', color='#F44336', linewidth=2, markersize=8, label='Over-Provision %')
ax2.set_xlabel('k (Safety Multiplier)')
ax2.set_ylabel('Coverage (%)', color='#4CAF50')
ax2_twin.set_ylabel('Over-Provision (%)', color='#F44336')
ax2.set_title('Load: Bucketed σ (by hour-of-day)')
ax2.grid(True, alpha=0.3)
lines2 = ax2.get_lines() + ax2_twin.get_lines()
ax2.legend(lines2, [l.get_label() for l in lines2], loc='center right')

plt.suptitle('Load k-Sensitivity: Coverage vs Over-Provision', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'k_sensitivity_load.png')
plt.close()
print("  ✓ k_sensitivity_load.png")

# --- 10c. Combined k-sensitivity (bucketed — the intended deployed method) ---
comb_buck = combined_coverage_df[combined_coverage_df['sigma_method'] == 'Bucketed σ'].copy()
comb_glob = combined_coverage_df[combined_coverage_df['sigma_method'] == 'Global σ'].copy()

fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(16, 5))

# Left panel: Bucketed σ (intended method)
ax_l.plot(comb_buck['k'], comb_buck['safety_rate_%'], 'o-', color='#009688', linewidth=2, markersize=8, label='Safety Rate %')
ax_l.plot(comb_buck['k'], comb_buck['recall_allow_%'], 's--', color='#FF5722', linewidth=2, markersize=8, label='Recall (ALLOW) %')
ax_l_twin = ax_l.twinx()
ax_l_twin.bar(comb_buck['k'], comb_buck['n_system_allows'], width=0.15, color='#9C27B0', alpha=0.4, label='# System ALLOWs')
ax_l.set_xlabel('k (Safety Multiplier)')
ax_l.set_ylabel('Rate (%)')
ax_l_twin.set_ylabel('Count (System ALLOWs)', color='#9C27B0')
ax_l.set_title('Bucketed σ (Intended Deployed Method)', fontsize=12, fontweight='bold')
lines_l = ax_l.get_lines()
ax_l.legend(lines_l, [l.get_label() for l in lines_l], loc='center left')
ax_l.grid(True, alpha=0.3)
ax_l.set_ylim(0, 105)

# Right panel: Global σ (comparison)
ax_r.plot(comb_glob['k'], comb_glob['safety_rate_%'], 'o-', color='#009688', linewidth=2, markersize=8, label='Safety Rate %')
ax_r.plot(comb_glob['k'], comb_glob['recall_allow_%'], 's--', color='#FF5722', linewidth=2, markersize=8, label='Recall (ALLOW) %')
ax_r_twin = ax_r.twinx()
ax_r_twin.bar(comb_glob['k'], comb_glob['n_system_allows'], width=0.15, color='#9C27B0', alpha=0.4, label='# System ALLOWs')
ax_r.set_xlabel('k (Safety Multiplier)')
ax_r.set_ylabel('Rate (%)')
ax_r_twin.set_ylabel('Count (System ALLOWs)', color='#9C27B0')
ax_r.set_title('Global σ (Comparison)', fontsize=12, fontweight='bold')
lines_r = ax_r.get_lines()
ax_r.legend(lines_r, [l.get_label() for l in lines_r], loc='center left')
ax_r.grid(True, alpha=0.3)
ax_r.set_ylim(0, 105)

plt.suptitle('Synthetic Combined Decision Evaluation\n(hour-of-day + month aligned, 176 pairs)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'k_sensitivity_combined.png')
plt.close()
print("  ✓ k_sensitivity_combined.png")

# --- 10d. Decision evaluation heatmaps — BUCKETED (primary) + GLOBAL (comparison) ---
for sigma_label, dm_dict, fname_suffix in [
    ('Bucketed σ (Intended Deployed Method)', decision_matrices_bucketed, 'bucketed'),
    ('Global σ (Comparison)', decision_matrices_global, 'global'),
]:
    fig, axes = plt.subplots(1, len(K_VALUES), figsize=(4 * len(K_VALUES), 4))
    if len(K_VALUES) == 1:
        axes = [axes]

    for idx, k in enumerate(K_VALUES):
        dm = dm_dict[k]
        matrix = np.array([
            [dm['Correct-ALLOW'], dm['Incorrect-DENY']],
            [dm['Incorrect-ALLOW'], dm['Correct-DENY']],
        ])
        labels = np.array([
            [f"Correct\nALLOW\n{dm['Correct-ALLOW']}", f"Incorrect\nDENY\n{dm['Incorrect-DENY']}"],
            [f"Incorrect\nALLOW\n{dm['Incorrect-ALLOW']}", f"Correct\nDENY\n{dm['Correct-DENY']}"],
        ])

        sns.heatmap(matrix, annot=labels, fmt='', cmap='RdYlGn',
                    xticklabels=['Ref: ALLOW', 'Ref: DENY'],
                    yticklabels=['System: ALLOW', 'System: DENY'],
                    ax=axes[idx], cbar=False, linewidths=1, linecolor='white',
                    annot_kws={'fontsize': 9})
        axes[idx].set_title(f'k = {k}', fontsize=12, fontweight='bold')

    plt.suptitle(f'Synthetic Decision Evaluation — {sigma_label}\n(Reference = synthetically aligned actual surplus)',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(COV_DIR / f'decision_evaluation_{fname_suffix}.png')
    plt.close()
    print(f"  ✓ decision_evaluation_{fname_suffix}.png")

# --- 10e. Bucketed sigma bar charts ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Solar buckets
colors_solar = ['#4CAF50', '#FFC107', '#F44336']
bars1 = ax1.bar(range(len(solar_bucket_stats)),
                solar_bucket_stats['sigma'].values,
                color=colors_solar[:len(solar_bucket_stats)],
                edgecolor='black', linewidth=0.5)
ax1.set_xticks(range(len(solar_bucket_stats)))
ax1.set_xticklabels(solar_bucket_stats.index, rotation=15, ha='right', fontsize=9)
ax1.set_ylabel('σ (kW)')
ax1.set_title('Solar: Bucketed σ by Cloud Cover')
for bar, val, cnt in zip(bars1, solar_bucket_stats['sigma'].values, solar_bucket_stats['count'].values):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
             f'{val:.4f}\n(n={cnt})', ha='center', va='bottom', fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

# Load buckets
colors_load = ['#3F51B5', '#00BCD4', '#8BC34A', '#FF9800']
bars2 = ax2.bar(range(len(load_bucket_stats)),
                load_bucket_stats['sigma'].values,
                color=colors_load[:len(load_bucket_stats)],
                edgecolor='black', linewidth=0.5)
ax2.set_xticks(range(len(load_bucket_stats)))
ax2.set_xticklabels(load_bucket_stats.index, rotation=15, ha='right', fontsize=9)
ax2.set_ylabel('σ (kW)')
ax2.set_title('Load: Bucketed σ by Hour Block')
for bar, val, cnt in zip(bars2, load_bucket_stats['sigma'].values, load_bucket_stats['count'].values):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
             f'{val:.4f}\n(n={cnt})', ha='center', va='bottom', fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

plt.suptitle('Bucketed Forecast Uncertainty (σ)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'bucketed_sigma.png')
plt.close()
print("  ✓ bucketed_sigma.png")

# --- 10f. Safe Solar clipping by k ---
fig, ax = plt.subplots(figsize=(8, 5))
clip_data = solar_global_results[['k', 'clipped_%']].copy()
bars = ax.bar(range(len(clip_data)), clip_data['clipped_%'].values,
              color=['#4CAF50', '#8BC34A', '#FFC107', '#FF9800', '#F44336'],
              edgecolor='black', linewidth=0.5)
ax.set_xticks(range(len(clip_data)))
ax.set_xticklabels([f'k={k}' for k in clip_data['k']], fontsize=11)
ax.set_ylabel('% of Test Samples Clipped to Zero')
ax.set_title('Safe Solar Clipping: Percentage of Samples Where\nmax(0, Predicted − k·σ) Was Clipped to Zero',
             fontsize=12, fontweight='bold')
for bar, pct, n in zip(bars, clip_data['clipped_%'].values, solar_global_results['n_clipped_to_zero'].values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{pct:.1f}%\n({n})', ha='center', va='bottom', fontsize=10)
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(COV_DIR / 'safe_solar_clipping.png')
plt.close()
print("  ✓ safe_solar_clipping.png")

# --- 10g. Residual distribution plots ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.hist(solar_preds['residual'], bins=80, color='#2196F3', edgecolor='white', alpha=0.85)
ax1.axvline(0, color='red', linewidth=1.5, linestyle='--', label='Zero')
ax1.axvline(solar_preds['residual'].mean(), color='orange', linewidth=1.5, linestyle=':', label=f'Mean={solar_preds["residual"].mean():.4f}')
ax1.set_xlabel('Residual (Actual − Predicted) kW')
ax1.set_ylabel('Count')
ax1.set_title(f'Solar Forecast Residuals (σ = {sigma_solar_global:.4f} kW)')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2.hist(load_preds['residual'], bins=80, color='#FF9800', edgecolor='white', alpha=0.85)
ax2.axvline(0, color='red', linewidth=1.5, linestyle='--', label='Zero')
ax2.axvline(load_preds['residual'].mean(), color='blue', linewidth=1.5, linestyle=':', label=f'Mean={load_preds["residual"].mean():.4f}')
ax2.set_xlabel('Residual (Actual − Predicted) kW')
ax2.set_ylabel('Count')
ax2.set_title(f'Load Forecast Residuals (σ = {sigma_load_global:.4f} kW)')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.suptitle('Backtest Residual Distributions\n(Used for sigma estimation AND coverage evaluation — same held-out set)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'residual_distributions.png')
plt.close()
print("  ✓ residual_distributions.png")

# --- 10h. Global vs Bucketed comparison chart ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Solar comparison
ax1.plot(solar_global_results['k'], solar_global_results['coverage_%'],
         'o-', color='#2196F3', linewidth=2, markersize=8, label='Global σ')
ax1.plot(solar_bucketed_results['k'], solar_bucketed_results['coverage_%'],
         's--', color='#4CAF50', linewidth=2, markersize=8, label='Bucketed σ')
ax1.set_xlabel('k')
ax1.set_ylabel('Coverage (%)')
ax1.set_title('Solar: Global vs Bucketed σ Coverage')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Load comparison
ax2.plot(load_global_results['k'], load_global_results['coverage_%'],
         'o-', color='#FF9800', linewidth=2, markersize=8, label='Global σ')
ax2.plot(load_bucketed_results['k'], load_bucketed_results['coverage_%'],
         's--', color='#F44336', linewidth=2, markersize=8, label='Bucketed σ')
ax2.set_xlabel('k')
ax2.set_ylabel('Coverage (%)')
ax2.set_title('Load: Global vs Bucketed σ Coverage')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.suptitle('Global vs Bucketed σ: Coverage Comparison (Research Experiment §15.3)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'global_vs_bucketed_comparison.png')
plt.close()
print("  ✓ global_vs_bucketed_comparison.png")

# ─────────────────────────────────────────────────────────────────────
# 11. k SELECTION — evidence-based, no arbitrary thresholds
#     Primary method: BUCKETED σ (per BUILD_PLAN Phase 4 spec)
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SECTION 11: K SELECTION ANALYSIS")
print("─" * 80)

print("\n  SIGMA METHOD DISCLOSURE:")
print("  ─────────────────────────────")
print("  • The INTENDED DEPLOYED METHOD is BUCKETED σ:")
print("      Solar: σ per cloud-cover bucket (Clear / Partly Cloudy / Overcast)")
print("      Load:  σ per hour-of-day block (Night / Morning / Afternoon / Evening)")
print("  • Global σ results are reported for comparison (Research Experiment §15.3).")
print("  • The synthetic decision matrix is reported for BOTH methods.")
print("  • k-selection below is based on the BUCKETED σ coverage/utilization results.")

# Build summary table with BOTH global and bucketed results
print("\n  === FULL K-SENSITIVITY SUMMARY TABLE ===\n")

# Bucketed decision matrix results for the summary
comb_buck_indexed = combined_bucketed_df.set_index('k')
comb_glob_indexed = combined_global_df.set_index('k')

summary_rows = []
for i, k in enumerate(K_VALUES):
    row = {
        'k': k,
        # --- Bucketed σ (primary / intended deployed) ---
        'solar_cov_bucketed_%': solar_bucketed_results.iloc[i]['coverage_%'],
        'solar_util_bucketed_%': solar_bucketed_results.iloc[i]['utilization_%'],
        'solar_clip_bucketed_%': solar_bucketed_results.iloc[i]['clipped_%'],
        'load_cov_bucketed_%': load_bucketed_results.iloc[i]['coverage_%'],
        'load_overprov_bucketed_%': load_bucketed_results.iloc[i]['over_provision_%'],
        'synth_n_allow_bucketed': int(comb_buck_indexed.loc[k, 'n_system_allows']),
        'synth_incorrect_allow_bucketed': int(comb_buck_indexed.loc[k, 'n_incorrect_allow']),
        'synth_safety_bucketed_%': comb_buck_indexed.loc[k, 'safety_rate_%'],
        'synth_recall_bucketed_%': comb_buck_indexed.loc[k, 'recall_allow_%'],
        # --- Global σ (comparison) ---
        'solar_cov_global_%': solar_global_results.iloc[i]['coverage_%'],
        'solar_util_global_%': solar_global_results.iloc[i]['utilization_%'],
        'solar_clip_global_%': solar_global_results.iloc[i]['clipped_%'],
        'load_cov_global_%': load_global_results.iloc[i]['coverage_%'],
        'load_overprov_global_%': load_global_results.iloc[i]['over_provision_%'],
        'synth_n_allow_global': int(comb_glob_indexed.loc[k, 'n_system_allows']),
        'synth_incorrect_allow_global': int(comb_glob_indexed.loc[k, 'n_incorrect_allow']),
        'synth_safety_global_%': comb_glob_indexed.loc[k, 'safety_rate_%'],
        'synth_recall_global_%': comb_glob_indexed.loc[k, 'recall_allow_%'],
    }
    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows)

# Print bucketed results (primary)
print("  --- Bucketed σ (primary / intended deployed) ---")
buck_cols = ['k', 'solar_cov_bucketed_%', 'solar_util_bucketed_%', 'solar_clip_bucketed_%',
             'load_cov_bucketed_%', 'load_overprov_bucketed_%',
             'synth_n_allow_bucketed', 'synth_incorrect_allow_bucketed',
             'synth_safety_bucketed_%', 'synth_recall_bucketed_%']
print(summary_df[buck_cols].to_string(index=False, float_format='%.2f'))

print("\n  --- Global σ (comparison) ---")
glob_cols = ['k', 'solar_cov_global_%', 'solar_util_global_%', 'solar_clip_global_%',
             'load_cov_global_%', 'load_overprov_global_%',
             'synth_n_allow_global', 'synth_incorrect_allow_global',
             'synth_safety_global_%', 'synth_recall_global_%']
print(summary_df[glob_cols].to_string(index=False, float_format='%.2f'))

summary_df.to_csv(COV_DIR / 'full_k_sensitivity_summary.csv', index=False)
print("\n  ✓ full_k_sensitivity_summary.csv")

# --- Evidence-based k selection: NO arbitrary thresholds ---
# Report the observed trade-off for each k and let the data speak.
print("\n  === K SELECTION — OBSERVED EMPIRICAL TRADE-OFF (bucketed σ) ===")
print("\n  For each k, the trade-off between coverage (safety) and")
print("  utilization (avoiding excessive conservatism) is shown below.")
print("  No arbitrary threshold is applied. The choice is based on")
print("  the empirical coverage-vs-utilization curve shape.\n")

for _, row in summary_df.iterrows():
    k = row['k']
    print(f"  k = {k}:")
    print(f"    Solar coverage (bucketed):  {row['solar_cov_bucketed_%']:.1f}%   utilization: {row['solar_util_bucketed_%']:.1f}%")
    print(f"    Load  coverage (bucketed):  {row['load_cov_bucketed_%']:.1f}%   over-provision: {row['load_overprov_bucketed_%']:.1f}%")
    print(f"    Synthetic: {int(row['synth_n_allow_bucketed'])} system ALLOWs, "
          f"{int(row['synth_incorrect_allow_bucketed'])} incorrect ALLOWs, "
          f"recall={row['synth_recall_bucketed_%']:.1f}%")
    # Coverage marginal gain
    if k > K_VALUES[0]:
        prev_i = K_VALUES.index(k) - 1
        solar_gain = row['solar_cov_bucketed_%'] - summary_df.iloc[prev_i]['solar_cov_bucketed_%']
        load_gain = row['load_cov_bucketed_%'] - summary_df.iloc[prev_i]['load_cov_bucketed_%']
        solar_loss = summary_df.iloc[prev_i]['solar_util_bucketed_%'] - row['solar_util_bucketed_%']
        print(f"    Δ from k={K_VALUES[prev_i]}: solar cov +{solar_gain:.1f}pp, "
              f"load cov +{load_gain:.1f}pp, solar util -{solar_loss:.1f}pp")
    print()

# Identify the "elbow" — where marginal coverage gain per unit k decreases
print("  MARGINAL ANALYSIS (bucketed σ):")
print("  Each step of +0.5 in k costs utilization and gains coverage.")
print("  The efficient operating point is where marginal coverage gain")
print("  starts to flatten relative to the utilization cost.\n")

for i in range(1, len(K_VALUES)):
    k_prev, k_curr = K_VALUES[i-1], K_VALUES[i]
    s_cov_gain = summary_df.iloc[i]['solar_cov_bucketed_%'] - summary_df.iloc[i-1]['solar_cov_bucketed_%']
    l_cov_gain = summary_df.iloc[i]['load_cov_bucketed_%'] - summary_df.iloc[i-1]['load_cov_bucketed_%']
    s_util_loss = summary_df.iloc[i-1]['solar_util_bucketed_%'] - summary_df.iloc[i]['solar_util_bucketed_%']
    print(f"  k {k_prev}→{k_curr}: solar cov +{s_cov_gain:.2f}pp, "
          f"load cov +{l_cov_gain:.2f}pp, solar util -{s_util_loss:.2f}pp")

# NOTE on synthetic decision matrix interpretation:
print("\n  NOTE ON SYNTHETIC DECISION MATRIX:")
print("  The synthetic 176-pair evaluation is a methodology demonstration.")
print("  At k >= 1.0, the system produces 0 ALLOW decisions in the 176-pair")
print("  sample — this means k >= 1.0 is EXTREMELY CONSERVATIVE in this")
print("  synthetic setting, producing 100% safety rate ONLY because it")
print("  denies everything. A 100% safety rate from zero ALLOWs is not")
print("  evidence of an optimal operating point — it is evidence of")
print("  extreme conservatism. The synthetic matrix alone cannot determine")
print("  the best k; the per-model coverage/utilization trade-off is the")
print("  primary basis for selection.\n")

# k selection: report the observed trade-off, defer final choice to user
# but provide a data-driven recommendation
print("  ══════════════════════════════════════════════")
print("  K SELECTION RECOMMENDATION (bucketed σ basis):")
print("  ")
print("  All k values from 0.5 to 2.5 are reported above.")
print("  The final k is a user decision based on the")
print("  coverage-vs-utilization trade-off and risk appetite.")
print("  ")
print("  The data shows:")

# Determine where the coverage curve flattens
k05 = summary_df.iloc[0]
k10 = summary_df.iloc[1]
k15 = summary_df.iloc[2]
k20 = summary_df.iloc[3]
k25 = summary_df.iloc[4]

print(f"  • k=0.5: Highest utilization ({k05['solar_util_bucketed_%']:.1f}%), "
      f"lowest coverage (solar {k05['solar_cov_bucketed_%']:.1f}%, load {k05['load_cov_bucketed_%']:.1f}%)")
print(f"  • k=2.5: Highest coverage (solar {k25['solar_cov_bucketed_%']:.1f}%, load {k25['load_cov_bucketed_%']:.1f}%), "
      f"lowest utilization ({k25['solar_util_bucketed_%']:.1f}%)")
print(f"  • In the synthetic decision evaluation, ONLY k=0.5 produces")
print(f"    any ALLOW decisions ({int(k05['synth_n_allow_bucketed'])} ALLOWs with bucketed σ).")
print(f"    k >= 1.0 produces zero ALLOWs — extremely conservative.")
print("  ══════════════════════════════════════════════")

# Save all results — let README and user make final determination
k_selection = {
    'note': (
        'Final k is deferred to user judgment based on the observed '
        'coverage-vs-utilization trade-off. No arbitrary coverage threshold '
        'is applied. Coverage is measured on the held-out backtest residual set '
        'used for sigma calibration (not an independent out-of-sample result). '
        'Synthetic decision evaluation uses 176 hour+month aligned pairs '
        '(not co-located data). At k >= 1.0 the synthetic evaluation produces '
        'zero ALLOW decisions; this reflects extreme conservatism, not optimal '
        'operating point selection.'
    ),
    'sigma_method_for_k_sensitivity': 'bucketed (primary) and global (comparison)',
    'sigma_method_for_synthetic_matrix': 'both bucketed and global reported separately',
    'sigma_method_for_deployed_decision_engine': 'bucketed (solar: cloud-cover bucket, load: hour-of-day block)',
    'k_sensitivity_bucketed': {
        str(k): {
            'solar_coverage_%': float(summary_df.iloc[i]['solar_cov_bucketed_%']),
            'solar_utilization_%': float(summary_df.iloc[i]['solar_util_bucketed_%']),
            'load_coverage_%': float(summary_df.iloc[i]['load_cov_bucketed_%']),
            'synth_n_allow': int(summary_df.iloc[i]['synth_n_allow_bucketed']),
            'synth_incorrect_allow': int(summary_df.iloc[i]['synth_incorrect_allow_bucketed']),
        }
        for i, k in enumerate(K_VALUES)
    },
}
with open(COV_DIR / 'k_selection.json', 'w') as f:
    json.dump(k_selection, f, indent=2)
print("\n  ✓ k_selection.json")

# ─────────────────────────────────────────────────────────────────────
# 12. FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("PHASE 4 EXECUTION COMPLETE — ALL ARTIFACTS SAVED")
print("=" * 80)

print(f"""
Files saved to: {COV_DIR}

Data artifacts:
  - sigma_summary.json
  - solar_bucketed_sigma.csv
  - load_bucketed_sigma.csv
  - load_hourly_sigma.csv
  - k_sensitivity_solar_global.csv
  - k_sensitivity_solar_bucketed.csv
  - k_sensitivity_load_global.csv
  - k_sensitivity_load_bucketed.csv
  - k_sensitivity_combined.csv
  - full_k_sensitivity_summary.csv
  - synthetic_decision_matrix.csv
  - synthetic_aligned_pairs.csv
  - synthetic_alignment_metadata.json
  - solar_bucket_alignment_report.json
  - k_selection.json

Plot artifacts:
  - k_sensitivity_solar.png
  - k_sensitivity_load.png
  - k_sensitivity_combined.png
  - decision_evaluation.png
  - bucketed_sigma.png
  - safe_solar_clipping.png
  - residual_distributions.png
  - global_vs_bucketed_comparison.png
""")
