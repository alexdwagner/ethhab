-- Job logs for admin refresh pipeline
create table if not exists public.job_logs (
  id bigserial primary key,
  job_name text not null,
  status text not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  params jsonb,
  summary jsonb
);

create index if not exists idx_job_logs_started on public.job_logs (started_at desc);

