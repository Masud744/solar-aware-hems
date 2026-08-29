/** Type-safe API client.  Every function maps to a real backend endpoint. */
import { API_BASE } from '../utils/constants';
import type {
  TelemetryLatestResponse,
  TelemetryHistoryResponse,
  DeviceStatus,
  DeviceControlResponse,
  SolarPrediction,
  LoadPrediction,
  RiskMargin,
  DeviceCheckResponse,
  ScheduleRecommendResponse,
  XAIResponse,
  ActionResponse,
  LoadSource,
  DailyEnergyRecord,
  MonthlyEnergyRecord,
  EnergySummaryResponse,
  SolarEstimateRequest,
  SolarEstimateResponse,
} from '../types';

class ApiError extends Error {
  status: number;
  data?: any;
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let currentAuthToken: string | null = (() => {
  try {
    return localStorage.getItem('solarmate_auth_token');
  } catch {
    return null;
  }
})();

export function setAuthToken(token: string | null) {
  currentAuthToken = token;
  try {
    if (token) {
      localStorage.setItem('solarmate_auth_token', token);
    } else {
      localStorage.removeItem('solarmate_auth_token');
    }
  } catch {
    // Ignore storage quota error
  }
}

export function getAuthToken(): string | null {
  return currentAuthToken;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  if (currentAuthToken && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${currentAuthToken}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    let parsedData = null;
    try {
      parsedData = await res.json();
      if (parsedData?.detail) {
        errorDetail = typeof parsedData.detail === 'string' ? parsedData.detail : JSON.stringify(parsedData.detail);
      }
    } catch {
      const rawText = await res.text().catch(() => '');
      if (rawText) errorDetail = rawText;
    }
    throw new ApiError(errorDetail, res.status, parsedData);
  }
  return res.json();
}

// ── Telemetry ────────────────────────────────────────────────────

export function fetchTelemetryLatest(deviceId = 'esp32_main') {
  return request<TelemetryLatestResponse>(
    `/telemetry/latest?device_id=${encodeURIComponent(deviceId)}`
  );
}

export function fetchTelemetryHistory(limit = 50) {
  return request<TelemetryHistoryResponse>(
    `/telemetry/history?limit=${limit}`
  );
}

// ── Device Status / Control ──────────────────────────────────────

export function fetchDeviceStatus(deviceId = 'esp32_main') {
  return request<DeviceStatus>(
    `/device/status?device_id=${encodeURIComponent(deviceId)}`
  );
}

export function sendDeviceControl(loads: Partial<Record<string, LoadSource>>, deviceId = 'esp32_main') {
  return request<DeviceControlResponse>('/device/control', {
    method: 'POST',
    body: JSON.stringify({ device_id: deviceId, ...loads }),
  });
}

// ── Predictions ──────────────────────────────────────────────────

export function fetchSolarPrediction(targetTime: string) {
  return request<SolarPrediction>(
    `/predict/solar?target_time=${encodeURIComponent(targetTime)}`
  );
}

export function fetchLoadPrediction(targetTime: string) {
  return request<LoadPrediction>(
    `/predict/load?target_time=${encodeURIComponent(targetTime)}`
  );
}

// ── Risk ─────────────────────────────────────────────────────────

export function fetchRiskMargin() {
  return request<RiskMargin>('/risk/margin');
}

// ── Device Check / Schedule ──────────────────────────────────────

export function postDeviceCheck(body: {
  device_name: string;
  rated_power_kw: number;
  duration_hours: number;
  target_time: string;
  priority?: string;
}) {
  return request<DeviceCheckResponse>('/device/check', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function postScheduleRecommend(body: {
  device_name: string;
  rated_power_kw: number;
  duration_hours: number;
  window_start: string;
  window_end: string;
  priority?: string;
}) {
  return request<ScheduleRecommendResponse>('/schedule/recommend', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── XAI ──────────────────────────────────────────────────────────

export function fetchXAI(predictionType: 'solar' | 'load', targetTime: string) {
  return request<XAIResponse>(
    `/xai/explanation?prediction_type=${encodeURIComponent(predictionType)}&target_time=${encodeURIComponent(targetTime)}`
  );
}

// ── Action ───────────────────────────────────────────────────────

export function postAction(deviceRequestId: number, action: 'accept' | 'reject' | 'manual') {
  return request<ActionResponse>('/action', {
    method: 'POST',
    body: JSON.stringify({ device_request_id: deviceRequestId, action }),
  });
}

// ── Persistent Energy & Cost Accounting ───────────────────────────

export function fetchEnergySummary(tariffRate = 7.50) {
  return request<EnergySummaryResponse>(`/energy/summary?tariff_rate=${tariffRate}`);
}

export function fetchDailyEnergy(date?: string, tariffRate = 7.50) {
  const query = date ? `date=${encodeURIComponent(date)}&tariff_rate=${tariffRate}` : `tariff_rate=${tariffRate}`;
  return request<DailyEnergyRecord>(`/energy/daily?${query}`);
}

export function fetchMonthlyEnergy(month?: string, tariffRate = 7.50) {
  const query = month ? `month=${encodeURIComponent(month)}&tariff_rate=${tariffRate}` : `tariff_rate=${tariffRate}`;
  return request<MonthlyEnergyRecord>(`/energy/monthly?${query}`);
}

export function postSolarEstimate(body: SolarEstimateRequest) {
  return request<SolarEstimateResponse>('/energy/solar-estimate', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── AI Assistant Chat (SolarMate AI) ──────────────────────────────

export function sendChatMessage(
  message: string,
  history: { role: 'user' | 'assistant'; content: string }[] = [],
  sessionId?: string
) {
  return request<{
    session_id: string;
    answer: string;
    data_sources: string[];
    tool_calls: string[];
    error?: string | null;
  }>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history, session_id: sessionId }),
  });
}

export function fetchChatHistory(sessionId: string, limit = 50) {
  return request<{
    session_id: string;
    messages: {
      id?: number;
      session_id: string;
      role: 'user' | 'assistant';
      content: string;
      data_sources?: string[];
      tool_calls?: string[];
      created_at?: string;
    }[];
    count: number;
  }>(`/chat/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
}

export function deleteChatHistory(sessionId: string) {
  return request<{ status: string; session_id: string }>(
    `/chat/history?session_id=${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' }
  );
}

// ── Authentication & Access Control ──────────────────────────────

export interface LoginResponse {
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  user: import('../types').UserProfile;
  message?: string;
}

export function loginApi(email: string, password: string) {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function signupApi(email: string, password: string, full_name?: string) {
  return request<LoginResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password, full_name }),
  });
}

export function getMeApi() {
  return request<import('../types').UserProfile>('/auth/me');
}

export function forgotPasswordApi(email: string, redirectUrl?: string) {
  return request<{ status: string; message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email, redirect_url: redirectUrl }),
  });
}

export function resetPasswordApi(new_password: string) {
  return request<{ status: string; message: string }>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ new_password }),
  });
}

// ── Admin Management ──────────────────────────────────────────────

export function getAdminUsersApi(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : '';
  return request<{ users: import('../types').UserProfile[]; count: number }>(`/admin/users${q}`);
}

export function approveUserApi(userId: string, role?: 'admin' | 'user') {
  return request<import('../types').UserProfile>('/admin/approve', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role }),
  });
}

export function rejectUserApi(userId: string) {
  return request<import('../types').UserProfile>('/admin/reject', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  });
}

export function setUserRoleApi(userId: string, role: 'admin' | 'user') {
  return request<import('../types').UserProfile>('/admin/set-role', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role }),
  });
}

// ── Health ────────────────────────────────────────────────────────

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/`, { signal: AbortSignal.timeout(5000) });
    return res.ok;
  } catch {
    return false;
  }
}

export { ApiError };
