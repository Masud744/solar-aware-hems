import React, { useMemo } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { formatTimeBst, formatDateTimeBst, formatVoltage, formatCurrent } from '../../utils/formatting';
import type { SensorReading } from '../../types';

interface Props {
  reading: SensorReading | null;
  history: SensorReading[];
  loading: boolean;
  tariffRate?: number; // 7.50 BDT / kWh
}

export function HistoryPage({
  history,
  loading,
}: Props) {
  // Prepare historical chart points
  const chartPoints = useMemo(() => {
    if (!history || history.length === 0) return [];
    return history
      .filter((r) => r.ts && typeof r.power_w === 'number')
      .slice(-40)
      .map((r) => ({
        ts: r.ts,
        time: formatTimeBst(r.ts),
        powerW: r.power_w ?? 0,
        voltageV: r.voltage_v ?? 0,
        currentA: r.current_a ?? 0,
        pf: r.power_factor ?? 1.0,
      }));
  }, [history]);

  return (
    <div className="page history-page">
      {/* 1. Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              PHYSICAL HARDWARE TELEMETRY STREAM
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
              Telemetry & Packet History
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Real-time time-series power profiles, electrical waveforms, and packet-level sensor audit logs from the ESP32 hardware.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DataHonestyTag type="MEASURED" size="md" tooltip="Direct hardware measurements from ACS712 & ZMPT101B" />
          </div>
        </div>
      </div>

      {/* 2. Observed Power Draw History Chart */}
      <div className="history-chart-card glass" style={{ marginBottom: '24px' }}>
        <div className="sect-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">Recent Active Power Draw (Aggregate AC Mains)</span>
            <DataHonestyTag type="MEASURED" size="sm" tooltip="Time-series power readings captured by ACS712 & ZMPT101B" />
          </div>
          <span className="sect-sublabel">Last {chartPoints.length} packets</span>
        </div>

        {loading ? (
          <div className="chart-loading-box">
            <div className="spinner" />
            <span>Loading telemetry history…</span>
          </div>
        ) : chartPoints.length < 2 ? (
          <div className="chart-empty-box">
            <span>Awaiting telemetry history stream…</span>
          </div>
        ) : (
          <div className="history-bars-visualizer">
            {chartPoints.map((pt, idx) => {
              const maxP = Math.max(...chartPoints.map((p) => p.powerW), 100);
              const heightPct = Math.min(100, Math.max(4, (pt.powerW / maxP) * 100));

              return (
                <div key={idx} className="hist-col" title={`${pt.time} BST: ${pt.powerW.toFixed(1)} W (${pt.voltageV.toFixed(1)} V, ${pt.currentA.toFixed(2)} A)`}>
                  <div className="hist-bar-fill" style={{ height: `${heightPct}%` }} />
                  {idx % 5 === 0 && <span className="hist-label">{pt.time}</span>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3. Telemetry Packets Log Table */}
      <div className="telemetry-table-card glass" style={{ marginBottom: '24px' }}>
        <div className="sect-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">Raw Telemetry Packets</span>
            <DataHonestyTag type="MEASURED" size="sm" />
          </div>
          <span className="sect-sublabel">ESP32 hardware packets (last 25 shown)</span>
        </div>

        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Packet Timestamp (BST)</th>
                <th>Active Power</th>
                <th>Mains Voltage</th>
                <th>Current</th>
                <th>Power Factor</th>
                <th>DHT22 Ambient</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 25).map((pkt) => (
                <tr key={pkt.id || pkt.ts}>
                  <td className="mono text-muted">{formatDateTimeBst(pkt.ts)} BST</td>
                  <td><strong className="mono">{pkt.power_w != null ? `${pkt.power_w.toFixed(1)} W` : '—'}</strong></td>
                  <td className="mono">{formatVoltage(pkt.voltage_v)}</td>
                  <td className="mono">{formatCurrent(pkt.current_a)}</td>
                  <td className="mono">{pkt.power_factor != null ? pkt.power_factor.toFixed(2) : '—'}</td>
                  <td>
                    {pkt.temperature_c != null && pkt.humidity_pct != null
                      ? `${pkt.temperature_c.toFixed(1)}°C · ${Math.round(pkt.humidity_pct)}%`
                      : 'Unavailable'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
