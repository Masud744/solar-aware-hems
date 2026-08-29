import React from 'react';
import { EnergyTracker } from '../energy/EnergyTracker';
import type { SensorReading, DeviceStatus } from '../../types';

interface Props {
  reading: SensorReading | null;
  history: SensorReading[];
  deviceStatus: DeviceStatus | null;
  tariffRate?: number; // 7.50 BDT / kWh baseline
}

export const EnergyAccountingStrip: React.FC<Props> = ({
  tariffRate = 7.5,
}) => {
  return (
    <div className="energy-accounting-section">
      <EnergyTracker tariffRate={tariffRate} showHistoryTable={false} />
    </div>
  );
};
