# Costing — make the ledger fillable

Status: **PLANNED, not built.** Written 2026-09-16, after the #128 walk.
This is a build doc. Nothing in it has been implemented.

Target file: `tempest_costing.html` (plus a small addition to `assets/kitchen.css`).

---

## The problem, in numbers

`ingredient_costs` holds **5 rows**. The order guide holds **254 active items**. Everything
downstream of the ledger — recipe costing %, inventory value, invoice pairing — is waiting
behind those 5 rows.

Entry stalled for two reasons. The first is now fixed: the **＋ Add button was invisible**
on the live page from the restyle until PR #138 (`.add-btn` is `display:none` outside
`.manager-mode`, which this page never sets). The second is not fixed, and is what this
doc is about: **entering an item is slow enough that entering 250 of them is not a job
anyone finishes.**

### What one item costs today

Read from `openAdd()` / `onPick()` / `saveItem()`:

1. Tap **＋ Add**. Modal opens.
2. The order-guide picker is a **flat `<select>` of up to 254 `<option>`s**, each formatted
   `Vendor » Name`, in `vendor.asc, sort_order.asc` order. There is **no search**. On a
   phone this is a native scroll wheel through 254 entries.
3. The picker **defaults to `✎ Custom (not on order guide)`**, and focus goes to the *name*
   field — so the path of least resistance creates an unlinked off-guide item rather than
   one tied to the order guide.
4. Fill invoice name, pack qty, unit, pack price.
5. Save → `closeEdit(); render();` — **the modal closes.** There is no "add another".

So every item is a full open → hunt → four fields → save → close cycle, and the fastest
available mistake is to create a duplicate that isn't linked to the guide.

### Where the items actually are

| vendor | active items | share |
|---|---:|---:|
| Birite | 151 | 59% |
| Cooks Produce | 78 | 31% |
| Dairy | 16 | 6% |
| Schmitz Ranch | 6 | 2% |
| Asia Intl | 3 | 1% |
| **total** | **254** | |

**Two vendors are 90% of the guide.** Entry will in practice be done vendor by vendor,
against one invoice or one order guide at a time — which is also how the paper arrives.

---

## Goals

1. Entering a run of items is a **run**, not a sequence of separate tasks.
2. Finding an item in the picker takes a keystroke or two, not a scroll through 254.
3. The default action links to the order guide; going off-guide is deliberate.
4. Nothing about the existing edit-an-item flow changes.

## Non-goals — deliberately out of this slice

- **Invoice entry (B4.2).** Still the next build after this one. It updates prices on items
  already in the ledger, so it wants a populated ledger first. Building it now would repeat
  exactly the #128 mistake of shipping against an empty table.
- **Recipe costing (B4.3), inventory (B4.4), the Dropbox OCR feed (Phase 2).**
- **Showing `invoice_ref`** — that is issue #140, and it belongs with B4.2.
- **Bulk import from a CSV or a paste.** Tempting given `~/Downloads/Tempest_ingredient_costs_DRAFT.csv`,
  but that file is a scraped draft with OCR duplicates and unconfirmed pack sizes. Pack size
  is the one value the whole model hinges on and the one OCR gets wrong most often. Confirming
  a pack once, by hand, on an item you actually use, is the design — not a bulk load of
  values nobody checked.

---

## Design

### 1. Filter the picker instead of building a typeahead

**No page in this app has a searchable picker.** All eight pages with a `<select>` use a
plain one. Introducing a custom typeahead means a new component, new CSS, new focus and
keyboard behaviour, and a new thing to get wrong on a phone.

Instead, compose two controls that already exist:

```
┌─ Order-guide item ─────────────────────────┐
│ [ Filter items…                          ] │  ← .search, the input the list already uses
│ [ Birite » Dried oregano, Mexican      ▾ ] │  ← the existing <select>, options filtered
└────────────────────────────────────────────┘
```

Typing in the filter rebuilds the `<option>` list. The select stays a native select, so it
keeps native phone behaviour for free. The filter input reuses `.search`, already defined
and already on this page.

Match against `vendor + name`, the same `hay` shape `render()` already uses for the list
search — so the picker and the list behave identically, which is the point.

### 2. Default to the first unpriced order-guide item, not Custom

`✎ Custom` moves to the **bottom** of the option list and stops being the default. The
default becomes the first option in the filtered list. Going off-guide stays one tap away,
but it stops being what happens when you don't look.

Note `openAdd()` already excludes items that are costed (`costedOrderIds()`), so the picker
is a list of *remaining work* — 249 items today. That is a useful property; keep it.

### 3. Save & add next

Add a third button to the modal's `.modal-btns`, and keep the current two:

| button | behaviour |
|---|---|
| Cancel | unchanged |
| Save | unchanged — saves and closes |
| **Save & next** | saves, keeps the modal open, clears qty/unit/price/alias, re-runs the picker, leaves the filter text alone, focuses the filter |

After a Save & next the count in the header updates and the toast fires, so there is still
feedback per item — you just don't lose your place. The vendor filter surviving the save is
the whole point: working Birite's 151 means typing `birite` once, not 151 times.

### 4. Nothing else moves

The edit path, retire/restore, price history and the unit-cost preview are untouched.

---

## Constraints this must respect

From `CLAUDE.md` and `docs/review-checklist.md`:

- **Class names are load-bearing.** The JS reaches for them by name. Add names; never rename
  one. `.ing-alias` vs the new `.ing-alias-line` in PR #139 is the pattern to follow.
- **No new `:root`,** no redeclared core token. Scoped tokens only.
- **State is fill, weight and border — never hue.** A filtered-empty picker is not a red error.
- **`--faint` is for inactive or locked text only.** The filter's placeholder carries meaning,
  so it is `--grey`, matching `.search::placeholder` as it already renders.
- **Run `python3 scripts/check_styling.py` before the PR.** CI runs it too.
- **Bump `?v=` on all ten pages** if and only if `assets/kitchen.css` changes. Ten must agree.
- **Print:** anything added inside the modal is screen-only; the print block already hides
  `.modal-bg`. Confirm rather than assume.
- **The database is live.** Read-only queries are fine. Do not write test rows into
  `ingredient_costs` — entry is in progress and a stray row lands inside someone's real work.

---

## Risks

| risk | why it matters | mitigation |
|---|---|---|
| Rebuilding `<option>`s on every keystroke | 254 options re-rendered per key on a phone | Build the option string once into an array at `openAdd()`; filter that array, don't re-read the DOM |
| The native select keeps a stale selection after filtering | You think you picked item A and save item B — a wrong price on a real item | After every filter, explicitly set `.value` to the first match and re-run `onPick()`; never leave the selection implicit |
| `onPick()` disables `#fName` for guide items | Save & next must re-enable it before the next entry or a Custom entry silently can't be typed | Reset `disabled=false` in the clear step, not only in `openAdd()` |
| Save & next double-fires on a slow connection | Duplicate rows against the same `order_item_id` | `saveItem()` already disables the button and guards duplicates via `costedOrderIds()`; keep both, and re-enable only in the callback |
| Filter input is below 16px | iOS zooms the page on focus — the live bug in #135 | `.search` is already 16px. Do not introduce a smaller input here; this slice must not add to #135's list |

---

## Slices

This is **one slice**. It is a single page, one modal, four behaviours, and it can be
reviewed in one sitting. If it grows past that while being built, the split is:

- **1a** — filter + default-to-first-unpriced (changes what you see)
- **1b** — Save & next (changes what happens after Save)

## Done when

- [ ] Typing in the filter narrows the picker, matching on vendor and name
- [ ] The picker defaults to the first unpriced guide item; `✎ Custom` is last
- [ ] Save & next saves, keeps the modal open, clears the value fields, and keeps the filter
- [ ] The selected option always matches what the fields show — verified by saving a filtered pick and reading the row back
- [ ] Editing, retire/restore and price history behave exactly as before
- [ ] `check_styling.py` clean; `?v=` bumped on all ten pages iff `kitchen.css` changed
- [ ] Walked at 390px with real rows before the PR — see the method note below

## How to see it before shipping

There is no browser tool in this repo's sessions. The #128 walk used headless Chrome from
Bash, and two traps will silently give wrong answers:

1. **`--window-size` does not set the layout viewport.** It stays 500px; only the capture is
   resized, so a screenshot looks catastrophically clipped when nothing is wrong. Simulate a
   phone with a `<div style="width:390px">` wrapper and measure inside it.
2. **Keep the real viewport under 760px.** `kitchen.css` has `@media (min-width:760px)` rules
   that re-pad `.header` with `calc((100% - 720px)/2 + 18px)`; against a 390px wrapper that
   computes negative and clamps to zero, silently deleting the header padding.

Build the harness by replaying the page's own string-building against rows pulled read-only
from PostgREST, link the real `assets/kitchen.css`, and assert on `scrollWidth > clientWidth`
rather than eyeballing. Screenshot to confirm; measure to conclude.

---

## Minors list

Findings logged during the build that aren't worth stopping for. Append, don't clear —
something minor in this slice is often a blocker in the next one.

_(empty — nothing built yet)_

---

## Adversarial review

Reviewed 2026-09-16 against `tempest_costing.html` at `71fca66`, `assets/kitchen.css`,
`CLAUDE.md`, `docs/review-checklist.md`, and read-only GETs of `order_items`,
`ingredient_costs` and `ingredient_price_history`. Nothing was written to the database.

**Verdict: No, not safe to build from as written.** The plan makes its own worst risk
worse. It removes the one signal that tells you nobody picked an item (Custom being the
default), then automatically picks an item on every keystroke and after every save. And
the only fix it offers for a stale selection ("set `.value` to the first match") is itself
how a price ends up on the wrong item. A wrong price saved this way looks exactly like a
real one, and nothing in the data would tell you afterwards. Two of the plan's stated
facts about the existing code are also wrong (B4, M1).

### Blockers

**B1. Defaulting to the first item turns "didn't look" into "priced the wrong item."**
Today, if you don't touch the picker you get a Custom item, and saving fails unless you
type a name. Under the plan, the same inattention saves a price against whatever item
happens to be first. On a run it gets worse: after each Save & next the item you just
saved drops out of the list, so the *next* item in the guide is selected automatically.
Guide order is `sort_order`. Invoice order is not. A chef reading down a Birite invoice,
eyes on the paper and one thumb on the phone, types qty, price, Save & next. Every price
lands on the next guide item, not the next invoice line. Nothing errors. The only check
is the greyed-out name field, and it shows no vendor.
*Required:* no item is selected after a save or a filter change. Saving should need an
explicit pick in that cycle (e.g. an empty "— choose item —" option that blocks Save).

**B2. The fix for the stale selection is itself a wrong-item bug.** Risk 2's mitigation
re-picks the first match after *every* filter keystroke. Picture the 40th item: the item
is picked, qty and price are typed, then the chef touches the filter. Maybe to double-check
the item, maybe a stray tap, maybe a colleague takes the phone. The selection silently
jumps to a different item, but `fQty`/`fPrice` keep their values. `onPick()` only fills
`fUnit` when it is empty (`tempest_costing.html:255`), so the old unit stays too. Save now
writes item A's pack onto item B.
Concrete case in today's data: `Slab bacon` is on the guide twice, Asia Intl (id 169) and
Birite (id 88). Filter `bacon` and the first match is Asia Intl, because the list sorts
by vendor. The disabled name field reads "Slab bacon" either way.
*Required:* changing the filter clears the selection *and* the value fields. Or: changing
the filter after any value is typed asks first. Show the vendor next to the locked name.

**B3. A wrong price can't be traced afterwards, and the obvious fix makes it permanent.**
- No row records who entered it or from which invoice. Price history is written
  `source:'manual', invoice_ref:null` (`:320`), and `effective_date` defaults to the day
  you type it, not the invoice date. Entering a stack of last month's invoices records
  them all as today.
- `logPrice` has no callback. If it fails, the price is in the ledger with no history row.
- Say Birite slab bacon's price gets saved against Asia Intl. The natural fix is **Retire**
  on the Asia Intl row. But `costedOrderIds()` (`:229`) counts retired rows, so Asia Intl
  slab bacon can then never be added again. The page also has no way to re-link a row to
  the right item (`pickWrap` is hidden on edit, `:262`). The only correct fix is to edit
  the wrong row's price to the right value, and a false price-history entry stays behind.
- There is no sanity check at all: no warning when unit cost is 10× out, or when qty/price
  look swapped.
*Required, in this slice:* capture the invoice ref and invoice date on entry (that means
#140's `invoice_ref` is not separable, see S1). Check that the history POST succeeded
before clearing fields. Write down the recovery path for a mispick.

**B4. The double-submit mitigation rests on something the code doesn't do.** Risk 4 says
"`saveItem()` already disables the button". It disables `#saveBtn` by id (`:289`), and
nothing else. A new Save & next button stays live while the request is in flight, and so
does Save once Save & next was the one pressed. The duplicate check reads `items`, which
only changes when a response comes back (`:301`), so two POSTs in flight both pass it.
Kitchen wifi makes this worse. `api()` has no timeout, and `onerror` passes `null`, so a
POST that *succeeded* but lost its response shows "Add failed — try again". Retrying then
creates a duplicate row. I could not confirm read-only whether
`ingredient_costs(location, order_item_id)` has a unique constraint. **If it doesn't,
duplicates are guaranteed eventually.**
*Required:* disable both buttons and the picker while a save is in flight, with a timeout.
Before a retry, re-GET the row by `order_item_id`. Add or confirm a unique partial index
(a migration, so ask first).

### Majors

**M1. The claim that the filter is already 16px is false.** `.search` is `font-size:0.95rem`,
about 15.2px (`kitchen.css:412`). iOS will zoom on focus, which is exactly the #135 bug
the plan says it will avoid. `user-scalable=no` (`:5`) doesn't stop that on iOS. It also
has `min-width:200px`, which was made for the header toolbar, not a 440px modal with 22px
padding.

**M2. Matching on the whole phrase breaks the plan's own workflow.** `render()` checks
whether the full query appears as one unbroken string (`:190`). The plan keeps `birite`
in the filter across saves. To find an item you then type `birite oregano`. That doesn't
match `Birite Dried oregano, Mexican`, because "dried" sits in between. So you either
clear the vendor text every time, or scroll up to ~150 options. That's the problem the
plan set out to remove, still there on the 40th item. Also, the list's search looks at
`invoice_alias` and the picker's wouldn't, so "behave identically" isn't true either.
Match word by word.

**M3. The search only knows the guide's names, but the chef is holding an invoice.** The
paper says `CHKN BRST BNLS 40#`. The guide says `Chicken breast`. The hard part is
matching one to the other in your head, and the plan doesn't touch it. At minimum, don't
promise "a keystroke or two".

**M4. The auto-filled unit is the order unit, not the pack unit, and a run will skip it.**
`order_items.unit` is `EA` for 103 items, `CS` for 78, `lb` for only 39. The existing
ledger rows use `lb`/`oz`. Save & next clears Unit and then `onPick()` fills in `CS`. A chef
types `40` and `139.60` and moves on, and the row saves as "40 CS", i.e. **$3.49 per case**.
It looks plausible and it's wrong for recipe costing. The plan calls pack size "the one
value the whole model hinges on" and then adds a step that fills in the wrong unit for it.
Either don't fill Unit during a run, or make it look unconfirmed until someone touches it.

**M5. Interruptions and handing the phone over aren't designed for.**
- A tap outside the modal closes it (`:352`) and throws away typed values and the filter.
  One-handed use makes that tap likely.
- A reload or iOS dropping the tab loses everything. PIN unlock survives in
  `sessionStorage`, so it *looks* like you picked up where you left off. You didn't.
- A handoff keeps the filter and the picked item. The next person can't tell those were
  picked for them.
- There's no running count *inside* the modal. The header count the plan relies on for
  feedback is behind a 70% black backdrop (`.modal-bg`, `kitchen.css:133`), and the toast
  shows for only 1.6s.

**M6. "Remaining work" means "no row", not "unpriced".** Row id 3 (`order_item_id` 33)
has no price, but because the row exists it's filtered out of the picker. It can only be
reached from the list. Goal 2's "first unpriced item" is therefore wrong, and the "249
remaining" figure is wrong too: 4 of the 5 rows are linked, so the picker holds 250. Any
unpriced row left behind by an interrupted entry disappears from the run. If the fix for
a network failure is "save with no price", that item drops out of the run for good.

**M7. The live table may already contain test data.** Price history for row 1 has
`effective_date` 2026-06-15 and 2026-07-20, both created 2026-09-02 within a minute of
each other, and one says `source:'invoice', invoice_ref:'SR-88214'`. The UI can't create
any of that. Before building "you'd be able to tell afterwards" on this table, confirm
which of the 5 rows are real.

### Minors

- m1. Focusing the filter from inside the XHR callback won't open the iOS keyboard, since
  it isn't a direct tap. When it does open, it covers most of an 88vh modal.
- m2. Three buttons in `.modal-btns` at 390px. Check that "Save & next" doesn't wrap, and
  that Save vs Save & next can't be mis-tapped with a thumb. They do different things.
- m3. The "(optional …)" span sets its colour inline (`:89`). If the build touches that
  area, move it into a class so `check_styling.py` can see it.
- m4. Every screen-only element added to the modal needs to be confirmed hidden under
  `@media print` (`kitchen.css:865` hides `.modal-bg`). The plan says to confirm, so do it.
- m5. The `curV` variable in `openAdd()` (`:238`) is dead code. It's harmless, but anyone
  "building the option array once" will read it as grouping that doesn't exist.
- m6. "Done when: verified by saving a filtered pick and reading the row back" breaks the
  rule against test rows in the live table. It has to be done against a stubbed `api()`
  (checklist §10), not production.

### On the plan's five risks

| # | verdict |
|---|---|
| 1 Rebuild cost | Not a real risk. 254 short strings is nothing. It crowds out the real ones. |
| 2 Stale selection | Real, but framed backwards. The mitigation causes wrong-item saves (B1, B2). The real issue is that the item and the values can get out of step. |
| 3 `fName` disabled | Mostly already handled: `onPick()` sets `disabled` both ways. The real danger is `fUnit` carrying over (B2, M4). |
| 4 Double-fire | Mitigation is based on a misreading (B4). The lost-response retry is missing. |
| 5 Sub-16px input | Real, and the plan's claim about it is false (M1). |

**What the list missed:** recording where a price came from (B3), fixing a mispick (B3),
unit auto-fill (M4), items with the same name (B2), interruptions and handoffs (M5), and
unpriced rows dropping out of the run (M6).

### Scope that can't be separated

- **S1. `invoice_ref` / invoice date (#140, B4.2).** This build is invoice entry in all but
  name: prices typed off paper invoices. Without the ref and date there's no way to audit
  the few hundred prices it exists to collect. Pull #140 in, at least as a sticky "Invoice
  #, date" field at the top of the run.
- **S2. Correcting a wrong link.** You can't ship a faster way to make mistakes without a
  way to fix them. Either allow re-linking on edit, or stop retired rows from blocking the
  picker.
