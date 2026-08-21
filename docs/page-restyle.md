# Page Restyle — carry the Expo Board look across the whole site

Status: **plan only, no code written.** Drafted 2026-08-21.
Worktree: `~/Developer/boxkitchen-page-restyle`, branch `page-restyle`, off live `origin/main` @ `5780efc`.

## The problem

`index.html` was rebuilt (PRs #98/#99/#100) into the approved "Expo Board in Chit colors"
look — paper background, black ink, yellow highlight, tomato accent, Barlow + Playfair.
Every other page is still the **old dark app**: near-black background, DM Sans, saturated
status colors. Tapping "Prep List" from the new home page drops you into what looks like a
different product.

Nine pages carry the old look. Measured on `origin/main`:

| Page | total lines | CSS block lines |
|---|---:|---:|
| tempest_orders.html | 1137 | 171 |
| tempest_prep.html | 969 | 161 |
| tempest_line.html | 962 | 160 |
| recipe_dashboard.html | 802 | 121 |
| tempest_flash.html | 644 | 117 |
| tempest_portion.html | 481 | 102 |
| tempest_meat.html | 481 | 102 |
| tempest_costing.html | 434 | 95 |
| tempest_notes.html | 418 | 88 |
| **total** | **5328** | **1117** |

Every page carries its **own inline `<style>` block**. There is no shared stylesheet.
That duplication is the whole reason this is a project rather than a one-line change.

Two pairs are near-twins, which the slicing exploits:
- `tempest_portion.html` / `tempest_meat.html` — CSS blocks are **byte-identical** (0 differing lines).
- `tempest_prep.html` / `tempest_line.html` — 21 differing CSS lines; same structure otherwise.

## The palette gap

Old (all nine pages):

    --bg:#0f1115  --surface:#1a1d24  --surface2:#22262f  --border:#2a2d35
    --text:#e8e6e3  --muted:#8a8a8a  --dim:#555
    --accent:#e85d3a  --green:#22c55e  --yellow:#f59e0b  --blue:#3b82f6
    --red:#ef4444  --purple:#a855f7
    font: DM Sans + Playfair Display

New (`index.html`):

    --paper:#fbfaf6  --ink:#121212  --grey:#6a6a6a  --hair:#e2e0d8
    --faint:#a9a7a0  --dash:#b8b6ae  --yellow:#ffe600  --tomato:#e85d3a  --press:#f3f1ea
    font: Barlow + Barlow Condensed + Playfair Display

**The important difference is not the colors — it's how state is expressed.** The old pages
say "done" with green and "urgent" with red. The new home page says it with **fill, weight,
and border**: a filled ink dot means done, a yellow dot means due, a hollow dot means
nothing scheduled, and `<mark>` puts a yellow highlighter behind the words that matter.
The new look has essentially one accent (tomato) and one highlighter (yellow).

So this is a translation job, not a find-and-replace. Proposed mapping:

| Old | New | Note |
|---|---|---|
| `--bg`, `--surface`, `--surface2` | `--paper` + hairline borders | new look uses outlines, not fills |
| `--border` | `--hair` | |
| `--text` / `--muted` / `--dim` | `--ink` / `--grey` / `--faint` | |
| `--accent` (tomato) | `--tomato` | **unchanged — same hex** |
| `--green` (done/success) | filled `--ink` | done = solid, not green |
| `--yellow` (warning/due) | `--yellow` #ffe600 | brighter; use as highlighter behind text |
| `--red` (urgent/destructive) | `--tomato` | |
| `--blue`, `--purple` (category tags) | **kept** — retuned for paper | **REVISED 2026-08-21** — see decision 1 |

## Decisions — settled 2026-08-21 by Stephen

1. **Category colors: KEPT.** *(Revised 2026-08-21 — supersedes the earlier "typographic
   labels" call.)* Notes keeps its per-category colour coding; the colour-scan is worth more
   than palette purity. The category still also carries a Barlow Condensed uppercase label,
   so colour is reinforcement, not the only signal.
   **Translation required:** the existing hues (#ef4444 red, #f59e0b amber, #3b82f6 blue)
   were chosen against a near-black background. On cream they will read differently and may
   need darkening/desaturating to hold contrast. Keep the *coding*, retune the *values*, and
   show Stephen on a phone before committing.
   **Scope:** decided for Notes. Orders (slice 8) and Recipes (slice 5) have their own
   category colours — ask again when those slices come up rather than assuming this answer
   carries.
2. **Shared stylesheet: yes, adopted page by page.** `assets/kitchen.css` is created in
   slice 1 and each later slice converts one page to it and deletes that page's duplicated
   rules. No big-bang PR. Ends with one source of styling truth.
3. **Dark mode: out of scope.** Noted so it isn't rediscovered as a surprise — the old pages
   were dark and staff read them in a dim kitchen at 6am. If the bright paper look is a
   problem in practice, that's a separate project, not a reason to stall this one.

## Constraints (non-negotiable)

- **Merging is deploying.** This is the kitchen's live tool. Never merge during service.
- **One page per PR.** A restyle touching orders + prep + line at once is unreviewable and
  unrevertable in practice.
- **Restyle only — no behaviour changes.** No renamed IDs, no changed queries, no altered
  JS logic. If a page has a bug, it keeps the bug; log it, fix it separately.
- **The class names in the CSS are load-bearing.** JS on these pages does
  `classList.add('done')`, `querySelector('.modal')` etc. Renaming a CSS class silently
  breaks behaviour that no visual review will catch.
- Never `git add -A`. Stage the specific files.
- Site password and manager PIN are plain text in these files — never print or repeat them.

## Risk register

| Risk | Why it bites | Mitigation |
|---|---|---|
| Class rename breaks JS | Styling and behaviour share the class namespace | Never rename; only change rules. Grep each class in JS before touching it |
| Drag-and-drop breakage | prep/line/orders use SortableJS; it reads computed styles + inserts its own ghost/chosen classes | Restyle those three last, after the pattern is proven; test a real drag on each |
| Manager mode invisible | mgr toggle/PIN styling appears 19–44× per page | Test manager mode on every page before PR |
| Modal/toast unreadable | 5–25 modal refs and 5–37 toast refs per page, all styled for dark | Convert modal + toast once in the shared stylesheet, reuse |
| Contrast regressions | Old greys were tuned for a dark background; on paper they wash out | Check `--grey`/`--faint` against paper, not against the old dark |
| Kitchen confusion | Staff learned the dark screens | Ship in a quiet window; the look is already familiar from the home page |

## Verification for every slice

1. `git diff --stat` shows only the intended file(s).
2. `python3 -m http.server 8000` in the worktree; open on a phone over Wi-Fi (the real device).
3. Walk the page's actual jobs — not just look at it: check an item off, open the add
   modal, flip manager mode on, trigger a toast, and on prep/line/orders drag a row.
4. Confirm no console errors.
5. Compare side by side with `index.html` on the same phone — does it read as one product?

---

# Build slices

**Reordered 2026-08-21.** The first cut ordered by file size, smallest first. That was
wrong: the two smallest pages (Notes, Costing) are the only two whose tables are **empty**,
so they're the two you can't actually see restyled. Order is now by *reviewability* —
pages with real data first — with the operationally risky pages still late.

Row counts behind each page, measured 2026-08-21:

| page | rows |
|---|---:|
| notes | **0** |
| ingredient_costs (costing) | **0** |
| meat_items | 18 |
| Recipes | 47 |
| flash_days | 51 |
| portion_items | 66 |
| order_items | 277 |
| prep_items | 351 |

**One slice = one PR.** Each is buildable, reviewable, mergeable and revertible on its own.

### Gate 0 — decisions — **DONE 2026-08-21**
Shared stylesheet adopted page by page; Notes keeps its category colours (retuned for
paper). Orders and Recipes re-ask when their slices come up. Dark mode out of scope.

### Slice 1 — `assets/kitchen.css` + `tempest_notes.html` — ✅ **MERGED (#102)**
The foundation, proven on the smallest page (418 lines, 88 CSS lines, no drag-and-drop).
Creates `assets/kitchen.css` — tokens, font import, base rules, and only the components
Notes actually uses (modal, toast, manager toggle, spinner). Later slices add components as
real pages demand them; don't style speculatively.
**Caveat:** `notes` has 0 rows, so the page renders its empty state. Verification requires
creating test notes across all five categories **and deleting every one afterwards** — this
writes to the live production database and the kitchen's home tile displays them meanwhile.
**Delivers:** Kitchen Notes matching the home page + a stylesheet eight pages can adopt.
**Risk:** low visually, **high in influence** — every later slice inherits its decisions.

### Slice 2 — `tempest_portion.html` + `tempest_meat.html` — ✅ **MERGED (#103)**
66 and 18 real rows, so the restyle is actually visible. Their CSS blocks are
**byte-identical** — one job done twice; splitting them would mean reviewing the same diff
twice. No SortableJS. First real test that the stylesheet generalizes to pages it wasn't
written against.
**Delivers:** both count sheets restyled; gaps in `kitchen.css` found and filled.
**Risk:** low. **Done when:** a count saves on both, date arrows work, manager mode works.

### Slice 3 — `tempest_flash.html` — ✅ **MERGED (#105)**
644 lines, 117 CSS, 51 rows of real data. Dense numeric tables plus month/year report
views — first page where tabular-figure alignment and table styling matter.
**Delivers:** Flash Reports restyled, report tables included. `kitchen.css` gains a table block.
**Risk:** medium. **Done when:** save a day, switch month/year views, PIN gate intact,
numbers align in columns.

### Slice 4 — `recipe_dashboard.html` — ✅ **MERGED (#106)**
802 lines, 121 CSS, 47 recipes (36 active / 11 archived), 44 manager-mode references —
heaviest manager surface.
**Correction to the earlier plan:** there is no category-colour question here. Categories
render as a single grey chip for all 12 values, and stations as a single tomato chip for all
6 — no per-value hues exist to preserve. The real colour question is `.location-tag`
(see ticket).
**Two things make this page unlike every other:**
- **86 literal hex values and zero `var(--…)` uses.** Every other page is tokenised; this
  one hard-codes its colours inline. The restyle is a hex-by-hex hunt, not a token swap, and
  a single missed hex leaves a dark patch on a paper page.
- **It is the only desktop-first page** (40px gutters, auto-fill grid, one 600px breakpoint).
  Everything else is phone-first. Keep it working on both.
**Delivers:** recipe dashboard restyled.
**Risk:** medium-high — raised from medium because of the 86 hard-coded hexes.
**Done when:** search/filter, archived toggle, and add/edit/archive recipes all work in and
out of manager mode.

### Slice 5 — `tempest_prep.html` — ✅ **MERGED (#108)**
969 lines, 161 CSS, 351 rows, **first SortableJS page**. Drag styling is the real work:
SortableJS injects its own ghost/chosen/drag classes and reads computed styles.
**Risk:** **high** — the page the kitchen uses most.
**Done when:** check items off on both shifts, add/edit/delete, drag to reorder, and the
new order survives a reload.

### Slice 6 — `tempest_line.html` — **IN PROGRESS**
962 lines, 160 CSS; 21 CSS lines differ from prep. Applies the pattern slice 5 proved.
**Risk:** medium. **Done when:** same checklist as slice 5, plus the SUN–SAT dropdown renders.

### Slice 7 — `tempest_orders.html` — **split, too big as one**
1137 lines, 171 CSS, 277 rows, 25 modal references, 24 manager references, SortableJS.
Largest page, most modal-heavy, and where an order actually gets submitted.
- **7a — layout, typography, shelves, item rows.** The page reads correctly at rest.
- **7b — modals, manager mode, drag affordances.** The interactive surfaces.
**Category colours: ask Stephen before 7a.**
**Risk:** **high** — a broken order guide means an order doesn't reach Birite.
**Done when:** build an order, submit it, view a previous order, move an item between
shelves, drag to reorder, manager mode behaves — all on a phone.

### Slice 8 — `tempest_costing.html` — **last, deliberately**
434 lines, 95 CSS. Moved from second to last: `ingredient_costs` and
`ingredient_price_history` are **both empty**, so this page can only be restyled blind
against its empty state. Doing it last means the pattern is fully proven by then and
blindness costs least.
**Separate question for Stephen, not part of this slice:** an unused costing tool is either
a data-entry job or a feature to retire. Worth deciding before spending review time on it.
**Risk:** low. **Done when:** the page renders correctly and the PIN gate still gates.

### Slice 9 — consistency sweep
Delete leftover duplicated rules, confirm no page still imports DM Sans or references a
dead `--surface`/`--green`/`--blue`, and walk the whole site on one phone looking for drift.
**Delivers:** one coherent product; `kitchen.css` as the single source of styling truth.
**Done when:** grep finds no old tokens and no page feels foreign.

## Verifying a page with no data — standing rule
Notes (slice 1) and Costing (slice 8) render empty. Any test rows created to review styling
go into the **live production database** and are visible to the kitchen immediately. Create
the minimum needed, delete every one before opening the PR, and confirm the home page tile
has returned to its empty reading. Never do this during service.

## Sizing note
Nine slices, ten PRs (7 splits). Slice 7 was the only one clearly oversized and is split.
Slice 1 is not the biggest but is the one worth slowing down on — every later slice
inherits whatever it decides. Slices 5 and 7 carry the real operational risk; both sit late
deliberately, after the pattern is boring.
