import React, { useState, useEffect, useCallback } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { CustomSelect, type CustomDropdownOption } from '../common/CustomSelect';
import { postScheduleRecommend } from '../../api/client';
import { formatTimeBst } from '../../utils/formatting';
import type { ScheduleRecommendResponse } from '../../types';
import type { ApplianceMeta } from './ApplianceCard';

interface Props {
  shiftableAppliances: ApplianceMeta[];
  tariffRate?: number; // 7.50 BDT / kWh
}

export const ScheduleRecommendations: React.FC<Props> = ({
  shiftableAppliances,
  tariffRate = 7.5,
}) => {
  const [selectedKey, setSelectedKey] = useState<string>(
    shiftableAppliances[0]?.key || 'load_1'
  );

  // Custom Appliance Schedule Parameters
  const [customName, setCustomName] = useState<string>('Custom Appliance');
  const [customPowerKw, setCustomPowerKw] = useState<number>(0.80);
  const [customDurationMins, setCustomDurationMins] = useState<number>(45);
  const [customPriority, setCustomPriority] = useState<string>('medium');

  const [scheduleData, setScheduleData] = useState<ScheduleRecommendResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isCustom = selectedKey === 'custom';
  const activeAppliance = shiftableAppliances.find((a) => a.key === selectedKey);

  const evalName = isCustom ? (customName || 'Custom Appliance') : (activeAppliance?.name || 'Appliance');
  const evalPowerKw = isCustom ? Math.max(0.01, customPowerKw || 0.8) : (activeAppliance?.powerKw || 1.0);
  const evalDurationHours = isCustom
    ? Math.max(0.05, (customDurationMins || 45) / 60)
    : (activeAppliance?.durationHours || 1.0);

  const fetchSchedule = useCallback(async () => {
    setLoading(true);
    setError(null);

    const now = new Date();
    now.setMinutes(0, 0, 0);
    const end = new Date(now.getTime() + 24 * 3600 * 1000);

    const pad = (n: number) => String(n).padStart(2, '0');
    const toIso = (d: Date) =>
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00:00`;

    try {
      const res = await postScheduleRecommend({
        device_name: evalName,
        rated_power_kw: evalPowerKw,
        duration_hours: evalDurationHours,
        window_start: toIso(now),
        window_end: toIso(end),
      });
      setScheduleData(res);
    } catch (err: any) {
      setError(err?.message || 'Schedule optimization currently unavailable. Check forecast stream.');
      setScheduleData(null);
    } finally {
      setLoading(false);
    }
  }, [evalName, evalPowerKw, evalDurationHours]);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const cycleKwh = evalPowerKw * evalDurationHours;
  const cycleCost = (cycleKwh * tariffRate).toFixed(2);
  const durationDisplayMins = Math.round(evalDurationHours * 60);

  return (
    <div className="schedule-recommendations-card glass">
      <div className="sect-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Forecast-Based Schedule Recommendation</span>
          <DataHonestyTag type="FORECAST" size="sm" tooltip="Advisory optimal start times computed from 24-hour safe surplus horizon" />
        </div>
        <span className="sect-sublabel">Advisory duration-aware recommendation (does not auto-switch physical relays)</span>
      </div>

      {/* Appliance Selector Tabs + Custom Mode */}
      <div className="schedule-tabs-row">
        {shiftableAppliances.map((app) => (
          <button
            key={app.key}
            className={`schedule-tab-btn ${selectedKey === app.key ? 'active' : ''}`}
            onClick={() => setSelectedKey(app.key)}
            type="button"
          >
            <span>{app.icon}</span>
            <strong>{app.name}</strong>
            <small>({app.powerDisplay})</small>
          </button>
        ))}

        <button
          className={`schedule-tab-btn tab-custom ${isCustom ? 'active' : ''}`}
          onClick={() => setSelectedKey('custom')}
          type="button"
        >
          <span>⚡</span>
          <strong>Custom Schedule</strong>
          <small>(Simulation)</small>
        </button>
      </div>

      {/* Custom Schedule Simulation Form */}
      {isCustom ? (
        <div style={{ margin: '14px 0' }}>
          <div className="simulation-notice-bar">
            <span className="sim-badge">FORECAST / SIMULATION ONLY</span>
            <span className="sim-desc">
              Advisory 24-hour schedule simulation for custom user-defined loads. Does not actuate physical ESP32 relays.
            </span>
          </div>

          <div className="custom-sim-form-grid" style={{ marginBottom: '14px' }}>
            <div className="control-field">
              <label className="field-label">Custom Appliance Name</label>
              <input
                type="text"
                className="custom-input-text"
                placeholder="e.g. EV Charger, Space Heater"
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
              <label className="field-label">Run Duration (Minutes)</label>
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

            <div className="control-field" style={{ justifyContent: 'flex-end' }}>
              <button
                className="btn-evaluate"
                onClick={fetchSchedule}
                disabled={loading}
                type="button"
                style={{ width: '100%' }}
              >
                {loading ? <><span className="spinner" /> Optimizing…</> : 'Run Custom Optimizer'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Non-shiftable exclusion note for preset mode */
        <div className="continuous-exclusion-note">
          <span>ℹ</span>
          <span>
            <strong>Refrigerator (Load 3)</strong> is continuous baseload (24/7 food preservation) and is excluded from schedule shifting.
          </span>
        </div>
      )}

      {loading && (
        <div className="schedule-loading-box">
          <div className="spinner" />
          <span>Computing continuous 24-hour solar windows for {evalName} ({evalPowerKw} kW, {durationDisplayMins}m)…</span>
        </div>
      )}

      {error && !loading && (
        <div className="banner" data-v="warning" style={{ margin: '14px 0' }}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {scheduleData && !loading && (
        <div className="schedule-content">
          {/* Best Recommended Window Banner */}
          <div className={`recommend-banner ${scheduleData.recommended_start ? 'has-window' : 'no-window'}`}>
            {scheduleData.recommended_start ? (
              <div className="recommend-banner-inner">
                <div className="rec-time-badge">
                  <span className="rec-lbl">RECOMMENDED START</span>
                  <strong className="rec-time">{formatTimeBst(scheduleData.recommended_start)}</strong>
                  <span className="rec-tz">BST</span>
                </div>
                <div className="rec-details">
                  <h4>Continuous Safe Solar Window Found</h4>
                  <p>
                    Starting the <strong>{scheduleData.device_name}</strong> ({scheduleData.rated_power_kw} kW) at {formatTimeBst(scheduleData.recommended_start)} BST maintains continuous safe surplus buffer for the full <strong>{durationDisplayMins} min</strong> run with minimal grid draw risk.
                  </p>
                </div>
                <div className="rec-cycle-cost">
                  <span className="cost-lbl">Est. Cycle Tariff Basis</span>
                  <strong className="cost-val mono">৳ {cycleCost} BDT</strong>
                  <span className="cost-sub">{cycleKwh.toFixed(2)} kWh @ ৳{tariffRate.toFixed(2)}/kWh</span>
                  <DataHonestyTag type="ESTIMATED" size="sm" />
                </div>
              </div>
            ) : (
              <div className="recommend-banner-empty">
                <span className="empty-icon">☁</span>
                <div>
                  <strong>No Continuous Safe Solar Window in Next 24 Hours</strong>
                  <p>
                    Safe solar surplus does not continuously exceed <strong>{scheduleData.rated_power_kw} kW</strong> for the required <strong>{durationDisplayMins} min</strong> cycle. Keep appliance on AC Grid or defer until weather conditions improve.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Hourly Slots Table */}
          <div className="slots-table-wrapper">
            <h4 className="slots-table-title">24-Hour Consecutive Horizon Breakdown ({scheduleData.slots.length} Hours)</h4>
            <div className="slots-grid">
              {scheduleData.slots.map((slot) => {
                const isAllow = slot.decision === 'ALLOW';
                const isBest = scheduleData.recommended_start && new Date(slot.start_time).getTime() === new Date(scheduleData.recommended_start).getTime();
                const hasPositiveSurplus = slot.safe_surplus_kw > 0.005;

                const badgeText = isBest
                  ? '★ Best'
                  : isAllow
                  ? 'Safe'
                  : hasPositiveSurplus
                  ? 'Low Surplus'
                  : 'Deficit';

                const badgeClass = (isBest || isAllow)
                  ? 'badge-allow'
                  : hasPositiveSurplus
                  ? 'badge-marginal'
                  : 'badge-deny';

                return (
                  <div
                    key={slot.start_time}
                    className={`slot-card ${isAllow ? 'slot-allow' : hasPositiveSurplus ? 'slot-marginal' : 'slot-deny'} ${isBest ? 'slot-best' : ''}`}
                  >
                    <div className="slot-head">
                      <span className="slot-time">{formatTimeBst(slot.start_time)}</span>
                      <span className={`slot-badge ${badgeClass}`}>
                        {badgeText}
                      </span>
                    </div>

                    <div className="slot-surplus-row">
                      <span className="surplus-lbl">Surplus:</span>
                      <strong className={`surplus-val mono ${slot.safe_surplus_kw >= 0 ? 'text-teal' : 'text-muted'}`}>
                        {slot.safe_surplus_kw > 0 ? '+' : ''}{slot.safe_surplus_kw.toFixed(2)} kW
                      </strong>
                    </div>

                    <div className="slot-sub-info">
                      <span>Solar: {slot.safe_solar_kw.toFixed(2)} kW</span>
                      <span>Base Load: {slot.conservative_load_kw.toFixed(2)} kW</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
