# Pydantic models for request/response payloads
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Prediction endpoints ──────────────────────────────────────────────

class SolarPredictionRequest(BaseModel):
    target_time: datetime = Field(
        ..., description="Future datetime to predict solar generation for"
    )


class SolarPredictionResponse(BaseModel):
    target_time: datetime
    predicted_kw: float
    safe_kw: float
    sigma_kw: float
    sigma_bucket: str
    k: float
    cloud_cover: float
    temperature: float
    relative_humidity: float
    wind_speed: float
    model_version: str
    weather_source: str = "Open-Meteo forecast API"


class LoadPredictionRequest(BaseModel):
    target_time: datetime = Field(
        ..., description="Future datetime to predict load for"
    )
    temperature_c: Optional[float] = Field(
        None, description="Optional temperature at 2m (°C). If omitted, fetched from Open-Meteo."
    )


class LoadPredictionResponse(BaseModel):
    target_time: datetime
    predicted_kw: float
    conservative_kw: float
    sigma_kw: float
    sigma_bucket: str
    k: float
    t2m_value: float
    model_version: str
    history_mode: str = "benchmark_profile_fallback"
    feature_provenance: Optional[dict] = None
    t2m_disclosure: dict


# ── Risk endpoint ──────────────────────────────────────────────────────

class RiskMarginResponse(BaseModel):
    k: float
    sigma_method: str = "bucketed"
    solar_sigma_buckets: dict
    load_sigma_buckets: dict
    calibration_disclosure: str
    k_selection_rationale: str


# ── Device check endpoint ──────────────────────────────────────────────

class DeviceCheckRequest(BaseModel):
    device_name: str = Field(..., description="Name of the device")
    rated_power_kw: float = Field(..., gt=0, description="Device rated power in kW")
    duration_hours: float = Field(
        ..., gt=0, le=24, description="How long the device runs (hours)"
    )
    target_time: datetime = Field(
        ..., description="When to run the device"
    )
    priority: Optional[str] = Field(
        None, description="Device priority label"
    )


class DeviceCheckResponse(BaseModel):
    id: int
    decision: str  # "ALLOW" or "DENY"
    device_name: str
    rated_power_kw: float
    duration_hours: float
    priority: Optional[str] = None
    target_time: datetime
    predicted_solar_kw: float
    safe_solar_kw: float
    solar_sigma_kw: float
    predicted_load_kw: float
    conservative_load_kw: float
    load_sigma_kw: float
    safe_surplus_kw: float
    k: float
    reason: str
    history_mode: str = "benchmark_profile_fallback"
    feature_provenance: Optional[dict] = None
    weather_source: str = "Open-Meteo forecast API"
    t2m_disclosure: dict


# ── Schedule recommend endpoint ────────────────────────────────────────

class ScheduleRecommendRequest(BaseModel):
    device_name: str
    rated_power_kw: float = Field(..., gt=0)
    duration_hours: float = Field(..., gt=0, le=24)
    window_start: datetime = Field(
        ..., description="Earliest acceptable start time"
    )
    window_end: datetime = Field(
        ..., description="Latest acceptable start time"
    )
    priority: Optional[str] = None


class HourlySlot(BaseModel):
    start_time: datetime
    safe_surplus_kw: float
    decision: str
    predicted_solar_kw: float
    safe_solar_kw: float
    predicted_load_kw: float
    conservative_load_kw: float
    history_mode: str = "benchmark_profile_fallback"


class ScheduleRecommendResponse(BaseModel):
    recommended_start: Optional[datetime]
    device_name: str
    rated_power_kw: float
    slots: list[HourlySlot]
    history_mode: str = "benchmark_profile_fallback"
    scheduling_disclosure: dict
    t2m_disclosure: dict


# ── XAI endpoint ──────────────────────────────────────────────────────

class XAIRequest(BaseModel):
    prediction_type: str = Field(
        ..., description="'solar' or 'load'"
    )
    target_time: datetime


class XAIResponse(BaseModel):
    prediction_type: str
    target_time: datetime
    predicted_kw: float
    base_value_kw: Optional[float] = None
    feature_contributions: list[dict]
    rule_based_explanation: str
    shap_source: str = "TreeExplainer (single-instance SHAP values)"


# ── Action endpoint ──────────────────────────────────────────────────

class ActionRequest(BaseModel):
    device_request_id: int
    action: str = Field(
        ..., description="'accept', 'reject', or 'manual'"
    )


class ActionResponse(BaseModel):
    id: int
    device_request_id: int
    action: str
    ts: datetime


# ── Ingest endpoint ──────────────────────────────────────────────────

class IngestRequest(BaseModel):
    device_id: str
    ts: Optional[datetime] = None
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    power_w: Optional[float] = None
    power_factor: Optional[float] = None
    energy_accum_kwh: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    grid_bank_enabled: Optional[bool] = None
    solar_bank_enabled: Optional[bool] = None
    relay_commanded_state: Optional[dict] = None
    mismatch_suspected: Optional[bool] = None
    # Remote calibration telemetry
    cal_status: Optional[str] = None
    v_zero_offset: Optional[float] = None
    i_zero_offset: Optional[float] = None
    v_cal_factor: Optional[float] = None
    i_sensitivity: Optional[float] = None


class IngestResponse(BaseModel):
    id: int
    device_id: str
    ts: datetime
    status: str = "inserted"


class SensorHistoryResponse(BaseModel):
    readings: list[dict]


# ── Device control / status / calibration endpoints ──────────────────

class DeviceStatusResponse(BaseModel):
    device_id: str
    load_1: str = "off"
    load_2: str = "off"
    load_3: str = "off"
    load_4: str = "off"
    # Alias keys without underscores for flexible client parsing
    load1: str = "off"
    load2: str = "off"
    load3: str = "off"
    load4: str = "off"
    cal_command: Optional[str] = "NONE"
    last_command_ts: Optional[str] = None
    updated_at: Optional[datetime] = None


class DeviceControlRequest(BaseModel):
    device_id: str = "esp32_main"
    load_1: Optional[str] = Field(None, description="'grid', 'solar', or 'off'")
    load_2: Optional[str] = Field(None, description="'grid', 'solar', or 'off'")
    load_3: Optional[str] = Field(None, description="'grid', 'solar', or 'off'")
    load_4: Optional[str] = Field(None, description="'grid', 'solar', or 'off'")


class DeviceControlResponse(BaseModel):
    device_id: str
    load_1: str
    load_2: str
    load_3: str
    load_4: str
    status: str = "updated"
    last_command_ts: Optional[str] = None
    updated_at: datetime


class CalibrateRequest(BaseModel):
    device_id: str = "esp32_main"
    command: str = Field(..., description="'CAL_ZERO', 'SET_VCAL', 'SET_SENS', or 'RESET_CAL'")
    value: Optional[float] = Field(None, description="Numeric parameter for SET_VCAL or SET_SENS")


class CalibrateResponse(BaseModel):
    device_id: str
    command: str
    value: Optional[float] = None
    status: str = "queued"
    message: str
    updated_at: datetime


# ── Persistent Energy & Cost Tracking schemas ─────────────────────────

class SolarEstimateRequest(BaseModel):
    date: str = Field(..., description="Target date in 'YYYY-MM-DD' format (Asia/Dhaka timezone)")
    estimated_solar_kwh: float = Field(..., ge=0.0, description="User-estimated solar contribution in kWh")
    notes: Optional[str] = Field("", description="Optional notes on solar irradiance/generation")


class SolarEstimateResponse(BaseModel):
    success: bool
    date: str
    estimated_solar_kwh: float
    persisted_id: Optional[int] = None


class DailyEnergyResponse(BaseModel):
    date: str
    timezone: str = "Asia/Dhaka"
    total_energy_kwh: float
    user_solar_kwh: float
    solar_utilized_kwh: float
    has_user_solar_estimate: bool
    estimated_savings_bdt: float
    estimated_remaining_kwh: float
    excess_solar_kwh: float
    tariff_rate: float = 7.50
    reading_count: int
    first_packet_ts: Optional[str] = None
    last_packet_ts: Optional[str] = None
    notes: Optional[str] = ""


class MonthlyEnergyResponse(BaseModel):
    month: str
    timezone: str = "Asia/Dhaka"
    total_energy_kwh: float
    total_solar_kwh: float
    total_solar_utilized_kwh: float
    total_savings_bdt: float
    total_remaining_kwh: float
    total_excess_solar_kwh: float
    days_recorded: int
    tariff_rate: float = 7.50
    daily_records: list[DailyEnergyResponse]


class EnergySummaryResponse(BaseModel):
    date: str
    month: str
    timezone: str = "Asia/Dhaka"
    today: DailyEnergyResponse
    this_month: MonthlyEnergyResponse
    tariff_rate: float = 7.50
    tariff_currency: str = "BDT"


# ── AI Assistant Chat Schemas ─────────────────────────────────────────

class ChatMessageItem(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatMessageRecord(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    data_sources: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's natural language input message")
    session_id: Optional[str] = Field(
        None, description="Unique anonymous conversation/session ID (persisted in client)"
    )
    history: Optional[list[ChatMessageItem]] = Field(
        default_factory=list, description="Recent conversation turns for context fallback"
    )


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    data_sources: list[str] = Field(
        default_factory=list, description="Data provenance tags used in answer ([MEASURED], [FORECAST], etc.)"
    )
    tool_calls: list[str] = Field(
        default_factory=list, description="Names of controlled backend tools executed"
    )
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageRecord] = Field(default_factory=list)
    count: int = 0


# ── Authentication & Admin Schemas ─────────────────────────────────────

class SignUpRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="User full name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="User email address")
    redirect_url: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class UserProfileSchema(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"  # 'admin' | 'user'
    status: str = "pending"  # 'pending' | 'approved' | 'rejected'
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: UserProfileSchema
    message: Optional[str] = None


class AdminUserActionRequest(BaseModel):
    user_id: str
    role: Optional[str] = None  # 'admin' | 'user'


class AdminUserListResponse(BaseModel):
    users: list[UserProfileSchema] = []
    count: int = 0

