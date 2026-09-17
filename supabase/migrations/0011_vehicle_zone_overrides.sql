-- 功能:车辆合规孪生(3D)团队在线编辑覆盖层,盖在静态 data/vehicle_zones.json 种子之上。
-- 按 zone_id 存整条 zone 定义 JSON(label_cn/label_en/gltf_nodes/dims/domain_keywords/desc);
-- 删除该行即回退发布版。RLS 暂全放行(与其余二期表一致)。
create table if not exists public.vehicle_zone_overrides (
  zone_id text primary key,
  data jsonb not null,
  updated_by text,
  updated_at timestamptz not null default now()
);

alter table public.vehicle_zone_overrides enable row level security;

drop policy if exists vehicle_zone_overrides_all on public.vehicle_zone_overrides;
create policy vehicle_zone_overrides_all on public.vehicle_zone_overrides
  for all using (true) with check (true);
