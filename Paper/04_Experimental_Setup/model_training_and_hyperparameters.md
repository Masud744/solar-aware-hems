# Machine Learning Model Architectures, Hyperparameters, and Training Protocols

**Document ID:** `Paper/04_Experimental_Setup/model_training_and_hyperparameters.md`  
**Phase:** Phase 4 — Experimental Setup and Data Provenance  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Problem Formulation and Horizon Execution Taxonomy

The forecasting pipeline is formulated as two independent, non-circular regression tasks operating over a discrete hourly time step $t \in \mathbb{Z}^+$:

$$\hat{P}_{\text{solar}}(t) = f_{\text{solar}}\left(\mathbf{x}_{\text{solar}}(t); \boldsymbol{\theta}_{\text{solar}}\right), \quad \mathbf{x}_{\text{solar}}(t) \in \mathbb{R}^7$$

$$\hat{P}_{\text{load}}(t) = f_{\text{load}}\left(\mathbf{x}_{\text{load}}(t); \boldsymbol{\theta}_{\text{load}}\right), \quad \mathbf{x}_{\text{load}}(t) \in \mathbb{R}^{16}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   PREDICTIVE MODEL EXECUTION TAXONOMY                                  │
├────────────────────────────────────────────────────┬───────────────────────────────────┤
│ 1. Solar Forecasting Pipeline (Direct Multi-Hour)  │ 2. Load Forecasting Pipeline      │
│    • Inputs: Numerical Weather Predictions (NWP)   │    • Offline Benchmarking: h = 1h │
│      (Cloud, Temp, Humidity, Wind, Sun Angles)     │      One-step ahead (6,532 test)  │
│    • Execution: Direct 24-hour ahead point forecast│    • Operational Scheduling:      │
│      without recursive autoregressive feedback     │      Recursive multi-step rollout │
│    • Champion: Random Forest (200 Trees, Depth 15) │    • Champion: Random Forest      │
│    • Test Performance: R² = 0.9547, MAE = 0.0641 kW│      (300 Trees, Depth 20)        │
└────────────────────────┬───────────────────────────┴─────────────────┬─────────────────┘
                         │                                             │
                         ▼                                             ▼
       ┌─────────────────────────────────────────────────────────────────────────┐
       │ 3. 24-Hour Lookahead Energy Scheduling Search                           │
       │    • Finite Discrete Search over 24 Candidate Hourly Slots               │
       │    • Evaluates Safe Surplus Window: S_window(t, n_hours) >= P_device    │
       │    • Algorithmic Complexity: O(|T| * n_hours) - Pure Exhaustive Search  │
       │    • Explicit Disclosure: Not a MILP, MINLP, or Dynamic Programming Sol.│
       └─────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Forecasting Horizon and Operational Execution Taxonomy
To ensure clarity in experimental claims, model execution is partitioned across three distinct operational regimes:

1. **Solar Generation Forecasting (Direct Multi-Hour):**
   The solar input feature vector $\mathbf{x}_{\text{solar}}(t) \in \mathbb{R}^7$ consists exclusively of exogenous meteorological parameters and calendar angles provided 24 hours in advance by numerical weather prediction (NWP) services. Because no autoregressive lags of solar power are used, multi-hour solar forecasts are generated directly in a single forward pass without recursive feedback error compounding.

2. **Offline Household Load Model Benchmarking ($h = 1\text{ h}$):**
   The offline comparative benchmarking of load forecasting models (reported in Section 3 and Phase 5) evaluates strictly **one-step-ahead ($h=1\text{ h}$) predictions** on the chronological holdout test set ($N_{\text{test}} = 6,532$ hours). Ground-truth observed lagged values are supplied at each time step. These offline metrics reflect one-step autoregressive skill, not multi-step open-loop trajectory forecasting.

3. **Operational Load Rollout (Recursive Multi-Step):**
   For multi-hour appliance scheduling across the 24-hour horizon, the cloud backend applies a **recursive rollout strategy**: at step $t+\tau$, previously predicted load outputs $\hat{P}_{\text{load}}(t+\tau-1)$ are recursively substituted into lag features ($P_{t-1}, P_{t-2}, P_{t-3}$). Where extended lag history is unavailable, deterministic calendar benchmark profiles provide fallback. Horizon-dependent multi-step error accumulation was not independently benchmarked offline.

4. **24-Hour Scheduling Search:**
   Appliance scheduling is executed via an exhaustive finite search over the discrete 24-hour candidate set $\mathcal{T} = \{t, t+1, \dots, t+23\}$:
   $$t^* = \arg\max_{t \in \mathcal{T}_{\text{ALLOW}}} S_{\text{window}}(t, n_{\text{hours}})$$
   where $\mathcal{T}_{\text{ALLOW}} = \{t \in \mathcal{T} \mid S_{\text{window}}(t, n_{\text{hours}}) \ge P_{\text{device}}\}$. This search operates with $\mathcal{O}(|\mathcal{T}| \cdot n_{\text{hours}})$ algorithmic complexity; it is not a Mixed-Integer Linear Programming (MILP) or Dynamic Programming solver.

---

## 2. Candidate Supervised Machine Learning Architectures

Five supervised machine learning regressors and two baseline models were implemented, tuned, and evaluated across both the solar generation and household load forecasting domains:

### 2.1 Random Forest Regressor (Champion Architecture)
Random Forest is an ensemble learning method based on bootstrap aggregating (bagging) of unpruned randomized decision trees. Given a training set $\mathcal{D} = \{(\mathbf{x}_i, y_i)\}_{i=1}^N$, the model constructs an ensemble of $B$ decision trees $\{T_b\}_{b=1}^B$:
1. For each tree $b \in \{1, \dots, B\}$, a bootstrap sample $\mathcal{D}_b$ of size $N$ is drawn with replacement from $\mathcal{D}$;
2. At each candidate node split, a randomized subset of $m \le d$ features is evaluated;
3. Split selection minimizes the Mean Squared Error (MSE) impurity criterion:
   $$\Delta \mathcal{I}(D, s) = \frac{|D_L|}{|D|} \text{Var}(D_L) + \frac{|D_R|}{|D|} \text{Var}(D_R)$$
4. The ensemble prediction is the arithmetic average across all $B$ randomized trees:
   $$\hat{y}(\mathbf{x}) = \frac{1}{B} \sum_{b=1}^B T_b(\mathbf{x})$$

Bagging reduces predictive variance without increasing bias, making Random Forest resilient to noise and sudden atmospheric fluctuations.

### 2.2 Extreme Gradient Boosting (XGBoost)
XGBoost constructs an additive ensemble of $K$ shallow regression trees $\{f_k\}_{k=1}^K$ in a forward stage-wise boosting manner. At iteration $m$, tree $f_m$ is fitted to minimize a second-order Taylor expansion of the regularized objective:
$$\mathcal{L}^{(m)} \approx \sum_{i=1}^N \left[ l\left(y_i, \hat{y}_i^{(m-1)}\right) + g_i f_m(\mathbf{x}_i) + \frac{1}{2} h_i f_m^2(\mathbf{x}_i) \right] + \Omega(f_m)$$
where $g_i = \partial_{\hat{y}^{(m-1)}} l(y_i, \hat{y}^{(m-1)})$ and $h_i = \partial^2_{\hat{y}^{(m-1)}} l(y_i, \hat{y}^{(m-1)})$ represent first- and second-order loss gradients, and the model complexity penalty is:
$$\Omega(f_m) = \gamma T + \frac{1}{2} \lambda \sum_{j=1}^T w_j^2$$
with $T$ denoting the number of terminal leaf nodes and $w_j$ the leaf weight scores.

### 2.3 Support Vector Regression (SVR)
SVR maps the input space into a high-dimensional feature space using a non-linear Radial Basis Function (RBF) kernel:
$$K(\mathbf{x}_i, \mathbf{x}_j) = \exp\left( -\gamma \|\mathbf{x}_i - \mathbf{x}_j\|^2 \right)$$
The optimization problem minimizes model complexity while penalizing residuals exceeding an $\epsilon$-insensitivity threshold:
$$\min_{\mathbf{w}, b, \boldsymbol{\xi}, \boldsymbol{\xi}^*} \frac{1}{2}\|\mathbf{w}\|^2 + C \sum_{i=1}^N \left( \xi_i + \xi_i^* \right)$$
subject to:
$$y_i - \mathbf{w}^T \phi(\mathbf{x}_i) - b \le \epsilon + \xi_i$$
$$\mathbf{w}^T \phi(\mathbf{x}_i) + b - y_i \le \epsilon + \xi_i^*$$
$$\xi_i, \xi_i^* \ge 0$$
Due to $\mathcal{O}(N^3)$ computational scaling, SVR is trained on a representative chronologically sub-sampled partition of $20,000$ training instances with standard feature normalization (`StandardScaler`).

### 2.4 Classification and Regression Trees (CART)
A single un-bagged decision tree recursively bisects the feature space using greedy variance-reduction splitting. CART serves as a transparent, lower-complexity benchmark to evaluate ensemble gains.

### 2.5 Ordinary Least Squares (OLS) Linear Regression
Standard multilinear regression solved via the closed-form normal equation:
$$\hat{\boldsymbol{\beta}} = \left( \mathbf{X}^T \mathbf{X} \right)^{-1} \mathbf{X}^T \mathbf{y}$$
serving as a baseline to quantify non-linear performance gains.

### 2.6 Naive Persistence Baselines
To verify that machine learning models capture genuine predictive signal beyond trivial autocorrelation, two naive persistence baselines are established:
1. **Load Naive Persistence:** Predicts that active power in the next hour equals active power in the current hour:
   $$\hat{P}_{\text{load}}(t) = P_{\text{load}}(t-1)$$
   This baseline achieves $R^2 = 0.350000$ and $\text{MAE} = 0.441000\text{ kW}$ on the test set.
2. **Solar Naive Persistence:** Predicts that solar power at hour $h$ on day $d$ equals solar power at the identical hour on day $d-1$:
   $$\hat{P}_{\text{solar}}(t) = P_{\text{solar}}(t-24)$$

---

## 3. Hyperparameter Configuration and Training Setup

### 3.1 Software and Hardware Environment
- **Operating System:** Ubuntu Linux 22.04 LTS (x86_64);
- **Programming Language:** Python 3.10.12;
- **Core ML Libraries:** `scikit-learn` v1.4.0, `xgboost` v2.0.3, `shap` v0.44.1, `numpy` v1.26.4, `pandas` v2.2.0;
- **Reproducibility Guarantee:** Random number generators across all algorithms and data partitions are initialized with fixed seeds (`random_state=42`);
- **Compute Hardware:** AMD Ryzen 7 5800H (8 physical cores, 16 threads @ 3.2–4.4 GHz), 16 GB DDR4 RAM.

### 3.2 Final Tuned Hyperparameter Specifications
Hyperparameters were tuned through systematic grid search and empirical validation strictly on the chronological training splits ($N_{\text{train}} = 46,444$ solar, $N_{\text{train}} = 26,124$ load), avoiding lookahead contamination. Table 1 summarizes the finalized configurations.

### Table 1: Finalized Model Hyperparameter Configurations

| Model Architecture | Forecasting Domain | Tuned Hyperparameter Configuration | Rationale / Regularization |
| :--- | :--- | :--- | :--- |
| **Random Forest (Champion)** | **Solar PV Generation** | `n_estimators=200`, `max_depth=15`, `min_samples_leaf=5`, `random_state=42`, `n_jobs=-1` | Limits tree depth to prevent memorizing rare cloud spikes; minimum leaf samples smooths leaf variance. |
| **Random Forest (Champion)** | **Household Load** | `n_estimators=300`, `max_depth=20`, `min_samples_leaf=3`, `random_state=42`, `n_jobs=-1` | Higher tree count and depth capture complex non-linear interactions across 16 autoregressive and calendar features. |
| **XGBoost Regressor** | **Solar PV Generation** | `n_estimators=200`, `max_depth=8`, `learning_rate=0.10`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42` | Subsampling (80% rows and features) prevents tree correlation and limits overfitting on clear-sky days. |
| **XGBoost Regressor** | **Household Load** | `n_estimators=300`, `max_depth=10`, `learning_rate=0.08`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42` | Lower learning rate ($0.08$) and deeper trees ($10$) ensure gradual gradient convergence on high-variance load spikes. |
| **Support Vector Regressor** | **Solar PV Generation** | `kernel='rbf'`, $C=10.0$, $\gamma=\text{'scale'}$, $\epsilon=0.01$, `StandardScaler` applied, trained on 20,000 samples | Smooth RBF kernel captures non-linear diurnal solar trajectories; standard scaling prevents variable scale distortion. |
| **Support Vector Regressor** | **Household Load** | `kernel='rbf'`, $C=10.0$, $\gamma=\text{'scale'}$, $\epsilon=0.01$, `StandardScaler` applied, trained on 20,000 samples | Continuous kernel regression maps autoregressive lags; small $\epsilon=0.01$ forces tight error tolerance. |
| **Decision Tree (CART)** | **Solar / Load** | `criterion='squared_error'`, `max_depth=12`, `min_samples_leaf=10`, `random_state=42` | Constrained single tree baseline preventing unconstrained leaf memorization. |
| **Linear Regression (OLS)** | **Solar / Load** | `fit_intercept=True`, `copy_X=True`, `n_jobs=-1` | Closed-form baseline without hyperparameter tuning. |

---

## 4. Explainable AI (TreeSHAP) Explainer Setup and Axiomatic Verification

To guarantee transparent algorithmic accountability, the champion Random Forest models are coupled with **TreeSHAP** (`shap.TreeExplainer`), computing exact Shapley feature attributions.

### 4.1 Cooperative Game-Theoretic Axioms
The model prediction $f(\mathbf{x})$ is uniquely decomposed into an additive linear sum of feature contributions anchored to the base expected value $\phi_0 = \mathbb{E}[f(\mathbf{X})]$:
$$f(\mathbf{x}) = \phi_0 + \sum_{i=1}^M \phi_i(\mathbf{x})$$

The attribution vector $\boldsymbol{\phi} = (\phi_1, \dots, \phi_M)$ satisfies four foundational axioms:
1. **Efficiency (Local Accuracy):** $\sum_{i=1}^M \phi_i(\mathbf{x}) = f(\mathbf{x}) - \mathbb{E}[f(\mathbf{X})]$. The sum of feature contributions perfectly reconstructs the difference between prediction and baseline;
2. **Missingness:** If feature $x_i$ is absent or uninformative, $\phi_i = 0$;
3. **Consistency (Monotonicity):** If a model changes such that the marginal contribution of feature $i$ increases or stays equal for all subsets, $\phi_i$ cannot decrease;
4. **Symmetry:** Two features that contribute equally to all possible feature subsets receive identical Shapley values.

### 4.2 Computational Complexity and Polynomial Acceleration
Evaluating exact Shapley values for arbitrary models requires iterating over all $2^M$ feature subsets, an NP-hard problem scaling exponentially as $\mathcal{O}(M \cdot 2^M)$. The TreeSHAP algorithm exploits the internal graph topology of decision tree ensembles, evaluating exact Shapley attributions in low-order polynomial time:
$$\text{Complexity}_{\text{TreeSHAP}} = \mathcal{O}\left( B \cdot L \cdot D^2 \right)$$
where $B$ is ensemble tree count ($200\text{--}300$), $L$ is maximum terminal leaves per tree ($\le 2^{\text{depth}}$), and $D$ is maximum tree depth ($15\text{--}20$). This enables on-demand explanation generation in $<150\text{ ms}$ on standard cloud CPUs.

### 4.3 Empirical Verification of Exact Additivity
In accordance with `BUILD_PLAN.md` Verification Gate requirements, the mathematical consistency of TreeSHAP attributions was formally audited across all holdout predictions:

$$\Delta_{\text{additivity}} = \left| f(\mathbf{x}) - \left( \phi_0 + \sum_{i=1}^M \phi_i(\mathbf{x}) \right) \right|$$

Table 2 presents the verification results.

### Table 2: TreeSHAP Additivity and Physical Consistency Verification

| Domain | Baseline Value $\phi_0$ | Test Predictions Audited | Maximum Absolute Error ($\Delta_{\text{additivity}}$) | Additivity Status |
| :---: | :---: | :---: | :---: | :---: |
| **Solar RF** | $0.430403\text{ kW}$ | $11,612\text{ samples}$ | $\mathbf{5.42 \times 10^{-14}\text{ kW}}$ | **PASSED** ($< 10^{-6}\text{ kW}$ tolerance) |
| **Load RF** | $1.109187\text{ kW}$ | $6,532\text{ samples}$ | $\mathbf{1.71 \times 10^{-13}\text{ kW}}$ | **PASSED** ($< 10^{-6}\text{ kW}$ tolerance) |

### 4.4 Top Feature Importance and Physical Sanity Verification
The physical effect direction of top contributors was audited against domain physics:

1. **Solar Forecasting Drivers:**
   - `hour` (Rank 1, Mean $|\phi| = 0.3248\text{ kW}$): Exhibits a bell-shaped diurnal trajectory, adding $+0.70\text{ kW}$ at midday (11:00–13:00) and subtracting $-0.60\text{ kW}$ at dawn, dusk, and night;
   - **The $10\times$ Importance Gap:** The top geometric feature (`hour`, $0.3248\text{ kW}$) exhibits an approximately $10\times$ larger attribution than direct cloud cover (`cloud_cover`, $0.0318\text{ kW}$). This gap is an honest reflection of empirical ML: the deterministic solar position determines the gross upper envelope of possible irradiance, while weather variables modulate generation below that envelope;
   - `relative_humidity` (Rank 2, Mean $|\phi| = 0.1950\text{ kW}$, $\text{corr} = -0.9066$): Strong negative correlation with solar output; acts as an effective proxy for cloud thickness and rain;
   - `temperature` (Rank 3, Mean $|\phi| = 0.0842\text{ kW}$, $\text{corr} = +0.7110$): Strong positive correlation with clear-sky daytime hours in Bangladesh;
   - `cloud_cover` (Rank 4, Mean $|\phi| = 0.0318\text{ kW}$, $\text{corr} = -0.7576$): High cloud fractions consistently suppress predicted solar generation.

2. **Household Load Forecasting Drivers:**
   - `power_lag_1` (Rank 1, Mean $|\phi| = 0.4501\text{ kW}$, $\text{corr} = +0.9795$): Represents $\approx 45\%$ of total attribution; previous hour load is the dominant predictor of continuous appliance baseload;
   - `hour` (Rank 2, Mean $|\phi| = 0.1063\text{ kW}$, $\text{corr} = +0.4590$): Evening peak demand hours (19:00–22:00) push predicted load above the daily mean;
   - `power_lag_168` (Rank 3, Mean $|\phi| = 0.0705\text{ kW}$, $\text{corr} = +0.8782$): Captures weekly consumer lifestyle alignment;
   - `T2M` (Rank 6, Mean $|\phi| = 0.0253\text{ kW}$, $\text{corr} = -0.8263$): Negative correlation confirms that sub-zero European temperatures increase electric space and water heating load.

---

## 5. Condition-Stratified Heteroskedastic Uncertainty Calibration

### 5.1 Formulation of Residual Error Distributions
Standard homoskedastic regression assumes normally distributed, constant error variance ($\epsilon \sim \mathcal{N}(0, \sigma^2)$). However, renewable energy generation and residential demand are inherently **heteroskedastic**:
- Clear-sky solar generation exhibits low variance, whereas partly cloudy days produce volatile atmospheric transitions;
- Nighttime household electricity consumption follows predictable baseloads, whereas evening cooking and leisure hours produce volatile multi-kilowatt spikes.

To capture dynamic error distributions without assuming Gaussianity, the Risk Module stratifies empirical model residuals:
$$e_{\text{solar}}(t) = P_{\text{solar, actual}}(t) - \hat{P}_{\text{solar}}(t)$$
$$e_{\text{load}}(t) = P_{\text{load, actual}}(t) - \hat{P}_{\text{load}}(t)$$

### 5.2 Condition-Stratified Standard Deviations
Residual standard deviations are stratified across physical atmospheric and operational categories:

1. **Solar Cloud-Cover Strata ($\sigma_{\text{solar}}(c_t)$):**
   $$\sigma_{\text{solar}}(c_t) = \begin{cases} \mathbf{0.0851\text{ kW}}, & \text{Clear Sky: } c_t \in [0\%, 20\%] \quad (N = 6,837) \\ \mathbf{0.1317\text{ kW}}, & \text{Partly Cloudy: } c_t \in (20\%, 80\%] \quad (N = 2,580) \\ \mathbf{0.1386\text{ kW}}, & \text{Overcast: } c_t \in (80\%, 100\%] \quad (N = 2,195) \end{cases}$$
   with a global unstratified baseline of $\sigma_{\text{solar, global}} = 0.1225\text{ kW}$ ($\text{RMSE} = 0.1244\text{ kW}$).
   *Sanity Check:* Overcast and partly cloudy conditions exhibit a $63\%$ increase in standard deviation over clear-sky conditions ($0.1386\text{ kW}$ vs. $0.0851\text{ kW}$), confirming that bucketing captures genuine atmospheric volatility.

2. **Load Diurnal Clock-Hour Strata ($\sigma_{\text{load}}(h_t)$):**
   $$\sigma_{\text{load}}(h_t) = \begin{cases} \mathbf{0.2662\text{ kW}}, & \text{Night Baseload: } h_t \in [0, 5] \quad (N = 1,633) \\ \mathbf{0.4800\text{ kW}}, & \text{Morning Routine: } h_t \in [6, 11] \quad (N = 1,627) \\ \mathbf{0.5114\text{ kW}}, & \text{Afternoon Window: } h_t \in [12, 17] \quad (N = 1,631) \\ \mathbf{0.6075\text{ kW}}, & \text{Evening Peak: } h_t \in [18, 23] \quad (N = 1,641) \end{cases}$$
   with a global unstratified baseline of $\sigma_{\text{load, global}} = 0.4831\text{ kW}$ ($\text{RMSE} = 0.4838\text{ kW}$).
   *Sanity Check:* Evening peak volatility is $2.28\times$ higher than nighttime baseload ($0.6075\text{ kW}$ vs. $0.2662\text{ kW}$).

### 5.3 Safety Multiplier Sensitivity Sweep ($k \in [0.5, 2.5]$)
Table 3 summarizes the empirical safety-utilization trade-off across varying safety factor multipliers ($k$) evaluated on the held-out backtest residual distributions.

### Table 3: Empirical Uncertainty Safety Multiplier ($k$) Sensitivity Sweep

| Safety Factor ($k$) | Solar Coverage Rate ($\%$) | Solar Utilization ($\%$) | Solar Clipping ($\%$) | Load Coverage Rate ($\%$) | Load Overprovisioning ($\%$) | Operational Characterization |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| $k = 0.5$ | $89.12\%$ | $87.83\%$ | $51.14\%$ | $79.04\%$ | $25.26\%$ | Aggressive: Higher solar capture; $21\%$ load shortfall risk |
| **$k = 1.0$ (Selected)** | **$93.92\%$** | **$81.50\%$** | **$56.04\%$** | **$88.36\%$** | **$47.90\%$** | **Conservative Operating Point: Balanced safety and utilization** |
| $k = 1.5$ | $96.05\%$ | $75.69\%$ | $58.57\%$ | $93.17\%$ | $70.54\%$ | Diminishing returns: $+2.13\text{ pp}$ solar coverage costs $-5.81\text{ pp}$ utilization |
| $k = 2.0$ | $97.36\%$ | $70.13\%$ | $59.82\%$ | $96.19\%$ | $93.18\%$ | Highly risk-averse: $<70\%$ solar energy usable |
| $k = 2.5$ | $98.32\%$ | $64.75\%$ | $61.22\%$ | $97.96\%$ | $115.81\%$ | Extreme ceiling: Over-hedging forces severe load rejection |

### 5.4 Justification of Operating Point ($k = 1.0$)
The operating point $k = 1.0$ was selected based on the empirical trade-off:
1. **Marginal Coverage Gain:** Stepping from $k=0.5$ to $k=1.0$ produces the single largest marginal coverage improvement across the sweep ($+4.80\text{ percentage points}$ solar coverage, $+9.32\text{ percentage points}$ load coverage) at an acceptable utilization cost ($-6.33\text{ pp}$);
2. **Robust Hedging:** Delivers $93.92\%$ solar coverage and $88.36\%$ load coverage;
3. **Preserved Usability:** Preserves $81.50\%$ solar self-consumption utilization, avoiding excessive solar shedding;
4. **Wording Boundary:** $k=1.0$ is designated strictly as the **empirically chosen conservative operating point**; it is not claimed to be mathematically or statistically optimal.

### 5.5 Methodological Disclosures
1. **Calibration Split Disclosure:** Empirical standard deviations ($\sigma$) and coverage rates were evaluated on the same held-out backtest residual set ($N_{\text{test}} = 11,612$ solar, $N_{\text{test}} = 6,532$ load) of the frozen models. This is not an independent third-split calibration result.
2. **Lead-Time Invariance:** In the runtime decision engine, $\sigma_{\text{load}}(h_t)$ is parameterized by the target hour's diurnal block and does not compound with recursive lead-time steps ($h$). Therefore, $k \cdot \sigma_{\text{load}}$ functions as an operational buffer to absorb diurnal demand volatility, rather than a formally compounded multi-step confidence bound.
