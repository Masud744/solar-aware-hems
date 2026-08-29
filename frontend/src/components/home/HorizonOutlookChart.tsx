import React, { useMemo, useState } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import type { HourlyForecastData } from '../../types';

interface Props {
  timeline: HourlyForecastData[];
  loading: boolean;
  onNavigateForecast?: () => void;
}

export const HorizonOutlookChart: React.FC<Props> = ({
  timeline,
  loading,
  onNavigateForecast,
}) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const chartData = useMemo(() => {
    if (!timeline || timeline.length === 0) return null;
    const rows = timeline.slice(0, 24);
    const width = 860;
    const height = 260;
    const padX = 44;
    const padTop = 28;
    const padBottom = 38;

    const allValues: number[] = [];
    rows.forEach((r) => {
      if (typeof r.safeSolarKw === 'number') allValues.push(r.safeSolarKw);
      if (typeof r.conservativeLoadKw === 'number' && Number.isFinite(r.conservativeLoadKw)) {
        allValues.push(r.conservativeLoadKw);
      }
      if (r.safeSurplusKw != null && r.safeSurplusKw > 0) {
        allValues.push(r.safeSurplusKw);
      }
    });

    const maxVal = Math.max(...allValues, 1.2);
    // Ceiling to nearest 0.5 kW for cleaner grid labels
    const maxKw = Math.max(1.5, Math.ceil(maxVal * 1.15 * 2) / 2);

    const getX = (index: number) =>
      padX + (index / Math.max(rows.length - 1, 1)) * (width - padX * 2);

    const getY = (val: number) =>
      padTop + (1 - Math.max(0, val) / maxKw) * (height - padTop - padBottom);

    const pathString = (accessor: (r: HourlyForecastData) => number | null) => {
      let d = '';
      let isFirst = true;
      rows.forEach((r, i) => {
        const v = accessor(r);
        if (v !== null && Number.isFinite(v)) {
          const x = getX(i).toFixed(1);
          const y = getY(v).toFixed(1);
          if (isFirst) {
            d += `M ${x} ${y}`;
            isFirst = false;
          } else {
            d += ` L ${x} ${y}`;
          }
        }
      });
      return d;
    };

    const solarPath = pathString((r) => r.safeSolarKw);
    const loadPath = pathString((r) => r.conservativeLoadKw);
    const surplusPath = pathString((r) => {
      const consLoad = r.conservativeLoadKw ?? 0;
      const surplus = r.safeSolarKw - consLoad;
      return Math.max(0, surplus);
    });

    // Solar area under curve
    let solarArea = '';
    if (solarPath && rows.length > 0) {
      solarArea = `${solarPath} L ${getX(rows.length - 1).toFixed(1)} ${(height - padBottom).toFixed(1)} L ${getX(0).toFixed(1)} ${(height - padBottom).toFixed(1)} Z`;
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
      surplusPath,
      solarArea,
      getX,
      getY,
    };
  }, [timeline]);

  if (loading) {
    return (
      <div className="horizon-outlook-card glass">
        <div className="sect-head">
          <span className="sect-label">24-Hour Energy Horizon</span>
          <span className="sect-sublabel">Refreshing predictions...</span>
        </div>
        <div className="chart-loading-box">
          <div className="spinner" />
          <span>Refreshing 24-hour weather & ML predictions…</span>
        </div>
      </div>
    );
  }

  if (!chartData || chartData.rows.length === 0) {
    return (
      <div className="horizon-outlook-card glass">
        <div className="sect-head">
          <span className="sect-label">24-Hour Energy Horizon</span>
          <DataHonestyTag type="FORECAST" size="sm" />
        </div>
        <div className="chart-empty-box">
          <span>Forecast service unavailable. Waiting for prediction stream.</span>
        </div>
      </div>
    );
  }

  const activeHoverRow = hoveredIdx !== null && chartData.rows[hoveredIdx] ? chartData.rows[hoveredIdx] : null;
  const hoverX = hoveredIdx !== null ? chartData.getX(hoveredIdx) : 0;
  const hoverSolarY = activeHoverRow ? chartData.getY(activeHoverRow.safeSolarKw) : 0;
  const hoverLoadY = activeHoverRow && activeHoverRow.conservativeLoadKw !== null ? chartData.getY(activeHoverRow.conservativeLoadKw) : null;
  const hoverSurplusVal = activeHoverRow
    ? activeHoverRow.safeSolarKw - (activeHoverRow.conservativeLoadKw ?? 0)
    : null;
  const hoverSurplusY = hoverSurplusVal !== null ? chartData.getY(Math.max(0, hoverSurplusVal)) : null;

  return (
    <div className="horizon-outlook-card glass">
      <div className="sect-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">24-Hour Energy Horizon</span>
          <DataHonestyTag type="FORECAST" size="sm" />
        </div>
        {onNavigateForecast && (
          <button className="btn-link" onClick={onNavigateForecast}>
            Full Forecast View →
          </button>
        )}
      </div>

      <div className="chart-legend-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
            <span className="legend-swatch solar-swatch" style={{ width: '12px', height: '3px', background: 'var(--solar)', borderRadius: '2px' }} />
            <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Safe Solar</span>
            <span style={{ color: 'var(--text-3)', fontSize: '0.7rem' }}>(k = 1.0)</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
            <span className="legend-swatch load-swatch" style={{ width: '12px', height: '3px', background: '#60a5fa', borderRadius: '2px', borderTop: '1px dashed #60a5fa' }} />
            <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Conservative Load</span>
            <span style={{ color: 'var(--text-3)', fontSize: '0.7rem' }}>(k = 1.0)</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
            <span className="legend-swatch surplus-swatch" style={{ width: '12px', height: '3px', background: 'var(--teal)', borderRadius: '2px' }} />
            <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>Safe Surplus</span>
          </div>
        </div>
        <span className="legend-unit" style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--text-3)' }}>Power (kW)</span>
      </div>

      <div className="svg-chart-wrapper" style={{ position: 'relative', marginTop: '12px', width: '100%' }}>
        <svg
          className="horizon-svg-chart"
          viewBox={`0 0 ${chartData.width} ${chartData.height}`}
          style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
          role="img"
          aria-label="24-hour forecast chart showing safe solar, conservative load, and safe surplus in kilowatts"
          onMouseLeave={() => setHoveredIdx(null)}
        >
          <defs>
            <linearGradient id="solarAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--solar)" stopOpacity="0.25" />
              <stop offset="85%" stopColor="var(--solar)" stopOpacity="0.02" />
              <stop offset="100%" stopColor="var(--solar)" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines (0, 0.5, 1.0, max) */}
          {[0, 0.33, 0.66, 1].map((ratio) => {
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
                  {val.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Solar fill area */}
          {chartData.solarArea && (
            <path d={chartData.solarArea} fill="url(#solarAreaGrad)" pointerEvents="none" />
          )}

          {/* Safe surplus curve (shaded under zero or line) */}
          {chartData.surplusPath && (
            <path
              d={chartData.surplusPath}
              fill="none"
              stroke="var(--teal)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              pointerEvents="none"
            />
          )}

          {/* Conservative load line */}
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

          {/* Safe solar line */}
          {chartData.solarPath && (
            <path
              d={chartData.solarPath}
              fill="none"
              stroke="var(--solar)"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              pointerEvents="none"
            />
          )}

          {/* X-axis time labels (evenly spaced every 3 hours across the 24h horizon) */}
          {chartData.rows.map((row, idx) => {
            if (idx % 3 !== 0) return null;
            const x = chartData.getX(idx);
            const anchor = idx === 0 ? 'start' : 'middle';
            return (
              <text
                key={row.isoTime}
                x={x}
                y={chartData.height - 12}
                fill="var(--text-3)"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="500"
                textAnchor={anchor}
              >
                {row.timeLabel}
              </text>
            );
          })}

          {/* Hover guideline and dots */}
          {activeHoverRow && (
            <g pointerEvents="none">
              {/* Vertical guideline */}
              <line
                x1={hoverX}
                x2={hoverX}
                y1={chartData.padTop}
                y2={chartData.height - chartData.padBottom}
                stroke="var(--text-2)"
                strokeWidth="1.2"
                strokeDasharray="3 3"
              />

              {/* Safe Solar Dot */}
              <circle
                cx={hoverX}
                cy={hoverSolarY}
                r="4.5"
                fill="var(--solar)"
                stroke="var(--bg-card, #131826)"
                strokeWidth="2"
              />

              {/* Conservative Load Dot */}
              {hoverLoadY !== null && (
                <circle
                  cx={hoverX}
                  cy={hoverLoadY}
                  r="4.5"
                  fill="#60a5fa"
                  stroke="var(--bg-card, #131826)"
                  strokeWidth="2"
                />
              )}

              {/* Safe Surplus Dot */}
              {hoverSurplusY !== null && (
                <circle
                  cx={hoverX}
                  cy={hoverSurplusY}
                  r="4"
                  fill="var(--teal)"
                  stroke="var(--bg-card, #131826)"
                  strokeWidth="2"
                />
              )}
            </g>
          )}

          {/* Transparent interactive hit areas across 24 hours */}
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
                style={{ cursor: 'crosshair' }}
                onMouseEnter={() => setHoveredIdx(idx)}
                onTouchStart={() => setHoveredIdx(idx)}
              />
            );
          })}
        </svg>

        {/* Floating Tooltip Box */}
        {activeHoverRow && (
          <div
            className="chart-hover-tooltip glass-strong"
            style={{
              position: 'absolute',
              top: '8px',
              left: `${Math.min(Math.max((hoverX / chartData.width) * 100, 14), 86)}%`,
              transform: 'translateX(-50%)',
              padding: '10px 14px',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--glass-border)',
              background: 'rgba(15, 23, 42, 0.88)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
              pointerEvents: 'none',
              zIndex: 10,
              minWidth: '180px',
              backdropFilter: 'blur(12px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '4px' }}>
              <strong style={{ fontSize: '0.8125rem', color: 'var(--text-1)' }}>
                {activeHoverRow.timeLabel} BST
              </strong>
              <span style={{ fontSize: '0.6875rem', color: 'var(--text-3)', fontWeight: 600 }}>
                {activeHoverRow.isNight ? '🌙 Night' : '☀️ Day'}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--solar)' }} />
                  Safe Solar:
                </span>
                <strong className="mono" style={{ color: 'var(--solar-text)' }}>
                  {activeHoverRow.safeSolarKw.toFixed(2)} kW
                </strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#60a5fa' }} />
                  Conservative Load:
                </span>
                <strong className="mono" style={{ color: '#93c5fd' }}>
                  {activeHoverRow.conservativeLoadKw !== null ? `${activeHoverRow.conservativeLoadKw.toFixed(2)} kW` : '— kW'}
                </strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px', paddingTop: '3px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <span style={{ color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--teal)' }} />
                  Safe Surplus:
                </span>
                <strong
                  className="mono"
                  style={{
                    color: hoverSurplusVal !== null && hoverSurplusVal > 0 ? 'var(--teal-text)' : 'var(--text-3)',
                  }}
                >
                  {hoverSurplusVal !== null
                    ? `${hoverSurplusVal > 0 ? '+' : ''}${hoverSurplusVal.toFixed(2)} kW`
                    : '— kW'}
                </strong>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="chart-footer-note" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <span>Forecast basis: Open-Meteo Kaliakair weather inputs + Random Forest ML models (k = 1.0)</span>
        <span style={{ color: 'var(--text-3)', fontSize: '0.6875rem' }}>Hover over any hour to inspect numerical bounds</span>
      </div>
    </div>
  );
};
