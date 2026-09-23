# Costing — make the ledger fillable

Status: **Slice 2 built** on `costing-slice2-undo` (PR #145), reviewed seven times.
**Round 5's blocker is fixed** — the price-history recovery this document used to claim twice
now exists (m24) — and round 6 also gated a wiped price (m26) and stopped a save on the
relink chooser from silently keeping the old link (m31). **Round 7 found no blocker and no
async bug**; it failed the round on the documentation claiming more than the code delivered,
for the third time on this feature. **Round 8 fixed the five majors it raised** — the debt
now holds the values it owes (m40), a payment in flight is not paid twice (m39), Restore
checks legality (m41), the m31 question cannot name a link it cannot resolve (m42), and m37's
declined tightening was done and its recorded reasoning corrected (m43). See "Slice 2 as
built" below, m21–m25 for what the slice left open, m26–m33 for rounds 5 and 6, m39–m46 for
round 7, and m47–m51 for what round 8 left recorded. **Slice 1 shipped** — merged to `main` as `7d79bd6` (PR #143, squashed; branch
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
| **m20** | `priceChanged` now includes `pack_unit`, so a unit-only edit **on a row that has a price on one side or the other** writes a history row — and the magnitude check can see the edit that most reliably swings unit cost 16×. **Narrowed by m43 in round 8, and that narrowing went unrecorded until round 9:** on a row that has never had a price, a unit-only edit now writes nothing, because there is no price to record. m20's own measured case (`Sea salt 2 lb @ $10` → `oz`) is unaffected. | `magnitude` scenario, six `m20:` assertions |

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
   **That sentence was false when written, and round 6 made it true rather than striking
   it. Round 7 then found the round-6 wording still wider than the code, and round 8
   narrowed it to this:** a failed history POST records, against the ledger row's id, the
   **values** it owes — `{price, qty, unit}` — and the next save of that row writes a row
   for each debt it owes, with the values *that debt* holds, clearing each entry only when a
   write of its own values really succeeds. So the missing row is written whether or not the
   price changed, **and it records the price that failed rather than the price in the form.**
   When the owed values and the current values differ, **both rows are written** — the owed
   price and the current one were each really PATCHed into the ledger and each was really in
   effect, so each is a state the item was in. When they are the same, one row is written,
   not two (m40). So the
   recovery is "save the row again" — no price needs to be altered to trigger it, and the
   $11→$12→$11 detour that used to be the only working route (and that wrote a fabricated
   $12) is gone. **The debt is held in memory only.** Close the tab or reload with one
   outstanding and it is forgotten: the price stands, the trail keeps its gap, and nothing
   says so. Persisting it was considered and declined — it would mean carrying a claim about
   a table across sessions with no cheap way to re-check it, and a genuine retry belongs with
   slice 4's reconcile-before-write.

**Round 6 added three more, from round 5's review** — all inside slice 2's own remit,
because slice 2 is the slice that defines when the save path stops and asks:

| finding | as built | guarded by |
|---|---|---|
| **m24** (blocker) | A failed history write records a debt in `historyOwed`; the next save of that row pays it regardless of `priceChanged`, and the debt clears only on a history write that really lands. In memory only — see decision 2. | `histfail`, four `m24:` assertions |
| **m26** | Clearing a price asks before saving, and records the removal as a history row with a null `pack_price`. | `magnitude`, seven `m26:` assertions |
| **m31** | Saving on an unresolved relink chooser names the link it is keeping and asks; a resolved chooser asks nothing. No link is ever guessed. | `relink`, eleven `m31:` assertions |

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
  **Cost widened by slice 2 — see m44, found in round 7.** Slice 2 put `order_item_id` into
  every edit payload, so this stale `items[]` no longer merely *loses* a row until a reload:
  a later ordinary edit now writes the stale link back to the database and undoes a re-link.
  Round 8 deliberately did **not** fix it — it is this race, not a new one, and the
  reconcile-before-write that fixes it is slice 4's. **Slice 4 must treat m15 as carrying
  that cost**, not the narrower one recorded above.
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

  > **Narrowed by m43 (round 8), recorded in round 9.** As fixed, this applies to a row with
  > a price on one side or the other. A unit-only edit on a row that has *never* had a price
  > writes no history row — deliberately, because `ingredient_price_history` records prices
  > and such a row states none, and because the ＋ Add door has always written nothing for
  > the same shape. The case measured above still records. Round 8 made this change and did
  > not say so here; that is the same documentation failure that failed round 7.

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

  > **BLOCKER, round 5 — FIXED in round 6 (option 1).** What was measured, and what it is
  > now. As found:
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
  > **Fixed with option 1.** `historyOwed[ledgerId]` is set when the history POST fails and
  > cleared only when one really lands. `saveItem()`'s EDIT branch now calls `logPrice` when
  > `priceChanged || historyOwed[savingId]`, so re-saving the same price pays the debt:
  >
  > ```
  > save $21, history fails  -> PATCH 1, history attempted 1, warning toast, debt owed
  > re-save the same $21     -> PATCH 1, history rows written 1 @ $21   [recovery works]
  > save again, unchanged    -> PATCH 1, history rows written 0         [debt is paid]
  > ```
  >
  > No fabricated price is written at any point. The debt is **in memory only** — see
  > decision 2 above for why, and for what is lost if the page is closed while one is
  > outstanding. Guarded by four `m24:` assertions in `histfail`, all proved to bite.
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

  > **Fixed (round 6): gated and logged.** `magnitudeWarning()` returns the removal question
  > before it reaches any ratio — *"Sea salt: $5.00 / lb → no price … This removes the price.
  > Recipes costed from this item lose their cost until it is set again. Remove it?"* — and
  > the history write is no longer guarded on `packPrice != null`, so the removal records
  > **a history row with a null `pack_price`**.
  >
  > A null-price row rather than a gap-plus-something-else, because the history is read as a
  > sequence of states the item has been in, and "no price" is one of those states. A gap
  > cannot be distinguished from a history write that failed — which is the very thing m24
  > exists to make visible — and anything recorded outside this table would be invisible to
  > the price-history modal and to slice 3's provenance. Guarded by seven `m26:` assertions
  > in `magnitude`, all proved to bite.

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

  > **Fixed (round 6): it says so plainly.** A `relinking` flag is true from `changePick()`
  > on an edit until the chooser is resolved (`showChosen()` clears it, as does
  > `closeEdit()`/`clearPick()`). Saving while it is true asks: *"You have not tapped an
  > item, so this row stays linked to Slab bacon (Birite). Save with the link unchanged?"* —
  > naming the link it is keeping. Answering No writes nothing and leaves the chooser up.
  > A resolved chooser asks nothing. **No link is ever guessed**, which is why this is a
  > confirm and not a silent default; Save is left reachable rather than disabled because
  > the chooser is always resolvable (the row's own item stays listed, and Custom unlinks),
  > and a dead button explains nothing. Guarded by eleven `m31:` assertions in `relink`.

- m32. **No assertion covered the RECOVERY path — the specific hole m24 slipped through.**
  *(Corrected in round 6: the original wording, "the suite never asserts a history row was
  written", was overstated. `check_costing.py:711` and `:746` both assert
  `hist().length===1`, so a written row was covered.)* What was not covered anywhere was the
  second save: the suite proved a history row is written when the price *changes*, and never
  that one is written when the documented recovery says it should be. The two assertions
  around the successful-write case (`:730`/`:731`, "stays quiet" and "still confirms
  itself") do both pass if `logPrice` is never called at all, so neither backstopped it
  either. The injection the "stays quiet" assertion was hardened against was "a `logPrice`
  that always complains", never "a `logPrice` that never fires" — and **m24's blocker is a
  `logPrice` that never fires**, which is why 199 assertions and three test-backed rounds
  did not catch a claim this document stated twice.

  Closed in round 6: `S2-3: a successful history write actually happens` plus the four
  `m24:` assertions that drive fail → re-save-unchanged → save-again. Proved to bite against
  a `logPrice` that never fires (17 failures) and against the pre-fix `priceChanged &&
  packPrice != null` guard (4).

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

### Added by round 6 (the fixes for m24, m26 and m31)

Round 6 changed only what rounds 5 flagged as a blocker or a gap in slice 2's own gate. m29
(the relink chooser at 856px, Save below an iPhone fold) is deliberately **left logged**:
＋ Add was already 802px, so it is a modal-layout problem across two surfaces and gets its
own pass. Slices 3–6 were not started.

- m33. **The history debt does not survive the page.** `historyOwed` is a plain in-memory
  map, so a reload, a closed tab or iOS dropping the page loses any outstanding debt: the
  price stands, its trail keeps a hole, and nothing on screen says a row is missing. The
  warning toast is the only notice it was ever owed, and it lasts 1.6s (m27). Deliberate —
  see decision 2 — and the durable version is slice 4's reconcile, which can ask the table
  what it actually holds instead of remembering a claim about it.
- m34. **A removal row needs its own reading, and got one.** `openHist()` rendered
  `money(x.pack_price)`, so m26's null-price row would have read **`$0.00`** — a price
  nobody ever paid, in the table that exists to say what was. It now reads `no price`. Fixed
  here because m26 is what created the row; nothing else on the page writes a null price.
- m35. **Two confirms can now stack on one save.** Save on an unresolved relink chooser
  after also clearing the price asks twice in a row — the link question, then the removal
  question. Each is correct and each is about a different thing, but two modal dialogs back
  to back is the shape people dismiss without reading. Recorded, not fixed; slice 4 owns the
  save path and is where combining them belongs.
- m37. **A pack edit on a never-priced row now writes a null-price history row.** Dropping
  the `packPrice != null` guard for m26 was scoped to removals in intent but not in code:
  any edit where `priceChanged` is true and the price is absent writes a row, so typing a
  unit onto a `needs price` row records `no price (4 gal)` in the trail. Considered
  tightening it to "a price on one side or the other", and **declined** — a removal leaves
  the stored price null, so that condition would make the m24 debt on a removal row
  unpayable forever, trading a documented recovery for a cosmetic one. The rows are honest
  (a pack size did change) and now read as `no price` rather than `$0.00` (m34). Revisit
  with slice 3, where the trail gets a reader.

  > **That reason was unsound, and round 8 did the tightening — see m43.** The claim was
  > that tightening "would make the m24 debt on a removal row unpayable forever". It would
  > not. The call site is `if(priceChanged||historyOwed[savingId])`: two independent
  > disjuncts, so narrowing the first leaves the debt entirely payable through the second.
  > A removal also still records, because `it.pack_price` is non-null on the save that
  > removes it. The trade-off described above is real for a guard on *both* halves and never
  > applied to this one. **The paragraph is left standing rather than rewritten**, because an
  > unsound argument that was believed for two rounds is worth being able to find again.
- m38. **The m31 question must not name a link that does not exist.** Caught in self-review
  before the PR: on an off-guide row `label` falls back to the typed name, so the first
  draft read *"this row stays linked to Sea salt"* about a row linked to nothing. It now
  reads *"stays off the order guide"*. Guarded, and proved to bite.
- m36. **The recovery is silent when it works.** Paying a debt writes the owed row and says
  only "saved" — the same as any other save. Someone who saw the failure toast has no
  confirmation that the trail was repaired, and someone who did not see it never learns a
  repair happened. Saying so would mean a toast about bookkeeping on an ordinary save;
  judged not worth it at this size, and it belongs with slice 3's provenance view, which is
  where the trail becomes visible at all.

### Added by round 7's review (PR #145, slice 2, pre-merge)

Slice 2's four promises were re-driven and all four still hold after round 6: re-link
preserves qty/unit/price/alias and writes the new `order_item_id`; a guide item held only by
a retired row returns to ＋ Add unbadged; a failed history write is surfaced as a named
warning; the magnitude gate fires on 10×, on 1/10th and on a unit swap, and an add never
asks. **No fourth instance of the async-staleness pattern.** `historyOwed` is the first state
on this page that outlives a save, and every read of it is either captured at call time
(`icId` in `logPrice`'s callback, `savingId` in `done()`) or is one that *must* be live —
`historyOwed[savingId]` is read in the callback on purpose, so a debt recorded while this
save was in flight is paid by it, and a debt cleared while it was in flight is not paid
twice. Both orderings were walked. The defects below are semantic, not stale reads: the debt
records *that* a row is owed and never *which*, and nothing marks a payment as in flight.

Measured with a probe page built the way "A correction to …" prescribes — the page's own
XHR stub, the gate neutralised, and **without** the suite's RUNNER appended.

- m39. **Two saves inside the debt-payment window write two identical history rows.**
  `done()` deletes `savingKey[key]` before it calls `logPrice`, and `historyOwed` is cleared
  only by the payment's *response*, so every save issued while a payment is in flight fires
  another payment. Measured, history POSTs held open:

  ```
  save $21, history fails      -> debt owed
  re-save (unchanged), held    -> 1 history POST out, historyOwed[502] STILL true,
                                  savingKey free, Save enabled
  re-save again (unchanged)    -> 2 history POSTs out
  release both                 -> 2 history rows written, both $21
  ```

  Neither price is fabricated, so this is not m24's artifact class — but it puts two rows
  in `ingredient_price_history` for one price change, on the same `effective_date`, and
  slice 3 reads that trail as a sequence of states. It is reached by the one action this
  fix tells the user to take ("save the row again"), on the slow network that caused the
  failure, and nothing says "once". `savingKey` exists for exactly this on the ledger write;
  the payment has no equivalent. Same family as m17 and m19 — a second write path with no
  in-flight guard — so slice 4 could own it, but this one was *created* by round 6.

- m40. **The debt is cleared by any successful history write, not by the owed one, so
  decision 2's claim is again wider than the code.** The doc says the next save "writes the
  missing history row **whether or not the price changed**". It writes a row for whatever the
  price is at that save. If the price has moved, the missing row is never written and the debt
  is silently dropped:

  ```
  save $21, history fails   -> 0 rows, debt owed        [$21 is live in the ledger]
  correct it to $30, saves  -> 1 row @ $30, debt CLEARED
  later unchanged save      -> 0 rows
  ```

  $21 was really in effect and really PATCHed, and its row is gone for good with no notice.
  The clause that makes the claim broad is the clause that is false, and correcting a price
  you were just told didn't record is the obvious next action. `historyOwed[id]` holds `true`;
  holding `{price,qty,unit}` and paying *that* would make the sentence true, at the cost of
  the debt describing a row rather than a row-shaped hole. **This is the third time this
  mechanism has been documented as doing more than it does** (the claimed harness, round 5's
  recovery, now this) — which is the reason round 7 fails rather than records.

- m41. **Restore is now an unguarded route to two active rows on one guide item.** Slice 2's
  promise 2 lets a guide item held only by a retired row be re-costed. Nothing then stops
  Restore on the retired row. Measured: add Birite Butter (guide 77, held only by retired
  503), then Restore 503 → `PATCH {active:true}`, **no confirm, no legality check, zero
  guard requests**, and the page holds two active rows on `order_item_id` 77 — the state
  `ingredient_costs_one_active_per_order_item` exists to forbid and that m9 assumes is
  impossible. Against the live table the index rejects it and `toggleActive()` says
  *"Butter (Birite) — update failed, try again"*, which will never succeed. Before slice 2
  this was unreachable, because retiring blocked the guide item from ＋ Add. The check it
  needs is `costRowFor(it.order_item_id)` on the restore branch, saying which active row
  holds it. Distinct from m19, which is about locking Retire during a save, not legality.

- m42. **m31's question can still be confidently wrong about what it is keeping.** m38 fixed
  the `order_item_id == null` half. The other half is a row linked to a guide item that
  `orderById` cannot resolve — an order-guide item deactivated while a ledger row still
  points at it, which `init()`'s `active=eq.true` guarantees, or any time `guideError` is
  set, when it applies to every linked row at once. Measured on a row linked to a guide id
  absent from the guide:

  ```
  chosen line   : "Off-guide items"  /  "Old ketchup"
  m31 question  : "…so this row stays linked to Old ketchup."
  ```

  The two contradict each other on the same screen, and the question names a link with no
  vendor — the m38 shape from a different cause. The relink chooser cannot list the row's own
  current item either, so the code comment "the row's own current item stays listed, so you
  can change your mind back" is false here; with `fName` disabled the only exits are
  re-linking elsewhere or Custom. Guarding on `newO` (the resolved guide row) rather than on
  `newOiId != null` is the same one-line shape m38 used.

- m43. **m37's recorded reason for declining the tightening is unsound, and a correct
  tightening exists.** m37 says tightening the history guard to "a price on one side or the
  other" was declined because it "would make the m24 debt on a removal row unpayable
  forever". It would not: the call site is `if(priceChanged||historyOwed[savingId])`, two
  independent disjuncts, and tightening only the first —
  `(priceChanged&&(it.pack_price!=null||packPrice!=null))||historyOwed[savingId]` — leaves
  the debt fully payable while dropping the spurious rows. A removal still records, because
  `it.pack_price` is non-null on the save that removes it. Measured cost of not doing it: a
  pack edit on `needs price` row 501 writes
  `{pack_price:null,pack_qty:4,pack_unit:"gal"}` with no gate, while **the identical shape
  through ＋ Add writes nothing** (`done()`'s add branch still guards on `packPrice!=null`),
  so the same user action records or doesn't depending on which door it came through. The
  trade-off m37 describes is real for a guard on *both* halves and does not apply to this
  one.

- m44. **Slice 2 put `order_item_id` into every edit payload, so m15's stale `items[]` can
  now write a link back to the database.** Pre-slice-2 the EDIT payload carried no
  `order_item_id`, so an edit could not touch the link. Measured, driving m15 exactly (a
  ledger GET sent before a re-link, landing after it, `loadGen` current so it is allowed
  to write):

  ```
  re-link 502 -> guide 88, saved        items[502].order_item_id = 88
  the older ledger GET lands            items[502].order_item_id = null   (m15)
  ordinary edit, price only, Save       PATCH order_item_id: null   <- the re-link is undone
  ```

  Not a fourth staleness bug — it is m15's logged race with a wider consequence, and it is
  visible before you commit it (the chosen line reads "Off-guide items / Sea salt", m18's
  kind of recoverable). But m15's recorded cost was "the saved row vanishes from `items[]`
  until a reload"; it is now "a later ordinary edit writes a stale link". Slice 4 owns the
  reconcile; m15 should carry the new cost.

- m45. **A null-price history row reads `no price (2 lb → )`.** m34 says such a row "now
  reads `no price`" — the price does, but `openHist()` still emits the pack parenthetical
  whenever `pack_qty` is truthy, and `uc` is `''` when the price is null, so the row ends in
  an arrow pointing at nothing. Measured at the real 358px a 390px viewport gives `.modal`:
  `no price (2 lb → )manual2026-09-23`, 35px tall, `scrollWidth === clientWidth` — no
  overflow, purely a reading defect, and it is m26's own primary row (a removal keeps its
  qty). Suppressing the `→ uc` half when `uc` is empty is the fix.

- m46. **`m24: no fabricated price was needed to get there` cannot fail when nothing is
  written.** It is `hist().every(…)`, and `[].every()` is `true`, so under the pre-fix guard
  — the exact fault it sits next to — it passes vacuously. Confirmed: that injection
  produces 4 failures and this is not one of them. Joins m32's three weak assertions; a
  length check alongside it would fix it.

**On the test claims.** The split is honest where it can be checked. The headline injection
was re-run: restoring the pre-fix `priceChanged && packPrice != null` guard gives **exactly
4 failures of 231** — `m24: re-saving an unchanged price writes the OWED history row`,
`m24: the owed row carries the price actually in effect`, `m26: removing a price is recorded
in the history`, `m26: the history row records it as no price` — matching the commit's
"the pre-fix priceChanged guard (4 fail)". The +29 / +3 assertion counts in the two round-6
commits are exact. Two bookkeeping slips, neither an overstatement: the commit names groups
covering 9 of the 11 assertions it calls unproven (the two unnamed are in the m24 block), and
`4d736ba` says it added "two m31: assertions" where the diff adds three (the third is the
`the off-guide row really is off-guide` precondition).

### Added by round 8 (the fixes for m39–m43, m45 and m46)

Round 8 fixed the five majors round 7 raised and rode along with its two smaller items.
Round 7 found **no blocker and no fourth async bug**, and `historyOwed` was examined
specifically and cleared — the architecture was never the problem. What failed three times
running was that this document claimed more than the code delivered (a harness that did not
exist, m24's recovery that did not work, m40's "whether or not the price changed" that was
true only narrowly). So the entries below say what the code does and stop there.

**Scope:** `tempest_costing.html` and `scripts/check_costing.py` only. `assets/kitchen.css`
is untouched, so no `?v=` bump. m44, m29 and control locking (m19) were deliberately not
touched; m15 now carries m44's widened cost.

| finding | as built | guarded by |
|---|---|---|
| **m40** | `historyOwed[id]` holds a **list of `{price,qty,unit}`**, not `true`. Each debt is paid with its own values and cleared only by a write of those values. Owed ≠ current → **both rows written**; owed = current → one row. | ten `m40:` assertions in `histfail` (round 9 added two) |
| **m39** | `historyPaying[id]` counts payment POSTs in flight. While one is out, the debt is not paid again; a genuine `priceChanged` still writes, because that is a new row, not a copy. | six `m39:` assertions in `histfail` |
| **m41** | `toggleActive()`'s **restore** branch checks `costRowFor(it.order_item_id)` before sending. An illegal restore sends nothing and names the row in the way. | nine `m41:` assertions in `retired` |
| **m42** | The m31 question guards on **`newO`**, the resolved guide row, not on `newOiId != null`. An unresolvable link is described as one, not named. | seven `m42:` assertions in `relink` |
| **m43** | `priceChanged` is `&&(it.pack_price!=null||packPrice!=null)`. The debt disjunct is untouched, so the m24 recovery is unaffected. Both doors now agree: a pack edit on a never-priced row writes no history row through **either** ＋ Add or edit. | nine `m43:` assertions in `histfail` (round 9 added six) |
| **m45** | `openHist()` emits `→ uc` only when `uc` is non-empty. A null-price row reads `no price (2 lb)`. | four `m45:` assertions in `histfail` |
| **m46** | Given something to assert: `hist().length>0 &&` alongside the `every()`. | itself |

**What m40 decides, exactly.** When the owed values and the current values differ, **both
rows are written** — the owed one first, then the save's own. Not "only the owed one",
because the current price is in the ledger now and a trail that omits it is a trail that
disagrees with the ledger. Not "only the current one", because that is the bug. Both prices
really were PATCHed and really were in effect, so neither row is fabricated. Measured:
`$21.50` fails → correct to `$30` → **two rows, `21.5` and `30`**, and a later unchanged save
writes none.

**One pre-existing assertion changed meaning**, which is worth naming rather than burying:
`S2-3: a successful history write actually happens` asserted `hist().length===1`. In that
scenario a `$14` save had already failed its history write, so the following `$15` save now
pays the `$14` debt as well — two rows, not one. The assertion was corrected to `===2` and
an `m40:` assertion added next to it checking the pair is `14,15`. This is the fix becoming
visible in an older test, not a regression.

#### What was proved, and what was not

**268 assertions, 12 scenarios, clean.** Up from 231, so **+37**. Each of the five majors and
both ride-alongs was proved to bite by reintroducing the exact fault:

| fault reintroduced | failures |
|---|---|
| m40 — debt holds `true` again, any write clears it | **6** |
| m39 — the payment-in-flight gate removed | **2** |
| m41 — the restore legality check removed | **5** |
| m42 — the question guards on `newOiId != null` again | **3** |
| m43 — the untightened m26 guard restored | **1** |
| m45 — the unconditional arrow restored | **1** |
| m46 — see below | **0 alone** |

**m46 could not be proved by its own fault, and needed a second one.** Its defect is
*vacuity*, which only shows when nothing is written at all — so restoring the bare
`every()` on the fixed page changes nothing (0 failures). Proved by pairing it with the
pre-fix m24 gate (`priceChanged && packPrice != null`, the fault it sits beside): **14
failures with the length check, 13 without**, and the named assertion flips from failing to
passing. That is the proof, and it is a two-fault proof, not a one-fault one.

**The honest split: of the 37 new assertions, 15 are proved to bite and 22 are not proved
either way.** Two *pre-existing* assertions were also strengthened and both were proved:
`S2-3: a successful history write actually happens` (by the m40 fault) and `m24: no
fabricated price was needed to get there` (by the paired fault above).

The 15 proved are the four failure lists in the table, minus the pre-existing assertion they
include: `m40: and it pays the owed row as well as its own`, `m40: correcting a price does
not discard the failed one`, `m40: exactly two rows, one per price that was in effect`,
`m39: a save inside the payment window does not pay the debt twice`, `m39: one owed row, not
two identical ones`, `m41: an illegal restore sends nothing`, `m41: the row stays retired`,
`m41: it says why rather than "try again"`, `m41: and it names the row in the way`,
`m41: it reads as a refusal, not a success`,
`m42: it does not claim a link to the typed name`, `m42: it says the link cannot be shown`,
`m42: it does not contradict the chosen line`, `m43: and writes NO null-price history row`,
and `m45: and no arrow pointing at nothing`.

**The 22 not proved either way**, named rather than counted: `m42: the injected row really is
linked but unresolvable`, `m42: it still asks before keeping an unresolved link`, `m42: nor
does it claim the row is off the order guide`, `m42: answering No writes nothing`, `m41: the
retired row still points at the taken guide item`, `m41: and that guide item is held by an
ACTIVE row now`, `m41: a legal restore still goes through`, `m41: and confirms itself`, `m40: the failing save left a debt owed`, `m40: and the
failed price is live in the ledger`, `m40: and the corrected price is recorded too`, `m40: no
price that was never in effect`, `m40: both debts are paid, so an unchanged save writes
nothing`, `m39: the debt is owed before the window opens`, `m39: the payment is in flight`,
`m39: and Save is live again, so a second save is reachable`, `m39: and it records the price
that was owed`, `m43: a pack edit on a never-priced row writes the ledger row`, `m43:
removing a real price still records a null-price row`, `m45: the null-price row still reads
"no price"`, `m45: but it keeps its pack size`, and `m45: a priced row still shows its unit
cost`.

Most are preconditions or control cases — `m41: a legal restore still goes through` exists to
show the new guard does not refuse a legal one, and the m43 and m45 pairs exist to show the
tightening did not swing too far. They are legitimate regression guards, and they are not proved. Not "every".

One weak assertion was found while doing this and **fixed rather than logged**: `m41: and it
names the row in the way` first read `toast().indexOf('Butter')>-1`, which a success toast
("Butter restored") satisfies too — m32's `:717` defect exactly. It now matches
`“Butter” already costs`, and that is what took the m41 injection from 4 failures to 5.

#### Recorded, not fixed

- m47. **m42 fixed the question, not the chooser.** Round 7 noted two things about an
  unresolvable link: the question named it wrongly, and the relink chooser cannot list the
  row's own current item, so the code comment "the row's own current item stays listed, so
  you can change your mind back" is false in that case. **Only the question was fixed.** On
  such a row the exits are still re-linking elsewhere or Custom — there is no way back to
  the link it has. Reachable whenever `guideError` is set, which is every linked row at
  once. Listing an item the guide did not return means inventing a row for it, which is
  slice 3's provenance thinking, not a one-liner.
- m48. **Two rows from one save share an `effective_date`.** `logPrice` sends no
  `effective_date`, so the column defaults to today. When m40 writes the owed row and the
  current row together, both carry today's date and the trail cannot order them — the owed
  price came first in reality and nothing in the row says so. Slice 3 both reads this trail
  as a sequence and is where `effective_date` stops meaning "the day it was typed", so it
  owns the fix. Same shape as m39's duplicate, without the duplication.
- m49. **The debt is now a list, so m33 loses more.** m33 said a reload forgets the debt; it
  now forgets a *list* of owed rows, and a row can accumulate several across a bad stretch
  of network. Nothing shows how many are outstanding. Unchanged in kind, larger in degree;
  slice 4's reconcile is still the durable answer.
- m50. **A save skipped by m39's gate is not retried.** While a payment is in flight the
  debt is left alone. If that payment then fails, the debt is re-recorded and the *next*
  save pays it — so a user who saved twice inside the window must save a third time. Correct
  (no duplicate row is written, and the debt is never lost) but one save longer than it
  looks, and m36 already notes the recovery says nothing when it works.
- m51. **m41's refusal names a row whose name is usually identical.** Two ledger rows on one
  guide item generally carry the same `name`, so *"“Butter” already costs that order-guide
  item"* is true but does not distinguish them. The `invoice_alias` or the id would, and
  neither reads well in a toast. Accepted at this size.

### Added by round 9's review (PR #145, slice 2, pre-merge)

Round 9 reviewed round 8's own five fixes. **No blocker.** The five majors hold: the debt is
keyed on the values it owes and a write of a different price cannot discharge it; a payment in
flight is not paid twice; Restore checks legality before sending; the m31 question no longer
names a link it cannot resolve; the tightened guard leaves the debt payable. Two defects were
found in round 8's work, one of them the same documentation failure that failed round 7, and
both are fixed here. One new gap is measured and **left logged**, because fixing it is the
control locking that slice 4 owns.

- m52. **The m41 legality check does not survive a concurrent restore.** It reads `items[]`,
  and an in-flight restore is not reflected there until its own response lands. Measured with
  `ingredient_costs` PATCHes held open, two retired rows on guide item 77 and no active
  holder:

  ```
  restore 503, held   -> PATCH id=eq.503 {active:true}   (guard passes: no active holder)
  restore 506         -> PATCH id=eq.506 {active:true}   (guard passes: items[] unchanged)
                      -> 2 PATCHes out on one order_item_id
  ```

  The partial unique index rejects the second, so this is not corruption — but the user gets
  *"update failed, try again"*, which is the exact message m41 exists to remove. So **m41
  removes the common path to that message and leaves a concurrent one.** Reaching it needs a
  restore in flight while a second retired row on the same guide item is opened, which means
  Cancel-and-reopen on a slow network. Exactly m30's shape (two concurrent re-links) and
  m17's, and `toggleActive()` still has no `savingKey` at all, which is m19. **Not fixed
  here: an in-flight guard on Retire/Restore is control locking, and slice 4 owns it.**
  Slice 4 should treat m19, m30 and m52 as one piece of work.

  *Reproduction, for whoever does fix it:* add a `deferWrites` flag to the suite's stub,
  checked alongside `SCEN==='inflight'` in the PATCH route. Round 9 built it, measured with
  it, and removed it again rather than leave an assertion that expects the bug — a green
  suite must not imply a correctness the page does not have.

- m53. **`sameVals` collided a null qty with a qty of 0, so a debt could be paid by values it
  did not owe.** `num(null)` is `0`, and round 8 compared null-ness on `price` but not on
  `qty`. Measured: a debt owed at *no qty* was discharged by a save of qty `0`, which wrote
  `pack_qty: 0` and dropped the owed row. This is **m40's own defect in miniature** — the
  whole point of keying the debt on values is that a write of different values cannot
  discharge it — in the code that fixed m40. **Fixed:** `sameVals` now compares null-ness on
  `qty` as well as on `price`. Guarded by two `m40:` assertions, proved to bite.

- **m20's recorded promise was narrowed by m43 and round 8 did not say so.** Not a new
  number, because it is m20. The slice-2 table said, unqualified, *"a unit-only edit writes a
  history row"*. After m43's tightening that is true only for a row with a price on one side
  or the other; on a never-priced row a unit-only edit now writes nothing. Measured: row 501
  (never priced), unit `gal` → `qt`, **1 PATCH, 0 history rows**, while the same edit on a
  priced row still writes one. **The behaviour is right** — `ingredient_price_history` records
  prices, such a row states none, and ＋ Add has always written nothing for the same shape —
  **so the doc is what was wrong**, corrected in both places above. Low consequence, and
  recorded as a finding anyway because this is the **fourth** round in a row on which a claim
  in this document turned out wider than the code. Consequence is not the reason it matters.

**m37's unsound argument is now measured, not merely argued.** Round 8 asserted in prose that
tightening `priceChanged` leaves the m24 debt on a removal row payable, and shipped no test of
the exact scenario m37 said would break. Round 9 drove it: a removal whose history write fails
records a debt at `{price:null, qty, unit}`, and the next unchanged save pays it — **1 history
row, `pack_price: null`** — after which it goes quiet. Six `m43:` assertions, and they fail
(`saw 0`) against the injection that makes m37's claim true. **This is the one place round 8
argued where it should have measured**, and it happened to be right.

#### What was proved, and what was not

**280 assertions, 12 scenarios, clean.** Both earlier counts were re-verified by running the
suite at those commits: **231** at `4d736ba` and **268** at `a49853c`. So round 9 adds
**12**. Faults reintroduced:

| fault reintroduced | failures |
|---|---|
| m53 — the null/0 qty collision restored | **1** |
| m43's tightening removed | **2** |
| the debt disjunct removed (which makes m37's claim true) | **14** |
| `pack_unit` dropped from `priceChanged` again | **3** |

**Of the 12 new assertions, 4 are proved to bite**: `m43: the debt on a removal row IS
payable`, `m20: a unit-only edit on a NEVER-PRICED row writes NO history row`, `m20: a
unit-only edit on a PRICED row still writes one`, and `m40: a null-qty debt is NOT discharged
by a qty-0 write`. **The other 8 are not**: `m43: a failed removal attempted a history row`,
`m43: and it failed, leaving a debt`, `m43: the ledger price really is gone`, `m43: and it
pays it as a null price`, `m43: and once a removal debt is paid it goes quiet`, `m20:
(precondition) the never-priced row is not already on qt`, `m20: (control) the ledger row
still took the edit`, and `m40: a debt can be recorded with a null qty`. Preconditions,
control cases and the setup steps of the two new sequences. Not "every".

Two of the four injections also tripped **round 8's** assertions rather than round 9's — the
`no-debt-disjunct` fault produced 14 failures across the `m24:`, `m39:`, `m40:` and `m43:`
blocks. Those are round 8's guards doing their job, not round 9's, and are not counted above.

**One assertion round 9 wrote was vacuous, and round 9 caught it rather than shipping it.**
`m20: a unit-only edit on a NEVER-PRICED row writes NO history row` first set the unit to
`gal` — which the `m43:` block above had already left it on, so nothing changed and the
assertion could not fail under any injection. It now sets `qt` and carries a precondition
asserting the row is not already on it. That is the m46 class, written fresh in the round that
fixed m46; it is worth knowing the shape is easy to reproduce by accident.

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
