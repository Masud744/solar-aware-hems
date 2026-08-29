import React, { useState, useEffect } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { fetchSolarPrediction } from '../../api/client';
import { getDaylightInfo } from '../../utils/sunrise';
import { describeCloudCover, formatTemp, formatHumidity } from '../../utils/formatting';
import { LOCATION } from '../../utils/constants';
import type { SolarPrediction } from '../../types';

interface Props {
  weather?: SolarPrediction | null;
  loading?: boolean;
  error?: string | null;
}

export function WeatherContext({
  weather: propWeather,
  loading: propLoading,
  error: propError,
}: Props = {}) {
  const [internalWeather, setInternalWeather] = useState<SolarPrediction | null>(null);
  const [internalLoading, setInternalLoading] = useState(false);
  const [internalError, setInternalError] = useState<string | null>(null);
  const daylight = getDaylightInfo();

  const isControlled = propWeather !== undefined || propLoading !== undefined || propError !== undefined;

  useEffect(() => {
    if (isControlled) return;

    let cancelled = false;
    const fetchWeather = async () => {
      setInternalLoading(true);
      try {
        const now = new Date();
        now.setMinutes(0, 0, 0);
        now.setHours(now.getHours() + 1);
        const pad = (n: number) => String(n).padStart(2, '0');
        const iso = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:00:00`;
        const res = await fetchSolarPrediction(iso);
        if (!cancelled) { setInternalWeather(res); setInternalLoading(false); setInternalError(null); }
      } catch {
        if (!cancelled) { setInternalLoading(false); setInternalError('Weather service unavailable'); }
      }
    };
    fetchWeather();
    const interval = setInterval(fetchWeather, 15 * 60 * 1000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [isControlled]);

  const weather = isControlled ? propWeather : internalWeather;
  const loading = isControlled ? (propLoading ?? false) : internalLoading;
  const error = isControlled ? propError : internalError;

  if (loading) {
    return (
      <div className="wx-card glass">
        <div className="sect-head" style={{ marginBottom: 0 }}>
          <span className="sect-label">Outdoor Weather & Daylight</span>
          <DataHonestyTag type="FORECAST" size="sm" />
        </div>
        <div className="wx-conditions">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="wx-item">
              <div className="skel" style={{ width: 50, height: 20 }} />
              <div className="skel" style={{ width: 70, height: 10, marginTop: 4 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="wx-card glass">
      <div className="sect-head" style={{ marginBottom: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Outdoor Weather (Open-Meteo)</span>
          <DataHonestyTag type="FORECAST" size="sm" tooltip="External forecast weather for Kaliakair, BD (distinct from indoor DHT22 sensor)" />
        </div>
        <span className="sect-sublabel">{LOCATION.name}</span>
      </div>

      {error ? (
        <div className="banner" data-v="warning" style={{ marginTop: '10px' }}>
          <span>☁</span>
          <span>{error}</span>
        </div>
      ) : (
        <>
          <div className="wx-conditions">
            {weather && (
              <>
                <div className="wx-item">
                  <span className="wx-val">{Math.round(weather.cloud_cover)}%</span>
                  <span className="wx-lbl">Cloud Cover</span>
                </div>
                <div className="wx-item">
                  <span className="wx-val">{formatTemp(weather.temperature)}</span>
                  <span className="wx-lbl">Outdoor Temp</span>
                </div>
                <div className="wx-item">
                  <span className="wx-val">{formatHumidity(weather.relative_humidity)}</span>
                  <span className="wx-lbl">Outdoor Humidity</span>
                </div>
                <div className="wx-item">
                  <span className="wx-val">{weather.wind_speed.toFixed(1)}</span>
                  <span className="wx-lbl">Wind km/h</span>
                </div>
              </>
            )}
          </div>

          {weather && (
            <div className="wx-desc">
              {describeCloudCover(weather.cloud_cover)}
              {weather.cloud_cover > 60 ? ' — increased cloud attenuation reduces safe solar buffer' : ' — favorable solar irradiance conditions'}
            </div>
          )}

          <div className="wx-divider" />

          <div>
            <div className="daylight-row">
              <span className="daylight-time">🌅 {daylight.sunrise}</span>
              <span className="daylight-hours">{daylight.daylightHours}h daylight</span>
              <span className="daylight-time">🌇 {daylight.sunset}</span>
            </div>
            <div className="daylight-track">
              <div className="daylight-fill" style={{ width: `${(daylight.progress ?? 0) * 100}%` }} />
            </div>
            <div className="daylight-note">Astronomical daylight progression at {LOCATION.lat}°N, {LOCATION.lng}°E</div>
          </div>
        </>
      )}
    </div>
  );
}
