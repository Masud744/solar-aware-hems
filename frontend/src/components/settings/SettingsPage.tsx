import React, { useState, useEffect } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { LOCATION, API_BASE } from '../../utils/constants';
import { fetchRiskMargin } from '../../api/client';
import type { ThemeMode, RiskMargin } from '../../types';

interface SettingsPageProps {
  theme: ThemeMode;
  onThemeChange: (mode: ThemeMode) => void;
  backendOnline: boolean;
}

export function SettingsPage({ theme, onThemeChange, backendOnline }: SettingsPageProps) {
  const [riskInfo, setRiskInfo] = useState<RiskMargin | null>(null);
  const [riskError, setRiskError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchRiskMargin()
      .then((data) => { if (!cancelled) setRiskInfo(data); })
      .catch(() => { if (!cancelled) setRiskError(true); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="page settings-page">
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
          SYSTEM HEALTH & CONFIGURATION
        </div>
        <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
          Settings & Diagnostics
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
          Appearance preferences, baseline tariff rate, and model risk configuration.
        </p>
      </div>

      {/* 1. Appearance */}
      <div className="settings-section glass" style={{ marginBottom: '20px' }}>
        <span className="sect-label">Appearance</span>
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-name">Theme Mode</span>
            <span className="settings-desc">Choose light, dark, or sync with operating system</span>
          </div>
          <div className="theme-seg" role="radiogroup" aria-label="Theme">
            {(['light', 'dark', 'system'] as ThemeMode[]).map((m) => (
              <button
                key={m}
                className="theme-opt"
                data-active={theme === m}
                onClick={() => onThemeChange(m)}
                role="radio"
                aria-checked={theme === m}
              >
                {m === 'light' ? '☀ Light' : m === 'dark' ? '🌙 Dark' : '⚙ System'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Location & Solar Coordinates */}
      <div className="settings-section glass" style={{ marginBottom: '20px' }}>
        <span className="sect-label">Deployment Location</span>
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-name">{LOCATION.name}</span>
            <span className="settings-desc">{LOCATION.lat}°N, {LOCATION.lng}°E · {LOCATION.timezone} (BST)</span>
          </div>
          <span className="badge-configured">Active Station</span>
        </div>
        <p className="settings-desc" style={{ marginTop: '8px' }}>
          Open-Meteo weather forecasts and astronomical solar irradiance curves are modeled for this latitude and longitude.
        </p>
      </div>

      {/* 3. Baseline Tariff Rate */}
      <div className="settings-section glass" style={{ marginBottom: '20px' }}>
        <div className="sect-head" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">Baseline Electricity Tariff</span>
            <DataHonestyTag type="ESTIMATED" size="sm" />
          </div>
        </div>
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-name">Bangladesh Residential Baseline Tariff</span>
            <span className="settings-desc">
              Rate used to evaluate tariff-equivalent cost of observed energy consumption.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <strong className="mono" style={{ fontSize: '1.2rem', color: 'var(--solar-text)' }}>৳ 7.50</strong>
            <span className="text-3">/ kWh</span>
          </div>
        </div>
        <p className="settings-desc" style={{ marginTop: '8px' }}>
          Note: In accordance with scientific data provenance rules, relay switching is not claimed as direct monetary savings because branch solar generation is unmetered in this prototype.
        </p>
      </div>

      {/* 4. Backend & Model Risk Parameters */}
      <div className="settings-section glass" style={{ marginBottom: '20px' }}>
        <span className="sect-label">System Backend & Decision Engine</span>
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-name">FastAPI Backend Service</span>
            <span className="settings-desc">{API_BASE}</span>
          </div>
          <div className="fresh" data-s={backendOnline ? 'live' : 'offline'}>
            <span className="fresh-dot" />
            <span>{backendOnline ? 'Connected' : 'Unreachable'}</span>
          </div>
        </div>

        {riskInfo && (
          <>
            <div className="settings-row">
              <div className="settings-info">
                <span className="settings-name">Safety Multiplier (k)</span>
                <span className="settings-desc">{riskInfo.k_selection_rationale}</span>
              </div>
              <span className="mono" style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--teal-text)' }}>
                k = {riskInfo.k}
              </span>
            </div>
            <div className="settings-row">
              <div className="settings-info">
                <span className="settings-name">Uncertainty Modeling Method</span>
                <span className="settings-desc">{riskInfo.calibration_disclosure}</span>
              </div>
              <span className="badge-configured">{riskInfo.sigma_method}</span>
            </div>
          </>
        )}
        {riskError && <p className="settings-desc" style={{ fontStyle: 'italic', color: 'var(--amber-warn)' }}>Could not fetch risk parameters from backend.</p>}
      </div>
    </div>
  );
}
