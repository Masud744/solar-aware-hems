import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import type { DeviceStatus, SensorReading, LoadSource, LoadTransitionState } from '../../types';

interface Props {
  deviceStatus: DeviceStatus | null;
  reading: SensorReading | null;
  loadStates: Record<string, { transition: LoadTransitionState; targetSource: LoadSource | null }>;
  onSetSource: (loadKey: string, source: LoadSource) => Promise<void>;
  onEmergencyOff: () => Promise<void>;
  onNavigateAppliances: () => void;
  loading: boolean;
}

const APPLIANCE_METADATA: Record<string, { name: string; channel: string; icon: string }> = {
  load_1: { name: 'Load 1', channel: 'Relay CH 1', icon: '🔌' },
  load_2: { name: 'Load 2', channel: 'Relay CH 2', icon: '🔌' },
  load_3: { name: 'Load 3', channel: 'Relay CH 3', icon: '🔌' },
  load_4: { name: 'Load 4', channel: 'Relay CH 4', icon: '🔌' },
};

export const ApplianceControlsPreview: React.FC<Props> = ({
  deviceStatus,
  reading,
  loadStates,
  onSetSource,
  onEmergencyOff,
  onNavigateAppliances,
  loading,
}) => {
  const relayMap = reading?.relay_commanded_state || {};

  const getAuthoritativeSource = (key: string): LoadSource => {
    const r = (relayMap as any)[key];
    const applied = (typeof r === 'object' && r !== null ? r.applied_source : r) || (deviceStatus as any)?.[key] || 'off';
    const s = String(applied).toLowerCase();
    if (s === 'solar' || s === 'grid' || s === 'off') return s as LoadSource;
    return 'off';
  };

  return (
    <div className="appliance-preview-card glass">
      <div className="sect-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Appliance Controls</span>
          <DataHonestyTag type="MEASURED" size="sm" tooltip="Hardware-confirmed relay state from applied_source" />
        </div>
        <button className="btn-link" onClick={onNavigateAppliances}>
          Manage devices →
        </button>
      </div>

      <div className="appliance-compact-grid">
        {(['load_1', 'load_2', 'load_3', 'load_4'] as const).map((key) => {
          const meta = APPLIANCE_METADATA[key];
          const currentSource = getAuthoritativeSource(key);
          const isTransitioning = loadStates[key]?.transition === 'switching' || loadStates[key]?.transition === 'sending';

          return (
            <div key={key} className={`appliance-compact-card glass ${currentSource}`}>
              <div className="appliance-compact-top">
                <span className="appliance-icon">{meta.icon}</span>
                <div className="appliance-compact-info">
                  <strong>{meta.name}</strong>
                  <span>{meta.channel} • {isTransitioning ? 'Switching...' : currentSource.toUpperCase()}</span>
                </div>
                <span className={`source-status-badge source-${currentSource}`} />
              </div>

              <div className="appliance-compact-actions">
                <button
                  className={`btn-source btn-solar ${currentSource === 'solar' ? 'active' : ''}`}
                  disabled={loading || isTransitioning}
                  onClick={() => onSetSource(key, 'solar')}
                  title="Route to Represented Solar bank"
                >
                  Solar
                </button>
                <button
                  className={`btn-source btn-grid ${currentSource === 'grid' ? 'active' : ''}`}
                  disabled={loading || isTransitioning}
                  onClick={() => onSetSource(key, 'grid')}
                  title="Route to AC Grid bank"
                >
                  Grid
                </button>
                <button
                  className={`btn-source btn-off ${currentSource === 'off' ? 'active' : ''}`}
                  disabled={loading || isTransitioning}
                  onClick={() => onSetSource(key, 'off')}
                  title="Disconnect appliance"
                >
                  Off
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <button className="btn-all-off" onClick={onEmergencyOff} disabled={loading}>
        <span>⛔</span> Turn All Appliances Off (Emergency Interlock)
      </button>
    </div>
  );
};
