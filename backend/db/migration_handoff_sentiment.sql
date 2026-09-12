-- ─── Migration: Smart Agent Handoff + Sentiment Analysis ─────────────────────
-- Run this in the Supabase SQL Editor on an EXISTING project.
-- It only adds new columns/tables and does not drop or modify existing data.

-- Frustration score (1-5) for human messages, set by the sentiment analysis
-- step. Null for AI messages and for rows created before this column existed.
alter table chat_history add column if not exists sentiment int;

-- Records every conversation handed off to a human, with the full transcript
-- captured at the moment of escalation.
create table if not exists escalations (
    id          uuid primary key default gen_random_uuid(),
    session_id  text not null,
    reason      text not null,
    transcript  jsonb not null,
    created_at  timestamptz default now()
);

create index if not exists escalations_session_idx
    on escalations (session_id, created_at);
