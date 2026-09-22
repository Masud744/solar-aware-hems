# Phase 3: Mathematical Formulations and Algorithmic Specifications

**Document ID:** `Paper/03_Research_Questions_and_Methodology/mathematical_formulation.md`  
**Phase:** Phase 3 — Research Questions, System Architecture & Mathematical Formulation  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Baseline:** `Project_Report/final_report/` (Chapters 3, 4)  

---

## 1. Physical Photovoltaic Generation Modeling

In the absence of utility-grade physical pyranometers at consumer residential installations, the baseline solar generation potential is derived from thermodynamic equations parameterizing a rooftop monocrystalline photovoltaic array.

### 1.1 Physical Photovoltaic Conversion Equation
The theoretical instantaneous electric power generation $P_{\text{PV}}(t)$ (kW) generated from solar irradiance is formulated as:
\begin{equation}
P_{\text{PV}}(t) = \frac{\text{GTI}(t) \cdot A_{\text{panel}} \cdot \eta_{\text{panel}} \cdot \text{PR} \cdot N_{\text{panels}}}{1000}
\label{eq:physical_pv_power}
\end{equation}
where:
- $\text{GTI}(t)$ is the Global Tilted Irradiance ($\text{W/m}^2$) incident on the plane of the array at timestamp $t$;
- $A_{\text{panel}}$ is the active surface area per photovoltaic module ($\text{m}^2$);
- $\eta_{\text{panel}}$ is the nominal module conversion efficiency at Standard Test Conditions (STC: $1000\text{ W/m}^2$, $25^\circ\text{C}$, AM 1.5);
- $\text{PR}$ is the balance-of-system Performance Ratio (accounting for inverter conversion losses, thermal derating, wiring resistance, and module soiling);
- $N_{\text{panels}}$ is the total number of installed solar panels;
- $1000$ is the dimensional scaling factor converting Watts to kilowatts (kW).

### 1.2 System Parameterization Constants
The physical array parameters implemented across this project reflect a standard residential rooftop installation:
\begin{equation}
A_{\text{panel}} = 2.42\text{ m}^2, \quad A_{\text{total}} = N_{\text{panels}} \times A_{\text{panel}} = 5 \times 2.42\text{ m}^2 = \mathbf{12.10\text{ m}^2}, \quad \eta_{\text{panel}} = 0.19, \quad \text{PR} = 0.92, \quad N_{\text{panels}} = 5
\end{equation}

#### Derived Array Electrical Specifications:
1. **Nameplate Peak Capacity per Module ($P_{\text{STC, module}}$):**
   $$P_{\text{module}} = 1000\text{ W/m}^2 \times 2.42\text{ m}^2 \times 0.19 = 459.8\text{ Wp} \quad (\text{Nominal rating: } \approx 423\text{--}460\text{ Wp})$$
2. **Gross Total Array Peak Capacity ($P_{\text{peak, array}}$):**
   $$P_{\text{array}} = 5 \times 423\text{ Wp} \approx \mathbf{2.115\text{ kWp}} \quad (\text{over } A_{\text{total}} = 12.10\text{ m}^2 \text{ total collector area})$$
3. **Target Label Construction Disclosure:** In the historical meteorological archive for Kaliakair, Bangladesh (2020–2026; 58,056 records), Equation~\eqref{eq:physical_pv_power} was evaluated using ERA5-Land reanalysis GTI to establish the ground-truth target variable $P_{\text{target}}(t)$. In accordance with Master Guardrail #4, contemporaneous GTI is strictly quarantined and excluded from all predictive input features to prevent target circularity.

---

## 2. Non-Circular & Non-Leaky Machine Learning Forecasting Formulations

The predictive forecasting pipeline formulates two independent regression tasks over discrete hourly steps $t$:
\begin{align}
\hat{P}_{\text{solar}}(t) &= f_{\text{solar}}\left(\mathbf{x}_{\text{solar}}(t); \; \boldsymbol{\theta}_{\text{solar}}\right), \quad \mathbf{x}_{\text{solar}}(t) \in \mathbb{R}^7 \\
\hat{P}_{\text{load}}(t) &= f_{\text{load}}\left(\mathbf{x}_{\text{load}}(t); \; \boldsymbol{\theta}_{\text{load}}\right), \quad \mathbf{x}_{\text{load}}(t) \in \mathbb{R}^{16}
\end{align}

### 2.1 Solar Feature Engineering Vector ($\mathbf{x}_{\text{solar}}$)
To eliminate target circularity ([Gap 1](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-1-target-circularity-and-pyranometer-dependency-in-solar-forecasting)), $\mathbf{x}_{\text{solar}}(t)$ is constructed exclusively from forecastable atmospheric variables and solar geometry:
\begin{equation}
\mathbf{x}_{\text{solar}}(t) = \begin{bmatrix}
c_t \\
T_{2\text{m}}(t) \\
RH(t) \\
WS_{10\text{m}}(t) \\
\sin\left(\frac{2\pi \cdot h_t}{24}\right) \\
\cos\left(\frac{2\pi \cdot h_t}{24}\right) \\
\sin\left(\frac{2\pi \cdot d_t}{365}\right)
\end{bmatrix} \in \mathbb{R}^7
\label{eq:solar_feature_vector}
\end{equation}
where $c_t \in [0, 100]\%$ is total cloud cover, $T_{2\text{m}}$ is 2-meter ambient temperature ($^\circ\text{C}$), $RH \in [0, 100]\%$ is relative humidity, $WS_{10\text{m}}$ is 10-meter wind speed ($\text{m/s}$), $h_t \in [0, 23]$ is diurnal clock hour, and $d_t \in [1, 365]$ is day-of-year index. All contemporaneous irradiance metrics ($\text{GTI}_t, \text{DNI}_t, \text{DHI}_t$) are quarantined.

### 2.2 Load Feature Engineering Vector ($\mathbf{x}_{\text{load}}$)
To eliminate contemporaneous metrology leakage ([Gap 2](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-2-contemporaneous-metrology-leakage-in-single-household-load-forecasting)), all concurrent measurements ($V_t, I_t, \text{Sub}_i$) are purged. The feature vector relies strictly on causal autoregressive lags, unshifted historical rolling statistics, calendar encodings, and exogenous temperature, comprising 16 features:
\begin{equation}
\mathbf{x}_{\text{load}}(t) = \begin{bmatrix}
P_{t-1}, \; P_{t-2}, \; P_{t-3} & \text{(Short-Term Causal Lags)} \\
P_{t-12} & \text{(Half-Day Periodicity Lag)} \\
P_{t-24}, \; P_{t-48} & \text{(Diurnal Cycle Lags)} \\
P_{t-168} & \text{(Weekly Seasonality Lag)} \\
\mu_{3\text{h}}(t-1) = \frac{1}{3}\sum_{k=1}^3 P_{t-k} & \text{(Unshifted 3-Hour Mean)} \\
\mu_{24\text{h}}(t-1) = \frac{1}{24}\sum_{k=1}^{24} P_{t-k} & \text{(Unshifted 24-Hour Mean)} \\
\sigma_{24\text{h}}(t-1) = \sqrt{\frac{1}{24}\sum_{k=1}^{24} (P_{t-k} - \mu_{24\text{h}})^2} & \text{(Unshifted 24-Hour Volatility)} \\
\mu_{168\text{h}}(t-1) = \frac{1}{168}\sum_{k=1}^{168} P_{t-k} & \text{(Unshifted Weekly Mean)} \\
h_t \in [0, 23], \; \text{DoW}_t \in [0, 6], \; m_t \in [1, 12] & \text{(Calendar Time Indices)} \\
\mathbb{I}_{\text{weekend}}(t) \in \{0, 1\} & \text{(Weekend Indicator)} \\
T_{2\text{m}}(t) & \text{(Exogenous Temperature)}
\end{bmatrix} \in \mathbb{R}^{16}
\label{eq:load_feature_vector}
\end{equation}
Ambient temperature ($T2M$) is legitimate exogenous weather data, not leakage.

### 2.3 Supervised Learning Formulations

#### 1. Random Forest Regressor (Champion Architecture)
Random Forest builds an ensemble of $B$ decorrelated decision trees $\{T_b\}_{b=1}^B$ trained on bootstrap samples $\mathcal{D}_b \subset \mathcal{D}$ drawn with replacement:
\begin{equation}
\hat{y}_{\text{RF}}(\mathbf{x}) = \frac{1}{B} \sum_{b=1}^B T_b\left(\mathbf{x}; \; \Theta_b\right)
\label{eq:rf_ensemble_average}
\end{equation}
At each candidate split node $s$ partitioning dataset $D$ into children $D_L$ and $D_R$, the algorithm evaluates a random feature subspace of size $m \le d$ to maximize variance reduction:
\begin{equation}
\Delta \mathcal{I}(D, s) = \text{Var}(D) - \left( \frac{|D_L|}{|D|} \text{Var}(D_L) + \frac{|D_R|}{|D|} \text{Var}(D_R) \right)
\label{eq:variance_reduction_impurity}
\end{equation}
where $\text{Var}(D) = \frac{1}{|D|}\sum_{i \in D} (y_i - \bar{y}_D)^2$.
- *Solar Hyperparameters:* $B = 200$, $\text{max\_depth} = 15$, $\text{min\_samples\_leaf} = 5$.
- *Load Hyperparameters:* $B = 300$, $\text{max\_depth} = 20$, $\text{min\_samples\_leaf} = 3$.

#### 2. Extreme Gradient Boosting (XGBoost)
XGBoost constructs an additive ensemble of $K$ shallow trees in a forward stage-wise manner:
\begin{equation}
\hat{y}^{(m)}(\mathbf{x}) = \hat{y}^{(m-1)}(\mathbf{x}) + f_m(\mathbf{x}), \quad f_m \in \mathcal{H}
\end{equation}
Tree $f_m$ is optimized via a second-order Taylor expansion of the regularized loss:
\begin{equation}
\tilde{\mathcal{L}}^{(m)} \approx \sum_{i=1}^N \left[ l\left(y_i, \hat{y}_i^{(m-1)}\right) + g_i f_m(\mathbf{x}_i) + \frac{1}{2} h_i f_m^2(\mathbf{x}_i) \right] + \gamma T + \frac{1}{2} \lambda \sum_{j=1}^T w_j^2
\label{eq:xgboost_taylor_objective}
\end{equation}
where $g_i = \frac{\partial l(y_i, \hat{y})}{\partial \hat{y}}$ and $h_i = \frac{\partial^2 l(y_i, \hat{y})}{\partial \hat{y}^2}$ are first and second order gradients, $T$ is the number of terminal leaves, and $w_j$ are leaf output weights.

#### 3. Support Vector Regression (SVR)
SVR maps inputs to a reproducing kernel Hilbert space using a Radial Basis Function (RBF) kernel:
\begin{equation}
K(\mathbf{x}_i, \mathbf{x}_j) = \exp\left(-\gamma \|\mathbf{x}_i - \mathbf{x}_j\|^2\right)
\end{equation}
The primal objective minimizes structural risk under $\epsilon$-insensitive loss:
\begin{equation}
\min_{\mathbf{w}, b, \boldsymbol{\xi}, \boldsymbol{\xi}^*} \frac{1}{2}\|\mathbf{w}\|^2 + C \sum_{i=1}^N \left(\xi_i + \xi_i^*\right) \quad \text{s.t.} \quad 
\begin{cases}
y_i - (\mathbf{w} \cdot \phi(\mathbf{x}_i) + b) \le \epsilon + \xi_i \\
(\mathbf{w} \cdot \phi(\mathbf{x}_i) + b) - y_i \le \epsilon + \xi_i^* \\
\xi_i, \xi_i^* \ge 0
\end{cases}
\end{equation}

#### 4. Naive Persistence Baseline (Load Reference)
To rigorously establish statistical forecasting utility, the load model is benchmarked against the standard time-series persistence baseline:
\begin{equation}
\hat{P}_{\text{persistence}}(t) = P_{\text{actual}}(t-1)
\label{eq:persistence_baseline}
\end{equation}

---

## 3. Decoupled Dual-Layer Explainable AI (XAI) Formulations

To resolve [Gap 4](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md#gap-4-explainability-conflation-and-omission-of-control-causality), explainability is partitioned into two structurally decoupled layers:

### 3.1 Layer 1: Model-Level Game-Theoretic TreeSHAP

#### 1. Exact Shapley Value Formula
The marginal contribution $\phi_i$ of feature $i$ across model $f$ and input instance $\mathbf{x}$ is defined by the unique cooperative game-theoretic formulation:
\begin{equation}
\phi_i(f, \mathbf{x}) = \sum_{S \subseteq \mathcal{F} \setminus \{i\}} \frac{|S|!(|\mathcal{F}| - |S| - 1)!}{|\mathcal{F}|!} \left[ f_{\mathbf{x}}(S \cup \{i\}) - f_{\mathbf{x}}(S) \right]
\label{eq:shapley_exact_definition}
\end{equation}
where $\mathcal{F}$ is the total set of $M$ features, $S$ is a feature coalition, and $f_{\mathbf{x}}(S) = \mathbb{E}\left[f(\mathbf{X}) \mid \mathbf{X}_S = \mathbf{x}_S\right]$.

#### 2. Fundamental Axioms Satisfied
TreeSHAP uniquely satisfies four fundamental game-theoretic axioms:
1. **Efficiency (Local Accuracy):** The sum of feature attributions equals the difference between model output and expected base prediction:
   \begin{equation}
   \hat{f}(\mathbf{x}) = \phi_0 + \sum_{i=1}^M \phi_i(\mathbf{x}), \quad \text{where } \phi_0 = \mathbb{E}[f(\mathbf{X})]
   \label{eq:shap_efficiency_axiom}
   \end{equation}
2. **Symmetry:** If $f_{\mathbf{x}}(S \cup \{i\}) = f_{\mathbf{x}}(S \cup \{j\})$ for all $S \subseteq \mathcal{F} \setminus \{i, j\}$, then $\phi_i = \phi_j$.
3. **Dummy (Null Player):** If $f_{\mathbf{x}}(S \cup \{i\}) = f_{\mathbf{x}}(S)$ for all $S \subseteq \mathcal{F}$, then $\phi_i = 0$.
4. **Additivity:** For an ensemble $f = \sum w_k f_k$, $\phi_i(f) = \sum w_k \phi_i(f_k)$.

#### 3. Computational Complexity
While arbitrary model Shapley evaluation requires $\mathcal{O}(M \cdot 2^M)$ exponential subsets, TreeSHAP optimizes attribution extraction by traversing the pre-computed tree graph topologies:
\begin{equation}
\text{Complexity}_{\text{TreeSHAP}} = \mathcal{O}\left(B \cdot L \cdot D^2\right)
\label{eq:treeshap_complexity}
\end{equation}
where $B$ is the ensemble tree count ($100\text{--}300$), $L$ is the maximum number of leaves, and $D$ is maximum tree depth ($15\text{--}20$). Floating-point additivity error is verified at:
\begin{equation}
\left| \hat{f}(\mathbf{x}) - \phi_0 - \sum_{i=1}^M \phi_i(\mathbf{x}) \right| < 10^{-6}\text{ kW}
\end{equation}

### 3.2 Layer 2: System-Level Deterministic Causal Translation

Layer 2 maps physical power margins, forecast deficits, and lookahead schedules into deterministic natural language explanations:

\begin{equation}
\text{Explanation}_{\text{Layer 2}}(d, t) = 
\begin{cases}
\text{Template}_{\text{ALLOW}}\left(P_{\text{device}}, D, \hat{P}_{\text{solar}}, \hat{P}_{\text{load}}, k\sigma_{\text{net}}, S_{\text{safe}}\right), & \text{if } S_{\text{window}} \ge P_{\text{device}} \\
\text{Template}_{\text{DENY}}\left(P_{\text{device}}, S_{\text{safe}}, \Delta P_{\text{deficit}}, t^*, S_{\text{safe}}(t^*)\right), & \text{if } S_{\text{window}} < P_{\text{device}}
\end{cases}
\label{eq:layer2_causal_mapping}
\end{equation}
where $\Delta P_{\text{deficit}}(t) = P_{\text{device}} - S_{\text{safe}}(t)$ and $t^*$ is the optimal deferral slot identified by Equation~\eqref{eq:optimal_deferral_t_star}.

---

## 4. Heteroskedastic Uncertainty Quantification & Closed-Form Safe Surplus

Conventional HEMS optimize under deterministic point predictions, ignoring that forecast errors are strongly **heteroskedastic** (error variance fluctuates systematically with physical conditions).

### 4.1 Empirical Residual Error Formulation
For model $f$ evaluated on chronological test partition $\mathcal{D}_{\text{test}}$, the hourly prediction error is:
\begin{equation}
e(t) = P_{\text{actual}}(t) - \hat{P}(t)
\label{eq:residual_error}
\end{equation}
with sample variance $\sigma^2 = \frac{1}{N_{\text{test}}-1}\sum_{t=1}^{N_{\text{test}}} (e(t) - \bar{e})^2$.

### 4.2 Empirical Condition-Based Stratification

#### 1. Solar Cloud-Cover Bucketing ($\sigma_{\text{solar}}$)
Solar forecast variance scales with atmospheric cloud volatility. The test partition ($N_{\text{test}} = 11,612$) is partitioned into three meteorological strata based on cloud cover $c_t \in [0, 100]\%$:
\begin{equation}
\sigma_{\text{solar}}(c_t) = 
\begin{cases}
\sigma_{\text{clear}} = \mathbf{0.0851\text{ kW}}, & 0\% \le c_t \le 20\% \quad (N = 4,166) \\
\sigma_{\text{partly}} = \mathbf{0.1317\text{ kW}}, & 21\% \le c_t \le 60\% \quad (N = 1,481) \\
\sigma_{\text{overcast}} = \mathbf{0.1386\text{ kW}}, & 61\% \le c_t \le 100\% \quad (N = 5,965)
\end{cases}
\label{eq:solar_bucketed_sigma}
\end{equation}
Fallback global standard deviation: $\sigma_{\text{solar, global}} = 0.1225\text{ kW}$.

#### 2. Household Load Diurnal Bucketing ($\sigma_{\text{load}}$)
Single-household load volatility varies across human-behavioral diurnal blocks. The load test partition ($N_{\text{test}} = 6,532$) is partitioned into four diurnal blocks based on hour $h_t \in [0, 23]$:
\begin{equation}
\sigma_{\text{load}}(h_t) = 
\begin{cases}
\sigma_{\text{night}} = \mathbf{0.2662\text{ kW}}, & h_t \in [0, 5] \quad (N = 1,634) \\
\sigma_{\text{morning}} = \mathbf{0.4800\text{ kW}}, & h_t \in [6, 11] \quad (N = 1,626) \\
\sigma_{\text{afternoon}} = \mathbf{0.5114\text{ kW}}, & h_t \in [12, 17] \quad (N = 1,631) \\
\sigma_{\text{evening}} = \mathbf{0.6075\text{ kW}}, & h_t \in [18, 23] \quad (N = 1,641)
\end{cases}
\label{eq:load_bucketed_sigma}
\end{equation}
Fallback global standard deviation: $\sigma_{\text{load, global}} = 0.4831\text{ kW}$.

### 4.3 Conservative Net Safe Surplus ($S_{\text{safe}}$) Formulation
The net available surplus solar power after subtracting empirical uncertainty margins is defined algebraically as:
\begin{equation}
P_{\text{solar, safe}}(t) = \max\left(0, \; \hat{P}_{\text{solar}}(t) - k_{\text{solar}} \cdot \sigma_{\text{solar}}(c_t)\right)
\label{eq:safe_solar_formula}
\end{equation}
\begin{equation}
P_{\text{load, conservative}}(t) = \hat{P}_{\text{load}}(t) + k_{\text{load}} \cdot \sigma_{\text{load}}(h_t)
\label{eq:conservative_load_formula}
\end{equation}
\begin{equation}
S_{\text{safe}}(t) = P_{\text{solar, safe}}(t) - P_{\text{load, conservative}}(t)
\label{eq:safe_surplus_formula}
\end{equation}
where $k_{\text{solar}}, k_{\text{load}} \ge 0$ are user-configurable risk tolerance multipliers (authoritative baseline: $k_{\text{solar}} = k_{\text{load}} = k$).

#### Root-Sum-Square (RSS) Symmetric Representation:
When solar generation exceeds the safety floor ($\hat{P}_{\text{solar}} \ge k\sigma_{\text{solar}}$), Equation~\eqref{eq:safe_surplus_formula} is equivalent to:
\begin{equation}
S_{\text{safe}}(t) = \hat{P}_{\text{solar}}(t) - \hat{P}_{\text{load}}(t) - k \cdot \left(\sigma_{\text{solar}}(c_t) + \sigma_{\text{load}}(h_t)\right)
\end{equation}
Or under an independent error variance root-sum-square formulation:
\begin{equation}
S_{\text{safe}}(t) = \hat{P}_{\text{solar}}(t) - \hat{P}_{\text{load}}(t) - k \sqrt{\sigma_{\text{solar}}^2(c_t) + \sigma_{\text{load}}^2(h_t)}
\end{equation}

### 4.4 Decision Logic and Multi-Hour Lookahead Optimization

#### 1. Instantaneous Decision Rule
For appliance $d$ requesting immediate connection at time $t$ with rated active power $P_{\text{device}}$:
\begin{equation}
\text{Decision}_{\text{instant}}(d, t) = 
\begin{cases}
\text{ALLOW (Switch to Solar)}, & \text{if } S_{\text{safe}}(t) \ge P_{\text{device}} \\
\text{DENY (Retain on Grid)}, & \text{if } S_{\text{safe}}(t) < P_{\text{device}}
\end{cases}
\label{eq:instantaneous_decision_rule}
\end{equation}

#### 2. Multi-Hour Duration-Aware Verification
For an appliance requiring continuous operation over cycle duration $D$ (hours), continuous duration is mapped to discrete hourly blocks via ceiling discretization:
\begin{equation}
n_{\text{hours}} = \max\left(1, \; \lceil D \rceil\right)
\label{eq:duration_nhours}
\end{equation}
The continuous runtime safety condition evaluates the minimum projected surplus over consecutive intervals:
\begin{equation}
S_{\text{window}}(t, n_{\text{hours}}) = \min_{\tau \in [t, \; t+n_{\text{hours}}-1]} S_{\text{safe}}(\tau)
\label{eq:window_safe_surplus}
\end{equation}
\begin{equation}
\text{Decision}_{\text{duration}}(d, t, D) = 
\begin{cases}
\text{ALLOW}, & \text{if } S_{\text{window}}(t, n_{\text{hours}}) \ge P_{\text{device}} \\
\text{DENY}, & \text{if } S_{\text{window}}(t, n_{\text{hours}}) < P_{\text{device}}
\end{cases}
\label{eq:duration_decision_rule}
\end{equation}

#### 3. 24-Hour Optimal Deferral Scheduling ($t^*$)
If an appliance is DENIED at current timestamp $t$, the decision engine searches the forward 24-hour lookahead horizon $\mathcal{T} = [t+1, t+24-n_{\text{hours}}]$ to identify the optimal future start time:
\begin{equation}
t^* = \arg\max_{t' \in \mathcal{T}_{\text{ALLOW}}} \sum_{\tau=0}^{n_{\text{hours}}-1} S_{\text{safe}}(t' + \tau)
\label{eq:optimal_deferral_t_star}
\end{equation}
where $\mathcal{T}_{\text{ALLOW}} = \{t' \in \mathcal{T} \mid S_{\text{window}}(t', n_{\text{hours}}) \ge P_{\text{device}}\}$. If $\mathcal{T}_{\text{ALLOW}} = \emptyset$, the engine reports no feasible solar window within 24 hours.

#### 4. Algorithmic Complexity Proof
- Instantaneous check: Evaluates Equation~\eqref{eq:instantaneous_decision_rule} via a single subtraction and inequality comparison: **$\mathcal{O}(1)$ algorithmic complexity**.
- Multi-hour check: Evaluates Equation~\eqref{eq:window_safe_surplus} across $n_{\text{hours}} \le 4$ discrete blocks: **$\mathcal{O}(n_{\text{hours}}) = \mathcal{O}(1)$ complexity**.
- 24-hour scheduling search: Iterates over $|\mathcal{T}| \le 24$ discrete candidate slots: **$\mathcal{O}(|\mathcal{T}| \cdot n_{\text{hours}}) = \mathcal{O}(1)$ finite-time complexity**.
- *Execution Location Boundary:* All decision formulas execute in the **FastAPI backend** (`backend/app/services/decision_engine.py`), **not** on the ESP32. The closed algebraic formulation eliminates commercial optimization solvers (CPLEX, Gurobi) while remaining structurally compatible with future embedded microcontroller C++ porting.

---

## 5. Embedded Discrete Metrology and Actuation Mathematics

### 5.1 Discrete Sampled RMS AC Estimation
On the physical ESP32 edge node, continuous sinusoidal AC waveforms are burst-sampled across $T_{\text{window}} = 200\text{ ms}$ (10 complete $50\text{ Hz}$ cycles, $M \approx 300\text{--}400$ discrete samples at $1.5\text{--}2.0\text{ kHz}$):

#### 1. Discrete Sampled Mains Voltage RMS Estimation:
\begin{equation}
V_{\text{RMS}} = K_V \times \sqrt{\frac{1}{M} \sum_{m=1}^M \left( \text{ADC}_v[m] - V_{\text{zero}} \right)^2}
\label{eq:v_rms_discrete_formula}
\end{equation}
where:
- $\text{ADC}_v[m] \in [0, 4095]$ is the raw 12-bit ADC reading from pin ADC1_CH7 (GPIO 35);
- $V_{\text{zero}} = 2539.65\text{ counts}$ is the measured quiescent DC mid-point offset;
- $K_V = 0.619060\text{ V/count}$ is the single-point voltage scaling constant derived from bench multimeter reference $V_{\text{ref}} = 225.00000\text{ V}$ over raw count swing $363.45427\text{ counts}$ ($1.40\%$ residual offset logged in Supabase row #836).

#### 2. Discrete Sampled Load Current RMS Estimation:
\begin{equation}
I_{\text{RMS}} = \frac{\sqrt{\frac{1}{M} \sum_{m=1}^M \left( \text{ADC}_i[m] - I_{\text{zero}} \right)^2} \times \left( \frac{V_{\text{ADC\_REF}}}{4095 \cdot K_{\text{divider}}} \right)}{\text{Sensitivity}_{\text{ACS712}}}
\label{eq:i_rms_discrete_formula}
\end{equation}
where:
- $\text{ADC}_i[m] \in [0, 4095]$ is the raw reading from pin ADC1_CH6 (GPIO 34);
- $I_{\text{zero}} = 2537.18\text{ counts}$ is the quiescent zero-current offset;
- $V_{\text{ADC\_REF}} = 3.300\text{ V}$ is the nominal ESP32 reference voltage;
- $K_{\text{divider}} = \frac{15\text{ k}\Omega}{10\text{ k}\Omega + 15\text{ k}\Omega} = 0.600$ is the passive resistive divider attenuation ratio;
- $\text{Sensitivity}_{\text{ACS712}} = 0.100\text{ V/A} \quad (100\text{ mV/A})$ is the nominal datasheet sensitivity for the ACS712-20A module.

#### 3. Real Active Power and Energy Accumulation:
Instantaneous product integration computes real active power, naturally incorporating the power factor ($\cos\theta$):
\begin{equation}
P_{\text{active}} = \frac{1}{M} \sum_{m=1}^M v_{\text{inst}}[m] \cdot i_{\text{inst}}[m] \quad (\text{Watts})
\label{eq:p_active_discrete_formula}
\end{equation}
\begin{equation}
E_{\text{accumulated}}(t) = E_{\text{accumulated}}(t-1) + \frac{P_{\text{active}}(t) \times \Delta t_{\text{hours}}}{1000} \quad (\text{kWh})
\label{eq:energy_accumulation_formula}
\end{equation}
To prevent ADC quantization noise from accumulating during quiescent periods, readings below $I_{\text{cutoff}} = 50\text{ mA}$ are clamped to zero ($I_{\text{RMS}} = 0.0\text{ A}, P_{\text{active}} = 0.0\text{ W}$).

### 5.2 Software Break-Before-Make Transfer Delay Logic
During source transfer switching between the 4-channel Grid bank ($G_i$) and 4-channel Solar bank ($S_i$), the firmware state machine enforces a software blocking delay:
\begin{equation}
\mathcal{S}_{\text{transition}}(i, \text{Target}) = 
\begin{cases}
G_i \to \text{LOW (OFF)}, \; \text{delay}(300\text{ ms}), \; S_i \to \text{LOW (ON)}, & \text{if Target = SOLAR} \\
S_i \to \text{HIGH (OFF)}, \; \text{delay}(300\text{ ms}), \; G_i \to \text{LOW (ON)}, & \text{if Target = GRID}
\end{cases}
\label{eq:relay_bbm_logic}
\end{equation}
This guarantees a non-overlapping de-energization window of $T_{\text{BBM}} = 300\text{ ms}$ in software, mitigating line-to-line contact arcing during routine operation (explicitly disclosed as an implementation software delay, not a certified hardware mechanical interlock).

---

## 6. Financial and Self-Consumption Accounting Formulations

Economic savings are computed from empirical self-consumption under a flat domestic tariff:

\begin{equation}
E_{\text{self}}(t) = \min\left(E_{\text{load}}(t), \; E_{\text{solar}}(t)\right) \quad (\text{kWh})
\label{eq:self_consumption_energy}
\end{equation}
\begin{equation}
\text{Cost Savings}(t) = E_{\text{self}}(t) \times \text{Tariff}_{\text{flat}} \quad (\text{BDT})
\label{eq:financial_savings_formula}
\end{equation}
where $\text{Tariff}_{\text{flat}} = 7.50\text{ BDT/kWh}$ (standard residential tier-3 domestic rate in Bangladesh). Financial accounting assumes zero feed-in credit for grid exports and models no battery capital depreciation.

---

## 7. Section Summary

This document formalizes the complete mathematical foundation of the Solar-Aware HEMS framework:
1. Physical PV target modeling establishing a $2.115\text{ kWp}$ benchmark array without target circularity.
2. Leak-free machine learning feature vectors for solar ($\mathbb{R}^7$) and load ($\mathbb{R}^{16}$).
3. Game-theoretic TreeSHAP polynomial complexity $\mathcal{O}(B \cdot L \cdot D^2)$ and exact additivity ($<10^{-6}\text{ kW}$).
4. Closed-form heteroskedastic Safe Surplus ($S_{\text{safe}}$) evaluated with $O(1)$ complexity in the backend.
5. Discrete sampled RMS AC metrology ($K_V = 0.619060\text{ V/count}$) and software-enforced 300 ms break-before-make delays.

Complete implementation architectures and operational edge-cloud topologies are detailed in [`edge_and_cloud_methodology.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/03_Research_Questions_and_Methodology/edge_and_cloud_methodology.md).
