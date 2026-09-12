-- ─── Enable pgvector extension ───────────────────────────────────────────────
create extension if not exists vector;

-- ─── Documents table (RAG knowledge base) ────────────────────────────────────
drop table if exists documents cascade;

create table documents (
    id          uuid primary key default gen_random_uuid(),
    content     text not null,
    embedding   vector(1536),
    metadata    jsonb default '{}'::jsonb,
    created_at  timestamptz default now()
);

create index if not exists documents_embedding_idx
    on documents
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists documents_metadata_idx
    on documents using gin (metadata);

-- Documents are read-only for the API. Only the service role (ingestion pipeline)
-- can insert. Public read access is safe — document content is not user-specific.
alter table documents enable row level security;
create policy "Public read access" on documents
    for select using (true);

-- ─── Chat history table (per-session conversation memory) ────────────────────
create table if not exists chat_history (
    id          uuid primary key default gen_random_uuid(),
    session_id  text not null,
    message     jsonb not null,
    created_at  timestamptz default now()
);

create index if not exists chat_history_session_idx
    on chat_history (session_id, created_at);

-- Frustration score (1-5) for human messages, set by the sentiment analysis
-- step. Null for AI messages and for rows created before this column existed.
alter table chat_history add column if not exists sentiment int;

-- NOTE ON RLS FOR chat_history:
-- Full per-user row isolation requires Supabase Auth (auth.uid() mapped to
-- session_id). The backend currently uses the service_role key which bypasses
-- RLS by design. Session isolation is enforced at the API layer — the
-- /history endpoint requires a valid API key and session UUIDs are
-- cryptographically random (128-bit), making enumeration infeasible.
--
-- To enable full RLS when Supabase Auth is added:
--   alter table chat_history enable row level security;
--   create policy "Users read own history" on chat_history
--       for select using (session_id = auth.uid()::text);
--   create policy "Users insert own messages" on chat_history
--       for insert with check (session_id = auth.uid()::text);

-- ─── Escalations table (Smart Agent Handoff) ─────────────────────────────────
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

-- ─── Match documents function ─────────────────────────────────────────────────
-- Default threshold (0.45) and count (6) match the Python retriever settings.
create or replace function match_documents (
    query_embedding  vector(1536),
    match_threshold  float default 0.45,
    match_count      int   default 6
)
returns table (
    id          uuid,
    content     text,
    metadata    jsonb,
    similarity  float
)
language sql stable
as $$
    select
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    from documents
    where 1 - (documents.embedding <=> query_embedding) > match_threshold
    order by documents.embedding <=> query_embedding
    limit match_count;
$$;
