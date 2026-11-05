# Menu Builder — what a draft dish might cost (B7)

Status, 2026-11-05: **the Recipe Costing plan was approved 2026-11-02**, and the planner re-checked
everything this plan leans on against it (see "Re-check", below — **all hold**). **Slices 0a and 1
are live** (PR #170, unlinked, phone-tested with Stephen's first real dish). **Slice 0b** (the lines
table) is being built now. **Slice 2** (lines on the page, with costs) waits for the costing window's
Slices 2 and 3 to be merged to `main`. Every row of "Decisions" is Stephen's; the design choices made
without asking are under "Decided in planning, not asked" so they can be overruled. Worktree
`~/Developer/boxkitchen-menu`, branch `menu-builder`.

Target file: a new page, `tempest_menu_builder.html`, copied from `tempest_costing.html` as its
template (manager-PIN gate, `api()` with its timeout), loading the shared
`assets/recipe-math.js` (created by the costing work, never edited from here), and a new
`scripts/check_menu_builder.py`.

**Approved by Stephen 2026-11-02** ("everything looks good"). Slices 0a and 1 start now; the rest
waits for the costing plan's approval (see Slices). Planned in one window, built in another.
At the very end, and only then: the home-page tile in `index.html`, `BUILD_PLAN.md` and
`CLAUDE.md`.

- **The Recipe Database, the Recipe Costing page, and their tables are never written to.** This
  page *reads* the price list (`ingredient_costs`, `order_items`) and the recipe list (`Recipes`),
  and later Recipe Costing's tables, and writes only its own two tables.
- **`assets/kitchen.css` is not expected to change.** The tap-to-pick list (`.pick-filter`,
  `.pick-list`, `.pick-row`), the list rows (`.ing-row`) and the yellow highlighter
  (`.ing-pack.unset`) are already in it.

---

## What it is for

R&D. While a dish is coming together, Stephen builds a rough draft of it here — what goes on the
plate, and how much — and gets a **good estimate of what it would cost and what to charge**,
before anything is written into the real recipe library. A dish may never make the menu, which is
why it lives apart.

When a dish does make the menu, Stephen moves it into the Recipe Database by hand. A "move to
real recipes" button may come later, so a draft line is shaped the way Recipe Costing shapes a
recipe line.

---

## Decisions — Stephen, 2026-11-02

| question | decided |
|---|---|
| What can a draft line be | **A raw ingredient** from the price list, at its live price; or **a house recipe** (*2 oz of the aioli*) — its cost comes from Recipe Costing once that exists; until then Stephen **types an estimate for that line**. |
| An ingredient not bought yet | **A typed name and a guessed price**, and the line is **marked as a guess**. |
| Price and food cost | **Both directions.** Enter a menu price → see the food cost %. Set a target % → get a suggested price. |
| Target food cost % | **26–28%** — a range, not one number. Every new dish starts at 26–28; any one dish can change its own. |
| Suggested price rounding | **To the half dollar, rounded inward** — the bottom of the range up, the top down — so every price shown really lands in the range. |
| Who can use it | **Manager PIN only** — the whole page. |
| When a dish makes the menu | **Moved by hand for now.** A button may come later, so draft lines match Recipe Costing's line shape. |
| Versions | **None side by side.** One dish, edited as the R&D goes — lines added and removed. |
| Status per dish | **Yes: Idea → Testing → Ready → Dropped.** Dropped dishes are hidden, never deleted, and can be brought back. |
| Menu view | **Yes, and it is the page's main list**: every draft on one line — status, plate cost, menu price, food cost %. Dropped dishes stay hidden from it. |
| One plate or a batch | **Both, with one box: "Makes __ plates"**, 1 unless changed. Type one plate's amounts, or a whole pot and the number of plates it makes. |

### Decided in planning, not asked — overrule any of these

- **The app never picks an ingredient for you.** The costing page's first rule, carried over: the
  picker starts with nothing selected; a line is linked by a person's tap on a row that shows the
  vendor. **Change** clears the pick *and* the amount.
- **A line is typed as boxes, not as a sentence.** Amount, unit, then what it is, plus an optional
  prep note (*sliced thin*). The line's words — *2 oz Roasted garlic aioli, sliced thin* — are
  made from the boxes, so the words and the numbers can never disagree. (Recipe Costing reads
  amounts out of a cook's text because its recipes already exist as text; a draft starts empty.)
- **A guess is a price for an amount** — *$14 for 1 lb* — stored the same three ways a real price
  is (pack amount, pack unit, pack price), so it goes through exactly the same math. The line's
  amount must be the same kind of measure as the guess (ounces against a per-pound guess is fine;
  cups against a per-pound guess is not, and the page says *type the guess in cups or the amount in
  weight*). No conversions of its own.
- **A house recipe's typed estimate is that line's total**, as Stephen said. Changing the line's
  amount highlights the estimate (*amount changed — check your estimate*) until it is saved again,
  so a 2 oz estimate is never silently kept for 4 oz.
- **No typed estimate on a raw-ingredient line.** One that needs a conversion (*1 cup diced
  onion*, onions bought by the lb) is typed in the price's kind of measure (*5 oz onion*), or gets
  a conversion added **on Recipe Costing** (a link there, not a second door) once that exists.
  Allowing estimates here would be a second, unofficial way of costing a real ingredient.
- **An incomplete dish says "at least".** Lines not yet costed can only add cost, so a dish with
  one uncosted line shows *at least $3.85 a plate · at least 27.5%*, and says which line and why.
  Its suggested price says *at least* too.
- **Soft numbers are named.** A total built on a guess, a typed estimate, or (later) an estimated
  conversion or yield from Recipe Costing says so — *includes 1 guess, 1 estimate* — and names
  the lines.
- **"Not costed on purpose"** — salt to taste, water, a garnish of herbs already on the line — can
  be marked like on Recipe Costing. It does not make a dish incomplete; the total says how many
  were skipped.
- **Removing a line hides it** (`active = false`), as the site removes things everywhere. Nothing
  is ever hard-deleted, and no new table has a delete policy.
- **Lines stay in the order they were added.** No drag-to-reorder in v1.
- **The menu view sorts Ready, then Testing, then Idea**, by name within each. **Show dropped
  (N)** reveals the hidden ones, each with **Restore**.
- **The tile goes in the Admin group**, beside Recipe Costing, Inventory and Flash — the other
  manager-only pages with money on them. Settled at the last slice, because Kits and Schedule add
  tiles too.
- **Page name `tempest_menu_builder.html`; tables `menu_drafts` and `menu_draft_lines`;
  `BUILD_PLAN.md` item B7.**

---

## Ground truth — read-only, 2026-11-02

Read through PostgREST with the site's anon key. Nothing written.

### The price list — `ingredient_costs`, edited on `tempest_costing.html`

- Columns: `id, location, order_item_id, name, invoice_alias, pack_qty, pack_unit, pack_price,
  active, created_at, updated_at`.
- **166 rows, all active, all priced.** 160 are linked to an order-guide item; **6 are off-guide**
  (Philly roll, Tobiko arare, Coriander ground, Cheddar jack shred, Tomatoes 5x5, Spitzenburg
  apples).
- A price is stored **like a case label**: pack amount, pack unit, pack price. The page's only math
  is `unitCost()` = pack price ÷ pack amount. Example: Gouda (3504), 10 lb at $54.05 → $5.405/lb.
- Pack units: lb 80 (+2 spelled `Lb`), oz 23, each 17 (+1 `Each`), gal 10, bunch 10, 1/2 gal 5,
  fl oz 4, qt 3, can 3, ml 2, bottle 1, L 1, g 1, bag 1, dozen 1, pt 1. **Mostly weight and
  count**; recipes and plates are often volume. Bridging that is Recipe Costing's *conversions*.
- **A price shows the order guide's current name, not its own** (`nameOf()`), and is linked by
  `order_item_id`. The Orders page **reuses an id when an item is renamed** (2026-10-20: #270
  Heirloom tomato → Arrow cabbage, #267 Plouts → Dried cranberries), so a renamed item silently
  carries the old item's price under its new name. **Checked all 166 today: no saved name differs
  from its order item's current name.**
- `ingredient_price_history`: 168 rows (every price change, with invoice and date). Not needed
  here — costs follow today's prices.
- `order_items`: 280 rows, all `Tempest`.

### The recipe list — `Recipes`, edited on `recipe_dashboard.html`

- **55 recipes, 37 active.** Ingredients are one free-text box per recipe; nothing in it points at
  a price. (Detail in the costing plan's "Ground truth".)

### Tables that do not exist yet

`recipe_lines`, `ingredient_conversions`, `recipe_conversions`, `recipe_yields` (Recipe Costing's,
planned; `recipe_conversions` was not checked, as it was added to that plan after this read) and
`menu_drafts`, `menu_draft_lines` (this plan's) all return 404 today. **Until Recipe Costing is
built, a house-recipe line can only be costed by its typed estimate**, and a raw ingredient only
in the same kind of measure as its price.

---

## The spine

> **This number prices a dish before it is real. It may be rough, but it is never quietly
> wrong: every guess and estimate is named, every gap is listed, and the math is the same math
> Recipe Costing uses.**

1. **One math, not two.** Quantity → cost goes through Recipe Costing's units and `lineCost()`,
   unchanged. This page adds only what is its own: the dish total, "makes N plates", the food
   cost %, and the suggested price.
2. **Never a guess dressed as a fact.** Guess, estimate, *at least*, and *not costed — why* are
   always on screen. An uncosted line is never $0.
3. **The app never picks for you.** Every link is a person's tap.
4. **A link is to what was there when it was made.** If a linked price's name changes (the
   order-ID reuse), the price is retired, or a house recipe is renamed or deleted, the line stops
   counting and says so until a person looks.
5. **The real recipe library is never touched.** Read only.

---

## The design

### The main list — the menu view

```
┌───────────────────────────────────────────────┐
│ ← Home     Tempest MENU BUILDER      Manager ●│
│ [ Filter dishes…                            ] │
│ 3 drafts · target 26–28%      [ ＋ New dish ] │
├───────────────────────────────────────────────┤
│ Chicken & Dumpling                     Ready  │
│   $2.95 plate · $12.00 · 24.6% · under        │
│ Winter Squash Melt                   Testing  │
│   $3.85 plate · $14.00 · 27.5% · in range     │
│   includes 1 guess                            │
│ Pork Belly Bao                          Idea  │
│   at least $4.10 plate · no menu price yet    │
│   suggested at least $15.00–$15.50            │
├───────────────────────────────────────────────┤
│ Show dropped (2)                              │
└───────────────────────────────────────────────┘
   (figures are illustrations, not data)
```

### One dish

```
┌───────────────────────────────────────────────┐
│ ← Menu    Winter Squash Melt                  │
│ Status [ Idea | Testing | Ready | Dropped ]   │
│ Makes  [ 1  ] plates                          │
├───────────────────────────────────────────────┤
│ 1 each Bun · Birite                  $0.62    │
│ 3 oz Honeynut squash · Cooks                  │
│   no price yet — price it first   Price →     │
│ 2 oz Roasted garlic aioli    your estimate    │
│                                      $0.40    │
│ 1 oz Calabrian chili crisp           GUESS    │
│   guessed $18 for 1 lb               $1.13    │
│ Salt to taste          not costed on purpose  │
│                               [ ＋ Add line ] │
├───────────────────────────────────────────────┤
│ At least $2.15 a plate                        │
│ 1 line not costed (no price yet)              │
│ includes 1 guess, 1 estimate                  │
│ Menu price [ 14.00 ]  → at least 15.4% · under│
│ Target  [ 26 ]–[ 28 ]% → suggested ≥ $8.00    │
│ Notes [ …                                   ] │
└───────────────────────────────────────────────┘
   (figures are illustrations, not data)
```

- The status is the site's segmented toggle (`.filter-btn` shape). **Dropped** asks once, then
  returns to the list with the dish hidden.
- **Guess**, **your estimate**, **no price yet** and every other *not costed* reason use the yellow
  highlighter (`.ing-pack.unset`'s fill), never a colour of their own. *In range / over / under* are
  words. Nothing is green or red.
- **Price →** opens Ingredient Costs with its filter set to the item (the same link Recipe Costing
  uses). Coming back, or refreshing, picks up the new price.

### Adding or editing a line

1. **Amount** and **unit** (the unit box suggests the spellings Recipe Costing's units table knows).
2. **What it is** — the tap-to-pick list, filtered word by word, nothing picked:
   - **price-list items**, with vendor (unpriced ones listed as *no price yet — price it first*,
     not pickable);
   - **house recipes** — active ones from `Recipes`, labelled *house recipe*;
   - last: **✎ Not bought yet — type a name and a guess**, and **Not costed on purpose**.
3. Then, depending on the pick: a house recipe asks for **your estimate for this line ($)**; a
   guess asks for the **name** and **guessed price for an amount** (*$ __ for __ __*).
4. Optional **prep note**.

A guess line carries **Link to a real price**: once the item is on Ingredient Costs, this opens the
picker with the guess's name in the filter. A person taps the real item; the guess is cleared.

### How a line is costed

| the line is | its cost |
|---|---|
| a price-list item, same kind of measure as its pack | `lineCost(amount, unit, price row's pack values)` |
| a price-list item, different kind | *needs a conversion* — or, once Recipe Costing exists, `lineCost(…)` with its conversion, read only |
| a guess | `lineCost(amount, unit, the guess's pack values)`, marked as a guess |
| a house recipe, before Recipe Costing | the typed estimate, marked *your estimate* |
| a house recipe, after Recipe Costing, recipe complete with a yield | the recipe's cost, through `recipeCost()` and `lineCost()` — via the recipe's own conversion (`recipe_conversions`, M1) when the line measures it another way than its yield (*2 oz* of a sauce made by the quart) — see Slice 5; the typed estimate shown beside it for comparison |
| a house recipe, after Recipe Costing, recipe not complete | the typed estimate, plus *Recipe Costing: $X so far, N lines not costed* |
| not costed on purpose | nothing; counted as skipped |

**Not costed — never $0 — and says why**, using Recipe Costing's reasons where they apply (*no
price yet*, *needs a conversion*, *renamed — linked as Heirloom tomato, now Arrow cabbage —
check*, *price retired — relink*, *conversion no longer matches the price*), plus this page's own:
*no guess yet*, *no estimate yet*, *recipe renamed — check*, *recipe deleted — relink*, *type the
guess and the amount in the same kind of measure*.

### The numbers

- **Plate cost** = (sum of the costed lines, unrounded) ÷ *makes N plates*. Rounded only on
  screen.
- **Complete** when every active line is costed or skipped on purpose. Otherwise the plate cost,
  the %, and the suggested price all say **at least**.
- **Food cost %** = plate cost ÷ menu price × 100, shown to one decimal. *In range* when the shown
  value is between the dish's low and high target (inclusive), *over* above, *under* below — the
  comparison uses the shown value, so 28.0% never reads *over*.
- **Suggested price**: the low end is plate cost ÷ (high target ÷ 100), **rounded up** to the next
  $0.50; the high end is plate cost ÷ (low target ÷ 100), **rounded down** to the $0.50 below.
  Example: a $4.20 plate at 26–28% → $15.00 and $16.15 → **$15.00–$16.00**. If no half-dollar lands
  inside (a very cheap dish), the exact cents are shown with *no half-dollar price lands in
  26–28%*.
- **No menu price** → the % reads *—* and the suggested price still shows.

### Printing

The menu view prints as a plain table; a dish prints as its lines and numbers with every mark
(GUESS, your estimate, not costed) as a word, never a fill. Every modal is hidden under
`@media print`.

---

## Tables — SQL Stephen runs; nothing is created from a session

Two new tables, `location`-scoped like everything else. **`ingredient_costs`, `order_items`,
`Recipes` and Recipe Costing's tables are not altered.** The exact SQL is written in Slice 0,
after the costing plan is approved, because it copies that plan's line shape, `Recipes.id`'s type
and the RLS pattern (see the re-check list).

| table | one row per | columns |
|---|---|---|
| `menu_drafts` | draft dish | `id` (uuid, named by the page), `location`, `name`, `status` (`idea` / `testing` / `ready` / `dropped`), `makes_plates` (>0, default 1), `menu_price` (optional), `target_low` (default 26), `target_high` (default 28), `notes`, `created_at`, `updated_at` |
| `menu_draft_lines` | line of a draft | `id` (uuid, named by the page), `location`, `draft_id` → `menu_drafts`, `position`, `qty`, `unit`, then **exactly one of** `ingredient_cost_id` → `ingredient_costs` / `sub_recipe_id` / `own_name`; `skip`; `guess_pack_qty`, `guess_pack_unit`, `guess_pack_price`; `estimate_cost`; `linked_name`; `component`; `note`; `active`; `created_at`, `updated_at` |

Choices worth saying out loud:

- **Matches `recipe_lines` where it can**: `qty`, `unit`, one of `ingredient_cost_id` /
  `sub_recipe_id`, `skip`, `linked_name`, `component`, `active`. **Different on purpose**: a draft
  has no recipe text, so there is no `line_text` / `occurrence` key — promotion will compose the
  text from the boxes, then key each line to it. `own_name` + the three `guess_*` columns are the
  guess (a guess has no price row and must never get one); `own_name` alone with `skip` is a line
  not costed on purpose. `estimate_cost` is the typed line total for a house recipe. `component`
  is there so a promoted dish can carry part headers later; v1 does not show it.
- **The line check:** either `skip` with an `own_name` and no target, guess or estimate; or an
  amount (>0), a unit, and exactly one of `ingredient_cost_id` / `sub_recipe_id` / `own_name`;
  guess columns only with `own_name`; `estimate_cost` only with `sub_recipe_id`.
- **The page names each new row** (a uuid made in the browser) and saves with an upsert, so a retry
  after a lost answer finds the same row instead of making a second — the costing page's Slice 4
  lesson, done the way Inventory and Recipe Costing do it.
- **`ingredient_cost_id` is a foreign key** (price rows are retired, never deleted). **`sub_recipe_id`
  is not**: a draft must never stop the Recipe Database deleting a real recipe. If the recipe is
  gone, the line says *recipe deleted — relink*.
- **RLS:** select / insert / update for `anon, authenticated`, no delete — the site's pattern,
  copied from what the costing plan's Slice 0 query finds.

---

## Where the math lives

**Not here.** Units, `lineCost()` and `recipeCost()` live in the shared file
`assets/recipe-math.js` (M5, approved 2026-11-02), under the single name `RecipeMath`, written to
the contract in the costing plan's section "What Kits, Inventory and Menu Builder can rely on".
This page **loads** it — `assets/recipe-math.js?v=N`, with the same `?v=` as every other page that
loads it — and **never edits it**. If Menu Builder ever needs the shared math to change, that
change goes through the costing plan and `scripts/check_recipe_math.py`, not through this window.

**This page's own math** — `dishCost()` (sum, skipped, reasons, soft inputs, ÷ plates, complete or
*at least*), the food cost %, the in-range test, and the half-dollar suggested range — sits on top,
as pure functions **in the page**, checked to the cent in `check_menu_builder.py`. It is kept out
of the shared file on purpose: no other page needs it yet, and every change to the shared file
bumps `?v=` on every page that loads it. If the costing plan's next plan — plate cost for real
menu dishes (D16) — needs the same numbers, they move into the shared file then.

---

## Re-check when the costing plan is approved

**Done 2026-11-05** by the planning window, against the approved costing plan and the live
database (read-only). **All hold**; the only changes are the column types and RLS details now in
Slice 0b. Results are in the second table below.

Every place this plan leans on `recipe-costing.md` (plan v1 as of 2026-11-02, with its Menu Builder
section). If any of these changes in the approved version, this plan changes with it before Slice 0.

| # | what this plan relies on | where in the costing plan | if it changes |
|---|---|---|---|
| D1 | **M5 — the math in one shared file**, `assets/recipe-math.js`, one name `RecipeMath`, loaded with `?v=N`; its check `check_recipe_math.py` confirms every page loading it uses the same `?v=` — which will include this page. **Approved 2026-11-02.** | Where the math lives; M5 | If reversed → a copy here plus an agreement check; "Where the math lives" above is rewritten |
| D2 | **M1 — a house recipe can have its own conversion** (*1 qt aioli = 2.1 lb*), in its own table `recipe_conversions`. **Approved 2026-11-02.** | M1; Tables; Slices 5–6 | If reversed → a house-recipe line must be typed in its recipe's yield kind (a quart-yield aioli only as *fl oz* or *cups*, never *2 oz*), or it stays on its typed estimate |
| D3 | **The math contract, items 1–5**: units table only; `lineCost()` takes **values**, looks nothing up, returns unrounded cost or a reason, and names the soft inputs; `recipeCost()` never returns nothing for an incomplete recipe; rounding only on screen; depth 6 counted from the caller | Menu Builder section, contract 1–5 | Guesses, *at least*, and the estimate fallback all rest on these |
| D4 | **A recipe's cost can be handed to `lineCost()` like a price** — yield amount, yield unit, batch cost — so *2 oz of aioli* is costed by the same function as *2 oz of mayo* | How a line is costed, rule 5; contract 2–3 | If recipe lines use a different path, Slice 5 calls that instead — still never a second version |
| D5 | **The units table exactly**: `oz` always weight; `#` = lb; dozen = 12 each; other count words convert only to themselves | Units | The unit box and the guess check follow it |
| D6 | **The reasons a line is not costed**, and their wording | How a line is costed, reasons table | This page reuses the words; its own reasons are listed above |
| D7 | **`recipe_lines`' shape**: `qty, unit, ingredient_cost_id / sub_recipe_id / skip, linked_name, component, active` | Tables | `menu_draft_lines` copies it before its SQL is written |
| D8 | **`ingredient_conversions`, `recipe_conversions` and `recipe_yields`** — names and columns, read here in Slice 5 | Tables | Slice 5's reads follow |
| D9 | **`Recipes.id`'s type and the RLS pattern**, from its Slice 0 read-only query | Slice 0 | This plan's SQL uses the same type and policies |
| D10 | **One door**: only Recipe Costing writes its tables; a missing conversion here is a *link* to Recipe Costing | Menu Builder section | If a second writer is ever allowed, this page still doesn't take it without a new decision |
| D11 | **The Recipe Costing page's address** (`tempest_recipe_costing.html`) and how to open it at one ingredient | Target file; Slice 7 | The *add a conversion* link follows |
| D12 | **Manager mode carries across** via `sessionStorage['boxkitchen_mgr']` | Decided in planning | This page reads the same key, so the PIN is asked once |
| D13 | **The costing plan's slice order**: the shared file starts in its **Slice 2** (units, amount reader); `lineCost()` is added in **3**; conversions in **4**; yields, totals and recipe conversions in **5**; recipes inside recipes in **6** | Slices | This plan's Slice 2 waits for its Slice 3 to be merged to `main`; this plan's Slice 5 waits for its Slices 4–6 to be live |
| D14 | **Archived recipes**: left out of lists; one already used still costs, labelled *archived* | Decided in planning | This page's house-recipe list behaves the same |
| D15 | **Promotion later**: composing the recipe text first; a guess can't be promoted until priced; a promote button is a second writer of `recipe_lines` | Menu Builder section, line shape | Out of scope now; the button needs a change to both plans |
| D16 | **Its "next plan" — plate cost for real menu dishes** | What it is for; Out of scope | That plan and this page cost the same thing (a plate). Plan them together; a *Ready* draft is the natural seed of a real menu dish |

**Re-check results, 2026-11-05:**

| # | result |
|---|---|
| D1–D6 | Unchanged in the approved plan: M5 (one shared `assets/recipe-math.js`), M1 (`recipe_conversions`), the math contract 1–5, a recipe costed through `lineCost()` like a price (rule 5), the units table, the reasons and their wording. |
| D7 | Holds. Live `recipe_lines`: `qty numeric`, `unit text`, `ingredient_cost_id bigint` → `ingredient_costs(id)` with no on-delete rule, `sub_recipe_id bigint` → `Recipes(id)` on delete restrict, `skip boolean not null default false`, `linked_name text`, `component text`, `active boolean not null default true`. Keyed by `(recipe_id, line_text, occurrence)` with a bigint identity id. `menu_draft_lines` copies these types. Different on purpose: a uuid id named by the page (as `menu_drafts`), no `line_text` / `occurrence`, and no foreign key on `sub_recipe_id` (D9). |
| D8 | Holds. `ingredient_conversions`, `recipe_conversions`, `recipe_yields` are live with 0 rows. Builder choices there: `from_kind` is `volume`, `weight` or the count word itself; a yield's and a portion's amount and unit are both set or both empty. Read here in Slice 5. |
| D9 | `Recipes.id` and `ingredient_costs.id` are both **`bigint` identity**, so both link columns here are `bigint`. **New and important:** `Recipes` has a live **delete policy**, so recipes really can be hard-deleted from the Recipe Database. That confirms `sub_recipe_id` gets **no foreign key**: a draft must never block a delete, and the page says *recipe deleted — relink* instead. RLS copies 0a as built. |
| D10–D12 | Unchanged. One door; the Recipe Costing page is `tempest_recipe_costing.html` (how to open it at one ingredient is not specified yet; settle in Slice 5); `boxkitchen_mgr` is already in use and phone-tested in Slice 1. |
| D13 | Unchanged order: shared file starts in costing Slice 2, `lineCost()` in 3, conversions 4, yields and recipe conversions 5, recipes inside recipes 6. **Status 2026-11-05:** costing Slice 0 closed (four tables live, 0 rows); costing Slice 1 built, local commit, not pushed; Slices 2–3 not started. So Menu Builder Slice 2 waits. |
| D14–D16 | Unchanged. |

---

## Slices

Seven, small, each reviewable in one sitting. The page stays **unlinked** — reachable only by its
address — until the last one. Every write path is proved against a stubbed `api()` before any phone
test.

**Split on 2026-11-02 (Stephen):** the dish part starts **before** the costing plan is approved,
because nothing in it depends on that plan. Slice 0 became **0a** (the dishes table, now) and
**0b** (the lines table, after approval). Slice 1 needs only 0a.

### Slice 0a — The dishes table *(no app code)* · **starts now**

- **The SQL** for `menu_drafts` alone: columns as in "Tables", checks, and RLS (select / insert /
  update for `anon, authenticated`, no delete — the pattern in `docs/inventory-guide-slice0.sql`),
  in one transaction, ending with a select that confirms the table exists with 0 rows.
  Dollar-quoted text. Proved first against a throwaway local Postgres: an upsert retry with the same
  id updating one row; delete refused; a bad status, plates ≤ 0, a menu price ≤ 0 and reversed
  targets each refused.
- Stephen runs it in the Supabase SQL editor and reports the confirming select.

**Done when:** `menu_drafts` exists (confirmed read-only, 0 rows) and RLS matches the site's pattern.

**As built — 2026-11-02.** `docs/menu-builder-slice0a.sql`, run by Stephen in the Supabase SQL
editor; confirming select `menu_drafts, 0`; PostgREST read-only `content-range: */0`; `pg_policies`
shows exactly select / insert / update. One addition to the ticket: Supabase's default privileges
grant ALL on new tables, so the script `revoke all` then grants select / insert / update — delete is
refused by the missing grant as well as the missing policy (Inventory's tables keep the default
delete grant and rely on the policy alone). Proved first on a throwaway `pgserver` Postgres with
Supabase-like roles and default privileges: same-id upsert twice → one row, updated; delete as
`anon` refused; `status='done'`, plates 0, price 0, targets 30–26, target 100, blank and null name
each refused. Gotcha: copying the SQL out of the terminal mangled a line (*syntax error near "st"*);
hand Stephen SQL with `pbcopy < file`, never from scrollback.

### Slice 0b — The lines table *(no app code)* · waits on costing-plan approval

- Re-check D1–D16 against the approved costing plan; update this document.
- **The SQL** for `menu_draft_lines`: keys, checks, the foreign key to `ingredient_costs`, and RLS,
  proved first against a throwaway local Postgres: a line with two targets refused; a guess on a
  price-list line refused; an estimate on a raw line refused; an upsert retry updating one row;
  delete refused; a price row a draft line uses cannot be deleted.
- Stephen runs it and reports the confirming select.

**Done when:** `menu_draft_lines` exists (confirmed read-only, 0 rows) and RLS matches.

### Slice 1 — The page, the dishes, the status *(new page, unlinked)* · needs only 0a

- `tempest_menu_builder.html`, copied from `tempest_costing.html`: the PIN gate (reading the shared
  manager-mode key), `api()` with its timeout.
- The menu view (names, statuses; costs read *—* until Slice 2). **＋ New dish**, rename, status
  toggle, *Makes __ plates*, menu price, targets (26–28 to start), notes. **Show dropped (N)** and
  **Restore**.
- The write path as costing's Slice 4 left it: every control disabled in flight, a timeout, and an
  upsert on the page-named id so a retry cannot duplicate.

**Done when:** a dish can be made, renamed, moved through every status, dropped and restored; a
dropped response cannot make two dishes; nothing is ever deleted — all against a stubbed `api()`.

**As built — 2026-11-02.** `tempest_menu_builder.html`, unlinked (no tile). Copied from
`tempest_costing.html`'s head, gate and `api()` (which gained a `prefer` argument for the upsert).
- **Screens:** the dish screen is a modal (`#dishModal`, *← Menu* closes it), so print hides it with
  every other modal. List rows reuse `.ing-row` / `.ing-pack` / `.uc`; status toggle reuses
  `.filter-toggle` / `.filter-btn`; filter reuses `.pick-filter`; errors reuse `.modal-err` (words)
  plus a 2px ink edge on the bad box. New classes, each with a `used by:` banner: `.dish-input`
  (qualified for 16px), `.dish-notes`, `.dish-inline`, `.dropped-bar`.
- **Second line of a row** reads `$14.00 · costs come later` / `no menu price yet · costs come
  later` (the ticket's wording, not the *—* above).
- **Write path:** `newUuid()` (randomUUID, getRandomValues fallback) is kept across retries until a
  create is confirmed; create = `POST ?on_conflict=id` with
  `resolution=merge-duplicates,return=representation`; edits and Restore = `PATCH id=eq.<id>` with
  `updated_at`, rendered from the returned row. `answerOf()` from costing: an `unknown` answer
  (no answer, 409, 5xx) re-GETs by id — a create found is opened; an edit is accepted only if the
  row matches what was sent. One write at a time page-wide (`busy`), every control disabled.
- **Drop** validates the form first, asks once, then saves every field with `status:'dropped'` and
  returns to the list.
- **Proved:** `scripts/check_menu_builder.py` — 17 scenarios, 223 assertions, stubbed stateful
  `menu_drafts` enforcing the table's checks and upsert rules; 16 guards removed one at a time in
  throwaway copies, each caught. Double-tap tests call `saveNew()` / `saveDish()` directly too,
  because a disabled button alone hid a missing busy guard. Phone width is simulated by narrowing
  `#app` (headless Chrome's layout viewport is 500px whatever `--window-size` says).
  `check_styling.py` clean, `FS_REGISTER` unchanged. Read-only render against live: 0 drafts, no
  writes. CI: `.github/workflows/menu-builder-guard.yml`, copied from Kits'.
- **Not yet:** Stephen's phone test and a read-back of his first real dish.

### Slice 2 — Lines from the price list · waits on the costing plan's Slice 3 (the math)

- ＋ Add line: amount, unit, pick a price-list item (tap-to-pick, word-by-word filter, vendor shown,
  nothing picked), prep note. **Change** clears the pick and the amount. Edit; remove (hide).
- **Not costed on purpose.**
- Same-kind lines cost through `lineCost()`; different-kind lines say *needs a conversion* (and,
  until Recipe Costing exists, *type it in lb*).
- The guards from day one: renamed price (`linked_name`), retired price, unpriced item not pickable.
- A plain running total: *at least $X a plate*, the reasons, skipped count.

**Done when:** no code path picks an ingredient; a renamed item and a retired price each stop a line
counting, with the reason; line costs match a hand calculation to the cent on fixtures; a dropped
response cannot make two lines.

### Slice 3 — Guesses and house recipes

- **Not bought yet**: name + guessed price for an amount, marked GUESS; the same-kind check; **Link
  to a real price**.
- **House recipe**: pick from active `Recipes`, amount, unit, *your estimate for this line*; the
  amount-changed highlight; *recipe renamed — check*; *recipe deleted — relink*.
- Soft inputs named on the total.

**Done when:** a guess costs through the same `lineCost()` as a real price (proved on a fixture
where the two give the same cent); an estimate is never kept silently across an amount change; a
deleted recipe stops its line counting.

### Slice 4 — The numbers

- *Makes N plates*; plate cost; complete vs *at least*; food cost % with *in range / over /
  under*; the half-dollar suggested range, rounded inward, with the no-half-dollar case.
- The menu view shows every dish's numbers.
- Print: the menu view and a dish, as plain lists with every mark as a word.

**Done when:** totals, %, and suggested prices match a hand calculation to the cent on fixtures
covering every line kind, a batch of 30, an incomplete dish, a dish at exactly 26.0% and 28.0%, and
a dish too cheap for a half-dollar price.

### Slice 5 — Hook up to Recipe Costing · waits on the costing plan's Slices 4–6 being live

- Raw lines that need a conversion use Recipe Costing's, read only; missing → a link to add it
  there.
- House-recipe lines use the recipe's real cost when it is complete with a yield (through its
  `recipe_conversions` row when the line measures it another way than the yield; missing → *needs
  a conversion*, with a link to add it on Recipe Costing); otherwise the typed estimate, with
  *Recipe Costing: $X so far*.
- Estimated conversions and yields carry up as soft inputs.

**Done when:** a dish using a complete house recipe costs to the cent the same as Recipe Costing
says for that amount; an incomplete one falls back to the estimate and says so; nothing is written
to Recipe Costing's tables.

### Slice 6 — Ship it *(shared files, last)*

- Bring the branch up to date with `main` first — the Kits, Schedule, Inventory and Costing windows
  all touch `index.html`.
- The home-page tile (Admin group); `BUILD_PLAN.md` B7; `CLAUDE.md` (the new page and the two
  tables).

**Done when:** Stephen reaches Menu Builder from its tile on his iPhone and builds a real draft.

---

## Out of scope

- **Side-by-side versions of a dish.** Stephen's call.
- **The "move to real recipes" button.** Later, and a change to the costing plan too (D15).
- **Cost history** — what a draft cost last week. Costs follow today's prices; a draft moves when
  an invoice is entered.
- **Writing anything** to `Recipes`, `ingredient_costs`, `order_items` or Recipe Costing's tables.
- **Pricing missing items.** Done on Ingredient Costs, as now; this page links there.
- **Conversions of its own**, for raw ingredients or guesses.
- **Reordering lines; part headers** (`component`) on screen.
- **Sharing drafts with staff.** Manager PIN only.

---

## Constraints

From `CLAUDE.md`, `docs/review-checklist.md`, and this window's rules:

- **The database is live. Never write test rows.** Read-only GETs are fine. Every write path is
  proved against a stubbed `api()` in `scripts/check_menu_builder.py`.
- **Only this worktree.** `index.html`, `BUILD_PLAN.md` and `CLAUDE.md` are touched in the last
  slice only.
- **`assets/recipe-math.js` is loaded, never edited, from here** — it belongs to the costing work
  and its own check. The page's `?v=` on it must match every other page that loads it.
- **`kitchen.css` unchanged if at all possible.** Reuse `.pick-*`, `.ing-*`, `.filter-btn`,
  `.modal`, `.save-bar`; page-only rules in the page's `<style>`. If it must change, bump `?v=` on
  every page — a collision with every other window.
- **No `:root`, no redeclared core token. Class names are load-bearing** — add, never rename; new
  classes carry a `used by:` banner.
- **No input below 16px.** A new input in a modal is written qualified —
  `.modal input[type="text"].your-class,.your-class{… font-size:16px …}` — or it renders at
  15.2px and zooms iOS (#135). `FS_REGISTER` in `check_styling.py` must not grow. (The guard finds
  new pages by itself — it reads `*.html`.)
- **State is fill, weight and border, never hue.** GUESS / estimate / not costed = the yellow
  highlighter; *over* is a word, not red.
- **`python3 scripts/check_styling.py`** before every PR (it needs Chrome).
- **Never write the manager PIN or the site password** in this document, a PR, or a comment.
- **SQL text is dollar-quoted.** Stephen runs all SQL himself.
- **Ship steps** (`.claude/skills/ship/SKILL.md`) apply, **except step 4**: this worktree is already
  on its own branch; never create or switch branches here. **Stop before every push.**

---

## Risks

| risk | why it matters | mitigation |
|---|---|---|
| The costing plan changes after this is written | This page is built on its math and line shape | The re-check list (D1–D16); Slice 0 re-reads it before any SQL |
| Waiting on Recipe Costing | Slice 2 can't start until the math exists | Slices 0–1 don't need it; Slice 5 is the only part that needs Recipe Costing *live* |
| A renamed order item carries an old price into a draft | A dish quietly costs cabbage at tomato prices | `linked_name` on every line; the line stops counting until a person looks |
| Estimates and guesses read as facts | A dish gets priced on a number nobody checked | Every soft number named, on the line and on the total; *at least* when incomplete |
| A typed estimate outlives its amount | 2 oz estimate kept for 4 oz | The amount-changed highlight until re-saved |
| `oz` meant as fluid ounces | Soy at *4 oz* against soy sold by the gallon asks for a conversion | The units table's rule (oz = weight); the hint Recipe Costing shows when `oz` meets a volume price |
| Prices move overnight | Yesterday's 27% is today's 29% | Intended — that's the live estimate he asked for |
| `index.html` is shared by five windows | Two tiles landing at once collide | The tile is the very last step, after bringing the branch up to date |

---

## How to verify without touching live data

As in `docs/costing-bulk-entry.md` and `docs/inventory-guide.md`:

- **Stub `api()`** and assert on the payloads it is handed — the only way to prove the write path,
  dropped responses and the upsert key.
- **Render real price rows and recipes read-only, every write blocked.**
- **To the cent on fixtures**: every line kind, every reason, a guess beside a real price, a batch,
  the 26.0% / 28.0% edges, the no-half-dollar case.
- **Break it on purpose** and check the harness catches each break: $0 for an uncosted line; a
  rounded line summed; an estimate kept across an amount change; 28.04% (shown as 28.0%) reading
  *over*; a guess not marked.
- **The SQL against a throwaway Postgres** before Stephen runs it.
- **A phone test by Stephen**, with every keystroke named.

---

## Questions still open

**None.** M1 and M5, the two costing-plan questions this page depended on, were answered yes on
2026-11-02 (D1, D2). What remains is the costing plan's approval, then the re-check list.

**For the costing window, when it next edits its plan:** its Menu Builder section can now point
here, and this plan takes the first of its two options for a guessed ingredient — the guess is
typed in the measure the dish uses; Menu Builder keeps **no** conversions of its own.
