-- 团队共享备忘录:跟踪法规动态、待办与提醒
create table public.memos (
  id bigint generated always as identity primary key,
  content text not null,
  country text not null default '',   -- 国家/地区标签(可空)
  tag_date text not null default '',  -- 时间标签(到期/关注日,YYYY-MM-DD)
  author text not null default '',
  done boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.memos enable row level security;
create policy "open read"   on public.memos for select using (true);
create policy "open insert" on public.memos for insert with check (true);
create policy "open update" on public.memos for update using (true) with check (true);
create policy "open delete" on public.memos for delete using (true);
