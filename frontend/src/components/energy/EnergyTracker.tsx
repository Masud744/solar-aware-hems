import React, { useState, useEffect, useCallback } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { fetchEnergySummary, postSolarEstimate } from '../../api/client';
import type { EnergySummaryResponse } from '../../types';

interface Props {
  tariffRate?: number; // 7.50 BDT / kWh
  showHistoryTable?: boolean;
  onEstimateSaved?: () => void;
}

export const EnergyTracker: React.FC<Props> = ({
  tariffRate = 7.50,
  showHistoryTable = true,
  onEstimateSaved,
}) => {
  const [summary, setSummary] = useState<EnergySummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // User input state for solar contribution
  const [inputKwh, setInputKwh] = useState<string>('');
  const [inputNotes, setInputNotes] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchEnergySummary(tariffRate);
      setSummary(data);
      if (data.today.has_user_solar_estimate) {
        setInputKwh(String(data.today.user_solar_kwh));
        setInputNotes(data.today.notes || '');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load persistent energy accounting from database.');
    } finally {
      setLoading(false);
    }
  }, [tariffRate]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleSaveEstimate = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedKwh = parseFloat(inputKwh);
    if (isNaN(parsedKwh) || parsedKwh < 0) {
      setSaveError('Please enter a valid positive number for solar generation.');
      return;
    }

    try {
      setSaving(true);
      setSaveError(null);
      setSaveSuccess(false);

      const targetDate = summary?.date || new Date().toISOString().slice(0, 10);
      await postSolarEstimate({
        date: targetDate,
        estimated_solar_kwh: parsedKwh,
        notes: inputNotes,
      });

      setSaveSuccess(true);
      await loadSummary();
      if (onEstimateSaved) onEstimateSaved();

      setTimeout(() => {
        setSaveSuccess(false);
      }, 4000);
    } catch (err: any) {
      setSaveError(err?.message || 'Failed to save solar estimate to Supabase.');
    } finally {
      setSaving(false);
    }
  };

  const today = summary?.today;
  const month = summary?.this_month;

  return (
    <div className="energy-tracker-container">
      {/* ── Section Header ────────────────────────────────────── */}
      <div className="sect-head" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span className="sect-label">Persistent Energy & Cost Accounting</span>
          <DataHonestyTag type="CALCULATED" size="sm" />
        </div>
        <span className="sect-sublabel">
          Database-backed timestamp integration · Conservative solar offset model · Asia/Dhaka bounds
        </span>
      </div>

      {loading && !summary && (
        <div className="chart-loading-box" style={{ padding: '32px' }}>
          <div className="spinner" />
          <span>Integrating timestamped energy history from database…</span>
        </div>
      )}

      {error && !summary && (
        <div className="banner" data-v="warning" style={{ marginBottom: '16px' }}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {summary && (
        <>
          {/* ── 3 Primary Energy Cards ──────────────────────────── */}
          <div className="primary-energy-cards-grid">
            {/* Card 1: Total Energy Used */}
            <div className="primary-energy-card glass">
              <div className="card-top-row">
                <span className="card-category-lbl">TOTAL ENERGY USED</span>
                <DataHonestyTag
                  type="CALCULATED"
                  size="sm"
                  tooltip="Calculated from timestamp-integrated ESP32 physical power history. Immune to volatile firmware counter resets."
                />
              </div>

              <div className="primary-val-row">
                <span className="period-pill">Today</span>
                <strong className="primary-val mono">
                  {today ? today.total_energy_kwh.toFixed(4) : '0.0000'}{' '}
                  <small>kWh</small>
                </strong>
              </div>

              <div className="secondary-val-row">
                <span className="secondary-lbl">This Month ({month?.days_recorded || 1}d logged):</span>
                <strong className="secondary-val mono text-teal">
                  {month ? month.total_energy_kwh.toFixed(4) : '0.0000'} kWh
                </strong>
              </div>

              <p className="card-academic-desc">
                Numerically integrated trapezoidal active power over {today?.reading_count || 0} hardware packets. Source of truth is persistent Supabase telemetry.
              </p>
            </div>

            {/* Card 2: User-Estimated Solar Generation */}
            <div className="primary-energy-card glass">
              <div className="card-top-row">
                <span className="card-category-lbl">USER-ESTIMATED SOLAR GENERATION</span>
                <DataHonestyTag
                  type="USER ESTIMATED"
                  size="sm"
                  tooltip="User-reported solar generation. Stored persistently in Supabase. No dedicated physical solar meter is installed."
                />
              </div>

              <div className="primary-val-row">
                <span className="period-pill">Today</span>
                <strong className="primary-val mono text-purple">
                  {today && today.has_user_solar_estimate ? today.user_solar_kwh.toFixed(2) : '0.00'}{' '}
                  <small>kWh</small>
                </strong>
              </div>

              <div className="secondary-val-row">
                <span className="secondary-lbl">This Month Total:</span>
                <strong className="secondary-val mono text-purple">
                  {month ? month.total_solar_kwh.toFixed(2) : '0.00'} kWh
                </strong>
              </div>

              {/* User Input / Edit Box */}
              <form onSubmit={handleSaveEstimate} className="solar-input-form">
                <div className="input-group-row">
                  <div className="input-with-unit">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      placeholder="e.g. 2.00"
                      className="custom-input-text mono solar-number-input"
                      value={inputKwh}
                      onChange={(e) => setInputKwh(e.target.value)}
                      disabled={saving}
                      aria-label="User-Estimated Solar Generation in kWh"
                    />
                    <span className="input-unit">kWh</span>
                  </div>

                  <button
                    type="submit"
                    className="btn-save-solar"
                    disabled={saving || !inputKwh}
                  >
                    {saving ? 'Saving…' : today?.has_user_solar_estimate ? 'Update' : 'Save Estimate'}
                  </button>
                </div>

                {saveSuccess && (
                  <span className="solar-save-msg success">✓ Estimate saved to Supabase</span>
                )}
                {saveError && (
                  <span className="solar-save-msg error">⚠ {saveError}</span>
                )}
              </form>

              <p className="card-academic-desc">
                User-reported estimate. No dedicated solar energy meter is installed.
              </p>
            </div>

            {/* Card 3: Estimated Solar Savings */}
            <div className="primary-energy-card glass">
              <div className="card-top-row">
                <span className="card-category-lbl">ESTIMATED SOLAR SAVINGS</span>
                <DataHonestyTag
                  type="ESTIMATED"
                  size="sm"
                  tooltip="Calculated conservatively from Solar Utilized for Load × baseline tariff (৳7.50/kWh). Never exceeds actual measured consumption."
                />
              </div>

              <div className="primary-val-row">
                <span className="period-pill">Today</span>
                <strong className="primary-val mono text-amber">
                  ৳ {today ? today.estimated_savings_bdt.toFixed(2) : '0.00'}{' '}
                  <small>BDT</small>
                </strong>
              </div>

              <div className="secondary-val-row">
                <span className="secondary-lbl">This Month Total:</span>
                <strong className="secondary-val mono text-amber">
                  ৳ {month ? month.total_savings_bdt.toFixed(2) : '0.00'} BDT
                </strong>
              </div>

              <div className="savings-calc-box">
                <span>Basis: Solar Utilized ({today ? today.solar_utilized_kwh.toFixed(2) : '0.00'} kWh) × ৳{tariffRate.toFixed(2)} / kWh</span>
                {today && (
                  <span className="mono text-muted" style={{ fontSize: '0.68rem' }}>
                    Utilized = min(Measured {today.total_energy_kwh.toFixed(2)} kWh, Solar {today.user_solar_kwh.toFixed(2)} kWh)
                  </span>
                )}
              </div>

              <p className="card-academic-desc">
                Estimated savings based on utilized solar offsetting household load. Not directly measured monetary savings.
              </p>
            </div>
          </div>

          {/* ── Today vs This Month Summary Comparison Strip (6 Metrics) ── */}
          <div className="tracker-comparison-strip glass" style={{ marginTop: '20px' }}>
            {/* TODAY COLUMN */}
            <div className="comparison-col">
              <span className="comp-badge">TODAY ({today?.date})</span>
              <div className="comp-metrics-grid-6">
                <div className="comp-item">
                  <span className="comp-lbl">1. Total Measured Used</span>
                  <strong className="comp-val mono">{today?.total_energy_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="CALCULATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">2. User-Estimated Solar</span>
                  <strong className="comp-val mono text-purple">{today?.user_solar_kwh.toFixed(2)} kWh</strong>
                  <DataHonestyTag type="USER ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">3. Solar Utilized for Load</span>
                  <strong className="comp-val mono text-teal">{today?.solar_utilized_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">4. Remaining Grid Load</span>
                  <strong className="comp-val mono text-rose">{today?.estimated_remaining_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">5. Estimated Excess Solar</span>
                  <strong className="comp-val mono text-muted">{today?.excess_solar_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">6. Estimated Savings</span>
                  <strong className="comp-val mono text-amber">৳ {today?.estimated_savings_bdt.toFixed(2)}</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
              </div>
            </div>

            <div className="comp-divider" />

            {/* THIS MONTH COLUMN */}
            <div className="comparison-col">
              <span className="comp-badge">THIS MONTH ({month?.month}) · {month?.days_recorded || 1}d Recorded</span>
              <div className="comp-metrics-grid-6">
                <div className="comp-item">
                  <span className="comp-lbl">1. Total Measured Used</span>
                  <strong className="comp-val mono">{month?.total_energy_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="CALCULATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">2. Total Estimated Solar</span>
                  <strong className="comp-val mono text-purple">{month?.total_solar_kwh.toFixed(2)} kWh</strong>
                  <DataHonestyTag type="USER ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">3. Total Solar Utilized</span>
                  <strong className="comp-val mono text-teal">{month?.total_solar_utilized_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">4. Total Remaining Grid</span>
                  <strong className="comp-val mono text-rose">{month?.total_remaining_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">5. Total Excess Solar</span>
                  <strong className="comp-val mono text-muted">{month?.total_excess_solar_kwh.toFixed(4)} kWh</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
                <div className="comp-item">
                  <span className="comp-lbl">6. Total Estimated Savings</span>
                  <strong className="comp-val mono text-amber">৳ {month?.total_savings_bdt.toFixed(2)}</strong>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
              </div>
            </div>
          </div>

          {/* ── Daily Historical Breakdown Table (7 Columns) ── */}
          {showHistoryTable && month?.daily_records && month.daily_records.length > 0 && (
            <div className="historical-daily-table-card glass" style={{ marginTop: '20px' }}>
              <div className="sect-head">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="sect-label">Daily Historical Records ({month.month})</span>
                  <DataHonestyTag type="CALCULATED" size="sm" />
                </div>
                <span className="sect-sublabel">
                  Asia/Dhaka calendar days · {month.daily_records.length} days logged
                </span>
              </div>

              <div className="audit-table-wrapper">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Date (BST)</th>
                      <th>Measured Used</th>
                      <th>User Solar</th>
                      <th>Solar Utilized</th>
                      <th>Remaining Load</th>
                      <th>Excess Solar</th>
                      <th>Estimated Savings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {month.daily_records.map((rec) => (
                      <tr key={rec.date}>
                        <td>
                          <strong className="mono">{rec.date}</strong>
                          {rec.date === today?.date && (
                            <span className="badge-today" style={{ marginLeft: '8px' }}>Today</span>
                          )}
                        </td>
                        <td>
                          <strong className="mono">{rec.total_energy_kwh.toFixed(4)} kWh</strong>
                        </td>
                        <td>
                          {rec.has_user_solar_estimate ? (
                            <span className="mono text-purple font-bold">
                              {rec.user_solar_kwh.toFixed(2)} kWh
                            </span>
                          ) : (
                            <span className="text-muted mono">— (0.00)</span>
                          )}
                        </td>
                        <td>
                          <span className="mono text-teal font-bold">
                            {rec.solar_utilized_kwh.toFixed(4)} kWh
                          </span>
                        </td>
                        <td>
                          <span className="mono text-rose">
                            {rec.estimated_remaining_kwh.toFixed(4)} kWh
                          </span>
                        </td>
                        <td>
                          <span className="mono text-muted">
                            {rec.excess_solar_kwh.toFixed(4)} kWh
                          </span>
                        </td>
                        <td>
                          {rec.estimated_savings_bdt > 0 ? (
                            <strong className="mono text-amber font-bold">
                              ৳ {rec.estimated_savings_bdt.toFixed(2)}
                            </strong>
                          ) : (
                            <span className="text-muted mono">৳ 0.00</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
