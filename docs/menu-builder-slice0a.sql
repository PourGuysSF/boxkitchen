-- Menu Builder, Slice 0a: the draft-dishes table and its security rules.
-- Plan: docs/menu-builder.md. Run ONCE, by Stephen, in the Supabase SQL editor.
--
-- Mirrors the site's pattern (docs/inventory-guide-slice0.sql):
--   RLS on; anon + authenticated may SELECT, INSERT, UPDATE; NO delete policy and no
--   delete grant, so a dish is never deleted (it is hidden with status = 'dropped').
--   The page names each new row itself (a uuid made in the browser) and saves with an
--   upsert on id, so a retry after a lost answer updates the same row.
--
-- One transaction: if any step fails, NOTHING is kept. The last statement, after the
-- commit, reads the table back.

begin;

create table public.menu_drafts (
  id            uuid        primary key default gen_random_uuid(),
  location      text        not null default 'Tempest',
  name          text        not null check (btrim(name) <> ''),
  status        text        not null default 'idea'
                            check (status in ('idea', 'testing', 'ready', 'dropped')),
  makes_plates  numeric     not null default 1 check (makes_plates > 0),
  menu_price    numeric     check (menu_price is null or menu_price > 0),
  target_low    numeric     not null default 26,
  target_high   numeric     not null default 28,
  notes         text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint menu_drafts_target_range
    check (target_low > 0 and target_low <= target_high and target_high < 100)
);
comment on table public.menu_drafts is
  $$Menu Builder draft dishes (B7). Never deleted: status 'dropped' hides a dish.$$;
comment on column public.menu_drafts.makes_plates is
  $$How many plates the dish's lines make: 1 = the lines are one plate.$$;

alter table public.menu_drafts enable row level security;

-- Supabase's default privileges hand new tables ALL rights; take delete back explicitly.
revoke all on public.menu_drafts from anon, authenticated;
grant select, insert, update on public.menu_drafts to anon, authenticated;

create policy menu_drafts_select on public.menu_drafts for select to anon, authenticated using (true);
create policy menu_drafts_insert on public.menu_drafts for insert to anon, authenticated with check (true);
create policy menu_drafts_update on public.menu_drafts for update to anon, authenticated using (true) with check (true);

commit;

-- What you should see: one row, menu_drafts, 0.
select 'menu_drafts' as table_name, count(*) as row_count from public.menu_drafts;
