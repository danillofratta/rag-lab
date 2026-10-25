create table schema_migrations (
    version text primary key,
    checksum text not null check (checksum ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz not null default now()
);
