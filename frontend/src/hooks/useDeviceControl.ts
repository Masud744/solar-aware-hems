import { useState, useCallback, useRef, useEffect } from 'react';
import { sendDeviceControl, fetchDeviceStatus } from '../api/client';
import type { LoadSource, LoadTransitionState, DeviceStatus } from '../types';

interface LoadState {
  transition: LoadTransitionState;
  targetSource: LoadSource | null;
}

const CONFIRM_TIMEOUT_MS = 12000; // 12 seconds to confirm
const CONFIRM_POLL_MS = 1500;

export function useDeviceControl(deviceStatus: DeviceStatus | null) {
  const [loadStates, setLoadStates] = useState<Record<string, LoadState>>({
    load_1: { transition: 'idle', targetSource: null },
    load_2: { transition: 'idle', targetSource: null },
    load_3: { transition: 'idle', targetSource: null },
    load_4: { transition: 'idle', targetSource: null },
  });

  const timersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pollRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  // When deviceStatus changes, check if any switching loads got confirmed
  useEffect(() => {
    if (!deviceStatus) return;
    setLoadStates(prev => {
      const next = { ...prev };
      let changed = false;
      for (const loadKey of ['load_1', 'load_2', 'load_3', 'load_4'] as const) {
        const ls = next[loadKey];
        if (ls.transition === 'switching' && ls.targetSource) {
          const actual = deviceStatus[loadKey];
          if (actual === ls.targetSource) {
            next[loadKey] = { transition: 'confirmed', targetSource: ls.targetSource };
            changed = true;
            // Clear confirmed after 3s
            setTimeout(() => {
              setLoadStates(p => ({
                ...p,
                [loadKey]: { transition: 'idle', targetSource: null },
              }));
            }, 3000);
            // Clean up timers
            if (timersRef.current[loadKey]) clearTimeout(timersRef.current[loadKey]);
            if (pollRef.current[loadKey]) clearInterval(pollRef.current[loadKey]);
          }
        }
      }
      return changed ? next : prev;
    });
  }, [deviceStatus]);

  const setLoadSource = useCallback(async (loadKey: string, source: LoadSource) => {
    // Set sending state
    setLoadStates(prev => ({
      ...prev,
      [loadKey]: { transition: 'sending', targetSource: source },
    }));

    try {
      await sendDeviceControl({ [loadKey]: source });

      // Move to switching
      setLoadStates(prev => ({
        ...prev,
        [loadKey]: { transition: 'switching', targetSource: source },
      }));

      // Start polling for confirmation
      pollRef.current[loadKey] = setInterval(async () => {
        try {
          const status = await fetchDeviceStatus();
          if (status[loadKey as keyof DeviceStatus] === source) {
            setLoadStates(prev => ({
              ...prev,
              [loadKey]: { transition: 'confirmed', targetSource: source },
            }));
            clearInterval(pollRef.current[loadKey]);
            clearTimeout(timersRef.current[loadKey]);
            setTimeout(() => {
              setLoadStates(prev => ({
                ...prev,
                [loadKey]: { transition: 'idle', targetSource: null },
              }));
            }, 3000);
          }
        } catch { /* silent poll failure */ }
      }, CONFIRM_POLL_MS);

      // Timeout — if not confirmed in time, show error
      timersRef.current[loadKey] = setTimeout(() => {
        clearInterval(pollRef.current[loadKey]);
        setLoadStates(prev => {
          if (prev[loadKey].transition === 'switching') {
            return { ...prev, [loadKey]: { transition: 'error', targetSource: source } };
          }
          return prev;
        });
        // Auto-clear error after 5s
        setTimeout(() => {
          setLoadStates(prev => ({
            ...prev,
            [loadKey]: { transition: 'idle', targetSource: null },
          }));
        }, 5000);
      }, CONFIRM_TIMEOUT_MS);

    } catch {
      setLoadStates(prev => ({
        ...prev,
        [loadKey]: { transition: 'error', targetSource: source },
      }));
      setTimeout(() => {
        setLoadStates(prev => ({
          ...prev,
          [loadKey]: { transition: 'idle', targetSource: null },
        }));
      }, 5000);
    }
  }, []);

  const emergencyAllOff = useCallback(async () => {
    // Set all to sending
    setLoadStates({
      load_1: { transition: 'sending', targetSource: 'off' },
      load_2: { transition: 'sending', targetSource: 'off' },
      load_3: { transition: 'sending', targetSource: 'off' },
      load_4: { transition: 'sending', targetSource: 'off' },
    });

    try {
      await sendDeviceControl({
        load_1: 'off',
        load_2: 'off',
        load_3: 'off',
        load_4: 'off',
      });

      setLoadStates({
        load_1: { transition: 'switching', targetSource: 'off' },
        load_2: { transition: 'switching', targetSource: 'off' },
        load_3: { transition: 'switching', targetSource: 'off' },
        load_4: { transition: 'switching', targetSource: 'off' },
      });
    } catch {
      setLoadStates({
        load_1: { transition: 'error', targetSource: 'off' },
        load_2: { transition: 'error', targetSource: 'off' },
        load_3: { transition: 'error', targetSource: 'off' },
        load_4: { transition: 'error', targetSource: 'off' },
      });
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach(clearTimeout);
      Object.values(pollRef.current).forEach(clearInterval);
    };
  }, []);

  return { loadStates, setLoadSource, emergencyAllOff };
}
