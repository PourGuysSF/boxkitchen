# Staff reordering (manager mode)

**Status:** built, reviewed, drag confirmed on the kitchen tablet by the owner (§7e).
**Not deployed** — awaiting approval (Slice 6). Branch `staff-edit-and-reorder`, PR #93.

Read §7a–§7e for what was actually built and tested, and §8 for what is still open. Anything
in §1–§6 is the *plan*; where the plan and §7 disagree, §7 is what exists.
**Feature name:** `staff-edit-and-reorder`
**Scope:** reordering ONLY. Renaming is deferred — see §6.
**Goal tags:** [Consistency]
**Effort:** S–M (one column + one UI change on prep/line + a query-string change on 5 more files)

---

## 1. Goal

In manager mode, drag staff into the order you want, and have that order drive every staff
**dropdown** across the site — "Who", "Assign", "Counted by", "Posted by" — instead of the
current hardcoded alphabetical sort.

"Dropdown" is the exact scope. Two staff-name fields are free-text boxes and are deliberately
out of it: "Entered by" on flash (`tempest_flash.html`) and the "Who's resolving this note?"
prompt on notes. They never read the `staff` table, so they inherit no ordering, and by owner
decision they stay typed boxes (§9 N1).

Manager-mode-only, consistent with the locked decision in `BUILD_PLAN.md`
("reordering is manager-mode only; staff can never reorder").

---

## 2. What the code does today

The `staff` table is read in **seven** places, every one with the same query:

```
GET staff?location=eq.Tempest&active=eq.true&order=name.asc
```

| File | What it uses staff for |
|---|---|
| `tempest_prep.html` | Staff bar (manager), "Who" dropdown per task, station-assign dropdown, View-as filter, note modal |
| `tempest_line.html` | Same as prep (near-identical file) |
| `tempest_meat.html` | "Counted by" dropdown (`fillStaff()`) |
| `tempest_portion.html` | "Counted by" dropdown (`fillStaff()`) |
| `tempest_notes.html` | "Posted by" dropdown (`loadStaff()`) |
| `tempest_orders.html` | Note-modal "posted by" dropdown |
| note modals on prep/line/orders | same list again (`loadStaff()` copies) |

Two facts that shape the plan:

**A. There is no `sort_order` on `staff`.** Order comes only from `order=name.asc` in the
query string. Adding the column is the whole backend of this feature.

**B. "Both Shifts" creates TWO rows.** `saveStaff()` with `BOTH` POSTs one row with
`shift:'AM'` and a second with `shift:'PM'` — same name, two ids. That is *good* here:
because they're separate rows, **AM and PM get independent orders for free**, which is
almost certainly what you want (the AM lineup isn't the PM lineup).

`getStaffForShift()` already filters by the active shift and preserves array order, so once
the query returns rows in the right order, the "Who" and station-assign dropdowns inherit it
with no further change.

One exception: `buildViewAs()` (prep/line) explicitly re-sorts the names alphabetically
after loading. That sort has to be removed or the View-as filter will disagree with
everything else on the same page.

---

## 3. Decisions

### D1. How is order stored? — **`staff.sort_order`, integer, seeded in gaps of ten**

Same pattern already proven on `prep_items`, `order_items`, and `order_categories`. Gaps of
ten (10, 20, 30…) so rows always have room to slide between — the same SQL-first prep A7 used.

Ordering is per row, so per `(location, shift)`. AM and PM ordered independently.

### D2. Where does reordering live? — **the existing manager staff bar, drag-to-reorder**

The staff bar on prep/line already renders one chip per person in manager mode with an ✕.
Add a drag grip to each chip and make the chip row a SortableJS list — the same
`initSortables()` / `persistOrder()` pattern already ported to prep, line, and orders in A7.
No new screen, no new mental model.

**Fallback:** if dragging small chips on a phone proves fiddly in real testing, fall back to
▲▼ arrows on each chip in manager mode. Decide by feel on a kitchen tablet, not in advance.
(`BUILD_PLAN.md` already sanctions arrows as the fallback where drag isn't safe.)

### D3. Which pages get the drag UI? — **prep + line only**

The other five are read-only consumers: they just get the query string changed so their
dropdowns list people in the chosen order.

---

## 4. Build sequence

House playbook: SQL first, verify, then one page, then propagate.

### Step 1 — SQL (read-only check, then migrate)

1. **Read-only first:** dump the current `staff` rows for Tempest (`id, name, shift, active,
   sort_order?`) to confirm the row set, the AM/PM duplication, and whether the column
   somehow already exists.
2. `ALTER TABLE staff ADD COLUMN sort_order integer;`
3. Backfill in gaps of ten per `(location, shift)`, in the **current alphabetical order** —
   so the first deploy visibly changes nothing. You then drag from a known-good baseline.
4. **Confirm RLS on `staff` allows UPDATE from the anon role.** This is a real gate, not a
   formality — the notes-delete bug was exactly a missing RLS policy that made the write
   silently no-op while the UI claimed success. If there's no UPDATE policy, dragging will
   look like it worked and persist nothing.

### Step 2 — `tempest_prep.html` only

- Staff GET becomes `order=sort_order.asc,name.asc` (the `name.asc` tiebreak keeps it sane
  if any row's `sort_order` is null).
- Drag grip on each staff chip, manager mode only; chip row becomes a SortableJS list.
- On drop: renumber the visible chips 10/20/30… and PATCH each changed row's `sort_order`.
  Self-healing renumber like `persistOrder()` already does, so legacy nulls fix themselves.
- Only reorder **within the current shift** — the bar only shows one shift at a time, so this
  is natural, but the persist step must not touch the other shift's rows.
- **Verify the PATCH actually landed before toasting success** — same lesson as the Recipes
  delete fix (#89). Don't assume the write worked.
- **Remove the alphabetical re-sort in `buildViewAs()`** so the View-as filter matches.

### Step 3 — Propagate

Port the drag to `tempest_line.html` (near-identical file — cheapest port), then change the
staff query to `order=sort_order.asc,name.asc` in `tempest_meat.html`,
`tempest_portion.html`, `tempest_notes.html`, `tempest_orders.html`, and the note-modal
`loadStaff()` copies on prep/line/orders.

Per CLAUDE.md there is no shared JS — every one is a separate hand-edit. Finish with the
**whitelist** check, not a blacklist one — grepping for the *old* string proves a page was
touched, not that it was touched correctly (that is exactly how B1 slipped through):

```
grep -rn "'staff','location" *.html
```

Expect **ten** lines, every one carrying the single approved order string
`order=shift.asc,sort_order.asc.nullslast,name.asc`. Anything else is a bug.

The count is ten, not eight: `refetchStaff()` (Slice 2, §7c) added one more copy of the query
in *each* of prep and line, taking the original eight to ten. If you change how many staff
queries exist, update this number in the same commit — a check that always fails is a check
that gets ignored.

---

## 5. Test checklist (real device, before deploy)

- Drag to reorder in manager mode → reload the page → order persists.
- Switch AM ⇄ PM → each shift keeps its own order; reordering one doesn't disturb the other.
- The per-task "Who" dropdown and the station-assign dropdown list people in the new order.
- The View-as filter lists people in the same order (not alphabetical).
- Reload `tempest_meat.html` / `tempest_portion.html` / `tempest_notes.html` → "Counted by"
  and "Posted by" match the new order.
- Non-manager view → no grip, no reordering possible.
- Retire (✕) and Add still work, unchanged.
- A newly added staff member lands at the end of the list, not the top.

---

## 6. Deferred: renaming

Dropped from this build by decision — there is currently one misspelled name, and it isn't
worth the surface area.

**Why renaming is the expensive half:** staff names are stored as plain **text** on every
record, not as a link to the employee — `prep_logs.assigned_to`, `meat_counts.counted_by`,
`portion_counts.counted_by`, `orders.submitted_by`, `notes.posted_by`, `notes.resolved_by`,
`flash_days.entered_by`, plus the View-as value in `localStorage`. A rename in the `staff`
table alone orphans every past assignment, and the person's existing tasks would show a
blank "Who".

Two of those seven are **typed by hand, not picked from a dropdown**, and stay that way by
decision (§9 N1): `notes.resolved_by` (a `prompt()`) and `flash_days.entered_by` (a text
input). They can hold spelling variants the `staff` table has never seen, so an exact-match
rename will silently skip them — list their distinct values first.

**The cheap fix for the one typo:** a one-off SQL `UPDATE` that changes the name in `staff`
(both the AM and PM row) **and** the seven columns above, in a single migration. Minutes,
not a feature. Worth doing on its own whenever you want it — it does not need this build.

**The real fix, long-term:** a `staff_id` foreign key on the five dropdown-fed columns
instead of text (the two hand-typed ones can't have one — see above).
That's a large migration on a live site. Logged as debt, not scheduled.

---

## 7. What was actually built (2026-08-19)

DB migration run by the owner: `staff.sort_order` added, backfilled 10/20/30… per
`(location, shift)` in the old alphabetical order.

**RLS:** `staff` has SELECT, INSERT and UPDATE policies open to `public`. That is what makes
the browser writes persist, so the feature needs it — but it is not a safety check that came
back clean. The anon key sits in plain text in all six of these HTML files, so `staff`
accepts UPDATE from anyone who opens dev tools. The locked decision "staff can never reorder"
is enforced by a hidden div and a localStorage PIN: a UX gate, not a security control.
Consistent with the rest of the site and not a reason to stop — just not evidence of safety.

**`tempest_prep.html` / `tempest_line.html`** — staff chips are a SortableJS list in manager
mode (`filter:'.remove'` so ✕ stays a click; `delay:120, delayOnTouchOnly:true` to stop
accidental drags while scrolling). `persistStaffOrder()` renumbers the current shift 10/20/30…,
PATCHes only changed rows, verifies each write returned a row, and rolls back with an error
toast if any fails. New staff land at the end of their shift (`nextOrder()`), not wherever the
name sorts. `buildViewAs()` no longer sorts alphabetically — it lists the current shift in the
chosen order, then anyone who only works the other shift.

**`tempest_meat.html` / `tempest_portion.html` / `tempest_notes.html` / `tempest_orders.html`**
— staff query now `order=shift.asc,sort_order.asc,name.asc`. The extra `shift.asc` matters:
these pages have no AM/PM concept, and the two shifts' `sort_order` values are independent
(AM 10 and PM 10 both exist), so without it the two shifts interleave. Meat and portion also
gained name de-duplication in `fillStaff()` — they had been listing anyone on both shifts twice
(pre-existing bug, visible before this change too).

### Local test results
Sortable's own drag gesture can't be synthesised in the automation harness, so `onEnd`'s
handler was driven directly against a reordered DOM. Verified: minimal PATCH set (3 rows for a
front-of-list move, not all 9); the other shift untouched; Who / station-assign / View-as all
follow the new order; a failed save rolls back cleanly and shows "Could not save staff order";
the ✕ still fires `removeStaff`. No console errors. **The real drag gesture is still untested —
it needs a human on a device.**

---

## 7b. Slice 1 — one ordering rule for every staff dropdown (2026-08-19)

Closes **B1**, **B2**, **N2** (query half).

All staff queries in the repo are now one identical string
(**eight** at the time of this slice; ten after Slice 2 added `refetchStaff()` — see M2.1):
`order=shift.asc,sort_order.asc.nullslast,name.asc`.

- The two half-fixed note modals (`tempest_prep.html`, `tempest_line.html`) gained
  `shift.asc`, so AM/PM no longer interleave in the "Posted by" list. All three note-modal
  `loadStaff()` bodies — prep, line, orders — are now byte-identical.
- The prep/line main loads gained `shift.asc` too. They did not need it
  (`getStaffForShift()` re-filters), but one string across all eight is what makes the
  whitelist check above meaningful.
- `.nullslast` states the NULL behaviour instead of inheriting it. It matches the `1e9`
  sentinel in `sortStaff()` — that agreement used to be accidental (N2) and is now written
  into the query. The column itself still has no `DEFAULT` and no `NOT NULL`; that half of
  N2 is unclosed and lives in the DB, not here.

**Verified against the live API**, not just by reading: the new order string returns
HTTP 200 with the AM block first, each block in `sort_order`. This mattered — PostgREST
answers an unknown/invalid order clause with a 400, which `api()` swallows into `staff=[]`
and would empty every staff dropdown on the site at once (R4).

Not deployed.

## 7c. Slice 2 — a failed save now tells the truth (2026-08-19)

Closes **B4**, **B5**, **N3**.

**Shape: the local snapshot is gone.** `persistStaffOrder()` used to restore `staff[]` from a
pre-drag snapshot when a PATCH failed. That was wrong in principle — the PATCHes are separate
requests, so by the time one fails the others may already be committed, and no local snapshot
can describe a half-written database. On *any* failure the code now calls a new
`refetchStaff(msg)`, which re-GETs the staff list with the canonical query and re-renders from
the server. The screen then shows what a reload would show, which is the only claim worth
making.

One change closes three findings: the partial write stops being invisible (B4), the
NULL-skipping restore disappears with the snapshot it lived in (N3), and the
`newGroup.length` mismatch path now refetches and toasts instead of returning silently with a
moved chip still on screen (B5).

If the refetch GET *itself* fails, `staff[]` is deliberately left alone rather than wiped, and
the toast escalates to "Could not save staff order — reload the page."

**Two consequences worth stating.** First, `refetchStaff()` hand-copies the canonical query
string into two more places, taking the whitelist count from eight to ten (M2.1) — the check
in §4 Step 3 was updated to match. Second, and more honestly than this section originally put
it: when the device is fully offline the screen does **not** immediately agree with the
database. The PATCH fails, the refetch fails too, `staff[]` is deliberately left intact, and
the unsaved order stays on screen until the user reloads — which is exactly what the toast
tells them to do. Screen and DB agree after a *reload*, not instantly. (m2.3)

### Local test results (prep, real browser, live-read DB, all writes stubbed)
1. **Partial failure** — 2 PATCHes succeed, 1 fails: error toast shown **and** the on-screen
   order returned to the true server order. Both halves of the §10 "done when", not just the
   toast. Confirmed the minimal PATCH set at the same time: moving the last of nine AM staff
   to the front issued **3** PATCHes, not 9.
2. **DOM/state mismatch (B5)** — refetch issued, error toast shown, nothing silent.
3. **Refetch also fails** — `staff[]` intact (24 rows before and after, not wiped), toast
   reads "reload the page".

No console errors on prep or line. `tempest_line.html` carries the identical code and loads
clean. **Live DB verified unchanged after testing** — every PATCH in these tests was stubbed.

Still untested here: the real finger-drag gesture (Slices 3 and 4). These tests drive
`persistStaffOrder()` directly, as before.

**Not fixed, by decision:** `persistOrder()` for prep *items* has the identical partial-write
flaw. It is already shipped, belongs to a different feature, and stays out of this build
(see "Explicitly not scheduled").

## 7d. Slice 3 — the drag grip D2 actually specified (2026-08-19)

Closes **B3**, **N4**.

D2 asked for a drag grip and the first build never made one: the whole chip was draggable and
carried `touch-action:none`, which turned a nine-chip staff bar into a multi-row scroll dead
zone at the top of the busiest page. Fixed by following the repo's own proven `.drag-handle`
pattern rather than inventing a second one:

- Each chip gains a **20px `.staff-grip`** (the same six-dot SVG as `.drag-handle`, at 8×14),
  shown only in manager mode.
- **`touch-action:none` moved off the chip and onto the grip only.** The chip now computes to
  `touch-action:auto`, so a finger that lands on a chip scrolls the page.
- Sortable gets `handle:'.staff-grip'`, and `delay:120 / delayOnTouchOnly:true` is replaced by
  `delay:0` — matching the item lists. The delay existed to guard against accidental drags, a
  job the handle now does properly. (The guard was never going to work anyway: it relies on
  letting the browser scroll instead, which the old `touch-action:none` forbade outright.)
- **`+ Add` moved out of `.staff-chips`** into a new `.staff-row` wrapper, so Sortable can no
  longer shuffle a chip past it and strand it mid-row (N4).

### Local test results (prep and line, real browser)
- `touch-action`: chip = `auto`, grip = `none`. This is the whole point of the slice and it is
  measured, not assumed.
- 9 chips, 9 grips, grip box 20×20. Sortable config reads
  `handle:'.staff-grip'`, `draggable:'.staff-chip'`, `filter:'.remove'`, `delay:0`.
- ✕ still fires `removeStaff` on a plain click (dispatched a real click event; correct id).
- Non-manager mode: grips `display:none`, staff bar `display:none`.
- Reorder logic still parses chips correctly through the new markup — a front-of-list move
  issued the same minimal **3** PATCHes and left the PM shift untouched. All writes stubbed;
  live DB not modified.
- No console errors on either page.

**Still not the real gesture.** Sortable's drag cannot be synthesised in the harness, so what
is proven here is the configuration and the scroll fix, not that a finger can perform the
drag. That is Slice 4, and it needs a person on the tablet.

## 7e. Slice 4 — tablet verdict: PASS (2026-08-19)

**Owner tested the drag on the real device and confirmed it works.**

This closes the one question the build had never asked: Sortable's gesture cannot be
synthesised in the automation harness, so every "tested" claim above §7d covers configuration
and persistence logic — not whether a finger can perform the drag. It now has a human answer.

Closes **R5**. **Slice 4b (▲▼ arrow fallback) is therefore cancelled** — it only ever existed
if this test failed. Do not build it.

Recorded as the owner's verdict on the gesture. The detailed §5 checklist items were not
individually re-reported here.


## 7f. Slice 7 — optional smalls (2026-08-19)

Closes **N5**; half-closes **R2**.

**`removeStaff()` now verifies its write (N5).** It used to toast success inside the PATCH
callback without checking the response — the exact pattern the new reorder code three
functions away was careful to avoid, and the shape of the old notes-delete bug. It now
requires a returned row before dropping the chip, and otherwise leaves the person on screen
and says "Couldn't remove — reload to check."

**Staff list re-reads on tab focus (R2, common case).** prep and line render the same staff
bar off the same table, so a manager returning to a stale tab could renumber from a stale
`staff[]` and silently overwrite the other tablet's reorder. A `visibilitychange` listener now
calls `refetchStaff()` when the tab becomes visible. Deliberately silent — no toast for a
background refresh — and `refetchStaff()` already leaves `staff[]` intact if the GET fails.

This is a *half* fix and is not a substitute for optimistic locking: it closes the window
where a tab sat idle, not two managers dragging within the same minute. Full R2 remains
unscheduled (§8).

### Local test results (prep and line, real browser)
- **Blocked write** (PATCH returns 0 rows): error toast, and the person stays on screen —
  no false success. Verified on both pages.
- **Successful write**: normal toast, chip removed, count 24 → 23.
- **Focus refetch**: with `staff[]` deliberately stale at 23, firing `visibilitychange` while
  visible restored it to 24 from the server, silently, with no toast.
  (Note: automation tabs report `document.hidden === true`, so the listener correctly skipped
  until `hidden` was forced false — worth knowing if this is ever retested.)
- No console errors on either page.

**Incidental confirmation that Slice 4 was real.** The live AM order is now
`Rubi 10, Isaac 20, Jose V. 30, Chepe 40, Ismael 50, Everyone 60, Isaac & Jose 70,
Rubi Jose & Isaac 80, Ismael & Chepe 90` — a clean 10..90 renumber, neither alphabetical nor
the original backfill (which had gaps at 20, 100). That is `persistStaffOrder()`'s own
renumbering, written by the owner's finger on the tablet. The drag persists for real.

## 8. Risks — what is still open

Rewritten 2026-08-19 to list only live risks. Closed items are recorded where they were
closed, not here.

1. **Live site, no test database.** `boxkitchen` and `boxkitchen-dev` both point at
   `sxppuyarecqkgkrsrefc.supabase.co`. Any reorder test touches the staff list the kitchen is
   using. Test before service, not during it. (R1)
2. **Rollback is "revert the HTML, never drop the column."** All ten staff queries now
   hard-depend on `sort_order`. PostgREST answers an unknown order column with a 400, and
   `api()` swallows that into `staff=[]` — dropping the column would empty every staff
   dropdown on the site at once. (R4)
3. **Cached tablets after deploy.** A device holding the old page keeps showing the old order
   until it reloads. Harmless — both query forms are valid against the migrated table — but it
   reads as broken. Hard-reload each device once as the last deploy step. (R6)
4. **Two managers, two tablets, silent overwrite.** prep and line render the same staff bar
   off the same table. Reorder on prep, then on line without reloading, and line renumbers
   from its stale `staff[]` and overwrites the first change. No version check, last write
   wins. Real but rare at this size; the focus-refetch in Slice 7 covers the common case.
   Full fix (optimistic locking) is not scheduled. (R2)
5. **`sort_order` has no `DEFAULT` and no `NOT NULL`.** Rows inserted from anywhere but these
   two pages get NULL. The queries now say `.nullslast` explicitly so the behaviour is stated
   rather than accidental, but the column itself is still unconstrained — a DB change, not an
   HTML one. (N2, DB half)
6. **Nothing deploys without approval.**

**Closed, for the record:** RLS UPDATE policy exists (§7, and see W2 for what that does and
does not prove). The "grep for the old string" check that missed B1 has been replaced by the
whitelist grep in §4 Step 3. The untested-drag risk was closed by the owner's tablet test
(§7e), which also cancelled the arrow-button fallback.

---

## 8b. Expected behaviour that looks like a bug

Both of these are working as designed. They are written down because to whoever is using the
feature they read as breakage.

**Reordering the PM bar does not change meat / portion / notes / orders. (R3)**
Those four pages have no AM/PM concept — they show one flat list of people. They sort
`shift.asc` first and then keep the first row per name, which is always the AM row. So those
dropdowns are: *everyone on AM, in AM order, then the PM-only people.* Dragging the PM staff
bar changes the PM order on prep and line, and correctly changes nothing on those four pages.
If you want a different rule there, it needs one ordering source for the read-only pages —
that is a new decision, not a bug fix.

**`boxkitchen` and `boxkitchen-dev` have now diverged. (N7)**
These files exist in both repos against one database; this work is only in `boxkitchen`.
Whichever repo is the deploy source, the other is stale — reconcile before doing staff work
out of `boxkitchen-dev`.

## 9. Adversarial review (2026-08-19)

Reviewed the doc against the working tree, not just on its own terms. Ranked worst first.

**This section is the original review, kept as written. It is no longer the open list** — most
of it has since been fixed. Current status:

| Finding | Status |
|---|---|
| B1 note-modal query, B2 grep check, N2 (query half) | Fixed — Slice 1, §7b |
| B4 partial write, B5 silent no-op, N3 NULL restore | Fixed — Slice 2, §7c |
| B3 drag grip / scroll dead zone, N4 stranded `+ Add` | Fixed — Slice 3, §7d |
| B6 uncommitted work | Fixed — Slice 0, committed and pushed as PR #93 |
| R5 untested gesture | Closed — owner tablet test passed, §7e |
| W1, W2, W3, W4, R3, N7 | Fixed — Slice 5, this pass (§Status, §1, §7, §8, §8b) |
| R1, R2, R4, R6, N2 (DB half) | **Still open** — see §8 |
| N5 unverified `removeStaff` write | **Still open** — Slice 7, optional |

For what is actually open right now, read §8. Do not use the list below as a to-do.

### Blockers — fix before deploy

**B1. The note-modal staff query on prep and line was only half-updated.**
`tempest_prep.html:906` and `tempest_line.html:899` read
`order=sort_order.asc,name.asc` — no `shift.asc` — then de-duplicate by name with no
shift concept anywhere in the modal. That is exactly the interleaving §7 says `shift.asc`
exists to prevent. Result: the "Posted by" list inside the note modal on prep and line is
in a *different* order from the identical modal on orders (`tempest_orders.html:1111`),
and AM/PM interleave in both. Two files, one query string each.

**B2. The verification step in §4 Step 3 cannot catch B1.**
"Grep for `order=name.asc` and confirm zero remain" proves a page was *touched*, not that
it was touched *correctly* — B1 passes that grep cleanly. The check that works is
whitelist-shaped, not blacklist-shaped: every staff query in the repo must be one of two
known-good strings.

```
grep -rn "GET','staff'\|'staff','location" *.html
```
→ prep/line main + note modal: `order=shift.asc,sort_order.asc,name.asc`
   (main loads may keep the 2-key form only because `getStaffForShift()` re-filters;
   the note modals do not, so they need the 3-key form)
→ meat/portion/notes/orders: `order=shift.asc,sort_order.asc,name.asc`
Anything else is a bug.

**B3. No drag grip was built, and the entire chip is a scroll dead zone.**
D2 specified "a drag grip to each chip." The shipped code drags the whole chip
(`draggable:'.staff-chip'`, no `handle:` option) and puts `touch-action:none` on the whole
chip — `tempest_prep.html:63`, `tempest_line.html:63`.

Compare the repo's own proven pattern at `tempest_prep.html:167`: `.drag-handle` confines
`touch-action:none` to a 22px handle, so the rest of the row still scrolls. The staff bar
throws that discipline away. Every chip now refuses to scroll the page, and `delay:120 /
delayOnTouchOnly:true` cannot rescue it — that guard works by *letting the browser scroll
instead*, which `touch-action:none` forbids outright. A staff bar of nine wrapped chips is
a multi-row dead zone at the top of the busiest page.

Manager-mode only (`.staff-bar` is `display:none` otherwise, `tempest_prep.html:58-59`) —
but managers are the only people who use this feature. Build the grip D2 asked for, or
drop `touch-action:none`. Not both as-is.

**B4. "Rolls back cleanly" (§7) is not true.**
`persistStaffOrder()` fires one PATCH per changed row. If two succeed and two fail, the two
successes are **already committed**. The rollback restores the in-memory array and
re-renders — the database is left half-renumbered, and the next reload shows an order
nobody chose. The inherited `persistOrder()` has the identical flaw, so this is pre-existing
debt rather than a new mistake, but §7 records it as a strength. Accurate wording: *"reverts
the screen; a partial write is not undone."* A real fix is one bulk PATCH, or a re-GET on
failure instead of a local restore.

**B5. There is a silent no-op path.**
`if(newGroup.length!==getStaffForShift().length)return;` — Sortable has already moved the
DOM by the time this runs. The function returns with no re-render and no toast, so the
screen shows a reorder that was never saved and will disappear on the next reload. Same
shape as the notes-delete RLS bug: the UI implies success, nothing persisted. Fail loudly
and re-render instead.

**B6. None of this is committed.** *(FIXED — Slice 0. The text below was true at review time
and is false now: the branch is committed and pushed as PR #93.)*
Branch `staff-edit-and-reorder` is **0 commits ahead of origin/main**. All 192 lines are
uncommitted working-tree edits, and `docs/` is untracked entirely. One `git checkout main`
loses the build. Given that this repo gets worked concurrently, this is the highest-
probability actual loss on the page — and it costs one commit to remove.

### What breaks in real use

**R1. There is no test database.** `boxkitchen` and `boxkitchen-dev` both point at
`sxppuyarecqkgkrsrefc.supabase.co`. §5's "real device, before deploy" checklist reorders the
live staff list the kitchen is using right now, and the migration is already on production.
Run the checklist before service, not during it.

**R2. Two managers, two tablets, silent overwrite.** prep and line render the same staff bar
off the same table. Reorder on prep, then reorder on line without reloading, and line
renumbers from its stale `staff[]` and overwrites the prep change with no warning. No
version check, last write wins. Not in the §5 checklist.

**R3. PM-only staff are permanently last on four pages.** meat/portion/notes/orders sort
`shift.asc` then keep the first row per name — always the AM row. Those dropdowns are
therefore *everyone on AM, in AM order, then the PM-only people*. Reordering the PM bar
changes nothing on those pages. Defensible, but undocumented: to whoever is using it, it
reads as the feature being broken. Write it down as expected behaviour, or give the
read-only pages one ordering source.

**R4. If `sort_order` ever goes missing, every staff dropdown on the site empties at once.**
All seven queries now hard-depend on the column. PostgREST answers an unknown order column
with a 400, and `api()` swallows it into `staff=[]`. So the rollback plan is **revert the
HTML, keep the column** — never drop the column to undo. That coupling is stated nowhere.

**R5. No fallback shipped, and the gesture has zero test coverage.** D2 named ▲▼ arrows as
the fallback if drag proves fiddly, and §7 admits the real drag was never exercised. If it
doesn't work on the kitchen tablet, there is no other way to reorder. Deciding "by feel on
a kitchen tablet" is fine; deploying with no plan B is the risk.

**R6. Cached HTML on the tablets.** Devices holding the old page keep showing alphabetical
order until they reload. Harmless — both query forms are valid against the migrated table —
but the manager will reorder, walk to the meat station, see the old order, and call it
broken. Add "hard-reload each device once" to the deploy steps.

### Wrong or misleading in this doc

**W1. The status line oversells it.** "built, tested locally" — the caveat that Sortable's
gesture can't be synthesised sits 190 lines below it. What was tested is
`persistStaffOrder()` invoked by hand against a pre-reordered DOM: the persistence logic,
not the feature. Untested: that Sortable initialises on the chip row at all, that
`filter:'.remove'` keeps the ✕ clickable, that `evt.oldIndex/newIndex` mean what the code
assumes, and that a finger can perform the drag. Move that caveat up to §Status.

**W2. §7 records "RLS … open to `public`" as a check that passed.** What it means in
practice: the anon key is in plain text in all seven of these HTML files, and `staff` now
accepts UPDATE from anyone who opens dev tools. The locked decision "staff can never
reorder" is enforced by a hidden div and a localStorage PIN — a UX gate, not a security
control. Consistent with the rest of the site and not a reason to stop, but it should not be
filed as a safety check that came back clean.

**W3. §8 Risks is stale.** Risk 1 (RLS) was closed in §7. Risk 2 (the grep) was run and
still missed B1. As written, a reader cannot tell what is still open.

**W4. "Seven places" counts where the `staff` table is read**, which is narrower than §1's
stated goal, "every Who / Assign / Counted by / Posted by dropdown across the site." Two
name fields sit outside that set by design (N1). Tighten §1 to "every staff *dropdown*" so
the goal matches what was actually scoped.

### Not thought about

**N1. Two staff-name fields aren't dropdowns — and stay that way. [decided 2026-08-19]**
`tempest_flash.html:187` ("Entered by", a free-text `<input>`) and `tempest_notes.html:269`
("Who's resolving this note?", a `prompt()`) don't read the `staff` table, so they inherit
no ordering. **Owner decision: leave them as typed boxes.** Only a few people can reach
those two pages, so a dropdown isn't worth the surface area. Closed — not a bug, not
scheduled.

One consequence still carries into §6 and is independent of that decision:
`flash_days.entered_by` holds typed staff names and is **missing from §6's rename column
list** — the one-off rename SQL updates seven columns, not six. And because these two
fields stay free text, a rename keyed on an exact match (`WHERE name = '…'`) will miss any
variant already typed into them. Read the distinct values in those two columns *before*
running a rename, not after.

**N2. `sort_order` has no `DEFAULT` and no `NOT NULL`.** Any row inserted from anywhere but
these two pages gets NULL. It happens to behave — Postgres sorts NULLs last on ASC, which
matches the `1e9` sentinel in `sortStaff()` — but that agreement is accidental and
undocumented. Make it explicit (`order=sort_order.asc.nullslast`, or a column default).

**N3. The rollback skips NULLs.** `if(snap[staff[j].id]!=null)` leaves the optimistic value
in place for any row whose original `sort_order` was NULL. Latent today because the backfill
filled everything; live again the moment N2 happens.

**N4. `+ Add` sits inside the sortable container.** It isn't `draggable`, so it can't be
picked up, but Sortable can still shuffle a chip past it and strand the button mid-row.
Cosmetic, untested, one line to fix — give chips a `handle`, or move the button out of
`.staff-chips`.

**N5. Retire (✕) still doesn't verify its write.** `removeStaff()` (`tempest_prep.html:790`)
toasts success inside the PATCH callback without checking `r` — the exact pattern the new
code three functions away was careful to avoid. §5 tests that ✕ "still works, unchanged";
unchanged includes unverified.

**N6. Good news worth stating: deploy order across the six files does not matter.** The
migration is already live and both the old (`name.asc`) and new query forms are valid
against it, so the files can go out one at a time, in any order, with no broken window.
That is normally the scariest part of a six-file change and here it is a non-issue.

**N7. The two repos will now diverge.** These files exist in both `boxkitchen` and
`boxkitchen-dev` against one database; this work is only in `boxkitchen`. Whichever repo is
the deploy source, the other is now stale.

### Judged not worth fixing

Double-add can create two active rows for one name (pre-existing; de-dup hides it
everywhere it matters). No index on `sort_order` — nine rows. Sortable instance churn on
every `render()` — `initSortables()` destroys the old instances first
(`tempest_prep.html:590`), so it is already handled.

---

## 10. Build slices

*(Written when everything was uncommitted; that is no longer true — see the status marks on
each slice below.)* What follows is the *remaining* work, cut so
each slice is one sitting, one commit, one review — and closes a named finding from §9.
"Done when" is the check that ends the slice; if it can't be checked, the slice isn't done.

Order matters only where "blocked by" says so.

---

### Slice 0 — Get the existing build into git ✅ DONE
**Delivers:** the 192 lines that already exist stop being one command away from gone, and
become a diff someone can actually review.
**Closes:** B6.
**Touches:** no code. `git` only — verify the branch is still based on `origin/main`, commit
the six HTML files and `docs/`, push, open the PR.
**Done when:** `git status` is clean, `git rev-list --count origin/main..HEAD` is ≥ 1, PR open.
**Size:** 10 minutes. **Blocked by:** nothing — and it blocks everything else, because every
slice below edits those same six files.

---

### Slice 1 — One ordering rule for every staff dropdown ✅ DONE (§7b)
**Delivers:** every staff list on the site — including the note pop-ups — comes back in the
same order, from the same query.
**Closes:** B1, B2, N2.
**Touches:** the two half-fixed note modals (`tempest_prep.html:906`,
`tempest_line.html:899`) get `shift.asc` added; all seven staff queries get
`sort_order.asc.nullslast` so the NULL behaviour is stated instead of inherited. Replace §4
Step 3's "grep for the old string" check with the whitelist grep from B2.
**Done when:** `grep -rn "GET','staff'\|'staff','location" *.html` returns eight lines and
every one matches an approved form *(was eight at the time; ten now — see M2.1)*; the note pop-up on prep, line and orders lists people in
the same order as the Who dropdown.
**Size:** ~30 minutes, mechanical, no device needed. **Blocked by:** Slice 0.

---

### Slice 2 — Make a failed save tell the truth ✅ DONE (§7c)
**Delivers:** after a reorder that fails, the screen and the database agree. Today they can
disagree silently, which is the failure mode that cost you the notes-delete bug.
**Closes:** B4, B5, N3.
**Touches:** `persistStaffOrder()` in prep and line. Recommended shape: on *any* PATCH
failure, stop trying to restore from the local snapshot and instead re-GET the staff list and
re-render from the server. That single change fixes all three findings at once — partial
writes stop being invisible (B4), the NULL-skipping restore disappears entirely (N3) — and
the `newGroup.length` mismatch path (B5) gets the same treatment: re-render and say so,
instead of returning silently.
**Done when:** with the network throttled to offline mid-drag, you get the error toast **and**
a reload shows the pre-drag order. Both halves, not just the toast.
**Size:** ~1 hour. No device needed — this is testable in a browser. **Blocked by:** Slice 0.

---

### Slice 3 — Build the drag grip D2 actually specified ✅ DONE (§7d)
**Delivers:** a deliberate drag handle, and a staff bar that still lets you scroll the page.
**Closes:** B3, N4.
**Touches:** prep and line — add a grip element to each chip, set `handle:` on the Sortable
config, move `touch-action:none` off the chip and onto the grip only (matching `.drag-handle`
at `tempest_prep.html:167`, which is the pattern that already works here), and move the
`+ Add` button out of `.staff-chips` so it can't get stranded mid-row.
**Done when:** on a real tablet — a finger swipe that *starts on a chip* scrolls the page; a
drag from the grip reorders; the ✕ still deletes on a single tap.
**Size:** ~1 hour to write, but the "done when" needs a device. **Blocked by:** Slice 0;
best done before Slice 4 so the device trip tests the final gesture, not the current one.

---

### Slice 4 — Prove it on the kitchen tablet ✅ DONE — PASS (§7e); 4b cancelled
**Delivers:** the answer to the only question this build has never asked: can a person
actually do this with a finger, during service, on your hardware.
**Closes:** R5, and the §5 checklist for real.
**Touches:** nothing yet — this is a test, and a decision.
**Done when:** you've run the §5 checklist on the tablet **before service** (R1: there is no
test database — this reorders the live staff list), and written the verdict into §7.
**Size:** 20 minutes. **Blocked by:** Slice 3.
**⚠ See "Is anything still too big" below — this slice hides a second one inside it.**

---

### Slice 5 — Doc truth pass ✅ DONE (this pass)
**Delivers:** a document someone can trust to decide whether to deploy.
**Closes:** W1, W2, W3, W4, R3, N7.
**Touches:** doc only. Status line carries the untested-gesture caveat instead of burying it
(W1); §7 stops recording "RLS open to public" as a check that passed (W2); §8 Risks is
rewritten to only what's still open (W3); §1's goal is scoped to "every staff dropdown" (W4);
**R3 gets written down as expected behaviour** — reordering the PM bar does not change
meat/portion/notes/orders, because those pages show AM order then PM-only people; and a line
noting `boxkitchen` and `boxkitchen-dev` have now diverged (N7).
**Done when:** the Status line and §8 both match what is actually true on the branch.
**Size:** 30 minutes. **Blocked by:** nothing. Can run any time before Slice 6.

---

### Slice 6 — Deploy ⬅ PARTLY DONE ALREADY (see §12)
**Delivers:** the feature in the kitchen's hands.
**Closes:** R4, R6, N6.
**Touches:** deploy of six HTML files. Write the rollback into the doc *first*: **revert the
HTML, never drop the column** — all seven queries now hard-depend on `sort_order`, and
dropping it 400s every staff query and empties every dropdown on the site at once (R4). Per
N6 the six files can go in any order, one at a time, safely. Finish by hard-reloading each
kitchen device once (R6) — otherwise a cached tablet shows the old order and reads as broken.
**Done when:** each device has been reloaded and shows the chosen order; the rollback line is
in the doc.
**Size:** 30 minutes. **Blocked by:** Slices 1–5, and your approval — live site.

---

### Slice 7 — Optional smalls ✅ DONE (§7f)
**Delivers:** two loose ends, only worth doing if you're already in these files.
**Closes:** N5 — `removeStaff()` (`tempest_prep.html:790`) toasts success without checking
the write landed, three functions away from the new code that was careful to check.
Optionally a cheap half-fix for R2: re-GET the staff list when the page regains focus, so a
manager returning to a stale tab doesn't overwrite the other tablet's reorder.
**Size:** 20 minutes. **Blocked by:** Slice 0. Skip freely.

---

### Explicitly not scheduled
- **R2 in full** (two managers, no version check, last write wins). Needs optimistic
  locking; real, but rare at this size. The focus-refetch in Slice 7 covers the common case.
- **The same partial-write flaw in `persistOrder()`** for prep items — identical bug, already
  shipped, different feature. Its own slice on its own day, not smuggled into this one.
- **§6 renaming.** Unchanged: worth a one-off SQL migration whenever you want it, and it does
  not need this build.

---

### Is anything still too big?

**Slice 4 is.** It reads as a 20-minute test, but it's a test *and* a contingent build hiding
behind it: D2 named ▲▼ arrows as the fallback if drag proves fiddly, and none were built. If
the tablet test fails, "Slice 4" silently becomes a fresh feature at the end of a day you'd
planned to finish. Cut it in two:

- **4a — Test on the tablet.** 20 minutes. Deliverable is a written yes/no, nothing more.
- **4b — Build ▲▼ arrows.** ~2 hours, prep and line. **Only exists if 4a says no.** Don't
  plan it, don't pre-build it; just don't be surprised by it.

Everything else is one sitting. The two worth watching:

- **Slice 2** carries a design change (re-GET instead of local snapshot restore) rather than a
  patch. That's the right call — one change closing three findings beats three patches — but
  it means the review is about the approach, not the diff. Decide the shape before writing it.
- **Slice 6** touches six files, which *looks* like the risky one and isn't: N6 established
  that any deploy order is safe here. Its real risk is approval and rollback, not size.

And one that's smaller than it looks: **Slice 0.** It's ten minutes of git with no code in it,
which is exactly why it keeps getting postponed. It's also the only slice where the downside
is losing work you've already paid for.

---

## 12. How this site actually deploys — and what is already live (2026-08-19)

**Merging to `main` IS the deploy.** GitHub Pages serves this repo from branch `main`, path
`/`, at https://pourguyssf.github.io/boxkitchen/. There is no build step, no CI, no checks
and no separate deploy action. A merged PR is in the kitchen about a minute later.

This corrects two things the plan got wrong:

- **§4/§10's "six files, one at a time, in any order" (N6) does not apply.** A merge is
  atomic — every file ships together. That is *safer* than the plan assumed, but it is not
  what the plan described.
- **"Nothing deploys without approval" is not enforced by anything.** It is a convention, and
  an ordinary PR merge silently satisfies it. If the gate should be real, these PRs must be
  opened as **drafts**, because merging is deploying.

### Already live as of 2026-08-19 20:21 UTC
PR #93 was squash-merged (commit `3409c30`), which deployed **Slices 0 and 1**. Verified
against the live URL, not just against git:

| | live? |
|---|---|
| Consistent staff queries everywhere (Slice 1, closes B1) | **yes** |
| `refetchStaff()` honest failed-save (Slice 2) | no |
| Drag grip + staff-bar scroll fix (Slice 3) | no |

So the production staff bar still carries `.staff-bar .staff-chip{...touch-action:none}` —
the B3 scroll dead zone — and still has the snapshot rollback that can show an order which
was never saved (B4/B5). **The bugs Slices 2 and 3 fix are the ones currently deployed.**

**Consequence for §7e:** the owner's tablet test was run against the *pre-grip* build, so it
confirms the old whole-chip gesture, not the grip. The grip is strictly more deliberate than
what was tested, but the grip gesture itself is still unproven on a device.

### Deploy checklist for the remaining slices
1. Merge outside service — there is no test database (R1).
2. Rollback = **revert the HTML commit on `main`**, which triggers a Pages rebuild.
   **Never drop the `sort_order` column** — all ten staff queries depend on it and dropping
   it 400s every one, emptying every staff dropdown at once (R4).
3. Pages serves `cache-control: max-age=600`, so a tablet can hold the old page for up to ten
   minutes. **Hard-reload each device** as the last step or it reads as broken (R6).

## 11. Running minors (slice reviews)

Small stuff surfaced by per-slice review. Not blockers; fold in whenever the relevant file
is already open. Newest slice last.

### From Slice 0 review (2026-08-19) — verdict: PASS
- **m0.1** PR #93 is not a draft, though both it and the commit message say "not for
  deploy yet." Nothing but convention prevents a merge. Mark it draft until Slice 5.
- **m0.2** §9 B6 and the §10 preamble are now stale — B6 (line ~273) still says "0 commits
  ahead… uncommitted," and §10's preamble says "written but uncommitted." Both are false as
  of `c807914`. Fold into Slice 5's doc truth pass.
- **m0.3** Slice 0 landed as one 729-line commit (537 of them the doc), which partly defeats
  its own stated deliverable — "a diff someone can actually review." Doc and code would have
  read better split. Not worth rewriting history; just split them next time.
- **m0.4** The Status line (line 3) carries no branch/PR pointer now that one exists. Add
  "PR #93" alongside the W1 caveat fix.

### From Slice 1 review (2026-08-19) — verdict: PASS
- **m1.1** The whitelist check in §4 Step 3 says "expect **eight** lines." That was true at
  `9c80fa5` and is no longer — see M2.1 below. Fix the number, not the queries.
  **FIXED — Slice 5.**

### From Slice 2 review (2026-08-19) — verdict: PASS, one major
- **M2.1** *(major, not a minor — listed here so it isn't lost)* `refetchStaff()` adds a
  tenth staff query (one in prep, one in line), so §4 Step 3's "expect eight lines" whitelist
  check now reports ten and appears to fail on every run. All ten strings are correct, so
  nothing is broken in the product — but the guard that exists to catch B1-shaped bugs now
  cries wolf, and a check that always fails is a check that gets ignored. Update the expected
  count to **ten** in §4 and §7b. **FIXED — Slice 5 (§4 Step 3, §7b, Slice 1's done-when).**
- **m2.2** §7c describes `refetchStaff()` as a re-render path and doesn't note that it also
  introduced a new copy of the canonical query string — which is what causes M2.1.
- **m2.3** Offline, the screen still shows the unsaved order until the user reloads: the
  PATCH fails, the refetch fails too, and `staff[]` is deliberately left intact. That is the
  right call and the toast says "reload the page," but §7c reads as though screen and DB
  always agree after a failure. They agree after a *reload*. **FIXED — Slice 5 rewrote that
  paragraph in §7c.**
- **m2.4** The canonical query string is now hand-copied in ten places. A per-file
  `STAFF_Q` constant would make the whitelist check trivially true. Noted only — there is no
  shared JS here by design, and this is not the build to change that.

### From Slice 3 review (2026-08-19) — verdict: PASS on the code, slice still open
- **M3.1** *(major)* Slice 3's "done when" is device-shaped — a finger swipe starting on a
  chip scrolls, a drag from the grip reorders, the ✕ deletes on one tap — and none of that
  has been run. What was verified is computed styles and Sortable config in the harness,
  which is the right evidence for the *fix* but not the stated check. Per §10's own rule
  ("if it can't be checked, the slice isn't done"), Slice 3 stays open until Slice 4a.
  **CLOSED — the owner's tablet test passed (§7e).** See M5.1: §7e records one overall PASS
  rather than the individual gestures, and does not say whether the 20×20 or the 22×30 grip
  was under the finger.
- **M3.2** *(major — FIXED 2026-08-19)* The grip shipped at 20px wide / 20px min-height,
  smaller than the `.drag-handle` pattern it copies (22×30) and well under the 44px touch
  guideline, on exactly the gesture Slice 4 exists to test. Bumped to **22×30** in prep and
  line so the device trip tests the version worth shipping. If 4a still says "fiddly," grip
  size is the next cheap lever before the ▲▼ arrows of 4b.
- **m3.3** `+ Add` alignment changed: it is now a sibling of `.staff-chips` under
  `align-items:flex-start`, so with chips wrapped over two or three rows it sits top-right of
  the block rather than trailing the last chip. Correct per N4, but it is a visible layout
  change and §7d's test list doesn't mention looking at it. Eyeball it during Slice 4a.
- **m3.4** `filter:'.remove'` / `preventOnFilter:false` are now dead config — with `handle:`
  set, the ✕ can't start a drag either way. Harmless belt-and-braces; the comment still
  explains it as the thing protecting the ✕.
- **m3.5** The grip is a `<span>` with an `aria-label` and no `tabindex`, so there is no
  keyboard path to reorder. Fine for this hardware; noted because the label implies otherwise.
- **m3.6** Chip padding became asymmetric (`4px 6px 4px 4px`) to seat the grip. Intentional,
  just unrecorded in §7d.

### From Slice 5 review (2026-08-19) — verdict: PASS, one major
- **M5.1** *(major, open)* §7e records a single blanket tablet PASS, and the 22×30 grip bump
  was committed *inside* `b61ca07` — the same commit as the test record. So the doc cannot
  say whether the finger test ran on the old 20×20 grip or the shipped 22×30 one, and §7e
  itself notes the §5 checklist items were not individually re-reported. Slice 4's done-when
  was "run the §5 checklist"; Slice 3's was three named gestures. Before Slice 6, write into
  §7e which grip was tested and which checklist lines were actually run. A bigger target is
  very unlikely to be worse — this is about the record, not the risk.
- **m5.2** *(fixed here)* §7's RLS paragraph said "all seven of these HTML files." It is six —
  the seventh was `tempest_flash.html`, which N1 took out of scope. Corrected. The identical
  line inside §9 W2 is **left alone on purpose**: §9 is kept as written, and editing the
  historical review would defeat the point of keeping it.
- **m5.3** *(fixed here)* §11 itself was the one section Slice 5 didn't sweep — M2.1, M3.1,
  m1.1 and m2.3 all still read as open after being fixed. Status marks added.
- **m5.4** *(open, cosmetic)* §9's W-findings still read as open in their own text (~lines
  524–541). The status table Slice 5 added above them covers it and §9 is explicitly
  historical, so this is consistent — but a skimmer can still land on W3 and conclude §8 is
  stale. If it ever bites, one "superseded" marker per W-heading fixes it.
