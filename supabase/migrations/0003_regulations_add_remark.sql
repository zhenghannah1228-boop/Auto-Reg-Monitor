-- 备注列参与草案关键词识别(草案/draft/proposal 常写在备注里)
alter table public.regulations add column remark text not null default '';
update public.regulations set remark = coalesce(raw->>'备注','') where raw ? '备注';
