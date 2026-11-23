# Kits — the Line PM link

Status: **plan v1, approved by Stephen 2026-11-08.** Written in the Kits planner window from
Stephen's answers on 2026-11-08. Every decision below is Stephen's. It goes into the repo as
`docs/kits-line-link.md` with Slice 1's PR.

**Slice 1 LIVE** (#188, 2026-11-16); Stephen's phone check passed 2026-11-19.
**Slice 2 LIVE** (#191, `897d045`); **phone check passed 2026-11-19** (Stephen confirmed to the
planner, 2026-11-22: "yes the 11/19 phone check passed"). See "Slice 1 as built" and
"Slice 2 as built" below. **Kits menu update** (Suadero and Chilorio buttons): **LIVE** (#196,
2026-11-22), phone check passed 2026-11-23; see `docs/kits.md` "Menu update as built". **The
Line PM link is done.**

It is the step `docs/kits.md` names first under "Later": tapping a kit item on Line PM opens
that kit's sheet, "so they make sure everything needed has been kitted". Kits itself (B5) is
done and live (#168, #174, #178, #182, #184).

---

## What it is for

The PM cook builds tomorrow's kits from the Line PM list. Today the list says *that* a kit is
due ("Kit - Pork belly", with its KIT/MAKE pill), and the Kits page says *what goes in it*,
but nothing connects the two. This adds a small **SHEET →** button to each kit item, which
opens that kit's sheet, and a way back to the list.

---

## Decisions (Stephen, 2026-11-08)

| question | decided |
|---|---|
| Where to tap | **A small "SHEET →" button** on the row, next to the KIT/MAKE pill. The name keeps working as it does today: it does nothing for staff, and in manager mode a tap renames the item. |
| Ticks on the sheet | **None.** The Line PM checkbox stays the "kit built" record. The sheet stays read-only, with no database change. |
| A renamed item | **The button hides until it's set up.** It shows only while the item's name still matches its kit, so a row renamed to another dish loses its button rather than opening the wrong sheet. A new kit gets its button when it's added to the Kits page (a small code change, as today). |
| Getting back | **"← Line PM"** at the top of the sheet when it was opened from Line PM, and it returns to the **PM** list. Opened from the Kits tile, it still says "← All kits". The phone's back swipe works either way. |
| Kit order | **The Kits page follows Line PM's current order**: Mac & cheese, Buffalo sauce, Pork belly, Gastrique, Chicken & dumpling soup, Dumpling, Spicy green sauce, Pickled onions & peppers. This applies to the list and to "Print all 8 kits". It's a one-time reorder, and it won't follow later moves automatically. |

**Stephen, 2026-11-16** (after the November menu change; these win where they differ above):

| question | decided |
|---|---|
| Are all 8 kit sheets still in use? | **No. Spicy green sauce is off the menu.** Row 673 stays on Line PM but gets **no button**: **7 buttons**, not 8. The Kits page and its Spicy green sauce sheet stay as they are for now. |
| Sheets for Suadero and Chilorio? | **Yes, as their own small ticket after Slice 2** (see "Later"). That ticket adds both sheets, removes Spicy green sauce, and maps 675 and 676. |
| Where the button sits | **On its own line under the item name**, not next to the pill: next to the pill it was cut off to "…" at phone width. Kit rows get a little taller. |

---

## Ground truth — read-only, 2026-11-16

**The kit items** (`prep_items`, `station='kits'`, `team=line`, `shift=PM`,
`category=daily`). There are 11 rows, read with one GET on 2026-11-16. **Since 2026-11-08** the
November menu change renamed placeholders 675 (→ Suadero) and 676 (→ Chilorio), and Spicy
green sauce came off the menu:

| id | name on Line PM | sort | gets |
|---|---|---|---|
| 668 | Kit - Mac and Cheese | 10 | button → `#mac-and-cheese` |
| 669 | Kit - Buffalo sauce | 20 | button → `#buffalo-sauce` |
| 670 | Kit - Pork belly | 30 | button → `#pork-belly` |
| 671 | Kit - Gastrique | 40 | button → `#gastrique` |
| 672 | Kit - Chicken & Dumpling soup | 50 | button → `#chicken-dumpling-soup` |
| 678 | Kit - Dumpling | 60 | button → `#dumpling` |
| 673 | Kit - Spicy green sauce | 70 | no button: off the menu |
| 674 | Kit - Pickle onions& peppers | 80 | button → `#pickled-onions-peppers` |
| 675 | Kit - Suadero | 90 | button → `#suadero` (since the Kits menu update, 2026-11-22) |
| 676 | Kit- Chilorio | 100 | button → `#chilorio` (since the Kits menu update, 2026-11-22) |
| 677 | Kit- New prep coming soon | 110 | no button (placeholder) |

Item names don't match the kit names ("Pickle onions& peppers", "Mac and Cheese"). That's why
the map is by row id, with a name check on top.

**The Line page** (`tempest_line.html`):
- Kit rows exist **only on Line, PM shift**. `stationOrder()` puts `kits` first on PM.
  `tempest_prep.html` shares the row code but never shows a kits station (team `kitchen`,
  no `kits` in its order), so **Prep is not touched**.
- The row is drawn in `bTask()`. The pill is
  `<span class="mode-pill …" onclick="event.stopPropagation();toggleMode(id)">`. The name
  calls `editN()`, which returns at once unless manager mode is on.
- **The page always opens on AM** (`var shift='AM'`). Nothing reads the address. So a plain
  link back to `tempest_line.html` would land on the AM list, not PM. That is why Slice 1
  exists.
- **No guard covers `tempest_line.html`** apart from `check_styling.py`. It is the busiest page
  in service, so the change stays small and gets its own headless checks.

**The Kits page** (`tempest_kits.html`): `KITS` is an array in Line PM's *old* order. The
address is the hash (`#pork-belly`), read by `route()`. Back is `#backLink`, "← All kits",
`href="#"`.

---

## The design

**On Line PM**, each matched kit row gets one more element, **on its own line under the
name** (inside `.task-info`, after the rename input; Stephen, 2026-11-16):

```
[✓]  Kit - Pork belly   (KIT)
     (SHEET →)
```

- It's a link, `<a class="link-btn kit-sheet-link" href="tempest_kits.html?from=line#pork-belly">SHEET →</a>`,
  in the same tab, so the phone's back swipe returns to Line.
- The look is the shared outline `.link-btn` that the Kits page already uses: no new colour,
  and a tap target of at least 44px. `kitchen.css` already hides `.link-btn` in print, so the
  printed Line list doesn't change. Its `onclick` stops the tap reaching anything else on the
  row.
- It shows for staff and in manager mode alike.
- **The map** is a small table in the Line page, one entry per row id: the kit's address plus
  a word the name must still contain (ignoring case, punctuation and spacing):
  668 `mac` · 669 `buffalo` · 670 `pork belly` · 671 `gastrique` · 672 `soup` ·
  678 `dumpling` **and not** `soup` · 674 `pickle` — **7 entries**. If the word is missing, or
  the id isn't in the map, there's no button. 673 (off the menu), 675/676 (no sheet yet) and
  677 (placeholder) have no entry.

**On the Kits page:**
- `?from=line` in the address changes the top link to **"← Line PM"**, going to
  `tempest_line.html#pm`. Without it, nothing changes.
- `KITS` is reordered to Line PM's current order. Nothing else in a kit changes.

**On Line PM, Slice 1's part:** the page opens on **PM** when its address ends in `#pm`. That
uses the existing `setShift('PM')` after the first load. Any other address still opens on AM,
exactly as today.

No database change, no SQL, no new table, and no change to `assets/kitchen.css` rules.
`index.html` is untouched.

---

## Slices

**Two, each small.** Every slice is its own branch and PR from `origin/main`, names its files
up front, adds its promises to a guard, passes `check_styling.py`, and **stops before pushing**.

### Slice 1 — The way back, and the order (invisible to staff on Line)

- `tempest_line.html`: open on PM when the address is `#pm`. Nothing else on Line changes.
  Nobody reaches `#pm` until Slice 2, so staff see no difference.
- `tempest_kits.html`: `?from=line` → "← Line PM" to `tempest_line.html#pm`, and the `KITS`
  reorder.
- Guards: `check_kits.py` gets the new order (list, print, addresses) and the
  `?from=line` back link on a kit, a not-found kit and the empty-kit screen. The plain
  address keeps "← All kits". Still GETs only, exactly 1. A new, small headless check on the
  Line page with a stubbed `api()`: plain address → AM; `#pm` → PM with the Kits station first;
  **no write on load** in either case.
- **Stephen's check:** open the Kits tile and see the new order. Open
  `…/tempest_kits.html?from=line#pork-belly` from a link the builder gives him, tap
  **← Line PM**, and he should land on the PM list.

### Slice 1 as built (2026-11-16, live as #188)

**`tempest_line.html`** — 4 lines. Before the first draw, an address ending in `#pm` starts the
page on PM with the PM SHIFT button active. Any other address opens on AM exactly as before. No
new request, no write, no class renamed, no `api()` call touched.

**`tempest_kits.html`** — opened with `from=line` in its query, the top link of a kit sheet
reads **"← Line PM"** and goes to `tempest_line.html#pm`; that covers the normal sheet, the
"Recipe not found" sheet and the empty-kit sheet. Without it, **"← All kits"** to the list, as
before. `backLink` / `kit-back` kept; the link never prints. `KITS` reordered to Line PM's live
order (Mac & cheese, Buffalo sauce, Pork belly, Gastrique, Chicken & dumpling soup, Dumpling,
Spicy green sauce, Pickled onions & peppers), matched on 2026-11-08. Nothing inside a kit
changed; addresses unchanged; the list and "Print all 8 kits" follow the new order.

**`scripts/check_kits.py`** — the new order everywhere it is asserted (list, print's 8 sheets,
the one read's id list); Back checked by words and address on every sheet; three new
`from=line` scenarios (a kit and moving to another, not-found, empty-kit), each "← Line PM" to
`tempest_line.html#pm`. Every scenario still ends GETs only, exactly 1.
**515 assertions, 22 scenarios, clean.**

**`scripts/check_line.py`** (new) — the real Line page with `XMLHttpRequest`, `fetch` and
`sendBeacon` stubbed, fed the 11 real kit rows plus one non-kit PM row and one AM row.
`plain`: AM active, no kit row drawn. `pm`: PM active, Kits station first, all 11 kit rows.
Both: GETs only, no write headers or bodies, only the four tables it always reads.
**18 assertions, 2 scenarios, clean.**

**`.github/workflows/line-guard.yml`** (new) — runs `check_line.py` on PRs touching
`tempest_line.html`, `assets/**` or `scripts/check_line.py`.

**`check_styling.py`** — clean (15 pages, 99 inputs measured, 75 on the #135 register).

**Fails when it should** (each in a scratch copy, never the worktree) — all six caught:
1. `#pm` ignored;
2. the page opening on PM with no hash;
3. a write on load;
4. the old Kits order;
5. "← Line PM" shown without `from=line`;
6. "← Line PM" going to `tempest_line.html` without `#pm`.

### Slice 2 — The SHEET → button (staff see it on merge)

- `tempest_line.html`: the map and the button in `bTask()`, as designed. Nothing else changes.
- Guard: the Line check with the 11 real rows stubbed. 8 buttons on PM, each to the right
  address with `?from=line`. None on the 3 placeholders and none on AM. A row renamed to
  another dish (670 → "Kit - Short rib") loses its button. "Kit - Dumpling" renamed to
  "Kit - Chicken & Dumpling soup" loses its button, and it never opens the wrong sheet.
  Manager mode still renames on a name tap, and the pill still flips. **A button tap sends no
  request.** Fails-when-it-should copies: a wrong address, a button on a placeholder, the name
  check removed.
- `docs/kits.md` "Adding a kit" gains one step: add the row id and its word to the Line map.
- **This merge puts the button in front of the PM line.** Stephen's check on the phone: the
  Line page → **PM SHIFT** → **SHEET →** on Pork belly → the sheet → **← Line PM** → back on the
  PM list. Then the same with the back swipe.

### Slice 1 phone check (Stephen, 2026-11-19)

Passed: the Kits list starts with Mac & cheese in the new order; Pork belly's top link says
"← All kits" and returns to the list; opened with `?from=line` it says "← Line PM" and lands on
the PM SHIFT list with Kits at the top; Tempest Line from the home page still opens on AM.

### Slice 2 as built (2026-11-19, live as #191)

**`tempest_line.html`** — `KIT_SHEETS`, the 7-entry map above (comment: matched to Line PM
2026-11-16, pointing to `docs/kits.md` "Adding a kit"), and `kitSheetLink(it)`, which returns
`<a class="link-btn kit-sheet-link" href="tempest_kits.html?from=line#<slug>">SHEET →</a>`
only for a mapped kits row whose name passes the word check, with an `onclick` that only stops
the tap travelling (no request). `bTask()` appends it to the line that closes the name column,
after `#ni<id>`, so `saveN()`'s `previousElementSibling` is still the name; every other row's
HTML is unchanged. One page-only rule: `.kit-sheet-link` 44px tall, `inline-flex`, small top
margin. Print: `kitchen.css` already hides `.link-btn`. No class renamed, no `api()` touched.

**Hand check** (local copy, real data, read-only, Stephen's Chrome): 7 buttons on PM, right
addresses, none on 673/675/676/677; at 390px each 44px tall and inside its row; SHEET → on
Pork belly → the sheet with "← Line PM" → back on PM; the browser's back button too; AM has
none.

**`scripts/check_line.py`** — fixtures re-read 2026-11-16. New scenarios: `pm` (exactly 7, in
order, exact addresses, no target, none on 673/675/676/677 or the non-kit row, every
`#ni<id>` still after its `.task-name`), `phone` (page pinned to 390px because headless Chrome
won't open a window under 500; kitchen.css has no breakpoint between: each button ≥44px and
wholly inside its row, not clipped), `renamed` (670 "Short rib", 678 "Chicken & Dumpling
soup" lose theirs), `mgr` (manager mode via localStorage, never the PIN: SHEET tap sends
nothing, opens no rename box, flips no pill, ticks no box; the pill still makes one refused
POST to `prep_logs` with `mode:'make'`; the name still opens `#ni670`), `staff` (SHEET tap
sends nothing). Load requests in every scenario: GETs only, the four tables.
**154 assertions, 6 scenarios, clean.** The `mgr` scenario taps the pill before the name: with
the rename box open, the pill's redraw blurs it and saves the name, which is how the page
always behaved.

**`check_kits.py`** clean (515 / 22); **`check_styling.py`** clean (15 pages, 102 inputs
measured, 75 on the #135 register).

**Fails when it should** (scratch copies, never the worktree) — all nine caught: a wrong
slug; `?from=line` dropped; a button on 677; a button on 673; the name check removed; the
button inside `.task-name` (phone check fails); the button between `.task-name` and its input
(sibling check fails); an `api()` call in the `onclick`; a button on AM.

---

## Constraints

- `tempest_line.html` is live in every service. Touch only `bTask()`'s kit branch, the map,
  and the `#pm` open. Rename no class, and change no `api()` call. The guard proves nothing is
  written.
- Never write to the database. Read-only GETs only, no test rows.
- No inputs added, so #135 can't happen here.
- The Kits page and `kitchen.css`: no `:root`, no hue, never rename a class the JS reaches for.
- Never write the manager PIN or site password anywhere. Grepping Line prints them, so filter
  with `grep -v -i 'pin\|password'`.
- Ask before every push, PR and merge.

## Later — not this plan

- ~~**Kits menu update — the next ticket:** add Suadero and Chilorio sheets, remove Spicy green
  sauce, and map 675/676.~~ **Done** in the Kits menu update PR (`docs/kits.md` "Menu update as
  built").
- **Ticks** on the sheet (decided against for now; needs a table).
- **A kit-id column on `prep_items`**, so managers can link a new kit without a code change.
  Worth it once kits change often.
- **The Kits order following Line PM automatically** (needs the Kits page to read
  `prep_items`).
