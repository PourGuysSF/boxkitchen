-- Menu Builder, Slice 0b: the draft-lines table and its security rules.
-- Plan: docs/menu-builder.md. Run ONCE, by Stephen, in the Supabase SQL editor.
--
-- One row per line of a draft dish. Column types copy the live recipe_lines
-- (docs/recipe-costing-slice0.sql in the costing worktree). Different on purpose:
-- a uuid id named by the page (as menu_drafts), no line_text / occurrence, and NO
-- foreign key on sub_recipe_id - recipes can be hard-deleted from the Recipe
-- Database, and a draft must never block that.
--
-- Security mirrors menu_drafts as built (docs/menu-builder-slice0a.sql): RLS on;
-- revoke all, then anon + authenticated may SELECT, INSERT, UPDATE; no delete
-- policy and no delete grant. A line is removed by setting active = false.
--
-- One transaction: if any step fails, or the check at the end does not match,
-- NOTHING is kept. The last statement, after the commit, reads both tables back.

begin;

create table public.menu_draft_lines (
  id                  uuid        primary key default gen_random_uuid(),
  location            text        not null default 'Tempest',
  draft_id            uuid        not null references public.menu_drafts (id) on delete cascade,
  position            integer     not null check (position >= 1),
  qty                 numeric,
  unit                text,
  ingredient_cost_id  bigint      references public.ingredient_costs (id),
  sub_recipe_id       bigint,
  own_name            text,
  skip                boolean     not null default false,
  guess_pack_qty      numeric,
  guess_pack_unit     text,
  guess_pack_price    numeric,
  estimate_cost       numeric,
  linked_name         text,
  component           text,
  note                text,
  active              boolean     not null default true,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  -- 1. What the line is: not costed on purpose (a name, nothing to cost it by),
  --    or an amount, a unit and exactly one of price row / house recipe / own name.
  constraint menu_draft_lines_kind check (coalesce(
    (skip
      and own_name is not null and btrim(own_name) <> ''
      and ingredient_cost_id is null and sub_recipe_id is null
      and guess_pack_qty is null and guess_pack_unit is null and guess_pack_price is null
      and estimate_cost is null
      and (qty is null or qty > 0))
    or
    (not skip
      and qty is not null and qty > 0
      and unit is not null and btrim(unit) <> ''
      and num_nonnulls(ingredient_cost_id, sub_recipe_id, own_name) = 1
      and (own_name is null or btrim(own_name) <> '')),
    false)),

  -- 2. The guess: all three empty, or all three set - and only on a costed own-name line.
  constraint menu_draft_lines_guess check (coalesce(
    num_nonnulls(guess_pack_qty, guess_pack_unit, guess_pack_price) = 0
    or
    (num_nonnulls(guess_pack_qty, guess_pack_unit, guess_pack_price) = 3
      and guess_pack_qty > 0 and btrim(guess_pack_unit) <> '' and guess_pack_price > 0
      and not skip and own_name is not null),
    false)),

  -- 3. The estimate: empty, or more than 0 and only on a house-recipe line.
  constraint menu_draft_lines_estimate check (coalesce(
    estimate_cost is null or (estimate_cost > 0 and sub_recipe_id is not null),
    false)),

  -- 4. The rename guard: a linked line keeps the name it had when it was linked.
  constraint menu_draft_lines_linked_name check (coalesce(
    (ingredient_cost_id is null and sub_recipe_id is null)
    or (linked_name is not null and btrim(linked_name) <> ''),
    false))
);
create index menu_draft_lines_draft_position on public.menu_draft_lines (draft_id, position);

comment on table public.menu_draft_lines is
  $$Menu Builder draft lines (B7). Never deleted: active = false hides a line.$$;
comment on column public.menu_draft_lines.position is
  $$Order added. Not unique: the page writes max + 1; ties sort by created_at.$$;
comment on column public.menu_draft_lines.sub_recipe_id is
  $$A Recipes id, with NO foreign key on purpose: recipes can be hard-deleted, and a draft must never block that. A missing recipe shows "recipe deleted - relink".$$;
comment on column public.menu_draft_lines.estimate_cost is
  $$The typed line total for a house recipe, until Recipe Costing can cost it.$$;
comment on column public.menu_draft_lines.linked_name is
  $$The name the price row or recipe had when linked (order-guide ids are reused on rename).$$;

alter table public.menu_draft_lines enable row level security;

-- Supabase's default privileges hand new tables ALL rights; take delete back explicitly.
revoke all on public.menu_draft_lines from anon, authenticated;
grant select, insert, update on public.menu_draft_lines to anon, authenticated;

create policy menu_draft_lines_select on public.menu_draft_lines for select to anon, authenticated using (true);
create policy menu_draft_lines_insert on public.menu_draft_lines for insert to anon, authenticated with check (true);
create policy menu_draft_lines_update on public.menu_draft_lines for update to anon, authenticated using (true) with check (true);

-- The check: any mismatch raises an error, and the whole transaction is undone.
do $check$
declare n_pol int; n_del int; rls boolean;
begin
  select count(*) into n_pol from pg_policies
   where schemaname = 'public' and tablename = 'menu_draft_lines';
  select count(*) into n_del from information_schema.role_table_grants
   where table_schema = 'public' and table_name = 'menu_draft_lines'
     and grantee in ('anon', 'authenticated') and privilege_type = 'DELETE';
  select relrowsecurity into rls from pg_class where oid = 'public.menu_draft_lines'::regclass;
  if n_pol <> 3 then raise exception 'expected 3 policies on menu_draft_lines, got %', n_pol; end if;
  if n_del <> 0 then raise exception 'anon/authenticated still hold delete on menu_draft_lines'; end if;
  if not rls then raise exception 'row level security is not on for menu_draft_lines'; end if;
end
$check$;

commit;

-- What you should see: menu_draft_lines 0, and menu_drafts with your dishes (1 today).
select 'menu_draft_lines' as table_name, count(*) as row_count from public.menu_draft_lines
union all select 'menu_drafts', count(*) from public.menu_drafts;
