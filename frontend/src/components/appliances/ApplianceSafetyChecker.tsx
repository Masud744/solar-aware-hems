import React, { useState, useEffect } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { CustomSelect, type CustomDropdownOption } from '../common/CustomSelect';
import { postDeviceCheck } from '../../api/client';
import { formatTimeBst } from '../../utils/formatting';
import type { DeviceCheckResponse } from '../../types';
import type { ApplianceMeta } from './ApplianceCard';

interface Props {
  selectedAppliance?: ApplianceMeta | null;
  appliances: ApplianceMeta[];
  onApplianceChange?: (appliance: ApplianceMeta) => void;
}

export const ApplianceSafetyChecker: React.FC<Props> = ({
  selectedAppliance,
  appliances,
  onApplianceChange,
}) => {
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');

  // Preset state
  const [currentApplianceKey, setCurrentApplianceKey] = useState<string>(
    selectedAppliance?.key || appliances[0]?.key || 'load_1'
  );

  // Custom simulation state
  const [customName, setCustomName] = useState<string>('Custom Load');
  const [customPowerKw, setCustomPowerKw] = useState<number>(0.80);
  const [customDurationMins, setCustomDurationMins] = useState<number>(45);
  const [customPriority, setCustomPriority] = useState<string>('medium');

  // Time offset state
  const [hourOffset, setHourOffset] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<DeviceCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFormulaDetails, setShowFormulaDetails] = useState<boolean>(false);

  useEffect(() => {
    if (selectedAppliance) {
      setCurrentApplianceKey(selectedAppliance.key);
      setMode('preset');
    }
  }, [selectedAppliance]);

  const activeAppliance = appliances.find((a) => a.key === currentApplianceKey) || appliances[0];

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);

    const now = new Date();
    const target = new Date(now.getTime() + hourOffset * 3600 * 1000);
    target.setMinutes(0, 0, 0);

    const pad = (n: number) => String(n).padStart(2, '0');
    const isoString = `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:00:00`;

    const isPreset = mode === 'preset';
    const evalName = isPreset ? (activeAppliance?.name || 'Appliance') : (customName || 'Custom Load');
    const evalPower = isPreset ? (activeAppliance?.powerKw || 1.0) : Math.max(0.01, customPowerKw || 0.8);
    const evalDuration = isPreset
      ? (activeAppliance?.durationHours || 1.0)
      : Math.max(0.05, (customDurationMins || 45) / 60);

    try {
      const res = await postDeviceCheck({
        device_name: evalName,
        rated_power_kw: evalPower,
        duration_hours: evalDuration,
        target_time: isoString,
      });
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to evaluate appliance run safety. Forecast service may be unavailable.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  // Re-evaluate on changes
  useEffect(() => {
    handleEvaluate();
  }, [mode, currentApplianceKey, customPowerKw, customDurationMins, hourOffset]);

  const resultingMargin = result ? result.safe_surplus_kw - result.rated_power_kw : null;

  // Dropdown options
  const applianceOptions: CustomDropdownOption<string>[] = appliances.map((app) => ({
    value: app.key,
    label: app.name,
    icon: app.icon,
    sublabel: `${app.powerDisplay} · ${app.durationDisplay}`,
  }));

  const timeOptions: CustomDropdownOption<number>[] = [
    { value: 0, label: 'Right Now (Immediate Run)', sublabel: 'Current hour' },
    ...Array.from({ length: 12 }).map((_, i) => {
      const h = i + 1;
      const d = new Date(Date.now() + h * 3600 * 1000);
      return {
        value: h,
        label: `+${h}h Horizon`,
        sublabel: `${formatTimeBst(d)} BST`,
      };
    }),
  ];

  return (
    <div className="safety-checker-card glass">
      <div className="sect-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Appliance Run Safety Checker</span>
          <DataHonestyTag type="FORECAST" size="sm" tooltip="Decision engine safety evaluation using Open-Meteo + ML bounds" />
        </div>
        <span className="sect-sublabel">Pre-run solar surplus verification</span>
      </div>

      {/* Mode Selection Tabs: Preset vs Custom Simulation */}
      <div className="checker-mode-tabs">
        <button
          className={`mode-tab-btn ${mode === 'preset' ? 'active' : ''}`}
          onClick={() => setMode('preset')}
          type="button"
        >
          <span>📋</span> Configured Appliances (Presets)
        </button>
        <button
          className={`mode-tab-btn ${mode === 'custom' ? 'active' : ''}`}
          onClick={() => setMode('custom')}
          type="button"
        >
          <span>⚡</span> Custom Safety Simulation
        </button>
      </div>

      {mode === 'custom' && (
        <div className="simulation-notice-bar">
          <span className="sim-badge">FORECAST SIMULATION ONLY</span>
          <span className="sim-desc">
            Evaluates solar surplus compatibility for user-defined loads without altering physical ESP32 relay bank circuits.
          </span>
        </div>
      )}

      {/* Mode 1: Preset Selectors */}
      {mode === 'preset' && (
        <div className="checker-controls-row">
          <CustomSelect
            label="Target Appliance"
            options={applianceOptions}
            value={currentApplianceKey}
            onChange={(val) => {
              setCurrentApplianceKey(val);
              const found = appliances.find((a) => a.key === val);
              if (found && onApplianceChange) onApplianceChange(found);
            }}
          />

          <CustomSelect
            label="Execution Time"
            options={timeOptions}
            value={hourOffset}
            onChange={(val) => setHourOffset(val)}
          />

          <button
            className="btn-evaluate"
            onClick={handleEvaluate}
            disabled={loading}
            type="button"
          >
            {loading ? <><span className="spinner" /> Evaluating…</> : 'Evaluate Safety'}
          </button>
        </div>
      )}

      {/* Mode 2: Custom Simulation Form */}
      {mode === 'custom' && (
        <div className="custom-sim-form-grid">
          <div className="control-field">
            <label className="field-label">Appliance Name</label>
            <input
              type="text"
              className="custom-input-text"
              placeholder="e.g. EV Charger, Heater"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
            />
          </div>

          <div className="control-field">
            <label className="field-label">Rated Power (kW)</label>
            <input
              type="number"
              step="0.05"
              min="0.01"
              max="10.0"
              className="custom-input-text mono"
              value={customPowerKw}
              onChange={(e) => setCustomPowerKw(parseFloat(e.target.value) || 0.1)}
            />
          </div>

          <div className="control-field">
            <label className="field-label">Duration (Minutes)</label>
            <input
              type="number"
              step="5"
              min="5"
              max="1440"
              className="custom-input-text mono"
              value={customDurationMins}
              onChange={(e) => setCustomDurationMins(parseInt(e.target.value, 10) || 15)}
            />
          </div>

          <CustomSelect
            label="Priority (Optional)"
            options={[
              { value: 'high', label: 'High Priority', sublabel: 'Essential load' },
              { value: 'medium', label: 'Medium Priority', sublabel: 'Standard run' },
              { value: 'low', label: 'Low Priority', sublabel: 'Flexible / Shiftable' },
            ]}
            value={customPriority}
            onChange={(val) => setCustomPriority(val)}
          />

          <CustomSelect
            label="Execution Time"
            options={timeOptions}
            value={hourOffset}
            onChange={(val) => setHourOffset(val)}
          />

          <div className="control-field" style={{ justifyContent: 'flex-end' }}>
            <button
              className="btn-evaluate"
              onClick={handleEvaluate}
              disabled={loading}
              type="button"
              style={{ width: '100%' }}
            >
              {loading ? <><span className="spinner" /> Evaluating…</> : 'Run Safety Simulation'}
            </button>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="banner" data-v="warning" style={{ marginTop: '14px' }}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Evaluation Results */}
      {result && (
        <div className={`safety-verdict-container verdict-${result.decision.toLowerCase()}`}>
          <div className="verdict-banner-head">
            <div className="verdict-badge-row">
              <span className="verdict-icon">
                {result.decision === 'ALLOW' ? '✓' : '✕'}
              </span>
              <div>
                <strong className="verdict-title">
                  {result.decision === 'ALLOW' ? 'Safe to Run on Solar' : 'Not Safe for Solar Routing'}
                </strong>
                <p className="verdict-reason">{result.reason}</p>
              </div>
            </div>
            <DataHonestyTag type="CALCULATED" size="sm" />
          </div>

          {/* 3 Core Decision Metrics */}
          <div className="verdict-kpi-grid">
            <div className="verdict-kpi-box">
              <span className="kpi-box-lbl">Available Safe Surplus</span>
              <strong className={`kpi-box-val mono ${result.safe_surplus_kw >= 0 ? 'text-teal' : 'text-amber'}`}>
                {result.safe_surplus_kw > 0 ? '+' : ''}{result.safe_surplus_kw.toFixed(2)} kW
              </strong>
              <span className="kpi-box-sub">Safe Solar − Conservative Base Load</span>
            </div>

            <div className="verdict-kpi-box">
              <span className="kpi-box-lbl">Appliance Required Power</span>
              <strong className="kpi-box-val mono text-blue">
                {result.rated_power_kw.toFixed(2)} kW
              </strong>
              <span className="kpi-box-sub">Continuous demand ({Math.round(result.duration_hours * 60)} mins)</span>
            </div>

            <div className="verdict-kpi-box">
              <span className="kpi-box-lbl">Resulting Safety Margin</span>
              <strong className={`kpi-box-val mono ${resultingMargin !== null && resultingMargin >= 0 ? 'text-teal' : 'text-amber'}`}>
                {resultingMargin !== null ? `${resultingMargin > 0 ? '+' : ''}${resultingMargin.toFixed(2)} kW` : '—'}
              </strong>
              <span className="kpi-box-sub">
                {resultingMargin !== null && resultingMargin >= 0 ? 'Surplus buffer maintained' : 'Grid deficit required'}
              </span>
            </div>
          </div>

          {/* Expandable "Why this decision?" section */}
          <div className="why-decision-section">
            <button
              className="btn-toggle-why"
              onClick={() => setShowFormulaDetails((prev) => !prev)}
              type="button"
            >
              <span>{showFormulaDetails ? '▾ Hide decision details' : '▸ Why this decision? (Energy Balancing & Bounds)'}</span>
            </button>

            {showFormulaDetails && (
              <div className="why-decision-body">
                <div className="why-grid">
                  <div>
                    <span className="why-lbl">Safe Solar Generation (k = {result.k}):</span>
                    <p className="why-val mono">
                      {result.safe_solar_kw.toFixed(2)} kW{' '}
                      <small>(Pred: {result.predicted_solar_kw.toFixed(2)} kW − {result.k}×{result.solar_sigma_kw.toFixed(2)} σ)</small>
                    </p>
                  </div>
                  <div>
                    <span className="why-lbl">Conservative Base Household Load (k = {result.k}):</span>
                    <p className="why-val mono">
                      {result.conservative_load_kw.toFixed(2)} kW{' '}
                      <small>(Pred: {result.predicted_load_kw.toFixed(2)} kW + {result.k}×{result.load_sigma_kw.toFixed(2)} σ)</small>
                    </p>
                  </div>
                </div>
                <p className="why-note">
                  <strong>Energy Balancing Principle:</strong> Predicted solar generation first offsets the concurrent base household load ({result.conservative_load_kw.toFixed(2)} kW). Only the remaining conservative safe surplus ({result.safe_surplus_kw > 0 ? '+' : ''}{result.safe_surplus_kw.toFixed(2)} kW) is evaluated against the additional appliance ({result.rated_power_kw.toFixed(2)} kW) continuously across its entire {Math.round(result.duration_hours * 60)}-minute run.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
