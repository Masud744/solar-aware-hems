import type { FreshnessStatus } from '../types';

/** Format watts for display: "59 W", "1.2 kW" */
export function formatPower(watts: number | null | undefined): { value: string; unit: string } {
  if (watts == null) return { value: '—', unit: '' };
  if (Math.abs(watts) >= 1000) {
    return { value: (watts / 1000).toFixed(2), unit: 'kW' };
  }
  return { value: Math.round(watts).toString(), unit: 'W' };
}

/** Format a number with appropriate decimal places */
export function formatNum(v: number | null | undefined, decimals = 1): string {
  if (v == null) return '—';
  return v.toFixed(decimals);
}

/** Format voltage: "220.5 V" */
export function formatVoltage(v: number | null | undefined): string {
  if (v == null) return '—';
  return `${v.toFixed(1)} V`;
}

/** Format current: "4.2 A" */
export function formatCurrent(a: number | null | undefined): string {
  if (a == null) return '—';
  return `${a.toFixed(2)} A`;
}

/** Format temperature: "31.5°C" */
export function formatTemp(c: number | null | undefined): string {
  if (c == null) return '—';
  return `${c.toFixed(1)}°C`;
}

/** Format humidity: "78%" */
export function formatHumidity(pct: number | null | undefined): string {
  if (pct == null) return '—';
  return `${Math.round(pct)}%`;
}

/** Format energy: "1.23 kWh" */
export function formatEnergy(kwh: number | null | undefined): string {
  if (kwh == null) return '—';
  return `${kwh.toFixed(2)} kWh`;
}

/** Determine telemetry freshness from timestamp */
export function getFreshness(ts: string | null | undefined): {
  status: FreshnessStatus;
  label: string;
  seconds: number;
} {
  if (!ts) return { status: 'unavailable', label: 'No data received', seconds: Infinity };

  const diff = (Date.now() - new Date(ts).getTime()) / 1000;

  if (diff < 0 || isNaN(diff)) {
    return { status: 'unavailable', label: 'Invalid timestamp', seconds: Infinity };
  }
  if (diff < 15) {
    return { status: 'live', label: 'Live', seconds: diff };
  }
  if (diff < 60) {
    return { status: 'live', label: `${Math.round(diff)}s ago`, seconds: diff };
  }
  if (diff < 300) {
    return { status: 'stale', label: `${Math.round(diff / 60)}m ago`, seconds: diff };
  }
  if (diff < 3600) {
    return { status: 'offline', label: `${Math.round(diff / 60)}m ago`, seconds: diff };
  }
  return { status: 'offline', label: 'Offline', seconds: diff };
}

/** Describe cloud cover in human terms */
export function describeCloudCover(pct: number): string {
  if (pct <= 10) return 'Clear sky';
  if (pct <= 25) return 'Mostly clear';
  if (pct <= 50) return 'Partly cloudy';
  if (pct <= 75) return 'Mostly cloudy';
  if (pct <= 90) return 'Overcast';
  return 'Heavy cloud cover';
}

/** Source label for display */
export function sourceLabel(source: string): string {
  switch (source) {
    case 'solar': return 'Solar-routed';
    case 'grid': return 'Grid-powered';
    case 'off': return 'Off';
    default: return source;
  }
}

/** Format time string in BST */
export function formatTimeBst(iso?: string | Date | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Format date and time string in BST */
export function formatDateTimeBst(iso?: string | Date | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Numerical Trapezoidal Integration over the Available Telemetry History Window
 */
export function calculateWindowEnergy(history: any[]): {
  kwh: number | null;
  durationMins: number;
  tStart: Date | null;
  tEnd: Date | null;
  isFullDay: boolean;
} {
  if (!history || history.length < 2) {
    return { kwh: null, durationMins: 0, tStart: null, tEnd: null, isFullDay: false };
  }

  const valid = history
    .filter((r) => r.ts && typeof r.power_w === 'number' && Number.isFinite(r.power_w))
    .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

  if (valid.length < 2) {
    return { kwh: null, durationMins: 0, tStart: null, tEnd: null, isFullDay: false };
  }

  const tStart = new Date(valid[0].ts);
  const tEnd = new Date(valid[valid.length - 1].ts);
  const durationSeconds = Math.max(0, (tEnd.getTime() - tStart.getTime()) / 1000);
  const durationMins = durationSeconds / 60;

  let integratedKwh = 0;
  for (let i = 1; i < valid.length; i++) {
    const tPrev = new Date(valid[i - 1].ts).getTime();
    const tCurr = new Date(valid[i].ts).getTime();
    const dtSeconds = Math.max(0, (tCurr - tPrev) / 1000);

    // Only integrate continuous segments (cap gaps to 60s)
    if (dtSeconds > 0 && dtSeconds <= 60) {
      const pPrev = valid[i - 1].power_w ?? 0;
      const pCurr = valid[i].power_w ?? 0;
      integratedKwh += (((pPrev + pCurr) / 2.0) * dtSeconds) / (3600 * 1000);
    }
  }

  const isFullDay = durationMins >= 23.5 * 60;

  return {
    kwh: integratedKwh,
    durationMins,
    tStart,
    tEnd,
    isFullDay,
  };
}

/** Count active loads from device status */
export function countActiveLoads(status: Record<string, string> | null): {
  total: number;
  grid: number;
  solar: number;
  off: number;
} {
  if (!status) return { total: 4, grid: 0, solar: 0, off: 4 };
  let grid = 0, solar = 0, off = 0;
  for (const key of ['load_1', 'load_2', 'load_3', 'load_4']) {
    const v = (status as Record<string, string>)[key] || 'off';
    if (v === 'grid') grid++;
    else if (v === 'solar') solar++;
    else off++;
  }
  return { total: 4, grid, solar, off: off };
}
