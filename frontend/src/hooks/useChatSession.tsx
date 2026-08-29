import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { sendChatMessage, fetchChatHistory, deleteChatHistory } from '../api/client';
import { useAuth } from './useAuth';
import type { ChatMessage } from '../types';

const SESSION_KEY = 'solarmate_chat_session_id';
const MSGS_KEY_PREFIX = 'solarmate_chat_msgs_';

export const DEFAULT_WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome-default',
  role: 'assistant',
  content:
    "👋 Hello! I am your **SolarMate AI Conversational Assistant**.\n\n" +
    "Ask me about live telemetry, solar forecasts, appliance safety, and energy usage.\n\n" +
    "How can I help you today?",
  data_sources: [],
  tool_calls: [],
  timestamp: new Date(),
};

interface ChatSessionContextValue {
  sessionId: string;
  messages: ChatMessage[];
  loading: boolean;
  errorMessage: string | null;
  sendMessage: (text: string) => Promise<void>;
  clearHistory: () => Promise<void>;
}

const ChatSessionContext = createContext<ChatSessionContextValue | null>(null);

function getOrCreateSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY);
    if (existing && existing.trim()) return existing.trim();
    const newId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    localStorage.setItem(SESSION_KEY, newId);
    return newId;
  } catch {
    return `session-${Date.now()}`;
  }
}

function getStorageKey(userId: string | null, sessionId: string): string {
  const userSegment = userId ? `u_${userId}` : 'anon';
  return `${MSGS_KEY_PREFIX}${userSegment}_${sessionId}`;
}

function loadCachedMessages(userId: string | null, sessionId: string): ChatMessage[] {
  try {
    const key = getStorageKey(userId, sessionId);
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp || Date.now()),
        }));
      }
    }
  } catch {
    // Ignore JSON error
  }
  return [DEFAULT_WELCOME_MESSAGE];
}

function saveCachedMessages(userId: string | null, sessionId: string, msgs: ChatMessage[]) {
  try {
    const key = getStorageKey(userId, sessionId);
    localStorage.setItem(key, JSON.stringify(msgs));
  } catch {
    // Ignore storage quota error
  }
}

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const userId = user?.id || null;

  const [sessionId] = useState<string>(getOrCreateSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadCachedMessages(userId, sessionId));
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reload cache when user changes (e.g. login/logout)
  useEffect(() => {
    setMessages(loadCachedMessages(userId, sessionId));
  }, [userId, sessionId]);

  // Sync with persistent backend / Supabase history on mount & user change
  useEffect(() => {
    let isMounted = true;
    async function syncBackendHistory() {
      try {
        const res = await fetchChatHistory(sessionId, 50);
        if (isMounted && res.messages && res.messages.length > 0) {
          const remoteMsgs: ChatMessage[] = res.messages.map((m) => ({
            id: `db-${m.id || Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
            role: m.role,
            content: m.content,
            data_sources: m.data_sources || [],
            tool_calls: m.tool_calls || [],
            timestamp: new Date(m.created_at || Date.now()),
          }));
          setMessages(remoteMsgs);
          saveCachedMessages(userId, sessionId, remoteMsgs);
        }
      } catch {
        // Offline or table not yet migrated — seamlessly rely on localStorage cache
      }
    }

    syncBackendHistory();
    return () => {
      isMounted = false;
    };
  }, [sessionId, userId]);

  const sendMessage = useCallback(
    async (rawText: string) => {
      const trimmed = rawText.trim();
      if (!trimmed || loading) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };

      const updatedWithUser = [...messages, userMsg];
      setMessages(updatedWithUser);
      saveCachedMessages(userId, sessionId, updatedWithUser);
      setErrorMessage(null);
      setLoading(true);

      try {
        // Pass bounded recent conversation turns for context fallback
        const historyTurns = updatedWithUser.slice(-6).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res = await sendChatMessage(trimmed, historyTurns, sessionId);

        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
          role: 'assistant',
          content: res.answer,
          data_sources: res.data_sources || [],
          tool_calls: res.tool_calls || [],
          timestamp: new Date(),
        };

        const finalMessages = [...updatedWithUser, assistantMsg];
        setMessages(finalMessages);
        saveCachedMessages(userId, sessionId, finalMessages);
      } catch (err: any) {
        const errMsg = err?.message || 'Failed to communicate with SolarMate AI.';
        setErrorMessage(errMsg);
        const errorMsg: ChatMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error:** ${errMsg}\n\nPlease check your backend server connection.`,
          error: errMsg,
          timestamp: new Date(),
        };
        const withError = [...updatedWithUser, errorMsg];
        setMessages(withError);
        saveCachedMessages(userId, sessionId, withError);
      } finally {
        setLoading(false);
      }
    },
    [messages, loading, sessionId, userId]
  );

  const clearHistory = useCallback(async () => {
    const cleared = [DEFAULT_WELCOME_MESSAGE];
    setMessages(cleared);
    saveCachedMessages(userId, sessionId, cleared);
    setErrorMessage(null);
    try {
      await deleteChatHistory(sessionId);
    } catch {
      // Ignore background delete errors
    }
  }, [sessionId, userId]);

  const value: ChatSessionContextValue = {
    sessionId,
    messages,
    loading,
    errorMessage,
    sendMessage,
    clearHistory,
  };

  return <ChatSessionContext.Provider value={value}>{children}</ChatSessionContext.Provider>;
}

export function useChatSession(): ChatSessionContextValue {
  const ctx = useContext(ChatSessionContext);
  if (!ctx) {
    throw new Error('useChatSession must be used within a ChatSessionProvider');
  }
  return ctx;
}
