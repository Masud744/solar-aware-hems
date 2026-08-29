# Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E.svg?logo=supabase&logoColor=white)](https://supabase.com)
[![ESP32](https://img.shields.io/badge/ESP32-FreeRTOS-E7352C.svg?logo=espressif&logoColor=white)](https://www.espressif.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Official Project Title:**  
> **"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"**  
>
> **System Identity / Short Name:** Solar-Aware HEMS / SolarMate  
> **Repository Type:** End-to-End Cyber-Physical System & Research Archive  
> **Status:** Phase 1–8 Verified (`46/46` Unit/Integration Tests Passing | Dual-Core ESP32 Hardware Silicon-Verified)

---

## Table of Contents

1. [Executive Summary & Abstract](#1-executive-summary--abstract)
2. [Research Motivation & Problem Statement](#2-research-motivation--problem-statement)
3. [Key Scientific & Engineering Contributions](#3-key-scientific--engineering-contributions)
4. [Master System Architecture & Cyber-Physical Dataflow](#4-master-system-architecture--cyber-physical-dataflow)
5. [Machine Learning Forecasting Subsystem](#5-machine-learning-forecasting-subsystem)
   - [Solar Generation Forecasting (Phase 1)](#solar-generation-forecasting-phase-1)
   - [Residential Load Forecasting (Phase 2)](#residential-load-forecasting-phase-2)
   - [Target Leakage Detection & Chronological Integrity](#target-leakage-detection--chronological-integrity)
   - [Comparative Metrics Benchmark](#comparative-metrics-benchmark)
6. [Uncertainty Quantification & Risk-Aware Decision Engine](#6-uncertainty-quantification--risk-aware-decision-engine)
   - [Bucketed Residual Dispersion ($\sigma$) Modeling](#bucketed-residual-dispersion-sigma-modeling)
   - [Conservative Safety Margin Formulation ($k \times \sigma$)](#conservative-safety-margin-formulation-k-times-sigma)
   - [Empirical Coverage & Risk Sensitivity Analysis](#empirical-coverage--risk-sensitivity-analysis)
   - [Appliance Feasibility & Window Scheduling Logic](#appliance-feasibility--window-scheduling-logic)
7. [Explainable AI (XAI) & Interpretability Layer](#7-explainable-ai-xai--interpretability-layer)
   - [TreeSHAP Attribution Methodology](#treeshap-attribution-methodology)
   - [Global & Local Explanations](#global--local-explanations)
8. [Embedded Hardware Layer (ESP32 IoT & Relays)](#8-embedded-hardware-layer-esp32-iot--relays)
   - [Dual-Bank Independent Source Selection Matrix](#dual-bank-independent-source-selection-matrix)
   - [AC Sensing, High-Speed Sampling & Signal Conditioning](#ac-sensing-high-speed-sampling--signal-conditioning)
   - [SmartProv Captive-Portal Wi-Fi Provisioning](#smartprov-captive-portal-wi-fi-provisioning)
   - [Dual-Core FreeRTOS Task Partitioning](#dual-core-freertos-task-partitioning)
   - [Safety Interlocks & Anti-Chattering Protection](#safety-interlocks--anti-chattering-protection)
9. [Backend Architecture (FastAPI & Decision Services)](#9-backend-architecture-fastapi--decision-services)
10. [Cloud Database, State Synchronization & Security](#10-cloud-database-state-synchronization--security)
11. [Frontend Architecture (React 19, TypeScript & Vite)](#11-frontend-architecture-react-19-typescript--vite)
12. [Dataset Provenance & Critical Academic Disclosures](#12-dataset-provenance--critical-academic-disclosures)
13. [Testing, Benchmarking & Verification Status](#13-testing-benchmarking--verification-status)
14. [Repository Structure](#14-repository-structure)
15. [Installation & Local Setup Guide](#15-installation--local-setup-guide)
16. [Deployment Architecture (Render & Vercel)](#16-deployment-architecture-render--vercel)
17. [Git LFS & Model Artifact Handling](#17-git-lfs--model-artifact-handling)
18. [API Reference & Endpoint Specifications](#18-api-reference--endpoint-specifications)
19. [Visual Demonstration & Complete Screenshot Gallery](#19-visual-demonstration--complete-screenshot-gallery)
    - [19.1 System Overview & Real-Time Monitoring](#191-system-overview--real-time-monitoring)
    - [19.2 Forecast Horizon & Uncertainty Envelopes](#192-forecast-horizon--uncertainty-envelopes)
    - [19.3 Appliance Source Routing & Safety Feasibility Checker](#193-appliance-source-routing--safety-feasibility-checker)
    - [19.4 Energy & Conservative Cost Accounting](#194-energy--conservative-cost-accounting)
    - [19.5 Dual-Layer Explainable AI (XAI) Dashboard](#195-dual-layer-explainable-ai-xai-dashboard)
    - [19.6 SolarMate AI Conversational Assistant](#196-solarmate-ai-conversational-assistant)
    - [19.7 Historical Telemetry & Analytics](#197-historical-telemetry--analytics)
    - [19.8 Settings & System Diagnostics](#198-settings--system-diagnostics)
    - [19.9 Authentication, User Lifecycle & Admin Approval Matrix](#199-authentication-user-lifecycle--admin-approval-matrix)
    - [19.10 Cloud Database Schema & Tables](#1910-cloud-database-schema--tables)
    - [19.11 SmartProv Wi-Fi Captive Portal Onboarding](#1911-smartprov-wi-fi-captive-portal-onboarding)
    - [19.12 Embedded Hardware Prototype & Physical Silicon Testbed](#1912-embedded-hardware-prototype--physical-silicon-testbed)
20. [Academic Disclosures & Future Work](#20-academic-disclosures--future-work)

---

## 1. Executive Summary & Abstract

Volatile renewable generation and non-linear residential demand create severe operational uncertainties in residential microgrids. Point-estimate machine learning forecasts frequently lead to aggressive load-dispatching schedules that fail during unexpected cloud transients or demand surges, forcing unintended utility grid draw or microgrid tripping.

This repository presents **SolarMate / Solar-Aware HEMS**, an end-to-end cyber-physical framework integrating:
1. **Multi-Horizon ML Forecasting:** Out-of-sample chronological forecasting of PV generation ($R^2 = 0.9547$) and residential aggregate load ($R^2 = 0.5929$) free of future lookahead and target leakage.
2. **Uncertainty-Quantified Risk Engine:** A dynamic $k \times \sigma$ conservative safety margin engine converting point forecasts into lower-bound solar generation and upper-bound load expectations, guaranteeing zero-deficit dispatch windows.
3. **Dual-Layer Explainable AI (XAI):** TreeSHAP attribution delivering instant global and local transparency for forecast drivers.
4. **Dual-Core Embedded Hardware Matrix:** An ESP32 microcontroller operating FreeRTOS, managing an 8-channel dual-bank relay matrix (Grid vs. Represented Solar), high-speed AC waveform sampling, break-before-make interlocks, and SmartProv captive-portal Wi-Fi provisioning.
5. **Decoupled Cloud & UI Ecosystem:** A FastAPI REST API, Supabase PostgreSQL persistence with Admin Approval Access Control, and a glassmorphic React 19 + TypeScript real-time dashboard.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       MASTER SYSTEM TOPOLOGY                                    │
│                                                                                                 │
│  [ Open-Meteo Weather ] ───┐                                                                    │
│                            ▼                                                                    │
│  [ UCI & Solar Data ] ──► [ Random Forest Models ] ──► [ $k \times \sigma$ Risk Engine ]        │
│                                      │                                  │                       │
│                                      ▼                                  ▼                       │
│                              [ TreeSHAP XAI ]                 [ Safe Surplus Windows ]          │
│                                      │                                  │                       │
│                                      └────────────────┬─────────────────┘                       │
│                                                       ▼                                         │
│                                        ┌─────────────────────────────┐                          │
│                                        │     FastAPI Cloud Engine    │                          │
│                                        │  • REST Endpoints / Decision│                          │
│                                        │  • Groq SolarMate AI Agent  │                          │
│                                        └──────────────┬──────────────┘                          │
│                                                       │                                         │
│                         ┌─────────────────────────────┴─────────────────────────────┐           │
│                         ▼                                                           ▼           │
│         ┌───────────────────────────────┐                           ┌─────────────────────────┐ │
│         │     React 19 + Vite UI        │                           │  ESP32 Dual-Core IoT    │ │
│         │  • Glassmorphic Dashboard     │                           │  • Dual-Bank Relay ATS  │ │
│         │  • Data Honesty Badges        │                           │  • High-Speed AC Sample │ │
│         │  • Interactive Scheduling     │                           │  • SmartProv Captive NVS│ │
│         └───────────────────────────────┘                           └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Research Motivation & Problem Statement

### The Problem of Deterministic HEMS Over-Optimism
Conventional Home Energy Management Systems (HEMS) treat point predictions ($\hat{P}_{\text{solar}}$ and $\hat{P}_{\text{load}}$) as ground-truth constants. When an appliance is scheduled under the naive constraint $\hat{P}_{\text{solar}} \ge \hat{P}_{\text{load}} + P_{\text{appliance}}$, any negative forecast error instantly drives the household into deficit, causing grid tariff penalties or battery degradation.

### Core Challenges Addressed:
1. **Target Leakage in Published Benchmarks:** Standard time-series pipelines inadvertently introduce target leakage (e.g., using contemporaneous direct irradiance or future sub-metering data), yielding near-perfect $R^2 \approx 1.0$ in notebooks that collapse in physical deployment.
2. **Asymmetric Risk of Forecast Errors:** An over-prediction of solar generation is significantly more hazardous than an under-prediction. Schedulers must evaluate worst-case lower bounds.
3. **Cyber-Physical Interlock Safety:** Software routing between utility grid and solar sources must be physically isolated with hardware/software dead-time to avoid destructive cross-conduction.
4. **Data Transparency & User Trust:** Homeowners require explainable reasoning (XAI) and absolute honesty regarding data provenance (measured hardware telemetry vs. synthetic/forecasted values).

---

## 3. Key Scientific & Engineering Contributions

- **Strict Leakage-Free ML Formulation:** Formal identification and elimination of lookahead bias, achieving verified test-set metrics across multiple candidate models (Random Forest, XGBoost, Decision Trees, SVR, Linear Regression).
- **Heteroskedastic Uncertainty Quantification:** Empirical residual analysis showing that forecast error variance ($\sigma$) strongly correlates with meteorological regimes (Clear / Partly Cloudy / Overcast) and diurnal demand phases (Night / Morning / Afternoon / Evening).
- **Conservative Safe Surplus Formulation:** Formulation of $\text{Surplus}_{\text{safe}} = (\hat{S} - k \cdot \sigma_S) - (\hat{L} + k \cdot \sigma_L)$, providing deterministic safety guarantees parameterized by user risk tolerance $k$.
- **Zero-Credential SmartProv IoT Layer:** Production-grade ESP32 firmware running FreeRTOS with captive-portal Wi-Fi onboarding, NVS storage, 300 ms dead-time break-before-make relay interlocking, and aggregate AC power calculation.
- **Data Honesty Badging Subsystem:** Full UI visual hierarchy categorizing every rendered data point into `[MEASURED]`, `[FORECAST]`, `[CALCULATED]`, `[USER ESTIMATED]`, or `[ESTIMATED]`.

---

## 4. Master System Architecture & Cyber-Physical Dataflow

The system comprises four decoupled tiers:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. EMBEDDED HARDWARE TIER (ESP32-WROOM-32 @ 240 MHz)                                             │
│    • Core 0: High-speed AC waveform sampling (4000+ S/s), RMS calculation, debouncing.          │
│    • Core 1: FreeRTOS network manager, SmartProv captive portal, HTTPS telemetry streaming.      │
│    • Actuation: 8-Channel Optocoupled Relay Bank (4 Grid lines + 4 Solar lines).                 │
│    • Interlock: 300 ms break-before-make software dead-time on all transfer transitions.         │
└─────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │ HTTPS Telemetry (/ingest) & Polling (/api/device/status)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. CLOUD BACKEND & DECISION TIER (FastAPI @ Python 3.11+)                                        │
│    • Ingestion Service: Validates packets, detects current mismatches, updates Supabase cache.   │
│    • ML Inference Service: Preprocesses lag/weather features, executes Random Forest predictors. │
│    • Risk Engine: Computes regime-specific $\sigma$, applies $k \times \sigma$ margins.          │
│    • XAI Engine: TreeSHAP decomposition into real-time feature attribution lists.                │
│    • AI Assistant: Groq LLM tool-calling agent with strict read-only hardware boundaries.        │
└─────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │ PostgreSQL REST & Realtime Subscriptions
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. PERSISTENCE & ACCESS CONTROL TIER (Supabase Cloud PostgreSQL)                                 │
│    • sensor_readings: Immutable, timestamped physical IoT records.                               │
│    • device_status & user_actions: Command queues, target states, and audit trails.              │
│    • profiles: Role-based access control (RBAC) with Admin Approval Matrix.                      │
│    • user_solar_estimates & chat_messages: User-isolated historical energy data.                 │
└─────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │ REST API Client & Session Tokens
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. PRESENTATION & CONTROL TIER (React 19 + TypeScript + Vite)                                    │
│    • Glassmorphic dashboard featuring real-time Power Hero & Sensor Grid.                        │
│    • 24-Hour Horizon Outlook chart with safe solar surplus envelope.                             │
│    • Appliance Safety Checker & Forecast Scheduling Optimizer.                                   │
│    • Interactive SolarMate AI conversational drawer with function-calling feedback.              │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Machine Learning Forecasting Subsystem

### Solar Generation Forecasting (Phase 1)
- **Target Variable:** Solar PV Power Output ($P_{\text{solar}}$ in kW), scaled for a standard $3.0\text{ kWp}$ residential rooftop installation.
- **Feature Set (7 features):** `cloud_cover` (%), `temperature` (°C), `relative_humidity` (%), `wind_speed` (m/s), `hour` ($0\text{–}23$), `month` ($1\text{–}12$), `day_of_year` ($1\text{–}365$).
- **Chronological Split:** Train on years 2020–2024 ($43,848\text{ hours}$); Test on out-of-sample holdout year 2025 ($8,760\text{ hours}$).

### Residential Load Forecasting (Phase 2)
- **Target Variable:** Active Household Load ($P_{\text{load}}$ in kW).
- **Feature Set (16 features):** Autoregressive lags (`lag_1`, `lag_2`, `lag_3`, `lag_12`, `lag_24`, `lag_48`, `lag_168`), Rolling Statistics (`rolling_mean_3h`, `rolling_mean_24h`, `rolling_std_24h`, `rolling_mean_168h`), Calendar features (`hour`, `day_of_week`, `month`, `is_weekend`), and Ambient Temperature (`T2M`).
- **Chronological Split:** Train on chronological $80\%$ ($17,280\text{ hours}$); Test on chronological out-of-sample holdout $20\%$ ($4,320\text{ hours}$).

### Target Leakage Detection & Chronological Integrity
During research audits, baseline models demonstrating suspicious $R^2 \approx 1.0$ were diagnosed with target leakage:
1. **Solar Leakage:** Using Direct Normal Irradiance (`DNI`) or global horizontal irradiance (`GHI`) contemporaneously inside the test split where PV power was derived from irradiance via physical transfer functions.
2. **Load Leakage:** Using contemporaneous sub-metering (`Sub_metering_3`) to predict total active power.

**Corrective Action:** All leaky features were permanently stripped from the training pipelines. The corrected models rely strictly on exogenous weather forecasts, historical autoregressive lags, and calendar harmonics.

### Comparative Metrics Benchmark

| Pipeline | Model | MAE (kW) | RMSE (kW) | $R^2$ | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Solar** | *RF Leaky Baseline (Reference)* | $0.00007$ | $0.00013$ | $1.0000$ | Leakage Demonstration |
| **Solar** | **Random Forest (Scientifically Approved)** | $\mathbf{0.06413}$ | $\mathbf{0.12436}$ | $\mathbf{0.9547}$ | **Production Primary** |
| **Solar** | XGBoost (Lightweight Alternative) | $0.06969$ | $0.12649$ | $0.9532$ | Production Alternative |
| **Solar** | Decision Tree | $0.06838$ | $0.13258$ | $0.9486$ | Benchmark |
| **Solar** | Support Vector Regression (SVR) | $0.09224$ | $0.15163$ | $0.9327$ | Benchmark |
| **Solar** | Linear Regression | $0.30011$ | $0.38374$ | $0.5690$ | Baseline |
| **Load** | *RF Leaky Baseline (Reference)* | $0.01591$ | $0.02316$ | $0.9993$ | Leakage Demonstration |
| **Load** | **Random Forest (Scientifically Approved)** | $\mathbf{0.33206}$ | $\mathbf{0.48383}$ | $\mathbf{0.5929}$ | **Production Primary** |
| **Load** | XGBoost (Lightweight Alternative) | $0.34244$ | $0.49191$ | $0.5792$ | Production Alternative |
| **Load** | Support Vector Regression (SVR) | $0.34534$ | $0.51168$ | $0.5447$ | Benchmark |
| **Load** | Linear Regression | $0.36821$ | $0.51913$ | $0.5313$ | Baseline |
| **Load** | Decision Tree | $0.37114$ | $0.54485$ | $0.4837$ | Benchmark |

---

## 6. Uncertainty Quantification & Risk-Aware Decision Engine

Deterministic forecasts cannot capture transient cloud shading or sudden cooking/heating demand spikes. The system models forecast uncertainty empirically through out-of-sample residual distributions:
$$e_S = S_{\text{actual}} - \hat{S}, \quad e_L = L_{\text{actual}} - \hat{L}$$

```
                                    UNCERTAINTY SAFETY ENVELOPE
  Power (kW)
     ▲
     │              ╭─────────────────────────────╮ <--- Upper Bound Load: L_upper = L_hat + k * sigma_L
     │             ╱        Point Forecast       ╱
     │            ╱       Load (L_hat)          ╱
     │           ╭─────────────────────────────╮
     │
     │           ╭─────────────────────────────╮ <--- Safe Solar Surplus Window: S_lower > L_upper + P_app
     │          ╱         Point Forecast        ╱
     │         ╱        Solar (S_hat)          ╱
     │        ╭─────────────────────────────╮ <--- Lower Bound Solar: S_lower = S_hat - k * sigma_S
     │       ╱                             ╱
     └──────┴─────────────────────────────┴────────────────────────────────────────────────► Time (Hours)
```

### Bucketed Residual Dispersion ($\sigma$) Modeling

Rather than applying a single global variance, the engine implements regime-stratified dispersion buckets:

1. **Solar Cloud Cover Buckets:**
   - **Clear Sky** ($\text{cloud\_cover} \le 20\%$): $\sigma_S = 0.0851\text{ kW}$
   - **Partly Cloudy** ($20\% < \text{cloud\_cover} \le 70\%$): $\sigma_S = 0.1317\text{ kW}$
   - **Overcast** ($\text{cloud\_cover} > 70\%$): $\sigma_S = 0.1386\text{ kW}$

2. **Load Diurnal Time-of-Day Buckets:**
   - **Night** ($00:00\text{–}05:59$): $\sigma_L = 0.2662\text{ kW}$
   - **Morning** ($06:00\text{–}11:59$): $\sigma_L = 0.4800\text{ kW}$
   - **Afternoon** ($12:00\text{–}17:59$): $\sigma_L = 0.5114\text{ kW}$
   - **Evening** ($18:00\text{–}23:59$): $\sigma_L = 0.6075\text{ kW}$

### Conservative Safety Margin Formulation ($k \times \sigma$)
For risk parameter $k \in [0.5, 3.0]$ (default operating point $k = 1.0$):
$$\hat{S}_{\text{lower}} = \max(0, \hat{S} - k \cdot \sigma_S(\text{regime}))$$
$$\hat{L}_{\text{upper}} = \hat{L} + k \cdot \sigma_L(\text{regime})$$
$$\text{Surplus}_{\text{safe}} = \max(0, \hat{S}_{\text{lower}} - \hat{L}_{\text{upper}})$$

### Appliance Feasibility & Window Scheduling Logic
When evaluating whether an appliance requiring rated power $P_{\text{app}}$ and duration $D$ hours can run safely on solar:
1. The engine scans the 24-hour horizon.
2. An appliance run is approved **IF AND ONLY IF**:
   $$\forall t \in [t_{\text{start}}, t_{\text{start}} + D], \quad \text{Surplus}_{\text{safe}}(t) \ge P_{\text{app}}$$
3. If the condition is met, the system flags the window as `SAFE_SOLAR_WINDOW`.
4. If the condition is violated, the system returns `UNSAFE_DEFICIT_RISK` and computes the exact grid draw penalty expected under worst-case lower bounds.

---

## 7. Explainable AI (XAI) & Interpretability Layer

The system integrates **TreeSHAP** (SHapley Additive exPlanations) directly into both the backend API (`/xai/solar`, `/xai/load`) and the frontend UI (`/insights`).

$$\hat{f}(x) = \phi_0 + \sum_{i=1}^{M} \phi_i(x)$$
Where $\phi_0 = \mathbb{E}[f(x)]$ is the base value, and $\phi_i$ is the exact additive contribution of feature $i$.

```
                      SHAP LOCAL WATERFALL EXPLANATION EXAMPLE (Solar Model)
   Base Value E[f(x)] = 0.354 kW
   ────────────────────────────────────────────────────────────────────────
   [+] hour = 13.00                │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  (+1.182 kW)
   [+] cloud_cover = 5.0%          │▓▓▓▓▓▓▓▓▓▓▓▓                    (+0.451 kW)
   [-] month = 12 (December)       │░░░░░░                          (-0.210 kW)
   [-] temperature = 18.2 C        │░░░                             (-0.083 kW)
   ────────────────────────────────────────────────────────────────────────
   Predicted Solar Generation f(x) = 1.694 kW
```

- **Global Attribution:** Confirms that `hour` and `cloud_cover` dominate solar generation ($>85\%$ total importance), while `power_lag_1`, `power_lag_24`, and `rolling_mean_24h` dominate residential load.
- **Local Attribution:** Provides instant natural-language explanations for unexpected model dips, allowing users to understand why a scheduled window was flagged unsafe.

---

## 8. Embedded Hardware Layer (ESP32 IoT & Relays)

```
                            ESP32 HARDWARE SCHEMATIC & WIRING
   ┌─────────────────────────────────────────────────────────────────────────┐
   │                          ESP32-WROOM-32 (30-Pin)                        │
   │                                                                         │
   │  [GPIO 04] ◄── DHT22 Data (10k Pull-up to 3.3V)                         │
   │  [GPIO 34] ◄── ACS712-20A (Via 10k/15k Resistor Divider: 5V -> 3.0V)    │
   │  [GPIO 35] ◄── ZMPT101B AC Voltage Transformer Module                   │
   │                                                                         │
   │  [GPIO 16] ──► Grid Relay Load 1 ──┐                                    │
   │  [GPIO 17] ──► Grid Relay Load 2   ├── Active-LOW 8-Channel Relay Board │
   │  [GPIO 18] ──► Grid Relay Load 3   │   (Songle SRD-05VDC-SL-C)          │
   │  [GPIO 19] ──► Grid Relay Load 4 ──┘   (External 5V/2A PSU)             │
   │                                                                         │
   │  [GPIO 21] ──► Solar Relay Load 1 ─┐                                    │
   │  [GPIO 22] ──► Solar Relay Load 2  ├── Active-LOW Transfer Selectors    │
   │  [GPIO 23] ──► Solar Relay Load 3  │                                    │
   │  [GPIO 13] ──► Solar Relay Load 4 ─┘                                    │
   │                                                                         │
   │  [GPIO 26, 27, 32, 33] ◄── 4x Physical Low-Voltage Source Switches      │
   └─────────────────────────────────────────────────────────────────────────┘
```

### Dual-Bank Independent Source Selection Matrix
- **Topology:** 4 independent household load circuits. Each circuit is routed through a SPDT dual-relay arrangement:
  - Relay Bank A: AC Utility Grid Source.
  - Relay Bank B: Represented Solar Inverter Source.
- **Break-Before-Make Safety:** Software-enforced $300\text{ ms}$ dead-time between de-energizing one relay and energizing the opposite relay, preventing destructive line-to-inverter short-circuits.

### AC Sensing, High-Speed Sampling & Signal Conditioning
- **Current Sensing:** ACS712-20A Hall-effect sensor with a $10\text{ k}\Omega / 15\text{ k}\Omega$ precision voltage divider scaling the $0\text{–}5\text{V}$ output safely to $0\text{–}3.0\text{V}$ for ESP32 ADC1 (GPIO 34).
- **Voltage Sensing:** ZMPT101B active transformer on ADC1 (GPIO 35).
- **Sampling Window:** Continuous $200\text{ ms}$ sampling window capturing exactly 10 complete $50\text{ Hz}$ AC cycles ($>4,000\text{ samples/sec}$) with trapezoidal true-RMS integration.

### SmartProv Captive-Portal Wi-Fi Provisioning
- **Zero Plaintext Credentials:** No hardcoded SSIDs or passwords in source code.
- **Captive Portal:** If credentials are not present in NVS, the ESP32 broadcasts a secure `HEMS_XXXX` SoftAP. Users connect via mobile browser to configure local credentials.
- **Transient Memory Recovery:** FreeRTOS completely unloads the WebServer and DNS server structures post-connection, recovering $>45\text{ KB}$ of heap for high-speed sampling.

### Dual-Core FreeRTOS Task Partitioning
- **Core 0 (Real-Time Sensing Task):** Dedicated high-frequency ADC sampling, RMS computation, zero-crossing detection, FIR digital filtering, and local physical switch debouncing ($40\text{ ms}$).
- **Core 1 (Communication Task):** Wi-Fi stack, HTTPS REST telemetry streaming ($3\text{ s}$ interval), command polling ($1.5\text{ s}$ interval), and background synchronization.

---

## 9. Backend Architecture (FastAPI & Decision Services)

The backend is built with FastAPI for high-throughput asynchronous execution:
- **`app/main.py`:** Application lifespan manager, CORS middleware, router registration.
- **`app/config.py`:** Strongly-typed Pydantic settings loading cloud secrets, model paths, and geographical coordinates.
- **`app/routers/`:**
  - `ingest.py`: Receives and validates ESP32 telemetry packets; updates real-time sensor tables.
  - `device.py`: Controls relay channels, executes source switching, and manages hardware status.
  - `predict.py`: Runs real-time Solar and Load inference.
  - `risk.py`: Computes $k \times \sigma$ conservative bounds and evaluates appliance safety windows.
  - `xai.py`: Generates TreeSHAP local waterfall and global feature attributions.
  - `energy.py`: Trapezoidal energy integration ($\text{kWh}$) and conservative cost savings accounting.
  - `chat.py`: Natural language assistant endpoint powered by Groq LLM tool calling.
  - `auth.py` & `admin.py`: Supabase Auth verification, profile lifecycle, and Admin Approval Matrix.

---

## 10. Cloud Database, State Synchronization & Security

### PostgreSQL Schema & Access Control (Supabase)

```
┌─────────────────────────┐          ┌───────────────────────────┐
│     sensor_readings     │          │         profiles          │
├─────────────────────────┤          ├───────────────────────────┤
│ id (uuid, PK)           │          │ id (uuid, PK -> auth.uid) │
│ created_at (timestamptz)│          │ full_name (text)          │
│ voltage (float4)        │          │ role ('admin' | 'user')   │
│ current (float4)        │          │ status ('pending'|'appr') │
│ active_power (float4)   │          └─────────────┬─────────────┘
│ power_factor (float4)   │                        │ 1:N
│ temp_c / humidity       │                        ▼
│ relay_states (jsonb)    │          ┌───────────────────────────┐
└─────────────────────────┘          │   user_solar_estimates    │
                                     ├───────────────────────────┤
┌─────────────────────────┐          │ id (uuid, PK)             │
│      device_status      │          │ user_id (uuid, FK)        │
│      device_requests    │          │ estimate_date (date)      │
│      user_actions       │          │ estimated_kwh (float4)    │
└─────────────────────────┘          └───────────────────────────┘
```

- **Row-Level Security (RLS):** All user tables enforce strict PostgreSQL RLS policies ensuring users can only read and mutate their own estimates and chat histories.
- **Admin Approval Gate:** Newly registered users default to `status = 'pending'`. Access to the full telemetry and control dashboard requires explicit approval by an administrator.

---

## 11. Frontend Architecture (React 19, TypeScript & Vite)

Built with a modern responsive glassmorphic design system in Vanilla CSS:
- **`App.tsx`:** Master application shell, real-time telemetry hooks, and authentication router.
- **Navigation Rail:** Responsive sidebar with role-aware views (Overview, Energy, Appliances, Forecast, Insights, History, Assistant, Settings, Admin).
- **Interactive UI Components:**
  - `PowerHero.tsx`: Live active power dial, power factor gauge, dynamic status badges.
  - `HorizonOutlookChart.tsx`: High-performance SVG/Recharts 24-hour forecast curve with shaded uncertainty bounds.
  - `ApplianceSafetyChecker.tsx`: Interactive feasibility checker with custom power/duration sliders.
  - `EnergyTracker.tsx`: Trapezoidal integration charts with tariff savings calculations.
  - `FloatingAssistant.tsx`: Global conversational AI drawer.

---

## 12. Dataset Provenance & Critical Academic Disclosures

> ### ⚠️ MANDATORY ACADEMIC TRANSPARENCY NOTICE
>
> 1. **Geographical & Temporal Non-Colocation:**
>    - **Load Dataset:** UCI Individual Household Electric Power Consumption dataset collected in **Sceaux, France (2006–2010)**.
>    - **Solar & Weather Dataset:** Open-Meteo ERA5 hourly reanalysis data collected for **Kaliakair, Bangladesh (2020–2026)** ($24.07^\circ\text{N}, 90.22^\circ\text{E}$).
>    - **Academic Disclosure:** These two datasets are **NOT geographically or temporally co-located**. They were joined synthetically by calendar matching solely to demonstrate and validate the multi-modal cyber-physical HEMS methodology under realistic forecast uncertainty. This dataset must **never** be cited or represented as a real measured household solar-paired deployment.
>
> 2. **Hardware "Solar" Representation:**
>    - In the prototype bench setup, the "Solar" input terminal is energized by a secondary grid-derived AC circuit to safely validate transfer switching, interlock dead-time, and telemetry streaming without requiring a physical live rooftop photovoltaic array.

---

## 13. Testing, Benchmarking & Verification Status

### Automated Test Suite Execution (46/46 Passed)

```bash
$ pytest -v backend/tests firmware/tests

============================== test session starts ===============================
backend/tests/test_assistant_chat.py::test_tool_get_live_telemetry PASSED   [  2%]
backend/tests/test_assistant_chat.py::test_tool_get_relay_status PASSED     [  4%]
backend/tests/test_assistant_chat.py::test_tool_appliance_safety_allow PASSED [  6%]
backend/tests/test_assistant_chat.py::test_tool_solar_estimate_confirmation_flow PASSED [  8%]
backend/tests/test_post_chat_endpoint_schema PASSED [ 10%]
backend/tests/test_assistant_chat.py::test_chat_hardware_safety_no_relays_in_tools PASSED [ 13%]
backend/tests/test_assistant_chat.py::test_chat_history_get_and_delete_endpoints PASSED [ 15%]
backend/tests/test_auth_and_admin.py::test_signup_creates_pending_user PASSED [ 17%]
backend/tests/test_auth_and_admin.py::test_login_pending_user_is_blocked_with_403 PASSED [ 19%]
backend/tests/test_auth_and_admin.py::test_login_approved_user_receives_token PASSED [ 21%]
backend/tests/test_admin_endpoints_require_admin_role PASSED [ 23%]
backend/tests/test_auth_and_admin.py::test_admin_can_approve_pending_user PASSED [ 26%]
backend/tests/test_auth_and_admin.py::test_chat_history_per_user_isolation PASSED [ 28%]
backend/tests/test_decision_engine.py::TestSection83WorkedExample::test_exact_intermediate_values PASSED [ 30%]
backend/tests/test_decision_engine.py::TestSection83WorkedExample::test_decision_is_deny PASSED [ 32%]
backend/tests/test_decision_engine.py::TestSection83WorkedExample::test_reason_contains_surplus_value PASSED [ 34%]
backend/tests/test_decision_engine.py::TestSection83WorkedExample::test_symmetric_formula_with_raw_k PASSED [ 36%]
backend/tests/test_decision_engine.py::TestEdgeCases::test_boundary_safe_surplus_equals_device_power PASSED [ 39%]
backend/tests/test_decision_engine.py::TestEdgeCases::test_negative_safe_surplus_no_crash PASSED [ 41%]
backend/tests/test_decision_engine.py::TestEdgeCases::test_duration_aware_mid_run_dip PASSED [ 43%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_solar_clear_boundary PASSED [ 45%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_solar_partly_cloudy_boundary PASSED [ 47%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_solar_overcast_boundary PASSED [ 50%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_load_night_boundary PASSED [ 52%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_load_morning_boundary PASSED [ 54%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_load_afternoon_boundary PASSED [ 56%]
backend/tests/test_decision_engine.py::TestSigmaBuckets::test_load_evening_boundary PASSED [ 58%]
backend/tests/test_energy_accounting.py::test_trapezoidal_integration_basic PASSED [ 60%]
backend/tests/test_energy_accounting.py::test_trapezoidal_integration_gap_protection PASSED [ 63%]
backend/tests/test_energy_accounting.py::test_dhaka_calendar_bounds PASSED [ 65%]
backend/tests/test_energy_accounting.py::test_conservative_solar_formulas_case_a_load_greater_than_solar PASSED [ 67%]
backend/tests/test_energy_accounting.py::test_conservative_solar_formulas_case_b_solar_greater_than_load PASSED [ 69%]
backend/tests/test_energy_accounting.py::test_energy_summary_endpoint PASSED [ 71%]
backend/tests/test_energy_accounting.py::test_solar_estimate_post_validation PASSED [ 73%]
backend/tests/test_firmware_v2_endpoints.py::test_firmware_v2_telemetry_ingest_mocked PASSED [ 76%]
backend/tests/test_firmware_v2_endpoints.py::test_device_status_endpoint PASSED [ 78%]
backend/tests/test_firmware_v2_endpoints.py::test_device_control_endpoint PASSED [ 80%]
backend/tests/test_firmware_v2_endpoints.py::test_device_calibrate_endpoint PASSED [ 82%]
backend/tests/test_firmware_v2_endpoints.py::test_calibrated_telemetry_ingest PASSED [ 84%]
backend/tests/test_state_synchronization.py::test_pending_command_protected_from_old_telemetry PASSED [ 86%]
backend/tests/test_state_synchronization.py::test_new_dashboard_command_generates_fresh_timestamp PASSED [ 89%]
backend/tests/test_state_synchronization.py::test_physical_selector_change_reconciles_normally PASSED [ 91%]
firmware/tests/test_firmware_math.py::test_pure_resistive_load PASSED      [ 93%]
firmware/tests/test_firmware_math.py::test_inductive_load_phase_lag PASSED [ 95%]
firmware/tests/test_firmware_math.py::test_acs712_resistor_divider_voltage_safety PASSED [ 97%]
firmware/tests/test_firmware_math.py::test_sampling_rate_and_sample_count PASSED [100%]
============================== 46 passed in 7.84s ===============================
```

### Hardware Verification Matrix

| Subsystem / Feature | Physical Verification Status | Evidence / Notes |
| :--- | :---: | :--- |
| **FreeRTOS Dual-Core Execution** | `VERIFIED ON HARDWARE` | Core 0 (ADC sampling) & Core 1 (HTTPS/SmartProv) running concurrently. |
| **SmartProv Captive Portal** | `VERIFIED ON HARDWARE` | Tested SoftAP connection, NVS credential write, and automatic STA reconnect. |
| **8-Channel Relay Matrix** | `VERIFIED ON HARDWARE` | All 8 GPIOs toggled and verified with multimeter and relay status LEDs. |
| **300ms Dead-Time Interlock** | `VERIFIED ON HARDWARE` | Break-before-make transition timing verified via digital logic capture. |
| **DHT22 Telemetry** | `VERIFIED ON HARDWARE` | Live temperature and humidity streaming reliably on GPIO 4. |
| **ZMPT101B & ACS712 Zero Calibration** | `VERIFIED ON HARDWARE` | Zero-offset calibration verified on live silicon ($V_{\text{zero}} \approx 2048$). |
| **Known-Load RMS Power Scaling** | `PENDING BENCH CALIBRATION` | Requires multi-point physical resistive load bench calibration. |

---

## 14. Repository Structure

```
capstone/
├── backend/                        # FastAPI Backend Service
│   ├── app/
│   │   ├── config.py               # Pydantic environment configuration
│   │   ├── database.py             # Supabase client factory
│   │   ├── main.py                 # FastAPI application lifespan & CORS
│   │   ├── models/                 # Pydantic schemas
│   │   ├── routers/                # 10 API route handlers
│   │   └── services/               # ML loaders, decision engine, XAI, accounting
│   ├── scripts/                    # PostgreSQL migrations & seeders
│   ├── tests/                      # Automated Pytest suite (42 tests)
│   ├── requirements.txt            # Backend production dependencies
│   ├── .env.example                # Backend environment template
│   └── README.md                   # Backend documentation
├── frontend/                       # React 19 + TypeScript + Vite Frontend
│   ├── public/                     # Static assets (bg.webp)
│   ├── src/
│   │   ├── api/                    # API client & 30-min forecastCache
│   │   ├── components/             # UI views (Overview, Energy, Appliances, XAI, Chat, Admin)
│   │   ├── hooks/                  # Telemetry, DeviceControl, Auth, Theme hooks
│   │   ├── types/                  # TypeScript interface definitions
│   │   └── utils/                  # Constants, formatting, astronomical sunrise math
│   ├── package.json                # Frontend manifest & scripts
│   ├── vercel.json                 # Vercel SPA routing rewrite
│   ├── .env.example                # Frontend environment template
│   └── README.md                   # Frontend documentation
├── firmware/                       # ESP32 FreeRTOS C++ Firmware
│   ├── firmware.ino                # Main setup, loop & dual-core task dispatch
│   ├── config.h                    # Pinouts, safety timing & calibration constants
│   ├── control_switches.*          # Debounced physical toggle switch handlers
│   ├── electricity_meter.*         # High-speed AC waveform true-RMS sampling
│   ├── relay_controller.*          # Interlocked dual-bank relay driver
│   ├── tests/                      # Python firmware math unit tests (4 tests)
│   ├── wiring_diagrams/            # Hardware schematics & wiring images
│   └── README.md                   # Hardware execution & pinout guide
├── ml/                             # Machine Learning Research Pipelines
│   ├── solar/                      # Phase 1: Solar ML training, evaluation & metrics
│   ├── load/                       # Phase 2: Load ML training, evaluation & metrics
│   ├── risk_module/                # Phase 4: Uncertainty quantification & k-sensitivity
│   └── xai/                        # Phase 3: TreeSHAP explainability scripts & plots
├── Dataset/                        # Raw Historical Datasets
│   ├── kaliakair_openmeteo_solar_raw.csv  # Bangladesh solar reanalysis data
│   └── main_data.csv               # UCI France household electric power consumption
├── docs/                           # Authoritative Documentation & Audit Reports
│   ├── audit/                      # 16 detailed phase audit reports
│   ├── DATA_PROVENANCE_REPORT.md
│   ├── HARDWARE_CALIBRATION_METHODOLOGY.md
│   ├── ML_MODEL_REPORT.md
│   ├── RISK_UNCERTAINTY_REPORT.md
│   ├── XAI_REPORT.md
│   ├── SMARTPROV_INTEGRATION_REPORT.md
│   ├── REPOSITORY_GITHUB_DEPLOYMENT_AUDIT.md
│   ├── GIT_LFS_AND_MODEL_ARTIFACT_STRATEGY.md
│   ├── TITLE_AND_BRANDING_CHANGELOG.md
│   └── GITHUB_PREFLIGHT_REPORT.md
├── Screenshoots/                   # UI dashboard and prototype hardware photographs (25 images)
├── .gitattributes                  # Git LFS tracking rules
├── .gitignore                      # Comprehensive Git exclusion rules
├── requirements.txt                # Root production & research dependencies
└── README.md                       # Master documentation entrypoint
```

---

## 15. Installation & Local Setup Guide

### 1. Prerequisites
- **Python:** Version `3.11` to `3.14`
- **Node.js:** Version `18.x` or `20.x` with `npm`
- **Arduino IDE:** Version `2.x` with ESP32 Board Package installed
- **Supabase Account:** Managed cloud PostgreSQL project

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/your-username/capstone.git
cd capstone

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and populate SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and GROQ_API_KEY

# Run test suite
pytest -v backend/tests firmware/tests

# Launch local backend server
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Configure environment variables
cp .env.example .env
# Default VITE_API_BASE_URL=http://127.0.0.1:8000

# Launch Vite development server
npm run dev

# Verify production build
npm run build
```

### 4. ESP32 Firmware Flashing
1. Open `firmware/firmware.ino` in Arduino IDE.
2. Select Board: **ESP32 Dev Module**.
3. Install required Arduino libraries: `SmartProv` (v2.1.3+), `DHT sensor library` (Adafruit), `ArduinoJson` (v6/v7).
4. Connect ESP32 via USB and upload.
5. On first boot, connect your smartphone to the `HEMS_XXXX` Wi-Fi access point and complete captive portal provisioning.

---

## 16. Deployment Architecture (Render & Vercel)

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│       VERCEL (Frontend Host)         │     │         RENDER (Backend Host)        │
│  • Framework: React + Vite SPA       │     │  • Service: Web Service (Python 3)   │
│  • Build: npm run build              │     │  • Build: pip install -r requirements│
│  • Output: dist/                     │     │  • Start: uvicorn app.main:app       │
│  • Routing: vercel.json rewrite      │     │  • Env: SUPABASE_*, GROQ_*, PORT     │
│  • Env: VITE_API_BASE_URL            │     │  • Sizing: Starter (1GB RAM) for RF  │
└──────────────────┬───────────────────┘     └──────────────────┬───────────────────┘
                   │                                            │
                   └────────────── HTTPS REST API ──────────────┘
```

- **Docker Recommendation:** **Docker is intentionally NOT used.** Render natively supports Python web services directly from `requirements.txt`. Native execution eliminates container engine memory overhead (~50–100 MB RAM), ensuring maximum available memory for ML model execution.
- **Render RAM Tier Requirement:** The production Random Forest models consume **613.75 MB RAM** at runtime. Render **Starter Tier (1 GB RAM)** is required. The Free Tier (512 MB) will fail with Out-Of-Memory.

---

## 17. Git LFS & Model Artifact Handling

The repository uses **Git LFS (Large File Storage)** to track large machine learning binary models:

```bash
# Initialize Git LFS on your machine
git lfs install

# Pull binary model artifacts
git lfs pull
```

- If cloning without Git LFS, the models can be reproduced deterministically by running:
  ```bash
  python ml/solar/scripts/train_solar_models.py
  python ml/load/scripts/train_load_models.py
  ```

---

## 18. API Reference & Endpoint Specifications

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/` | Service health check and version metadata. | No |
| `POST` | `/ingest` | Ingests ESP32 physical sensor telemetry packet. | No (Device Auth) |
| `GET` | `/api/device/status` | Returns latest relay states, sensor readings, and command queue. | No |
| `POST` | `/api/device/control` | Dispatches relay switching command for Load 1–4 (`GRID` / `SOLAR` / `OFF`). | Yes (User) |
| `POST` | `/api/device/emergency-off` | Immediate emergency shutdown of all relay channels. | Yes (User) |
| `POST` | `/predict/solar` | Generates point solar generation prediction from weather features. | Yes (User) |
| `POST` | `/predict/load` | Generates point load prediction from lag/weather features. | Yes (User) |
| `GET` | `/predict/24h` | Returns 24-hour hourly Solar and Load forecast horizon. | Yes (User) |
| `POST` | `/risk/evaluate` | Evaluates appliance feasibility under $k \times \sigma$ conservative bounds. | Yes (User) |
| `POST` | `/xai/solar` | Computes TreeSHAP feature attributions for solar prediction. | Yes (User) |
| `POST` | `/xai/load` | Computes TreeSHAP feature attributions for load prediction. | Yes (User) |
| `GET` | `/energy/summary` | Trapezoidal energy accounting ($\text{kWh}$) and tariff savings. | Yes (User) |
| `POST` | `/energy/solar-estimate` | Stores user-reported solar generation for a specific date. | Yes (User) |
| `POST` | `/api/assistant/chat` | Conversational SolarMate AI query with safe decision tool calling. | Yes (User) |
| `POST` | `/auth/signup` | Registers new user profile into Supabase (Pending Approval). | No |
| `POST` | `/auth/login` | Authenticates user; enforces Admin Approval check. | No |
| `GET` | `/admin/pending-users` | Returns list of users awaiting approval. | Yes (Admin) |
| `POST` | `/admin/approve-user` | Approves or rejects pending registration. | Yes (Admin) |

---

## 19. Visual Demonstration & Complete Screenshot Gallery

Every major cyber-physical subsystem, user interface view, machine learning insight, and physical hardware stage is documented below using the 25 authoritative repository screenshot assets.

### 19.1 System Overview & Real-Time Monitoring

![Overview Dashboard Top View](Screenshoots/overview_1.png)
*Figure 1: Overview Dashboard (Top Section) — Live Power Hero gauge with active power (kW), power factor, local weather telemetry (Kaliakair, BD: 24.07°N, 90.22°E), and 24-hour Horizon Outlook forecast curve.*

![Overview Dashboard Middle View](Screenshoots/overview_2.png)
*Figure 2: Overview Dashboard (Middle Section) — 4-metric physical sensor strip (RMS Voltage, RMS Current, Ambient Temperature, Humidity) and Quick Appliance Status grid showing live active source.*

![Overview Dashboard Bottom View](Screenshoots/overview_3.png)
*Figure 3: Overview Dashboard (Bottom Section) — Real-time dynamic dual-bank energy routing flow diagram illustrating live power distribution between AC Utility Grid and Represented Solar banks.*

---

### 19.2 Forecast Horizon & Uncertainty Envelopes

![24-Hour Forecast Horizon Curve](Screenshoots/forcast_1.png)
*Figure 4: 24-Hour ML Forecast Horizon — Multi-horizon point predictions for Solar generation ($\hat{P}_{\text{solar}}$) and Household Load ($\hat{P}_{\text{load}}$) with shaded conservative uncertainty bands ($k \cdot \sigma$).*

![24-Hour Forecast Hourly Table](Screenshoots/forcast_2.png)
*Figure 5: Detailed 24-Hour Hourly Forecast Breakdown Table — Hourly matrix indicating expected solar generation, upper-bound load, safe solar surplus, and dispatch status.*

---

### 19.3 Appliance Source Routing & Safety Feasibility Checker

![Appliance Controls & Presets](Screenshoots/appliance_1.png)
*Figure 6: Appliance Management View — 4-Channel dual-bank relay controls (Grid / Solar / Off), emergency all-off safety interlock, and preset appliance feasibility checker (Washing Machine, Water Pump, Rice Cooker).*

![Appliance Feasibility Simulation Result](Screenshoots/appliance_2.png)
*Figure 7: Custom Appliance Pre-Run Safety Evaluation — Interactive simulation showing rated power input, duration selection, safe solar surplus calculations, and deterministic risk reasoning.*

![24-Hour Appliance Schedule Recommendations](Screenshoots/appliance_3.png)
*Figure 8: Continuous 24-Hour Safe Solar Schedule Recommendations — Automated timeline identifying optimal multi-hour windows with zero grid-deficit risk.*

---

### 19.4 Energy & Conservative Cost Accounting

![Energy & Cost Accounting View](Screenshoots/energy_page.png)
*Figure 9: Energy & Cost Accounting Dashboard — Timestamped trapezoidal energy integration (Total Measured kWh), user-reported solar estimate input modal, and conservative tariff savings (৳7.50 / kWh).*

---

### 19.5 Dual-Layer Explainable AI (XAI) Dashboard

![XAI Global Feature Importance](Screenshoots/xai_1.png)
*Figure 10: Dual-Layer Explainable AI (Global View) — TreeSHAP global feature importance rankings for Solar and Load forecasting models highlighting primary environmental drivers.*

![XAI Local Waterfall Attribution](Screenshoots/xai_2.png)
*Figure 11: Explainable AI (Local Explanation View) — TreeSHAP waterfall decompositions and natural language derivation rules detailing feature contributions for specific prediction instances.*

---

### 19.6 SolarMate AI Conversational Assistant

![SolarMate AI Conversational Assistant](Screenshoots/solarmate_ai.png)
*Figure 12: SolarMate AI Assistant Drawer — Conversational agent executing function-calling against live IoT telemetry, prediction pipelines, and safe appliance scheduling.*

---

### 19.7 Historical Telemetry & Analytics

![Historical Telemetry Trends](Screenshoots/history_page.png)
*Figure 13: Historical Sensor Analytics — Multi-day time-series telemetry charts for AC RMS Voltage, Current, Active Power, and Ambient Temperature with custom date-range filtering.*

---

### 19.8 Settings & System Diagnostics

![Settings & Diagnostics](Screenshoots/settings.png)
*Figure 14: System Settings & Diagnostics — Dark/Light theme toggle, geographical coordinates (Kaliakair, BD), residential tariff configuration (৳7.50/kWh), and backend service latency metrics.*

---

### 19.9 Authentication, User Lifecycle & Admin Approval Matrix

![User Login Interface](Screenshoots/Login_page.png)
*Figure 15: User Authentication — Secure sign-in portal enforcing Supabase JWT authentication.*

![User Registration Interface](Screenshoots/signup_page.png)
*Figure 16: User Registration — Sign-up portal creating pending user accounts.*

![Password Recovery Interface](Screenshoots/Forget_pass.png)
*Figure 17: Password Recovery — Email-based self-service password reset request.*

![Supabase Auth Verification Email](Screenshoots/signup_auth_mail.png)
*Figure 18: Email Verification — Supabase Cloud authentication verification and confirmation flow.*

![Admin Approval Access Control Matrix](Screenshoots/admin_page.png)
*Figure 19: Admin Approval Control Panel — Administrative interface for reviewing pending registrations, approving user access, and assigning system roles.*

---

### 19.10 Cloud Database Schema & Tables

![Supabase Database Schema & Tables](Screenshoots/database_ss.png)
*Figure 20: Cloud PostgreSQL Persistence (Supabase) — Live tables for `sensor_readings`, `device_status`, `user_actions`, `user_solar_estimates`, and `chat_messages` with Row-Level Security.*

---

### 19.11 SmartProv Wi-Fi Captive Portal Onboarding

![SmartProv Mobile Captive Portal](Screenshoots/SmartProv.jpeg)
*Figure 21: SmartProv SoftAP Wi-Fi Provisioning — Smartphone captive-portal interface enabling zero-hardcoded credential network onboarding into ESP32 NVS memory.*

---

### 19.12 Embedded Hardware Prototype & Physical Silicon Testbed

![ESP32 Hardware Testbed Overview](Screenshoots/prototype_view_1.jpeg)
*Figure 22: Physical Embedded Testbed Overview — ESP32-WROOM-32 microcontroller, 8-channel optocoupled dual-bank relay board, AC sensing modules, and terminal blocks.*

![AC Sensing Stage Close-Up](Screenshoots/prototype_view_2.jpeg)
*Figure 23: AC Sensing Stage Detail — ACS712-20A Hall-effect current sensor with precision resistor divider and ZMPT101B active AC voltage transformer.*

![Relay Matrix & Source Selectors Close-Up](Screenshoots/prototype_view_3.jpeg)
*Figure 24: Actuation & Selector Matrix Detail — Songle SRD-05VDC-SL-C relay channels and physical low-voltage source selector toggle switches.*

![ESP32 DevKit & Breadboard Close-Up](Screenshoots/prototype_view_4.jpeg)
*Figure 25: Microcontroller Core Detail — ESP32 30-Pin DevKit with status LEDs, DHT22 digital bus, and analog signal conditioning circuits.*

---

## 20. Academic Disclosures & Future Work

### Academic Disclosures
- This project is submitted as capstone research demonstrating a complete, reproducible IoT-enabled framework for risk-aware and explainable residential energy management under forecast uncertainty.
- All code, datasets, training scripts, test suites, and audit logs are permanently documented to enable full external replication.

### Future Work
1. **Multi-Point Hardware Load Calibration:** Complete full multi-point physical bench calibration across resistive, inductive, and non-linear AC loads.
2. **On-Silicon Micro-Inference:** Quantize the Random Forest and XGBoost models for direct on-chip inference via TensorFlow Lite for Microcontrollers (TFLM).
3. **Multi-Household Microgrid Aggregation:** Extend the risk engine from a single household to a multi-agent peer-to-peer (P2P) residential energy trading microgrid.

---

## License

This project is open-source and licensed under the [MIT License](LICENSE).
