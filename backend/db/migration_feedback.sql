-- ─── Migration: "Was this helpful?" feedback ─────────────────────────────────
-- Run this in the Supabase SQL Editor on an EXISTING project.
-- It only adds a new table and does not drop or modify existing data.

-- Captures the 1-5 star rating shown under each bot reply, plus an optional
-- follow-up comment for low ratings. Ratings at or below
-- LOW_RATING_ESCALATION_THRESHOLD (default 3) also trigger a Smart Agent
-- Handoff (see escalation.py, reason "low_rating").
create table if not exists message_feedback (
    id          uuid primary key default gen_random_uuid(),
    session_id  text not null,
    question    text not null,
    answer      text not null,
    rating      int not null check (rating between 1 and 5),
    comment     text,
    created_at  timestamptz default now()
);

create index if not exists message_feedback_session_idx
    on message_feedback (session_id, created_at);
