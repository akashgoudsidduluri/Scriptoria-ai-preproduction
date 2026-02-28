-- ============================================================
-- SCRIPTORIA - Supabase Database Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- ─────────────────────────────────────────
-- 1. USERS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 2. SESSIONS TABLE
-- Tracks active login sessions per user
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    expires_at    TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

-- ─────────────────────────────────────────
-- 3. CHAT HISTORY TABLE
-- Stores every story prompt + AI response
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.chat_history (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    prompt     TEXT NOT NULL,
    response   TEXT NOT NULL,
    title      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 4. CHARACTERS TABLE (Character Bible)
-- Stores detailed descriptions of recurring characters
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.characters (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    personality TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 5. INDEXES (for fast lookups)
-- ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sessions_user_id      ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token        ON public.sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id  ON public.chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_characters_user_id    ON public.characters(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email           ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username        ON public.users(username);

-- ─────────────────────────────────────────
-- 6. DISABLE ROW LEVEL SECURITY
-- ─────────────────────────────────────────
ALTER TABLE public.users        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions     DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.characters   DISABLE ROW LEVEL SECURITY;

