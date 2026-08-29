import React, { useState, useEffect, useCallback } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { fetchXAI } from '../../api/client';
import type { XAIResponse } from '../../types';

interface Props {}

const FEATURE_FRIENDLY_NAMES: Record<string, { label: string; desc: string; icon: string }> = {
  cloud_cover: { label: 'Cloud Cover Impact', desc: 'Direct sunlight attenuation and atmospheric scattering', icon: '☁' },
  hour: { label: 'Time of Day (Solar Angle)', desc: 'Diurnal solar trajectory and irradiance zenith', icon: '☀️' },
  temperature: { label: 'Ambient Temperature', desc: 'Photovoltaic semiconductor operating thermal factor', icon: '🌡' },
  relative_humidity: { label: 'Atmospheric Humidity', desc: 'Moisture content affecting optical transmission', icon: '💧' },
  wind_speed: { label: 'Wind Velocity', desc: 'Convective panel surface cooling effect', icon: '💨' },
  power_lag_1: { label: 'Preceding Hour Power (t-1)', desc: 'Immediate residential baseload persistence', icon: '⚡' },
  power_lag_24: { label: 'Same Hour Yesterday (t-24)', desc: '24-hour diurnal household routine habit', icon: '📅' },
  power_lag_168: { label: 'Same Hour Last Week (t-168)', desc: 'Weekly lifestyle and schedule synchronization', icon: '🗓' },
  rolling_mean_24h: { label: '24-Hour Rolling Average', desc: 'Daily baseline consumption moving baseline', icon: '📊' },
  T2M: { label: 'Outdoor Forecast Temp (T2M)', desc: 'Thermal comfort and cooling equipment demand', icon: '🌡' },
};

export function InsightsPage({}: Props) {
  const [activeModel, setActiveModel] = useState<'solar' | 'load'>('solar');
  const [xaiData, setXaiData] = useState<XAIResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showShapMath, setShowShapMath] = useState<boolean>(false);

  const loadXAI = useCallback(async (modelType: 'solar' | 'load') => {
    setLoading(true);
    setError(null);

    const now = new Date();
    now.setMinutes(0, 0, 0);
    const pad = (n: number) => String(n).padStart(2, '0');
    const isoString = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:00:00`;

    try {
      const res = await fetchXAI(modelType, isoString);
      setXaiData(res);
    } catch (err: any) {
      setError(err?.message || `XAI explanation for ${modelType} currently unavailable.`);
      setXaiData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadXAI(activeModel);
  }, [activeModel, loadXAI]);

  const sumShap = xaiData
    ? xaiData.feature_contributions.reduce((acc, feat) => acc + feat.shap_value, 0)
    : 0;

  return (
    <div className="page insights-page">
      {/* 1. Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              EXPLAINABLE AI (XAI) & TREEEXPLAINER SHAP ATTRIBUTIONS
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>
              Explainability & Insights
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Deconstructing machine learning model predictions into tangible feature contributions.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DataHonestyTag type="CALCULATED" size="md" tooltip="SHAP values represent additive feature attribution (not physical causality)" />
          </div>
        </div>
      </div>

      {/* 2. Model Selector Tabs */}
      <div className="insights-model-tabs" style={{ marginBottom: '20px' }}>
        <button
          className={`model-tab-btn ${activeModel === 'solar' ? 'active' : ''}`}
          onClick={() => setActiveModel('solar')}
        >
          <span>☀️</span>
          <strong>Solar Generation Model</strong>
          <small>Open-Meteo Weather Features</small>
        </button>
        <button
          className={`model-tab-btn ${activeModel === 'load' ? 'active' : ''}`}
          onClick={() => setActiveModel('load')}
        >
          <span>🏠</span>
          <strong>Household Load Model</strong>
          <small>Autoregressive Consumption Lags</small>
        </button>
      </div>

      {/* 3. Primary Feature Attribution Card */}
      <div className="insights-card glass" style={{ marginBottom: '24px' }}>
        <div className="sect-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="sect-label">Top Driving Factors for {activeModel === 'solar' ? 'Solar Output' : 'Household Demand'}</span>
            <DataHonestyTag type="CALCULATED" size="sm" />
          </div>
          <span className="sect-sublabel">SHAP (SHapley Additive exPlanations)</span>
        </div>

        {loading ? (
          <div className="chart-loading-box">
            <div className="spinner" />
            <span>Computing TreeExplainer SHAP values for {activeModel} model…</span>
          </div>
        ) : error ? (
          <div className="banner" data-v="warning" style={{ margin: '14px 0' }}>
            <span>⚠</span>
            <span>{error}</span>
          </div>
        ) : xaiData ? (
          <div className="insights-content">
            {/* Rule-Based Executive Summary */}
            <div className="executive-summary-box">
              <div className="summary-head">
                <span className="summary-icon">💡</span>
                <strong>Model Prediction Summary: {xaiData.predicted_kw.toFixed(2)} kW</strong>
              </div>
              <p className="summary-text">{xaiData.rule_based_explanation}</p>
            </div>

            {/* Feature Impact Bars */}
            <div className="factors-list">
              <h4 className="factors-title">Key Contributing Features</h4>
              {xaiData.feature_contributions.map((feat) => {
                const meta = FEATURE_FRIENDLY_NAMES[feat.feature_name] || {
                  label: feat.feature_name.replace(/_/g, ' ').toUpperCase(),
                  desc: 'Model feature parameter',
                  icon: '🔹',
                };
                const val = feat.shap_value;
                const isPositive = val >= 0;
                const absVal = Math.abs(val);
                const barWidth = Math.min(100, Math.max(8, absVal * 120));

                return (
                  <div key={feat.feature_name} className="factor-row glass">
                    <div className="factor-left">
                      <span className="factor-icon">{meta.icon}</span>
                      <div>
                        <strong className="factor-name">{meta.label}</strong>
                        <span className="factor-desc">{meta.desc}</span>
                      </div>
                    </div>

                    <div className="factor-middle">
                      <div className="factor-bar-track">
                        <div
                          className={`factor-bar-fill ${isPositive ? 'positive' : 'negative'}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </div>

                    <div className="factor-right">
                      <strong className={`factor-val mono ${isPositive ? 'text-teal' : 'text-blue'}`}>
                        {isPositive ? '+' : ''}{val.toFixed(3)} kW
                      </strong>
                      <span className="factor-direction">
                        {isPositive ? 'Increases output' : 'Decreases output'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Expandable Technical SHAP details */}
            <div className="shap-math-expander">
              <button
                className="btn-toggle-why"
                onClick={() => setShowShapMath((prev) => !prev)}
              >
                <span>{showShapMath ? '▾ Hide Mathematical Foundation' : '▸ Mathematical Foundation (TreeExplainer SHAP)'}</span>
              </button>

              {showShapMath && (
                <div className="tech-details-body">
                  <div className="shap-equation-card glass" style={{ padding: '12px 16px', marginBottom: '12px', borderRadius: 'var(--r-md)' }}>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-3)', fontWeight: 700, marginBottom: '6px' }}>
                      EXACT ADDITIVE FEATURE ATTRIBUTION IDENTITY:
                    </div>
                    <p className="tech-formula mono" style={{ fontSize: '1rem', color: 'var(--text-1)', margin: '0 0 8px' }}>
                      f(x) = E[f(x)] + Σ φ_i(x)
                    </p>
                    <div className="mono" style={{ fontSize: '0.8125rem', color: 'var(--teal-text)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      <span>• Model Output f(x) = <strong>{xaiData.predicted_kw.toFixed(3)} kW</strong></span>
                      {xaiData.base_value_kw != null && (
                        <span>• Base Expected Value E[f(x)] = <strong>{xaiData.base_value_kw.toFixed(3)} kW</strong></span>
                      )}
                      <span>• Net Sum of SHAP Values Σ φ_i = <strong>{sumShap >= 0 ? '+' : ''}{sumShap.toFixed(3)} kW</strong></span>
                    </div>
                  </div>
                  <p className="tech-note">
                    SHAP values are rooted in cooperative game theory (Shapley values). For tree ensembles (Random Forest),
                    TreeExplainer computes the exact conditional expectation of feature attribution in polynomial time,
                    guaranteeing local accuracy and consistency across all feature partitions.
                  </p>
                  <p className="tech-note" style={{ marginTop: '6px', color: 'var(--text-3)' }}>
                    Source: {xaiData.shap_source} • Attribution represents statistical contribution within the trained decision trees, not physical causality.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
