/** Sunrise/sunset calculation for Kaliakair, BD (24.07°N, 90.22°E).
 *
 * Uses the NOAA solar position algorithm (simplified).
 * These are CALCULATED values — not measured or backend-provided.
 */

const LAT = 24.07;
const LNG = 90.22;
const DEG = Math.PI / 180;

function julianDay(date: Date): number {
  const y = date.getUTCFullYear();
  const m = date.getUTCMonth() + 1;
  const d = date.getUTCDate();
  const a = Math.floor((14 - m) / 12);
  const y1 = y + 4800 - a;
  const m1 = m + 12 * a - 3;
  return d + Math.floor((153 * m1 + 2) / 5) + 365 * y1 +
    Math.floor(y1 / 4) - Math.floor(y1 / 100) + Math.floor(y1 / 400) - 32045;
}

function solarDeclination(jd: number): number {
  const n = jd - 2451545.0;
  const L = (280.46 + 0.9856474 * n) % 360;
  const g = ((357.528 + 0.9856003 * n) % 360) * DEG;
  const lambda = (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * DEG;
  const epsilon = 23.439 * DEG;
  return Math.asin(Math.sin(epsilon) * Math.sin(lambda));
}

function hourAngle(lat: number, decl: number, elevation: number = -0.833): number {
  const latRad = lat * DEG;
  const ha = Math.acos(
    (Math.sin(elevation * DEG) - Math.sin(latRad) * Math.sin(decl)) /
    (Math.cos(latRad) * Math.cos(decl))
  );
  return ha / DEG;
}

export interface DaylightInfo {
  sunrise: string;   // "HH:MM" in local time
  sunset: string;    // "HH:MM" in local time
  daylightHours: number;
  /** 0–1 progress through daylight (0 = sunrise, 1 = sunset, null if outside daylight) */
  progress: number | null;
}

/** Calculate sunrise/sunset for Kaliakair, BD on the given date. */
export function getDaylightInfo(date: Date = new Date()): DaylightInfo {
  const jd = julianDay(date);
  const decl = solarDeclination(jd);
  const ha = hourAngle(LAT, decl);

  // UTC noon in fractional hours
  const n = jd - 2451545.0;
  const L = (280.46 + 0.9856474 * n) % 360;
  const g = ((357.528 + 0.9856003 * n) % 360) * DEG;
  const eqTime = -1.915 * Math.sin(g) - 0.020 * Math.sin(2 * g) +
    2.466 * Math.sin(2 * (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * DEG) -
    0.053 * Math.sin(4 * (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * DEG);

  // Solar noon in UTC hours
  const solarNoonUTC = 12 - LNG / 15 - eqTime / 60;

  // Bangladesh is UTC+6
  const tzOffset = 6;
  const sunriseHour = solarNoonUTC - ha / 15 + tzOffset;
  const sunsetHour = solarNoonUTC + ha / 15 + tzOffset;
  const daylightHours = 2 * ha / 15;

  // Current time progress
  const now = new Date();
  const currentHour = now.getHours() + now.getMinutes() / 60;
  let progress: number | null = null;
  if (currentHour >= sunriseHour && currentHour <= sunsetHour) {
    progress = (currentHour - sunriseHour) / (sunsetHour - sunriseHour);
  }

  return {
    sunrise: formatHour(sunriseHour),
    sunset: formatHour(sunsetHour),
    daylightHours: Math.round(daylightHours * 10) / 10,
    progress,
  };
}

function formatHour(h: number): string {
  const hour = Math.floor(h);
  const min = Math.round((h - hour) * 60);
  const h12 = hour % 12 || 12;
  const ampm = hour < 12 ? 'AM' : 'PM';
  return `${h12}:${min.toString().padStart(2, '0')} ${ampm}`;
}
