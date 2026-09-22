# Dataset Provenance, Cleaning, and Preprocessing Protocols

**Document ID:** `Paper/04_Experimental_Setup/dataset_provenance_and_preprocessing.md`  
**Phase:** Phase 4 — Experimental Setup and Data Provenance  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Introduction and Multi-Regional Dataset Architecture

Intelligent residential energy management systems (HEMS) require high-fidelity empirical data capturing both renewable supply dynamics and stochastic domestic consumption. Developing robust machine-learning-driven HEMS introduces three core data-engineering challenges:
1. **Methodological Data Leakage:** Pervasive target circularity from contemporaneous physical electrical metrology or direct solar irradiance features in published literature;
2. **Temporal Continuity and Missing Data:** Intermittent hardware logging outages requiring gap-aware cleaning without artificial flatline interpolation; and
3. **Cold-Start Deployment Constraints:** Bootstrapping autoregressive feature pipelines before on-site edge history is accumulated.

To address these challenges under rigorous experimental controls, this research establishes a multi-regional data architecture integrating two independent historical datasets and live embedded metrology:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-REGIONAL DATASET ARCHITECTURE                             │
├────────────────────────────────────────────────────┬───────────────────────────────────┤
│ 1. UCI Household Electrical Load Benchmark         │ 2. Open-Meteo Solar Reanalysis    │
│    • Location: Sceaux, Paris, France               │    • Location: Kaliakair, BD      │
│    • Coordinates: 48.78°N, 2.29°E                  │    • Coordinates: 24.07°N, 90.22°E│
│    • Period: Dec 2006 – Nov 2010 (47 months)       │    • Period: Jan 2020 – Aug 2026  │
│    • Raw Records: 2,075,259 min / 34,168 hourly    │    • Raw Records: 58,056 hourly   │
│    • Cleaned Records: 32,656 hourly (94.4%)        │    • Valid Records: 58,056 (100%) │
│    • Split: 26,124 Train (80%) / 6,532 Test (20%)  │    • Split: 46,444 Train (80%) /  │
│    • Exogenous Feature: NASA POWER T2M Temp        │             11,612 Test (20%)     │
└────────────────────────┬───────────────────────────┴─────────────────┬─────────────────┘
                         │                                             │
                         ▼                                             ▼
       ┌─────────────────────────────────────────────────────────────────────────┐
       │ 3. Synthetic Cross-Regional Evaluation Pairing                          │
       │    • Decoupled Supply/Demand Simulation Testbed                         │
       │    • Aligned Across 176 Common (Hour-of-Day, Month-of-Year) Scenarios   │
       │    • Synchronous Decision Interval: Hourly Energy Balance (Δt = 1.0 h)  │
       │    • Explicit Disclosure: Academic Benchmark, Not Co-Located Microgrid  │
       └─────────────────────────────────────────────────────────────────────────┘
```

Table 1 summarizes the complete technical specifications, geographical coordinates, temporal partitions, and data roles across the evaluated corpora.

### Table 1: Comprehensive Specification of Evaluated Datasets

| Dataset Attribute | UCI Household Electrical Load | Open-Meteo Solar Reanalysis | Live ESP32 Edge Metrology | Synthetic Evaluation Pairing |
| :--- | :--- | :--- | :--- | :--- |
| **Geographical Location** | Sceaux, Île-de-France, France | Kaliakair, Gazipur, Bangladesh | Gazipur, Bangladesh | Synthetic Cross-Regional Pairing |
| **Geographic Coordinates** | $48.78^\circ\text{N}, 2.29^\circ\text{E}$, Elev. $68\text{ m}$ | $24.074^\circ\text{N}, 90.223^\circ\text{E}$, Elev. $18\text{ m}$ | Local Laboratory Testbed | Dual-Hemisphere Decoupled Pairing |
| **Temporal Coverage** | Dec 16, 2006 $\rightarrow$ Nov 26, 2010 ($47\text{ mo.}$) | Jan 01, 2020 $\rightarrow$ Aug 15, 2026 ($6.6\text{ yr}$) | Live Hardware Deployment Sessions | Multi-Year Retrospective Simulation |
| **Native Sampling Rate** | $1\text{-minute}$ electrical telemetry | Quasi-hourly ($60 \pm 1\text{ min}$ jitter) | $200\text{ ms}$ burst / $3\text{ s}$ telemetry push | Synchronous $1\text{-hour}$ decision step |
| **Raw Sample Count** | $2,075,259\text{ min}$ ($34,168$ hourly) | $58,056$ quasi-hourly records | Session-dependent ($>3,000$ rows) | $34,168$ Load / $58,056$ Solar |
| **Missing Gaps / Outages** | $8$ multi-hour gaps ($421\text{ missing hours}$) | $0$ multi-hour gaps ($0\text{ missing records}$) | Transient network retry buffering | Gap-aware non-interpolated filtering |
| **Clean Analytical Records** | **$32,656$ records** ($94.4\%$ retention) | **$58,056$ records** ($100\%$ retention) | Persistent NVS and cloud PostgreSQL | $176$ common calendar scenarios |
| **Chronological Split** | Train: **$26,124$** ($80\%$) / Test: **$6,532$** ($20\%$) | Train: **$46,444$** ($80\%$) / Test: **$11,612$** ($20\%$) | Real-time live inference | Strict forward holdout (`shuffle=False`) |
| **Target Variable** | `Global_active_power` ($P_{\text{load}}$, kW) | Modeled Solar Output ($P_{\text{solar}}$, kW) | Discrete RMS Active Power ($P$, W) | Safe Surplus ($S_{\text{safe}}$, kW) |
| **Primary Scientific Role** | Autoregressive load forecasting | Exogenous solar PV forecasting | Embedded edge metrology validation | Risk-aware admission gating |

---

## 2. Residential Household Load Dataset (UCI Sceaux, France)

### 2.1 Dataset Provenance and Raw Electrical Telemetry
The benchmark domestic electrical consumption dataset is obtained from the landmark UCI Machine Learning Repository *Individual Household Electric Power Consumption* archive. The raw dataset comprises $2,075,259$ sub-minute electrical records collected from a single detached residential household in Sceaux, France, spanning 47 consecutive months from December 16, 2006 to November 26, 2010.

Each sub-minute raw observation logs seven physical parameters:
1. `Global_active_power`: Household total active power ($P$, in kilowatts);
2. `Global_reactive_power`: Household total reactive power ($Q$, in kilovolt-amperes reactive);
3. `Voltage`: Minute-averaged terminal AC voltage ($V$, in volts);
4. `Global_intensity`: Household total current intensity ($I$, in amperes);
5. `Sub_metering_1`: Active energy consumed by kitchen appliances (dishwasher, microwave, oven; in watt-hours);
6. `Sub_metering_2`: Active energy consumed by laundry appliances (washing machine, tumble dryer, refrigerator, light; in watt-hours);
7. `Sub_metering_3`: Active energy consumed by electric space and water heating appliances (in watt-hours).

To match the operational decision interval of grid-tied residential energy management, sub-minute telemetry is aggregated into hourly arithmetic means, yielding a raw time-series of $N_{\text{raw}} = 34,168$ hourly records spanning December 23, 2006 17:00:00 to November 26, 2010 21:00:00. In addition, the dataset is joined with hourly historical 2-meter air temperature ($T2M$, in $^\circ\text{C}$) extracted from the NASA Prediction of Worldwide Energy Resources (POWER) reanalysis database for the exact geographic coordinates of Sceaux ($48.78^\circ\text{N}, 2.29^\circ\text{E}$).

### 2.2 Gap Inventory and Gap-Aware Cleaning Protocol
A perfectly continuous hourly grid from December 23, 2006 00:00 to November 26, 2010 21:00 comprises $N_{\text{grid}} = 34,589$ hours. The raw aggregated dataset exhibits $421$ missing hourly intervals ($1.23\%$ missing rate) distributed across eight discrete multi-hour outage episodes ($\ge 12\text{ hours}$), summarized in Table 2.

### Table 2: Raw UCI Household Load Missing Data Gap Inventory

| Gap ID | Outage Start Timestamp | Outage End Timestamp | Outage Duration | Probable Cause |
| :---: | :---: | :---: | :---: | :---: |
| **G1** | 2007-01-28 17:00:00 | 2007-01-29 08:00:00 | $16\text{ hours}$ | Submeter maintenance / sensor disconnect |
| **G2** | 2007-04-28 01:00:00 | 2007-04-30 14:00:00 | $62\text{ hours}$ | Long weekend / multi-day logging power loss |
| **G3** | 2007-06-25 18:00:00 | 2007-06-26 12:00:00 | $19\text{ hours}$ | Data logger memory buffer overflow |
| **G4** | 2009-06-13 22:00:00 | 2009-06-15 05:00:00 | $32\text{ hours}$ | Gateway hardware fault |
| **G5** | 2009-08-13 14:00:00 | 2009-08-14 11:00:00 | $22\text{ hours}$ | Summer maintenance shutdown |
| **G6** | 2010-01-12 18:00:00 | 2010-01-13 12:00:00 | $19\text{ hours}$ | Winter storm power disruption |
| **G7** | 2010-03-20 16:00:00 | 2010-03-21 11:00:00 | $20\text{ hours}$ | Network switch reboot / comms outage |
| **G8** | 2010-08-17 14:00:00 | 2010-08-22 16:00:00 | **$123\text{ hours}$** ($\approx 5.1\text{ days}$) | Extended summer holiday logging failure |
| **Total** | — | — | **$421\text{ missing hours}$** | Distributed across 47 calendar months |

**Rejection of Artificial Flatline Interpolation:** Standard imputation practices (e.g., forward-filling, backward-filling, or linear spline interpolation) across multi-day outages (such as Gap G8, spanning 123 consecutive hours) artificially synthesize flatlines that distort genuine diurnal human consumption patterns. Furthermore, forward-filling across a 5.1-day boundary corrupts weekly autoregressive lags (such as $P_{t-168}$), propagating invalid historical values into predictive models.

**The Gap-Aware Filtering Protocol:**
1. A continuous hourly datetime index spanning the complete 47-month horizon ($N_{\text{grid}} = 34,589$) is instantiated.
2. Missing timestamps are reindexed and marked as explicit IEEE 754 floating-point `NaN` values.
3. Autoregressive lags ($P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}$) and shifted rolling window statistics are computed strictly on the continuous datetime index.
4. Any feature row containing one or more `NaN` values (originating from initial 168-hour boundary burn-in or missing outage spans) is discarded without imputation.

This protocol retains **$N_{\text{clean}} = 32,656$ non-interpolated hourly records** ($94.4\%$ of the temporal timeline), ensuring that every training and testing row is formed entirely from genuine physical sensor readings.

### 2.3 Identification and Remediation of Target Leakage

#### Hazard 1: Contemporaneous Physical Metrology Leakage
In several published residential load forecasting studies, instantaneous electrical measurements—specifically terminal Voltage ($V_t$) and total current Global Intensity ($I_t$)—are included as predictors for active power ($P_t$). However, active power is physically defined by Ohm's and Joule's laws:
$$P_t = V_t \cdot I_t \cdot \cos(\theta_t)$$
where $\cos(\theta_t)$ is the instantaneous displacement power factor. Because AC voltage in residential distribution is tightly regulated near nominal $230\text{ V}$, active power and current intensity share an empirical Pearson correlation of $r = 0.999$.

Including $V_t$ or $I_t$ in the feature vector creates a trivial identity mapping rather than a true forecast. In our diagnostic audit, an intentionally leaky Random Forest model trained with contemporaneous $(V_t, I_t)$ achieved an artificially perfect $R^2 = 0.999335$ and $\text{MAE} = 0.0159\text{ kW}$. In an operational deployment, future current $I_{t+h}$ is physically unmeasurable prior to appliance activation, rendering such models unusable. Consequently, contemporaneous physical metrology variables are **strictly purged** from the feature set.

#### Hazard 2: Unshifted Rolling Window Lookahead Bias
A more subtle, pervasive vulnerability arises when computing moving averages or rolling volatilities. If a 24-hour backward rolling window is computed on an unshifted series:
$$\text{RollingMean}_{24}(t) = \frac{1}{24} \sum_{i=0}^{23} P_{t-i} = \frac{1}{24} P_t + \frac{1}{24} \sum_{i=1}^{23} P_{t-i}$$
The input feature contains $\frac{1}{24} \approx 4.17\%$ of the ground-truth target $P_t$, introducing direct lookahead contamination. In our diagnostic audit, a linear regression model trained on unshifted rolling features achieved an inflated $R^2 = 0.9928$. Once strictly shifted using pandas `.shift(1).rolling(24).mean()`, performance dropped to honest $R^2 = 0.5313$.

### 2.4 Authoritative Non-Leaky Load Feature Vector ($\mathbf{x}_{\text{load}} \in \mathbb{R}^{16}$)
To eliminate all leakage while maximizing autoregressive predictive power, the load forecasting pipeline restricts inputs strictly to 16 causal features:

$$\mathbf{x}_{\text{load}}(t) = \begin{bmatrix} P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}, \\ \mu_{3\text{h}}(t), \mu_{24\text{h}}(t), \sigma_{24\text{h}}(t), \mu_{168\text{h}}(t), \\ h_t, \text{DoW}_t, m_t, \mathbb{I}_{\text{weekend}}(t), T_{2\text{m}}(t) \end{bmatrix}^T \in \mathbb{R}^{16}$$

1. **Short-Term Autoregressive Lags (3 features):** $P_{t-1}, P_{t-2}, P_{t-3}$ capturing recent appliance operational state and thermal momentum.
2. **Semi-Diurnal Autoregressive Lag (1 feature):** $P_{t-12}$ capturing 12-hour sub-daily activity patterns.
3. **Diurnal Autoregressive Lags (2 features):** $P_{t-24}, P_{t-48}$ capturing consumer routine 1 and 2 days prior at the identical hour.
4. **Weekly Seasonality Lag (1 feature):** $P_{t-168}$ capturing identical-hour lifestyle routines on the same day of the preceding week.
5. **Shifted Rolling Statistics (4 features):**
   - Short-term trend: $\mu_{3\text{h}}(t) = \frac{1}{3} \sum_{i=1}^3 P_{t-i}$;
   - Daily baseload: $\mu_{24\text{h}}(t) = \frac{1}{24} \sum_{i=1}^{24} P_{t-i}$;
   - Daily volatility: $\sigma_{24\text{h}}(t) = \sqrt{\frac{1}{23} \sum_{i=1}^{24} \left(P_{t-i} - \mu_{24\text{h}}(t)\right)^2}$;
   - Weekly moving average: $\mu_{168\text{h}}(t) = \frac{1}{168} \sum_{i=1}^{168} P_{t-i}$.
6. **Calendar Encodings (4 features):** Hour-of-day ($h_t \in [0, 23]$), day-of-week ($\text{DoW}_t \in [0, 6]$), calendar month ($m_t \in [1, 12]$), and binary weekend indicator ($\mathbb{I}_{\text{weekend}} \in \{0, 1\}$).
7. **Exogenous Meteorological Input (1 feature):** Historical 2-meter air temperature ($T_{2\text{m}} \in \mathbb{R}$, $^\circ\text{C}$). In SHAP feature attribution audits, $T_{2\text{m}}$ contributes $2.5\%$ of model attribution; its inclusion provides seasonal heating demand correlation without introducing target leakage.

### 2.5 Chronological Partitioning and Statistical Properties
Random shuffling (`train_test_split(shuffle=True)`) is strictly prohibited to prevent temporal autocorrelation leakage. The cleaned load dataset ($N_{\text{clean}} = 32,656$) is partitioned using a strict forward chronological split, providing chronological out-of-sample evaluation without intentional train/test temporal shuffling:
- **Training Partition ($80\%$):** $N_{\text{train}} = 26,124$ hourly records (December 23, 2006 17:00:00 $\rightarrow$ January 27, 2010 18:00:00).
- **Testing Partition ($20\%$):** $N_{\text{test}} = 6,532$ hourly records (January 27, 2010 19:00:00 $\rightarrow$ November 26, 2010 21:00:00).

Table 3 details the descriptive statistical parameters across each stage of dataset preparation.

### Table 3: Descriptive Statistics of Household Active Power Demand ($P_{\text{load}}$, kW)

| Data Partition | Sample Count ($N$) | Mean (kW) | Std Dev (kW) | Median (kW) | IQR (kW) | Min (kW) | Max (kW) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Raw Aggregated** | $34,168$ | $1.0911$ | $0.9124$ | $0.8120$ | $1.1540$ | $0.0760$ | $6.4210$ |
| **Cleaned Non-Leaky** | $32,656$ | $1.0924$ | $0.9138$ | $0.8140$ | $1.1560$ | $0.0760$ | $6.4210$ |
| **Training Partition ($80\%$)** | $26,124$ | $1.0882$ | $0.9152$ | $0.8060$ | $1.1520$ | $0.0760$ | $6.4210$ |
| **Testing Partition ($20\%$)** | $6,532$ | $1.1092$ | $0.9081$ | $0.8460$ | $1.1680$ | $0.0780$ | $6.2180$ |

### 2.6 Short-History Cold-Start Operational Strategy
Because the full feature vector requires lag history up to $t-168$ ($7\text{ days}$), a physical edge device deployed in a new residence initially lacks historical telemetry. To avoid operational stalls or catastrophic zero-predictions, the backend implements a deterministic benchmark profile fallback:
$$\bar{\mathcal{F}}_{\text{fallback}}(m, d, h) = \mathbb{E}\left[ \mathbf{x}_{\text{load}} \;\middle|\; \text{month}=m, \; \text{DoW}=d, \; \text{hour}=h \right]$$
Precomputed conditional expectations derived from the historical training partition populate unobserved lag entries until genuine live telemetry accumulates. Live sensor readings take immediate precedence over fallback values, and fallback values are never written to the persistent database.

---

## 3. Solar Meteorological Reanalysis Dataset (Kaliakair, Bangladesh)

### 3.1 Geographical Provenance and Archive Pipeline
Solar energy supply dynamics are modeled using multi-year meteorological timeseries acquired from the Open-Meteo Historical Weather API for Kaliakair, Gazipur District, Bangladesh ($24.074^\circ\text{N}, 90.223^\circ\text{E}$, elevation $18\text{ m}$). The dataset spans 6.6 consecutive years from **January 1, 2020 00:00:00 to August 15, 2026 23:00:00**, totaling exactly **$N = 58,056$ quasi-hourly records** spanning $2,419$ complete calendar days ($24\text{ records/day}$).

The Open-Meteo archive extracts atmospheric variables from the European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5-Land reanalysis model, which provides continuous numerical atmospheric reconstructions on an enhanced $0.1^\circ \times 0.1^\circ$ ($\approx 9\text{ km}$) spatial grid.

**Discretization Jitter Disclosure:** An empirical audit of the exported timestamps reveals a deterministic sampling jitter: intervals alternate in a repeating $59\text{m} \to 61\text{m} \to 60\text{m}$ sequence. Crucially, there are zero missing hours, zero multi-hour gaps, and exactly 24 observations for every calendar day. Chronological splitting is executed strictly on row indices.

The raw meteorological timeseries provides nine parameters:
- `temperature_2m`: Dry-bulb air temperature at 2 meters ($^\circ\text{C}$);
- `relative_humidity_2m`: Relative humidity at 2 meters ($\%$);
- `cloud_cover`: Total cloud cover fraction ($0\text{--}100\%$);
- `wind_speed_10m`: Wind speed at 10 meters above ground ($\text{m/s}$);
- `shortwave_radiation`: Downward global horizontal solar radiation ($\text{W/m}^2$);
- `direct_radiation`: Direct beam solar radiation on horizontal plane ($\text{W/m}^2$);
- `diffuse_radiation`: Diffuse horizontal solar radiation ($\text{W/m}^2$);
- `direct_normal_irradiance`: Direct beam radiation perpendicular to solar rays ($\text{W/m}^2$);
- `global_tilted_irradiance`: Total solar irradiance on tilted PV panel surface ($\text{GTI}$, $\text{W/m}^2$).

### 3.2 Photovoltaic System Parameterization (5-Panel Monocrystalline Array)
To ground meteorological irradiance in domestic engineering reality, a standardized residential rooftop photovoltaic installation is modeled. The system models a $2.115\text{ kWp}$ DC array comprising five commercial monocrystalline silicon modules.

Table 4 details the verified physical, optical, and electrical parameter specifications.

### Table 4: Physical and Electrical Parameters of the Rooftop Solar PV Installation

| Parameter Symbol | Physical Specification Description | Value & Units | Engineering Basis / Standard |
| :---: | :--- | :---: | :--- |
| $N_{\text{panels}}$ | Number of Photovoltaic Modules | **$5\text{ Panels}$** | Standard residential single-phase inverter limit |
| $A_{\text{panel}}$ | Single Module Collector Aperture Area | **$2.42\text{ m}^2$** | Commercial $550\text{ Wp}$ module ($2.28\text{ m} \times 1.06\text{ m}$) |
| $A_{\text{total}}$ | Gross Total Array Collector Area | **$12.10\text{ m}^2$** | Total rooftop solar aperture ($5 \times 2.42\text{ m}^2$) |
| $\eta$ | Nominal Module Conversion Efficiency | **$0.19$ ($19.0\%$)** | Monocrystalline silicon at Standard Test Conditions (STC) |
| $PR$ | System Performance Ratio | **$0.92$ ($92.0\%$)** | MPPT tracking, DC wiring, inverter, and dust derating |
| $\beta$ | Fixed Array Tilt Angle | **$24.0^\circ$** | Optimally matched to local latitude ($24.07^\circ\text{N}$) |
| $\gamma$ | Surface Azimuth Orientation | **$180.0^\circ$ (True South)** | Maximum annual solar capture in Northern Hemisphere |
| $P_{\text{peak}}$ | Modeled Peak DC Array Capacity | **$2.115\text{ kWp}$** | Peak DC power under STC ($1000\text{ W/m}^2, 25^\circ\text{C}$) |

### 3.3 Solar Generation Target Formulation and Target Circularity Elimination
Using the physical parameters from Table 4, the synthetic ground-truth photovoltaic active power generation ($P_{\text{solar}}$, kW) is deterministically generated from Global Tilted Irradiance ($\text{GTI}$):

$$P_{\text{solar}}(t) = \frac{\text{GTI}(t) \cdot A_{\text{panel}} \cdot \eta \cdot PR \cdot N_{\text{panels}}}{1000}$$

Substituting verified values:
$$P_{\text{solar}}(t) = \frac{\text{GTI}(t) \cdot 2.42 \cdot 0.19 \cdot 0.92 \cdot 5}{1000} = \text{GTI}(t) \times \mathbf{0.00211508}\text{ kW}$$

Across the $58,056$ records, modeled solar generation exhibits a mean of $0.4315\text{ kW}$, a standard deviation of $0.5471\text{ kW}$, a peak generation of $2.0106\text{ kW}$, and $27,225$ nighttime inactive hours ($P_{\text{solar}} = 0\text{ kW}$, accounting for $46.89\%$ zero-power mass).

**Elimination of Target Circularity:** Because the target $P_{\text{solar}}$ is mathematically calculated from $\text{GTI}$, feeding $\text{GTI}$ (or collinear irradiance features like DNI or direct horizontal radiation) into the machine learning model creates an artificial identity mapping. An intentionally circular model trained with $\text{GTI}$ achieved $R^2 = 1.000000$ and $\text{MAE} = 0.000068\text{ kW}$, simply memorizing the constant multiplier $0.002115$.

In real-world operations, ground-level pyranometer irradiance 24 hours ahead is unobtainable. Therefore, all irradiance variables ($\text{GTI}$, `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`, `direct_normal_irradiance`) are **strictly quarantined**. The model is constrained to predict solar generation exclusively from forecastable atmospheric variables and solar calendar geometry:

$$\mathbf{x}_{\text{solar}}(t) = \begin{bmatrix} \text{cloud\_cover}(t), \text{temperature}(t), \text{relative\_humidity}(t), \text{wind\_speed}(t), \\ h_t, m_t, \text{day\_of\_year}_t \end{bmatrix}^T \in \mathbb{R}^7$$

### 3.4 Chronological Partitioning
The solar dataset is partitioned chronologically without shuffling:
- **Training Partition ($80\%$):** $N_{\text{train}} = 46,444$ hourly records (January 1, 2020 00:00:00 $\rightarrow$ April 19, 2025 03:00:00).
- **Testing Partition ($20\%$):** $N_{\text{test}} = 11,612$ hourly records (April 19, 2025 03:59:00 $\rightarrow$ August 15, 2026 23:00:00).

Table 5 provides the descriptive statistics of modeled solar generation across partitions.

### Table 5: Descriptive Statistics of Modeled Solar Generation ($P_{\text{solar}}$, kW)

| Data Partition | Sample Count ($N$) | Mean (kW) | Std Dev (kW) | Median (kW) | Daylight Mean ($P>0$) | Max (kW) | Zero Mass ($\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Complete Dataset** | $58,056$ | $0.4315$ | $0.5471$ | $0.0988$ | $0.8124\text{ kW}$ | $2.0106$ | $46.89\%$ |
| **Training Split ($80\%$)** | $46,444$ | $0.4318$ | $0.5474$ | $0.0991$ | $0.8128\text{ kW}$ | $2.0106$ | $46.88\%$ |
| **Testing Split ($20\%$)** | $11,612$ | $0.4304$ | $0.5459$ | $0.0975$ | $0.8109\text{ kW}$ | $2.0084$ | $46.92\%$ |

---

## 4. Synthetic Cross-Regional Evaluation Pairing Protocol

### 4.1 Pairing Rationale and Scenario Alignment
Because real-world co-located microgrid deployments capturing multi-year high-resolution domestic load alongside localized rooftop solar generation are rare in developing regions, this research couples the French household load profile with Bangladeshi solar generation in a synthetic cross-regional evaluation testbed.

The synthetic coupling is aligned along two cyclic calendar coordinates:
1. **Hour-of-Day ($h \in [0, 23]$):** Preserves diurnal lifestyle alignment (e.g., matching midday solar peaks with domestic midday demand profiles);
2. **Month-of-Year ($m \in [1, 12]$):** Captures seasonal climate interactions (e.g., European winter heating paired with South Asian dry-season solar peaks).

Filtering for complete overlapping pairs produces **176 unique common $(h, m)$ calendar scenarios** across the evaluation horizon.

### 4.2 Explicit Academic Disclosures and Limitations
In accordance with scientific rigor, the methodological limitations of this pairing are explicitly stated:
1. **Non-Co-Location:** Sceaux, France ($48.78^\circ\text{N}$) and Kaliakair, Bangladesh ($24.07^\circ\text{N}$) experience distinct climates, solar zenith angles, and cultural activity cycles. The synthetic pairing serves as a computational evaluation testbed to benchmark non-circular forecasting algorithms and risk-aware admission gating; it is not a physical co-located microgrid measurement.
2. **Reanalysis vs. Operational Numerical Weather Prediction (NWP):** Historical ERA5-Land reanalysis provides spatially interpolated atmospheric data that is inherently smoother than operational, turbulent live weather forecasts.
3. **Extreme Conservatism in Synthetic Setting:** When compounding solar safety margins ($k \cdot \sigma_{\text{solar}}$) with load demand buffers ($k \cdot \sigma_{\text{load}}$) across 176 synthetic pairs, the system produces zero ALLOW decisions for high-wattage appliances ($1.2\text{ kW}$) at $k \ge 1.0$. This demonstrates rigorous fail-safe conservatism in a decoupled setting, prioritizing grid stability over speculative switching.

---

## 5. Data Hygiene, Quality Assurance, and Leakage Prevention Audit Matrix

Table 6 provides a comprehensive traceability matrix documenting feature transformations, potential leakage hazards, and empirical verification evidence.

### Table 6: Comprehensive Data Leakage and Preprocessing Audit Matrix

| Domain | Feature Name | Representation / Formula | Leakage Risk / Vulnerability | Remediation Protocol | Empirical Audit Evidence |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **Solar** | $\text{GTI}$ | $\text{GTI}(t) \text{ [W/m}^2\text{]}$ | Target circularity ($P_{\text{PV}} \propto \text{GTI}$) | Strictly quarantined from $\mathbf{x}_{\text{solar}}$ | Leaky $R^2 = 1.0000 \to$ Honest $R^2 = 0.9547$ |
| **Solar** | Direct / Diffuse Rad | $\text{DNI}(t), \text{GHI}(t) \text{ [W/m}^2\text{]}$ | Collinear with target formula | Strictly quarantined from $\mathbf{x}_{\text{solar}}$ | Verification report confirms zero radiation inputs |
| **Solar** | Weather Features | Cloud, Temp, Humidity, Wind | None (Exogenous NWP inputs) | Included in $\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$ | SHAP direction: cloud inhibitory ($\text{corr} = -0.758$) |
| **Solar** | Calendar Angles | Hour, Month, Day of Year | None (Deterministic astronomical) | Included in $\mathbf{x}_{\text{solar}} \in \mathbb{R}^7$ | SHAP captures diurnal bell curve ($10\times$ signal) |
| **Load** | Voltage ($V_t$) | Instantaneous AC Volts ($V_t$) | Near-deterministic $P = V \cdot I \cos\theta$ | Strictly purged from $\mathbf{x}_{\text{load}}$ | Eliminates leaky model ($R^2 = 0.9993$) |
| **Load** | Current ($I_t$) | Global Intensity ($I_t$) | Direct physical target proxy | Strictly purged from $\mathbf{x}_{\text{load}}$ | Verifies no contemporaneous current input |
| **Load** | Sub-metering | $\text{Sub}_1, \text{Sub}_2, \text{Sub}_3$ | Contemporaneous load breakdown | Strictly purged from $\mathbf{x}_{\text{load}}$ | Ensures purely autoregressive formulation |
| **Load** | Rolling Mean 24h | $\frac{1}{24}\sum_{i=1}^{24} P_{t-i}$ | Unshifted lookahead ($4.17\%$ target) | Strictly shifted: `.shift(1).rolling(24)` | Leaky $R^2 = 0.9928 \to$ Honest $R^2 = 0.5313$ |
| **Load** | Autoregressive Lags | $P_{t-1}, P_{t-2}, P_{t-3}, P_{t-12}, P_{t-24}, P_{t-48}, P_{t-168}$ | Lookahead if index unaligned | Continuous datetime index reindexed | Causal memory verified; $P_{t-1}$ dominates ($\text{corr} = +0.98$) |
| **Load** | Ambient Temp ($T_{2\text{m}}$) | ERA5 / POWER reanalysis ($^\circ\text{C}$) | Same-hour reanalysis observation | Retained as exogenous; $2.5\%$ SHAP | Negative heating correlation confirmed |
| **Load** | Missing Gaps | 8 gaps ($421\text{ missing hours}$) | Flatline distortion if interpolated | Gap-aware NaN dropping ($N=32,656$) | Retains $94.4\%$ genuine historical records |
