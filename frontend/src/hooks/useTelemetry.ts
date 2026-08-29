import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchTelemetryLatest, fetchTelemetryHistory, fetchDeviceStatus, checkBackendHealth } from '../api/client';
import { TELEMETRY_POLL_MS, DEVICE_STATUS_POLL_MS } from '../utils/constants';
import type { SensorReading, DeviceStatus } from '../types';

interface TelemetryState {
  reading: SensorReading | null;
  history: SensorReading[];
  deviceStatus: DeviceStatus | null;
  loading: boolean;
  error: string | null;
  backendOnline: boolean;
}

export function useTelemetry() {
  const [state, setState] = useState<TelemetryState>({
    reading: null,
    history: [],
    deviceStatus: null,
    loading: true,
    error: null,
    backendOnline: true,
  });

  const mountedRef = useRef(true);

  const fetchAll = useCallback(async () => {
    try {
      const [telRes, histRes, devRes] = await Promise.all([
        fetchTelemetryLatest(),
        fetchTelemetryHistory(100).catch(() => ({ readings: [] })),
        fetchDeviceStatus(),
      ]);
      if (!mountedRef.current) return;
      setState(prev => ({
        ...prev,
        reading: telRes.reading,
        history: histRes.readings || [],
        deviceStatus: devRes,
        loading: false,
        error: null,
        backendOnline: true,
      }));
    } catch (err) {
      if (!mountedRef.current) return;
      // Check if backend is reachable at all
      const online = await checkBackendHealth();
      setState(prev => ({
        ...prev,
        loading: false,
        error: online
          ? 'Failed to fetch telemetry'
          : 'Backend unavailable',
        backendOnline: online,
      }));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    fetchAll();

    // Poll telemetry
    const telInterval = setInterval(fetchAll, TELEMETRY_POLL_MS);

    return () => {
      mountedRef.current = false;
      clearInterval(telInterval);
    };
  }, [fetchAll]);

  const refetch = useCallback(() => { fetchAll(); }, [fetchAll]);

  return { ...state, refetch };
}

/** Separate hook for device status polling at a faster rate */
export function useDeviceStatusPoll() {
  const [status, setStatus] = useState<DeviceStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const res = await fetchDeviceStatus();
        if (mounted) setStatus(res);
      } catch { /* silent on poll failure */ }
    };
    poll();
    const interval = setInterval(poll, DEVICE_STATUS_POLL_MS);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return status;
}
