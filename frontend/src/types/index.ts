/* TypeScript interfaces matching the exact backend response schemas */

// ── Telemetry ────────────────────────────────────────────────────
export interface SensorReading {
  id: number;
  device_id: string;
  ts: string;
  voltage_v: number | null;
  current_a: number | null;
  power_w: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  power_factor: number | null;
  energy_accum_kwh: number | null;
  grid_bank_enabled: boolean | null;
  solar_bank_enabled: boolean | null;
  relay_commanded_state: RelayState | null;
  mismatch_suspected: boolean | null;
  cal_status: string | null;
  v_zero_offset: number | null;
  i_zero_offset: number | null;
  v_cal_factor: number | null;
  i_sensitivity: number | null;
}

export interface RelayState {
  load_1?: LoadRelay;
  load_2?: LoadRelay;
  load_3?: LoadRelay;
  load_4?: LoadRelay;
}

export interface LoadRelay {
  applied_source: LoadSource;
  desired_source?: string;
  selector_switch?: string;
}

export type LoadSource = 'grid' | 'solar' | 'off';

export interface TelemetryLatestResponse {
  reading: SensorReading | null;
}

export interface TelemetryHistoryResponse {
  readings: SensorReading[];
}

// ── Device Status / Control ──────────────────────────────────────
export interface DeviceStatus {
  device_id: string;
  load_1: LoadSource;
  load_2: LoadSource;
  load_3: LoadSource;
  load_4: LoadSource;
  cal_command: string | null;
  last_command_ts: string | null;
  updated_at: string | null;
}

export interface DeviceControlResponse {
  device_id: string;
  load_1: LoadSource;
  load_2: LoadSource;
  load_3: LoadSource;
  load_4: LoadSource;
  status: string;
  last_command_ts: string | null;
  updated_at: string;
}

// ── Solar Prediction ─────────────────────────────────────────────
export interface SolarPrediction {
  target_time: string;
  predicted_kw: number;
  safe_kw: number;
  sigma_kw: number;
  sigma_bucket: string;
  k: number;
  cloud_cover: number;
  temperature: number;
  relative_humidity: number;
  wind_speed: number;
  model_version: string;
  weather_source: string;
}

// ── Load Prediction ──────────────────────────────────────────────
export interface LoadPrediction {
  target_time: string;
  predicted_kw: number;
  conservative_kw: number;
  sigma_kw: number;
  sigma_bucket: string;
  k: number;
  t2m_value: number;
  model_version: string;
  history_mode?: 'real_history' | 'benchmark_profile_fallback';
  feature_provenance?: Record<string, any>;
  t2m_disclosure: T2MDisclosure;
}

export interface T2MDisclosure {
  source: string;
  training_source: string;
  provenance_note: string;
}

// ── Risk Margin ──────────────────────────────────────────────────
export interface RiskMargin {
  k: number;
  sigma_method: string;
  solar_sigma_buckets: Record<string, number>;
  load_sigma_buckets: Record<string, number>;
  calibration_disclosure: string;
  k_selection_rationale: string;
}

// ── Device Check ─────────────────────────────────────────────────
export interface DeviceCheckResponse {
  id: number;
  decision: 'ALLOW' | 'DENY';
  device_name: string;
  rated_power_kw: number;
  duration_hours: number;
  priority: string | null;
  target_time: string;
  predicted_solar_kw: number;
  safe_solar_kw: number;
  solar_sigma_kw: number;
  predicted_load_kw: number;
  conservative_load_kw: number;
  load_sigma_kw: number;
  safe_surplus_kw: number;
  k: number;
  reason: string;
  history_mode?: 'real_history' | 'benchmark_profile_fallback';
  feature_provenance?: Record<string, any>;
  weather_source: string;
  t2m_disclosure: T2MDisclosure;
}

// ── Schedule Recommend ───────────────────────────────────────────
export interface HourlySlot {
  start_time: string;
  safe_surplus_kw: number;
  decision: string;
  predicted_solar_kw: number;
  safe_solar_kw: number;
  predicted_load_kw: number;
  conservative_load_kw: number;
  history_mode?: 'real_history' | 'benchmark_profile_fallback';
}

export interface ScheduleRecommendResponse {
  recommended_start: string | null;
  device_name: string;
  rated_power_kw: number;
  slots: HourlySlot[];
  history_mode?: 'real_history' | 'benchmark_profile_fallback';
  scheduling_disclosure: {
    method: string;
    limitations: string[];
  };
  t2m_disclosure: T2MDisclosure;
}

// ── XAI ──────────────────────────────────────────────────────────
export interface FeatureContribution {
  feature_name: string;
  shap_value: number;
}

export interface XAIResponse {
  prediction_type: 'solar' | 'load';
  target_time: string;
  predicted_kw: number;
  base_value_kw?: number;
  feature_contributions: FeatureContribution[];
  rule_based_explanation: string;
  shap_source: string;
}

// ── Action ───────────────────────────────────────────────────────
export interface ActionResponse {
  id: number;
  device_request_id: number;
  action: string;
  ts: string;
}

// ── UI State Types ───────────────────────────────────────────────
export type ThemeMode = 'light' | 'dark' | 'system';

export type FreshnessStatus = 'live' | 'stale' | 'offline' | 'unavailable';

export type LoadTransitionState = 'idle' | 'sending' | 'switching' | 'confirmed' | 'error';

export type View = 'home' | 'energy' | 'appliances' | 'forecast' | 'insights' | 'history' | 'settings' | 'assistant' | 'admin';

export type DataHonestyTagType = 'MEASURED' | 'CALCULATED' | 'FORECAST' | 'ESTIMATED' | 'USER ESTIMATED';

// ── AI Assistant Chat Types ───────────────────────────────────────
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  data_sources?: string[];
  tool_calls?: string[];
  error?: string;
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  history?: { role: 'user' | 'assistant'; content: string }[];
}

export interface ChatResponse {
  answer: string;
  data_sources: string[];
  tool_calls: string[];
  error?: string | null;
}

// ── Persistent Energy & Cost Accounting ───────────────────────────
export interface DailyEnergyRecord {
  date: string;
  timezone: string;
  total_energy_kwh: number;
  user_solar_kwh: number;
  solar_utilized_kwh: number;
  has_user_solar_estimate: boolean;
  estimated_savings_bdt: number;
  estimated_remaining_kwh: number;
  excess_solar_kwh: number;
  tariff_rate: number;
  reading_count: number;
  first_packet_ts?: string | null;
  last_packet_ts?: string | null;
  notes?: string;
}

export interface MonthlyEnergyRecord {
  month: string;
  timezone: string;
  total_energy_kwh: number;
  total_solar_kwh: number;
  total_solar_utilized_kwh: number;
  total_savings_bdt: number;
  total_remaining_kwh: number;
  total_excess_solar_kwh: number;
  days_recorded: number;
  tariff_rate: number;
  daily_records: DailyEnergyRecord[];
}

export interface EnergySummaryResponse {
  date: string;
  month: string;
  timezone: string;
  today: DailyEnergyRecord;
  this_month: MonthlyEnergyRecord;
  tariff_rate: number;
  tariff_currency: string;
}

export interface SolarEstimateRequest {
  date: string;
  estimated_solar_kwh: number;
  notes?: string;
}

export interface SolarEstimateResponse {
  success: boolean;
  date: string;
  estimated_solar_kwh: number;
  persisted_id?: number | null;
}

export interface HourlyForecastData {
  timeLabel: string;
  isoTime: string;
  hourOfDay: number;
  isNight: boolean;
  predSolarKw: number;
  safeSolarKw: number;
  solarSigmaKw: number;
  solarBucket: string;
  predLoadKw: number | null;
  conservativeLoadKw: number | null;
  loadSigmaKw: number | null;
  loadBucket: string;
  safeSurplusKw: number | null;
  historyMode?: 'real_history' | 'benchmark_profile_fallback';
}

export interface EventItem {
  id: string;
  ts: Date;
  type: 'command' | 'confirm' | 'system';
  title: string;
  detail: string;
}

// ── Authentication & Access Control ──────────────────────────────
export type UserRole = 'admin' | 'user';
export type UserStatus = 'pending' | 'approved' | 'rejected';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role: UserRole;
  status: UserStatus;
  created_at?: string;
  approved_at?: string | null;
  approved_by?: string | null;
}

export interface AuthSession {
  access_token: string;
  token_type?: string;
  expires_in?: number;
  user: UserProfile;
}

export type AuthScreen = 'login' | 'signup' | 'forgot-password' | 'reset-password';
