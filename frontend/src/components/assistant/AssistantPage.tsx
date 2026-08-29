import React, { useState, useEffect, useRef } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { useChatSession } from '../../hooks/useChatSession';
import type { DataHonestyTagType } from '../../types';

interface Props {
  onNavigateToView?: (view: any) => void;
}

const QUICK_SUGGESTIONS = [
  "What is my current power consumption?",
  "What is the current room temperature?",
  "How much solar power is expected in the next hour?",
  "What is the conservative load forecast?",
  "Can I run a 1.5 kW heater for 2 hours now?",
  "When is the best time to run my washing machine?",
  "How much energy did I use today?",
  "Update today's solar estimate to 3 kWh",
];

export function AssistantPage({ onNavigateToView }: Props) {
  const { messages, loading, errorMessage, sendMessage, clearHistory } = useChatSession();
  const [inputValue, setInputValue] = useState('');

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const rawText = (textToSend ?? inputValue).trim();
    if (!rawText || loading) return;
    setInputValue('');
    await sendMessage(rawText);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="page assistant-page" style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>
      {/* 1. Header */}
      <div className="page-header" style={{ marginBottom: '16px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              AI CONVERSATIONAL DECISION & INFORMATION ASSISTANT
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>SolarMate AI</span>
              <span className="badge-online" style={{ fontSize: '0.75rem', padding: '3px 8px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontWeight: 600 }}>
                ● Active
              </span>
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Ask me about live telemetry, solar forecasts, appliance safety, and energy usage.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DataHonestyTag type="CALCULATED" size="md" tooltip="Assistant uses controlled backend tools with strict provenance tracking" />
            <button
              className="btn-secondary"
              onClick={clearHistory}
              style={{ fontSize: '0.8125rem', padding: '6px 12px' }}
              title="Reset conversation history"
            >
              🗑 Clear Chat
            </button>
          </div>
        </div>
      </div>

      {/* 2. Main Chat Container */}
      <div
        className="assistant-chat-container glass"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderRadius: 'var(--r-lg)',
          border: '1px solid var(--border)',
          background: 'var(--bg-card, rgba(19, 24, 38, 0.7))',
        }}
      >
        {/* Messages Stream */}
        <div
          className="assistant-messages-stream"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`chat-bubble-row ${isUser ? 'user-row' : 'assistant-row'}`}
                style={{
                  display: 'flex',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                  gap: '10px',
                }}
              >
                {!isUser && (
                  <div
                    className="assistant-avatar"
                    style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, var(--solar), #f59e0b)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '1rem',
                      flexShrink: 0,
                      boxShadow: '0 2px 8px rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    ⚡
                  </div>
                )}

                <div
                  className={`chat-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}
                  style={{
                    maxWidth: '82%',
                    padding: '14px 18px',
                    borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    background: isUser
                      ? 'linear-gradient(135deg, #2563eb, #1d4ed8)'
                      : 'var(--bg-panel, rgba(30, 41, 59, 0.75))',
                    color: '#fff',
                    border: isUser ? 'none' : '1px solid var(--border)',
                    boxShadow: '0 4px 14px rgba(0, 0, 0, 0.18)',
                    lineHeight: '1.55',
                    fontSize: '0.9375rem',
                  }}
                >
                  {/* Content with basic markdown formatting */}
                  <div className="chat-markdown-body" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {msg.content}
                  </div>

                  {/* Tool Calls & Data Sources Indicator */}
                  {(!isUser && ((msg.data_sources && msg.data_sources.length > 0) || (msg.tool_calls && msg.tool_calls.length > 0))) && (
                    <div
                      className="chat-provenance-footer"
                      style={{
                        marginTop: '10px',
                        paddingTop: '8px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                        display: 'flex',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '6px',
                        fontSize: '0.75rem',
                      }}
                    >
                      {msg.data_sources?.map((ds) => {
                        const cleanType = ds.replace(/\[|\]/g, '') as DataHonestyTagType;
                        return (
                          <DataHonestyTag key={ds} type={cleanType || 'CALCULATED'} size="sm" />
                        );
                      })}

                      {msg.tool_calls?.map((tc) => (
                        <span
                          key={tc}
                          className="mono"
                          style={{
                            fontSize: '0.6875rem',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: 'rgba(255, 255, 255, 0.06)',
                            color: 'var(--text-3, #94a3b8)',
                          }}
                        >
                          🔧 {tc}
                        </span>
                      ))}
                    </div>
                  )}

                  <div
                    style={{
                      fontSize: '0.6875rem',
                      color: isUser ? 'rgba(255, 255, 255, 0.65)' : 'var(--text-3, #64748b)',
                      marginTop: '6px',
                      textAlign: 'right',
                    }}
                  >
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                {isUser && (
                  <div
                    className="user-avatar"
                    style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.9rem',
                      flexShrink: 0,
                    }}
                  >
                    👤
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="chat-bubble-row assistant-row" style={{ display: 'flex', gap: '10px' }}>
              <div
                className="assistant-avatar"
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--solar), #f59e0b)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1rem',
                }}
              >
                ⚡
              </div>
              <div
                className="chat-bubble assistant-bubble"
                style={{
                  padding: '12px 18px',
                  borderRadius: '18px 18px 18px 4px',
                  background: 'var(--bg-panel, rgba(30, 41, 59, 0.75))',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'var(--text-2)',
                  fontSize: '0.875rem',
                }}
              >
                <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                <span>Consulting SolarMate decision engine & sensor tools…</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Chips */}
        <div
          className="assistant-suggestions-bar"
          style={{
            padding: '8px 16px',
            background: 'rgba(0, 0, 0, 0.15)',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            display: 'flex',
            gap: '8px',
            overflowX: 'auto',
            whiteSpace: 'nowrap',
          }}
        >
          {QUICK_SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              className="suggestion-chip"
              onClick={() => handleSendMessage(sug)}
              disabled={loading}
              style={{
                fontSize: '0.75rem',
                padding: '5px 10px',
                borderRadius: '14px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: 'var(--text-2, #cbd5e1)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {sug}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div
          className="assistant-input-bar"
          style={{
            padding: '14px 16px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(0, 0, 0, 0.25)',
          }}
        >
          <input
            ref={inputRef}
            type="text"
            className="input-field"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about live power, solar forecast, appliance safety, or energy usage…"
            disabled={loading}
            style={{
              flex: 1,
              height: '42px',
              padding: '0 16px',
              borderRadius: '21px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border)',
              color: '#fff',
              fontSize: '0.9375rem',
              outline: 'none',
            }}
          />

          <button
            className="btn-primary"
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || loading}
            style={{
              height: '42px',
              padding: '0 20px',
              borderRadius: '21px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            <span>Send</span>
            <span>➤</span>
          </button>
        </div>
      </div>
    </div>
  );
}
