-- 汽车法规库监控台 · 二期数据库(已通过 MCP 应用到项目 nxiyifglhycvbrccbdhg)
-- 日期/编号等字段保持 text:一期前端以字符串比较日期(localeCompare),保持行为一致

create table public.regulations (
  id bigint generated always as identity primary key,
  country text not null,
  reg_key text not null,            -- norm(法规编号 || 中文名):去空白+大写,与一期主键规则一致
  reg_id text not null default '',
  cn_name text not null default '',
  orig_name text not null default '',
  en_name text not null default '',
  lang text not null default '',
  dim_text text not null default '',  -- 对标维度(8列)
  domain text not null default '',    -- 法规领域(28列)
  ref_cn text not null default '',
  ref_eu text not null default '',
  ref_us text not null default '',
  pub_date text not null default '',
  eff_date text not null default '',
  status text not null default '',    -- 正式法规 or 草案
  source text not null default '',
  link text not null default '',
  parents_raw jsonb not null default '[]'::jsonb, -- 上位法规原始文本数组
  dims jsonb not null default '[]'::jsonb,        -- 0-9 维度下标数组(导入时按一期三层逻辑归集)
  refs jsonb not null default '[]'::jsonb,        -- 国际标准引用 ["UN R100", ...]
  amend text,                                     -- 修订系列标注
  rec_date text not null default '',              -- 发布||生效日期(排序用)
  raw jsonb,                                      -- 原始行全部列(28列等),无损保留
  source_file text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (country, reg_key)
);
create index regulations_country_idx on public.regulations (country);

create table public.text_files (
  id bigint generated always as identity primary key,
  filename text not null,
  base text not null,               -- 去扩展名
  path text not null unique,        -- webkitRelativePath || 文件名
  country text,                     -- 登记时按路径自动识别/手动指定
  matched_reg_id bigint references public.regulations(id) on delete set null,
  match_score int not null default 0,
  uploaded_at timestamptz not null default now()
);

create table public.snapshots (
  id bigint generated always as identity primary key,
  snap_date date not null default current_date,
  reg_keys jsonb not null,                        -- 主键数组
  names jsonb not null default '{}'::jsonb,       -- 主键→简名映射(与一期基准 JSON 同构)
  auto boolean not null default true,             -- true=导入后自动生成
  note text not null default '',
  created_at timestamptz not null default now()
);

create table public.import_logs (
  id bigint generated always as identity primary key,
  filename text not null,
  row_count int not null default 0,
  added_count int not null default 0,
  operator text not null default '',
  created_at timestamptz not null default now()
);

create or replace function public.set_updated_at() returns trigger
language plpgsql security definer set search_path = '' as $$
begin new.updated_at := now(); return new; end $$;
create trigger regulations_updated_at before update on public.regulations
  for each row execute function public.set_updated_at();

-- 团队内部工具,业主确认暂不做登录:对 anon 开放读写(RLS 形式上开启,策略放行)
alter table public.regulations enable row level security;
alter table public.text_files enable row level security;
alter table public.snapshots enable row level security;
alter table public.import_logs enable row level security;

create policy "open read"   on public.regulations for select using (true);
create policy "open insert" on public.regulations for insert with check (true);
create policy "open update" on public.regulations for update using (true) with check (true);
create policy "open delete" on public.regulations for delete using (true);

create policy "open read"   on public.text_files for select using (true);
create policy "open insert" on public.text_files for insert with check (true);
create policy "open update" on public.text_files for update using (true) with check (true);
create policy "open delete" on public.text_files for delete using (true);

create policy "open read"   on public.snapshots for select using (true);
create policy "open insert" on public.snapshots for insert with check (true);
create policy "open delete" on public.snapshots for delete using (true);

create policy "open read"   on public.import_logs for select using (true);
create policy "open insert" on public.import_logs for insert with check (true);
