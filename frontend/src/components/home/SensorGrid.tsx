import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { formatPower } from '../../utils/formatting';
import type { SensorReading, HourlyForecastData } from '../../types';

interface SensorStripProps {
  reading: SensorReading | null;
  timeline: HourlyForecastData[];
  loading: boolean;
}

/**
 * Compact High-Value KPI Strip (Section 1.D):
 * 1. Live Household Power [MEASURED]
 * 2. Safe Solar (Next Hour) [FORECAST]
 * 3. Conservative Load (Next Hour) [FORECAST]
 * 4. Safe Surplus (Next Hour) [CALCULATED]
 */
export function SensorStrip({ reading, timeline, loading }: SensorStripProps) {
  if (loading) {
    return (
      <div className="kpi-strip">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="kpi-card glass">
            <div className="skel" style={{ width: 60, height: 14 }} />
            <div className="skel" style={{ width: 90, height: 26, margin: '8px 0' }} />
            <div className="skel" style={{ width: 120, height: 10 }} />
          </div>
        ))}
      </div>
    );
  }

  const livePowerFormatted = formatPower(reading?.power_w);
  const nextHour = timeline.length > 0 ? timeline[0] : null;

  const safeSolarVal = nextHour ? `${nextHour.safeSolarKw.toFixed(2)} kW` : '— kW';
  const consLoadVal = nextHour?.conservativeLoadKw != null ? `${nextHour.conservativeLoadKw.toFixed(2)} kW` : '— kW';
  const safeSurplusVal = nextHour?.safeSurplusKw != null
    ? `${nextHour.safeSurplusKw > 0 ? '+' : ''}${nextHour.safeSurplusKw.toFixed(2)} kW`
    : '— kW';

  return (
    <div className="kpi-strip">
      {/* 1. Live Power */}
      <div className="kpi-card glass">
        <div className="kpi-card-head">
          <span className="kpi-label">Live Power Draw</span>
          <DataHonestyTag type="MEASURED" size="sm" />
        </div>
        <div className="kpi-value mono text-emerald">
          {livePowerFormatted.value} <small>{livePowerFormatted.unit}</small>
        </div>
        <span className="kpi-sub">Real power on aggregate AC mains</span>
      </div>

      {/* 2. Safe Solar Next Hour */}
      <div className="kpi-card glass">
        <div className="kpi-card-head">
          <span className="kpi-label">Safe Solar (Next Hr)</span>
          <DataHonestyTag type="FORECAST" size="sm" />
        </div>
        <div className="kpi-value mono text-solar">
          {safeSolarVal}
        </div>
        <span className="kpi-sub">P_solar − 1.0σ (Clear/Overcast model)</span>
      </div>

      {/* 3. Conservative Load Next Hour */}
      <div className="kpi-card glass">
        <div className="kpi-card-head">
          <span className="kpi-label">Conservative Load</span>
          <DataHonestyTag type="FORECAST" size="sm" />
        </div>
        <div className="kpi-value mono text-blue">
          {consLoadVal}
        </div>
        <span className="kpi-sub">
          {nextHour?.conservativeLoadKw != null
            ? (nextHour.historyMode === 'benchmark_profile_fallback'
                ? 'P_load + 1.0σ (UCI benchmark profile lags)'
                : 'P_load + 1.0σ (Measured sensor history)')
            : 'Forecast unavailable'}
        </span>
      </div>

      {/* 4. Safe Surplus Next Hour */}
      <div className="kpi-card glass">
        <div className="kpi-card-head">
          <span className="kpi-label">Safe Surplus (Next Hr)</span>
          <DataHonestyTag type="CALCULATED" size="sm" />
        </div>
        <div className={`kpi-value mono ${nextHour?.safeSurplusKw && nextHour.safeSurplusKw > 0 ? 'text-teal' : 'text-muted'}`}>
          {safeSurplusVal}
        </div>
        <span className="kpi-sub">Safe Solar − Conservative Load</span>
      </div>
    </div>
  );
}
