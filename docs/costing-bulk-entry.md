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
