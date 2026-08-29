import React, { useState } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { ApplianceCard, ApplianceMeta } from './ApplianceCard';
import { ApplianceSafetyChecker } from './ApplianceSafetyChecker';
import { ScheduleRecommendations } from './ScheduleRecommendations';
import type { DeviceStatus, SensorReading, LoadSource, LoadTransitionState } from '../../types';

export const APPLIANCES_LIST: ApplianceMeta[] = [
  {
    key: 'load_1',
    name: 'Washing Machine',
    powerKw: 1.20,
    powerDisplay: '1.20 kW',
    durationHours: 0.75,
    durationDisplay: '45 mins',
    shiftable: true,
    icon: '🧺',
    typicalUse: 'Shiftable laundry wash cycle',
  },
  {
    key: 'load_2',
    name: 'Water Pump',
    powerKw: 0.75,
    powerDisplay: '0.75 kW',
    durationHours: 0.50,
    durationDisplay: '30 mins',
    shiftable: true,
    icon: '💧',
    typicalUse: 'Shiftable rooftop tank pumping',
  },
  {
    key: 'load_3',
    name: 'Refrigerator',
    powerKw: 0.15,
    powerDisplay: '0.15 kW',
    durationHours: 24.0,
    durationDisplay: 'Continuous',
    shiftable: false,
    icon: '❄️',
    typicalUse: 'Continuous baseload (24/7 food preservation)',
  },
  {
    key: 'load_4',
    name: 'Rice Cooker',
    powerKw: 0.70,
    powerDisplay: '0.70 kW',
    durationHours: 0.67,
    durationDisplay: '40 mins',
    shiftable: true,
    icon: '🍚',
    typicalUse: 'Shiftable meal preparation cycle',
  },
];

interface Props {
  deviceStatus: DeviceStatus | null;
  reading: SensorReading | null;
  loadStates: Record<string, { transition: LoadTransitionState; targetSource: LoadSource | null }>;
  onSetSource: (loadKey: string, source: LoadSource) => void;
  onEmergencyOff: () => void;
  loading: boolean;
}

export function AppliancesPage({
  deviceStatus,
  reading,
  loadStates,
  onSetSource,
  onEmergencyOff,
  loading,
}: Props) {
  const [selectedForCheck, setSelectedForCheck] = useState<ApplianceMeta | null>(null);
  const [confirmingEmergency, setConfirmingEmergency] = useState(false);

  // Authoritative routing state extraction
  const relayMap = reading?.relay_commanded_state || {};
  const channelSources = APPLIANCES_LIST.map((app) => {
    const r = (relayMap as any)[app.key];
    const applied = (typeof r === 'object' && r !== null ? r.applied_source : r) || (deviceStatus as any)?.[app.key] || 'off';
    return String(applied).toLowerCase();
  });

  const solarCount = channelSources.filter((s) => s === 'solar').length;
  const gridCount = channelSources.filter((s) => s === 'grid').length;
  const activeCount = solarCount + gridCount;

  const shiftableOnly = APPLIANCES_LIST.filter((app) => app.shiftable);

  const handleEmergencyClick = () => {
    if (confirmingEmergency) {
      onEmergencyOff();
      setConfirmingEmergency(false);
    } else {
      setConfirmingEmergency(true);
      setTimeout(() => setConfirmingEmergency(false), 5000);
    }
  };

  const handleSelectApplianceForCheck = (app: ApplianceMeta) => {
    setSelectedForCheck(app);
    // Smooth scroll to safety checker
    const el = document.getElementById('safety-checker-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  if (loading) {
    return (
      <div className="page">
        <h1 className="t-display">Appliance Management</h1>
        <div className="loads-grid">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="load-tile glass">
              <div className="skel" style={{ width: 120, height: 18 }} />
              <div className="skel" style={{ width: '100%', height: 44, marginTop: 16 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page appliances-page">
      {/* 1. Page Header & Active Circuits Bar */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              HARDWARE LOAD CONTROL & UNCERTAINTY-AWARE SCHEDULING
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
              Appliance Management
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Authoritative relay control, pre-run surplus verification, and duration-aware solar scheduling.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="active-circuits-pill glass">
              <span className="pill-dot" />
              <strong>{activeCount} of 4</strong> circuits active
              <span className="pill-divider">•</span>
              <span className="text-solar font-bold">{solarCount} solar-routed</span>
              <span className="pill-divider">•</span>
              <span className="text-blue font-bold">{gridCount} grid-powered</span>
            </div>

            <button
              className={`btn-emergency-interlock ${confirmingEmergency ? 'confirming' : ''}`}
              onClick={handleEmergencyClick}
              title="Disengage all 4 appliance relay coils"
            >
              {confirmingEmergency ? '⚠ Confirm Emergency All Off' : '⏻ All Off'}
            </button>
          </div>
        </div>
      </div>

      {/* 2. Interactive Pre-Run Safety Checker */}
      <div id="safety-checker-section" style={{ marginBottom: '28px' }}>
        <ApplianceSafetyChecker
          selectedAppliance={selectedForCheck}
          appliances={APPLIANCES_LIST}
          onApplianceChange={(app) => setSelectedForCheck(app)}
        />
      </div>

      {/* 3. Controlled Appliances Hardware Matrix */}
      <div style={{ marginBottom: '28px' }}>
        <div className="sect-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">Controlled Appliances</span>
            <DataHonestyTag type="MEASURED" size="sm" tooltip="Hardware-confirmed relay states via applied_source" />
          </div>
          <span className="sect-sublabel">Dual-bank relay routing matrix</span>
        </div>

        <div className="appliances-card-grid">
          {APPLIANCES_LIST.map((app) => {
            const ls = loadStates[app.key] || { transition: 'idle', targetSource: null };
            return (
              <ApplianceCard
                key={app.key}
                appliance={app}
                deviceStatus={deviceStatus}
                reading={reading}
                transitionState={ls.transition}
                targetSource={ls.targetSource}
                onSetSource={onSetSource}
                onSelectForCheck={handleSelectApplianceForCheck}
              />
            );
          })}
        </div>
      </div>

      {/* 4. Automated 24-Hour Optimal Solar Schedule */}
      <div style={{ marginBottom: '28px' }}>
        <ScheduleRecommendations
          shiftableAppliances={shiftableOnly}
          tariffRate={7.5}
        />
      </div>
    </div>
  );
}
