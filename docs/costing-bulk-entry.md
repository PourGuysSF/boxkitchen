# Costing — make the ledger fillable

Status: **Slice 2 built** on `costing-slice2-undo` (PR #145) and **reviewed — one blocker
open**: the price-history recovery this document states twice does not exist (m24). All four
of the slice's promises are otherwise implemented and verified. See "Slice 2 as built"
below, m21–m25 for what it left open, and m26–m32 for round 5's findings. **Slice 1 shipped** — merged to `main` as `7d79bd6` (PR #143, squashed; branch
deleted). Four rounds of review; round 4 found no fourth async-staleness bug and passed it.
See "Slice 1 as built" below, and m18–m20 for the three majors round 4 left open. Slices 2–6
are still planned.
v2, rewritten 2026-09-16 after the v1 plan was reviewed and rejected. The review that rejected it is preserved verbatim in the
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
  3. A plain 390px wrapper does **not** hold a `position:fixed` modal — the modal positions
     against the real window, and `vh` still follows the real window too. So the modal's
     *height* (`max-height:88vh`, the picker list inside it) cannot be measured inside the
     wrapper. Measure **widths** in the wrapper; judge **height** from a screenshot taken in
     a tall window.
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

## Slice 1 as built

The picker shipped, was reviewed, and the review's blockers were fixed on the same
branch. What the fixes were, and what guards them:

| finding | fix | guarded by |
|---|---|---|
| **B2** a price logged against the wrong item | `saveItem()`'s EDIT branch captures `editId` into a local `savingId` at call time and the callback uses only that — for the `items[]` update and for `logPrice`. The ADD branch already used the POST's own returned row id. | `inflight` scenario: save-then-Cancel, save-then-open-another, and the ADD path |
| **B1** you can't tell which Slab bacon you picked | **Solved inside ＋ Add only.** `pickExisting()` passes the tapped order-guide row through to `openEdit()`, which keeps `pickWrap` visible showing vendor and name. `Change` is hidden there — re-linking is slice 2. **Unsolved from the main list:** tapping either Slab bacon row there still hides the picker area and opens "Edit item / Slab bacon" with no vendor. The fix is slice 2's "show the picker on edit"; it is deliberately not done here. | `ok` scenario, `B1:` assertions (＋ Add path only) |
| **M1** the picker usable before the ledger loaded | `ledgerLoaded` / `ledgerError` alongside the guide's. "Loaded" means **both** requests returned; a ledger failure gets the same error-with-Retry. | `ledgerslow`, `ledgerfail` scenarios |
| **M3** unit not required | `saveItem()` blocks on an empty unit the way it blocks on a missing pick. | `ok` scenario, `M3:` assertions |
| **M4** the suite didn't guard the core promise | Filtering/re-filtering/clearing picks nothing; Change clears qty, unit, price and alias; the three above. Chrome path is `$CHROME`-overridable; CI runs it (`.github/workflows/costing-guard.yml`). | itself |

Every one of those assertions was proved to bite by reintroducing the exact fault and
watching it fail — including auto-picking the sole filter match, and a `Change` that
leaves the numbers behind.

### Round 3 — one bug, found three times

The third sign-off found three more blockers, and together with round 2's B2 they are
**one bug**: an async callback touching shared state without asking whether its response is
still the current one. B2's callback re-read the shared `editId`. B-new's callback closed
whatever modal was open *now* and toasted over it. M-a's superseded load overwrote `items[]`.

So the fix is the pattern, not the instances. **Every async callback captures what it needs
at call time and checks it is still the current operation before touching shared state or
the screen.** One counter per kind of operation names "current": `loadGen` (bumped by every
`init()`), `modalGen` (bumped by `modalMoved()` whenever the edit modal stops showing what
it showed — open, close, pick, Change), `histGen` (price-history open/close). All six
callbacks on the page were audited, not only the three reported: both `init()` requests,
both save branches, Retire/Restore, and Price history. `logPrice` has no callback.

| finding | fix | guarded by |
|---|---|---|
| **B-new** a slow save closes the wrong modal and says it worked | `saveItem()` captures `modalGen`, the item's label and a key (`oi:<id>` / `ic:<id>`) at call time. On return it `closeEdit()`s **only if `modalGen` is unchanged**; otherwise it updates `items[]`, the list and an open picker silently. Toasts name the item — "✓ Slab bacon (Asia Intl) added", "⚠ Sea salt failed — try again" — so they are true whatever is on screen. Save reads **Saving…** while *this* modal's save is in flight and is live again the moment the modal moves on. A second write for an item whose first is still out is refused with "… is still saving", not sent. `toggleActive()` got the same capture-and-check. | `inflight` (b)–(e): modal state, toast text, and the second item's typed values, not just the ids written |
| **M-a** Retry races the old load and can delete a saved row | `init()` takes `gen=++loadGen`; both callbacks return early if `gen!==loadGen`, on the success and the null/error paths alike. | `retry` scenario: a stale ledger landing after a save, a stale guide failure, a stale empty guide, a stale ledger failure |
| **M-c** the suite ran with no stylesheet | `check_costing.py` copies `assets/` beside the page, so `assets/kitchen.css` resolves. The header comment now says what was wrong. | `css:` assertions — the sheet is loaded, a `.pick-row` and the chosen line are really on screen, a pick row is a 44px target, the filter computes to 16px |

The suite's fake ledger is now **stateful**: a GET answers with what existed when it was
sent, so a slow GET is genuinely stale by the time it lands. A static fixture could not have
shown M-a.

Each guard was proved to bite by reintroducing the exact fault: closing whatever modal is
open (9 failures), un-named toasts (6), a Save that is disabled with no label and stays dead
across Change (3), no load generation (8; ledger check alone removed: 5), no assets copy (3),
a CSS rule hiding `.pick-row` (2) and hiding the chosen line (3), and no in-flight guard (2).

**Landed early, for slice 5's review:** the picker filter is already its own 16px class
(`.pick-filter`, not `.search`), and the "No order-guide items match “…”" and "Every
order-guide item is already priced" messages already exist. Slice 5 owes word-by-word and
alias matching and the `N of 250 match` count; it should review these, not rebuild them.

**Not done here, on purpose:** full control locking during a save (slice 4). Save is
honest about being busy; the picker, Cancel and Change stay live.

**Test labels follow this document**, not the v1 review's numbering: `slice1:` for a
slice-1 promise, `B1`/`B2`/`M1`/`M3` for the findings above. The suite's old `M1:`/`M2:`
labels (which meant something else entirely) were renamed to `slice1:` for that reason.

Also fixed, small: `.pick-change` was 40px against the plan's own 44px minimum; the
auto-focus to Pack qty after a pick is gone (speed is not in this slice); a dead
expression in `check_costing.py` removed.

## Slice 2 as built

"Mistakes can be undone." Four fixes, one per promise, plus m20 because the magnitude
check could not be built honestly without it.

| promise | as built | guarded by |
|---|---|---|
| **Re-link on edit** | `openEdit()` no longer hides `pickWrap` on any path — the chosen line with its vendor is always on screen, and **Change** is live. `renderPick()` gains a relink mode: it lists only legal targets (a guide item held by another *active* row is excluded, because the partial unique index would reject it) and a tap re-points *this* row instead of navigating to another. `saveItem()`'s EDIT branch writes the new `order_item_id` and name. | `relink` scenario |
| **Retired rows stop blocking** | `costedOrderIds()` and `costRowFor()` both count **active rows only**, which is exactly what `ingredient_costs_one_active_per_order_item` enforces — the UI now agrees with the constraint instead of being stricter than it. Fixes m10 (a retired unpriced row showed "needs price" and tapped through into a retired item) and settles m9 (active-only makes the first match the only match). | `retired` scenario |
| **`logPrice` gets a callback** | A failed history write is surfaced as a warning toast naming the item. The ledger write is **never rolled back** — see the decision below. | `histfail` scenario |
| **Magnitude check on edit** | `magnitudeWarning()` asks before saving when the new unit cost is ≥10× or ≤1/10th the old one, **or** when the unit itself changed under an existing price. Adds never ask: there is no previous cost to compare. | `magnitude` scenario |
| **m20** | `priceChanged` now includes `pack_unit`, so a unit-only edit writes a history row — and the magnitude check can see the edit that most reliably swings unit cost 16×. | `magnitude` scenario, `m20:` assertions |

**Two decisions this slice had to make, recorded because they are judgement, not fact:**

1. **Re-linking on an edit keeps qty, unit, price and alias; it replaces only the
   name/vendor binding.** Slice 1's rule — Change clears the numbers — is right for ＋ Add,
   where the numbers were typed *for* the item being abandoned. It is wrong for the repair
   this slice exists to enable: there the price is correct and the *link* is what is broken,
   so clearing the numbers would destroy the data being rescued. `Change` therefore does two
   different things, and `changePick()` branches on `editId` to say which. The hint text on
   an edit says so out loud: "The pack size and price you see stay as they are."
2. **A failed price-history write never rolls back the ledger write.** The ledger is what
   the kitchen prices from; unwinding a correct price because its audit row failed would
   turn a bookkeeping failure into a costing failure. So the price stands, and the failure is
   said out loud — "⚠ Sea salt saved, but its price history didn't record" — rather than
   swallowed. ~~Re-saving the same price writes the missing row (m24).~~
   **That last sentence is false as built — see m24, which is an open blocker.** The
   decision itself (never roll back) survives review; only the claimed recovery does not
   exist. Do not merge this slice with the sentence standing: either make it true, or
   strike it and say there is no recovery.

**Also closed, as a side effect:** the "unsolved from the main list" half of B1. Tapping
either Slab bacon in the main list now opens an edit whose chosen line names its vendor,
because the picker is no longer hidden there.

**Not in this slice, on purpose:** speed of any kind (slices 5 and 6), invoice provenance
(slice 3), and control locking during a save — including Retire as a second write path,
m19 — which is slice 4.

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
- m7. The "(optional — how it reads on the invoice)" span still sets its colour inline
  (`tempest_costing.html:101`), so `check_styling.py` cannot see it. *(same span as m3)*
- m8. `.pick-filter:focus` in `kitchen.css` is dead — `.modal input:focus` out-specifies it
  with identical declarations. Deleting it changes nothing visually; leave it or remove it
  deliberately, but do not assume it is doing the work.
- m9. `costRowFor()` returns the first match. The partial unique index still allows one
  active plus one retired row on the same `order_item_id`, so which of the two the picker
  routes a tap to is list-order luck.
- m10. A retired unpriced row shows `needs price` in the picker and taps through into a
  retired item. Recorded, not fixed — excluding retired rows is Slice 2's
  `costedOrderIds()` change and belongs with it. *(m12 was the same finding written twice;
  merged here.)*
- m11. `pickExisting` → `openEdit` is not specified by slice 1 and partly pre-empts slice 2;
  `pickItem`'s auto-focus to `fQty` is a speed affordance, which slice 1 said it would not add.
  *(the auto-focus is now removed; `pickExisting` stays, and now keeps the chosen line — B1)*
  **Accepted deviation, and wider than it looks:** because it goes through `openEdit()`, the
  ＋ Add flow also exposes **Retire** and **Price history** for a needs-price row. Both are
  slice 2 territory. Slice 2's review should treat them as already shipped, not new.
- m12. *(merged into m10)*
- m13. If the guide GET fails but the ledger loads, every linked item lists under
  "Off-guide items", because `vendorOf()` resolves through `orderById`. The picker says so
  loudly; the list behind it does not. Recorded, not fixed.
- m14. The list redraws when the ledger arrives, and a tap at that instant can land on a
  neighbouring row. The M1 fix shrinks the window — the picker is not tappable at all until
  both requests return — but the main list behind the modal still repaints. Recorded, not
  fixed. *That shrunk window is the **load** path only; m18 is the same failure shape on the
  **save** path, where the picker is fully tappable.*
- m15. `loadGen` ignores a *superseded* load, not a *current* one that is merely old. If the
  current load's ledger GET was sent before a save and lands after it, it still replaces
  `items[]` without that row. Reaching this needs a save in flight while the ledger is still
  loading, which the picker already blocks for ＋ Add (it is untappable until both requests
  land); it is reachable only through an edit from the main list. Recorded, not fixed —
  reconciling a reload with in-flight writes is slice 4's job.
- m16. Named toasts are longer. `.toast` has no max-width and sits at `left:50%`, so at
  390px a long name wraps to two or three lines. ~~Readable, not measured on a phone.~~
  **Measured (round 4), and the guess was exact.** `.toast` is `position:fixed; left:50%`
  with no `right` and no `width`, so its available width is viewport − 50% = **195px** at
  390. "Slab bacon (Asia Intl) added" → 195×66, 2 lines; "Distilled white vinegar (Birite)
  failed — try again" → 195×88, 3 lines. At `bottom:30px` an 88px toast reaches y≈118 and
  overlaps the modal's button row, but `.toast` is `pointer-events:none`, so it never blocks
  a tap. Acceptable as shipped; a `max-width` would be the fix if slice 6's longer run makes
  it grating.
- m17. The in-flight guard keys on `order_item_id` or ledger id. A Custom add has neither,
  so Cancel-and-re-add of the same Custom name mid-save can still send two POSTs.
  Slice 4's reconciliation covers it.

### Added by round 4's review (post-merge, #143)

Round 4 found **no fourth instance of the async-staleness bug** — all six callbacks capture
at call time and check they are still current, and a held save across a Change was driven end
to end with both Slab bacons kept apart (`POST oi88 15lb $90`, `POST oi169 20lb $150`, the
second item's typed values untouched by the first item's response). These three are majors
that do not break a slice-1 promise, recorded here so slices 2 and 4 inherit them.

- m18. **The picker repaints under your thumb when a superseded save lands.** Round 3
  replaced the unconditional `closeEdit()` in `saveItem()`'s `done()` with
  `if(gen===modalGen)closeEdit();else refreshPicker()`. The `else` branch redraws a picker
  the user is looking at, with no action from them. Measured in `#inflight` — save Birite
  Slab bacon, hit **Change**, sit on the chooser, release the held POST:

  ```
  BEFORE  Asia Intl Slab bacon @y189 | Birite Slab bacon @y241
          Birite vinegar (needs price) @y293 | Custom @y345      listH=200
  AFTER   Asia Intl Slab bacon @y189 | Birite vinegar (needs price) @y241
          Custom @y293                                           listH=148
  ```

  A different item now occupies y241 and a thumb already descending lands on it. Recoverable,
  because the chosen line then shows the wrong vendor before you save — which is why it is not
  a blocker. **Slice 6 must fix it before Save & next ships**, because Save & next makes this
  repaint happen on every item of a run. Same failure shape as m14, opposite path.

- m19. **Retire is a live second write path during a save, and it is not covered by
  `savingKey`.** The "Slice 1 as built" note says only *"the picker, Cancel and Change stay
  live"* — that list is navigation and reads. Measured with a save held on row 502:
  `save="Saving…" disabled=true`, but `retireDisabled=false cancelDisabled=false
  histDisabled=false`, and two PATCHes go out on the same row —
  `{pack_price:42,…}` and `{active:false,…}`. `toggleActive()` neither reads nor sets
  `savingKey`, so the guard that refuses a double *Save* does not refuse Save-then-Retire.
  Three of the four orderings converge; in the fourth (server applies the save first, its
  response lands last) `items[i]=r[0]` overwrites the retire with `active:true` and the row
  shows active in a list whose database row is retired, until a reload. Self-healing and
  cosmetic. **Slice 4's "disable every control in flight" must include Retire and Price
  history, not just the two save buttons and the picker.**

- m20. **Editing only the Unit writes no price-history row.** `priceChanged`
  (`tempest_costing.html`, `saveItem()`'s EDIT branch) tests `pack_price` and `pack_qty` and
  not `pack_unit`. Measured: `Sea salt 2 lb @ $10` → change unit to `oz` only → Save sends
  `["PATCH ingredient_costs"]` and **0** history rows; the price-change control sends
  `["PATCH","POST ingredient_price_history"]`, 1 row; the qty-change control, 1 row. The real
  unit cost went $5.00/lb → $5.00/oz — 16× — and the trail says nothing happened.

  Pre-existing (identical on `main` before #143), so not a regression. It matters **now** for
  two reasons slice 1 created: Unit is no longer auto-filled and is required, so it is typed
  for all 250 items and corrected routinely; and **slice 2 specifies its magnitude check as
  "if a new unit cost is ≥10× or ≤1/10th the previous one" — built on `priceChanged` it would
  be blind to the single edit that most reliably produces a 16× unit-cost swing.** Fix
  `priceChanged` as part of slice 2, not after it.

Smaller, from the same review: `.pick-error` / `.pick-loading` / `.pick-retry` are emitted in
`renderPick()` but have no rule in `kitchen.css`, so a failed load computes to
`rgb(106,106,106) italic 400 13.6px` — identical to "Loading the order guide…" and to the
zero-match line; m13's "the picker says so loudly" is not true as built. The Retire `confirm()`
names no item. `openHist()` sets `histName` from `nameOf(it)`, so the price-history modal for
either Slab bacon reads just "Slab bacon" — `itemLabel()` already exists and is what the toasts
use. B1 is solved on every surface that **writes**, and unsolved on these two that **read**.

### Added by slice 2 (branch `costing-slice2-undo`)

- m21. **Re-linking a row does not move its price history.** History rows hang off the
  ledger row id, not off `order_item_id`, so after a re-link the existing trail describes
  a different guide item than the row now points at. For the mis-link repair this is
  arguably right — it is the same physical purchase, recorded before the link was
  corrected — but nothing says so, and the price-history modal gives no hint that the
  earlier rows predate the re-link. Recorded, not fixed; slice 3 is where provenance
  gets its own thinking.
- m22. **Swapping two rows' links needs a detour through Custom.** The re-link chooser
  hides any guide item already held by another *active* row, which is what the partial
  unique index requires. So correcting a straight transposition — row A on item B, row B
  on item A — means unlinking one row to Custom, re-linking the other, then coming back.
  Correct, and unexplained by the UI.
- m23. **The relink chooser's zero-state wording is written for ＋ Add.** With every other
  guide item spoken for it still reads "Every order-guide item is already priced — use
  **Custom** below". In relink mode "already priced" should be "already costed", and
  Custom means *unlink*, not *add off-guide*. Cosmetic, recorded.
- m24. **A failed price-history write has no retry affordance.** It is surfaced as a
  warning toast naming the item (slice 2's fix). ~~and the recovery is to save the same
  price again, which writes the history row.~~ Nothing in the message says that. A real
  retry belongs with slice 4's reconciliation.

  > **BLOCKER, open (round 5). The stated recovery does not exist.** Measured against a
  > stubbed `api()`, start to finish:
  >
  > ```
  > 1. save Sea salt at $11, history POST fails
  >    -> toast "Sea salt saved, but its price history didn't record"   [correct]
  >    -> ledger holds 11                                               [correct]
  > 2. history healthy again. Reopen, save the same $11 — the documented recovery:
  >    -> requests: ["PATCH ingredient_costs ..."]
  >    -> history rows written: 0        <-- recovery DOES NOT WORK
  > 3. what actually writes it: 11 -> 12 -> 11, two extra saves
  >    -> 2 history rows, one recording $12 — a price never in effect
  > ```
  >
  > Cause: `priceChanged` (`tempest_costing.html:547`) compares the form against the stored
  > row, so re-saving identical values makes all three comparisons false and the guarded
  > `logPrice` at `:563` never fires.
  >
  > This blocks rather than being a minor because slice 3 builds provenance on this trail,
  > and step 3 is what a person will actually do when told their history didn't record. It
  > writes a fabricated $12 into `ingredient_price_history` — the same class of artifact
  > v1's M7 found and that Stephen cleared the table over in Slice 0. The UI could not
  > produce a fabricated price before; now it can, and this document's own advice leads
  > there.
  >
  > Two acceptable fixes, both small: track that a history row is owed and write it on the
  > next save regardless of `priceChanged`; or strike the claim here and in decision 2 and
  > say plainly there is no recovery. The first is better.
- m25. **The magnitude check compares against the row's own previous cost, including
  across a re-link.** Re-link and re-price in one save and the question contrasts the new
  unit cost with the *old item's* — the same ledger row, but arguably not a comparable
  number. Left as is: the alternative is not asking at all on the save that changes most.

### Added by round 5's review (PR #145, slice 2, pre-merge)

Slice 2's four promises were driven end to end against a stubbed `api()` and all four work:
re-link writes the new `order_item_id` while preserving qty/unit/price/alias; the legality
guard refuses a target held by an active row and accepts one held only by a retired row;
retired rows return their guide items to ＋ Add; the magnitude gate fires on 10× and on a
unit swap; m20 is fixed; B1's main-list half is closed. No fifth async-staleness bug — the
new `logPrice` callback captures `label` and touches nothing but `showToast`, verified by
reading the warning while the screen showed a different item. Scope is clean and
`check_styling.py` passes. The one blocker is recorded under m24 above.

- m26. **Wiping a price asks nothing and records nothing.** The largest possible change to
  a price is deleting it, and it is the one edit the new gate cannot see:

  ```
  Sea salt 2 oz @ $10  ->  clear the price field  ->  Save
    confirm():      []        (no gate)
    PATCH:          pack_price: null
    history rows:   0
  ```

  `magnitudeWarning()` needs `newUC` non-null to compute a ratio and `unitSwapped` is
  false, so it returns `null`; separately `priceChanged` is true but `packPrice != null`
  is false, so no history row is written either. Pre-existing behaviour, but slice 2 is
  the slice that defines when the gate fires, and this is the gap in it. In a slice called
  "Mistakes can be undone" it is the least undoable mistake on the page. **Decide
  deliberately: gate it, log it, or accept it here.**

- m27. **The history-failure toast is six lines at 390px** — the longest string on the
  page. Measured at the true 195px containing block (see m16): *"Distilled white vinegar
  (Birite) saved, but its price history didn't record"* → **195w × 134h, ~6 lines**,
  reaching 164px up from the bottom, over the modal's button row. It shows for 1.6s and
  arrives *after* the green success toast, so on the slow network that caused the failure
  the user may see "✓ saved" and look away before the warning lands. m16 predicted a
  `max-width` would be needed "if slice 6's longer run makes it grating"; slice 2 made it
  grating early. This is the error channel for the failure the slice exists to surface.

- m28. **The unit trigger fires on cosmetic edits.** `oz` → `ozs` asks *"The unit changed
  from oz to ozs, so it is not the same measure."* Pedantically true, but
  `magnitudeWarning()`'s own comment says "a gate that always fires is a gate nobody
  reads", and every unit typo fix now gates.

- m29. **The relink chooser is the tallest state on the page.** Modal *content* height at
  a pinned 358px width (`scrollHeight`, so viewport-independent and safe from trap 3):

  | state | content height |
  |---|---|
  | main-list edit, slice 1 (`pickWrap` hidden) | 514px |
  | main-list edit, slice 2 (chosen line shown) | **640px** (+126) |
  | relink chooser open | **856px** |
  | ＋ Add chooser (pre-existing) | 802px |

  88vh of an 844px iPhone is 743px, so Cancel and Save sit below the fold whenever the
  relink chooser is open. ＋ Add was already over at 802px, so this is a worsening rather
  than a new class — but it now applies to a second surface. With the keyboard up it is m1.

- m30. **The re-link duplicate guard is correct but untested, and two concurrent re-links
  are unguarded.** Reached by hand, it behaves correctly: re-linking row 502 onto guide
  item 12 (held by active row 501) is refused with "That order-guide item is already
  costed", zero requests, row unchanged. But **no assertion in any scenario reaches
  `tempest_costing.html:539`**, and the stub's PATCH echo makes it hard to — after a
  re-link the echoed row loses `active`, so `costRowFor()` reads the target as free again.
  Separately, `costRowFor(newOiId)` reads `items[]` and an in-flight re-link is not there
  yet, while `savingKey` keys on the row id rather than the target, so two rows re-linked
  to the same target both pass. The partial unique index catches it and the save reports
  "failed — try again", so it is not corruption; slice 4's reconcile-before-retry covers
  it. Reasoned, not measured.

- m31. **Saving while sitting on the relink chooser silently keeps the old link.**
  `pickId == null` meaning "link unchanged" is the right call, but at that moment the
  screen shows a chooser and the hint reads "Tap the item this row should be linked to."
  Confirmed: `saveItem()` on the chooser with no pick sends a PATCH carrying the original
  `order_item_id`.

- m32. **The suite has no assertion that a history row was ever actually written.**
  `check_costing.py:730`/`:731` both pass if `logPrice` is **never called at all** —
  `H.reqs.length=0` is reset at `:722`, so one line would have closed it:

  ```js
  ok('S2-3: a successful history write actually happens', hist().length===1, 'saw '+hist().length);
  ```

  The injection the "stays quiet" assertion was hardened against was "a `logPrice` that
  always complains", never "a `logPrice` that never fires". **m24's blocker is a `logPrice`
  that never fires**, which is why 199 assertions and three test-backed rounds did not
  catch a claim this document states twice. Add the assertion regardless of how m24 is
  resolved.

  Also from the same audit, recorded rather than fixed:
  - The claim *"every new assertion was proved to bite"* is overstated. The 35 figure is
    credible (~37–38 would genuinely fail against the slice-1 page), but 35 plus the seven
    listed injections accounts for 42 of the 63 new assertions; roughly 19–20 are proved
    neither way. They are legitimate regression guards, not padding — but not "every".
  - Three weak assertions: `:768` cannot be false on any reachable path; `:686` asserts an
    absence that holds even in the failure state; `:717` ("the failure names the item")
    cannot distinguish `"⚠ … price history didn't record"` from `"✓ Sea salt saved"`,
    since both contain the name. Matching `/price history/i` would fix `:717`.
  - The `:728` timing fix is real and deterministic under this stub, but it encodes "the
    history response is exactly one tick behind the ledger response" implicitly. If that
    route ever gains a `defer` branch the way `/ingredient_costs` has for `inflight`, both
    `:730` and `:716` go quiet with nothing to flag it.
  - **The PATCH-echo limitation has stopped being cosmetic.** Slice 2 made `active`
    load-bearing in `costedOrderIds()` and `costRowFor()`, and the stub's echo drops it, so
    after any *edit*-save the local row has `active === undefined`. Adds are unaffected
    (the POST payload carries `active:true`). The suite therefore cannot distinguish
    "active-only filtering works" from "nothing matches at all" on any post-save state.

### A correction to "How to verify without touching live data"

Trap 3 says a `width:390px` wrapper cannot hold a `position:fixed` modal *for height*. **It
cannot hold it for width either** — inside the wrapper the modal still sizes against the real
window (measured: modal 440px, picker inner 392px), so every width measured "at 390px" that
way is really measured at 440. Trap 1 confirmed independently: `--window-size=390,844` left
`innerWidth` at 500.

The working route is arithmetic. At a 390px viewport `.modal-bg`'s `padding:16px` caps
`.modal` at **358px**, so pin `max-width:358px` and measure there. Done that way the picker is
clean at 390: modal 358, picker inner 310, `scrollWidth === clientWidth` on every row, on the
chosen line and on `.field-row` (no horizontal overflow anywhere), rows 52px/44px,
`.pick-change` 74×44 and still 74 against a 48-character name, filter computed 16px,
Cancel/Save 151×48.

Two more things the next reviewer should know:

- **`check_costing.build_page()` already appends the suite's own RUNNER at `</body>`.** A
  probe appended after it runs *alongside* the suite, which unlocks the PIN gate, opens modals
  and consumes deferred responses. Round 4's first four probe runs were contaminated this way
  and produced a convincing "the modal closes on you mid-save" result that was entirely the
  suite's own `closeEdit()`. To probe by hand, rebuild the page with the gate neutralisation
  and the XHR stub but **without** the RUNNER, and unlock the manager gate yourself.
- **The stub's PATCH response echoes the request body as the row**, so `items[i]=r[0]` loses
  every field the payload omits (`active`, `location`, `order_item_id`). Real PostgREST with
  `return=representation` returns the whole row, so the page is fine — but the suite cannot
  catch a page bug of that shape, because its own fixture has it.

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
