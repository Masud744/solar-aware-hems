import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

export function PendingApprovalScreen() {
  const { user, refreshProfile, logout } = useAuth();
  const [checking, setChecking] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleRefresh = async () => {
    setChecking(true);
    setFeedback(null);
    try {
      const fresh = await refreshProfile();
      if (fresh?.status === 'approved') {
        setFeedback('Account approved! Entering dashboard...');
      } else {
        setFeedback('Status refreshed. Still awaiting administrator approval.');
      }
    } catch {
      setFeedback('Could not reach server to check approval status.');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        position: 'relative',
        zIndex: 1,
      }}
    >
      <div
        className="glass"
        style={{
          width: '100%',
          maxWidth: '480px',
          borderRadius: 'var(--r-xl, 20px)',
          background: 'var(--bg-card, #131826)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7)',
          padding: '40px 32px',
          textAlign: 'center',
          position: 'relative',
        }}
      >
        {/* Pulsing Icon */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '68px',
            height: '68px',
            borderRadius: '50%',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '2px solid var(--solar, #f59e0b)',
            fontSize: '2rem',
            marginBottom: '20px',
            boxShadow: '0 0 30px rgba(245, 158, 11, 0.3)',
          }}
        >
          ⏳
        </div>

        <div
          style={{
            fontSize: '0.6875rem',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: 'var(--solar, #f59e0b)',
            marginBottom: '6px',
          }}
        >
          ACCOUNT STATUS: PENDING APPROVAL
        </div>

        <h1
          className="t-display"
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            margin: '0 0 12px 0',
            color: '#fff',
          }}
        >
          Access Pending Approval
        </h1>

        <p
          style={{
            fontSize: '0.9375rem',
            color: 'var(--text-2, #94a3b8)',
            lineHeight: 1.55,
            margin: '0 0 24px 0',
          }}
        >
          Your account is pending administrator approval. Please wait until your access is approved.
        </p>

        {/* User Card */}
        <div
          style={{
            padding: '16px',
            borderRadius: 'var(--r-lg, 14px)',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border, rgba(255, 255, 255, 0.1))',
            textAlign: 'left',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-3, #64748b)' }}>Email:</span>
            <strong style={{ fontSize: '0.8125rem', color: '#fff' }}>{user?.email}</strong>
          </div>
          {user?.full_name && (
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-3, #64748b)' }}>Name:</span>
              <span style={{ fontSize: '0.8125rem', color: '#fff' }}>{user.full_name}</span>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-3, #64748b)' }}>Approval Status:</span>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '10px',
                background: 'rgba(245, 158, 11, 0.18)',
                color: '#fbbf24',
              }}
            >
              ⏳ Pending Admin Review
            </span>
          </div>
        </div>

        {feedback && (
          <div
            style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-2, #94a3b8)',
              fontSize: '0.8125rem',
              marginBottom: '16px',
            }}
          >
            ℹ️ {feedback}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button
            onClick={handleRefresh}
            disabled={checking}
            className="btn-primary"
            style={{
              padding: '12px',
              borderRadius: 'var(--r-md, 10px)',
              background: 'linear-gradient(135deg, var(--solar, #f59e0b), #d97706)',
              color: '#111827',
              fontWeight: 700,
              fontSize: '0.9375rem',
              border: 'none',
              cursor: checking ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
            }}
          >
            {checking ? (
              <>
                <span className="spinner" style={{ width: '16px', height: '16px' }} />
                <span>Checking Approval...</span>
              </>
            ) : (
              <span>🔄 Refresh Approval Status</span>
            )}
          </button>

          <button
            onClick={logout}
            className="btn-secondary"
            style={{
              padding: '10px',
              fontSize: '0.875rem',
              color: 'var(--text-2, #94a3b8)',
              border: '1px solid var(--border)',
            }}
          >
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
}
