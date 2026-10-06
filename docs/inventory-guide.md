# Inventory Guide — the monthly count

Status: **plan v1, approved by Stephen 2026-10-06** with one change: Tempest's real storage
places, in walking order (see "Decisions"). **Slice 0 is closed** — the tables are live and
seeded. **Slice 1 is built** on the branch, not merged: see "Slice 1 as built". Every decision below was made
by Stephen in the interview that produced this document. Branch `inventory-guide`, in the
worktree `~/Developer/boxkitchen-inventory`.

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

> **BUILT 2026-10-06** on `inventory-guide`, not yet merged — see "Slice 1 as built" below.
> The walk-through is still to do.

### Slice 2 — Set-up (manager)

- Add, rename, reorder and retire places.
- Move an item to another place; add it to a second one; reorder within a place (drag, as on
  Orders — SortableJS, manager-only, within a place).
- **"Not on the count"** — every active guide item that is in no place, with Add. A food item
  added to the order guide next spring must not silently miss every count after it. Non-food
  shelves are listed here too, collapsed, so a manager *can* add them.

**Done when:** every action writes only in manager mode; the harness asserts each payload;
a new guide item appears under "Not on the count" without any set-up.

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

### Slice 4 — Nothing typed is lost

Coolers and freezers are where the signal dies.

- A typed value that has not had its ✓ is kept **on the phone** until it has, and retried
  when the signal comes back.
- The header says so plainly: *"3 counts waiting for signal."*
- Leaving the page with anything waiting asks first.
- If a second phone saved the same row meanwhile, the newer one wins and the row says who.

**Done when:** with the network cut in the harness, typed counts survive a reload and go
through when it returns; nothing is ever shown ✓ that the database did not confirm.

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
  section holding `.link-btn` (Try again). HEADER, EMPTY / LOADING and TOAST already say
  every page. Re-check the list against the page at the time; later slices add to it.

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

## Out of scope

- **The bar.** Stephen: bar stock "will be counted when we build the inventory sheet for the
  bar." That includes the drinks and juices on the food order guide. A later build; the
  `inventory_places` / `inventory_items` tables could serve it, but nothing here assumes so.
- **House-made prep** (sauces, dressings, portioned proteins). Valuing them needs recipe
  costing (B4.3). The tables allow it later; nothing here builds toward a guess.
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
