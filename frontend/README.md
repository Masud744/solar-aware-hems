# SolarMate — Official React Frontend

Official frontend workspace for **SolarMate** (Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework). Built with React 18/19, TypeScript, and Vite, with a modern glassmorphic responsive design system.

---

## Architecture & Integration

The frontend connects to the FastAPI backend (`VITE_API_BASE_URL`, default `http://127.0.0.1:8000`) and strictly utilizes database-backed, persistent endpoints with authoritative provenance labels.

### Core Dashboard Views

1. **Home (`/`)**:
   - Power Hero card with live consumption, real-time power factor, and dynamic status.
   - 4-metric Sensor KPI Strip (Voltage, Current, Ambient Temp, Humidity).
   - 24-Hour Horizon Outlook chart with safe solar surplus vs conservative load.
   - Dual-Bank Energy Routing Flow (AC Grid vs Represented Solar banks).
   - Appliance Controls Preview with instant 3-way routing controls and emergency all-off.
   - Local weather & daylight context for Kaliakair, BD (24.07°N, 90.22°E).

2. **Energy & Cost Accounting (`/energy`)**:
   - **Total Energy Used** (Today & This Month) derived from timestamped trapezoidal integration of `sensor_readings`.
   - **User-Estimated Solar Generation** with interactive input form backed by `user_solar_estimates` table in Supabase.
   - **Estimated Solar Savings** calculated conservatively using:
     $$\text{Solar Utilized} = \min(\text{Total Measured Used}, \text{User Solar})$$
     $$\text{Savings (BDT)} = \text{Solar Utilized} \times \text{Tariff (৳7.50 / kWh)}$$
   - Today vs This Month 6-metric comparison strip.
   - Historical daily records breakdown table (7 columns) bounded by Asia/Dhaka calendar days.

3. **Appliance Management (`/appliances`)**:
   - 4-Channel hardware relay matrix (`applied_source` state feedback, anti-chatter transitions, emergency all-off interlock).
   - **Pre-Run Safety Checker** supporting preset appliances (Washing Machine, Water Pump, Rice Cooker) and custom simulations.
   - **24-Hour Forecast-Based Schedule Optimizer** identifying continuous safe solar windows.
   - Custom appliance simulation parameters: Name, Rated Power (kW), Duration (mins), and Priority.
   - Explicit advisory disclosure: Simulations do not actuate physical relays.

4. **Forecast Horizon (`/forecast`)**:
   - 24-hour hourly outlook of solar generation ($\hat{P}_{\text{solar}}$), household load ($\hat{P}_{\text{load}}$), uncertainty bounds ($k \cdot \sigma$), and safe solar surplus.
   - In-memory 30-minute caching via `forecastCache` to prevent redundant network requests.

5. **Explainability & Insights (`/insights`)**:
   - TreeSHAP feature contributions explaining solar and load predictions.
   - Natural language rule breakdowns and contextual environmental drivers.

6. **SolarMate AI Conversational Assistant (`/assistant` & Floating Widget)**:
   - Natural-language Q&A powered by Groq LLM with safe decision tool calling.
   - Queries live telemetry, forecasts, appliance run feasibility, scheduling, and energy savings.
   - Two-step confirmation flow for user solar estimate updates.
   - Strict hardware safety (zero physical relay actuation).

7. **History & Telemetry Analysis (`/history`)**:
   - Historical voltage, current, active power, and temperature trends with time-range filtering.

8. **Settings & Diagnostics (`/settings`)**:
   - Theme Switcher: Light, Dark, or System mode (persisted to `localStorage`).
   - Location station configuration (Kaliakair, BD).
   - Baseline residential tariff rate (৳7.50 / kWh).
   - Backend health diagnostics and model risk multiplier ($k = 1.0$).

---

## Data Honesty & Provenance

Every metric displays a prominent data honesty badge:
- `[MEASURED]`: Direct physical ESP32 sensor telemetry.
- `[FORECAST]`: ML model predictions.
- `[CALCULATED]`: Mathematical derivations from stored database readings.
- `[USER ESTIMATED]`: User-reported values stored in PostgreSQL.
- `[ESTIMATED]`: Derived savings or simulation offsets.

---

## Local Development & Build

```bash
# Install dependencies
npm install

# Run local development server
npm run dev

# Run TypeScript typecheck
npm run typecheck

# Build optimized production bundle
npm run build
```
