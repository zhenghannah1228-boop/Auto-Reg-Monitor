-- 功能20 汽车网络安全合规中心:团队共享的自查/成熟度评估状态
-- 每个清单条目(item_key,见 data/cyber_hub.json domains[].items[].key)一行,全团队共享。
-- status: 0=未开始 / 1=部分达成 / 2=已达成。RLS 暂全放行(与其余二期表一致)。

create table if not exists public.cyber_assessments (
  id bigint generated always as identity primary key,
  item_key text unique not null,
  status int not null default 0,
  note text,
  updated_by text,
  updated_at timestamptz not null default now()
);

alter table public.cyber_assessments enable row level security;

drop policy if exists cyber_assessments_all on public.cyber_assessments;
create policy cyber_assessments_all on public.cyber_assessments
  for all using (true) with check (true);
