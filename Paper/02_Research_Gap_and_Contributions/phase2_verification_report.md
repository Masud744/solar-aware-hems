# Phase 2 Verification Report: Research Gaps, Novel Contributions, and Scope Disclosures

**Document ID:** `Paper/02_Research_Gap_and_Contributions/phase2_verification_report.md`  
**Phase:** Phase 2 — Formal Research Gaps, Limitations, and Novelty Claims (Evidence-Resolution Pass)  
**Target Publication:** IEEE Two-Column Journal Manuscript  
**Paper Title:** *"Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework"*  
**Verification Date:** September 2026  
**Status:** Phase 2 Evidence-Resolution Pass Complete — **Hard Stop: Awaiting Supervisor Approval for Phase 3**  

---

## 1. Executive Summary & Verification Scope

In strict compliance with the Paper Workspace Operating Rules (`Paper/README.md`), `AGENTS.md`, and the Phase 2 Evidence-Resolution Mandate, this verification report establishes the formal, peer-review-defensible baseline for research gaps, academic novelty claims, and system boundaries. 

Phase 2 builds directly upon the 58 authenticated peer-reviewed publications audited in Phase 1, formalizing the core theoretical and empirical vulnerabilities of existing literature and establishing the exact scientific contributions of the proposed Solar-Aware HEMS architecture.

### Phase 2 Deliverables Finalized:
1. **[`research_gaps.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/research_gaps.md):** Formal, mathematically grounded articulation of Gaps 1 through 6, source-level literature citations from the 58-paper corpus, and the complete theoretical formulation of the **Triad Convergence Gap** with corpus-bounded phrasing.
2. **[`novel_contributions.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/novel_contributions.md):** Detailed technical specification of the 6 core scientific contributions, detailing mathematical formulation, $O(1)$ algorithmic complexity, characterized metrology boundaries, and quantitative performance benchmarks.
3. **[`gap_to_contribution_matrix.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/gap_to_contribution_matrix.md):** Comprehensive traceability matrix mapping Literature Limitations $\to$ Key Literature Studies $\to$ Identified Gap $\to$ Architectural Solution $\to$ Implemented Component $\to$ Core Contribution $\to$ Empirical Evidence $\to$ Research Questions (RQ1–RQ4), with explicit separation between software tests and physical safety validation.
4. **[`limitations_and_scope.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/limitations_and_scope.md):** Exhaustive academic disclosure of the 8 system boundaries (synthetic cross-regional evaluation pairing, ERA5-Land reanalysis vs. NWP, discrete voltage single-point calibration residuals, nominal ACS712-20A current sensitivity, software BBM delay vs. hardware interlocks, backend execution location, algebraic rule logic vs. Pareto solvers, and flat tariff accounting).
5. **[`phase2_verification_report.md`](file:///home/shahriar-alom-masud/Capstone/capstone/Paper/02_Research_Gap_and_Contributions/phase2_verification_report.md):** This formal verification report, gate checklist, and before/after claim-change log.

---

## 2. Phase 2 Verification Gate Checklist

Every verification gate criterion has been systematically evaluated against verified repository artifacts:

- [x] **Gate 1: Exact Phase 2 Scope & Verification Gate Read Before Starting**
  - Confirmed: Phase 2 scope strictly covers formal research gaps, academic novelty claims, gap-to-contribution mapping, research questions, and explicit limitation disclosures.
- [x] **Gate 2: Strict Phase Ordering Maintained (No Skip or Auto-Advance)**
  - Confirmed: Phase 1 is fully approved. Phase 2 is complete. Phase 3 has NOT been started. Execution stops unconditionally at this gate.
- [x] **Gate 3: All Frozen Benchmarks & Metrics Preserved with Zero Distortion**
  - Confirmed: Solar RF ($N=11,612$): $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, $\text{RMSE} = 0.124356\text{ kW}$, $\text{MAPE} = 49.42\%$.
  - Confirmed: Load RF ($N=6,532$): $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$, $\text{RMSE} = 0.483827\text{ kW}$, $\text{MAPE} = 42.59\%$.
  - Confirmed: Load Persistence Baseline: $\hat{P}_t = P_{t-1}$, $R^2 = 0.350000$, $\text{MAE} = 0.441000\text{ kW}$, proving $+69.39\%$ relative $R^2$ gain ($+0.2429$ absolute) and $24.70\%$ relative MAE reduction.
- [x] **Gate 4: Leakage & Target Circularity Remediation Preserved**
  - Confirmed: Solar pipeline strictly excludes GTI from predictive features $\mathcal{F}_{\text{solar}}$.
  - Confirmed: Load pipeline strictly excludes contemporaneous $V_t, I_t, \text{Sub}_i$ and unshifted rolling lookaheads.
  - Confirmed: Ambient temperature ($T2M$) is preserved and classified as legitimate exogenous weather data, not leakage.
  - Confirmed: Terminology properly distinguishes AC active power ($P = V \cdot I \cdot \cos\theta$), dataset-specific near-deterministic coupling, and experimental target leakage without misuse of "Ohm's Law".
- [x] **Gate 5: Hardware Identity and Metrology Calibration Accurately Bounded**
  - Confirmed: Current sensor is strictly ACS712-20A with nominal sensitivity $0.100\text{ V/A}$ ($100\text{ mV/A}$) on ADC1_CH6 (resistor divider ratio $0.600$). Explicitly disclosed that current sensitivity remains nominal/datasheet-based without independent multi-point current-meter validation across the operational current span. Zero occurrences of ACS712-05B exist in draft text.
  - Confirmed: Voltage scaling constant $K_V = 0.619060\text{ V/count}$ is derived from $V_{\text{ref}} / \text{ADC}_{\text{RMS, raw}} = 225.00000\text{ V} / 363.45427\text{ counts}$ with $1.40\%$ residual disclosure ($228.16\text{ V}$ reading). Explicitly characterized as a **system-level board calibration coefficient**, not an inherent universal sensor constant.
- [x] **Gate 6: Software Break-Before-Make Delay Accurately Characterized**
  - Confirmed: Described strictly as a software-enforced $300\text{ ms}$ blocking delay (`delay(300)` in `firmware/firmware.ino:318`), mitigating contact arcing and cross-conduction risk during routine transfer switching, but explicitly NOT a certified fail-safe hardware mechanical interlock.
- [x] **Gate 7: Safe Surplus Complexity and Execution Location Accurately Demarcated**
  - Confirmed: Described strictly as executing in the FastAPI backend (`backend/app/services/decision_engine.py`) with $O(1)$ algorithmic complexity (closed-form arithmetic evaluated without numerical optimization solvers). The unbenchmarked empirical claim of "<1 ms" has been completely removed. The report does not claim that the engine currently executes on the ESP32.
- [x] **Gate 8: Synthetic Cross-Regional Pairing Fully Disclosed**
  - Confirmed: Sceaux, France (UCI load) and Kaliakair, Bangladesh (Open-Meteo solar) pairing across 176 unique common hour-month scenarios is explicitly disclosed as a **synthetic cross-regional evaluation testbed**, not a geographically co-located single-dwelling validation.
- [x] **Gate 9: Corpus-Bounded Language Enforced**
  - Confirmed: Absolute phrasing ("proves zero surveyed studies", "zero papers in literature") has been replaced with corpus-bounded phrasing ("no study was identified within the reviewed 58-paper corpus").
  - Confirmed: For Gap 5 and Gap 6, literature limitations use "no implementation detail was identified in the inspected material" rather than inferring absence beyond documented facts.
- [x] **Gate 10: Strict Separation of Software Tests from Bench Observations & Hardware Limitations**
  - Confirmed: The report explicitly separates backend software tests (64 passed), firmware simulation math tests (4 passed), documented bench observations and firmware implementation checks (multimeter calibration and software relay sequencing), and remaining hardware limitations, avoiding any claim that software tests prove physical safety or that physical contact arcing/dead-time was instrumented with an oscilloscope.
- [x] **Gate 11: Zero Changes to Core Code, Datasets, Models, or Firmware**
  - Confirmed: No modifications to `ml/`, `backend/`, `firmware/`, or `Project_Report/final_report/` occurred during this phase.

---

## 3. Mathematical and Calibration Audit: $K_V = 0.619060\text{ V/count}$

To ensure absolute scientific and metrological rigor, the voltage scaling constant $K_V$ was audited across repository records:

### 1. Mathematical Formula and Derivation:
$$K_V = \frac{V_{\text{ref}}}{\text{ADC}_{\text{RMS, raw}}} = \frac{225.00000\text{ V}}{363.45427\text{ counts}} = 0.61906048\dots \approx \mathbf{0.619060\text{ V/count}}$$

### 2. Primary Source Rows & Calibration Artifacts:
- `Project_Report/final_report/chapters/Chapter5.tex:571`
- `docs/HARDWARE_CALIBRATION_METHODOLOGY.md:202`
- Persisted in ESP32 non-volatile storage (NVS) namespace `"hems_cal"`, key `"vcal"`

### 3. Dimensional Units:
Strictly **Volts per ADC count ($\text{V/count}$)**. It is a dimensional physical scaling constant, not a unitless coefficient:
$$V_{\text{RMS}} = K_V \times \text{ADC}_{\text{RMS}}$$

### 4. System-Level Calibration Interpretation:
Crucially, $K_V = 0.619060\text{ V/count}$ is a **system-level board calibration coefficient**, not an inherent universal sensor constant of the ZMPT101B module. It integrates:
- The specific ZMPT101B transformer primary-to-secondary turns ratio and magnetizing inductance;
- The onboard operational-amplifier burden resistor, trim potentiometer adjustment, and active feedback gain;
- The anti-aliasing passive RC filter attenuation;
- The individual ESP32 successive approximation register (SAR) ADC transfer response and reference voltage variations at the specific $225.0\text{ V}$ calibration point.

### 5. Residual Disclosure:
Live telemetry logged an unadjusted ESP32 voltage reading of $V_{\text{ESP32, live}} = 228.16\text{ V}$, representing a **$+1.40\%$ calibration-session residual offset** relative to the $225.00\text{ V}$ DMM standard ($0.96\%$ cross-session delta relative to a subsequent $\approx 226\text{ V}$ DMM check).

---

## 4. End-to-End 5-Stage Claim Traceability Matrix

$$\text{CLAIM} \longrightarrow \text{SOURCE / DATA} \longrightarrow \text{METHOD / IMPLEMENTATION} \longrightarrow \text{EVIDENCE / RESULT} \longrightarrow \text{PAPER STATEMENT}$$

| Item # | Core Scientific Claim | Primary Source / Dataset | Method / Implementation Path | Quantitative Evidence / Test Result | Paper Statement & Academic Scope |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **C01** | Solar model eliminates target circularity while maintaining high accuracy. | Open-Meteo reanalysis archive (Kaliakair, BD, 2020–2026; 58,056 records). | Scikit-Learn Random Forest trained strictly on non-circular atmospheric reanalysis variables (cloud cover, temperature, humidity, wind). | Test holdout ($N=11,612$): $R^2 = 0.954743$, $\text{MAE} = 0.064134\text{ kW}$, $\text{RMSE} = 0.124356\text{ kW}$, $\text{MAPE} = 49.42\%$. | Non-circular solar RF model achieves $R^2 = 0.954743$ and $\text{MAE} = 0.064134\text{ kW}$ ($78.63\%$ MAE reduction over OLS baseline $0.300105\text{ kW}$). |
| **C02** | Load model captures single-household stochastic predictability without data leakage. | UCI Machine Learning Repository (Sceaux, France; 32,656 clean records). | Random Forest ($n=100$) trained on causal autoregressive lags ($P_{t-1 \dots 168}$), `.shift(1)` stats, calendar features, and exogenous $T2M$. | Test holdout ($N=6,532$): $R^2 = 0.592867$, $\text{MAE} = 0.332060\text{ kW}$ vs persistence baseline ($R^2=0.3500$, $\text{MAE}=0.4410\text{ kW}$). | Non-leaky load RF model achieves $R^2 = 0.5929$ and $\text{MAE} = 0.3321\text{ kW}$, outperforming persistence by $+69.39\%$ relative $R^2$ gain ($24.70\%$ MAE reduction). |
| **C03** | Closed-form Safe Surplus hedges forecast uncertainty in $O(1)$ complexity. | Residual backtest logs from solar and load holdout test sets. | Closed-form algebraic inequality $S_{\text{safe}}(t) = \hat{P}_{\text{solar}} - \hat{P}_{\text{load}} - k\sqrt{\sigma_{\text{solar}}^2 + \sigma_{\text{load}}^2} \ge P_{\text{device}}$. | Evaluated algebraically in backend with $O(1)$ algorithmic complexity; zero solver licenses; $k=1.0 \rightarrow 93.92\%$ solar coverage, $88.36\%$ load coverage, $81.50\%$ utilization. | Empirical safety margin $k\sigma_{\text{net}}$ enables tunable risk hedging, evaluated deterministically in the FastAPI backend with $O(1)$ algorithmic complexity. |
| **C04** | Dual-layer XAI cleanly decouples model-level drivers from control causality. | TreeSHAP TreeExplainer and deterministic rule-based natural language generator. | Layer 1 computes TreeSHAP feature attributions; Layer 2 translates $S_{\text{safe}}$, deficit, and $t^*$ into actionable natural language recommendations. | Exact TreeSHAP additivity ($\sum \phi_i = \hat{f}(x) - E[f(x)]$) with discrepancy $<10^{-6}\text{ kW}$; deterministic deferral window $t^*$. | Decoupled dual-layer architecture prevents conflation of forecasting regression weights with appliance control causality. |
| **C05** | Dual-core FreeRTOS firmware isolates analog metrology from network latency. | ESP32 DevKit firmware implementation (`firmware/firmware.ino`). | Task pinning: Core 1 pins analog sampling loop (10 ms, Priority 2); Core 0 pins WiFi/HTTP telemetry (5000 ms, Priority 1). | Continuous discrete True-RMS AC sampling with no observable blocking interruption during asynchronous WiFi telemetry transmission. | Dual-core FreeRTOS task partitioning isolates high-frequency AC metrology from network latency, preventing telemetry blocking from stalling sensing. |
| **C06** | Software break-before-make delay mitigates transfer switching cross-conduction. | ESP32 dual 4-channel Songle SRD-05VDC relay driver code. | Blocking `delay(300)` enforced between de-asserting Grid relays and asserting Solar relays across dual banks. | Software-enforced 300 ms de-energization window confirmed in firmware state sequencing; eliminates software-commanded concurrent coil energization. | A software-enforced 300 ms break-before-make delay mitigates contact arc-over and cross-conduction risk during transfer switching (not a certified hardware safety interlock). |
| **C07** | Conversational AI assistant operates under fail-safe architectural boundaries. | SolarMate LLM agent service integrated into web dashboard. | Strict read-only advisory architecture: LLM possesses zero database write access and zero relay actuation authority. | SolarMate cannot override Safe Surplus admission decisions, modify database state, or trigger physical relay switching. | The conversational assistant operates strictly as an advisory user interface layer, fully decoupled from physical actuator control. |
| **C08** | Multi-level verification establishes software correctness and identifies physical boundaries. | Pytest test suite, firmware simulation tests, and documented benchtop calibration logs. | 64 backend regression tests + 4 firmware mathematical unit tests + documented bench multimeter calibration readings. | **64 backend + 4 firmware tests passed (100% pass rate in 3.84s).** Bench multimeter check confirmed single-point voltage calibration; firmware inspection verified software blocking delay. | Automated testing verifies software logic and discrete math; physical hardware relies on software-enforced delays without certified mechanical interlocks or external oscilloscope timing captures. |

---

## 5. Before vs. After Claim-Change Log (Phase 2 Evidence-Resolution Pass)

The following table details every revised claim, documenting the exact before wording, after wording, and supporting evidence:

| # | File & Location | Audit Category | Before Wording | After Wording | Supporting Source / Justification |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | `novel_contributions.md` (Box & §5) | Contribution 4 Title & Scope | "Hardware-Validated Dual-Core FreeRTOS Edge Prototype with 300 ms BBM Delay" | "Dual-Core FreeRTOS Edge Microcontroller Prototype with Characterized Metrology and Software-Enforced Transfer Delay" | Accurately reflects partial calibration: single-point voltage ($K_V$), nominal ACS712-20A current sensitivity without multi-point shunt calibration, and software-enforced delay. |
| **2** | `novel_contributions.md` (§5) | Hardware Metrology Boundaries | "...discrete RMS metrology ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual)..." | Added explicit boundaries: (1) single-point voltage calibration; (2) nominal ACS712-20A sensitivity ($0.100\text{ V/A}$); (3) absence of independent multi-point current calibration; (4) software 300 ms delay is not certified hardware interlock. | Master Guardrails #11 & #12; `Chapter5.tex:571`; `docs/HARDWARE_CALIBRATION_METHODOLOGY.md`. |
| **3** | `research_gaps.md` (§2, Gap 3) | Safe Surplus Timing & Location | "...($O(1)$ arithmetic complexity, $<1\text{ ms}$ algorithmic compute time per query)..." | "...evaluated deterministically in the FastAPI backend (`backend/app/services/decision_engine.py`) with $O(1)$ algorithmic complexity (closed-form arithmetic evaluated without numerical optimization solvers)..." | Removed unbenchmarked empirical "<1 ms" claim. Retained $O(1)$ as algorithmic complexity statement. Explicitly stated execution in backend, not ESP32. |
| **4** | `novel_contributions.md` (§3) | Safe Surplus Timing & Location | "...evaluated deterministically in the FastAPI backend with $O(1)$ arithmetic complexity and $<1\text{ ms}$ algorithmic compute time..." | "...evaluated deterministically in the FastAPI backend (`backend/app/services/decision_engine.py`) with $O(1)$ algorithmic complexity (closed-form arithmetic evaluated without numerical optimization solvers)..." | Removed "<1 ms"; clarified backend execution and compatibility with future embedded porting. |
| **5** | `research_gaps.md` (§2, Gap 2) | Gap 2 Electrical Terminology | "...recreating Ohm's Law ($R^2 > 0.999$)..." | Separated into 3 distinct concepts: (1) physical AC power relationship $P = V \cdot I \cdot \cos\theta$; (2) dataset-specific near-deterministic coupling in UCI; (3) verified experimental target leakage ($R^2=0.999335$). Removed "Ohm's Law". | Technical accuracy: $P = V \cdot I \cdot \cos\theta$ is AC power, not Ohm's Law ($V = I \cdot R$). |
| **6** | `novel_contributions.md` (§2) | Gap 2 Electrical Terminology | "...which artificially yields $R^2 > 0.999$ by recreating Ohm's Law..." | "...which introduces target leakage via the AC active power relationship ($P = V \cdot I \cdot \cos\theta$) and the near-deterministic algebraic coupling present in sub-metered datasets ($R^2 > 0.999$ in our reproduction)..." | Removed "Ohm's Law"; properly articulated AC circuit theory and dataset coupling. |
| **7** | `research_gaps.md` (§3, Triad Gap) | Corpus-Bounded Wording | "First unified architecture achieving end-to-end convergence across leak-free ML, closed-form UQ, decoupled XAI, and dual-core edge hardware." | "Within the reviewed 58-paper corpus, no study was identified that unifies leak-free ML forecasting, closed-form UQ, decoupled XAI, and dual-core edge hardware into an integrated cyber-physical architecture." | Calibrated absolute claim to corpus-bounded phrasing referencing the 58 inspected papers. |
| **8** | `research_gaps.md` (§2, Gap 5) | Literature Concurrency Detail | "Pradhan et al. (2025) [P43] and Siregar et al. (2023) [P45] report microcontroller prototypes where network communication latencies perturb local sensor acquisition loops." | "In surveyed microcontroller prototypes [P43], [P45], firmware relies on single-threaded loops where synchronous network communications introduce latency; no implementation detail regarding task concurrency was identified in the inspected material." | Avoided inferring absence beyond documented material; used exact requested phrasing. |
| **9** | `research_gaps.md` (§2, Gap 6) | Literature Dead-Time Detail | "Surveyed microcontroller literature [P42], [P44], [P45] documents basic relay control circuits but omits software-enforced dead-time delays during power transfer operations..." | "In surveyed dual-source microcontroller prototypes [P42], [P44], [P45], no implementation detail regarding transfer switching dead-times or phase-isolation interlocks was identified in the inspected material." | Avoided inferring absence beyond documented material; kept 300 ms explicitly software-enforced and blocking. |
| **10** | `novel_contributions.md` (Box & §7) | Synthetic Evaluation Terminology | "6. Empirical Cross-Regional Validation & Risk-Coverage Trade-Off Analysis" | "6. Synthetic Cross-Regional Evaluation & Risk-Coverage Trade-Off Analysis" | Replaced "validation" with "synthetic evaluation" to prevent implying co-located household measurement. Preserved France/Bangladesh disclosure. |
| **11** | `gap_to_contribution_matrix.md` (Row 27 & 28) | Contribution 4 Title & Gaps 5–6 | "Contribution 4: Hardware-Validated Dual-Core FreeRTOS Edge Prototype" | "Contribution 4: Dual-Core FreeRTOS Edge Prototype with Characterized Metrology and Software-Enforced Transfer Delay" (with "no implementation detail identified in inspected material" for Gaps 5 & 6). | Synchronized matrix with calibrated Contribution 4 scope and literature wording. |
| **12** | `gap_to_contribution_matrix.md` (RQ4 Section) | Multi-Level Testing Separation | "...300 ms dead-time confirmed on bench testbed; verified by 68 automated regression tests (100% pass rate)." | Explicitly separated: (1) software verification (64 backend tests); (2) firmware simulation tests (4 mathematical tests); (3) documented bench observations and firmware implementation checks (multimeter calibration, software delay); (4) remaining hardware limitations. Removed uninstrumented oscilloscope claims. | Did not imply software tests prove physical cyber-physical safety; accurately bounded bench checks. |
| **13** | `limitations_and_scope.md` (§2, Boundary 3) | K_V System-Level Interpretation | "$K_V = \frac{V_{\text{ref}}}{\text{ADC}_{\text{RMS, raw}}} = \frac{225.0\text{ V}}{363.45427\text{ counts}} = 0.619060\text{ V/count}$" | Added explicit statement: $K_V = 0.619060\text{ V/count}$ is a system-level board calibration coefficient integrating transformer ratio, burden op-amp gain, and ESP32 ADC transfer function, NOT a universal sensor constant. | Grounded physical interpretation in hardware reality. |
| **14** | `limitations_and_scope.md` (§2, Boundary 4) | Nominal Current Sensitivity | "...relies on nominal datasheet specifications..." | Explicitly confirmed: current sensing relies strictly on nominal datasheet sensitivity ($0.100\text{ V/A}$) without independent multi-point calibration against precision shunts across operational span. | Preserved transparent metrological boundary. |
| **15** | `limitations_and_scope.md` (§2, Boundary 7) | Solver Complexity Timing | "...guarantees instantaneous deterministic decisions ($<1\text{ ms}$)." | "...guarantees instantaneous deterministic decisions evaluated with $O(1)$ algorithmic complexity." | Removed "<1 ms"; preserved $O(1)$ algorithmic complexity statement. |
| **16** | `phase2_verification_report.md` (§6) | Test-Count Arithmetic Reconciliation | Listed category counts summed to 54 (2+17+8+5+3+19) despite claiming 64 backend tests. | Provided complete pytest collection output and exact breakdown across all 7 backend test files (including test_assistant_chat.py [7], test_auth_and_admin.py [6], test_weather_cache_and_resilience.py [18]) and firmware (4), summing precisely to 64 backend + 4 firmware = 68 total tests. | Fixed categorization omission and truncation in summary table. |
| **17** | `phase2_verification_report.md` (§6) & `gap_to_contribution_matrix.md` (Row 28 & RQ4) | Bench Evidence & Timing Instrumentation | Implied oscilloscope measurement of 300 ms de-energization window. | Reframed as a documented bench observation (voltage calibration with DMM, fan load observation) and firmware implementation check (software-enforced delay(300)). Explicitly stated that physical contact arcing and phase isolation under asynchronous sources were not instrumented with an oscilloscope. | Accurately reflects actual repository evidence and Chapter5.tex:600 disclosure. |
| **18** | `phase2_verification_report.md` (§7) | Git Deliverables Status | Implied Phase 2 deliverables were part of commit 571418d. | Explicitly disclosed that commit 571418d is a pre-existing commit from Sep 9, and all five Phase 2 deliverables currently exist as untracked files (?? Paper/) in the working tree. | Full repository integrity transparency without false commit attribution. |

---

## 6. Compilation Diagnostics, Test-Count Reconciliation & Bench Evidence Audit

### 6.1 Exact Test-Count Collection and Reconciliation (68 Total Items)

Pytest collection (`pytest --collect-only backend/tests/ firmware/tests/`) and verbose execution confirm exactly **68 automated tests** (64 backend tests + 4 firmware simulation tests).

#### 1. File-Wise Test Breakdown:
| # | Test File Path | Component Under Test | Collected Tests | Status | Execution Time |
| :-: | :--- | :--- | :-: | :-: | :-: |
| 1 | `backend/tests/test_assistant_chat.py` | SolarMate AI Chat Safety, Read-Only Boundary, Tool Schemas | **7** | PASSED | ~0.85s |
| 2 | `backend/tests/test_auth_and_admin.py` | JWT Auth, Pending User Gating, Admin Role & User Isolation | **6** | PASSED | ~0.45s |
| 3 | `backend/tests/test_decision_engine.py` | Section 8.3 Worked Example, Boundary Conditions, Sigma Buckets, Stale-Gating | **17** | PASSED | ~0.55s |
| 4 | `backend/tests/test_energy_accounting.py` | Trapezoidal Integration, Gap Protection, Calendar Bounds, Dhaka Time | **8** | PASSED | ~0.40s |
| 5 | `backend/tests/test_firmware_v2_endpoints.py` | Ingest Telemetry, Status Poll, Relay Control, Calibration Endpoint | **5** | PASSED | ~0.35s |
| 6 | `backend/tests/test_state_synchronization.py` | Command Timestamp Freshness, Race Prevention, Physical Selector Reconciliation | **3** | PASSED | ~0.25s |
| 7 | `backend/tests/test_weather_cache_and_resilience.py` | Upstream 429 Resilience, Negative TTL, Stale-Serving, Cooldown Timers | **18** | PASSED | ~0.90s |
| **—** | **Subtotal Backend Software Tests** | **Full Backend Application Suite** | **64** | **PASSED** | **~3.75s** |
| 8 | `firmware/tests/test_firmware_math.py` | True-RMS Math, Inductive Phase Lag, Resistor Divider Safety, Sampling Count | **4** | PASSED | ~0.09s |
| **TOTAL** | **Full Repository Test Suite** | **Backend Software + Firmware Mathematical Simulation** | **68** | **PASSED** | **3.84s** |

#### 2. Reconciliation of the Previous 54 vs. 64 Category Deficit:
In the previous draft, the category breakdown listed:
$$\text{Previous List: } 2 \text{ (auth/admin)} + 17 \text{ (decision)} + 8 \text{ (energy)} + 5 \text{ (firmware)} + 3 \text{ (sync)} + 19 \text{ (weather)} = \mathbf{54\text{ tests}}$$
This temporary 10-test categorization discrepancy is fully reconciled as follows:
1. **Omission of `test_assistant_chat.py` ($-7\text{ tests}$):** The 7 SolarMate AI safety and chat tests were omitted from the category list.
2. **Truncation of `test_auth_and_admin.py` ($-4\text{ tests}$):** Listed as 2 instead of the actual 6 tests collected in this module.
3. **Off-by-One in `test_weather_cache_and_resilience.py` ($+1\text{ test}$):** Listed as 19 instead of the actual 18 tests (7 admission tests + 11 resilience tests).
$$\text{Discrepancy: } 7 + 4 - 1 = \mathbf{10\text{ tests missing from category display}}$$
$$54 + 10 = \mathbf{64\text{ Backend Tests}} \quad (\text{plus } 4\text{ Firmware Tests} = \mathbf{68\text{ Total Tests}})$$

#### 3. Category-Wise Test Breakdown:
1. **SolarMate Chat & Advisory AI Safety (7 tests):** Live telemetry tool, relay status tool, appliance safety evaluation, confirmation flow, chat schema, hardware safety isolation (relays omitted from tools), history endpoints.
2. **Authentication, User Isolation & RBAC (6 tests):** Signup pending flow, 403 login block for pending users, token issuance for approved users, admin endpoint authorization, admin approval flow, per-user chat history isolation.
3. **Safe Surplus Decision Engine & Risk Gating (17 tests):** Section 8.3 worked example (intermediate values, deny decision, surplus value string, symmetric formula), edge boundaries (exact equality, negative surplus safety, duration-aware mid-run dip), heteroskedastic sigma buckets (clear, partly cloudy, overcast, night, morning, afternoon, evening), stale-forecast gating (stale-deny, fresh-allow, duration-aware stale check).
4. **Energy Accounting & Self-Consumption (8 tests):** Trapezoidal integration, gap protection, calendar bounds, conservative solar formulas (Load > Solar, Solar > Load), energy summary endpoint, post-validation estimate, explicit month filtering.
5. **Firmware v2 Endpoints & Ingest (5 tests):** Telemetry ingest, device status polling, relay control endpoint, device calibration endpoint, calibrated telemetry ingestion.
6. **State Synchronization & Switch Arbitration (3 tests):** Pending command protection from stale telemetry, fresh timestamp generation on dashboard toggle, physical selector override reconciliation.
7. **Weather Caching & Upstream Resilience (18 tests):** Admission policies under stale/fresh/unavailable forecast (7 tests), upstream 429 handling, exponential backoff cooldown, retry-after header parsing, negative TTL, concurrency coalescing, payload validation, memory-cache failover, 503 error handling (11 tests).
8. **Firmware Discrete Mathematics & Electrical Safety (4 tests):** Discrete True-RMS active power under unity power factor, inductive phase-lag apparent vs active power, $10\text{ k}\Omega / 15\text{ k}\Omega$ resistor divider voltage safety ($<3.0\text{ V}$ into ADC), discrete 2,000-sample count across 10 AC cycles.

---

### 6.2 Physical Bench Evidence & Instrumentation Audit

To adhere to rigorous empirical standards, the physical evidence for the edge prototype is audited and classified:

#### 1. AC Voltage Metrology Calibration:
- **Reference Instrument:** Calibrated bench Digital Multimeter (DMM) connected to AC mains supply.
- **Measurement Procedure:** Edge node executes discrete RMS AC waveform sampling over a $200\text{ ms}$ window (10 full $50\text{ Hz}$ cycles, 2,000 samples burst sampled at $1.5\text{--}2.0\text{ kHz}$) on analog pin ADC1_CH7 (GPIO 35) with zero-offset subtraction ($V_{\text{zero}} = 2539.65\text{ counts}$).
- **Number of Measurements:** 1 primary calibration session (Stage 2) + 1 subsequent observational comparison check (Session 2).
- **Reference Value:** $V_{\text{ref}} = 225.00\text{ V AC RMS}$.
- **Raw Measured ADC Value:** $\text{ADC}_{\text{RMS, raw}} = 363.45427\text{ counts RMS}$ (unrounded quotient from uncalibrated test factor).
- **Scaling Multiplier:** $K_V = \frac{225.00000\text{ V}}{363.45427\text{ counts}} = 0.619060\text{ V/count}$, persisted to NVS namespace `"hems_cal"`.
- **Live Verification Telemetry:** $V_{\text{ESP32, live}} = 228.16\text{ V AC RMS}$ logged in Supabase row #836.
- **Error Calculation:**
  $$\text{Calibration Residual Offset} = \frac{|228.16\text{ V} - 225.00\text{ V}|}{225.00\text{ V}} \times 100\% = \mathbf{1.40\%}$$
  Subsequent non-synchronous observational check against DMM ($\approx 226\text{ V}$) logged a $0.96\%$ delta.
- **Primary Source Locations:** `Project_Report/final_report/chapters/Chapter5.tex:567-574`, `docs/HARDWARE_CALIBRATION_METHODOLOGY.md:187-216`.

#### 2. Current Metrology & Reference Load Observation:
- **Sensing Hardware:** ACS712-20A Hall-effect module connected to ADC1_CH6 (GPIO 34) via $10\text{ k}\Omega / 15\text{ k}\Omega$ voltage divider ($\alpha = 0.600$).
- **Reference Appliance:** Physical Walton WTF9M3 domestic table fan ($60\text{ W}$ nameplate rated).
- **Multimeter / Telemetry Observation:** $V \approx 226\text{ V AC RMS}$, $I_{\text{telemetry}} \approx 0.28\text{ A}$, apparent power $S = 63.28\text{ VA}$.
- **Evidence Limitation:** ACS712 sensitivity relies strictly on the nominal datasheet rating ($0.100\text{ V/A}$). Operating power factor ($\cos\phi$) and true active power ($P$) were unmeasured on the bench due to lack of phase-angle instrumentation. No multi-point calibration was performed.

#### 3. 300 ms Break-Before-Make Transfer Delay:
- **Measurement Method:** Implementation check of firmware software logic in `firmware/firmware.ino` (`switchRelayChannel`) and `firmware/relay_controller.cpp:113-125`. The firmware enforces a blocking `delay(300)` call between de-asserting the active relay and asserting the target relay.
- **Physical Artifacts Status:** No oscilloscope waveform capture files, raw timing logs, or contact-arc voltage traces exist in the repository. As explicitly documented in thesis Chapter 5 (`Chapter5.tex:600`): *"physical contact arcing and phase-isolation behavior under asynchronous sources were not instrumented on this prototype."*
- **Claim Boundary:** The 300 ms delay is confirmed as a **software-enforced non-overlapping state sequence** in firmware that prevents simultaneous coil energization; it is explicitly **not** claimed as an experimentally validated physical safety interlock.

---

## 7. Git Status, Commit Integrity & Repository Disclosure

### 7.1 Authoritative Git Audit Outputs:

1. **`git rev-parse HEAD`:**
   ```text
   571418d7ea46367ddc94ec428094a6542dc43382
   ```

2. **`git show --stat 571418d`:**
   ```text
   commit 571418d7ea46367ddc94ec428094a6542dc43382 (HEAD -> main, origin/main, origin/HEAD)
   Author: Shahriar Alom Masud <masud.nil74@gmail.com>
   Date:   Wed Sep 9 03:32:30 2026 +0600

       fix: enforce upstream cooldown on rate-limit failures to prevent polling storms

    backend/app/services/weather.py                    | 198 +++++++++++++++------
    backend/tests/test_weather_cache_and_resilience.py | 101 +++++++++++
    2 files changed, 241 insertions(+), 58 deletions(-)
   ```

3. **`git ls-tree -r --name-only 571418d Paper/02_Research_Gap_and_Contributions/`:**
   ```text
   (Empty — returns exit code 0 with zero files)
   ```

4. **`git status --short`:**
   ```text
    M firmware/config.h
    M firmware/firmware.ino
   ?? Paper/
   ?? libreoffice-core_4%3a26.2.5.2-0ubuntu0.26.04.1_amd64.deb
   ?? scratch/
   ```

### 7.2 Explicit Repository Status Disclosure:
- **Phase 2 Deliverables Are Currently Untracked:** All five Phase 2 documents in `Paper/02_Research_Gap_and_Contributions/` exist in the local filesystem as untracked files (`?? Paper/`). They are **not** committed in `571418d`. Commit `571418d` is a historical commit from Sep 9 modifying backend weather services.
- **Working Tree Preservation:** As instructed, zero changes have been made to datasets, ML model binaries, backend code, firmware code, or thesis reports. Pre-existing modifications in `firmware/config.h` and `firmware/firmware.ino` (modified Sep 15) remain untouched.

---

## 8. Conclusion and Hard Stop

The final focused verification pass for Phase 2 is **100% complete and fully reconciled**:
1. **Test Counts Reconciled:** 64 backend tests + 4 firmware tests = 68 total tests (100% pass rate in 3.84s). The 10-test deficit in the previous categorization was identified and resolved (omitted `test_assistant_chat.py` [7], truncated `test_auth_and_admin.py` [4], and weather off-by-one [1]).
2. **Physical Bench Evidence Audited:** Single-point voltage calibration ($K_V = 0.619060\text{ V/count}$, $1.40\%$ residual) and Walton fan observation are documented from thesis records; the 300 ms delay is confirmed as a software-enforced blocking sequence in firmware, with explicit disclosure that oscilloscope waveforms and certified hardware interlocks were not instrumented.
3. **Calibration Wording Grounded:** Transparently distinguishes single-point voltage calibration, nominal ACS712-20A sensitivity, software blocking delay, and absence of certified hardware interlocks.
4. **Git Integrity Transparently Disclosed:** Clarified that commit `571418d` does not contain `Paper/`, and all Phase 2 deliverables currently reside as untracked files in the working tree.

**HARD STOP:** In strict adherence to `AGENTS.md` and the Phase-by-Phase Discipline, **execution is stopped here**. I will wait for your explicit review and confirmation before initiating **Phase 3: Research Questions & Methodology**.

