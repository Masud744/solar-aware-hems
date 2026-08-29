"""
Phase 3 -- SHAP Explainability (XAI)
=====================================
Runs TreeExplainer on the best corrected models from Phase 1 (solar RF)
and Phase 2 (load RF). Generates all required SHAP outputs:
  - Summary bar plot
  - Beeswarm / dot plot
  - Dependence plot for top feature
  - Force plot (two contrasting examples per model)
  - Waterfall plot (two contrasting examples per model)
  - Top-feature-contributors table
  - Numerical verification: base_value + sum(shap_values) ≈ prediction

Reference: BUILD_PLAN.md Phase 3
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
import shap

warnings.filterwarnings('ignore')

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
XAI_DIR = os.path.join(PROJECT_ROOT, 'ml', 'xai')
OUTPUT_DIR = os.path.join(XAI_DIR, 'shap_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Model and data paths
SOLAR_MODEL_PATH = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'models', 'rf_corrected.joblib')
SOLAR_DATA_PATH = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'data', 'solar_processed.csv')

LOAD_MODEL_PATH = os.path.join(PROJECT_ROOT, 'ml', 'load', 'models', 'rf_corrected.joblib')
LOAD_DATA_PATH = os.path.join(PROJECT_ROOT, 'ml', 'load', 'data', 'load_processed_clean.csv')

# Plot settings
plt.style.use('seaborn-v0_8-whitegrid')
DPI = 150

print("=" * 70)
print("PHASE 3 -- SHAP EXPLAINABILITY (XAI)")
print("=" * 70)

# ===================================================================
# HELPER: run full SHAP analysis for one model
# ===================================================================
def run_shap_analysis(model, X_test, y_test, feature_names, model_name, prefix):
    """Run TreeExplainer and generate all SHAP outputs for one model."""
    
    print(f"\n{'='*60}")
    print(f"SHAP ANALYSIS: {model_name}")
    print(f"{'='*60}")
    
    # --- 1. TreeExplainer ---
    print(f"\n[1] Running TreeExplainer...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    base_value = explainer.expected_value
    # In some SHAP versions, expected_value is a 1-element array
    if hasattr(base_value, '__len__'):
        base_value = float(base_value[0]) if len(base_value) == 1 else float(base_value)
    else:
        base_value = float(base_value)
    print(f"  Base value (E[f(x)]): {base_value:.4f}")
    print(f"  SHAP values shape: {shap_values.shape}")
    
    # --- 2. Numerical verification: base + sum(shap) ≈ prediction ---
    print(f"\n[2] Numerical verification: base_value + sum(SHAP) ≈ prediction...")
    predictions = model.predict(X_test)
    shap_sums = base_value + shap_values.sum(axis=1)
    reconstruction_errors = np.abs(predictions - shap_sums)
    
    print(f"  Max reconstruction error:  {reconstruction_errors.max():.2e}")
    print(f"  Mean reconstruction error: {reconstruction_errors.mean():.2e}")
    print(f"  All within 1e-6: {(reconstruction_errors < 1e-6).all()}")
    
    # Show 5 individual checks
    print(f"\n  Sample-level verification (first 5 test rows):")
    print(f"  {'Row':>5}  {'Prediction':>12}  {'base+sum(SHAP)':>15}  {'Error':>12}")
    print(f"  {'-'*50}")
    for i in range(min(5, len(predictions))):
        pred = predictions[i]
        recon = shap_sums[i]
        err = reconstruction_errors[i]
        print(f"  {i:5d}  {pred:12.6f}  {recon:15.6f}  {err:12.2e}")
    
    verification_results = {
        'model': model_name,
        'base_value': float(base_value),
        'max_reconstruction_error': float(reconstruction_errors.max()),
        'mean_reconstruction_error': float(reconstruction_errors.mean()),
        'all_within_1e-6': bool((reconstruction_errors < 1e-6).all()),
        'n_test_samples': len(predictions)
    }
    
    # --- 3. Summary bar plot ---
    print(f"\n[3] Generating summary bar plot...")
    fig, ax = plt.subplots(figsize=(10, max(4, len(feature_names) * 0.4)), dpi=DPI)
    shap.summary_plot(shap_values, X_test, feature_names=feature_names,
                      plot_type='bar', show=False, max_display=20)
    plt.title(f'{model_name} — SHAP Feature Importance (mean |SHAP|)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{prefix}_summary_bar.png'), bbox_inches='tight')
    plt.close('all')
    print(f"  > {prefix}_summary_bar.png")
    
    # --- 4. Beeswarm / dot plot ---
    print(f"\n[4] Generating beeswarm plot...")
    fig, ax = plt.subplots(figsize=(10, max(4, len(feature_names) * 0.4)), dpi=DPI)
    shap.summary_plot(shap_values, X_test, feature_names=feature_names,
                      plot_type='dot', show=False, max_display=20)
    plt.title(f'{model_name} — SHAP Beeswarm Plot', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{prefix}_beeswarm.png'), bbox_inches='tight')
    plt.close('all')
    print(f"  > {prefix}_beeswarm.png")
    
    # --- 5. Dependence plot for top feature ---
    print(f"\n[5] Generating dependence plot for top feature...")
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    top_feature_idx = np.argmax(mean_abs_shap)
    top_feature_name = feature_names[top_feature_idx]
    print(f"  Top feature: {top_feature_name} (mean |SHAP| = {mean_abs_shap[top_feature_idx]:.4f})")
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    shap.dependence_plot(top_feature_idx, shap_values, X_test,
                         feature_names=feature_names, show=False, ax=ax)
    ax.set_title(f'{model_name} — SHAP Dependence: {top_feature_name}', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{prefix}_dependence_{top_feature_name}.png'), bbox_inches='tight')
    plt.close('all')
    print(f"  > {prefix}_dependence_{top_feature_name}.png")
    
    # --- 6. Select contrasting examples for force/waterfall ---
    print(f"\n[6] Selecting contrasting examples...")
    # High prediction case and low prediction case
    high_idx = np.argmax(predictions)
    low_idx = np.argmin(predictions)
    # Also find a "medium" case near the median
    median_val = np.median(predictions)
    med_idx = np.argmin(np.abs(predictions - median_val))
    
    print(f"  High case: row {high_idx}, prediction={predictions[high_idx]:.4f}, actual={y_test.iloc[high_idx]:.4f}")
    print(f"  Low case:  row {low_idx}, prediction={predictions[low_idx]:.4f}, actual={y_test.iloc[low_idx]:.4f}")
    
    cases = [
        (high_idx, 'high', f'High {model_name.split()[0]}'),
        (low_idx, 'low', f'Low {model_name.split()[0]}'),
    ]
    
    # --- 7. Force plots ---
    print(f"\n[7] Generating force plots...")
    for idx, label, desc in cases:
        explanation = shap.Explanation(
            values=shap_values[idx],
            base_values=base_value,
            data=X_test.iloc[idx].values,
            feature_names=feature_names
        )
        fig = plt.figure(figsize=(16, 4), dpi=DPI)
        shap.plots.force(explanation, show=False, matplotlib=True)
        plt.title(f'{model_name} — Force Plot ({desc}, pred={predictions[idx]:.3f})', fontsize=12, pad=40)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'{prefix}_force_{label}.png'), bbox_inches='tight')
        plt.close('all')
        print(f"  > {prefix}_force_{label}.png ({desc})")
    
    # --- 8. Waterfall plots ---
    print(f"\n[8] Generating waterfall plots...")
    for idx, label, desc in cases:
        explanation = shap.Explanation(
            values=shap_values[idx],
            base_values=base_value,
            data=X_test.iloc[idx].values,
            feature_names=feature_names
        )
        fig = plt.figure(figsize=(10, max(5, len(feature_names) * 0.35)), dpi=DPI)
        shap.plots.waterfall(explanation, show=False, max_display=15)
        plt.title(f'{model_name} — Waterfall ({desc}, pred={predictions[idx]:.3f})', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'{prefix}_waterfall_{label}.png'), bbox_inches='tight')
        plt.close('all')
        print(f"  > {prefix}_waterfall_{label}.png ({desc})")
    
    # --- 9. Feature-effect direction check ---
    print(f"\n[9] Feature-effect direction analysis...")
    direction_report = []
    for i, fname in enumerate(feature_names):
        feature_vals = X_test.iloc[:, i].values
        shap_col = shap_values[:, i]
        
        # Compute correlation between feature value and SHAP value
        if np.std(feature_vals) > 0 and np.std(shap_col) > 0:
            corr = np.corrcoef(feature_vals, shap_col)[0, 1]
        else:
            corr = 0.0
        
        mean_abs = mean_abs_shap[i]
        direction = "+" if corr > 0.1 else ("-" if corr < -0.1 else "~0")
        
        direction_report.append({
            'feature': fname,
            'mean_abs_shap': round(float(mean_abs), 6),
            'shap_feature_corr': round(float(corr), 4),
            'effect_direction': direction
        })
        
        if mean_abs > 0.01:  # Only print significant features
            print(f"  {fname:25s}: mean|SHAP|={mean_abs:.4f}, corr={corr:+.3f} ({direction})")
    
    # --- 10. Top feature contributors table ---
    print(f"\n[10] Building top-feature-contributors table...")
    contrib_df = pd.DataFrame(direction_report)
    contrib_df = contrib_df.sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
    contrib_df.to_csv(os.path.join(OUTPUT_DIR, f'{prefix}_feature_contributors.csv'), index=False)
    print(f"  > {prefix}_feature_contributors.csv")
    print(f"\n  Top 5 contributors:")
    print(contrib_df.head(5).to_string(index=False))
    
    return verification_results, direction_report, cases, predictions


# ===================================================================
# SOLAR MODEL SHAP
# ===================================================================
print("\n" + "=" * 70)
print("LOADING SOLAR MODEL & DATA")
print("=" * 70)

solar_model = joblib.load(SOLAR_MODEL_PATH)
solar_data = pd.read_csv(SOLAR_DATA_PATH, index_col=0, parse_dates=True)

# Recreate the corrected feature set (must match training)
SOLAR_FEATURES = ['cloud_cover', 'temperature', 'relative_humidity',
                   'wind_speed', 'hour', 'month', 'day_of_year']
SOLAR_TARGET = 'solar_power_kW'

# Chronological split (same as training: 80/20)
split_idx = int(len(solar_data) * 0.8)
solar_test = solar_data.iloc[split_idx:]
X_solar_test = solar_test[SOLAR_FEATURES]
y_solar_test = solar_test[SOLAR_TARGET]
print(f"Solar test set: {len(X_solar_test)} rows")
print(f"Solar features: {SOLAR_FEATURES}")

solar_verification, solar_directions, solar_cases, solar_preds = run_shap_analysis(
    solar_model, X_solar_test, y_solar_test, SOLAR_FEATURES,
    'Solar RF (Corrected)', 'solar'
)

# ===================================================================
# LOAD MODEL SHAP
# ===================================================================
print("\n" + "=" * 70)
print("LOADING LOAD MODEL & DATA")
print("=" * 70)

load_model = joblib.load(LOAD_MODEL_PATH)
load_data = pd.read_csv(LOAD_DATA_PATH, index_col=0, parse_dates=True)

# Recreate the corrected feature set (must match training)
LOAD_FEATURES = [
    'power_lag_1', 'power_lag_2', 'power_lag_3', 'power_lag_12',
    'power_lag_24', 'power_lag_48', 'power_lag_168',
    'rolling_mean_3h', 'rolling_mean_24h', 'rolling_std_24h', 'rolling_mean_168h',
    'hour', 'day_of_week', 'month', 'is_weekend', 'T2M'
]
LOAD_TARGET = 'Global_active_power'

# Chronological split (same as training: 80/20)
split_idx = int(len(load_data) * 0.8)
load_test = load_data.iloc[split_idx:]
X_load_test = load_test[LOAD_FEATURES]
y_load_test = load_test[LOAD_TARGET]
print(f"Load test set: {len(X_load_test)} rows")
print(f"Load features: {LOAD_FEATURES}")

load_verification, load_directions, load_cases, load_preds = run_shap_analysis(
    load_model, X_load_test, y_load_test, LOAD_FEATURES,
    'Load RF (Corrected)', 'load'
)

# ===================================================================
# DIRECTION SANITY CHECKS
# ===================================================================
print("\n" + "=" * 70)
print("FEATURE-EFFECT DIRECTION SANITY CHECKS")
print("=" * 70)

print("\n--- SOLAR MODEL ---")
solar_dir_dict = {d['feature']: d for d in solar_directions}

checks = [
    ('cloud_cover', '-', 'Higher cloud cover should push solar prediction DOWN'),
    ('hour', '+', 'Midday hours (high irradiance) should push solar prediction UP'),
    ('relative_humidity', '-', 'Higher humidity correlates with less clear sky'),
    ('temperature', '+', 'Higher temp correlates with sunny conditions (though panel efficiency decreases, net effect is typically positive due to seasonal correlation)'),
]
print(f"\n  {'Feature':25s}  {'Expected':>8}  {'Actual':>8}  {'Corr':>8}  {'Status':>8}")
print(f"  {'-'*65}")
for feat, expected_dir, reason in checks:
    if feat in solar_dir_dict:
        d = solar_dir_dict[feat]
        actual = d['effect_direction']
        corr = d['shap_feature_corr']
        status = 'OK' if actual == expected_dir or actual == '~0' else 'CHECK'
        print(f"  {feat:25s}  {expected_dir:>8}  {actual:>8}  {corr:>+8.3f}  {status:>8}")
        if status == 'CHECK':
            print(f"    NOTE: {reason}")
            print(f"    Actual direction {actual} vs expected {expected_dir} — may need investigation")

print("\n--- LOAD MODEL ---")
load_dir_dict = {d['feature']: d for d in load_directions}
checks_load = [
    ('power_lag_1', '+', 'Higher recent consumption suggests continued high consumption'),
    ('hour', '+', 'Effect is non-monotonic (U-shaped); correlation may be weak/positive'),
    ('T2M', '-', 'Higher temp → less heating → lower load (European household in winter-dominated period). NOTE: T2M is same-timestamp observed, not forecast.'),
]
print(f"\n  {'Feature':25s}  {'Expected':>8}  {'Actual':>8}  {'Corr':>8}  {'Status':>8}")
print(f"  {'-'*65}")
for feat, expected_dir, reason in checks_load:
    if feat in load_dir_dict:
        d = load_dir_dict[feat]
        actual = d['effect_direction']
        corr = d['shap_feature_corr']
        status = 'OK' if actual == expected_dir or actual == '~0' else 'CHECK'
        print(f"  {feat:25s}  {expected_dir:>8}  {actual:>8}  {corr:>+8.3f}  {status:>8}")
        if status == 'CHECK':
            print(f"    NOTE: {reason}")

# ===================================================================
# SAVE VERIFICATION RESULTS
# ===================================================================
print("\n" + "=" * 70)
print("SAVING VERIFICATION RESULTS")
print("=" * 70)

all_verification = {
    'solar': solar_verification,
    'load': load_verification,
}
with open(os.path.join(OUTPUT_DIR, 'shap_verification.json'), 'w') as f:
    json.dump(all_verification, f, indent=2)
print(f"  > shap_verification.json")

# List all generated files
print("\n--- All generated files ---")
for f_name in sorted(os.listdir(OUTPUT_DIR)):
    f_path = os.path.join(OUTPUT_DIR, f_name)
    size = os.path.getsize(f_path)
    print(f"  {f_name:50s}  {size:>8d} bytes")

# ===================================================================
# SUMMARY
# ===================================================================
print("\n" + "=" * 70)
print("PHASE 3 SHAP ANALYSIS COMPLETE")
print("=" * 70)
print(f"\nSolar verification: base+sum(SHAP) error max={solar_verification['max_reconstruction_error']:.2e}")
print(f"Load  verification: base+sum(SHAP) error max={load_verification['max_reconstruction_error']:.2e}")
print(f"\nAll outputs saved to: {OUTPUT_DIR}")
print(f"\n>>> Run Phase 3 Verification Gate checks next.")
