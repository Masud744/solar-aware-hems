import React from 'react';
import type { DataHonestyTagType } from '../../types';

interface Props {
  type: DataHonestyTagType;
  tooltip?: string;
  className?: string;
  size?: 'sm' | 'md';
}

const DEFAULT_TOOLTIPS: Record<DataHonestyTagType, string> = {
  MEASURED: 'Direct physical telemetry reading from ESP32 hardware sensors (ZMPT101B / ACS712-20A).',
  CALCULATED: 'Deterministic mathematical derivation from measured or confirmed hardware states.',
  FORECAST: 'Future prediction from Open-Meteo weather inputs and trained Random Forest ML models.',
  ESTIMATED: 'Cost estimate based on Bangladesh baseline residential tariff rate (৳7.50/kWh).',
  'USER ESTIMATED': 'User-reported solar contribution estimate. No dedicated physical solar energy sensor is installed.',
};

export const DataHonestyTag: React.FC<Props> = ({
  type,
  tooltip,
  className = '',
  size = 'sm',
}) => {
  const tip = tooltip || DEFAULT_TOOLTIPS[type];
  const tagClass = type.toLowerCase().replace(/\s+/g, '-');

  return (
    <span
      className={`data-honesty-tag tag-${tagClass} tag-size-${size} ${className}`}
      title={tip}
      role="note"
      aria-label={`Data provenance: ${type}. ${tip}`}
    >
      <span className="tag-dot" aria-hidden="true" />
      <span className="tag-text">{type}</span>
    </span>
  );
};
