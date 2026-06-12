-- 业主 2026-06 三项扩展的库侧支撑(已通过 MCP 应用到项目 nxiyifglhycvbrccbdhg):
-- 1) 备忘录置顶 + 链接(日期本就可空,前端放开必填即可)
alter table public.memos add column pinned boolean not null default false;
alter table public.memos add column url text not null default '';

-- 2) 法规备注粘贴图片:公开 storage 桶,只存压缩后的 JPEG,备注文本里以 [img]URL 标记引用
insert into storage.buckets (id, name, public) values ('note-images','note-images', true)
on conflict (id) do nothing;
create policy "note images open read" on storage.objects
  for select using (bucket_id = 'note-images');
create policy "note images open insert" on storage.objects
  for insert with check (bucket_id = 'note-images');

-- 3) 09 认证金字塔可编辑:覆盖层按国家存整条 cert_systems 条目,
--    前端加载时盖在静态 data/cert_pyramid.json 之上;删除该行即恢复默认
create table public.cert_overrides (
  country text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.cert_overrides enable row level security;
create policy "cert_overrides open select" on public.cert_overrides for select using (true);
create policy "cert_overrides open insert" on public.cert_overrides for insert with check (true);
create policy "cert_overrides open update" on public.cert_overrides for update using (true) with check (true);
create policy "cert_overrides open delete" on public.cert_overrides for delete using (true);
