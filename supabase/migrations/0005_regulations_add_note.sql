-- 单条法规的团队共享备注(与导入数据解耦:重复导入不会覆盖,因导入 payload 不含此列)
alter table public.regulations add column note text not null default '';
