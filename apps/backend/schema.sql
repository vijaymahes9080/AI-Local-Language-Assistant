-- Enable the vector extension for RAG embedding storage
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ==========================================
-- 1. USERS & AUTHN/AUTHZ
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- 'user', 'moderator', 'admin'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_info TEXT,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ==========================================
-- 2. LANGUAGE & VOICE PROFILES
-- ==========================================
CREATE TABLE IF NOT EXISTS language_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    preferred_language VARCHAR(50) NOT NULL DEFAULT 'english', -- 'tamil', 'hindi', 'telugu', 'malayalam', 'kannada', 'bengali', 'english'
    preferred_dialect VARCHAR(100),
    transliteration_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    accessibility_mode VARCHAR(50) DEFAULT 'standard', -- 'standard', 'dyslexia', 'high_contrast', 'large_text'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS voice_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    gender VARCHAR(20) NOT NULL DEFAULT 'neutral', -- 'male', 'female', 'neutral'
    speech_speed REAL NOT NULL DEFAULT 1.0,        -- 0.5 to 2.0
    voice_tone VARCHAR(50) DEFAULT 'default',
    age_mode VARCHAR(20) DEFAULT 'standard',       -- 'elder', 'child', 'standard'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ==========================================
-- 3. CHAT MESSAGES (Partitioned by range of created_at)
-- ==========================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID NOT NULL,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    language VARCHAR(50) NOT NULL DEFAULT 'english',
    audio_url TEXT,
    prompt_injection_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create concrete partitions for messages (2026/2027)
CREATE TABLE messages_y2026m06 PARTITION OF messages
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

CREATE TABLE messages_y2026m07 PARTITION OF messages
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');

CREATE TABLE messages_default PARTITION OF messages DEFAULT;

-- ==========================================
-- 4. AGENT MEMORY & KNOWLEDGE (RAG)
-- ==========================================
CREATE TABLE IF NOT EXISTS user_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    significance REAL DEFAULT 0.5, -- Importance score (0.0 to 1.0)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, memory_key)
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- Vector embeddings (1536 dims for OpenAI/Gemini models)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ==========================================
-- 5. AUDIT LOGS (Partitioned by range of created_at)
-- ==========================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    request_payload TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create concrete partitions for audit logs
CREATE TABLE audit_logs_y2026m06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

CREATE TABLE audit_logs_y2026m07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');

CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

-- ==========================================
-- 6. SYSTEM STABILITY: FEATURE FLAGS & ANALYTICS
-- ==========================================
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_key VARCHAR(100) UNIQUE NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL, -- 'api_latency', 'token_usage', 'asr_wer', 'safety_alert'
    metric_name VARCHAR(255) NOT NULL,
    metric_value REAL NOT NULL,
    metric_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ==========================================
-- INDEXES & PERFORMANCE OPTIMIZATIONS
-- ==========================================
-- Composite indexes for query filters
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_memory_user ON user_memory(user_id);
CREATE INDEX idx_analytics_event ON system_analytics(event_type, created_at);

-- HNSW Vector Index for efficient cosine similarity queries on RAG knowledge
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_items USING hnsw (embedding vector_cosine_ops);
