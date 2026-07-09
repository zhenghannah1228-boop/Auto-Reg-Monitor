-- 功能20 影响驾驶舱:团队在线编辑的覆盖层(盖在静态 data/cyber_hub.json 的 cockpit 种子之上)
-- 单行(id='team')存整份 cockpit JSON;删除该行即回退发布版。RLS 暂全放行(与其余二期表一致)。

create table if not exists public.cockpit_overrides (
  id text primary key default 'team',
  data jsonb not null,
  updated_by text,
  updated_at timestamptz not null default now()
);

alter table public.cockpit_overrides enable row level security;

drop policy if exists cockpit_overrides_all on public.cockpit_overrides;
create policy cockpit_overrides_all on public.cockpit_overrides
  for all using (true) with check (true);
