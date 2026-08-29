import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { EnergyTracker } from './EnergyTracker';

interface Props {
  tariffRate?: number; // 7.50 BDT / kWh baseline
}

export const EnergyPage: React.FC<Props> = ({ tariffRate = 7.50 }) => {
  return (
    <div className="page energy-page">
      {/* ── Page Header ────────────────────────────────────────── */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              DATABASE-BACKED ENERGY & COST TRACKER
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
              Energy & Cost Accounting
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Persistent timestamp-integrated household energy, user-reported solar contributions, and tariff savings tracking.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DataHonestyTag type="CALCULATED" size="md" tooltip="Derived from persistent Supabase telemetry packets" />
          </div>
        </div>
      </div>

      {/* ── Main Persistent Energy Tracker ──────────────────────── */}
      <EnergyTracker tariffRate={tariffRate} showHistoryTable={true} />
    </div>
  );
};
