import React, { useState, useEffect, useRef } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { useChatSession } from '../../hooks/useChatSession';
import type { DataHonestyTagType } from '../../types';

interface Props {
  onOpenFullPage?: () => void;
}

const POPULAR_QUESTIONS = [
  "Current power & temperature",
  "Solar forecast next hour",
  "Can I run washing machine now?",
  "Energy used today",
];

export function FloatingAssistant({ onOpenFullPage }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const { messages, loading, sendMessage } = useChatSession();
  const [inputValue, setInputValue] = useState('');

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [isOpen, messages, loading]);

  const handleSend = async (text?: string) => {
    const query = (text ?? inputValue).trim();
    if (!query || loading) return;
    setInputValue('');
    await sendMessage(query);
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <div className="floating-assistant-btn-wrapper">
        <button
          className="floating-assistant-toggle"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label="Toggle SolarMate AI Assistant"
        >
          <span style={{ fontSize: '1.15rem' }}>⚡</span>
          <span>{isOpen ? 'Close Assistant' : 'Ask SolarMate AI'}</span>
        </button>
      </div>

      {/* Floating Chat Modal / Popover */}
      {isOpen && (
        <div className="floating-assistant-modal glass">
          {/* Header */}
          <div
            className="floating-header"
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(0, 0, 0, 0.2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem' }}>⚡</span>
              <div>
                <strong style={{ fontSize: '0.9375rem', color: '#fff' }}>SolarMate AI</strong>
                <div style={{ fontSize: '0.6875rem', color: '#34d399', fontWeight: 600 }}>● Online (Groq)</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {onOpenFullPage && (
                <button
                  className="btn-icon"
                  onClick={() => {
                    setIsOpen(false);
                    onOpenFullPage();
                  }}
                  title="Expand to Full Page"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-3)',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    padding: '4px 6px',
                  }}
                >
                  ⤢ Full Page
                </button>
              )}
              <button
                className="btn-icon"
                onClick={() => setIsOpen(false)}
                title="Close"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-3)',
                  cursor: 'pointer',
                  fontSize: '1.1rem',
                  padding: '2px 6px',
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages list */}
          <div
            className="floating-messages"
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {messages.map((m) => {
              const isUser = m.role === 'user';
              return (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    justifyContent: isUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '85%',
                      padding: '10px 14px',
                      borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                      background: isUser ? '#2563eb' : 'var(--bg-panel, rgba(30, 41, 59, 0.8))',
                      color: '#fff',
                      fontSize: '0.875rem',
                      lineHeight: '1.45',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      border: isUser ? 'none' : '1px solid var(--border)',
                    }}
                  >
                    {m.content}

                    {(!isUser && m.data_sources && m.data_sources.length > 0) && (
                      <div style={{ marginTop: '6px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {m.data_sources.map((ds) => {
                          const cleanType = ds.replace(/\[|\]/g, '') as DataHonestyTagType;
                          return <DataHonestyTag key={ds} type={cleanType || 'CALCULATED'} size="sm" />;
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--text-3)', fontSize: '0.8125rem' }}>
                <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                <span>Assistant thinking…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Questions */}
          <div
            style={{
              padding: '6px 12px',
              display: 'flex',
              gap: '6px',
              overflowX: 'auto',
              whiteSpace: 'nowrap',
              background: 'rgba(0, 0, 0, 0.15)',
            }}
          >
            {POPULAR_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                style={{
                  fontSize: '0.7rem',
                  padding: '4px 8px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: 'var(--text-2)',
                  cursor: 'pointer',
                }}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div
            style={{
              padding: '10px 12px',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              gap: '8px',
              background: 'rgba(0, 0, 0, 0.25)',
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type your question…"
              disabled={loading}
              style={{
                flex: 1,
                height: '36px',
                padding: '0 12px',
                borderRadius: '18px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border)',
                color: '#fff',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || loading}
              style={{
                height: '36px',
                padding: '0 14px',
                borderRadius: '18px',
                background: 'var(--solar, #f59e0b)',
                color: '#111827',
                fontWeight: 700,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
