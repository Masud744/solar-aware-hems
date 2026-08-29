import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { formatPower, formatVoltage, formatCurrent, formatDateTimeBst, formatTimeBst, getFreshness } from '../../utils/formatting';
import type { SensorReading, HourlyForecastData } from '../../types';

interface PowerHeroProps {
  reading: SensorReading | null;
  timeline: HourlyForecastData[];
  loading: boolean;
  backendOnline: boolean;
  error: string | null;
  onNavigateAppliances: () => void;
}

export const PowerHero: React.FC<PowerHeroProps> = ({
  reading,
  timeline,
  loading,
  backendOnline,
  error,
  onNavigateAppliances,
}) => {
  const powerW = reading?.power_w;
  const formattedPower = formatPower(powerW);
  const freshness = getFreshness(reading?.ts);

  const voltageV = reading?.voltage_v;
  const currentA = reading?.current_a;
  const pf = reading?.power_factor;
  const tempC = reading?.temperature_c;
  const humPct = reading?.humidity_pct;

  // Demand interpretation
  const getDemandMessage = () => {
    if (powerW == null) return 'Waiting for ESP32 telemetry stream';
    if (powerW > 2000) return 'High household demand';
    if (powerW > 800) return 'Moderate household demand';
    return 'Your home is running light (baseload)';
  };

  // Find next best safe surplus opportunity in the next 24 hours
  const safeWindows = timeline
    .filter((slot) => slot.safeSurplusKw !== null && slot.safeSurplusKw > 0)
    .sort((a, b) => (b.safeSurplusKw || 0) - (a.safeSurplusKw || 0));

  const nextBestSlot = safeWindows.length > 0 ? safeWindows[0] : null;

  return (
    <div className="overview-hero-container">
      {/* 1. Main Live Power Card */}
      <div className="overview-hero glass">
        <div className="hero-copy">
          <div className="hero-kicker">
            <span className={`live-pulse-dot ${freshness.status}`} aria-hidden="true" />
            <span className="kicker-title">LIVE HOME LOAD</span>
            <DataHonestyTag type="MEASURED" />
          </div>

          <div className="hero-main-value">
            <span className="hero-num">{formattedPower.value}</span>
            <span className="hero-unit">{formattedPower.unit}</span>
          </div>

          <h2 className="hero-heading">{getDemandMessage()}</h2>
          <p className="hero-subtext">
            {reading?.ts
              ? `Aggregate mains draw captured at ${formatDateTimeBst(reading.ts)} BST.`
              : 'Connect ESP32 telemetry stream to see live physical consumption.'}
          </p>

          {/* Secondary Live Electrical Parameters */}
          <div className="hero-secondary-metrics">
            <div className="hero-metric-item">
              <span className="metric-lbl">Voltage</span>
              <strong className="metric-val">{formatVoltage(voltageV)}</strong>
              <DataHonestyTag type="MEASURED" size="sm" />
            </div>

            <div className="hero-metric-item">
              <span className="metric-lbl">Current</span>
              <strong className="metric-val">{formatCurrent(currentA)}</strong>
              <DataHonestyTag type="MEASURED" size="sm" />
            </div>

            <div className="hero-metric-item">
              <span className="metric-lbl">Power Factor</span>
              <strong className="metric-val">{pf != null ? pf.toFixed(2) : '—'}</strong>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>

            <div className="hero-metric-item">
              <span className="metric-lbl">DHT22 Temp</span>
              <strong className="metric-val">
                {tempC != null ? `${tempC.toFixed(1)}°C` : 'Unavailable'}
              </strong>
              <DataHonestyTag type="MEASURED" size="sm" />
            </div>

            <div className="hero-metric-item">
              <span className="metric-lbl">DHT22 Humidity</span>
              <strong className="metric-val">
                {humPct != null ? `${Math.round(humPct)}% RH` : 'Unavailable'}
              </strong>
              <DataHonestyTag type="MEASURED" size="sm" />
            </div>
          </div>
        </div>

        {/* 2. Next Safe Forecast Opportunity Card */}
        <div className="hero-forecast-sidebar">
          <div className="forecast-side-kicker">
            <span>NEXT SAFE WINDOW</span>
            <DataHonestyTag type="FORECAST" size="sm" />
          </div>

          {nextBestSlot ? (
            <>
              <div className="forecast-side-time">
                {formatTimeBst(nextBestSlot.isoTime)}
                <small>BST</small>
              </div>
              <div className="forecast-side-detail">
                <strong>+{nextBestSlot.safeSurplusKw?.toFixed(2)} kW</strong> safe surplus (k = 1.0)
              </div>
              <p className="forecast-side-note">
                Safe solar ({nextBestSlot.safeSolarKw.toFixed(2)} kW) exceeds conservative load.
              </p>
            </>
          ) : (
            <div className="forecast-side-empty">
              <div className="empty-time-icon">☁</div>
              <strong>No safe solar surplus</strong>
              <p>Keep heavy flexible appliances on grid or deferred.</p>
            </div>
          )}

          <button className="btn-hero-action" onClick={onNavigateAppliances}>
            Check an appliance →
          </button>
        </div>
      </div>
    </div>
  );
};
