-- 功能20 自查支持多档案(分车型/项目):主键从 item_key 改为 (profile,item_key)
-- 既有行默认归入「团队基线」档案。前端 on_conflict 相应改为 profile,item_key。

alter table public.cyber_assessments
  add column if not exists profile text not null default '团队基线';

alter table public.cyber_assessments
  drop constraint if exists cyber_assessments_item_key_key;

create unique index if not exists cyber_assessments_profile_item
  on public.cyber_assessments(profile, item_key);
