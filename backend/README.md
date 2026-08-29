# Backend API — Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management

> **Official Project Title:** Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework  
> **System Identity:** Solar-Aware HEMS Backend API  
> **Phase 5 Implementation** — FastAPI backend with 10 endpoints, risk-aware decision engine, Supabase database, and Open-Meteo weather integration.

---

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
cp .env.example .env
# Edit .env with your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

The app fails immediately at startup if credentials are missing. No fallback database.

### 2. Supabase Tables

Run `scripts/create_tables.sql` in your Supabase SQL Editor to create all 6 tables.

### 3. Seed Test Data

```bash
python scripts/seed_test_data.py
```

Inserts 200 hourly sensor readings (device_id="seed_test_data") for integration testing.

### 4. Run the Server

```bash
cd backend
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`

---

## Endpoints

### `POST /predict/solar`

Predict solar generation for a future time. Weather fetched from Open-Meteo.

**Request:**
```json
{"target_time": "2026-08-21T12:00:00"}
```

**Response:**
```json
{
  "target_time": "2026-08-21T12:00:00",
  "predicted_kw": 0.423,
  "safe_kw": 0.291,
  "sigma_kw": 0.1317,
  "sigma_bucket": "Partly Cloudy (21-60%)",
  "k": 1.0,
  "cloud_cover": 45,
  "temperature": 32.1,
  "relative_humidity": 78,
  "wind_speed": 4.2,
  "model_version": "rf_corrected",
  "weather_source": "Open-Meteo forecast API"
}
```

---

### `POST /predict/load`

Predict household load. Lag features from sensor_readings, weather from Open-Meteo.

**Request:**
```json
{"target_time": "2010-02-04T14:00:00"}
```

**Response includes `t2m_disclosure`** documenting the provenance mismatch.

---

### `GET /risk/margin`

Return current sigma values, k, and calibration disclosure.

---

### `POST /device/check`

ALLOW/DENY decision for a device request (§8.1/§8.2).

**Request:**
```json
{
  "device_name": "Washing Machine",
  "rated_power_kw": 1.2,
  "duration_hours": 1.0,
  "target_time": "2026-08-21T12:00:00"
}
```

**Response:**
```json
{
  "decision": "DENY",
  "safe_surplus_kw": 0.123,
  "reason": "Safe surplus (0.123 kW) < device power (1.200 kW)...",
  "predicted_solar_kw": 0.423,
  "safe_solar_kw": 0.291,
  "predicted_load_kw": 0.856,
  "conservative_load_kw": 1.367,
  ...
}
```

k is **NOT user-controllable** on this endpoint. Uses production `SAFETY_K=1.0`.

---

### `POST /schedule/recommend`

Recommend best start time within a window (§9). Uses recursive forecasting.

**Request:**
```json
{
  "device_name": "Washing Machine",
  "rated_power_kw": 1.2,
  "duration_hours": 1.0,
  "window_start": "2026-08-21T08:00:00",
  "window_end": "2026-08-21T16:00:00"
}
```

**Response includes `scheduling_disclosure`** with recursive forecasting limitations.

---

### `POST /xai/explanation`

SHAP feature contributions + rule-based explanation.

**Request:**
```json
{"prediction_type": "solar", "target_time": "2026-08-21T12:00:00"}
```

---

### `POST /action`

Log user accept/reject/manual decision.

**Request:**
```json
{"device_request_id": 1, "action": "accept"}
```

---

### `POST /ingest`

Ingest ESP32 sensor reading.

**Request:**
```json
{
  "device_id": "esp32_main",
  "ts": "2026-08-21T12:00:00",
  "voltage_v": 220.5,
  "current_a": 4.2,
  "power_w": 925.0,
  "temperature_c": 31.5
}
```

### `GET /telemetry/latest` and `GET /telemetry/history`

Dashboard-only read endpoints for the latest verified ESP32 reading and recent telemetry history. If no physical data has arrived, `latest` returns `{ "reading": null }`; it never supplies fabricated values.

---

## Decision Engine

### Formulas (§8)

```
Safe Solar        = max(0, Predicted Solar - k × σ_solar_bucket)
Conservative Load = Predicted Load + k × σ_load_bucket
Safe Surplus      = Safe Solar - Conservative Load
```

### §8.1 Instantaneous: `Safe Surplus >= Device Power → ALLOW`
### §8.2 Duration-aware: `min(Safe Surplus over all hours) >= Device Power → ALLOW`

### Bucketed Sigma (Phase 4)

| Solar Bucket | Cloud Cover | σ (kW) |
|:---|:---:|:---:|
| Clear | 0–20% | 0.0851 |
| Partly Cloudy | 21–60% | 0.1317 |
| Overcast | 61–100% | 0.1386 |

| Load Bucket | Hour | σ (kW) |
|:---|:---:|:---:|
| Night | 0–5 | 0.2662 |
| Morning | 6–11 | 0.4800 |
| Afternoon | 12–17 | 0.5114 |
| Evening | 18–23 | 0.6075 |

### k = 1.0 (Production Default)

Selected operating point based on the observed empirical coverage-utilization trade-off (Phase 4). Not described as mathematically optimal or having a textbook confidence interpretation.

### `GET /energy/summary`

Consolidated Today + Current Month persistent energy accounting and savings based on Asia/Dhaka calendar day boundaries.

**Response:**
```json
{
  "date": "2026-08-29",
  "month": "2026-08",
  "timezone": "Asia/Dhaka",
  "today": {
    "date": "2026-08-29",
    "total_energy_kwh": 0.1192,
    "user_solar_kwh": 0.05,
    "solar_utilized_kwh": 0.05,
    "has_user_solar_estimate": true,
    "estimated_savings_bdt": 0.38,
    "estimated_remaining_kwh": 0.0692,
    "excess_solar_kwh": 0.0,
    "tariff_rate": 7.50,
    "reading_count": 1804
  },
  "this_month": {
    "month": "2026-08",
    "total_energy_kwh": 0.767,
    "total_solar_kwh": 0.05,
    "total_solar_utilized_kwh": 0.05,
    "total_savings_bdt": 0.38,
    "total_remaining_kwh": 0.717,
    "total_excess_solar_kwh": 0.0,
    "days_recorded": 4
  }
}
```

### `POST /energy/solar-estimate`

Persist user-entered daily solar generation estimate into Supabase `user_solar_estimates`.

**Request:**
```json
{
  "date": "2026-08-29",
  "estimated_solar_kwh": 0.25,
  "notes": "Clear morning sunny generation"
}
```

---

## Database Schema (Supabase)

```sql
sensor_readings       (id, device_id, ts, voltage_v, current_a, power_w, temperature_c)
user_solar_estimates  (id, date, estimated_solar_kwh, notes, updated_at)
solar_predictions     (id, ts, predicted_kw, safe_kw, sigma, model_version)
load_predictions      (id, ts, predicted_kw, conservative_kw, sigma, model_version)
device_requests       (id, ts, device_name, rated_power_kw, duration_hours, priority, decision, safe_surplus_kw, reason)
user_actions          (id, device_request_id, ts, action)
shap_explanations     (id, prediction_id, prediction_type, feature_name, contribution_value)
```

### Conservative Solar Accounting Formulas
```
Solar Utilized for Load = min(Total Measured Energy Used, User Estimated Solar Generation)
Estimated Remaining Load = max(0, Total Measured Energy Used - Solar Utilized for Load)
Estimated Excess Solar = max(0, User Estimated Solar Generation - Total Measured Energy Used)
Estimated Solar Savings = Solar Utilized for Load × Tariff (৳7.50/kWh)
```

---

## T2M Provenance Disclosure

The load model was trained on same-timestamp NASA POWER reanalysis T2M for Sceaux, France — not a genuine future weather forecast. Phase 5 uses Open-Meteo forecast `temperature_2m` for Kaliakair, Bangladesh at deployment. This creates two provenance mismatches:

1. **Product:** Reanalysis (observed) vs. forecast
2. **Location:** France vs. Bangladesh

Phase 2 reported metrics reflect performance with observed/reanalysis T2M, not forecast-sourced T2M. Deployed performance may differ.

---

## Weather Integration

The backend owns Open-Meteo forecast retrieval. The frontend does not need Open-Meteo logic.

- **API:** `https://api.open-meteo.com/v1/forecast` (free, no key)
- **Location:** Kaliakair, BD (24.07°N, 90.22°E)
- **Variables:** cloud_cover, temperature_2m, relative_humidity_2m, wind_speed_10m
- **Horizon:** 7-day forecast (configurable up to 16 days)
- **Caching:** 1 hour TTL

If Open-Meteo is unreachable → HTTP 503 error. No fabricated values.

---

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

### §8.3 Worked Example Test
Reproduces the exact documented numbers: Safe Solar = 1.575 kW, Conservative Load = 0.80 kW, Safe Surplus = 0.775 kW → DENY.

### Edge Cases
1. Boundary: Safe Surplus == Device Power → ALLOW (§8.1 `>=`)
2. Negative Safe Surplus → DENY, no crash
3. Duration-aware mid-run dip → DENY (§8.2)

---

## Seed Test Data

200 rows from UCI load dataset test-set portion, `device_id="seed_test_data"`.
- **Timestamp range:** 2010-01-27 19:00 to 2010-02-05 02:00
- **No gaps:** every hourly timestamp present
- **Lag coverage verified:** all required lag/rolling timestamps exist for the last 32 rows
- **NOT used for:** model retraining, model evaluation, or reported metrics

---

## ML Forecasting Context and Short-History Demonstration Mode

### 1. Architectural Motivation & Context
The project operates across distinct, transparently disclosed data and validation layers:
* **Load Forecasting Model**: Trained and evaluated using the benchmark **UCI Individual Household Electric Power Consumption dataset** (Sceaux, France, 2006–2010).
* **Live Hardware Implementation**: An ESP32-based residential energy monitoring and dual-bank relay control system deployed in Bangladesh.
* **Solar & Weather Forecasting**: Driven by Open-Meteo forecast API for Kaliakair, Bangladesh ($24.07^\circ\text{N}, 90.22^\circ\text{E}$).

The trained Random Forest load model requires historical power lag features up to 168 hours ($\text{lag}_1, \text{lag}_2, \text{lag}_3, \text{lag}_{12}, \text{lag}_{24}, \text{lag}_{48}, \text{lag}_{168}$) and rolling window statistics ($\text{mean}_{3h}, \text{mean}_{24h}, \text{std}_{24h}, \text{mean}_{168h}$). In laboratory, testing, or newly commissioned hardware environments, the ESP32 will not have accumulated 168 continuous hours (7 days) of unbroken mains telemetry.

### 2. Dual-Layer System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HARDWARE MONITORING LAYER                            │
│  • Physical Source: ESP32 + ZMPT101B + ACS712 + DHT22 + 8-Ch Relays         │
│  • Metrics: AC Voltage, Current, Power (W), Session Energy (kWh), Relays   │
│  • Data Honesty: [MEASURED] / [CALCULATED] (Firmware accumulation)          │
│  • Storage: Supabase sensor_readings table (Strictly real hardware only)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ (Isolated)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ML FORECASTING & DECISION LAYER                         │
│  • Solar Engine: Open-Meteo Weather → Solar RF Model → [FORECAST]           │
│  • Load Engine: Open-Meteo T2M + Lag Features → Load RF Model → [FORECAST]  │
│  • Decision Engine: Safe Solar − Conservative Load → Safe Surplus           │
│  • Provenance Modes: 'real_history' vs 'benchmark_profile_fallback'         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Deterministic Benchmark Profile Fallback
When live ESP32 history is insufficient ($< 168\text{h}$):
* **Deterministic Derivation**: Missing historical load features are supplied dynamically from a precomputed conditional expectation matrix $\mathbb{E}[\text{Feature} \mid \text{month}, \text{day\_of\_week}, \text{hour}]$ derived directly from [`ml/load/data/load_processed_clean.csv`](file:///home/shahriar-alom-masud/Capstone/capstone/ml/load/data/load_processed_clean.csv) ($12 \times 7 \times 24 = 2,016$ discrete bins).
* **Precedence Rule**: Live sensor readings in `sensor_readings` are always evaluated first. Real hourly measurements take absolute precedence over the benchmark profile.
* **Automatic Transition**: When $\ge 168\text{h}$ of continuous live sensor readings accumulate, the system automatically transitions from fallback mode to the pure real-history execution path (`real_history`).
* **Database Isolation**: **No synthetic or benchmark data is ever written into the live Supabase `sensor_readings` database.** The database stores solely genuine physical telemetry.

### 4. API Metadata Output
Prediction endpoints (`/predict/load`, `/device/check`, `/schedule/recommend`, `/xai/explanation`) return transparent provenance metadata:

| Field | Type | Values / Description |
|---|---|---|
| `history_mode` | `string` | `"real_history"` or `"benchmark_profile_fallback"` |
| `feature_provenance` | `object` | Lists exact breakdown of `real_lags_used`, `benchmark_lags_used`, `real_rolling_used`, and `benchmark_rolling_used` |
| `t2m_disclosure` | `object` | Documents the reanalysis-vs-forecast and France-vs-Bangladesh meteorological context |

### 5. Academic Core Disclosure
> *"The ML forecasting layer uses the UCI residential benchmark dataset for historical load context during short-history demonstration operation, while live ESP32 telemetry is independently used for hardware monitoring and validation."*

