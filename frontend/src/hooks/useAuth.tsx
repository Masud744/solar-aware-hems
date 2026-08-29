import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  loginApi,
  signupApi,
  getMeApi,
  forgotPasswordApi,
  resetPasswordApi,
  setAuthToken,
  getAuthToken,
  ApiError,
} from '../api/client';
import type { UserProfile, AuthScreen } from '../types';

const USER_STORAGE_KEY = 'solarmate_user_profile';
const TOKEN_STORAGE_KEY = 'solarmate_auth_token';

interface AuthContextValue {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  authScreen: AuthScreen;
  isAuthenticated: boolean;
  isApproved: boolean;
  isPending: boolean;
  isRejected: boolean;
  isAdmin: boolean;
  setAuthScreen: (screen: AuthScreen) => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName?: string) => Promise<{ pending: boolean; message: string }>;
  logout: () => void;
  forgotPassword: (email: string) => Promise<string>;
  resetPassword: (newPassword: string) => Promise<string>;
  refreshProfile: () => Promise<UserProfile | null>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function getCachedProfile(): UserProfile | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(getCachedProfile);
  const [token, setTokenState] = useState<string | null>(getAuthToken);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');

  const saveSession = useCallback((newToken: string | null, newUser: UserProfile | null) => {
    setTokenState(newToken);
    setAuthToken(newToken);
    setUser(newUser);
    if (newUser && newToken) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(newUser));
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }, []);

  // Validate and sync fresh profile from backend /auth/me
  const refreshProfile = useCallback(async (): Promise<UserProfile | null> => {
    const activeToken = getAuthToken();
    if (!activeToken) {
      console.log('[useAuth] No active token found in storage.');
      setUser(null);
      localStorage.removeItem(USER_STORAGE_KEY);
      setLoading(false);
      return null;
    }
    try {
      console.log('[useAuth] Fetching fresh profile with token...');
      const fresh = await getMeApi();
      console.log('[useAuth] Fresh profile received:', {
        id: fresh.id,
        email: fresh.email,
        role: fresh.role,
        status: fresh.status,
      });
      setUser(fresh);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(fresh));
      return fresh;
    } catch (err: any) {
      console.warn('[useAuth] Profile refresh failed:', err);
      if (err instanceof ApiError && err.status === 401) {
        // Token expired or invalid
        saveSession(null, null);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [saveSession]);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      setLoading(true);
      try {
        console.log('[useAuth] Logging in:', email);
        const res = await loginApi(email, password);
        console.log('[useAuth] Login response received:', {
          hasToken: Boolean(res.access_token),
          user: res.user,
        });

        if (res.access_token && res.user) {
          saveSession(res.access_token, res.user);
          console.log('[useAuth] Authenticated user saved:', {
            id: res.user.id,
            email: res.user.email,
            role: res.user.role,
            status: res.user.status,
          });
        } else if (res.user) {
          setUser(res.user);
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(res.user));
        }
      } catch (err: any) {
        const msg = err?.message || 'Login failed. Please check your credentials.';
        console.warn('[useAuth] Login error:', msg, err);
        setError(msg);
        if (err?.data?.user) {
          setUser(err.data.user);
        }
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [saveSession]
  );

  const signup = useCallback(
    async (email: string, password: string, fullName?: string) => {
      setError(null);
      setLoading(true);
      try {
        const res = await signupApi(email, password, fullName);
        if (res.user) {
          setUser(res.user);
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(res.user));
          if (res.access_token) {
            saveSession(res.access_token, res.user);
          }
        }
        const isPending = res.user?.status === 'pending';
        return {
          pending: isPending,
          message:
            res.message ||
            (isPending
              ? 'Registration successful! Your account is pending administrator approval.'
              : 'Registration successful!'),
        };
      } catch (err: any) {
        const msg = err?.message || 'Registration failed. Please try again.';
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [saveSession]
  );

  const logout = useCallback(() => {
    console.log('[useAuth] Performing full logout and clearing storage.');
    saveSession(null, null);
    try {
      localStorage.removeItem(USER_STORAGE_KEY);
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // Ignore
    }
    setError(null);
    setAuthScreen('login');
  }, [saveSession]);

  const forgotPassword = useCallback(async (email: string) => {
    setError(null);
    try {
      const res = await forgotPasswordApi(email, `${window.location.origin}/reset-password`);
      return res.message;
    } catch (err: any) {
      const msg = err?.message || 'Failed to send password reset email.';
      setError(msg);
      throw err;
    }
  }, []);

  const resetPassword = useCallback(async (newPassword: string) => {
    setError(null);
    try {
      const res = await resetPasswordApi(newPassword);
      return res.message;
    } catch (err: any) {
      const msg = err?.message || 'Failed to update password.';
      setError(msg);
      throw err;
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const isAuthenticated = Boolean(token && user);
  const isApproved = user?.status === 'approved';
  const isPending = user?.status === 'pending';
  const isRejected = user?.status === 'rejected';
  const isAdmin = user?.role === 'admin' && isApproved;

  const value: AuthContextValue = {
    user,
    token,
    loading,
    error,
    authScreen,
    isAuthenticated,
    isApproved,
    isPending,
    isRejected,
    isAdmin,
    setAuthScreen,
    login,
    signup,
    logout,
    forgotPassword,
    resetPassword,
    refreshProfile,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
