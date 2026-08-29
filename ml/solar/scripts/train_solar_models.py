"""
Phase 1 — Solar Model Training Pipeline
========================================
Trains solar power forecasting models on Open-Meteo data for Kaliakair, BD.

Produces:
  - EDA plots (5 figures)
  - Leaky baseline model (GTI as input — intentionally circular, for paper comparison)
  - 5 corrected models (RF, XGB, SVR, DT, Linear) on non-circular features
  - Physical formula row (no ML)
  - Per-model diagnostic plots (scatter, time-series, residuals, residual histogram, feature importance)
  - Comparison table (.csv + .json) and grouped bar chart

Reference: BUILD_PLAN.md Phase 1, PROJECT_MASTER_CONTEXT.md §4.1
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

warnings.filterwarnings('ignore')

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DATA_RAW = os.path.join(PROJECT_ROOT, 'Dataset', 'kaliakair_openmeteo_solar_raw.csv')
DATA_DIR = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'models')
METRICS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'results', 'metrics')
PLOTS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'results', 'plots')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'solar', 'results')

# ─── Panel / System Constants ────────────────────────────────────────────────
# Confirmed: 5 panels (code comment "৫টি প্যানেলের জন্য" is correct; 10 was a bug)
PANEL_AREA = 2.42        # m²
PANEL_EFFICIENCY = 0.19
SYSTEM_PERFORMANCE = 0.92
NUMBER_OF_PANELS = 5     # Fixed from 10 → 5 per user confirmation

# ─── 1. Load & Prepare Data ─────────────────────────────────────────────────
print("=" * 70)
print("PHASE 1 — SOLAR MODEL TRAINING")
print("=" * 70)

print("\n[1/10] Loading raw data...")
df = pd.read_csv(DATA_RAW, encoding='utf-8-sig')
print(f"  Raw shape: {df.shape}")

# Rename columns for convenience
df.columns = [
    'time', 'temperature', 'shortwave_radiation', 'direct_radiation',
    'diffuse_radiation', 'direct_normal_irradiance', 'gti',
    'relative_humidity', 'cloud_cover', 'wind_speed'
]

# Parse datetime
df['time'] = pd.to_datetime(df['time'], format='mixed', dayfirst=False)
df = df.sort_values('time').reset_index(drop=True)

# Check datetime continuity
time_diffs = df['time'].diff().dropna()
expected_freq = pd.Timedelta(hours=1)
gaps = time_diffs[time_diffs != expected_freq]
print(f"  Date range: {df['time'].min()} → {df['time'].max()}")
print(f"  Expected hourly frequency. Gaps found: {len(gaps)}")
if len(gaps) > 0:
    print(f"  Gap details (first 10): {gaps.head(10).values}")

# Compute target variable: solar_power_kW
df['solar_power_kW'] = (
    df['gti'] * PANEL_AREA * PANEL_EFFICIENCY * SYSTEM_PERFORMANCE * NUMBER_OF_PANELS / 1000
)

# Extract calendar features (useful for corrected models)
df['hour'] = df['time'].dt.hour
df['month'] = df['time'].dt.month
df['day_of_year'] = df['time'].dt.dayofyear

# Save processed data
processed_path = os.path.join(DATA_DIR, 'solar_processed.csv')
df.to_csv(processed_path, index=False)
print(f"  Processed data saved → {processed_path}")

# Basic stats
print(f"\n  Target (solar_power_kW) stats:")
print(f"    Mean:   {df['solar_power_kW'].mean():.4f} kW")
print(f"    Median: {df['solar_power_kW'].median():.4f} kW")
print(f"    Max:    {df['solar_power_kW'].max():.4f} kW")
print(f"    Std:    {df['solar_power_kW'].std():.4f} kW")
print(f"    Zero-power hours: {(df['solar_power_kW'] == 0).sum()} / {len(df)} "
      f"({(df['solar_power_kW'] == 0).mean()*100:.1f}%)")

# ─── 2. EDA Plots ───────────────────────────────────────────────────────────
print("\n[2/10] Generating EDA plots...")

# Set consistent plot style
plt.style.use('seaborn-v0_8-whitegrid')
FIGSIZE = (12, 6)
DPI = 150

# 2a. Target distribution histogram
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
ax.hist(df['solar_power_kW'], bins=80, color='#2196F3', edgecolor='white', alpha=0.85)
ax.set_xlabel('Solar Power (kW)', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title('Distribution of Solar Power Output (5 Panels, Kaliakair BD)', fontsize=14)
ax.axvline(df['solar_power_kW'].mean(), color='red', linestyle='--', label=f"Mean: {df['solar_power_kW'].mean():.2f} kW")
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_target_distribution.png'))
plt.close()
print("  ✅ eda_target_distribution.png")

# 2b. Full-period time-series (subsample for readability)
fig, ax = plt.subplots(figsize=(14, 5), dpi=DPI)
# Plot weekly max for full-period visibility
weekly = df.set_index('time')['solar_power_kW'].resample('W').agg(['mean', 'max'])
ax.fill_between(weekly.index, 0, weekly['max'], alpha=0.3, color='#FF9800', label='Weekly Max')
ax.plot(weekly.index, weekly['mean'], color='#E65100', linewidth=1.2, label='Weekly Mean')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Solar Power (kW)', fontsize=12)
ax.set_title('Solar Power Output Over Full Period (2020–2026)', fontsize=14)
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_timeseries_full.png'))
plt.close()
print("  ✅ eda_timeseries_full.png")

# 2c. Hourly boxplot
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
# Filter only daytime for better visualization
daytime = df[df['solar_power_kW'] > 0]
daytime.boxplot(column='solar_power_kW', by='hour', ax=ax,
                patch_artist=True,
                boxprops=dict(facecolor='#FFF3E0', color='#E65100'),
                medianprops=dict(color='#BF360C', linewidth=2),
                whiskerprops=dict(color='#E65100'),
                capprops=dict(color='#E65100'),
                flierprops=dict(marker='.', markersize=2, alpha=0.3))
ax.set_xlabel('Hour of Day', fontsize=12)
ax.set_ylabel('Solar Power (kW)', fontsize=12)
ax.set_title('Solar Power by Hour of Day (Daytime Only)', fontsize=14)
fig.suptitle('')  # Remove auto-generated title
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_hourly_boxplot.png'))
plt.close()
print("  ✅ eda_hourly_boxplot.png")

# 2d. Monthly boxplot
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
daytime.boxplot(column='solar_power_kW', by='month', ax=ax,
                patch_artist=True,
                boxprops=dict(facecolor='#E3F2FD', color='#1565C0'),
                medianprops=dict(color='#0D47A1', linewidth=2),
                whiskerprops=dict(color='#1565C0'),
                capprops=dict(color='#1565C0'),
                flierprops=dict(marker='.', markersize=2, alpha=0.3))
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Solar Power (kW)', fontsize=12)
ax.set_title('Solar Power by Month (Seasonal Pattern)', fontsize=14)
fig.suptitle('')
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_monthly_boxplot.png'))
plt.close()
print("  ✅ eda_monthly_boxplot.png")

# 2e. Correlation heatmap of all candidate input features
feature_cols = ['temperature', 'shortwave_radiation', 'direct_radiation',
                'diffuse_radiation', 'direct_normal_irradiance', 'gti',
                'relative_humidity', 'cloud_cover', 'wind_speed',
                'hour', 'month', 'solar_power_kW']
corr = df[feature_cols].corr()
fig, ax = plt.subplots(figsize=(10, 8), dpi=DPI)
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdYlBu_r',
            center=0, square=True, linewidths=0.5, ax=ax,
            cbar_kws={'shrink': 0.8})
ax.set_title('Feature Correlation Heatmap (Including Target)', fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_correlation_heatmap.png'))
plt.close()
print("  ✅ eda_correlation_heatmap.png")

# ─── 3. Train/Test Split (chronological) ────────────────────────────────────
print("\n[3/10] Preparing train/test split (chronological, shuffle=False)...")

# Use 80/20 chronological split
split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx].copy()
test_df = df.iloc[split_idx:].copy()
print(f"  Train: {len(train_df)} rows ({train_df['time'].min()} → {train_df['time'].max()})")
print(f"  Test:  {len(test_df)} rows ({test_df['time'].min()} → {test_df['time'].max()})")

# ─── 4. Define Feature Sets ─────────────────────────────────────────────────
# Leaky features (includes GTI — intentionally circular)
LEAKY_FEATURES = ['temperature', 'shortwave_radiation', 'direct_radiation',
                  'diffuse_radiation', 'direct_normal_irradiance', 'gti',
                  'relative_humidity', 'cloud_cover', 'wind_speed']

# Corrected features (only forecast-available variables, NO GTI/DNI/DHI)
CORRECTED_FEATURES = ['cloud_cover', 'temperature', 'relative_humidity',
                      'wind_speed', 'hour', 'month', 'day_of_year']

TARGET = 'solar_power_kW'

# ─── Helper: compute metrics ────────────────────────────────────────────────
def compute_metrics(y_true, y_pred, model_name):
    """Compute MAE, RMSE, R², MAPE (avoiding division by zero)."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # MAPE: only on non-zero actuals to avoid inf
    nonzero_mask = y_true > 0.001  # small threshold to avoid near-zero noise
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100
    else:
        mape = np.nan

    metrics = {
        'model': model_name,
        'MAE_kW': round(mae, 6),
        'RMSE_kW': round(rmse, 6),
        'R2': round(r2, 6),
        'MAPE_%': round(mape, 4) if not np.isnan(mape) else None
    }
    return metrics


# ─── Helper: generate per-model diagnostic plots ────────────────────────────
def generate_model_plots(y_true, y_pred, time_index, model_name, has_feature_importance=False,
                         feature_importances=None, feature_names=None):
    """Generate the standard 4-5 plot set per model."""
    prefix = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')

    # (a) Actual vs Predicted — time-series overlay
    fig, ax = plt.subplots(figsize=(14, 5), dpi=DPI)
    # Subsample for readability if too many points
    n = len(y_true)
    if n > 2000:
        step = max(1, n // 2000)
        idx = slice(None, None, step)
    else:
        idx = slice(None)
    ax.plot(time_index[idx], y_true.values[idx], label='Actual', color='#1565C0', linewidth=0.8, alpha=0.8)
    ax.plot(time_index[idx], y_pred[idx], label='Predicted', color='#E65100', linewidth=0.8, alpha=0.8)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Solar Power (kW)', fontsize=12)
    ax.set_title(f'{model_name} — Actual vs Predicted (Test Set)', fontsize=14)
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_timeseries.png'))
    plt.close()

    # (b) Actual vs Predicted — scatter with y=x line and R² annotation
    fig, ax = plt.subplots(figsize=(8, 8), dpi=DPI)
    ax.scatter(y_true, y_pred, alpha=0.15, s=8, color='#1565C0', edgecolors='none')
    lims = [0, max(y_true.max(), y_pred.max()) * 1.05]
    ax.plot(lims, lims, 'r--', linewidth=1.5, label='y = x (perfect)')
    r2 = r2_score(y_true, y_pred)
    ax.text(0.05, 0.92, f'R² = {r2:.4f}', transform=ax.transAxes,
            fontsize=14, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax.set_xlabel('Actual Solar Power (kW)', fontsize=12)
    ax.set_ylabel('Predicted Solar Power (kW)', fontsize=12)
    ax.set_title(f'{model_name} — Actual vs Predicted Scatter', fontsize=14)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_aspect('equal')
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_scatter.png'))
    plt.close()

    # (c) Residual vs Predicted
    residuals = y_true.values - y_pred
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    ax.scatter(y_pred, residuals, alpha=0.12, s=6, color='#4CAF50', edgecolors='none')
    ax.axhline(0, color='red', linestyle='--', linewidth=1.2)
    ax.set_xlabel('Predicted Solar Power (kW)', fontsize=12)
    ax.set_ylabel('Residual (Actual − Predicted) (kW)', fontsize=12)
    ax.set_title(f'{model_name} — Residuals vs Predicted', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_residuals.png'))
    plt.close()

    # (d) Residual distribution histogram
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    ax.hist(residuals, bins=80, color='#9C27B0', edgecolor='white', alpha=0.8)
    ax.axvline(0, color='red', linestyle='--', linewidth=1.2)
    ax.axvline(np.mean(residuals), color='orange', linestyle='--', linewidth=1.2,
               label=f'Mean: {np.mean(residuals):.4f} kW')
    ax.set_xlabel('Residual (kW)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'{model_name} — Residual Distribution', fontsize=14)
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_residual_hist.png'))
    plt.close()

    # (e) Feature importance (tree-based models only)
    if has_feature_importance and feature_importances is not None:
        sorted_idx = np.argsort(feature_importances)
        fig, ax = plt.subplots(figsize=(10, max(4, len(feature_names) * 0.5)), dpi=DPI)
        ax.barh(range(len(sorted_idx)), feature_importances[sorted_idx], color='#FF7043')
        ax.set_yticks(range(len(sorted_idx)))
        ax.set_yticklabels(np.array(feature_names)[sorted_idx], fontsize=11)
        ax.set_xlabel('Feature Importance', fontsize=12)
        ax.set_title(f'{model_name} — Feature Importance', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_feature_importance.png'))
        plt.close()

    print(f"  ✅ {model_name}: all diagnostic plots saved")


# ─── Helper: save metrics to disk ───────────────────────────────────────────
def save_metrics(metrics, model_name):
    """Save metrics as both .csv and .json."""
    prefix = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(os.path.join(METRICS_DIR, f'{prefix}_metrics.csv'), index=False)
    with open(os.path.join(METRICS_DIR, f'{prefix}_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 5. LEAKY BASELINE (intentionally circular — for paper comparison)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[4/10] Training LEAKY BASELINE (RF with GTI — intentionally circular)...")

X_train_leaky = train_df[LEAKY_FEATURES]
X_test_leaky = test_df[LEAKY_FEATURES]
y_train = train_df[TARGET]
y_test = test_df[TARGET]

rf_leaky = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf_leaky.fit(X_train_leaky, y_train)
y_pred_leaky = rf_leaky.predict(X_test_leaky)

# Save model
joblib.dump(rf_leaky, os.path.join(MODELS_DIR, 'rf_leaky_baseline.joblib'))

# Metrics
metrics_leaky = compute_metrics(y_test, y_pred_leaky, 'RF Leaky Baseline')
save_metrics(metrics_leaky, 'RF Leaky Baseline')
print(f"  R² = {metrics_leaky['R2']:.4f}  |  MAE = {metrics_leaky['MAE_kW']:.4f} kW  |  RMSE = {metrics_leaky['RMSE_kW']:.4f} kW")

# Plots
generate_model_plots(y_test, y_pred_leaky, test_df['time'], 'RF Leaky Baseline',
                     has_feature_importance=True,
                     feature_importances=rf_leaky.feature_importances_,
                     feature_names=LEAKY_FEATURES)

all_metrics = [metrics_leaky]

# ═══════════════════════════════════════════════════════════════════════════
# 6. CORRECTED MODELS (non-circular features only)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[5/10] Training CORRECTED MODELS (non-circular features)...")

X_train_corr = train_df[CORRECTED_FEATURES]
X_test_corr = test_df[CORRECTED_FEATURES]

# --- 6a. Random Forest ---
print("\n  --- Random Forest (Corrected) ---")
rf_corr = RandomForestRegressor(n_estimators=200, max_depth=15, min_samples_leaf=5,
                                random_state=42, n_jobs=-1)
rf_corr.fit(X_train_corr, y_train)
y_pred_rf = rf_corr.predict(X_test_corr)
joblib.dump(rf_corr, os.path.join(MODELS_DIR, 'rf_corrected.joblib'))
m = compute_metrics(y_test, y_pred_rf, 'Random Forest')
save_metrics(m, 'Random Forest')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_rf, test_df['time'], 'Random Forest',
                     has_feature_importance=True,
                     feature_importances=rf_corr.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 6b. XGBoost ---
print("\n  --- XGBoost (Corrected) ---")
xgb_model = xgb.XGBRegressor(n_estimators=200, max_depth=8, learning_rate=0.1,
                              subsample=0.8, colsample_bytree=0.8,
                              random_state=42, n_jobs=-1, verbosity=0)
xgb_model.fit(X_train_corr, y_train)
y_pred_xgb = xgb_model.predict(X_test_corr)
joblib.dump(xgb_model, os.path.join(MODELS_DIR, 'xgboost_corrected.joblib'))
m = compute_metrics(y_test, y_pred_xgb, 'XGBoost')
save_metrics(m, 'XGBoost')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_xgb, test_df['time'], 'XGBoost',
                     has_feature_importance=True,
                     feature_importances=xgb_model.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 6c. SVR (with StandardScaler) ---
print("\n  --- SVR (Corrected) ---")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_corr)
X_test_scaled = scaler.transform(X_test_corr)
# SVR can be slow on large data — use a subsample for training if needed
n_svr_train = min(len(X_train_scaled), 20000)  # Cap at 20k for reasonable runtime
if len(X_train_scaled) > n_svr_train:
    print(f"  (SVR: subsampling to {n_svr_train} rows for tractable runtime)")
    rng = np.random.RandomState(42)
    svr_idx = rng.choice(len(X_train_scaled), n_svr_train, replace=False)
    svr_idx.sort()  # maintain chronological ordering within the subsample
    X_train_svr = X_train_scaled[svr_idx]
    y_train_svr = y_train.iloc[svr_idx]
else:
    X_train_svr = X_train_scaled
    y_train_svr = y_train
svr_model = SVR(kernel='rbf', C=10.0, epsilon=0.01)
svr_model.fit(X_train_svr, y_train_svr)
y_pred_svr = svr_model.predict(X_test_scaled)
# Save SVR + scaler together
joblib.dump({'model': svr_model, 'scaler': scaler}, os.path.join(MODELS_DIR, 'svr_corrected.joblib'))
m = compute_metrics(y_test, y_pred_svr, 'SVR')
save_metrics(m, 'SVR')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_svr, test_df['time'], 'SVR')
all_metrics.append(m)

# --- 6d. Decision Tree ---
print("\n  --- Decision Tree (Corrected) ---")
dt_model = DecisionTreeRegressor(max_depth=12, min_samples_leaf=10, random_state=42)
dt_model.fit(X_train_corr, y_train)
y_pred_dt = dt_model.predict(X_test_corr)
joblib.dump(dt_model, os.path.join(MODELS_DIR, 'dt_corrected.joblib'))
m = compute_metrics(y_test, y_pred_dt, 'Decision Tree')
save_metrics(m, 'Decision Tree')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_dt, test_df['time'], 'Decision Tree',
                     has_feature_importance=True,
                     feature_importances=dt_model.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 6e. Linear Regression (naive baseline) ---
print("\n  --- Linear Regression (Corrected) ---")
lr_model = LinearRegression()
lr_model.fit(X_train_corr, y_train)
y_pred_lr = lr_model.predict(X_test_corr)
joblib.dump(lr_model, os.path.join(MODELS_DIR, 'linear_regression_corrected.joblib'))
m = compute_metrics(y_test, y_pred_lr, 'Linear Regression')
save_metrics(m, 'Linear Regression')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_lr, test_df['time'], 'Linear Regression')
all_metrics.append(m)

# ═══════════════════════════════════════════════════════════════════════════
# 7. PHYSICAL FORMULA (no ML — just GTI × panel constants)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[6/10] Computing PHYSICAL FORMULA baseline (no ML)...")

# The target IS the physical formula applied to actual GTI, so "predicting" via the formula
# on the same actual GTI gives perfect reconstruction. The meaningful comparison is:
# what if we used forecast GTI? Since we're using reanalysis data, the physical formula
# here represents the "best-case" ceiling — it tells us how close ML can get to the
# deterministic formula when using indirect features instead of GTI directly.
y_pred_formula = (
    test_df['gti'] * PANEL_AREA * PANEL_EFFICIENCY * SYSTEM_PERFORMANCE * NUMBER_OF_PANELS / 1000
)
m = compute_metrics(y_test, y_pred_formula.values, 'Physical Formula')
save_metrics(m, 'Physical Formula')
print(f"  R² = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW")
print("  (Note: R²≈1.0 expected — target IS this formula applied to the same GTI values)")
print("  This row exists to show the ceiling / to compare against ML on indirect features")
generate_model_plots(y_test, y_pred_formula.values, test_df['time'], 'Physical Formula')
all_metrics.append(m)

# ═══════════════════════════════════════════════════════════════════════════
# 8. COMPARISON TABLE
# ═══════════════════════════════════════════════════════════════════════════
print("\n[7/10] Building comparison table...")

comparison_df = pd.DataFrame(all_metrics)
comparison_df = comparison_df.set_index('model')
comparison_path = os.path.join(RESULTS_DIR, 'comparison_table.csv')
comparison_df.to_csv(comparison_path)
print(f"  Saved → {comparison_path}")
print("\n" + comparison_df.to_string())

# Also save as JSON
with open(os.path.join(RESULTS_DIR, 'comparison_table.json'), 'w') as f:
    json.dump(all_metrics, f, indent=2)

# ═══════════════════════════════════════════════════════════════════════════
# 9. MODEL COMPARISON BAR CHART
# ═══════════════════════════════════════════════════════════════════════════
print("\n[8/10] Generating model comparison bar chart...")

# Exclude Physical Formula from the visual comparison (it's a trivial identity)
plot_df = comparison_df.drop('Physical Formula', errors='ignore')
metrics_to_plot = ['MAE_kW', 'RMSE_kW', 'R2']

fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=DPI)
colors = ['#1565C0', '#E65100', '#2E7D32', '#7B1FA2', '#C62828', '#00838F']

for i, metric in enumerate(metrics_to_plot):
    ax = axes[i]
    values = plot_df[metric].values
    model_names = plot_df.index.tolist()
    bars = ax.bar(range(len(model_names)), values, color=colors[:len(model_names)],
                  edgecolor='white', linewidth=0.8)
    ax.set_xticks(range(len(model_names)))
    ax.set_xticklabels(model_names, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel(metric, fontsize=12)
    ax.set_title(metric, fontsize=13, fontweight='bold')
    # Annotate values on bars
    for bar, val in zip(bars, values):
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f'{val:.4f}', ha='center', va='bottom', fontsize=8)

fig.suptitle('Solar Model Comparison (All Models)', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'model_comparison_bar.png'), bbox_inches='tight')
plt.close()
print("  ✅ model_comparison_bar.png")

# ═══════════════════════════════════════════════════════════════════════════
# 10. SAVE TEST-SET PREDICTIONS (for Phase 4 risk module)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[9/10] Saving test-set predictions for downstream phases...")

predictions_df = test_df[['time', TARGET]].copy()
predictions_df['pred_rf_leaky'] = y_pred_leaky
predictions_df['pred_rf'] = y_pred_rf
predictions_df['pred_xgb'] = y_pred_xgb
predictions_df['pred_svr'] = y_pred_svr
predictions_df['pred_dt'] = y_pred_dt
predictions_df['pred_lr'] = y_pred_lr
predictions_df['pred_formula'] = y_pred_formula.values
predictions_path = os.path.join(DATA_DIR, 'solar_test_predictions.csv')
predictions_df.to_csv(predictions_path, index=False)
print(f"  Saved → {predictions_path}")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 1 TRAINING COMPLETE")
print("=" * 70)
print(f"\nModels trained: {len(all_metrics)}")
print(f"  - 1 leaky baseline (RF with GTI)")
print(f"  - 5 corrected models (RF, XGBoost, SVR, DT, Linear)")
print(f"  - 1 physical formula (no ML)")
print(f"\nAll artifacts saved to:")
print(f"  Models:  {MODELS_DIR}")
print(f"  Metrics: {METRICS_DIR}")
print(f"  Plots:   {PLOTS_DIR}")
print(f"  Table:   {comparison_path}")
print(f"\n⚠️  OPEN-METEO DATA SOURCE: Confirmed as historical/reanalysis (not forecast).")
print(f"    σ_solar from this backtest is a LOWER BOUND on real deployment uncertainty.")
print(f"\n⚠️  PANEL COUNT: Fixed to 5 (was incorrectly 10 in original notebook).")
print(f"\n[10/10] Run Phase 1 Verification Gate checks next.")
