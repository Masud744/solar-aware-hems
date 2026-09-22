# Evaluation Metrics, Uncertainty Protocols, and Benchmarking Standards

**Document ID:** `Paper/04_Experimental_Setup/evaluation_metrics_and_protocols.md`  
**Phase:** Phase 4 — Experimental Setup and Data Provenance  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Authoritative Context:** Aligned with `PROJECT_MASTER_CONTEXT.md`, `BUILD_PLAN.md`, and `Project_Report/final_report/`

---

## 1. Multi-Tiered Evaluation Framework

To provide rigorous, reproducible validation of the Solar-Aware HEMS cyber-physical architecture, evaluation is structured across four rigorous experimental tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-TIERED EVALUATION FRAMEWORK                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: Predictive Regression Accuracy                                                 │
│ • Metrics: R², MAE, RMSE, Active-Filtered MAPE                                         │
│ • Protocol: Strict Chronological Holdout (80% Train, 20% Test, shuffle=False)          │
│ • Benchmark: Beat Naive Persistence (Load R² = 0.35, Solar R² = 0.57 baseline)         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: Heteroskedastic Uncertainty Quantification & Risk Calibration                  │
│ • Metrics: Empirical Solar Coverage %, Load Coverage %, Solar Utilization %            │
│ • Protocol: Residual Stratification by Condition Buckets & k-Sensitivity Sweep        │
│ • Gate: Monotonic Coverage Growth with Increasing Multiplier k (0.5 -> 2.5)            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: Operational Decision Engine & Level-3 Admission Evaluation                     │
│ • Metrics: 2x2 Decision Matrix (Correct-ALLOW, Incorrect-ALLOW, Correct-DENY, ID)      │
│ • Safety Objective: Minimize Unsafe Incorrect-ALLOW (Target: Zero Unhedged Shortfall)  │
│ • Protocol: Evaluated on Aligned Cross-Regional Calendar Scenarios                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: Embedded Edge Metrology & Real-Time Cyber-Physical Benchmarks                  │
│ • Metrology Validation: Residual Gain Calibration vs Reference DMM Instruments        │
│ • Concurrency: FreeRTOS task separation across Core 1 and Core 0; ADC1 conflict avoidance  │
│ • Safety Interlocks: 300 ms Software Break-Before-Make Relay Switching Verification    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Predictive Machine Learning Evaluation Metrics (Tier 1)

### 2.1 Coefficient of Determination ($R^2$)
The coefficient of determination quantifies the proportion of variance in the physical ground-truth target explained by the model's non-circular feature representations:

$$R^2 = 1 - \frac{\sum_{i=1}^N \left( y_i - \hat{y}_i \right)^2}{\sum_{i=1}^N \left( y_i - \bar{y} \right)^2} = 1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}}$$

where $y_i$ is the empirical ground-truth target, $\hat{y}_i$ is the model prediction, $\bar{y} = \frac{1}{N}\sum_{i=1}^N y_i$ is the sample mean of the test partition, $\text{SS}_{\text{res}}$ is the residual sum of squares, and $\text{SS}_{\text{tot}}$ is the total sum of squares. An $R^2 = 1.0$ indicates perfect prediction; $R^2 = 0.0$ indicates performance equivalent to predicting the historical mean; and $R^2 < 0.0$ indicates worse performance than the mean.

### 2.2 Mean Absolute Error (MAE)
MAE measures the average magnitude of absolute prediction residuals in physical engineering units ($\text{kW}$), providing a linear, scale-dependent metric that does not disproportionately penalize rare outliers:

$$\text{MAE} = \frac{1}{N} \sum_{i=1}^N \left| y_i - \hat{y}_i \right| \quad [\text{kW}]$$

### 2.3 Root Mean Squared Error (RMSE)
RMSE penalizes larger prediction errors quadratically, reflecting severe forecast deviations that pose substantial risks to electrical grid stability:

$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N \left( y_i - \hat{y}_i \right)^2} \quad [\text{kW}]$$

Because $\text{RMSE} \ge \text{MAE}$, the divergence between RMSE and MAE indicates error variance: a large spread signals intermittent, high-magnitude prediction spikes (common during sudden thunderstorm onsets or unexpected electric heating activations).

### 2.4 Active-Filtered Mean Absolute Percentage Error (MAPE)
Standard MAPE is mathematically defined as:
$$\text{MAPE} = \frac{100\%}{N} \sum_{i=1}^N \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$

**Filtering Protocol for Solar and Low-Load Zero Mass:**
When evaluating solar PV generation, nighttime hours produce $y_i = 0.0\text{ kW}$, causing instantaneous division-by-zero errors. Furthermore, dawn, dusk, and sub-watt baseloads produce near-zero denominators that distort percentage error (e.g., predicting $0.05\text{ kW}$ when actual is $0.01\text{ kW}$ yields a $400\%$ error despite a negligible absolute error of $40\text{ W}$).

To prevent numerical distortion, MAPE is computed strictly over an active threshold subset $\mathcal{I}_{\text{active}}$:
$$\text{MAPE}_{\text{filtered}} = \frac{100\%}{|\mathcal{I}_{\text{active}}|} \sum_{i \in \mathcal{I}_{\text{active}}} \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$
- **Solar Filtering Threshold:** $\mathcal{I}_{\text{active, solar}} = \{i \in [1, N_{\text{test}}] \mid y_i \ge 0.05\text{ kW}\}$, isolating daylight generation hours;
- **Load Filtering Threshold:** $\mathcal{I}_{\text{active, load}} = \{i \in [1, N_{\text{test}}] \mid y_i \ge 0.10\text{ kW}\}$, eliminating standby zero-power artifacts.

---

## 3. Uncertainty Quantification and Risk Hedging Protocols (Tier 2)

### 3.1 Empirical Solar Coverage Rate
The empirical solar coverage rate quantifies the probability that actual solar generation meets or exceeds the conservatively discounted solar forecast ($P_{\text{solar, safe}}$) across daylight hours:

$$\text{Coverage}_{\text{solar}}(k) = \frac{1}{N_{\text{daylight}}} \sum_{i=1}^{N_{\text{daylight}}} \mathbb{I}\left( P_{\text{solar, actual}}(i) \ge P_{\text{solar, safe}}(i; k) \right)$$

where $\mathbb{I}(\cdot)$ is the binary indicator function, and:
$$P_{\text{solar, safe}}(t; k) = \max\left(0, \; \hat{P}_{\text{solar}}(t) - k \cdot \sigma_{\text{solar}}(c_t)\right)$$

### 3.2 Conservative Household Load Coverage Rate
The conservative load coverage rate quantifies the probability that actual household electricity consumption remains within the augmented load forecast buffer ($P_{\text{load, conservative}}$):

$$\text{Coverage}_{\text{load}}(k) = \frac{1}{N_{\text{test}}} \sum_{i=1}^{N_{\text{test}}} \mathbb{I}\left( P_{\text{load, actual}}(i) \le P_{\text{load, conservative}}(i; k) \right)$$

where:
$$P_{\text{load, conservative}}(t; k) = \hat{P}_{\text{load}}(t) + k \cdot \sigma_{\text{load}}(h_t)$$

### 3.3 Solar Energy Self-Consumption Utilization Rate
Increasing the safety factor $k$ expands the uncertainty margin, reducing the usable safe surplus and causing usable solar energy to be rejected (clipped). The solar utilization rate quantifies the fraction of actual solar generation admitted by the safety gate:

$$\text{Utilization}_{\text{solar}}(k) = \frac{\sum_{t \in \mathcal{T}_{\text{day}}} \min\left( P_{\text{solar, safe}}(t; k), \; P_{\text{solar, actual}}(t) \right)}{\sum_{t \in \mathcal{T}_{\text{day}}} P_{\text{solar, actual}}(t)} \times 100\%$$

**The Verification Monotonicity Law:**
In strict compliance with `BUILD_PLAN.md` Verification Gate requirements:
1. Coverage rates must **increase monotonically** as $k$ increases ($k = 0.5 \to 1.0 \to 1.5 \to 2.0 \to 2.5$);
2. Solar utilization must **decrease monotonically** as $k$ increases, demonstrating the physical trade-off between risk hedging and energy harvesting.

---

## 4. Level-3 Operational Decision Engine Evaluation (Tier 3)

### 4.1 Decision Admission Matrix (The 2×2 Evaluation Confusion Grid)
To evaluate the cyber-physical payoff of risk-aware energy scheduling, every admission decision is compared against the actual physical ground-truth energy balance. For an appliance with rated power $P_{\text{device}}$, the true physical surplus is:
$$S_{\text{actual}}(t) = P_{\text{solar, actual}}(t) - P_{\text{load, actual}}(t)$$

Decisions are classified into four mutually exclusive operational quadrants, summarized in Table 1.

### Table 1: Operational Decision Evaluation Confusion Matrix (Level-3 Evaluation)

| Physical Ground Truth | System Decision: ALLOW ($S_{\text{safe}} \ge P_{\text{device}}$) | System Decision: DENY ($S_{\text{safe}} < P_{\text{device}}$) |
| :---: | :--- | :--- |
| **Physical Surplus Sufficient**<br>($S_{\text{actual}} \ge P_{\text{device}}$) | **Correct-ALLOW (CA)**<br>• Success: Appliance transferred to solar.<br>• Payoff: $100\%$ renewable utilization; zero grid draw. | **Incorrect-DENY (ID)**<br>• False Rejection: Surplus was actually sufficient.<br>• Cost: Opportunity loss; unutilized solar curtailed. |
| **Physical Deficit Exists**<br>($S_{\text{actual}} < P_{\text{device}}$) | **Incorrect-ALLOW (IA) — CRITICAL HAZARD**<br>• Safety Failure: Solar generation fell short.<br>• Consequence: Unexpected grid energy import; tariff penalty. | **Correct-DENY (CD)**<br>• Safe Protection: Deficit anticipated.<br>• Payoff: Prevented grid penalty; preserved stability. |

### 4.2 Primary Cyber-Physical Objective: Incorrect-ALLOW Minimization
In standard machine learning, algorithms optimize symmetric losses (e.g., MSE). However, in cyber-physical energy systems, errors are highly asymmetric:
- An **Incorrect-DENY** produces only an opportunity cost (solar energy remains unused);
- An **Incorrect-ALLOW** causes unexpected grid import, risking domestic breaker tripping, inverter overload, and unexpected billing.

Therefore, the overarching objective of the Risk Module is to drive the **Incorrect-ALLOW rate to zero**:
$$\text{Rate}_{\text{IA}} = \frac{\text{Count}(\text{IA})}{\text{Count}(\text{ALLOW})} \longrightarrow 0.0\%$$

---

## 5. Economic Energy Accounting and Tariff Modeling

### 5.1 Residential Tariff Parameterization
To quantify economic benefits, avoided electricity expenditure is modeled using the flat residential Tier-3 tariff structure of the Bangladesh Rural Electrification Board (BREB / DPDC):

$$\text{Tariff}_{\text{grid}} = \mathbf{7.50\text{ BDT/kWh}} \quad (\approx 0.068\text{ USD/kWh})$$

### 5.2 Avoided Electricity Expenditure Formulation
Net financial savings generated by autonomous solar self-consumption over an operational evaluation horizon $T$ are calculated as:

$$\text{Savings}_{\text{total}} = \sum_{t=1}^T \left( P_{\text{solar, utilized}}(t) \times \Delta t \right) \times \text{Tariff}_{\text{grid}}$$

where $P_{\text{solar, utilized}}(t) = \sum_{d \in \mathcal{A}_{\text{active}}} P_{\text{rated}}(d)$ is the active power consumed by appliances transferred to the solar bus, and $\Delta t = 1.0\text{ h}$.

**Accounting Boundary Disclosure:**
Financial calculations account strictly for avoided grid consumption resulting from behind-the-meter domestic self-consumption. Feed-in tariffs, net-metering export compensation, and capacity demand charges are explicitly excluded in accordance with project boundaries.

---

## 6. Computational Complexity and Execution Profiling (Tier 4)

### 6.1 Algorithmic Time and Space Complexity
To confirm operational feasibility on edge and cloud hardware, computational complexity is rigorously analyzed:

1. **Conservative Net Safe Surplus Evaluation ($S_{\text{safe}}$):**
   - Inputs: Point forecasts $\hat{P}_{\text{solar}}, \hat{P}_{\text{load}}$, condition indices $c_t, h_t$, and safety factor $k$;
   - Operation: Table lookup for bucketed standard deviations followed by three scalar arithmetic operations:
     $$P_{\text{safe}} = \max\left(0, \; \hat{P}_{\text{solar}} - k \cdot \sigma_{\text{solar}}[c_t]\right)$$
     $$P_{\text{cons}} = \hat{P}_{\text{load}} + k \cdot \sigma_{\text{load}}[h_t]$$
     $$S_{\text{safe}} = P_{\text{safe}} - P_{\text{cons}}$$
   - **Algorithmic Time Complexity:** $\mathcal{O}(1)$ closed-form algebraic evaluation;
   - **Execution Location:** Evaluated deterministically in the FastAPI cloud backend service.

2. **Multi-Hour Duration Feasibility Search ($S_{\text{window}}$):**
   - Evaluates a sliding window of $n_{\text{hours}} = \max(1, \lceil D \rceil)$ discrete blocks:
     $$S_{\text{window}}(t, n_{\text{hours}}) = \min_{\tau \in [t, \; t+n_{\text{hours}}-1]} S_{\text{safe}}(\tau)$$
   - **Time Complexity:** $\mathcal{O}(n_{\text{hours}})$ scalar comparisons.

3. **24-Hour Lookahead Advisory Scheduling ($t^*$):**
   - Iterates the duration window primitive over candidate set $\mathcal{T} = \{t, \dots, t+23\}$:
     $$t^* = \arg\max_{t \in \mathcal{T}_{\text{ALLOW}}} S_{\text{window}}(t, n_{\text{hours}})$$
   - **Time Complexity:** $\mathcal{O}(|\mathcal{T}| \cdot n_{\text{hours}})$ where $|\mathcal{T}| = 24$ and $n_{\text{hours}} \in \{1, 2, 3\}$. The search requires $\le 72$ total scalar operations, completing in $<50\text{ }\mu\text{s}$ on modern CPUs without requiring an optimization solver.

### 6.2 Embedded FreeRTOS Timing and Execution Constraints
Table 2 details the empirical timing boundaries enforced across the embedded IoT edge node.

### Table 2: Embedded Edge FreeRTOS Real-Time Execution Profiling

| Execution Parameter | Configured Value | Hardware Task / Core | Functional Role & Empirical Status |
| :--- | :---: | :---: | :--- |
| **Metrology Burst Window** | **$200\text{ ms}$** | `loopTask` (Core 1) | Samples 10 full $50\text{ Hz}$ AC cycles; captures $300\text{--}400$ ADC pairs. |
| **Meter Sampling Cadence** | **$1000\text{ ms}$** | `loopTask` (Core 1) | Re-evaluates metrology every second or immediately upon relay switching. |
| **Switch Debounce Window** | **$40\text{ ms}$** | `loopTask` (Core 1) | Eliminates electromechanical contact bounce on manual switches. |
| **Relay BBM Dead-Time Delay** | **$300\text{ ms}$** | `loopTask` (Core 1) | Software blocking `delay(300)` preventing grid-solar short-circuits. |
| **Cloud Command Poll Cadence** | **$1500\text{ ms}$** | `networkTask` (Core 0) | HTTP GET `/api/device/status`; checks for pending actuation commands. |
| **Telemetry Ingest Cadence** | **$3000\text{ ms}$** | `networkTask` (Core 0) | HTTP POST `/ingest`; pushes RMS electrical and relay state telemetry. |
| **HTTP Socket Timeout** | **$1000\text{ ms}$** | `networkTask` (Core 0) | Prevents network stalls from hanging the Core 0 network state machine. |
| **Inter-Core Queue Depth** | **$16\text{ items}$** | FreeRTOS IPC | `remoteCommandQueue` buffering commands between Core 0 and Core 1. |
| **State Reconciliation Holdoff** | **$15\text{ seconds}$** | Cloud Backend | Holdoff window preventing stale edge telemetry from overriding commands. |
| **Anti-Chatter Dwell Time** | **$180\text{ seconds}$** | Cloud Decision Engine | Enforces 3-minute minimum runtime before allowing another toggle. |
