import React, { useState } from 'react';

interface Props {
  defaultOpen?: boolean;
  mismatchSuspected?: boolean | null;
  sensorOffline?: boolean;
  sensorStatusLabel?: string;
}

export const DisclosuresDrawer: React.FC<Props> = ({
  defaultOpen = false,
  mismatchSuspected = false,
  sensorOffline = false,
  sensorStatusLabel = 'ESP32 Telemetry',
}) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="disclosures-container">
      {mismatchSuspected && (
        <div className="banner" data-v="warning" style={{ marginBottom: '12px' }}>
          <span style={{ fontSize: '1.1rem' }}>⚠</span>
          <div>
            <strong>Relay Feedback State Discrepancy Suspected</strong>
            <p style={{ margin: '2px 0 0', fontSize: '0.75rem', opacity: 0.9 }}>
              The authoritative hardware state (<code>applied_source</code>) differs from recent commanded states.
              Verify hardware selector switches and relay coils.
            </p>
          </div>
        </div>
      )}

      <div className="disclosures-drawer glass">
        <button
          className="disclosures-drawer-header"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1rem' }}>📖</span>
            <strong>Academic & Hardware Implementation Disclosures</strong>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
            {open ? 'Hide details ▴' : 'Read scientific disclosures ▾'}
          </span>
        </button>

        {open && (
          <div className="disclosures-drawer-body">
            <div className="disclosure-grid">
              {/* 1. Single-Point Sensing */}
              <div className="disclosure-item">
                <h4>1. Single-Point AC Sensing & Virtual Routing</h4>
                <p>
                  A single ACS712-20A CT and ZMPT101B PT pair measures aggregate household mains consumption at the entry panel.
                  Individual sub-circuit loads are switched between AC Grid and Represented Solar banks via an 8-channel relay matrix (2 × 4-channel).
                  Because branch CTs are uninstalled in this prototype, individual branch active powers and source-specific kWh cannot be directly isolated.
                </p>
              </div>

              {/* 2. Numerical Energy Integration */}
              <div className="disclosure-item">
                <h4>2. Software Energy Accumulation</h4>
                <p>
                  The ESP32 microcontroller does not contain dedicated energy metering hardware; it numerically integrates sampled real power
                  (<code>energy_accum_kwh += P_real × Δt</code>) every 2.5 seconds. This accumulator resets on microcontroller reboot.
                  Window energy is computed via trapezoidal integration over valid historical database packets.
                </p>
              </div>

              {/* 3. Multi-Source Datasets */}
              <div className="disclosure-item">
                <h4>3. Asynchronous Multi-Source Datasets</h4>
                <p>
                  Household load forecasting models are trained on the UCI France residential power dataset, while solar generation models are trained
                  on historical irradiance data for Kaliakair, Bangladesh (24.07°N, 90.22°E). The datasets are not temporally co-located; they are synthesized
                  for academic evaluation of risk-aware residential demand management.
                </p>
              </div>

              {/* 4. Ambient Temperature & Humidity Sensor Management */}
              <div className="disclosure-item">
                <h4>4. Ambient Sensor Management (DHT22)</h4>
                <p>
                  The physical DHT22 indoor temperature and humidity sensor is connected to the ESP32 and provides measured telemetry
                  (<code>temperature_c</code>, <code>humidity_pct</code>) tagged as <code>[MEASURED]</code>. If communication dropouts occur,
                  the system transparently reports <code>Unavailable</code> without fabricating arbitrary zeros or constants.
                  Future load forecasting utilizes outdoor 2m temperature predictions supplied directly by Open-Meteo.
                </p>
              </div>
            </div>

            <div className="disclosure-footer">
              <span>Status: {sensorOffline ? 'Awaiting Telemetry' : sensorStatusLabel}</span>
              <span>Baseline Tariff: ৳ 7.50 / kWh</span>
              <span>Model Risk Multiplier: k = 1.0 (Heteroskedastic σ)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
