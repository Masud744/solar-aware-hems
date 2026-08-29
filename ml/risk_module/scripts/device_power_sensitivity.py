#!/usr/bin/env python3
"""
Device-Power Sensitivity Check for Phase 4 Verification Gate.

Re-runs the synthetic decision matrix using BOTH 0.5 kW and 1.2 kW device
powers on the same 176 synthetically aligned pairs. No changes to alignment,
sigma values, or uncertainty formulas.
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COV_DIR = PROJECT_ROOT / 'ml' / 'risk_module' / 'coverage_experiments'

plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
})

K_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5]
DEVICE_POWERS = [0.5, 1.2]

# ─────────────────────────────────────────────────────────────────────
# Load existing data
# ─────────────────────────────────────────────────────────────────────
print("=" * 80)
print("DEVICE-POWER SENSITIVITY CHECK")
print("=" * 80)

aligned_df = pd.read_csv(COV_DIR / 'synthetic_aligned_pairs.csv')
print(f"\nLoaded {len(aligned_df)} synthetically aligned pairs (unchanged)")

# Load sigma values
with open(COV_DIR / 'sigma_summary.json') as f:
    sigma_summary = json.load(f)
sigma_solar_global = sigma_summary['sigma_solar_global_kW']
sigma_load_global = sigma_summary['sigma_load_global_kW']

solar_bucket_sigma = pd.read_csv(COV_DIR / 'solar_bucketed_sigma.csv', index_col=0)
load_bucket_sigma = pd.read_csv(COV_DIR / 'load_bucketed_sigma.csv', index_col=0)

print(f"σ_solar (global) = {sigma_solar_global:.4f} kW")
print(f"σ_load  (global) = {sigma_load_global:.4f} kW")

# Re-derive bucketed sigma columns (same logic as main script)
def cloud_bucket(cc):
    if cc <= 20:
        return 'Clear (0-20%)'
    elif cc <= 60:
        return 'Partly Cloudy (21-60%)'
    else:
        return 'Overcast (61-100%)'

def hour_bucket(h):
    if 0 <= h < 6:
        return 'Night (0-5)'
    elif 6 <= h < 12:
        return 'Morning (6-11)'
    elif 12 <= h < 18:
        return 'Afternoon (12-17)'
    else:
        return 'Evening (18-23)'

aligned_df['cloud_bucket'] = aligned_df['solar_cloud_cover'].apply(cloud_bucket)
aligned_df['solar_sigma_bucketed'] = aligned_df['cloud_bucket'].map(solar_bucket_sigma['sigma'])
aligned_df['hour_bucket'] = aligned_df['hour'].apply(hour_bucket)
aligned_df['load_sigma_bucketed'] = aligned_df['hour_bucket'].map(load_bucket_sigma['sigma'])

# ─────────────────────────────────────────────────────────────────────
# Run decision matrix for both device powers × both sigma methods
# ─────────────────────────────────────────────────────────────────────

def run_decision_matrix(aligned, k_values, solar_sigma, load_sigma, device_power, sigma_label):
    """Run decision evaluation and return detailed metrics."""
    rows = []
    for k in k_values:
        safe_solar = np.maximum(0, aligned['solar_predicted'] - k * solar_sigma)
        conservative_load = aligned['load_predicted'] + k * load_sigma
        safe_surplus = safe_solar - conservative_load

        system_allows = safe_surplus >= device_power
        actual_surplus = aligned['solar_actual'] - aligned['load_actual']
        actual_allows = actual_surplus >= device_power

        ca = (system_allows & actual_allows).sum()
        ia = (system_allows & ~actual_allows).sum()
        cd = (~system_allows & ~actual_allows).sum()
        id_ = (~system_allows & actual_allows).sum()
        total = len(aligned)
        n_allow = system_allows.sum()

        rows.append({
            'k': k,
            'device_power_kW': device_power,
            'sigma_method': sigma_label,
            'Correct-ALLOW': int(ca),
            'Incorrect-ALLOW': int(ia),
            'Correct-DENY': int(cd),
            'Incorrect-DENY': int(id_),
            'Total': total,
            'ALLOW_count': int(n_allow),
            'ALLOW_rate_%': n_allow / total * 100,
            'Incorrect_ALLOW_rate_%': ia / total * 100,
            'Incorrect_DENY_rate_%': id_ / total * 100,
            'Precision_ALLOW_%': ca / (ca + ia) * 100 if (ca + ia) > 0 else float('nan'),
            'Recall_ALLOW_%': ca / (ca + id_) * 100 if (ca + id_) > 0 else float('nan'),
            'Safety_rate_%': (1 - ia / total) * 100,
        })
    return pd.DataFrame(rows)


all_results = []

for device_kw in DEVICE_POWERS:
    for sigma_label, solar_sigma, load_sigma in [
        ('Global σ', sigma_solar_global, sigma_load_global),
        ('Bucketed σ', aligned_df['solar_sigma_bucketed'], aligned_df['load_sigma_bucketed']),
    ]:
        result = run_decision_matrix(
            aligned_df, K_VALUES, solar_sigma, load_sigma, device_kw, sigma_label
        )
        all_results.append(result)

full_df = pd.concat(all_results, ignore_index=True)

# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("RESULTS: SYNTHETIC DECISION MATRIX — DEVICE-POWER SENSITIVITY")
print("─" * 80)

for device_kw in DEVICE_POWERS:
    for sigma_label in ['Bucketed σ', 'Global σ']:
        subset = full_df[(full_df['device_power_kW'] == device_kw) &
                         (full_df['sigma_method'] == sigma_label)]
        print(f"\n  === Device = {device_kw} kW | {sigma_label} ===")
        display_cols = ['k', 'Correct-ALLOW', 'Incorrect-ALLOW', 'Correct-DENY',
                        'Incorrect-DENY', 'ALLOW_count', 'ALLOW_rate_%',
                        'Incorrect_ALLOW_rate_%', 'Incorrect_DENY_rate_%']
        print(subset[display_cols].to_string(index=False, float_format='%.1f'))

# ─────────────────────────────────────────────────────────────────────
# Comparative summary
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("COMPARATIVE SUMMARY (Bucketed σ — Intended Deployed Method)")
print("─" * 80)

buck = full_df[full_df['sigma_method'] == 'Bucketed σ'].copy()

print(f"\n  {'k':>4} | {'─── Device = 0.5 kW ───':^36} | {'─── Device = 1.2 kW ───':^36}")
print(f"  {'':>4} | {'CA':>3} {'IA':>3} {'CD':>4} {'ID':>3} {'ALLOWs':>7} {'IA%':>6} | {'CA':>3} {'IA':>3} {'CD':>4} {'ID':>3} {'ALLOWs':>7} {'IA%':>6}")
print(f"  {'─'*4}-+-{'─'*36}-+-{'─'*36}")

for k in K_VALUES:
    r05 = buck[(buck['k'] == k) & (buck['device_power_kW'] == 0.5)].iloc[0]
    r12 = buck[(buck['k'] == k) & (buck['device_power_kW'] == 1.2)].iloc[0]
    print(f"  {k:4.1f} | {int(r05['Correct-ALLOW']):>3} {int(r05['Incorrect-ALLOW']):>3} "
          f"{int(r05['Correct-DENY']):>4} {int(r05['Incorrect-DENY']):>3} "
          f"{int(r05['ALLOW_count']):>7} {r05['Incorrect_ALLOW_rate_%']:>5.1f}% | "
          f"{int(r12['Correct-ALLOW']):>3} {int(r12['Incorrect-ALLOW']):>3} "
          f"{int(r12['Correct-DENY']):>4} {int(r12['Incorrect-DENY']):>3} "
          f"{int(r12['ALLOW_count']):>7} {r12['Incorrect_ALLOW_rate_%']:>5.1f}%")

# ─────────────────────────────────────────────────────────────────────
# Flag extreme conservatism
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("EXTREME-CONSERVATISM CHECK")
print("─" * 80)

for k in K_VALUES:
    buck_k = buck[buck['k'] == k]
    allows_05 = buck_k[buck_k['device_power_kW'] == 0.5].iloc[0]['ALLOW_count']
    allows_12 = buck_k[buck_k['device_power_kW'] == 1.2].iloc[0]['ALLOW_count']
    if allows_05 == 0 and allows_12 == 0:
        print(f"  k={k}: ⚠ ZERO ALLOWs for BOTH device powers — extreme conservatism")
    elif allows_05 == 0 or allows_12 == 0:
        zero_dev = '0.5 kW' if allows_05 == 0 else '1.2 kW'
        nonz_dev = '1.2 kW' if allows_05 == 0 else '0.5 kW'
        print(f"  k={k}: Zero ALLOWs for {zero_dev}, {int(max(allows_05, allows_12))} ALLOWs for {nonz_dev}")
    else:
        print(f"  k={k}: ALLOWs for 0.5 kW = {int(allows_05)}, for 1.2 kW = {int(allows_12)}")

# Determine which k values produce meaningful ALLOWs
print("\n  SUMMARY:")
any_allow_k = []
for k in K_VALUES:
    buck_k = buck[buck['k'] == k]
    for dp in DEVICE_POWERS:
        row = buck_k[buck_k['device_power_kW'] == dp].iloc[0]
        if row['ALLOW_count'] > 0:
            any_allow_k.append(k)
            break
if any_allow_k:
    print(f"  k values producing any ALLOWs: {sorted(set(any_allow_k))}")
else:
    print(f"  NO k value produces any ALLOWs for either device power — "
          f"all decisions are DENY across the board.")

# ─────────────────────────────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("SAVING ARTIFACTS")
print("─" * 80)

full_df.to_csv(COV_DIR / 'device_power_sensitivity.csv', index=False)
print("  ✓ device_power_sensitivity.csv")

# Update synthetic_decision_matrix files to include both device powers
for sigma_label, suffix in [('Bucketed σ', 'bucketed'), ('Global σ', 'global')]:
    subset = full_df[full_df['sigma_method'] == sigma_label]
    subset.to_csv(COV_DIR / f'synthetic_decision_matrix_{suffix}.csv', index=False)
    print(f"  ✓ synthetic_decision_matrix_{suffix}.csv (updated with both device powers)")

# ─────────────────────────────────────────────────────────────────────
# Generate comparison heatmap
# ─────────────────────────────────────────────────────────────────────
buck_data = full_df[full_df['sigma_method'] == 'Bucketed σ']

fig, axes = plt.subplots(2, len(K_VALUES), figsize=(4.2 * len(K_VALUES), 8))

for row_idx, device_kw in enumerate(DEVICE_POWERS):
    for col_idx, k in enumerate(K_VALUES):
        ax = axes[row_idx, col_idx]
        dm = buck_data[(buck_data['k'] == k) & (buck_data['device_power_kW'] == device_kw)].iloc[0]

        matrix = np.array([
            [dm['Correct-ALLOW'], dm['Incorrect-DENY']],
            [dm['Incorrect-ALLOW'], dm['Correct-DENY']],
        ])
        labels = np.array([
            [f"Correct\nALLOW\n{int(dm['Correct-ALLOW'])}", f"Incorrect\nDENY\n{int(dm['Incorrect-DENY'])}"],
            [f"Incorrect\nALLOW\n{int(dm['Incorrect-ALLOW'])}", f"Correct\nDENY\n{int(dm['Correct-DENY'])}"],
        ])

        sns.heatmap(matrix, annot=labels, fmt='', cmap='RdYlGn',
                    xticklabels=['Ref: ALLOW', 'Ref: DENY'],
                    yticklabels=['Sys: ALLOW', 'Sys: DENY'],
                    ax=ax, cbar=False, linewidths=1, linecolor='white',
                    annot_kws={'fontsize': 8})
        ax.set_title(f'k={k}', fontsize=11, fontweight='bold')

    # Row label
    axes[row_idx, 0].set_ylabel(f'Device = {device_kw} kW\n\nSys: ALLOW / DENY',
                                 fontsize=10, fontweight='bold')

plt.suptitle('Synthetic Decision Evaluation — Device-Power Sensitivity\n'
             'Bucketed σ | 176 synthetically aligned pairs | '
             'NOT real-world co-located measurements',
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(COV_DIR / 'decision_evaluation_device_sensitivity.png')
plt.close()
print("  ✓ decision_evaluation_device_sensitivity.png")

# ─────────────────────────────────────────────────────────────────────
# k-selection evidence summary
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 80)
print("K-SELECTION EVIDENCE (for user decision)")
print("─" * 80)

print("""
  The synthetic decision matrix was evaluated for BOTH device powers
  (0.5 kW and 1.2 kW, the canonical worked-example device from §8.3).

  Key observations for k selection:
""")

for k in K_VALUES:
    buck_k = buck[buck['k'] == k]
    r05 = buck_k[buck_k['device_power_kW'] == 0.5].iloc[0]
    r12 = buck_k[buck_k['device_power_kW'] == 1.2].iloc[0]
    print(f"  k = {k}:")
    print(f"    0.5 kW: {int(r05['ALLOW_count'])} ALLOWs "
          f"({int(r05['Correct-ALLOW'])} correct, {int(r05['Incorrect-ALLOW'])} incorrect)")
    print(f"    1.2 kW: {int(r12['ALLOW_count'])} ALLOWs "
          f"({int(r12['Correct-ALLOW'])} correct, {int(r12['Incorrect-ALLOW'])} incorrect)")
    if r05['ALLOW_count'] == 0 and r12['ALLOW_count'] == 0:
        print(f"    → Zero ALLOWs for both devices: 100% DENY rate (extreme conservatism)")
    print()

print("  LIMITATION (retained per user instruction):")
print("  This evaluation is based on only 176 synthetically aligned solar/load")
print("  pairs. It demonstrates the decision logic but is NOT evidence of zero")
print("  real-world grid-usage violations.")

print("\n" + "=" * 80)
print("DEVICE-POWER SENSITIVITY CHECK COMPLETE")
print("=" * 80)
