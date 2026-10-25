create table workspaces (
    id uuid primary key,
    -- SHA-256 hex digest of the session token; the token itself is never stored.
    token_hash text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null,
    expires_at timestamptz not null,
    check (expires_at > created_at)
);

create index workspaces_expires_at_idx on workspaces (expires_at);
