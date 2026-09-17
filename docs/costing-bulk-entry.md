# Costing — make the ledger fillable

Status: **PLANNED, not built.** v2, rewritten 2026-09-16 after the v1 plan was
reviewed and rejected. The review that rejected it is preserved verbatim in the
appendix; read it before this, because this document is the answer to it.

Target file: `tempest_costing.html`, plus additions to `assets/kitchen.css`.

---

## What the review changed

v1 proposed: filter a native `<select>`, auto-select the first match, add "Save & next".
The review's verdict was **not safe to build**, and it was right. Four of v1's factual
claims about the existing code were wrong, and — worse — v1's central mechanism *was* the
bug. Auto-selecting the first match is precisely how a price lands on the wrong item
without anyone noticing.

The corrections that reshape this plan:

| v1 said | actually |
|---|---|
| `.search` is 16px, so no #135 risk | `0.95rem` = **15.2px**. v1 would have added a sub-16px input while claiming it didn't |
| `saveItem()` already disables the button | it disables `#saveBtn` **by id only** |
| the picker lists remaining work, 249 items | **250**, and `costedOrderIds()` keys on `order_item_id != null` regardless of priced-or-retired |
| "first unpriced item" | no such concept exists — any row that *exists* drops out |

And the data facts that drive the design: `order_items.unit` is **EA 103 / CS 78 / lb 39**,
so auto-filling unit writes `40 CS` — $3.49 per *case* — which looks right and poisons every
recipe cost downstream. `Slab bacon` is on the guide **twice** (Asia Intl 169, Birite 88) and
is the only duplicated name, so a wrong-item save is not hypothetical.

---

## The spine

> **Speed is the dangerous part. Every slice before the fast one must make a wrong
> entry harder to make, easier to spot, and possible to undo.**

Two rules follow, and everything below obeys them:

1. **The app never chooses an item on your behalf.** Not on open, not on filter, not
   after a save. Picking is always something a person did.
2. **No slice ships a speed increase before the safety it depends on.** If the work
   stops after any slice, the page is strictly safer than it was — never faster-but-looser.

---

## The design change that matters

**v1's blockers B1 and B2 are both artifacts of a `<select>`.** A select holds a selection
as *state*, independently of the fields next to it. That state can drift — a filter
rebuild, a stray tap, a colleague taking the phone — while `fQty` and `fPrice` keep the
values you typed for a different item. Every mitigation v1 offered was discipline applied
on top of a widget that wants to drift.

So: **replace the select with a filtered list you tap.**

```
┌─ Order-guide item ─────────────────────────────┐
│ [ Filter…                                    ] │   16px input
│ 3 of 250 match                                 │
│ ┌────────────────────────────────────────────┐ │
│ │ Birite » Slab bacon                        │ │ ← tap = the pick
│ │ Asia Intl » Slab bacon                     │ │
│ │ ✎ Custom (not on order guide)              │ │
│ └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
        ↓ after a tap
┌────────────────────────────────────────────────┐
│ Birite » Slab bacon                 [ Change ] │   vendor always visible
└────────────────────────────────────────────────┘
```

Why this kills the bug class rather than managing it:

- **Selection becomes an event, not a state.** There is no widget holding a choice that can
  go stale. You tapped a row; that row's id is written to a variable at that instant.
- **The vendor is on the row you tap and stays on screen after.** `Slab bacon` is
  disambiguated at the moment of choosing, which is the only moment it matters.
- **Filtering cannot change your pick,** because the filter only exists before a pick. Once
  picked, the list collapses to a confirmation line with a **Change** button. Changing is
  deliberate, and per Slice 1 it clears the value fields.
- **Nothing is picked by default**, so "didn't look" produces no save at all rather than a
  save against whatever sorted first.

This is a new component — the app has none — which the review's own logic argues for: a
structural fix beats five behavioural mitigations. It reuses the row shape and type scale
`.ing-row` already establishes, so it is new CSS, not a new visual language.

---

## Slices

Seven, deliberately small, ordered so the risky capability is last. Each is reviewable in
one sitting, and each leaves the page safer than it found it.

### Slice 0 — Ground truth *(no app code)*

Nothing can be reasoned about until these are known. **Blocks everything.**

- Confirm which of the 5 `ingredient_costs` rows are real vs test. Review finding M7: row 1's
  history has `effective_date` 2026-06-15 and 2026-07-20 both created 2026-09-02 a minute
  apart, one with `source:'invoice'` — the UI cannot produce that, so it was hand-backfilled.
- Confirm whether `ingredient_costs` has a unique constraint on `(location, order_item_id)`.
  Not in the repo (`supabase/` holds only the two Edge Functions) and not exposed to the anon
  role via the REST spec. **Approved by Stephen 2026-09-17; SQL written, pending his run.**

  **It must be a _partial_ index, scoped to `active = true`.** A plain unique index would
  make Slice 2 impossible: retiring a mis-linked row would permanently block that guide item
  at the database level, which is the exact bug Slice 2 exists to remove. Verified read-only
  that no duplicates exist today, so it can be created cleanly.

  ```sql
  create unique index if not exists ingredient_costs_one_active_per_order_item
    on ingredient_costs (location, order_item_id)
    where active = true and order_item_id is not null;
  ```

**Done when:** both answers are written into this doc, and the constraint exists or has been
consciously declined.

> **CLOSED 2026-09-17.** Stephen confirmed the five rows were test numbers and cleared them.
> He ran the cleanup and the index together in the SQL editor; the confirming select returned
> `items_left 0, history_left 0, guard_installed 1`. Verified independently read-only:
> `ingredient_costs` and `ingredient_price_history` both report `content-range: */0`. The
> index result came from `pg_indexes` and is the authoritative check — DDL is not visible
> through PostgREST.
>
> A restore script for the deleted rows is at
> `~/Downloads/boxkitchen_costing_backup_2026-09-17.sql` (dollar-quoted, explicit ids,
> restores into an empty table).
>
> **The ledger is now genuinely empty, and that is the correct starting state.** Slice 1's
> builder should expect `listBody` to render the "No costed items yet" empty state; the
> picker is driven by `order_items` (254 rows) and is unaffected.

### Slice 1 — You save what you meant

No speed. Correctness of a single entry.

- Replace the select with the filtered tap-to-pick list above. **Nothing preselected.**
- Save is blocked until an item is picked (or Custom is chosen explicitly).
- The picked item stays on screen **with its vendor**.
- **Change** clears qty, unit, price and alias along with the pick — you cannot carry one
  item's numbers onto another.
- **Stop auto-filling Unit from `order_items.unit`.** It is the *order* unit (CS/EA), not
  the *pack* unit. Leave it empty; it is a required field.
- Unpriced-but-linked rows (today: *Distilled white vinegar*) **appear in the picker**, marked
  `needs price`, instead of vanishing because a row exists.
- Tapping the backdrop no longer discards typed values — confirm first.

**Done when:** no code path selects an item; saving without a pick is impossible; Change
clears the numbers; Unit is never auto-filled; the unpriced row is reachable from ＋ Add.

### Slice 2 — Mistakes can be undone

Still no speed. This exists because Slice 5 and 6 make mistakes faster to create.

- **Re-link on edit.** `pickWrap` is hidden on edit today, so a row bound to the wrong guide
  item can never be corrected. Show the picker on edit.
- **Retired rows stop blocking the picker.** `costedOrderIds()` counts them, so retiring a
  mis-linked row permanently removes that guide item from ever being added. Exclude
  `active=false` from the block set.
- **`logPrice` gets a callback.** It is fire-and-forget today, so a failed history write
  leaves a price with no trail and nobody knows.
- **Magnitude check on edit:** if a new unit cost is ≥10× or ≤1/10th the previous one,
  confirm before saving. This is where a `lb`/`CS` mix-up surfaces.

**Done when:** a mis-linked row can be corrected without retiring it; retiring frees the
guide item; a failed history write is surfaced; a 10× price change asks.

### Slice 3 — Every price has a provenance *(absorbs #140)*

The review's S1 is correct: this feature *is* invoice entry in all but name, and v1 was
wrong to push provenance to B4.2. Typing several hundred prices off paper with no record of
which paper is not auditable.

**Two modes, because the first 250 items are not invoice entry.** Stephen is bootstrapping
the ledger from the order guide — establishing pack sizes and current prices — not filing a
delivery. Forcing an invoice number on that work would make him invent one, which is worse
than recording nothing. Invoice-driven updates come afterwards, forever.

| mode | `source` | `invoice_ref` | `effective_date` |
|---|---|---|---|
| **Setting up** (default) | `manual` | none | today |
| **Working an invoice** | `invoice` | the number you set | the invoice's date |

- The mode and the current invoice live in a **sticky header, always visible** at the top of
  the modal — not set once per session. Set once and it holds; change it when you pick up the
  next invoice. One invoice means typing it once; three means changing it twice; and you can
  always see which one you are filing against.
- `effective_date` comes from the **invoice date** in invoice mode, not today. A stack of
  last month's invoices currently all record as the day they were typed.
- `logPrice` passes the real `invoice_ref` and `source` instead of `null`/`'manual'`.
- **Display `invoice_ref` in the price-history modal** — closes #140. The data is already
  there (`SR-88214`) and invisible.

**Done when:** setting-up mode records no invented invoice; invoice mode stamps every row it
saves with the number and the invoice's own date; the mode is visible without scrolling;
history shows the reference; #140 closes.

### Slice 4 — The write path cannot double-fire

Hardening before anyone is given a reason to go fast.

- Disable **every** control in flight — both save buttons and the picker — not just `#saveBtn`.
- Add a **timeout** to `api()`. There is none, and `onerror` passes `null`, so a POST that
  *succeeded* but lost its response reports "Add failed — try again". Retrying duplicates.
- **Before any retry, re-GET by `order_item_id`** and reconcile rather than blindly POSTing.

**Done when:** a save in flight cannot be triggered twice; a dropped response cannot create a
duplicate; behaviour verified against a stubbed `api()` that simulates loss and delay.

### Slice 5 — Find the item fast

The first slice that adds speed, and only now.

- **Word-by-word matching.** `render()` uses `hay.indexOf(q)`, so `birite oregano` fails to
  match `Birite Dried oregano, Mexican`. Split the query on whitespace; every token must
  appear somewhere in `vendor + name + invoice_alias`.
- **Match `invoice_alias` too.** This is the compounding win: the paper says
  `CHKN BRST BNLS 40#` and the guide says `Chicken breast`. Every alias entered makes the
  *next* invoice easier to work from. The bridge is built by using it.
- **The filter input is 16px**, not `.search`'s 15.2px. It is a new class, scoped to the
  picker — do **not** change `.search` globally, which would reach into six other pages and
  belongs to #135.
- Show `N of 250 match`, and say so plainly when nothing matches.

**Done when:** `birite oregano` finds the item; an aliased item is findable by its invoice
string; the filter input computes to ≥16px; zero matches reads as a statement, not an error.

### Slice 6 — Run the run

Everything above exists so that this is safe.

- **Save & next**: saves, keeps the modal open, clears the pick and all value fields, keeps
  the **filter text** and the **invoice header**, and returns to an unpicked state.
- A **running count inside the modal** — "12 saved this session". The header count is behind
  a 70% black backdrop and the toast lasts 1.6s, so neither is feedback during a run.
- Three buttons in `.modal-btns` at 390px: verify Save and Save & next cannot be
  thumb-mistaken for each other, and that nothing wraps.

**Done when:** a run of ten items is possible without losing the filter or the invoice
header, every one of them required an explicit pick, and the in-modal count is accurate.

---

## What is still out of scope

- **Recipe costing (B4.3), inventory (B4.4), Dropbox OCR (Phase 2).**
- **Bulk CSV import.** `~/Downloads/Tempest_ingredient_costs_DRAFT.csv` is a scraped draft
  with OCR duplicates and unconfirmed pack sizes. Pack size is the value the model hinges on
  and the one OCR gets wrong most. Parser proposes, human confirms once.
- **B4.2 as a separate module.** Slice 3 absorbs the part that cannot be separated
  (provenance). Whole-invoice entry — one invoice, many lines, totals reconciled — remains a
  later build.
- **Fixing #135 globally.** Slice 5 adds one correctly-sized input. It must not make #135
  worse, and it does not attempt to fix the other fourteen.

---

## Constraints

From `CLAUDE.md` and `docs/review-checklist.md`:

- **Class names are load-bearing.** Add names, never rename. New picker classes need a
  `used by:` banner or the guard fails.
- **No new `:root`**, no redeclared core token.
- **State is fill, weight and border — never hue.** A zero-match filter is not red. `needs
  price` is the existing yellow highlighter (`.ing-pack.unset`), not a colour of its own.
- **`--faint` is inactive/locked text only.** Live secondary text is `--grey`.
- **`python3 scripts/check_styling.py` before every PR.** CI runs it on `**.html`,
  `assets/**`, `scripts/check_styling.py`.
- **Bump `?v=` on all ten pages** iff `assets/kitchen.css` changes. Ten must agree.
- **Print:** confirm every new modal element is hidden under `@media print`.
- **The database is live and someone is entering real data into it.** Read-only GETs are
  fine. **Never write test rows.**

---

## How to verify without touching live data

Review finding m6 is correct: v1's "save a filtered pick and read the row back" would have
written to a production table mid-entry. It cannot be done that way.

- **Stub `api()`** and assert on the payload it was handed. That is the only way to test the
  save path, and the only way to simulate Slice 4's dropped responses and timeouts.
- **Render with real rows read-only**, using the headless harness from the #128 walk. Two
  traps that silently give wrong answers:
  1. `--window-size` does **not** set the layout viewport — it stays 500px and only the
     capture resizes, so a screenshot looks clipped when nothing is wrong. Simulate a phone
     with a `width:390px` wrapper and measure inside it.
  2. Keep the real viewport **under 760px**, or `@media (min-width:760px)` re-pads `.header`
     with `calc((100% - 720px)/2 + 18px)`, which computes negative against a 390px wrapper
     and clamps to zero, silently deleting the header padding.
- **Assert, don't eyeball:** `scrollWidth > clientWidth` for truncation, computed `fontSize`
  for the 16px rule, computed `borderBottomStyle` for dividers.

---

## Questions — answered 2026-09-17

1. **Slice 0's migration — YES**, approved. See the partial-index SQL in Slice 0. Pending his
   run; it is DDL, so it cannot be done with the anon key from a session.
2. **Which of the 5 rows are real — open, but narrowed.** All five were created in one sitting
   on 2026-09-02, the day the page was first tried. Row 5 is confirmed not real (below). Row
   1's three history entries were all *written* on 2026-09-02 while carrying `effective_date`
   of 2026-06-15 and 2026-07-20, one with `source:'invoice'` and `invoice_ref:'SR-88214'` —
   the UI cannot produce any of that, so that trail is invented. **Recommendation: clear the
   table and start clean**, rather than build a costing engine on four unverified prices and
   one fabricated price history. Awaiting his call; deleting is a live write.
3. **Invoice header scope — answered by redesign.** Neither "once per session" nor "per item".
   A sticky, always-visible *current invoice* with a **setting-up mode** for the bootstrap.
   See Slice 3.
4. **Off-guide items — "we don't have saffron."** Row 5 is test data and goes. It was created
   off-guide not by intent but because `✎ Custom` is the picker's default, which is the trap
   Slice 1 removes. It is evidence the trap fires in practice, on the very first sitting.
   Custom therefore stays in the list but last, and never preselected.

---

## Risks

Rewritten. v1's risk 1 is dropped — 254 short strings is not a performance problem, and
listing it crowded out the real ones.

| risk | why it matters | mitigation |
|---|---|---|
| A new picker component is new surface | It replaces a native control that worked on phones for free | Tap targets ≥44px, real scrolling inside the modal, tested at 390px before the PR. The bug class it removes is worse than the surface it adds |
| Seven slices is a long runway before any speed | Motivation dies; entry stays stalled | Slices 1–4 each ship something that makes today's entry safer. Speed is 5 and 6 and should not be reordered forward |
| Slice 3 changes what `effective_date` means | Existing rows already carry backfilled dates (M7) | Settle Slice 0's question first; don't mix real and test rows under a new rule |
| Modal grows: picker list + invoice header + 3 buttons | An 88vh modal on a phone with the keyboard up is small | Measure with the keyboard simulated; the picker list scrolls internally rather than growing the modal |
| Slice 5's 16px input diverges from `.search` | Two search-ish inputs that look slightly different | Accept it. Changing `.search` globally touches six pages and is #135's job, not this build's |
| Custom entry is de-emphasised | Legitimate off-guide items get harder to add | Question 4 settles it. Custom stays in the list, last, always reachable |

---

## Minors list

Carried from the v1 review; append as building proceeds. Do not clear it — something minor
in one slice is often a blocker in the next.

- m1. Focusing the filter from inside an XHR callback won't open the iOS keyboard (not a
  direct tap). When it does open it covers most of an 88vh modal. *(Slice 6)*
- m2. Three buttons in `.modal-btns` at 390px — check wrapping and thumb separation. *(Slice 6)*
- m3. The "(optional …)" span sets its colour inline (`:89`). Move it to a class if that area
  is touched, so `check_styling.py` can see it.
- m4. Confirm every new modal element is hidden under `@media print`.
- m5. `curV` in `openAdd()` (`:238`) is dead code — remove it while rewriting that function so
  nobody reads it as grouping that doesn't exist.
- m6. Verification must use a stubbed `api()`, never a live write. *(folded into the
  verification section above)*

---
---

# Appendix — adversarial review of v1

Preserved verbatim. This is the review that rejected the v1 plan; the document above is the
response to it. Section numbers referenced above (B1–B4, M1–M7, m1–m6, S1–S2) are its.

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
