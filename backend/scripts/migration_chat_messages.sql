-- Migration: Persistent Chat Messages Table for SolarMate AI Assistant
-- Execute this query in the Supabase Dashboard -> SQL Editor

CREATE TABLE IF NOT EXISTS chat_messages (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          TEXT NOT NULL,
    user_id             UUID NULL, -- Reserved for future Supabase Auth integration
    role                TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content             TEXT NOT NULL,
    data_sources        JSONB DEFAULT '[]'::jsonb,
    tool_calls          JSONB DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast chronological message loading per session
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id, created_at ASC);

-- Comment documenting purpose
COMMENT ON TABLE chat_messages IS 'Stores persistent conversation turns between users and SolarMate AI assistant. Partitioned by session_id and ready for future user_id auth association.';
