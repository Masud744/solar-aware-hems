import React, { useState } from 'react';
import { AuthLayout } from './AuthLayout';
import { useAuth } from '../../hooks/useAuth';

export function ResetPasswordPage() {
  const { resetPassword, setAuthScreen, clearError } = useAuth();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (newPassword.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const msg = await resetPassword(newPassword);
      setSuccessMessage(msg || 'Password updated successfully! You can now log in.');
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to update password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Set New Password"
      subtitle="Enter a secure new password for your account"
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {successMessage ? (
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--r-md, 10px)',
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: '#34d399',
                fontSize: '0.85rem',
                lineHeight: 1.4,
                marginBottom: '16px',
              }}
            >
              ✅ {successMessage}
            </div>
            <button
              type="button"
              onClick={() => {
                clearError();
                setAuthScreen('login');
              }}
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
                cursor: 'pointer',
              }}
            >
              Proceed to Sign In
            </button>
          </div>
        ) : (
          <>
            {errorMessage && (
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
                ⚠️ {errorMessage}
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
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
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
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
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
                  <span>Updating Password...</span>
                </>
              ) : (
                <span>Update Password</span>
              )}
            </button>

            <div style={{ textAlign: 'center', marginTop: '10px' }}>
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
                ← Back to Sign In
              </button>
            </div>
          </>
        )}
      </form>
    </AuthLayout>
  );
}
