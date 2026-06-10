-- 快照列表页只取元数据,不拉 reg_keys 大字段;条数单独存一列
alter table public.snapshots add column key_count int not null default 0;
