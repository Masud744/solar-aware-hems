import React, { useState, useMemo } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import type { HourlyForecastData, RiskMargin } from '../../types';

interface Props {
  timeline: HourlyForecastData[];
  riskMargin: RiskMargin | null;
  loading: boolean;
  onRefresh: () => void;
}

export function ForecastPage({
  timeline,
  riskMargin,
  loading,
  onRefresh,
}: Props) {
  const [selectedHourIndex, setSelectedHourIndex] = useState<number>(0);
  const [hoveredHourIndex, setHoveredHourIndex] = useState<number | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  const activeIndex = hoveredHourIndex !== null ? hoveredHourIndex : selectedHourIndex;
  const selectedSlot = timeline[activeIndex] || timeline[0] || null;

  // Compute summary stats over the 24-hour horizon
  const stats = useMemo(() => {
    if (!timeline || timeline.length === 0) return null;

    let peakSolarKw = 0;
    let peakSolarTime = '';
    let peakSurplusKw = -Infinity;
    let peakSurplusTime = '';
    let safeWindowCount = 0;

    timeline.forEach((slot) => {
      if (slot.safeSolarKw > peakSolarKw) {
        peakSolarKw = slot.safeSolarKw;
        peakSolarTime = slot.timeLabel;
      }
      if (slot.safeSurplusKw !== null && slot.safeSurplusKw > peakSurplusKw) {
        peakSurplusKw = slot.safeSurplusKw;
        peakSurplusTime = slot.timeLabel;
      }
      if (slot.safeSurplusKw !== null && slot.safeSurplusKw > 0.001) {
        safeWindowCount++;
      }
    });

    return {
      peakSolarKw,
      peakSolarTime,
      peakSurplusKw: Math.max(0, peakSurplusKw),
      peakSurplusTime,
      safeWindowCount,
    };
  }, [timeline]);

  // Window quality categorizer
  const getWindowQuality = (surplusKw: number | null) => {
    if (surplusKw === null || surplusKw < 0) {
      return { label: 'Not Recommended (Deficit)', status: 'deficit', desc: 'Household load exceeds safe solar generation. Power supplied from AC Grid.' };
    }
    if (surplusKw >= 0.5) {
      return { label: 'Optimal Window (High Surplus)', status: 'optimal', desc: 'High surplus buffer available. Ideal for heavy shiftable appliances.' };
    }
    return { label: 'Marginal Window (Low Surplus)', status: 'marginal', desc: 'Slight surplus available. Suitable for low-power devices only.' };
  };

  const currentQuality = getWindowQuality(selectedSlot?.safeSurplusKw ?? null);

  // SVG Chart Dimensions and Geometry
  const chartData = useMemo(() => {
    if (!timeline || timeline.length === 0) return null;
    const rows = timeline.slice(0, 24);
    const width = 920;
    const height = 280;
    const padX = 48;
    const padTop = 32;
    const padBottom = 42;

    const allValues: number[] = [];
    rows.forEach((r) => {
      if (typeof r.safeSolarKw === 'number') allValues.push(r.safeSolarKw);
      if (typeof r.conservativeLoadKw === 'number' && Number.isFinite(r.conservativeLoadKw)) {
        allValues.push(r.conservativeLoadKw);
      }
    });

    const maxVal = Math.max(...allValues, 1.2);
    const maxKw = Math.max(1.5, Math.ceil(maxVal * 1.2 * 2) / 2);

    const getX = (index: number) =>
      padX + (index / Math.max(rows.length - 1, 1)) * (width - padX * 2);

    const getY = (val: number) =>
      padTop + (1 - Math.max(0, val) / maxKw) * (height - padTop - padBottom);

    const solarPoints: { x: number; y: number }[] = [];
    const loadPoints: { x: number; y: number }[] = [];

    rows.forEach((r, i) => {
      solarPoints.push({ x: getX(i), y: getY(r.safeSolarKw) });
      loadPoints.push({ x: getX(i), y: getY(r.conservativeLoadKw ?? 0) });
    });

    const buildPath = (pts: { x: number; y: number }[]) => {
      if (pts.length === 0) return '';
      return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    };

    const solarPath = buildPath(solarPoints);
    const loadPath = buildPath(loadPoints);

    const zeroY = height - padBottom;
    let solarArea = '';
    if (solarPoints.length > 0) {
      solarArea = `${solarPath} L ${solarPoints[solarPoints.length - 1].x.toFixed(1)} ${zeroY.toFixed(1)} L ${solarPoints[0].x.toFixed(1)} ${zeroY.toFixed(1)} Z`;
    }

    return {
      rows,
      width,
      height,
      maxKw,
      padX,
      padTop,
      padBottom,
      solarPath,
      loadPath,
      solarArea,
      getX,
      getY,
      solarPoints,
      loadPoints,
    };
  }, [timeline]);

  return (
    <div className="page forecast-page">
      {/* 1. Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              OPEN-METEO WEATHER INPUTS + RANDOM FOREST ML MODELS
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
              24-Hour Energy Horizon
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Uncertainty-aware solar generation and household load projections for Kaliakair, BD (Asia/Dhaka).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <DataHonestyTag type="FORECAST" size="md" />
            <button className="btn-secondary" onClick={onRefresh} disabled={loading}>
              {loading ? 'Refreshing…' : '↻ Refresh Predictions'}
            </button>
          </div>
        </div>
      </div>

      {/* 2. Key Horizon Summary Cards */}
      {stats && (
        <div className="forecast-summary-strip" style={{ marginBottom: '24px' }}>
          <div className="kpi-card glass">
            <div className="kpi-card-head">
              <span className="kpi-label">Safe Solar Peak</span>
              <DataHonestyTag type="FORECAST" size="sm" />
            </div>
            <div className="kpi-value mono text-solar">
              {stats.peakSolarKw.toFixed(2)} <small>kW</small>
            </div>
            <span className="kpi-sub">
              {stats.peakSolarKw > 0 ? `Expected at ${stats.peakSolarTime} BST` : 'No daytime solar expected'}
            </span>
          </div>

          <div className="kpi-card glass">
            <div className="kpi-card-head">
              <span className="kpi-label">Peak Safe Surplus</span>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>
            <div className="kpi-value mono text-teal">
              +{stats.peakSurplusKw.toFixed(2)} <small>kW</small>
            </div>
            <span className="kpi-sub">
              {stats.peakSurplusKw > 0 ? `Optimal slot at ${stats.peakSurplusTime} BST` : 'No safe surplus in 24h'}
            </span>
          </div>

          <div className="kpi-card glass">
            <div className="kpi-card-head">
              <span className="kpi-label">Safe Operating Windows</span>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>
            <div className="kpi-value mono text-emerald">
              {stats.safeWindowCount} <small>of 24 hours</small>
            </div>
            <span className="kpi-sub">Hours where Safe Solar exceeds Conservative Load</span>
          </div>

          <div className="kpi-card glass">
            <div className="kpi-card-head">
              <span className="kpi-label">Risk Policy Parameter</span>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>
            <div className="kpi-value mono text-blue">
              k = {riskMargin?.k ?? '1.0'}
            </div>
            <span className="kpi-sub">Heteroskedastic standard deviation buffer</span>
          </div>
        </div>
      )}

      {/* 3. Main Composed Horizon Chart Card */}
      <div className="forecast-chart-card glass" style={{ marginBottom: '24px' }}>
        <div className="sect-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">24-Hour Solar vs Load Horizon</span>
            <DataHonestyTag type="FORECAST" size="sm" />
          </div>
          <span className="sect-sublabel">Hover or tap any hour to inspect exact conservative bounds</span>
        </div>

        {/* Legend */}
        <div className="forecast-legend-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
              <span className="legend-swatch solar-swatch" style={{ width: '14px', height: '3px', background: 'var(--solar)', borderRadius: '2px' }} />
              <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Safe Solar Generation</span>
              <span style={{ color: 'var(--text-3)', fontSize: '0.7rem' }}>(k = 1.0)</span>
            </div>
            <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
              <span className="legend-swatch load-swatch" style={{ width: '14px', height: '3px', background: '#60a5fa', borderRadius: '2px', borderTop: '1px dashed #60a5fa' }} />
              <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Conservative Household Load</span>
              <span style={{ color: 'var(--text-3)', fontSize: '0.7rem' }}>(k = 1.0)</span>
            </div>
            <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
              <span className="legend-swatch surplus-swatch" style={{ width: '10px', height: '10px', background: 'var(--teal)', borderRadius: '2px', opacity: 0.8 }} />
              <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Safe Surplus Operating Windows</span>
            </div>
          </div>
          <span className="legend-loc" style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>Kaliakair, BD (24.07°N, 90.22°E) · Asia/Dhaka (BST)</span>
        </div>

        {/* Chart SVG Visualization */}
        {loading ? (
          <div className="chart-loading-box" style={{ padding: '40px' }}>
            <div className="spinner" />
            <span>Fetching Open-Meteo weather and calculating ML uncertainty bounds…</span>
          </div>
        ) : !chartData || chartData.rows.length === 0 ? (
          <div className="chart-empty-box" style={{ padding: '40px' }}>
            <span>Forecast data temporarily unavailable. Please verify backend connection.</span>
          </div>
        ) : (
          <div className="svg-chart-wrapper" style={{ position: 'relative', width: '100%' }}>
            <svg
              className="horizon-svg-chart"
              viewBox={`0 0 ${chartData.width} ${chartData.height}`}
              style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
              role="img"
              aria-label="24-hour energy horizon composed chart"
              onMouseLeave={() => setHoveredHourIndex(null)}
            >
              <defs>
                <linearGradient id="forecastSolarAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--solar)" stopOpacity="0.30" />
                  <stop offset="85%" stopColor="var(--solar)" stopOpacity="0.04" />
                  <stop offset="100%" stopColor="var(--solar)" stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((ratio) => {
                const y = chartData.getY(chartData.maxKw * ratio);
                const val = chartData.maxKw * ratio;
                return (
                  <g key={ratio}>
                    <line
                      x1={chartData.padX}
                      x2={chartData.width - chartData.padX}
                      y1={y}
                      y2={y}
                      stroke="var(--border)"
                      strokeWidth="1"
                      strokeDasharray={ratio === 0 ? 'none' : '3 3'}
                    />
                    <text
                      x={chartData.padX - 8}
                      y={y + 3.5}
                      fill="var(--text-3)"
                      fontSize="10"
                      fontFamily="monospace"
                      textAnchor="end"
                    >
                      {val.toFixed(1)} kW
                    </text>
                  </g>
                );
              })}

              {/* Solar Area under Curve */}
              {chartData.solarArea && (
                <path d={chartData.solarArea} fill="url(#forecastSolarAreaGrad)" pointerEvents="none" />
              )}

              {/* Conservative Load Curve (Dashed) */}
              {chartData.loadPath && (
                <path
                  d={chartData.loadPath}
                  fill="none"
                  stroke="#60a5fa"
                  strokeWidth="2.4"
                  strokeDasharray="5 4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  pointerEvents="none"
                />
              )}

              {/* Safe Solar Curve (Solid Amber) */}
              {chartData.solarPath && (
                <path
                  d={chartData.solarPath}
                  fill="none"
                  stroke="var(--solar)"
                  strokeWidth="2.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  pointerEvents="none"
                />
              )}

              {/* Time axis labels */}
              {chartData.rows.map((row, idx) => {
                if (idx % 3 !== 0 && idx !== chartData.rows.length - 1) return null;
                const x = chartData.getX(idx);
                return (
                  <text
                    key={row.isoTime}
                    x={x}
                    y={chartData.height - 12}
                    fill="var(--text-3)"
                    fontSize="10.5"
                    fontFamily="monospace"
                    fontWeight="500"
                    textAnchor="middle"
                  >
                    {row.timeLabel}
                  </text>
                );
              })}

              {/* Selected / Hovered Hour Guideline & Markers */}
              {selectedSlot && (
                <g pointerEvents="none">
                  <line
                    x1={chartData.getX(activeIndex)}
                    x2={chartData.getX(activeIndex)}
                    y1={chartData.padTop}
                    y2={chartData.height - chartData.padBottom}
                    stroke="var(--text-2)"
                    strokeWidth="1.4"
                    strokeDasharray="3 3"
                  />
                  {/* Solar point */}
                  <circle
                    cx={chartData.getX(activeIndex)}
                    cy={chartData.getY(selectedSlot.safeSolarKw)}
                    r="5"
                    fill="var(--solar)"
                    stroke="var(--bg-card, #131826)"
                    strokeWidth="2"
                  />
                  {/* Load point */}
                  {selectedSlot.conservativeLoadKw !== null && (
                    <circle
                      cx={chartData.getX(activeIndex)}
                      cy={chartData.getY(selectedSlot.conservativeLoadKw)}
                      r="5"
                      fill="#60a5fa"
                      stroke="var(--bg-card, #131826)"
                      strokeWidth="2"
                    />
                  )}
                </g>
              )}

              {/* Transparent Column Hit-Areas for Interactive Hover / Touch */}
              {chartData.rows.map((_, idx) => {
                const x = chartData.getX(idx);
                const colWidth = (chartData.width - chartData.padX * 2) / Math.max(chartData.rows.length - 1, 1);
                return (
                  <rect
                    key={idx}
                    x={x - colWidth / 2}
                    y={chartData.padTop}
                    width={colWidth}
                    height={chartData.height - chartData.padTop - chartData.padBottom}
                    fill="transparent"
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredHourIndex(idx)}
                    onClick={() => setSelectedHourIndex(idx)}
                    onTouchStart={() => {
                      setHoveredHourIndex(idx);
                      setSelectedHourIndex(idx);
                    }}
                  />
                );
              })}
            </svg>
          </div>
        )}

        {/* 24-Hour Interactive Horizon Slot Matrix */}
        {timeline.length > 0 && (
          <div className="forecast-slot-matrix-wrapper" style={{ marginTop: '16px' }}>
            <div className="hourly-bars-track">
              {timeline.slice(0, 24).map((slot, idx) => {
                const isSelected = idx === activeIndex;
                const surplus = slot.safeSurplusKw ?? 0;
                const isPositive = surplus > 0.001;

                return (
                  <button
                    key={slot.isoTime}
                    className={`hourly-bar-col ${isSelected ? 'selected' : ''} ${isPositive ? 'has-surplus' : 'deficit'}`}
                    onClick={() => setSelectedHourIndex(idx)}
                    onMouseEnter={() => setHoveredHourIndex(idx)}
                    type="button"
                    title={`${slot.timeLabel} BST: Safe Solar ${slot.safeSolarKw.toFixed(2)} kW, Cons. Load ${slot.conservativeLoadKw?.toFixed(2) ?? '—'} kW`}
                  >
                    <span className="bar-hour-label">{slot.timeLabel.split(' ')[0]}</span>
                    <span className={`bar-surplus-indicator ${isPositive ? 'pos' : 'neg'}`}>
                      {isPositive ? `+${surplus.toFixed(1)}` : '—'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 4. Selected Hour Inspector Card */}
      {selectedSlot && (
        <div className={`hour-inspector-card glass quality-${currentQuality.status}`} style={{ marginBottom: '24px' }}>
          <div className="inspector-top-row">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="inspector-time">{selectedSlot.timeLabel} BST</span>
                <span className={`quality-chip status-${currentQuality.status}`}>
                  {currentQuality.label}
                </span>
              </div>
              <p className="inspector-desc">{currentQuality.desc}</p>
            </div>

            <div className="inspector-surplus-badge">
              <span className="surplus-badge-lbl">Safe Surplus</span>
              <strong className={`surplus-badge-val mono ${selectedSlot.safeSurplusKw && selectedSlot.safeSurplusKw > 0 ? 'text-teal' : 'text-muted'}`}>
                {selectedSlot.safeSurplusKw !== null
                  ? `${selectedSlot.safeSurplusKw > 0 ? '+' : ''}${selectedSlot.safeSurplusKw.toFixed(2)} kW`
                  : '— kW'}
              </strong>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>
          </div>

          <div className="inspector-metrics-grid">
            <div className="inspector-metric-box">
              <span className="box-lbl">Safe Solar Generation</span>
              <strong className="box-val mono text-solar">{selectedSlot.safeSolarKw.toFixed(2)} kW</strong>
              <span className="box-sub">Atmosphere: {selectedSlot.solarBucket}</span>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>

            <div className="inspector-metric-box">
              <span className="box-lbl">Conservative Household Load</span>
              <strong className="box-val mono text-blue">{selectedSlot.conservativeLoadKw?.toFixed(2) ?? '—'} kW</strong>
              <span className="box-sub">Time Bucket: {selectedSlot.loadBucket}</span>
              <DataHonestyTag type="CALCULATED" size="sm" />
            </div>

            <div className="inspector-metric-box">
              <span className="box-lbl">Solar Model Raw Prediction</span>
              <strong className="box-val mono">{selectedSlot.predSolarKw.toFixed(2)} kW</strong>
              <span className="box-sub">Without uncertainty discount</span>
              <DataHonestyTag type="FORECAST" size="sm" />
            </div>

            <div className="inspector-metric-box">
              <span className="box-lbl">Load Model Raw Prediction</span>
              <strong className="box-val mono">{selectedSlot.predLoadKw?.toFixed(2) ?? '—'} kW</strong>
              <span className="box-sub">Without conservative buffer</span>
              <DataHonestyTag type="FORECAST" size="sm" />
            </div>
          </div>

          {/* Expandable Technical Risk Details */}
          <div className="tech-details-expander">
            <button
              className="btn-toggle-why"
              onClick={() => setShowTechnicalDetails((prev) => !prev)}
              type="button"
            >
              <span>{showTechnicalDetails ? '▾ Hide Risk & Uncertainty Details' : '▸ Technical Risk & Uncertainty Details (k = 1.0, Heteroskedastic σ)'}</span>
            </button>

            {showTechnicalDetails && (
              <div className="tech-details-body">
                <div className="tech-grid">
                  <div>
                    <strong>Solar Generation Bound:</strong>
                    <p className="mono">
                      S_safe = max(0, {selectedSlot.predSolarKw.toFixed(2)} − 1.0 × {selectedSlot.solarSigmaKw.toFixed(2)}) = {selectedSlot.safeSolarKw.toFixed(2)} kW
                    </p>
                    <small>Cloud cover bucket: {selectedSlot.solarBucket}</small>
                  </div>
                  <div>
                    <strong>Conservative Load Bound:</strong>
                    <p className="mono">
                      L_cons = {selectedSlot.predLoadKw?.toFixed(2) ?? '—'} + 1.0 × {selectedSlot.loadSigmaKw?.toFixed(2) ?? '—'} = {selectedSlot.conservativeLoadKw?.toFixed(2) ?? '—'} kW
                    </p>
                    <small>Diurnal time bucket: {selectedSlot.loadBucket}</small>
                  </div>
                </div>
                <p className="tech-note">
                  Heteroskedastic standard deviation (σ) dynamically expands confidence intervals during highly variable weather (overcast conditions) and peak residential cooking hours to guarantee risk-averse appliance scheduling.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
