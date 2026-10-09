# Inventory Guide — the monthly count

Status: **plan v1, approved by Stephen 2026-10-06** with one change: Tempest's real storage
places, in walking order (see "Decisions"). **Slice 0 is closed** — the tables are live and
seeded. **Slice 1 is live** — merged as `a82d60b` (PR #158), unlinked, and walked by Stephen
on 2026-10-07. **Slice 2 is live** — merged as `29eedf0` (PR #160) and hand-tested by Stephen
on an iPhone on 2026-10-07. **Slice 3 is live** — merged as `59fe0ca` (PR #162) and hand-tested
by Stephen on 2026-10-08 on the real October count, **which is open** for month-end. **Slice 4
is built** on branch `inventory-slice4`: see "Slice 4 as built". Every decision below was made by Stephen, in the interview that produced
this document or as each slice began. Worktree `~/Developer/boxkitchen-inventory`.

Target file: a new page, `tempest_inventory.html`, copied from `tempest_meat.html` as its
template. At the very end, and only then: the tile in `index.html`, `CLAUDE.md`, and
`BUILD_PLAN.md` (B3). This plan needs **no change to `assets/kitchen.css`** (see Constraints).

---

## What it is for

Once a month, count what is on the shelves, put a dollar value on it, and use that to work
out the **true food cost %**:

> (what you started the month with + what you bought − what is left) ÷ food sales

Flash Reports today divides purchases by sales. That number is right only if the shelves end
the month exactly as full as they started it. A month you stock up looks worse than it was,
and a month you run the coolers down looks better. The count fixes that.

It is BUILD_PLAN **B3**, and it is where B4 (Recipe Costing) pays off a second time: the same
prices that cost a recipe also value the shelves.

---

## Decisions — 2026-10-06

| question | decided |
|---|---|
| What is it for | The monthly count, to get a true food cost % each month. Not an ordering aid; the order guide keeps par. |
| Where prices live | **One price list**: Recipe Costing's `ingredient_costs`. Inventory **reads** it and never writes it or keeps a price of its own. |
| What is counted | **Order-guide food only.** Paper Goods, Cleaning, Equipment and Bar are left off; a manager can add any guide item later. House-made prep is a later version. |
| How the sheet is ordered | **By where it is stored**, in walking order. **The places differ by location**, so each location keeps its own list. Tempest's, in order: **Vegetable cooler → Prep/protein cooler → Fry freezer → Stand-up freezer → Dairy coolers → Dry storage → Spice shelf → Vinegar shelf → Flour shelf → Line.** |
| A part-used case | **Full packs + loose.** Two boxes: "2" full, "7" loose lb. |
| Who counts | **Anyone.** Several people at once, each taking a place, on their own phones. **Dollar values, closing and set-up need the manager PIN.** |
| When a month is done | **A manager closes it and it freezes**: counts and prices as they were on the close day. A manager can reopen it; the reopen is recorded. |
| Where the true food cost % shows | **On the Inventory page.** It reads purchases and sales from Flash; Flash itself is not touched. |

---

## Ground truth — read-only, 2026-10-06

**The order guide** (`order_items`): **254** active items, 5 vendors — Birite 151, Cooks
Produce 78, Dairy 16, Schmitz Ranch 6, Asia Intl 3 — on **23** shelves (`order_categories`).
Columns: `id, name, vendor, location, unit, par_level, item_number, sort_order, category,
unit_id, active`. Order units: EA 103, CS 78, lb 39, BU 10, GAL 9, BAG 9, DOZ 2, BSKT 2, PK 1,
BOX 1.

- **206 are food. 48 are not**: Paper Goods 36, Cleaning 8, Equipment 3, Bar 1.
- **A shelf is not a place.** Birite "Cooler" holds frozen fries (`Potato FF 3/8`); Cooks
  "Peppers" holds fresh jalapeños *and* dried guajillo; "Misc" (Cooks 14, Dairy 5) mixes nori
  and lentils with butter and eggs. So places cannot be derived from shelves. They have to be
  proposed per item and checked by a person (Slice 0).

**The price list** (`ingredient_costs`): **1** active priced row. Columns: `id, location,
order_item_id, name, invoice_alias, pack_qty, pack_unit, pack_price, active, updated_at,
created_at`. The price of one loose unit is `pack_price ÷ pack_qty`, per `pack_unit` — the
costing page's own `unitCost()`. History (`ingredient_price_history`) carries `pack_price,
pack_qty, pack_unit, source, invoice_ref, effective_date`.

> **The first count will be valued almost entirely blank** unless costing fills up first.
> Counting needs no price; valuing does. This plan is built so the two never block each other.

**Flash** (`flash_days`): `report_date, purchases, food_sales`, with `purchases` an object keyed
by Flash vendor id. July, August and September are complete; October is in progress.
`flash_vendors` has **9** vendors, and five have no order-guide vendor of the same name —
PANORAMA, OSPREY, PEACH FARM, CHALLENGE, ARAMARK. (CHALLENGE may be the guide's "Dairy".) Stock
from those vendors is not on the order guide, so it is **not on the count** — see Question 3.

**The count sheets we already have**: `meat_items` (16) and `portion_items` (58) are their own
lists, counted daily against par. Neither is order-guide stock, and neither is in scope.

**Found while planning — not this build's to fix:** `.count-input`, the box on Meat Count and
Portion Count, is `font-size:0.95rem` = **15.2px**. iPhones zoom on every one of them. It is not
in `FS_REGISTER` because those boxes are built at runtime and `check_styling.py` only measures
inputs in the markup (its own comment says so). It is #135 again, live and unregistered.
**Recommend filing it as an issue.** For this build it means: **do not reuse `.count-input`.**

---

## The spine

> **A count is a number someone will put on a P&L. Every slice makes a wrong number harder to
> enter, easier to see, and impossible to lose.**

Three rules, and everything below obeys them:

1. **Counting never needs a price, and valuing never guesses one.** An item with no price
   shows as *not valued*, never as $0. A total always says how many items it leaves out.
2. **Nothing typed is lost.** Not to a cooler with no signal, not to two phones, not to a
   closed tab.
3. **Blank is not zero.** An empty box means *not counted yet*. Zero is something a person
   typed. The difference is the whole of "did we forget the freezer."

---

## The design

### What the counter sees

```
┌───────────────────────────────────────────────┐
│ ← Home      Tempest INVENTORY       Manager ○ │
│ October 2026 count · open                     │
│ Counted by: [ Select…  ▾]                     │
├───────────────────────────────────────────────┤
│ VEGETABLE COOLER                  31 of 64    │
│ Baby spinach                Cooks Produce     │
│   Full [  2 ] × 4 lb      Loose [  1 ] lb  ✓  │
│ Ginger                      Cooks Produce     │
│   Full [    ] × 30 lb     Loose [    ] lb     │  ← blank = not counted
│ Cilantro                    Cooks Produce     │
│   Count [  0 ] BU                          ✓  │  ← no price yet: one box
├───────────────────────────────────────────────┤
│ PREP COOLER                        0 of 28    │
└───────────────────────────────────────────────┘
  (pack sizes and counts in this sketch are illustrations, not data)
```

- Staff never see a dollar sign. The pack size ("× 40 lb") is not a price, so it shows.
- The ✓ means *this phone has heard back from the database*. A row without it was typed and
  is not yet saved (Slice 3).
- Each place header says how many of its items are counted. A count is done when every place
  says *N of N*.

### Which boxes an item gets

The boxes depend on what the price list knows about the item **when it is counted**, and the
row remembers what they meant (see `pack_qty_snap` below):

| what the price list has | boxes | example |
|---|---|---|
| a pack of more than 1 | **Full** × pack, **Loose** in pack units | Full 2 × 40 lb, Loose 7 lb |
| a pack of exactly 1 | **one box**, decimals allowed | 1.5 jugs fish sauce |
| nothing yet | **one box in the order-guide unit**, decimals allowed | 3 CS, 4.5 lb |

The third row is the honest fallback: without a pack size there is no "loose" unit to count
in. It goes away as costing fills.

### How a line is valued

`value = full × pack_price + loose × (pack_price ÷ pack_qty)` — using the pack the row was
**counted against**. A line is *not valued*, with the reason shown, when:

- **no price** — the item has no priced row in `ingredient_costs`;
- **pack changed** — the price list's `pack_qty`/`pack_unit` is no longer what the row was
  counted against (someone re-entered chicken as "1 CS" after it was counted as "40 lb"). The
  row is never silently re-read under a new meaning;
- **counted in order units** — it was counted before it had a pack, and the order unit is not
  the price list's `pack_unit`. (When they match — 39 items are ordered by the lb — it values.)

### Tables — SQL Stephen runs; nothing is created from a session

Five new tables, all `location`-scoped like everything else. **`order_items` is not
altered**: the live order guide is untouched, for the same reason A5a chose a separate
registry.

| table | one row per | key columns |
|---|---|---|
| `inventory_places` | storage place, **per location** | `label, sort_order, active` — Tempest seeded with its ten, in walking order, at 10, 20 … 100 |
| `inventory_items` | guide item **in a place** | `order_item_id, place_id, sort_order, active`; unique `(place_id, order_item_id)` where active |
| `inventory_counts` | month | `period` (first of the month), `status` open/closed, `closed_at, closed_by`; unique `(location, period)`; **at most one open** per location |
| `inventory_count_lines` | item-in-place, per month | `count_id, inventory_item_id, full_qty, loose_qty, pack_qty_snap, pack_unit_snap, counted_by, updated_at`; frozen at close: `unit_cost_frozen, value_frozen, value_note`; unique `(count_id, inventory_item_id)` |
| `inventory_count_log` | start, close or reopen | `count_id, action, by_name, created_at` — append-only |

As written in `docs/inventory-guide-slice0.sql`, two things differ from the first draft of this
table: a line does **not** repeat `order_item_id` (it reaches the item through
`inventory_items`, so the two can never disagree), and who *started* a count lives in the log
rather than on the count. No table has a delete policy, so nothing is ever deleted — the
site's existing pattern.

Two choices in there worth saying out loud:

- **An item can be in more than one place** — a backup case in dry storage and an open one on
  the line are two stocks, counted separately and added up. The seed gives every item one
  place; a second is a manager action (Slice 2). Cheap to allow now, painful to add later.
- **The freeze is enforced by the database, not just the page.** The RLS policy on
  `inventory_count_lines` allows insert/update only while its count is `open`. Since the anon
  key is public, a page-only freeze would be a polite request.

Saving is an **upsert** on `(count_id, inventory_item_id)` — PostgREST `on_conflict` with
`Prefer: resolution=merge-duplicates`. A retry after a lost response *cannot* create a second
row; that is what the unique key is for. This replaces Meat Count's POST-then-409-then-adopt
dance, and it means Slice 4 of costing's lesson (a dropped response that succeeded) is solved
by the table, not by care.

---

## Slices

Ten counting Slice 0, each small, ordered so nothing that writes ships before the thing that
makes it safe. **The
first real count can happen after Slice 4.** Slices 5–7 can follow before the month is closed.

### Slice 0 — Ground truth and tables *(no app code)* · **blocks everything**

- **Places, proposed per item.** I write `~/Downloads/inventory_places_proposal.xlsx`: all 206
  food items, vendor, shelf, and a proposed place, picked from a dropdown of Tempest's ten
  places (plus *Not counted*) so a typo cannot reach the seed. An optional *Also stored in*
  column answers Question 2 in the same pass. Stephen corrects it, and the corrected file
  becomes the seed. Guesses I am unsure of are marked so they get looked at, not skimmed.

  > **DONE 2026-10-06.** Stephen corrected it (in Numbers, which dropped the dropdowns, so some
  > answers came back as notes or typed names). Every disagreement between a note and the
  > *Stored in* column was read back to Stephen and confirmed. Stephen renamed *Prep cooler* to
  > **Prep/protein cooler**. The approved list is `~/Downloads/inventory_places_approved.csv`
  > and is the seed:
  >
  > | place | items | also kept here |
  > |---|---|---|
  > | Vegetable cooler | 53 | |
  > | Prep/protein cooler | 11 | 1 |
  > | Fry freezer | 1 | |
  > | Stand-up freezer | 8 | 1 |
  > | Dairy coolers | 27 | 1 |
  > | Dry storage | 46 | 15 |
  > | Spice shelf | 26 | |
  > | Vinegar shelf | 15 | |
  > | Flour shelf | 11 | |
  > | Line | 0 | |
  > | **Not counted** | 8 | |
  >
  > **198 items counted, 18 of them in a second place** (216 `inventory_items` rows). Not counted:
  > staff coffee; root beer, Capri Sun, bottled water and the three juices (they wait for a
  > bar inventory); Birite slab bacon (only bought from Asia Intl now). Order within each
  > place starts in order-guide order; a manager re-orders it on the page (Slice 2).
- **RLS pattern.** Before writing policies, Stephen runs one **read-only** query in the SQL
  editor (`select * from pg_policies where tablename = 'order_categories'`) so the new tables
  mirror what the site already uses. DDL is not visible through PostgREST.

  > **DONE 2026-10-06.** Stephen ran a read-only query over `pg_policies`,
  > `information_schema.columns`, `pg_constraint` and `pg_indexes` for `order_items`,
  > `order_categories`, `meat_counts` and `ingredient_costs`. The pattern: RLS on; separate
  > SELECT / INSERT / UPDATE policies with `using (true)` / `with check (true)`, roles `anon,
  > authenticated` on the newer tables; **no DELETE policy** except on `order_items`; `bigint`
  > identity ids; `location text not null default 'Tempest'`; foreign keys to parents.
- **The SQL**: five tables, the unique keys, RLS, the places seed and the items seed — in one
  file, dollar-quoted text, ending with a `select` that confirms the counts. Stephen runs it.

  > **WRITTEN 2026-10-06, not yet run.** `docs/inventory-guide-slice0.sql` (copy at
  > `~/Downloads/inventory_guide_setup.sql`), generated from the approved CSV. One
  > transaction; a `do` block raises — undoing everything — unless places = 10, item-in-place
  > rows = 216, distinct items = 198, and every seeded item is an active Tempest guide item.
  >
  > **Proved against a throwaway local Postgres** shaped like Supabase (`anon` and
  > `authenticated` roles, the real 254 `order_items` ids), sending the file as one message the
  > way the SQL editor does — 20 of 20 checks: the counts and walking order; spot items in the
  > right places; the 8 not-counted items absent; as `anon`: start a count and log it, a second
  > open count refused, a mid-month period refused, a line saved by upsert, a retry updating
  > the same line, a negative count refused, delete refused on lines and items, the log
  > uneditable; close then refuse both an upsert and an update on that month's lines; reopen,
  > logged, and editable again; and a deliberately failing check leaving **no tables at all**.
  > Not proved: Supabase's own grants and PostgREST's schema reload, which only the real run
  > shows — hence the read-only GETs below.
  >
  > **To undo it**, if ever needed (Stephen runs it; it deletes the five tables and their data):
  > `drop table public.inventory_count_log, public.inventory_count_lines,
  > public.inventory_counts, public.inventory_items, public.inventory_places;`

**Done when:** the tables exist (confirmed read-only: places 10 rows, items 216, counts/lines/log
0), RLS matches the existing pattern, and the open-only write rule on lines is in place.

> **CLOSED 2026-10-06.** Stephen ran `docs/inventory-guide-slice0.sql` in the SQL Editor
> (Database, production). Its closing select returned places 10, items 216, counts 0, lines 0,
> log 0. Verified independently, read-only, through PostgREST with the site's anon key: all
> five tables answer (`content-range` 10 / 216 / 0 / 0 / 0); places load in walking order;
> an embedded read of `inventory_items` with `order_items(...)` and `inventory_places(...)`
> returns 216 rows, 198 distinct items, none inactive — so PostgREST picked up the foreign
> keys. No row has been written by a session.
>
> One trap on the way, for next time: the first paste went into a query box whose data
> source was not **Database** (it offered to "adjust to ClickHouse SQL"). Nothing ran. The
> SQL Editor's source dropdown, beside Save, must read **Database**.
>
> Order within each place is order-guide order for now, so Birite items lead most places
> (the vegetable cooler opens on *Dill pickles*). Slice 2's re-ordering fixes that; Slice 1
> shows it as it is.

### Slice 1 — The sheet, read-only

The page exists, and writes nothing.

- `tempest_inventory.html`, copied from `tempest_meat.html`. Gate, header, Manager switch,
  `kitchen.css` link at the current `?v=` — the same as every other page.
- Places in walking order; items in their order within each place; each item's name, vendor
  and boxes exactly per "Which boxes an item gets." The boxes are disabled: there is no open
  count yet, and the page says so.
- Count boxes are a **new class at 16px**, written qualified per CLAUDE.md, with
  `inputmode="decimal"`.
- `scripts/check_inventory.py` started, modeled on `check_costing.py`: real page, stubbed
  `XMLHttpRequest`, headless Chrome.

**Done when:** Stephen can walk the kitchen with it and check the order and places; the
harness proves the page makes **no request but GET**, and that the runtime-built boxes compute
to ≥16px — the measurement `check_styling.py` cannot make.

> **SHIPPED.** Merged to `main` as `a82d60b` (PR #158, squashed) on 2026-10-06, live at
> `tempest_inventory.html` with no tile linking to it. **Walked by Stephen on 2026-10-07**:
> "I think it all looks good for now." Stephen asked for drag handles to move things quickly —
> already this plan's Slice 2 — "does not need to happen today". See "Slice 1 as built".

### Slice 2 — Set-up (manager)

- Add, rename, reorder and retire places.
- Move an item to another place; add it to a second one; reorder within a place (drag, as on
  Orders — SortableJS, manager-only, within a place).
- **"Not on the count"** — every active guide item that is in no place, with Add. A food item
  added to the order guide next spring must not silently miss every count after it. Non-food
  shelves are listed here too, collapsed, so a manager *can* add them.

**Done when:** every action writes only in manager mode; the harness asserts each payload;
a new guide item appears under "Not on the count" without any set-up.

> **Decided by Stephen as the slice began (2026-10-07):**
> - **Drag to reorder within a place; a Move button to change place.** Not drag between places:
>   on a phone, that means scrolling a 61-item list while holding a row, with nothing to
>   confirm where it landed.
> - **A "New items" list, not one list of everything uncounted.** Each new guide item stays
>   listed until a manager gives it a place or taps "Don't count". That needs to remember what
>   was left off on purpose — one new table, `inventory_left_off`, SQL Stephen ran (see
>   "Slice 2 as built") — so that the 56 deliberate omissions are never "new", and a genuinely
>   new item cannot get lost among them.
>
> **SHIPPED.** Merged to `main` as `29eedf0` (PR #160, squashed) on 2026-10-07. **Hand-tested by
> Stephen on an iPhone the same day** — scrolling by the names, dragging by the grip ("✓ Order
> saved", and the order held after reopening), Move, and switching manager mode off: "everything
> worked correctly and looks good." That closes the "drag with a finger" item left open in
> "Slice 2 as built".

### Slice 3 — Counting saves

The first slice that writes count data.

- **Start a count** (manager): pick *this month* or *last month*. One open count at a time.
- **Counted by** is required, as on Meat Count.
- Each row saves itself shortly after typing stops, by upsert, through an `api()` with a
  **timeout** (port it from `tempest_costing.html`). The row shows ✓ only on a confirmed
  response with a row in it.
- **Blank vs zero**: both boxes blank = not counted, no row. One filled, one blank = the blank
  is 0. Clearing both boxes on a saved row deletes nothing; it marks it not counted.
- Opening the page shows everyone's counts so far, with who counted each.

**Done when:** a save in flight cannot double-fire; a retry after a dropped response leaves
exactly one row; blank and zero are stored differently; the harness proves all three without
touching the database.

> **Decided by Stephen as the slice began (2026-10-07):** counting happens on the kitchen
> tablet and sometimes phones, and the name should be asked for "only if someone leaves the
> page". Built that way — kept in `sessionStorage` while the page is open, so it survives iOS
> reloading a background tab — plus, for the shared tablet, the name always on screen
> ("Counting as Maria") with a one-tap **Change**. No idle timeout: re-asking every time a phone
> locks inside a freezer would cost more than it saves. And the hand test is **the real October
> count**: Stephen starts it, counts two items for real, and clears them — no made-up data.
>
> **SHIPPED.** Merged to `main` as `59fe0ca` (PR #162, squashed) on 2026-10-08. **Hand-tested by
> Stephen the same day, on the real October count**: started it in manager mode, counted two
> items for real ("✓ Counted by …" appeared, and the heading moved), closed and reopened the
> page (both numbers were still there), and cleared them — "no confusion". Verified read-only
> afterwards: `inventory_counts` id 1, 2026-10-01, **open**; one `start` log row with a name; two
> lines, both cleared to blanks, each with the unit it was counted in; no duplicates. **The
> October count stays open for month-end.** See "Slice 3 as built".

### Slice 4 — Nothing typed is lost

Coolers and freezers are where the signal dies.

- A typed value that has not had its ✓ is kept **on the phone** until it has, and retried
  when the signal comes back.
- The header says so plainly: *"3 counts waiting for signal."*
- Leaving the page with anything waiting asks first.
- If a second phone saved the same row meanwhile, the newer one wins and the row says who.

**Done when:** with the network cut in the harness, typed counts survive a reload and go
through when it returns; nothing is ever shown ✓ that the database did not confirm.

> **BUILT 2026-10-08** on `inventory-slice4` — see "Slice 4 as built". Nothing in it needed a
> new decision from Stephen: every rule above was already in the approved plan.

**After this slice, a real count is safe to run.**

### Slice 5 — The paper backup

Paper is what the kitchen falls back to. Printing the page gives a count sheet you can run on
a clipboard: places in order, every item, empty boxes drawn as boxes (borders, not fills —
backgrounds do not print), pack sizes, "Counted by ____" and a date line. No prices on it,
ever.

**Done when:** a print preview of every place fits the page width, the boxes are visible
with background graphics off, and nothing manager-only prints.

### Slice 6 — Dollar values (manager)

- With the PIN on: each line's value, each place's subtotal, the month's total.
- **The total says what it leaves out**: *"$11,480 · 171 of 206 items valued · 35 not
  valued"*, with the 35 listed by reason (no price / pack changed / counted in order units)
  and a link to Recipe Costing for the missing prices.
- Values are live while the count is open: price an item in costing, refresh, and it values.

**Done when:** no unvalued line contributes $0 to a total; every unvalued line has its reason;
staff mode shows no dollar figure anywhere, including in the page source's rendered HTML.

### Slice 7 — Close the month (manager)

- **Before closing**, the page lists what is not counted, place by place, and asks. Closing
  with gaps is allowed; doing it without seeing them is not.
- Closing asks *who* is closing, then freezes each line's unit cost and value in **one** bulk
  write, then sets the count closed. If the second step fails, the count is still open and
  closing again recomputes.
- A closed month is read-only for everyone. **Reopen** needs the PIN and writes a log line.
- **Previous months**: a list of closed counts, each viewable as it was frozen.

**Done when:** a closed count cannot be written to (proved in the harness against the page,
and by the RLS rule in Slice 0 at the database); reopen is logged; a price changed in costing
after close does not move the closed month.

### Slice 8 — True food cost %

For any closed month whose previous month is also closed:

- Opening value (last month's close), purchases and food sales for the month (summed from
  `flash_days`), closing value, and the result — beside Flash's own purchases ÷ sales, so the
  difference is visible.
- **Marked incomplete** when either count has unvalued items, with how many. Never shown
  without that mark when it applies.

**The first month this can show is the second month counted.** If the first count is the
end of October, the first true food cost % is November's, available in early December.

**Done when:** the figure matches a hand calculation from the same rows; it is marked
incomplete whenever it should be; the page never writes to any `flash_*` table.

### Slice 9 — Ship it into the site *(shared files, last)*

- Bring the branch up to date with `main` first — the costing window keeps merging.
- `index.html`: the tile becomes a link. Subtitle from "Track on-hand par levels" to what it
  now does. It stays in Admin, unlocked, because staff count.
- `CLAUDE.md`: "ten pages" → eleven, wherever it is counted (the `?v=` rule, the styling
  section). `BUILD_PLAN.md`: B3 status.
- `check_styling.py` needs **no page-list change** — it takes `glob("*.html")`, so the new page
  is checked from Slice 1 on. Confirm it runs clean.
- `assets/kitchen.css`: add *inventory* to the `used by:` banner of every shared section the
  page uses — no rule changes, but the banners are how the next person tells a shared
  component from a private one. As of Slice 1: DATE / NAME / INTRO BARS (`.date-bar`,
  `.intro`), CATEGORY HEADER (`.cat-header`), COUNT ROWS (`.count-row` and family), and the
  section holding `.link-btn` (Try again). Slice 2 adds MANAGER-ONLY CONTROLS
  (`.row-mgr-actions`, `.mgr-retire-btn`, `.mgr-add-bar`), DRAG TO REORDER (`.drag-handle`)
  and the SEGMENTED TOGGLE (`.mode-toggle` in the place picker). HEADER, EMPTY / LOADING,
  MODAL, TOAST and MANAGER MODE already say every page or every tool page. Re-check the list
  against the page at the time; later slices add to it.

---

## Slice 1 as built

`tempest_inventory.html` (new), `scripts/check_inventory.py` (new),
`.github/workflows/inventory-guard.yml` (new, mirrors the costing guard). **No shared file
touched**: `kitchen.css`, `index.html`, `check_styling.py` and `CLAUDE.md` are as they were.
The page is reachable only by its address; no tile links to it yet.

### What it does

- Three GETs — places, item-in-place rows (with the guide item embedded), and the price list's
  **pack sizes only** (`select=order_item_id,pack_qty,pack_unit`: the page never asks for a
  price, so none can reach a staff screen by accident). The sheet is drawn only when **all
  three** have landed; one failure, error or 60s timeout shows "Could not load the count
  sheet" with **Try again**, and no partial sheet — without the pack sizes a 40 lb case would
  get one box in order units, a different count rather than a smaller one.
- Places in walking order, each with its item count; an empty place (Tempest's Line) says
  "Nothing is stored here yet." Items in their `sort_order`.
- Boxes per "Which boxes an item gets". A pack counts only with a quantity above zero **and** a
  unit. An item in two places is drawn in both, each saying "also in …". An item retired from
  the order guide says so. An item whose *place* is retired is shown under "Not in an active
  place" rather than dropped.
- Boxes are `.stock-input`: 16px, qualified against `.modal input[type="text"]`, 44px tall,
  `inputmode="decimal"`, **disabled** (dashed `--edge` on `--press`). One-box rows line their
  boxes up in one column (a floor under the unit text); two-box rows wrap under the name.
- `api()` is the costing page's, with its timeouts (this page uses only the 60s load one).

### Two departures from the plan

- **No Manager switch yet.** A switch that unlocks nothing is a control that lies. It arrives
  with Slice 2, which gives manager mode something to do. So this page holds no PIN at all.
- **The class prefix is `stock-`, not `inv-`.** `.inv-input` already exists in `kitchen.css` —
  it is the costing page's invoice-number field. Reusing the prefix would have put two
  unrelated components one typo apart.

### Proved

- `check_inventory.py`: **79 assertions, 7 scenarios, clean** (ok, slow, fail, packfail, hang,
  empty, orphan). Among them: no request but GET in every scenario; every read scoped to
  Tempest and active rows; the price list asked for pack size only; no `$` in the rendered
  text although the fixture hands back prices; all 14 boxes ≥16px, ≥44px, decimal, disabled,
  labelled; no row runs off the edge at 390px or 320px; a name containing markup shown as
  text; a second load while loading sends nothing; Try again recovers.
- **It fails when it should.** Fourteen deliberate breaks, each in a throwaway copy, each
  caught: a 15.2px box, asking for prices, drawing from partial data, an unescaped name, a
  pack of 1 given two boxes, a blank-unit pack treated as a pack, orphans dropped, boxes left
  enabled, a stray POST, no load timeout, retired items requested, "also in" on every row,
  boxes forced onto one line, and one-box rows knocked out of their column (13px apart). One further break was **correctly not caught**: dropping the
  `.modal …` qualifier changes nothing on this page, because no box sits in a modal — Slice 2
  must measure any box it puts in one.
- `check_styling.py`: clean, **11 pages**, 83 inputs measured, 75 on the register (unchanged).
- **Live data, read-only**, rendered in headless Chrome at 390px: 198 items, 10 places in
  walking order, 217 boxes, none under 16px, no row overflowing, no `$`, 36 rows with "also
  in", 4 of 198 items with a pack size at the time (Recipe Costing is being filled).

### Not proved

- On a real iPhone, with real fonts. The harness strips the webfonts (no network); the live
  render loaded them. Stephen's walk-through is the check that matters here.
- Print — Slice 5.

### Found while building — for Recipe Costing, not this page

**Bubu arare** (Birite, order unit EA) was given a pack of **1,210.58 oz** in Recipe Costing on
2026-10-06. That looks like a typo — possibly a price typed into the pack-size box. Because the
price list is shared, the count sheet faithfully asks for "Full × 1210.58 oz" plus loose ounces.
Fix it in Recipe Costing; nothing here needs to change.
---

## Slice 2 as built

`tempest_inventory.html` (manager set-up added), `scripts/check_inventory.py` (rewritten
around a stateful stub), `docs/inventory-guide-slice2.sql` (new; Stephen ran it),
`.github/workflows/inventory-guard.yml` (now also watches `vendor/**`, since the page loads
SortableJS). **No shared file touched.**

### The table — `docs/inventory-guide-slice2.sql`, run 2026-10-07

`inventory_left_off` (`location, order_item_id, active, created_at`; one active row per item
per location; RLS as Slice 0, no delete). Seeded with the **56** active guide items not on the
count on 2026-10-07 — the 48 on Paper Goods, Cleaning, Equipment and Bar, and the 8 marked Not
counted — **listed by id**, not "whatever is unplaced", so nothing new could slip in as left
off. Its check refuses (and keeps nothing) unless exactly 56 are left off, none is also
counted, and every active guide item is now either counted or left off. Proved first on a
throwaway Postgres with Slice 0 applied: 8 of 8, including that a guide item added before
the run makes it refuse. Stephen's run returned `inventory_left_off 56, inventory_items 216`;
verified read-only with the anon key: 56 left off, 198 counted, 0 both, **0 new**.

### What it does

- **A Manager switch** (the same PIN and `sessionStorage` key as Meat and Portion). The PIN
  box is restated qualified, so it renders at the 1.4rem `kitchen.css` intended rather than
  losing to `.modal input[type="tel"]` at 15.2px. Unlocking reads two more tables — the order
  guide and the left-off list — which staff never ask for; neither is asked for a price.
- **Manager mode is set-up, not counting**: the boxes give way to a grip, **Move** and
  **Remove** on every row.
- **Drag** reorders within a place: one SortableJS list per place, grabbed only by
  `.drag-handle`, no shared group, so a row cannot be dropped into another place. A drop
  renumbers that place 10, 20, 30 … and PATCHes only the rows whose number changed. Any
  failure re-reads the sheet, since some PATCHes may have landed.
- **Move** opens a place picker: *Move it* (one PATCH of `place_id` and `sort_order`, to the
  bottom of the new place) or *Also count it* (a POST of a second row). Places where the item
  is already counted are shown and disabled, never silently offered.
- **Remove** asks first. In a second place it retires just that row. In its **last** place it
  records the item as left off **first**, then retires the row — and if the record fails, it
  does not retire: an item is never in neither list.
- **New on the order guide** heads manager mode: every active guide item neither counted nor
  left off, with **Add** (the picker) and **Don't count**. On live data today it reads "Nothing
  new — every order-guide item is counted or left off on purpose."
- **Left off on purpose**, collapsed, with **Count it** — which adds the count row first and
  only then undoes the left-off record, for the same reason.
- **Places** — reorder (▲▼, renumbering), rename, retire (only when empty, and the page itself
  refuses even if the button were live), and add (at the end of the walk). A name already in
  use is refused before any write, ignoring case and spacing; a retired place's name, which
  the table still holds, comes back as a plain message rather than a failure. Controls that
  cannot be used are dashed and faint, not merely inert.
- **One write at a time.** While a write is in flight every other action says "Still saving"
  and the drag lists are locked. **Every write ends in a fresh read** (kept on screen, no
  spinner), so the screen shows what the table holds — including after a lost answer, which is
  reported as "No answer", never as saved.

### Proved

- `check_inventory.py`: **208 assertions, 16 scenarios, clean** — slice 1's seven and nine
  more (mgr, drag, dragfail, move, remove, newitems, places, busy, lost). The stub is stateful
  and enforces the real unique keys with 409s, so "after the re-read" checks mean something.
- **It fails when it should**: nineteen deliberate breaks, each in a throwaway copy, each
  caught — no busy guard; retire-before-record; drag between places; no re-read after a write;
  no answer reported as saved; Count it undoing before adding; staff seeing controls; drag
  not locked while saving; drag saving every row; retiring a full place; a case-sensitive name
  check; left-off items shown as new; staff reading the guide; any PIN unlocking; a 15.2px PIN
  box; moving to its own place; a new place first instead of last; an orphan given a grip; and
  disabled controls drawn like live ones. Two of these were **missed on the first pass** —
  Count it's failure path and the page's own retire refusal — and the tests were added.
- `check_styling.py`: clean, 11 pages, **85 inputs** measured (the PIN and place-name boxes
  are new, both ≥16px), register unchanged at 75.
- **Live data, read-only, manager mode** at 390px: 0 new, ten places, 56 left off, 216 rows
  each with a grip, ten drag lists, nothing past the edge. Nothing was clicked.

### Not proved

- **Drag with a finger.** The harness fires SortableJS's own `onEnd` after moving the row; it
  cannot hold a touch. `touch-action` is on `.drag-handle` only (the shared rule), as the
  review checklist requires — but whether a cook can scroll the sheet in manager mode, and
  drag by the grip, is for Stephen's hand test on an iPhone.
- **The pop-ups at a true 390px.** Headless Chrome lays out fixed elements against a 500px
  viewport (the costing doc's trap 3), so screenshots crop them. The harness proves nothing
  inside them overflows and that every picker button is a 48px target; their look on a phone
  is the hand test's.
- Print — Slice 5.

---

## Slice 3 as built

`tempest_inventory.html` (counting added), `scripts/check_inventory.py` (six scenarios added;
the stub learned the count tables, the staff list and the upsert), and this document. **No
SQL** — Slice 0's tables already had everything, including the open-only rule. **No shared
file touched.**

### What it does

- **Two more reads on every load**: the open count (`status=eq.open`, at most one by the
  table's own index) and the active staff list; then, if a count is open, **its** lines
  (`count_id=eq.<id>`). Nothing is drawn until all have landed. On live data today, with no
  count open: all five reads answer 200, and every box stays locked.
- **A Manager can start the month's count** — this month or last month, named in the
  question. One write, then a log line saying who. The table refuses a second open count and
  a second count for a month (unique keys), and the page says so in words. Until anything
  is counted, a count started under the wrong month can be moved ("Wrong month? Make it
  September 2026"); after that the button goes, and the page refuses even if asked.
- **Who is counting**: a name from the active staff list (once each, not once per shift),
  kept while the page is open, always shown, changed in one tap. **Change** first sends
  anything typed but not yet saved, under the name it was typed under. No name, no boxes.
- **Each row saves itself** 1.2 s after typing stops, or at once when the box loses focus,
  as an **upsert on `(count_id, inventory_item_id)`** — `on_conflict` with
  `Prefer: resolution=merge-duplicates`. A retry after a lost answer updates the same line
  and cannot add a second. **One request per row at a time**; an edit made while one is in
  flight is sent when it lands, so the table always ends on the newest value.
- **✓ only for a confirmed row**: a 2xx carrying exactly one row, for this item and this
  count, with the values that were sent. Anything else is "Not saved — …" in words, as a 44px
  button that retries: *no answer from the server*, *the server did not confirm it*, *the
  server refused it*, or *the count may have been closed* (which also re-reads the sheet).
- **Blank is not zero**: both boxes blank = not counted; one blank beside a filled box = 0;
  `0` typed is a count. Clearing a saved row sends blanks — nothing is deleted. Typing and
  erasing before a save sends nothing; retyping the saved value sends nothing. Words are
  refused in words ("Numbers only — like 2 or 1.5"); a comma is read as a decimal point.
- **A row keeps the pack it was counted against**: once counted, its boxes come from the
  line's `pack_qty_snap` / `pack_unit_snap`, not today's price list, so "4 loose" cannot
  change meaning mid-count. Each save records the pack the boxes showed.
- **Progress counts only what is saved**: each place "12 of 53 counted", the bar "45 of 216
  counted". A typed-but-unconfirmed number does not count.
- **A refresh never wipes a typed number**: the sheet re-reads when a phone comes back to the
  page (others' counts appear), but not while someone is typing, and a re-draw keeps every
  unsaved value in its box.

### Proved

- `check_inventory.py`: **288 assertions, 22 scenarios, clean** — slices 1–2's sixteen and six
  more (start, count, inflight, countlost, countclosed, who). The stub enforces the upsert, the
  unique keys and the open-only RLS rule, answering 403 for a closed count as PostgREST does.
- **It fails when it should**: fifteen deliberate breaks in throwaway copies. **Fourteen
  caught** — a plain POST instead of the upsert; no in-flight guard; a blank partner not
  zeroed; today's pack instead of the counted one; a tick on any 2xx (missed at first — the
  stub never answered 2xx without a row; the case was added); `0` read as blank; no name
  needed; Change dropping typed values; names not de-duplicated; lines of every count read;
  a start with no log; a closed count not re-read; a refresh wiping typed values; a month
  changed after counting. **One correctly not caught**: treating "no answer" as success
  changes nothing, because with no answer there is no row to confirm.
- `check_styling.py`: clean, 11 pages, **86 inputs** (the name box is new, at 16px), register
  unchanged at 75.
- **Live data, read-only, with every write blocked** in the page before it could leave: five
  reads, all 200; no count open; 220 boxes, all locked.

### Not proved, and known

- **On a real phone, against the live table** — the hand test: the real October count.
- **The log line is best-effort.** If the count is created but the log write fails, the count
  stands and nothing says who started it. Slice 7's close and reopen must not be built that
  way: a reopen that is not recorded is the failure Stephen asked to prevent.
- **Remove during an open count** retires a row whose line may hold a count; that number then
  stops showing and stops counting. Slice 6 (values) and Slice 7 (close) must decide what a
  line of a retired row means — most likely: still counted, shown under "Not in an active
  place" until the month closes.
- Typed numbers live only in the page: a closed tab, or a count closed underneath, loses
  them. That is Slice 4.

---

## Slice 4 as built

`tempest_inventory.html` (kept-on-device, retry, the header line, the leave guard) and
`scripts/check_inventory.py` (five scenarios added; the stub can cut the network, and a
scenario can **reload the page for real** and carry its results across). **No SQL. No shared
file touched.**

### What it does

- **On the device before it is sent.** Every keystroke writes the row's typed values — and
  who typed them, and when — to `localStorage`, one key per count
  (`boxkitchen_inv_pending_<count id>`), before any request. A row leaves the device only
  when the table has confirmed it. `localStorage`, not `sessionStorage`: it survives the tab
  closing, which is the point.
- **No answer is not an error.** A save with no answer (or a 5xx) leaves the row
  "Waiting for signal — kept on this device": no tick, no red. Refusals (4xx) stay red with
  their reason, as in Slice 3; a closed count still re-reads the sheet.
- **It sends itself.** A retry is a **fresh read first**, then the send — the read proves
  the signal is back and shows what the table now holds. It fires when the phone reports it
  is back online, when the page comes back to the front, every 20 seconds while anything is
  waiting, from **Try now**, and when the page is next opened on that device.
- **Reconcile, don't overwrite.** Before sending a kept value the page compares it with the
  freshly read line: already there (a lost answer that had landed) → simply confirmed, never
  sent twice; counted on another device **after** this was typed → theirs stays, and the row
  says so ("✓ Counted by Jose — newer than the 3 typed here earlier, which was not saved");
  otherwise → sent. To make that comparison honest, `updated_at` is now **when the count was
  typed**, not when it arrived.
- **Sent under the name it was typed under**, even if whoever opens the page next has not
  picked a name.
- **The header says what this device holds** — a highlighter line in the sticky header,
  visible wherever you scroll: "3 counts waiting for signal — kept on this device, and sent by
  themselves when it comes back." with **Try now**. Rows that need a person ("see the rows
  marked in red") are counted there too.
- **Counts kept for a count that is no longer open** (an orphan — the month was closed, or
  another count opened) are **never sent and never shown in this count's boxes**. The header
  names them ("2 counts typed on this device for the September 2026 count were never saved,
  and that count is no longer open") with **Forget them**, which asks first.
- **Leaving asks first.** The Home link asks ("3 counts are not saved yet. They stay on this
  device and send the next time this page is open here. Leave anyway?"); closing the tab asks
  where the browser allows it (iOS Safari mostly does not — which is fine, because nothing is
  lost either way).
- **Offline, the sheet stays.** A refresh with no signal used to replace the sheet with "Could
  not load"; a quiet re-read that fails now keeps the sheet and every waiting number on screen,
  says "No signal — showing what was last loaded", and tries again.

### Proved

- `check_inventory.py`: **323 assertions, 27 scenarios, clean** (about 15 seconds). The five new
  ones: **offline** (no signal; three rows waiting; the header line; nothing in the table; the
  leave question; then a **real page reload** with the signal back and no name picked — all
  three sent by themselves, under the name typed, stamped with when they were typed, the
  device emptied), **comeback** (a refresh with no signal keeps the sheet; the "online" event
  sends; with no event, the 20-second timer does), **newer** (a real reload after another
  device counted the row later: nothing sent over it, and the row says whose stands),
  **orphaned** (kept values for a closed September count shown, never sent, forgotten on
  request), **leave**. Slice 3's *countlost* now proves that Try now re-reads first, so a
  value that had landed is confirmed **without being sent again**.
- **It fails when it should**: fourteen deliberate breaks. **Thirteen caught** — not kept
  before sending; no answer shown as a red error; nothing restored on load; sent over a newer
  count; stamped when sent; an offline refresh wiping the sheet; no "online" listener; no retry
  timer; orphans sent as this count; leaving never asking; no header line; kept values sent
  under the current name; the device forgetting before the table confirmed. **One correctly
  not caught**: removing the re-read's "already landed" check changes nothing, because the
  save itself refuses to send a value the table already holds.
- `check_styling.py`: clean, 11 pages, 86 inputs, register unchanged at 75.

### Not proved

- **On a real phone in Airplane Mode** — Stephen's hand test.
- **Two devices clocked minutes apart.** "Newer" compares the two devices' clocks. Phones
  and tablets set their clocks from the network, so they agree to within seconds; a device
  with a hand-set clock could lose or win a tie it should not.
- **Storage refused** (a private window, a full disk): the page carries on without keeping
  values, as before this slice. It does not say so.

---

## Out of scope

- **The bar.** Stephen: bar stock "will be counted when we build the inventory sheet for the
  bar." That includes the drinks and juices on the food order guide. A later build; the
  `inventory_places` / `inventory_items` tables could serve it, but nothing here assumes so.
- **House-made prep** (sauces, dressings, portioned proteins). Valuing them needs recipe
  costing (B4.3). The tables allow it later; nothing here builds toward a guess.

  **Stephen, 2026-10-07:** "we will need to add a 'prepared items' section to cost out all the
  prep to maintain a proper and accurate inventory … that is something that we can link
  through recipe costing once both pages are fully built. We have time, I just need to start
  thinking about what that looks like." Unvalued prep on the shelves at month-end makes the
  month's true food cost read high, so it belongs in the count. A first sketch, offered and
  not yet decided:

  - **Counted in the same walk**, under a *Prepared* group in each place — the aioli in the
    prep cooler is counted standing at the prep cooler, not on a second trip.
  - **Counted by container** — quart, 1/6 pan, portion — with the same full-and-partial idea.
  - **Listed from the recipe library** (each recipe has a yield), or the prep lists, or both.
  - **Valued at recipe cost per yield unit** from Recipe Costing (B4.3): the link Stephen
    described, and the piece that has to exist first.
  - **One schema change**: `inventory_items` requires `order_item_id` today, so a prepared
    item needs a recipe link instead (one or the other, never both).

  Stephen's to decide when it starts: which prep counts; the container units; whether a
  partly-used container counts; where the list comes from.
- **Ordering help** — on-hand vs par. The order guide keeps par.
- **Writing to the price list.** Missing prices are fixed in Recipe Costing, which has four
  slices of safety around that write path. Inventory gets a link, not a second door.
- **Changing Flash Reports**, including what counts as a "food" purchase there.
- **Fixing `.count-input`'s 15.2px** on Meat and Portion Count (see "Found while planning").
- **Other locations.** Everything is `location`-scoped, so Phase C inherits it.

---

## Constraints

From `CLAUDE.md`, `docs/review-checklist.md`, and Stephen's rules for this window:

- **The database is live. Never write test rows.** Read-only GETs are fine. Every write path
  is proved against a stubbed `api()` in `scripts/check_inventory.py`.
- **Any new table is SQL Stephen runs.** No DDL from a session.
- **Ask before any push, PR, merge or deploy.** Before a PR, bring the branch up to date with
  `main`. Never reset, stash or switch branches here without asking.
- **Shared files last**: `index.html`, `assets/kitchen.css`, `scripts/check_styling.py`,
  `CLAUDE.md`. The page's own rules live in its own `<style>`, which CLAUDE.md allows for
  page-only rules — so `kitchen.css` and its `?v=` stay as they are.
- **16px.** Every new input, written qualified (`.modal input[type="text"].x,.x`) wherever it
  could sit in a modal. Runtime-built inputs are measured by the harness, not by eye.
- **No new `:root`**, no redeclared core token. **State is fill, weight and border, never
  hue**: a counted box is the ink-filled state; *not valued* is the yellow highlighter, not
  red; nothing "done" is green.
- **`--faint` is inactive text only.** Live secondary text — vendor names, pack sizes — is
  `--grey`.
- **Print**: every manager-only element and every modal hidden under `@media print`.
- **The manager PIN and site password are never written into this doc, a PR, or output.**

---

## Risks

| risk | why it matters | mitigation |
|---|---|---|
| The first count is mostly unvalued | 1 of 206 items is priced today | Counting and valuing are separate. Quantities still make the opening count. Values fill in as costing fills, up until close. Decide when to close October by how much is valued (Question 4) |
| Prices freeze on the **close** day, not the count day | Close a week late and October is valued at mid-November prices | Close within a day or two of counting. The page shows both dates side by side |
| Costing changes a pack after an item is counted | "7 loose" read under a new meaning is a wrong number that looks right | Each row stores the pack it was counted against. A mismatch is *not valued — pack changed*, never re-read |
| No signal in a cooler or freezer | A count typed and silently lost is the worst failure here | Slice 4, before any real count |
| Blank read as zero | "We forgot the freezer" looks like "the freezer is empty" | Blank is stored as *no row*; closing lists every uncounted item first |
| A new guide item never gets a place | It silently misses every count after | "Not on the count" (Slice 2) |
| Flash purchases include vendors not on the count | True food cost % is off by whatever stock they leave on the shelves | Question 3. The % says which vendors it covers |
| The PIN is not security | Prices and values are readable by anyone with the page source | The same as Flash and Costing today. RLS is the protection; the PIN only hides the dollars from view |
| The other window merges to `main` throughout | Conflicts in shared files, a `?v=` mismatch | Shared files last; update from `main` before every PR |

---

## How to verify without touching live data

Exactly as `docs/costing-bulk-entry.md` lays out, and for the same reasons:

- **`scripts/check_inventory.py`** loads the real page, stubs `XMLHttpRequest` before the
  page's script runs (so nothing can leave the machine), drives it in headless Chrome, and
  asserts on payloads and the DOM. It simulates delay, a dropped response, and no network.
- **Real rows, read-only**, for rendering: GETs against the live tables are fine.
- **Phone width** inside a 390px wrapper; widths measured there, heights judged from a
  screenshot (the costing doc's three traps apply unchanged).
- **Assert, don't eyeball**: computed `fontSize` on runtime-built boxes; that no request is
  anything but GET in read-only slices; that staff-mode HTML contains no `$`.
- **Hand test on Stephen's iPhone** before each write slice merges, with every step's keys
  spelled out — including Airplane Mode for Slice 4.

---

## Questions still open

1. ~~Which place each of the 206 items is in~~ — **answered 2026-10-06**, see Slice 0.
2. ~~Does anything live in two places?~~ — **answered 2026-10-06: yes, 18 items**, mostly
   vinegar-shelf items with backup stock in dry storage. See Slice 0.
3. **Stock from vendors not on the order guide.** Is there month-end stock from PANORAMA,
   OSPREY, PEACH FARM or CHALLENGE (fish in the freezer, say)? If so it is not counted, and
   the true food cost % is off by its value. And is ARAMARK food? If not, Flash's purchases
   include it anyway — out of scope to change, but the % should say so.
4. **When is the first count, and when does it close?** The suggestion is the night of
   October 31 or the morning of November 1, before deliveries, as the opening count. Close it
   once the big-money items are priced, or close it partial and accept the first month's %
   will be marked incomplete.
5. **Half a jug.** For a pack of 1, one box with decimals (1.5) — is that how you would count
   an opened jug or bottle, or would you rather it was whole numbers only?
