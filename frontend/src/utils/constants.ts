/** Load names — UI-level labels for load_1 through load_4.
 *  The firmware/backend only knows "load_1"–"load_4".
 *  These labels are purely cosmetic and can be customized. */
export const LOAD_NAMES: Record<string, string> = {
  load_1: 'Load 1',
  load_2: 'Load 2',
  load_3: 'Load 3',
  load_4: 'Load 4',
};

/** Load icons — emoji placeholders */
export const LOAD_ICONS: Record<string, string> = {
  load_1: '💡',
  load_2: '💡',
  load_3: '💡',
  load_4: '💡',
};

/** Polling intervals (ms) */
export const TELEMETRY_POLL_MS = 4000;
export const DEVICE_STATUS_POLL_MS = 3000;

/** Freshness thresholds (seconds) */
export const STALE_THRESHOLD_S = 30;
export const OFFLINE_THRESHOLD_S = 120;

/** Location — Kaliakair, Bangladesh */
export const LOCATION = {
  name: 'Kaliakair, Bangladesh',
  lat: 24.07,
  lng: 90.22,
  timezone: 'Asia/Dhaka',
};

/** API base URL */
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
