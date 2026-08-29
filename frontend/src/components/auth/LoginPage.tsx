import React, { useState } from 'react';
import { AuthLayout } from './AuthLayout';
import { useAuth } from '../../hooks/useAuth';

export function LoginPage() {
  const { login, loading, error, setAuthScreen, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    try {
      await login(email.trim(), password);
    } catch (err: any) {
      // Error handled in useAuth
    }
  };

  const displayError = localError || error;

  return (
    <AuthLayout
      title="Welcome to SolarMate"
      subtitle="Sign in to access your SolarMate dashboard"
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {displayError && (
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              color: '#f87171',
              fontSize: '0.85rem',
              lineHeight: 1.4,
            }}
          >
            ⚠️ {displayError}
          </div>
        )}

        <div>
          <label
            style={{
              display: 'block',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--text-2, #94a3b8)',
              marginBottom: '6px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoComplete="email"
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border, rgba(255, 255, 255, 0.15))',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
              transition: 'border-color 0.2s ease',
            }}
          />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'var(--text-2, #94a3b8)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Password
            </label>
            <button
              type="button"
              onClick={() => {
                clearError();
                setAuthScreen('forgot-password');
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--solar, #f59e0b)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Forgot password?
            </button>
          </div>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            autoComplete="current-password"
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border, rgba(255, 255, 255, 0.15))',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
              transition: 'border-color 0.2s ease',
            }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary"
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: 'var(--r-md, 10px)',
            background: 'linear-gradient(135deg, var(--solar, #f59e0b), #d97706)',
            color: '#111827',
            fontWeight: 700,
            fontSize: '0.9375rem',
            border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
            marginTop: '8px',
            boxShadow: '0 4px 16px rgba(245, 158, 11, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
        >
          {loading ? (
            <>
              <span className="spinner" style={{ width: '16px', height: '16px' }} />
              <span>Signing In...</span>
            </>
          ) : (
            <span>Sign In</span>
          )}
        </button>

        <div style={{ textAlign: 'center', marginTop: '12px' }}>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-3, #64748b)' }}>
            Don't have an account?{' '}
          </span>
          <button
            type="button"
            onClick={() => {
              clearError();
              setAuthScreen('signup');
            }}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--solar, #f59e0b)',
              fontSize: '0.8125rem',
              fontWeight: 700,
              cursor: 'pointer',
              padding: 0,
            }}
          >
            Create an Account
          </button>
        </div>
      </form>
    </AuthLayout>
  );
}
