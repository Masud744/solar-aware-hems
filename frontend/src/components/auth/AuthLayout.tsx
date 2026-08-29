import React, { type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  title: string;
  subtitle: string;
}

export function AuthLayout({ children, title, subtitle }: Props) {
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
      {/* Background radial glow */}
      <div
        style={{
          position: 'fixed',
          top: '20%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(245, 158, 11, 0.12) 0%, rgba(14, 165, 233, 0.04) 50%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <div
        className="glass"
        style={{
          width: '100%',
          maxWidth: '440px',
          borderRadius: 'var(--r-xl, 20px)',
          background: 'var(--bg-card, #131826)',
          border: '1px solid var(--border, rgba(255, 255, 255, 0.12))',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.65)',
          padding: '36px 32px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '52px',
              height: '52px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(14, 165, 233, 0.2))',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              fontSize: '1.75rem',
              marginBottom: '14px',
              boxShadow: '0 8px 20px rgba(245, 158, 11, 0.25)',
            }}
          >
            ☀️
          </div>
          <div
            style={{
              fontSize: '0.6875rem',
              fontWeight: 800,
              letterSpacing: '0.12em',
              color: 'var(--solar, #f59e0b)',
              marginBottom: '4px',
            }}
          >
            SOLAR-INTEGRATED & RISK-AWARE ENERGY MANAGEMENT
          </div>
          <h1
            className="t-display"
            style={{
              fontSize: '1.65rem',
              fontWeight: 800,
              letterSpacing: '-0.02em',
              margin: '0 0 6px 0',
              color: 'var(--text-1, #fff)',
            }}
          >
            {title}
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-2, #94a3b8)', margin: 0 }}>
            {subtitle}
          </p>
        </div>

        {/* Content Body */}
        {children}
      </div>
    </div>
  );
}
