import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import type { DeviceStatus, SensorReading, LoadSource, LoadTransitionState } from '../../types';

export interface ApplianceMeta {
  key: string;
  name: string;
  powerKw: number;
  powerDisplay: string;
  durationHours: number;
  durationDisplay: string;
  shiftable: boolean;
  icon: string;
  typicalUse: string;
}

interface Props {
  appliance: ApplianceMeta;
  deviceStatus: DeviceStatus | null;
  reading: SensorReading | null;
  transitionState?: LoadTransitionState;
  targetSource?: LoadSource | null;
  onSetSource: (loadKey: string, source: LoadSource) => void;
  onSelectForCheck?: (appliance: ApplianceMeta) => void;
  disabled?: boolean;
}

const SOURCES: LoadSource[] = ['solar', 'grid', 'off'];

export const ApplianceCard: React.FC<Props> = ({
  appliance,
  deviceStatus,
  reading,
  transitionState = 'idle',
  targetSource = null,
  onSetSource,
  onSelectForCheck,
  disabled = false,
}) => {
  // Authoritative relay state from ESP32 telemetry feedback
  const relayMap = reading?.relay_commanded_state || {};
  const r = (relayMap as any)[appliance.key];
  const applied = (typeof r === 'object' && r !== null ? r.applied_source : r) || (deviceStatus as any)?.[appliance.key] || 'off';
  const currentSource: LoadSource = ['solar', 'grid', 'off'].includes(String(applied).toLowerCase())
    ? (String(applied).toLowerCase() as LoadSource)
    : 'off';

  const isTransitioning = transitionState !== 'idle';

  return (
    <div className={`appliance-control-card glass source-border-${currentSource}`}>
      <div className="card-top-row">
        <div className="appliance-ident">
          <span className="appliance-icon-lg">{appliance.icon}</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <h3 className="appliance-name">{appliance.name}</h3>
              <span className={`shiftable-badge ${appliance.shiftable ? 'shiftable' : 'continuous'}`}>
                {appliance.shiftable ? 'Shiftable' : 'Non-shiftable · 24/7'}
              </span>
            </div>
            <span className="appliance-sub-desc">{appliance.typicalUse}</span>
          </div>
        </div>

        <div className="appliance-source-state">
          <span className={`source-dot source-${currentSource}`} />
          <span className="source-label-text">{currentSource.toUpperCase()}</span>
          <DataHonestyTag type="MEASURED" size="sm" tooltip="Hardware-confirmed relay state from applied_source" />
        </div>
      </div>

      <div className="appliance-specs-row">
        <div className="spec-block">
          <span className="spec-lbl">Rated Power</span>
          <strong className="spec-val">{appliance.powerDisplay}</strong>
        </div>
        <div className="spec-block">
          <span className="spec-lbl">Cycle Time</span>
          <strong className="spec-val">{appliance.durationDisplay}</strong>
        </div>
        <div className="spec-block">
          <span className="spec-lbl">Est. Cycle Energy</span>
          <strong className="spec-val">
            {(appliance.powerKw * appliance.durationHours).toFixed(2)} kWh
          </strong>
        </div>
      </div>

      {/* Transition State Banner */}
      {isTransitioning && (
        <div className={`transition-banner status-${transitionState}`}>
          {transitionState === 'sending' && (
            <><span className="spinner" /> Sending command to controller…</>
          )}
          {transitionState === 'switching' && (
            <><span className="spinner" /> Energizing relay coil ({targetSource?.toUpperCase()})…</>
          )}
          {transitionState === 'confirmed' && (
            <>✓ Confirmed by ESP32 telemetry</>
          )}
          {transitionState === 'error' && (
            <>⚠ Command unconfirmed — check hardware selector</>
          )}
        </div>
      )}

      {/* Tactile Source Selection Controls */}
      <div className="appliance-btn-group">
        {SOURCES.map((source) => {
          const isActive = currentSource === source && !isTransitioning;
          return (
            <button
              key={source}
              className={`btn-ctrl-source btn-${source} ${isActive ? 'active' : ''}`}
              disabled={disabled || isTransitioning || currentSource === source}
              onClick={() => onSetSource(appliance.key, source)}
              aria-pressed={isActive}
              aria-label={`Route ${appliance.name} to ${source}`}
            >
              <span className="btn-dot" />
              <span className="btn-text">
                {source === 'solar' ? 'Solar Bank' : source === 'grid' ? 'AC Grid' : 'Turn Off'}
              </span>
            </button>
          );
        })}
      </div>

      {/* Shiftable Quick Action */}
      {appliance.shiftable && onSelectForCheck && (
        <button
          className="btn-quick-check"
          onClick={() => onSelectForCheck(appliance)}
          disabled={disabled}
        >
          <span>⚡</span> Check run safety at current surplus →
        </button>
      )}
    </div>
  );
};
