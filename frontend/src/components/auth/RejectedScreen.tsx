import React from 'react';
import { useAuth } from '../../hooks/useAuth';

export function RejectedScreen() {
  const { user, logout } = useAuth();

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
          maxWidth: '460px',
          borderRadius: 'var(--r-xl, 20px)',
          background: 'var(--bg-card, #131826)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7)',
          padding: '40px 32px',
          textAlign: 'center',
          position: 'relative',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '2px solid #ef4444',
            fontSize: '2rem',
            marginBottom: '20px',
          }}
        >
          🚫
        </div>

        <h1
          className="t-display"
          style={{
            fontSize: '1.65rem',
            fontWeight: 800,
            margin: '0 0 12px 0',
            color: '#fff',
          }}
        >
          Access Denied
        </h1>

        <p
          style={{
            fontSize: '0.9375rem',
            color: 'var(--text-2, #94a3b8)',
            lineHeight: 1.5,
            margin: '0 0 24px 0',
          }}
        >
          Your account ({user?.email}) has been rejected by the administrator. You do not have permission to access the SolarMate dashboard.
        </p>

        <button
          onClick={logout}
          className="btn-primary"
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: 'var(--r-md, 10px)',
            background: 'rgba(239, 68, 68, 0.8)',
            color: '#fff',
            fontWeight: 700,
            fontSize: '0.9375rem',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Log Out
        </button>
      </div>
    </div>
  );
}
