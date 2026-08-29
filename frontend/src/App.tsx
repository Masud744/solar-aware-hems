import React, { useState, useEffect, useCallback } from 'react';
import type { View, HourlyForecastData, DeviceStatus, LoadSource, RiskMargin } from './types';
import { useTheme } from './hooks/useTheme';
import { useTelemetry } from './hooks/useTelemetry';
import { useDeviceControl } from './hooks/useDeviceControl';
import { useAuth, AuthProvider } from './hooks/useAuth';
import { forecastCache } from './api/forecastCache';
import { NavRail, MobileNav } from './components/layout/Navigation';
import { PowerHero } from './components/home/PowerHero';
import { SensorStrip } from './components/home/SensorGrid';
import { HorizonOutlookChart } from './components/home/HorizonOutlookChart';
import { EnergyFlow } from './components/home/EnergyFlow';
import { ApplianceControlsPreview } from './components/home/ApplianceControlsPreview';
import { WeatherContext } from './components/home/WeatherContext';
import { EnergyPage } from './components/energy/EnergyPage';
import { AppliancesPage } from './components/appliances/AppliancesPage';
import { ForecastPage } from './components/forecast/ForecastPage';
import { InsightsPage } from './components/insights/InsightsPage';
import { HistoryPage } from './components/history/HistoryPage';
import { SettingsPage } from './components/settings/SettingsPage';
import { AssistantPage } from './components/assistant/AssistantPage';
import { FloatingAssistant } from './components/assistant/FloatingAssistant';
import { AdminPage } from './components/admin/AdminPage';
import { LoginPage } from './components/auth/LoginPage';
import { SignUpPage } from './components/auth/SignUpPage';
import { ForgotPasswordPage } from './components/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './components/auth/ResetPasswordPage';
import { PendingApprovalScreen } from './components/auth/PendingApprovalScreen';
import { RejectedScreen } from './components/auth/RejectedScreen';
import { ChatSessionProvider } from './hooks/useChatSession';
import { getFreshness } from './utils/formatting';

function AppShell() {
  const [view, setView] = useState<View>('home');
  const { mode, setMode } = useTheme();
  const { reading, history, deviceStatus, loading: telemetryLoading, error, backendOnline } = useTelemetry();
  const { loadStates, setLoadSource, emergencyAllOff } = useDeviceControl(deviceStatus);
  const { isAdmin } = useAuth();

  // 24-Hour Forecast Horizon State (cached via forecastCache)
  const [timeline, setTimeline] = useState<HourlyForecastData[]>([]);
  const [riskMargin, setRiskMargin] = useState<RiskMargin | null>(null);
  const [firstHourSolar, setFirstHourSolar] = useState<import('./types').SolarPrediction | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // Fetch forecast timeline on mount and periodic 5-minute interval (with 30-min cache hit)
  const loadForecast = useCallback(async (force = false) => {
    setForecastLoading(true);
    setForecastError(null);
    try {
      const { timeline: rows, riskMargin: rm, firstHourSolar: fhs } = await forecastCache.build24HourTimeline(new Date(), { forceRefresh: force });
      setTimeline(rows);
      setRiskMargin(rm);
      setFirstHourSolar(fhs);
    } catch (err: any) {
      setTimeline([]);
      setFirstHourSolar(null);
      setForecastError(err?.message || 'Forecast stream currently unavailable.');
    } finally {
      setForecastLoading(false);
    }
  }, []);

  useEffect(() => {
    loadForecast();
    const interval = setInterval(() => loadForecast(false), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadForecast]);

  // Wrap setLoadSource to log real user commands and state changes
  const handleSetSource = async (key: string, source: LoadSource) => {
    await setLoadSource(key, source);
  };

  const handleEmergencyOff = async () => {
    await emergencyAllOff();
  };

  return (
    <>
      {/* Atmospheric background layer */}
      <div className="app-atmosphere" aria-hidden="true">
        <div className="app-atmosphere-overlay" />
      </div>

      <div className="shell">
        <NavRail activeView={view} onNavigate={setView} />
        <MobileNav activeView={view} onNavigate={setView} />
        <main className="shell-main">
          {view === 'home' && (
            <HomePage
              reading={reading}
              history={history}
              deviceStatus={deviceStatus}
              timeline={timeline}
              riskMargin={riskMargin}
              firstHourSolar={firstHourSolar}
              loadStates={loadStates}
              telemetryLoading={telemetryLoading}
              forecastLoading={forecastLoading}
              error={error}
              forecastError={forecastError}
              backendOnline={backendOnline}
              onSetSource={handleSetSource}
              onEmergencyOff={handleEmergencyOff}
              onNavigate={(targetView) => setView(targetView)}
            />
          )}
          {view === 'energy' && (
            <EnergyPage tariffRate={7.5} />
          )}
          {view === 'appliances' && (
            <AppliancesPage
              deviceStatus={deviceStatus}
              reading={reading}
              loadStates={loadStates}
              onSetSource={handleSetSource}
              onEmergencyOff={handleEmergencyOff}
              loading={telemetryLoading}
            />
          )}
          {view === 'forecast' && (
            <ForecastPage
              timeline={timeline}
              riskMargin={riskMargin}
              loading={forecastLoading}
              onRefresh={() => loadForecast(true)}
            />
          )}
          {view === 'insights' && (
            <InsightsPage />
          )}
          {view === 'history' && (
            <HistoryPage
              reading={reading}
              history={history}
              loading={telemetryLoading}
              tariffRate={7.5}
            />
          )}
          {view === 'assistant' && (
            <AssistantPage onNavigateToView={setView} />
          )}
          {view === 'settings' && (
            <SettingsPage
              theme={mode}
              onThemeChange={setMode}
              backendOnline={backendOnline}
            />
          )}
          {view === 'admin' && isAdmin && (
            <AdminPage />
          )}
        </main>
      </div>
      {view !== 'assistant' && (
        <FloatingAssistant onOpenFullPage={() => setView('assistant')} />
      )}
    </>
  );
}

function AuthRouter() {
  const { isAuthenticated, isApproved, isPending, isRejected, authScreen, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-3)' }}>
          <div className="spinner" style={{ width: '32px', height: '32px', margin: '0 auto 12px auto' }} />
          <div style={{ fontSize: '0.875rem' }}>Authenticating SolarMate...</div>
        </div>
      </div>
    );
  }

  // Not authenticated -> Render auth screen
  if (!isAuthenticated) {
    if (authScreen === 'signup') return <SignUpPage />;
    if (authScreen === 'forgot-password') return <ForgotPasswordPage />;
    if (authScreen === 'reset-password') return <ResetPasswordPage />;
    return <LoginPage />;
  }

  // Authenticated but pending admin approval -> Show Pending Screen
  if (isPending) {
    return <PendingApprovalScreen />;
  }

  // Authenticated but rejected by admin -> Show Rejected Screen
  if (isRejected) {
    return <RejectedScreen />;
  }

  // Authenticated and approved -> Render full application dashboard
  if (isApproved) {
    return (
      <ChatSessionProvider>
        <AppShell />
      </ChatSessionProvider>
    );
  }

  return <LoginPage />;
}

export function App() {
  return (
    <AuthProvider>
      <AuthRouter />
    </AuthProvider>
  );
}

interface HomePageProps {
  reading: ReturnType<typeof useTelemetry>['reading'];
  history: ReturnType<typeof useTelemetry>['history'];
  deviceStatus: DeviceStatus | null;
  timeline: HourlyForecastData[];
  riskMargin: RiskMargin | null;
  firstHourSolar: import('./types').SolarPrediction | null;
  loadStates: ReturnType<typeof useDeviceControl>['loadStates'];
  telemetryLoading: boolean;
  forecastLoading: boolean;
  error: string | null;
  forecastError: string | null;
  backendOnline: boolean;
  onSetSource: (key: string, source: LoadSource) => Promise<void>;
  onEmergencyOff: () => Promise<void>;
  onNavigate?: (view: View) => void;
}

function HomePage({
  reading,
  history,
  deviceStatus,
  timeline,
  riskMargin,
  firstHourSolar,
  loadStates,
  telemetryLoading,
  forecastLoading,
  error,
  forecastError,
  backendOnline,
  onSetSource,
  onEmergencyOff,
  onNavigate,
}: HomePageProps) {
  return (
    <div className="home-dashboard">
      <PowerHero
        reading={reading}
        timeline={timeline}
        loading={telemetryLoading}
        backendOnline={backendOnline}
        error={error}
        onNavigateAppliances={() => onNavigate?.('appliances')}
      />

      <WeatherContext
        weather={firstHourSolar}
        loading={forecastLoading}
        error={forecastError}
      />

      <HorizonOutlookChart
        timeline={timeline}
        loading={forecastLoading}
        onNavigateForecast={() => onNavigate?.('forecast')}
      />

      <SensorStrip
        reading={reading}
        timeline={timeline}
        loading={telemetryLoading}
      />

      <ApplianceControlsPreview
        deviceStatus={deviceStatus}
        reading={reading}
        loadStates={loadStates}
        onSetSource={onSetSource}
        onEmergencyOff={onEmergencyOff}
        onNavigateAppliances={() => onNavigate?.('appliances')}
        loading={telemetryLoading}
      />

      <EnergyFlow
        deviceStatus={deviceStatus}
        reading={reading}
      />
    </div>
  );
}
