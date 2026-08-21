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

Ordered smallest-and-safest first, so the pattern is proven on a page nobody's shift
depends on before it reaches the pages that run service. **One slice = one PR.**

Each slice is written so it can be built, previewed, reviewed and merged on its own, and
reverted on its own if it lands wrong.

### Gate 0 — decide the open questions — **DONE 2026-08-21**
Both answered by Stephen: typographic category labels, and a shared stylesheet adopted
page by page. See "Decisions" above. Slice 1 is unblocked.

### Slice 1 — `assets/kitchen.css` + convert `tempest_notes.html`
The foundation, proven on the smallest page (418 lines, 88 CSS lines, no drag-and-drop).
Create `assets/kitchen.css` holding the `:root` tokens, the font import, and base rules
(body, header, buttons, inputs) **plus only the components notes actually uses** — modal,
toast, manager toggle. Don't speculatively style components no page has needed yet; later
slices add them as real pages demand them.
**Delivers:** Kitchen Notes looks like the home page, and a stylesheet the other eight
pages can adopt. **Files:** `assets/kitchen.css` (new), `tempest_notes.html`.
**Risk:** low visually, **high in influence** — every later slice inherits these decisions.
**Done when:** notes reads as one product with the home page; add/edit/delete a note,
manager mode, and a toast all still work.

### Slice 2 — `tempest_costing.html`
Second-smallest (434 lines, 95 CSS). No SortableJS. First real test that the stylesheet
generalizes to a page it wasn't written against.
**Delivers:** Recipe Costing restyled; any gaps in `kitchen.css` found and filled.
**Risk:** low. **Done when:** costing calculations display correctly, PIN gate still gates.

### Slice 3 — `tempest_portion.html` + `tempest_meat.html` (both, one PR)
Their CSS blocks are **byte-identical**, so this is genuinely one job done twice. Splitting
them would mean reviewing the same diff twice.
**Delivers:** both count sheets restyled. **Files:** two.
**Risk:** low. **Done when:** a count saves on both, the date arrows work, manager mode works.

### Slice 4 — `tempest_flash.html`
644 lines, 117 CSS. Dense numeric tables plus the month/year report views — the first page
where tabular-figure alignment and table styling matter.
**Delivers:** Flash Reports restyled, including its report tables.
**Risk:** medium — tables are new styling territory; `kitchen.css` will gain a table block.
**Done when:** save a day, switch month/year views, PIN gate intact, numbers align.

### Slice 5 — `recipe_dashboard.html`
802 lines, 121 CSS, 44 manager-mode references — the heaviest manager surface in the app.
**Delivers:** recipe dashboard restyled.
**Risk:** medium. **Done when:** search/filter, category and station labels, and add/edit/
delete recipes all work in and out of manager mode.

### Slice 6 — `tempest_prep.html`
969 lines, 161 CSS, **first SortableJS page**. Drag styling is the real work: SortableJS
injects its own ghost/chosen/drag classes and reads computed styles.
**Delivers:** prep list restyled, drag-and-drop intact.
**Risk:** **high** — this is the page the kitchen uses most.
**Done when:** check items off on both shifts, add/edit/delete, reorder by dragging, and
confirm the reorder survives a reload.

### Slice 7 — `tempest_line.html`
962 lines, 160 CSS; 21 CSS lines differ from prep. Applies the pattern slice 6 proved.
**Delivers:** line list restyled.
**Risk:** medium (pattern already proven). **Done when:** same checklist as slice 6, plus
the SUN–SAT day dropdown renders correctly.

### Slice 8 — `tempest_orders.html` — **too big, split it**
1137 lines, 171 CSS, 25 modal references, 24 manager references, SortableJS. This is the
largest page and the most modal-heavy, and it is where an order actually gets submitted.
Split into:
- **8a — layout, typography, shelves and item rows.** The page reads correctly at rest.
- **8b — modals, manager mode, drag affordances.** The interactive surfaces.
**Delivers (8a+8b):** order guides restyled.
**Risk:** **high** — a broken order guide means an order doesn't go to Birite.
**Done when:** build an order, submit it, view a previous order, move an item between
shelves, drag to reorder, and manager mode behaves — all on a phone.

### Slice 9 — consistency sweep
With all pages converted: delete leftover duplicated rules, confirm no page still imports
DM Sans or references a dead `--surface`/`--green`/`--blue` variable, and walk the whole
site on one phone looking for drift.
**Delivers:** one coherent product; `kitchen.css` as the single source of styling truth.
**Risk:** low. **Done when:** grep finds no old tokens, and the walk-through finds no page
that feels foreign.

## Sizing note

Nine slices (ten PRs, since 8 splits). Slice 8 was the only one that came out clearly
oversized and it has been split above. Slice 1 is not the biggest but is the one most worth
slowing down on — every later slice inherits whatever it decides. Slices 6 and 8 carry the
real operational risk; both sit late deliberately, after the pattern is boring.
