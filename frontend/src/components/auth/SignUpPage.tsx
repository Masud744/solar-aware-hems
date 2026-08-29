import React, { useState } from 'react';
import { AuthLayout } from './AuthLayout';
import { useAuth } from '../../hooks/useAuth';

export function SignUpPage() {
  const { signup, loading, error, setAuthScreen, clearError } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please fill in all required fields.');
      return;
    }

    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match. Please verify.');
      return;
    }

    try {
      await signup(email.trim(), password, fullName.trim());
    } catch {
      // Error handled in useAuth
    }
  };

  const displayError = localError || error;

  return (
    <AuthLayout
      title="Create Account"
      subtitle="Register for SolarMate access"
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Notice badge explaining approval workflow */}
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--r-md, 10px)',
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            color: '#fbbf24',
            fontSize: '0.78125rem',
            lineHeight: 1.45,
          }}
        >
          🛡️ <strong>Access Notice:</strong> New accounts require administrator approval before dashboard access is granted.
        </div>

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
            Full Name
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="John Doe"
            autoComplete="name"
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border, rgba(255, 255, 255, 0.15))',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
            }}
          />
        </div>

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
            Email Address *
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
            }}
          />
        </div>

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
            Password *
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 6 characters"
            required
            minLength={6}
            autoComplete="new-password"
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border, rgba(255, 255, 255, 0.15))',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
            }}
          />
        </div>

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
            Confirm Password *
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter password"
            required
            minLength={6}
            autoComplete="new-password"
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border, rgba(255, 255, 255, 0.15))',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
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
              <span>Registering Account...</span>
            </>
          ) : (
            <span>Create Account</span>
          )}
        </button>

        <div style={{ textAlign: 'center', marginTop: '10px' }}>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-3, #64748b)' }}>
            Already have an account?{' '}
          </span>
          <button
            type="button"
            onClick={() => {
              clearError();
              setAuthScreen('login');
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
            Sign In
          </button>
        </div>
      </form>
    </AuthLayout>
  );
}
