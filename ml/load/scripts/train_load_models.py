"""
Phase 2 -- Load Model Training Pipeline
========================================
Trains household load forecasting models on UCI data (main_data.csv).

Gap-aware approach:
  - Reindexes to complete hourly grid (no interpolation)
  - Computes lag/rolling features on the complete grid
  - NaN propagates naturally at gap boundaries
  - Drops all NaN rows, then splits chronologically

Produces:
  - EDA plots (6 figures)
  - Leaky baseline (Voltage+Intensity as features, random split)
  - 5 corrected models (RF, XGB, SVR, DT, Linear) on lag/calendar/rolling features
  - Per-model diagnostic plots
  - Comparison table + grouped bar chart

Reference: BUILD_PLAN.md Phase 2, PROJECT_MASTER_CONTEXT.md section 4.2
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

warnings.filterwarnings('ignore')

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DATA_RAW = os.path.join(PROJECT_ROOT, 'Dataset', 'main_data.csv')
DATA_DIR = os.path.join(PROJECT_ROOT, 'ml', 'load', 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'load', 'models')
METRICS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'load', 'results', 'metrics')
PLOTS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'load', 'results', 'plots')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'load', 'results')

# --- Plot settings ---
plt.style.use('seaborn-v0_8-whitegrid')
FIGSIZE = (12, 6)
DPI = 150

# ===================================================================
# 1. LOAD & PREPARE DATA
# ===================================================================
print("=" * 70)
print("PHASE 2 -- LOAD MODEL TRAINING")
print("=" * 70)

print("\n[1/11] Loading raw data...")
df = pd.read_csv(DATA_RAW, encoding='utf-8-sig')
print(f"  Raw shape: {df.shape}")

df['DateTime'] = pd.to_datetime(df['DateTime'], format='mixed', dayfirst=False)
df = df.sort_values('DateTime').reset_index(drop=True)
print(f"  Date range: {df['DateTime'].min()} -> {df['DateTime'].max()}")

TARGET = 'Global_active_power'

# ===================================================================
# 2. GAP-AWARE REINDEX (no interpolation)
# ===================================================================
print("\n[2/11] Gap-aware reindex to complete hourly grid...")

full_range = pd.date_range(
    start=df['DateTime'].min(), end=df['DateTime'].max(), freq='h'
)
print(f"  Complete grid: {len(full_range)} timestamps")
print(f"  Gap hours to fill with NaN: {len(full_range) - len(df)}")

df_full = df.set_index('DateTime').reindex(full_range)
df_full.index.name = 'DateTime'

# ===================================================================
# 3. FEATURE ENGINEERING
# ===================================================================
print("\n[3/11] Engineering features on complete grid...")

# Calendar features (derived from index, always available)
df_full['hour'] = df_full.index.hour
df_full['day_of_week'] = df_full.index.dayofweek
df_full['month'] = df_full.index.month
df_full['is_weekend'] = (df_full.index.dayofweek >= 5).astype(int)

# Temperature (T2M) -- from NASA POWER, keep as-is
# For gap rows, T2M is NaN; we won't use it to define the cleaning mask
# since it's an exogenous feature. We'll forward-fill T2M only (weather
# doesn't jump discontinuously, so ffill is physically defensible for
# a few missing hours of temperature -- unlike load power).
df_full['T2M'] = df_full['T2M'].ffill().bfill()

# Lag features (these will naturally NaN at gaps and at series start)
# Iteration 2: added lag_12 (half-day, corr=0.24) and lag_168 (weekly, corr=0.45)
# to capture weekly periodicity not covered by the original lag set.
lag_steps = [1, 2, 3, 12, 24, 48, 168]
lag_cols = []
for lag in lag_steps:
    col = f'power_lag_{lag}'
    df_full[col] = df_full[TARGET].shift(lag)
    lag_cols.append(col)

# Rolling features -- CRITICAL: compute on .shift(1) so the window only covers
# strictly PAST values (t-1, t-2, ...), never the current target value at time t.
# Without shift(1), rolling_mean_3h = mean(power(t), power(t-1), power(t-2)),
# which leaks the target and allows perfect reconstruction:
#   power(t) = 3 * rolling_mean_3h - lag1 - lag2  (R^2 = 1.0 for Linear Regression)
# With shift(1), rolling_mean_3h = mean(power(t-1), power(t-2), power(t-3)) -- safe.
shifted_target = df_full[TARGET].shift(1)
df_full['rolling_mean_3h'] = shifted_target.rolling(3, min_periods=3).mean()
df_full['rolling_mean_24h'] = shifted_target.rolling(24, min_periods=24).mean()
df_full['rolling_std_24h'] = shifted_target.rolling(24, min_periods=24).std()
# Iteration 2: add weekly rolling mean to capture weekly consumption patterns
df_full['rolling_mean_168h'] = shifted_target.rolling(168, min_periods=168).mean()
rolling_cols = ['rolling_mean_3h', 'rolling_mean_24h', 'rolling_std_24h', 'rolling_mean_168h']

# ===================================================================
# 4. CLEAN: DROP ALL NaN ROWS (gaps + initial boundary + contamination)
# ===================================================================
print("\n[4/11] Dropping NaN rows (gaps + initial boundary + contamination windows)...")

# Columns that must ALL be non-NaN for a row to be usable
integrity_cols = [TARGET] + lag_cols + rolling_cols
any_nan = df_full[integrity_cols].isna().any(axis=1)

# Accounting
total_grid = len(df_full)
initial_boundary = df_full.iloc[:48][integrity_cols].isna().any(axis=1).sum()
gap_rows_count = df_full[TARGET].isna().sum()
total_dropped = any_nan.sum()
contamination = total_dropped - initial_boundary - gap_rows_count

print(f"  Total grid rows:               {total_grid}")
print(f"  Initial boundary (first ~48):  {initial_boundary} dropped")
print(f"  Gap rows (missing data):       {gap_rows_count} dropped")
print(f"  Contamination window rows:     {contamination} dropped")
print(f"  Total dropped:                 {total_dropped}")

df_clean = df_full[~any_nan].copy()
print(f"  >>> FINAL CLEAN ROWS: {len(df_clean)} ({len(df_clean)/total_grid*100:.1f}% of grid)")
print(f"  Date range: {df_clean.index.min()} -> {df_clean.index.max()}")

# Save processed clean data
df_clean.to_csv(os.path.join(DATA_DIR, 'load_processed_clean.csv'))
print(f"  Saved -> {os.path.join(DATA_DIR, 'load_processed_clean.csv')}")

# ===================================================================
# 5. SPOT-CHECK LAG CORRECTNESS
# ===================================================================
print("\n[5/11] Spot-checking lag feature correctness...")

# Pick 5 random clean rows and verify lag values against the grid
rng = np.random.RandomState(42)
check_indices = rng.choice(len(df_clean), 5, replace=False)
all_correct = True
for idx in sorted(check_indices):
    row = df_clean.iloc[idx]
    ts = df_clean.index[idx]
    # Verify power_lag_1: should equal the target value at ts - 1h
    ts_minus_1 = ts - pd.Timedelta(hours=1)
    if ts_minus_1 in df_full.index:
        expected_lag1 = df_full.loc[ts_minus_1, TARGET]
        actual_lag1 = row['power_lag_1']
        match = abs(expected_lag1 - actual_lag1) < 1e-10
        if not match:
            all_correct = False
        print(f"  {ts}: lag1={actual_lag1:.4f}, grid[t-1]={expected_lag1:.4f} {'OK' if match else 'MISMATCH!'}")

    # Verify power_lag_24
    ts_minus_24 = ts - pd.Timedelta(hours=24)
    if ts_minus_24 in df_full.index:
        expected_lag24 = df_full.loc[ts_minus_24, TARGET]
        actual_lag24 = row['power_lag_24']
        match = abs(expected_lag24 - actual_lag24) < 1e-10
        if not match:
            all_correct = False
        print(f"  {ts}: lag24={actual_lag24:.4f}, grid[t-24]={expected_lag24:.4f} {'OK' if match else 'MISMATCH!'}")

print(f"  All spot-checks passed: {all_correct}")

# ===================================================================
# 6. EDA PLOTS
# ===================================================================
print("\n[6/11] Generating EDA plots...")

# 6a. Target distribution
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
ax.hist(df_clean[TARGET], bins=80, color='#1565C0', edgecolor='white', alpha=0.85)
ax.set_xlabel('Global Active Power (kW)', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title('Distribution of Household Power Consumption', fontsize=14)
ax.axvline(df_clean[TARGET].mean(), color='red', linestyle='--',
           label=f"Mean: {df_clean[TARGET].mean():.2f} kW")
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_target_distribution.png'))
plt.close()
print("  > eda_target_distribution.png")

# 6b. Full time-series
fig, ax = plt.subplots(figsize=(14, 5), dpi=DPI)
weekly = df_clean[TARGET].resample('W').agg(['mean', 'max'])
ax.fill_between(weekly.index, 0, weekly['max'], alpha=0.3, color='#FF9800', label='Weekly Max')
ax.plot(weekly.index, weekly['mean'], color='#E65100', linewidth=1.2, label='Weekly Mean')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Power (kW)', fontsize=12)
ax.set_title('Household Power Consumption Over Full Period (2006-2010)', fontsize=14)
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_timeseries_full.png'))
plt.close()
print("  > eda_timeseries_full.png")

# 6c. Hourly boxplot
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
hour_data = [df_clean.loc[df_clean['hour'] == h, TARGET].values for h in range(24)]
bp = ax.boxplot(hour_data, positions=range(24), patch_artist=True,
                boxprops=dict(facecolor='#E3F2FD', color='#1565C0'),
                medianprops=dict(color='#0D47A1', linewidth=2),
                whiskerprops=dict(color='#1565C0'),
                capprops=dict(color='#1565C0'),
                flierprops=dict(marker='.', markersize=2, alpha=0.3),
                widths=0.7)
ax.set_xlabel('Hour of Day', fontsize=12)
ax.set_ylabel('Power (kW)', fontsize=12)
ax.set_title('Power Consumption by Hour of Day', fontsize=14)
ax.set_xticks(range(24))
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_hourly_boxplot.png'))
plt.close()
print("  > eda_hourly_boxplot.png")

# 6d. Day-of-week boxplot
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
dow_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
dow_data = [df_clean.loc[df_clean['day_of_week'] == d, TARGET].values for d in range(7)]
bp = ax.boxplot(dow_data, positions=range(7), patch_artist=True,
                boxprops=dict(facecolor='#FFF3E0', color='#E65100'),
                medianprops=dict(color='#BF360C', linewidth=2),
                whiskerprops=dict(color='#E65100'),
                capprops=dict(color='#E65100'),
                flierprops=dict(marker='.', markersize=2, alpha=0.3),
                widths=0.6)
ax.set_xlabel('Day of Week', fontsize=12)
ax.set_ylabel('Power (kW)', fontsize=12)
ax.set_title('Power Consumption by Day of Week', fontsize=14)
ax.set_xticks(range(7))
ax.set_xticklabels(dow_labels)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_dayofweek_boxplot.png'))
plt.close()
print("  > eda_dayofweek_boxplot.png")

# 6e. Monthly boxplot
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
month_data = [df_clean.loc[df_clean['month'] == m, TARGET].values for m in range(1, 13)]
bp = ax.boxplot(month_data, positions=range(1, 13), patch_artist=True,
                boxprops=dict(facecolor='#E8F5E9', color='#2E7D32'),
                medianprops=dict(color='#1B5E20', linewidth=2),
                whiskerprops=dict(color='#2E7D32'),
                capprops=dict(color='#2E7D32'),
                flierprops=dict(marker='.', markersize=2, alpha=0.3),
                widths=0.7)
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Power (kW)', fontsize=12)
ax.set_title('Power Consumption by Month (Seasonal Pattern)', fontsize=14)
ax.set_xticks(range(1, 13))
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_monthly_boxplot.png'))
plt.close()
print("  > eda_monthly_boxplot.png")

# 6f. Correlation heatmap of corrected features
corr_features = [TARGET] + lag_cols + rolling_cols + ['hour', 'day_of_week', 'month', 'is_weekend', 'T2M']
corr = df_clean[corr_features].corr()
fig, ax = plt.subplots(figsize=(12, 10), dpi=DPI)
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdYlBu_r',
            center=0, square=True, linewidths=0.5, ax=ax,
            cbar_kws={'shrink': 0.8}, annot_kws={'size': 8})
ax.set_title('Feature Correlation Heatmap (Corrected Features + Target)', fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'eda_correlation_heatmap.png'))
plt.close()
print("  > eda_correlation_heatmap.png")

# ===================================================================
# 7. TRAIN/TEST SPLIT (chronological, AFTER cleaning)
# ===================================================================
print("\n[7/11] Chronological train/test split (on clean data)...")

split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx].copy()
test_df = df_clean.iloc[split_idx:].copy()
print(f"  Train: {len(train_df)} rows ({train_df.index.min()} -> {train_df.index.max()})")
print(f"  Test:  {len(test_df)} rows ({test_df.index.min()} -> {test_df.index.max()})")

# ===================================================================
# FEATURE DEFINITIONS
# ===================================================================

# Leaky features (intentionally circular -- Voltage + Intensity)
LEAKY_FEATURES = ['Voltage', 'Global_intensity', 'T2M']

# Corrected features (only future-available information)
CORRECTED_FEATURES = lag_cols + rolling_cols + ['hour', 'day_of_week', 'month', 'is_weekend', 'T2M']

y_train = train_df[TARGET]
y_test = test_df[TARGET]

# ===================================================================
# HELPERS (same pattern as Phase 1)
# ===================================================================
def compute_metrics(y_true, y_pred, model_name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    nonzero_mask = y_true > 0.01
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100
    else:
        mape = np.nan
    return {
        'model': model_name,
        'MAE_kW': round(mae, 6),
        'RMSE_kW': round(rmse, 6),
        'R2': round(r2, 6),
        'MAPE_%': round(mape, 4) if not np.isnan(mape) else None
    }

def save_metrics(metrics, model_name):
    prefix = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
    pd.DataFrame([metrics]).to_csv(os.path.join(METRICS_DIR, f'{prefix}_metrics.csv'), index=False)
    with open(os.path.join(METRICS_DIR, f'{prefix}_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)

def generate_model_plots(y_true, y_pred, time_index, model_name,
                         has_feature_importance=False,
                         feature_importances=None, feature_names=None):
    prefix = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')

    # (a) Time-series overlay
    fig, ax = plt.subplots(figsize=(14, 5), dpi=DPI)
    n = len(y_true)
    step = max(1, n // 2000) if n > 2000 else 1
    idx = slice(None, None, step)
    ax.plot(time_index[idx], y_true.values[idx], label='Actual', color='#1565C0', linewidth=0.8, alpha=0.8)
    ax.plot(time_index[idx], y_pred[idx], label='Predicted', color='#E65100', linewidth=0.8, alpha=0.8)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Power (kW)', fontsize=12)
    ax.set_title(f'{model_name} -- Actual vs Predicted (Test Set)', fontsize=14)
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_timeseries.png'))
    plt.close()

    # (b) Scatter with y=x and R^2
    fig, ax = plt.subplots(figsize=(8, 8), dpi=DPI)
    ax.scatter(y_true, y_pred, alpha=0.15, s=8, color='#1565C0', edgecolors='none')
    lims = [0, max(y_true.max(), max(y_pred)) * 1.05]
    ax.plot(lims, lims, 'r--', linewidth=1.5, label='y = x (perfect)')
    r2 = r2_score(y_true, y_pred)
    ax.text(0.05, 0.92, f'R$^2$ = {r2:.4f}', transform=ax.transAxes,
            fontsize=14, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax.set_xlabel('Actual Power (kW)', fontsize=12)
    ax.set_ylabel('Predicted Power (kW)', fontsize=12)
    ax.set_title(f'{model_name} -- Actual vs Predicted Scatter', fontsize=14)
    ax.set_xlim(lims); ax.set_ylim(lims); ax.set_aspect('equal')
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_scatter.png'))
    plt.close()

    # (c) Residual vs predicted
    residuals = y_true.values - y_pred
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    ax.scatter(y_pred, residuals, alpha=0.12, s=6, color='#4CAF50', edgecolors='none')
    ax.axhline(0, color='red', linestyle='--', linewidth=1.2)
    ax.set_xlabel('Predicted Power (kW)', fontsize=12)
    ax.set_ylabel('Residual (Actual - Predicted) (kW)', fontsize=12)
    ax.set_title(f'{model_name} -- Residuals vs Predicted', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_residuals.png'))
    plt.close()

    # (d) Residual histogram
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    ax.hist(residuals, bins=80, color='#9C27B0', edgecolor='white', alpha=0.8)
    ax.axvline(0, color='red', linestyle='--', linewidth=1.2)
    ax.axvline(np.mean(residuals), color='orange', linestyle='--', linewidth=1.2,
               label=f'Mean: {np.mean(residuals):.4f} kW')
    ax.set_xlabel('Residual (kW)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'{model_name} -- Residual Distribution', fontsize=14)
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_residual_hist.png'))
    plt.close()

    # (e) Feature importance
    if has_feature_importance and feature_importances is not None:
        sorted_idx = np.argsort(feature_importances)
        fig, ax = plt.subplots(figsize=(10, max(4, len(feature_names) * 0.45)), dpi=DPI)
        ax.barh(range(len(sorted_idx)), feature_importances[sorted_idx], color='#FF7043')
        ax.set_yticks(range(len(sorted_idx)))
        ax.set_yticklabels(np.array(feature_names)[sorted_idx], fontsize=10)
        ax.set_xlabel('Feature Importance', fontsize=12)
        ax.set_title(f'{model_name} -- Feature Importance', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, f'{prefix}_feature_importance.png'))
        plt.close()

    print(f"  > {model_name}: all diagnostic plots saved")


all_metrics = []

# ===================================================================
# 8. LEAKY BASELINE (intentionally circular -- random split)
# ===================================================================
print("\n[8/11] Training LEAKY BASELINE (Voltage + Intensity, random split)...")

# Per BUILD_PLAN: reproduce original circular baseline with random split
from sklearn.model_selection import train_test_split

X_leaky = df_clean[LEAKY_FEATURES]
y_leaky = df_clean[TARGET]
X_tr_leak, X_te_leak, y_tr_leak, y_te_leak = train_test_split(
    X_leaky, y_leaky, test_size=0.2, random_state=42  # shuffle=True (default) -- intentionally wrong
)

rf_leaky = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf_leaky.fit(X_tr_leak, y_tr_leak)
y_pred_leaky = rf_leaky.predict(X_te_leak)
joblib.dump(rf_leaky, os.path.join(MODELS_DIR, 'rf_leaky_baseline.joblib'))
m = compute_metrics(y_te_leak, y_pred_leaky, 'RF Leaky Baseline')
save_metrics(m, 'RF Leaky Baseline')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")

# For leaky baseline, use leaky test set for plots
generate_model_plots(y_te_leak, y_pred_leaky, X_te_leak.index, 'RF Leaky Baseline',
                     has_feature_importance=True,
                     feature_importances=rf_leaky.feature_importances_,
                     feature_names=LEAKY_FEATURES)
all_metrics.append(m)

# ===================================================================
# 9. CORRECTED MODELS (chronological split, non-circular features)
# ===================================================================
print("\n[9/11] Training CORRECTED MODELS (lag/calendar/rolling features, chronological split)...")

X_train_corr = train_df[CORRECTED_FEATURES]
X_test_corr = test_df[CORRECTED_FEATURES]

# --- 9a. Random Forest ---
print("\n  --- Random Forest (Corrected) ---")
# Iteration 2: increased depth and trees for better capacity
rf_corr = RandomForestRegressor(n_estimators=300, max_depth=20, min_samples_leaf=3,
                                random_state=42, n_jobs=-1)
rf_corr.fit(X_train_corr, y_train)
y_pred_rf = rf_corr.predict(X_test_corr)
joblib.dump(rf_corr, os.path.join(MODELS_DIR, 'rf_corrected.joblib'))
m = compute_metrics(y_test, y_pred_rf, 'Random Forest')
save_metrics(m, 'Random Forest')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_rf, test_df.index, 'Random Forest',
                     has_feature_importance=True,
                     feature_importances=rf_corr.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 9b. XGBoost ---
print("\n  --- XGBoost (Corrected) ---")
# Iteration 2: increased estimators and depth
xgb_model = xgb.XGBRegressor(n_estimators=300, max_depth=10, learning_rate=0.08,
                              subsample=0.8, colsample_bytree=0.8,
                              random_state=42, n_jobs=-1, verbosity=0)
xgb_model.fit(X_train_corr, y_train)
y_pred_xgb = xgb_model.predict(X_test_corr)
joblib.dump(xgb_model, os.path.join(MODELS_DIR, 'xgboost_corrected.joblib'))
m = compute_metrics(y_test, y_pred_xgb, 'XGBoost')
save_metrics(m, 'XGBoost')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_xgb, test_df.index, 'XGBoost',
                     has_feature_importance=True,
                     feature_importances=xgb_model.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 9c. SVR ---
print("\n  --- SVR (Corrected) ---")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_corr)
X_test_scaled = scaler.transform(X_test_corr)
n_svr_train = min(len(X_train_scaled), 20000)
if len(X_train_scaled) > n_svr_train:
    print(f"  (SVR: subsampling to {n_svr_train} rows for tractable runtime)")
    rng_svr = np.random.RandomState(42)
    svr_idx = rng_svr.choice(len(X_train_scaled), n_svr_train, replace=False)
    svr_idx.sort()
    X_train_svr = X_train_scaled[svr_idx]
    y_train_svr = y_train.iloc[svr_idx]
else:
    X_train_svr = X_train_scaled
    y_train_svr = y_train
svr_model = SVR(kernel='rbf', C=10.0, epsilon=0.01)
svr_model.fit(X_train_svr, y_train_svr)
y_pred_svr = svr_model.predict(X_test_scaled)
joblib.dump({'model': svr_model, 'scaler': scaler}, os.path.join(MODELS_DIR, 'svr_corrected.joblib'))
m = compute_metrics(y_test, y_pred_svr, 'SVR')
save_metrics(m, 'SVR')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_svr, test_df.index, 'SVR')
all_metrics.append(m)

# --- 9d. Decision Tree ---
print("\n  --- Decision Tree (Corrected) ---")
dt_model = DecisionTreeRegressor(max_depth=12, min_samples_leaf=10, random_state=42)
dt_model.fit(X_train_corr, y_train)
y_pred_dt = dt_model.predict(X_test_corr)
joblib.dump(dt_model, os.path.join(MODELS_DIR, 'dt_corrected.joblib'))
m = compute_metrics(y_test, y_pred_dt, 'Decision Tree')
save_metrics(m, 'Decision Tree')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_dt, test_df.index, 'Decision Tree',
                     has_feature_importance=True,
                     feature_importances=dt_model.feature_importances_,
                     feature_names=CORRECTED_FEATURES)
all_metrics.append(m)

# --- 9e. Linear Regression ---
print("\n  --- Linear Regression (Corrected) ---")
lr_model = LinearRegression()
lr_model.fit(X_train_corr, y_train)
y_pred_lr = lr_model.predict(X_test_corr)
joblib.dump(lr_model, os.path.join(MODELS_DIR, 'linear_regression_corrected.joblib'))
m = compute_metrics(y_test, y_pred_lr, 'Linear Regression')
save_metrics(m, 'Linear Regression')
print(f"  R2 = {m['R2']:.4f}  |  MAE = {m['MAE_kW']:.4f} kW  |  RMSE = {m['RMSE_kW']:.4f} kW")
generate_model_plots(y_test, y_pred_lr, test_df.index, 'Linear Regression')
all_metrics.append(m)

# ===================================================================
# 10. COMPARISON TABLE + BAR CHART
# ===================================================================
print("\n[10/11] Building comparison table...")

comparison_df = pd.DataFrame(all_metrics).set_index('model')
comparison_path = os.path.join(RESULTS_DIR, 'comparison_table.csv')
comparison_df.to_csv(comparison_path)
with open(os.path.join(RESULTS_DIR, 'comparison_table.json'), 'w') as f:
    json.dump(all_metrics, f, indent=2)
print(f"  Saved -> {comparison_path}")
print("\n" + comparison_df.to_string())

# Bar chart
plot_df = comparison_df
metrics_to_plot = ['MAE_kW', 'RMSE_kW', 'R2']
colors = ['#1565C0', '#E65100', '#2E7D32', '#7B1FA2', '#C62828', '#00838F']
fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=DPI)
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
    for bar, val in zip(bars, values):
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f'{val:.4f}', ha='center', va='bottom', fontsize=8)
fig.suptitle('Load Model Comparison (All Models)', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'model_comparison_bar.png'), bbox_inches='tight')
plt.close()
print("  > model_comparison_bar.png")

# ===================================================================
# 11. SAVE TEST PREDICTIONS (for Phase 4 risk module)
# ===================================================================
print("\n[11/11] Saving test-set predictions...")

predictions_df = test_df[[TARGET]].copy()
predictions_df['pred_rf_leaky'] = np.nan  # leaky used different split, not comparable
predictions_df['pred_rf'] = y_pred_rf
predictions_df['pred_xgb'] = y_pred_xgb
predictions_df['pred_svr'] = y_pred_svr
predictions_df['pred_dt'] = y_pred_dt
predictions_df['pred_lr'] = y_pred_lr
predictions_path = os.path.join(DATA_DIR, 'load_test_predictions.csv')
predictions_df.to_csv(predictions_path)
print(f"  Saved -> {predictions_path}")

# ===================================================================
# SUMMARY
# ===================================================================
print("\n" + "=" * 70)
print("PHASE 2 TRAINING COMPLETE")
print("=" * 70)
print(f"\nData integrity:")
print(f"  Raw rows:   34,168")
print(f"  Grid rows:  34,589  (421 gap-hours added as NaN)")
print(f"  Dropped:    {total_dropped} (initial boundary: {initial_boundary}, gaps: {gap_rows_count}, contamination: {contamination})")
print(f"  Clean rows: {len(df_clean)} ({len(df_clean)/total_grid*100:.1f}%)")
print(f"  Split: train {len(train_df)} / test {len(test_df)} (chronological, AFTER cleaning)")
print(f"\nModels trained: {len(all_metrics)}")
print(f"  - 1 leaky baseline (Voltage+Intensity, random split)")
print(f"  - 5 corrected models (RF, XGBoost, SVR, DT, Linear)")
print(f"\nAll artifacts saved to:")
print(f"  Models:  {MODELS_DIR}")
print(f"  Metrics: {METRICS_DIR}")
print(f"  Plots:   {PLOTS_DIR}")
print(f"  Table:   {comparison_path}")
print(f"\nBug fix applied: test_rmse (not train_rmse) is computed and reported.")
print(f"\n>>> Run Phase 2 Verification Gate checks next.")
