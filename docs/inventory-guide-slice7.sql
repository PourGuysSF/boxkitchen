-- Inventory Guide, Slice 7: close the month.
-- Plan: docs/inventory-guide.md. Run ONCE, by Stephen, in the Supabase SQL Editor
-- (the source dropdown beside Save must read Database), BEFORE the Slice 7 page
-- goes live: that page reads inventory_counts.practice, and fails without it.
--
-- What it does:
--   1. inventory_counts.practice - a practice count (October 2026). It is closed
--      like any other month, but the true food cost % (Slice 8) never starts from
--      it.
--   2. inventory_counts.changed_by - who is starting, closing or reopening a count,
--      sent WITH that write. It is never kept: the trigger copies it into the log
--      and clears it, so a later write can never reuse an old name.
--   3. A trigger that writes inventory_count_log for every start, close and reopen
--      in the same statement as the change itself - both or neither - refuses one
--      without a name, and stamps closed_at / closed_by from the database's own
--      clock. Until now the page wrote the log as a second request, which a dropped
--      signal could lose. The Slice 7 page no longer writes the log at all.
--   4. The log's link to its count is checked at the end of the transaction rather
--      than the end of each statement, so the trigger can log a start for the very
--      count row being inserted.
--   5. A self-test, inside this transaction: a pretend count under location
--      '__selftest__' is started, closed, refused a reopen with no name, reopened,
--      and marked practice - then undone. None of its rows survive; it only uses up
--      a few id numbers.
--
-- Between this running and the Slice 7 page going live, the Slice 6 page cannot
-- START a count (it sends no name, and is refused). October's count is already
-- open, so nothing needs starting.
--
-- One transaction; any failed check undoes everything.
--
-- To undo, if ever needed (Stephen runs it):
--   drop trigger inventory_counts_log on public.inventory_counts;
--   drop function public.inventory_counts_log();
--   alter table public.inventory_counts drop column practice, drop column changed_by;
--   alter table public.inventory_count_log
--     alter constraint inventory_count_log_count_id_fkey not deferrable;

begin;

alter table public.inventory_counts
  add column practice   boolean not null default false,
  add column changed_by text;

comment on column public.inventory_counts.practice is
  $$A practice count: closed like any other month, but never an opening value for the true food cost %.$$;
comment on column public.inventory_counts.changed_by is
  $$Who is starting, closing or reopening the count, sent with that write. Always empty at rest: the trigger inventory_counts_log copies it into inventory_count_log and clears it.$$;

alter table public.inventory_count_log
  alter constraint inventory_count_log_count_id_fkey deferrable initially deferred;

create function public.inventory_counts_log() returns trigger
language plpgsql
set search_path = public
as $$
declare
  act text;
  who text := nullif(btrim(new.changed_by), '');
begin
  if tg_op = 'INSERT' then
    act := 'start';
  elsif new.status is distinct from old.status then
    act := case new.status when 'closed' then 'close' else 'reopen' end;
  end if;
  new.changed_by := null;
  if act is null then
    return new;   -- not a start, close or reopen (a month corrected, say): nothing to log
  end if;
  if who is null then
    raise exception 'A count cannot be % without a name.',
      case act when 'start' then 'started' when 'close' then 'closed' else 'reopened' end
      using errcode = 'check_violation';
  end if;
  if act = 'close' then
    new.closed_at := now();
    new.closed_by := who;
  elsif act = 'reopen' then
    new.closed_at := null;
    new.closed_by := null;
  end if;
  insert into public.inventory_count_log (location, count_id, action, by_name)
  values (new.location, new.id, act, who);
  return new;
end
$$;

create trigger inventory_counts_log
  before insert or update on public.inventory_counts
  for each row execute function public.inventory_counts_log();

-- The self-test. Its last line raises on purpose, which undoes every row it wrote;
-- any other failure is not caught, and undoes the whole file.
do $selftest$
declare
  c bigint;
  n int;
  r public.inventory_counts%rowtype;
begin
  begin
    insert into public.inventory_counts (location, period, changed_by)
      values ($$__selftest__$$, date '2000-01-01', $$  Selftest $$) returning id into c;
    select * into r from public.inventory_counts where id = c;
    if r.changed_by is not null then raise exception 'self-test: the name was kept on the count'; end if;
    select count(*) into n from public.inventory_count_log where count_id = c and action = 'start' and by_name = 'Selftest';
    if n <> 1 then raise exception 'self-test: the start was not logged with its name (% lines)', n; end if;

    begin
      insert into public.inventory_counts (location, period) values ($$__selftest__$$, date '2000-02-01');
      raise exception 'self-test: a count was started without a name';
    exception when check_violation then null;
    end;

    update public.inventory_counts set status = 'closed', changed_by = 'Selftest' where id = c;
    select * into r from public.inventory_counts where id = c;
    if r.status <> 'closed' or r.closed_at is null or r.closed_by is distinct from 'Selftest' or r.changed_by is not null then
      raise exception 'self-test: the close did not stamp who and when';
    end if;
    select count(*) into n from public.inventory_count_log where count_id = c and action = 'close' and by_name = 'Selftest';
    if n <> 1 then raise exception 'self-test: the close was not logged (% lines)', n; end if;

    -- a name sent with the close must not carry over to the reopen
    begin
      update public.inventory_counts set status = 'open' where id = c;
      raise exception 'self-test: a count was reopened without a name';
    exception when check_violation then null;
    end;

    update public.inventory_counts set status = 'open', changed_by = 'Selftest Two' where id = c;
    select * into r from public.inventory_counts where id = c;
    if r.status <> 'open' or r.closed_at is not null or r.closed_by is not null then
      raise exception 'self-test: the reopen did not clear the close';
    end if;
    select count(*) into n from public.inventory_count_log where count_id = c and action = 'reopen' and by_name = 'Selftest Two';
    if n <> 1 then raise exception 'self-test: the reopen was not logged (% lines)', n; end if;

    -- a change that is not a start, close or reopen writes no log line
    update public.inventory_counts set practice = true, period = date '2000-03-01' where id = c;
    select count(*) into n from public.inventory_count_log where count_id = c;
    if n <> 3 then raise exception 'self-test: % log lines, expected 3', n; end if;

    raise exception using errcode = 'IG7OK', message = 'self-test passed';
  exception when sqlstate 'IG7OK' then
    raise notice 'Slice 7 self-test passed; its pretend count was undone.';
  end;
end
$selftest$;

-- The checks. Any mismatch undoes everything above.
do $check$
begin
  if (select count(*) from information_schema.columns
      where table_schema = 'public' and table_name = 'inventory_counts'
        and column_name in ('practice', 'changed_by')) <> 2 then
    raise exception 'check: the two new columns are not both there';
  end if;
  if not exists (select 1 from pg_trigger
                 where tgname = 'inventory_counts_log'
                   and tgrelid = 'public.inventory_counts'::regclass and not tgisinternal) then
    raise exception 'check: the trigger is missing';
  end if;
  if not exists (select 1 from pg_constraint
                 where conname = 'inventory_count_log_count_id_fkey' and condeferred) then
    raise exception 'check: the log link is still checked statement by statement';
  end if;
  if exists (select 1 from public.inventory_counts where location = '__selftest__')
     or exists (select 1 from public.inventory_count_log where location = '__selftest__') then
    raise exception 'check: the self-test left rows behind';
  end if;
  if exists (select 1 from public.inventory_counts where practice or changed_by is not null) then
    raise exception 'check: an existing count came out marked practice, or with a name kept';
  end if;
end
$check$;

commit;

notify pgrst, 'reload schema';

-- Expected: counts 1 · practice counts 0 · log lines 1 · trigger inventory_counts_log
-- · log link checked at end of transaction. (If counts or log lines differ, they are
-- simply what the table held before this ran; the checks above have already passed.)
select 'counts' as what, count(*)::text as value from public.inventory_counts
union all select 'practice counts', count(*)::text from public.inventory_counts where practice
union all select 'log lines', count(*)::text from public.inventory_count_log
union all select 'trigger', string_agg(tgname, ', ')
  from pg_trigger where tgrelid = 'public.inventory_counts'::regclass and not tgisinternal
union all select 'log link checked at',
  case when condeferred then 'end of transaction' else 'end of statement' end
  from pg_constraint where conname = 'inventory_count_log_count_id_fkey';
