# Recipe Costing — what a batch costs (B4.3)

Status: **plan v1, approved by Stephen 2026-11-02. Slice 0 is next.** No code written, no SQL run
yet. It is built in a separate window: this plan is owned by the planning window, the build window
records each slice "as built" here, and any change to the design goes back to the planner. Every
decision in "Decisions" was Stephen's, in the interview that produced this document. The design
choices made without asking are listed under "Decided in planning, not asked" so they can be
overruled. **Updated later on 2026-11-02:** Menu Builder added to "What Kits, Inventory and Menu
Builder can rely on", with the math contract it reuses; two choices that would make its job hard
(M1, M5) were flagged, and **both were approved by Stephen the same day and are folded in**: a
house recipe can have its own conversion, and the costing math lives in one shared file. Stephen
also confirmed what "portion" means and archived the duplicate Chicken and Dumpling (#52). Worktree `~/Developer/boxkitchen-costing`, branch `recipe-costing`.

Target files: a new page, `tempest_recipe_costing.html`, copied from `tempest_costing.html` as its
template; a new shared file, `assets/recipe-math.js` (M5), with its own check,
`scripts/check_recipe_math.py`; and `scripts/check_recipe_costing.py`. `CLAUDE.md` gets one line
corrected in Slice 2, when the shared file is created. At the very end, and only then: a
**Recipes** tab on `tempest_costing.html`, `BUILD_PLAN.md` (B4), and the rest of `CLAUDE.md`.

- **`index.html` is not touched** — the Recipe Costing tile already leads to the costing page.
- **`assets/kitchen.css` is not expected to change** (see Constraints).
- **The `Recipes` table and `recipe_dashboard.html` are not touched at all** (see "What Kits,
  Inventory and Menu Builder can rely on").

---

## What it is for

For every house recipe: **what one batch costs, and what one unit of it costs** — a quart of
aioli, a pint of pickled onions, one dumpling — worked out from the prices already in the
ingredient price list (`ingredient_costs`), and moving with them.

Two things wait on that number:

- **Inventory's prepared items.** The monthly count cannot value the aioli in the prep cooler
  until a quart of aioli has a cost (`docs/inventory-guide.md`, "Out of scope": *valued at recipe
  cost per yield unit from Recipe Costing (B4.3)*). Unvalued prep at month end makes the true
  food cost read high.
- **Plate cost** — what one order of a dish costs — is **the next plan**. A plate is portions of
  these recipes plus bought items, and it needs menu dishes and portion sizes, which exist nowhere
  on the site yet.

BUILD_PLAN B4 says costing "depends on recipes being complete". This plan does not wait for that:
a recipe is costed as far as it can be, and always says what is missing.

---

## Decisions — Stephen, 2026-10-28 → 2026-11-02

| question | decided |
|---|---|
| What should it tell you | **Batch cost and cost per unit of yield**, and per portion — a portion size set on each recipe, such as *2 fl oz of aioli* (confirmed 2026-11-02). Plate cost is the next plan. |
| How recipe amounts become money | **Recipes stay exactly as written.** Each conversion — "1 qt sliced shallots takes 0.8 lb of shallots" — is recorded **once per ingredient** and reused by every recipe. Changes within one kind of measure (cups → quarts, ounces → pounds) are automatic. A line with no conversion yet says *needs a conversion*, never a guess. |
| How yields get filled in | **"As we build the recipe and I see the correct yield and portions."** Recipes are set up one at a time, in the tool; the yield and portion are entered when Stephen sets that recipe up. No bulk fill-in. A yield can be marked *estimate*. |
| Where it lives, who sees money | **On the Recipe Costing page, behind the manager PIN**, as a second view beside the ingredient price list. The Recipe Database shows no money and is unchanged. |
| Can a house recipe have its own conversion (M1) | **Yes** — *1 qt Spicy Green Sauce weighs 2.1 lb* — so a portion, a dish, or another recipe can use it by a different measure than its yield. Raised for Menu Builder; decided 2026-11-02. |
| Where the costing math lives (M5) | **One shared file**, `assets/recipe-math.js`, loaded by every page that costs anything — this one, Inventory, Menu Builder — instead of a copy in each. Decided 2026-11-02. |

### Decided in planning, not asked — overrule any of these

- **A separate file that looks like a tab.** To Stephen, *Recipes* is a second tab on the Recipe
  Costing page. Underneath, it is its own file, so the price-entry page — six slices and more than
  ten review rounds of hardening — is touched only twice, both small (Slices 1 and 7). Manager mode
  carries across: the costing page stores it in `sessionStorage['boxkitchen_mgr']`, and the new
  page reads the same key, so moving between the tabs does not ask for the PIN again.
- **The app never picks an ingredient.** It may *read* `2 qt.` out of `2 qt. sliced shallots` and
  propose it, and it starts the picker's filter with `sliced shallots`; a person taps the
  ingredient. The costing page's first rule, carried over.
- **Conversions are "as bought".** The question is *"How much of what you buy does it take to make
  1 qt?"* — so peel, stems and trim are inside the number, and a quart of diced onion costs what
  the onions it took cost.
- **One conversion per ingredient per kind of measure** in v1: one for volume, one for weight, one
  per count word (clove, head, bunch). A quart of sliced shallots and a quart of whole shallots
  share one. Good enough to price a menu; recorded as a known limit.
- **Lines that cost nothing on purpose** — water, `Salt TT`, `pepper` — can be marked **not costed
  on purpose**. They do not stop a recipe being complete; the total says how many were skipped.
- **Recipes inside recipes are in v1.** Jang Aioli is 4 cups of aioli base and gochujang; it cannot
  be costed without them.
- **Archived recipes are left out of the list.** A recipe used inside another still costs if it is
  archived, labelled *archived*.
- **The rename guard comes first** (Slice 1), before any recipe links to a price.

---

## Ground truth — read-only, 2026-11-02

Read through PostgREST with the site's anon key. Nothing written. The same numbers were read on
2026-10-28; nothing had changed in between.

### The recipe library — `Recipes`, edited on `recipe_dashboard.html`

- **55 recipes, all `location = Tempest`: 37 active, 18 archived** (`status`).
- Columns: `id, name, category, station, yield_text, ingredients, method, location, status,
  created_at`. **Nothing in a recipe is structured.** `ingredients` is one text box, one line per
  ingredient, typed the way a cook writes: `2 qt. sliced shallots`, `1 bottle red wine`,
  `Salt TT`. Nothing points at the price list or the order guide.
- **Multi-part recipes** — 10 of 55; 5 active (Bread & Butter Squash, Dumpling, Fava Santorini,
  Mac & Cheese, Pickled Onion & Pepper) — keep their parts in the same box, separated by header
  lines such as `— CHEESE BASE —`. The Recipe Database's edit form shows the whole box as one
  block and saves it back as it was.
- **281 ingredient lines in the 37 active recipes:**

  | measured by | lines | e.g. |
  |---|---|---|
  | volume | 163 | `2 C Lentils`, `1½ Tbsp Salt`, `2 qt. sliced shallots` |
  | count | 75 | `10 ea Garlic clove`, `½ bunch Thyme`, `1 can chipotle chiles`, `3 inch ginger` |
  | weight | 16 | `5# Sweet onion`, `2.5 lb. Velveeta cheese`, `32 oz. soy` |
  | no amount | 27 | `Salt`, `Ribeye`, `pork or veg stock to cover`, `AP flour` |

- **One unit, many spellings:** `C` / `c.` / `cup` / `cups`; `Tbsp` / `TB.` / `Tb.`; `#` / `lb` /
  `lb.`; `ea` / `ea.` / `each`; `qt` / `qt.` / `quart`.
- **`oz` is ambiguous.** In Chili Lemongrass Dressing, `32 oz. soy` and `32 oz. water` are surely
  fluid ounces; Mac & Cheese's `8 oz. butter` is weight. The text cannot tell them apart.
- **Yields: 2 of 55** have anything in `yield_text`, and neither is a number: `4X batch` (Chili
  Lemongrass Dressing) and `2 skewers per order` (Duck Hearts, archived).
- **Recipes used inside recipes**, by name in the text: `aioli base` (Jang Aioli); `Aioli`
  (Horseradish Blue Cheese Dressing); `roasted garlic` (5: Horseradish Blue Cheese, Mac & Cheese,
  Ribeye, Roasted Garlic Aioli, Roasted Red Pepper Aioli); `mayo` (Mac Salad and both aiolis);
  `chicken stock` (both Chicken & Dumplings, Onion Soubise); Pork Belly's `cooking liquid
  (reserved from braise)`. **The library has no active aioli base or roasted garlic recipe** —
  Basil Aioli is archived, and Garlic Confit may be what "roasted garlic" means. Chicken Stock is
  on the price list, bought.
- **A likely duplicate:** *Chicken & Dumpling (Soup Base)* (#19) and *Chicken and Dumpling* (#52)
  are both active, with the same ingredients. Stephen chose #19 for Kits. **Stephen archived #52
  later on 2026-11-02** (confirmed read-only: #19 active, #52 archived), so active recipes are now
  **36**, with **268** ingredient lines. The counts above are as first read.
- The Recipe Database reads `select=*` with no location filter. In manager mode it adds, edits,
  archives, and hard-deletes (typed-name confirm).

### The price list — `ingredient_costs`, edited on `tempest_costing.html`

- **166 rows, all active, all priced**: 160 on order-guide items, 6 off-guide (Philly roll 8 in,
  Tobiko arare, Coriander ground, Cheddar jack shred, Tomatoes 5x5, Spitzenburg apples).
- A price is **pack quantity, pack unit, pack price**; unit cost = price ÷ quantity (`unitCost()`).
  Pack units in use: lb 82 (2 spelled `Lb`), oz 23, each 18 (1 `Each`), gal 10, bunch 10, 1/2 gal
  5, fl oz 4, qt 3, can 3, ml 2, bottle 1, L 1, g 1, bag 1, dozen 1, pt 1. **Mostly weight and
  count — while recipes are mostly volume.** That gap is what conversions are for.
- **A price shows the order guide's name, not its own.** `nameOf()` returns the order item's
  *current* name, and every edit re-saves the row's own `name` from the order guide. See
  "Order-ID reuse" below.

### Coverage — what the recipes use against what is priced

By name, by hand, so approximate:

- **Most recipe ingredients are already priced** — mirin, gochujang, Velveeta, mascarpone,
  guajillo, tahini, harissa, Old Bay, lemongrass, pork belly, ribeye, crème fraîche, buttermilk,
  shallots, peeled garlic, chicken stock, and so on.
- **13 are on the order guide but unpriced** — see the leftovers.
- **About a dozen are on neither the order guide nor the price list**: **olive oil** (in 10 active
  recipes), saltines, oyster sauce, Thai chili, serrano, tarragon, celery seed, fennel seed,
  turmeric, ground cinnamon, red wine, Jimmy Nardello peppers. Some are probably on the guide
  under another name (vegetable oil → *Soy bean oil salad*? cherry tomato → *Toy box tomato*?
  macaroni → *Elbow noodles*?); the rest need an off-guide price (✎ Custom) on Ingredient Costs.
  Answered line by line as each recipe is set up.

### The price-list leftovers

| leftover | today | blocks recipe costing? |
|---|---|---|
| **Unpriced food items** | **49** active food items have no price (about 37 on 2026-10-20; the guide has grown since — Jack Cheese, Dino Kale and Redbor Kale were added that day). Three are the placeholders below and one is staff coffee. **13 appear in active recipes:** bay leaves (10 recipes), Kewpie mayonnaise, kombu, sake, yellow split peas, baking powder, baking soda, brown sugar, champagne vinegar, distilled white vinegar, ground cumin, nori, honeynut squash. Greek yogurt and slab bacon also have unpriced rows, but each has a second, priced version (Straus Greek yogurt; Asia Intl slab bacon). | **Not the build.** They keep the recipes that use them from being *complete*: each such line says *no price yet*, with a link to price it. Price these 13 first. |
| **Bubu arare pack size** | Still **1,210.58 oz** at $185.88. It should be 126.96 oz, as the Tobiko arare row has. | **No.** No recipe uses arare. A one-minute fix on Ingredient Costs; it matters to the inventory count. |
| **Placeholder order items** | `empty place` ×2 (#268 Cooks Produce / Fruit, #269 Cooks Produce / Peppers) and `Hi guys xoxo` (#281 Asia Intl / Pork). Active, unpriced. | **No.** Not ingredients, and with no price they never reach the recipe picker. Rename or retire them on the Orders page. |
| **Order-ID reuse** | Nothing mismatched today: every price row's saved name matches its order item. | **Does not block the build; shapes the design.** On 2026-10-20 the Orders page was found renaming summer items in place into fall items (#270 Heirloom → Arrow Cabbage, #267 Plouts → Dried Cranberries). A price follows the order item's id and shows its *current* name, so a renamed item carries the old item's price under the new name, silently. A recipe linked to that price would start reading *Arrow cabbage* at the tomato price. Guarded twice: Slice 1 marks it on the price list; Slice 3 makes each recipe line remember the name it was linked under. |

---

## The spine

> **A recipe cost is a number someone will price a menu with and value a shelf with. Every slice
> makes a wrong cost harder to produce, easier to see, and never silent.**

Four rules, and everything below obeys them:

1. **Never a guess dressed as a fact.** A line that cannot be costed says why. A recipe total says
   what it leaves out. A cost per unit appears only when every line is accounted for. Anything
   built on an estimate — a yield, a conversion, a recipe inside — says *estimate*.
2. **The app never picks an ingredient for you.** It may propose the amount and unit it reads from
   the text; the ingredient is always a person's tap.
3. **The recipe the cooks read is never changed by costing.** This page reads `Recipes` and never
   writes to it.
4. **A link is to what was there when it was made.** If the recipe line's text, the ingredient's
   name, or the price's pack unit changes afterwards, the line says so and stops counting until a
   person looks.

---

## The design

### What the manager sees — the list

```
┌───────────────────────────────────────────────┐
│ ← Home     Tempest RECIPE COSTING    Manager ●│
│ [ Ingredients ][ Recipes ]                    │
│ [ Filter recipes…                           ] │
│ 36 recipes · 3 complete · 6 started           │
├───────────────────────────────────────────────┤
│ Jang Aioli                              Sauce │
│   $14.20 batch · makes 1 gal (estimate)       │
│   $3.55 / qt · $0.22 / 2 fl oz portion        │
│ Kabayaki                                Sauce │
│   $22.10 so far · 3 of 8 lines not costed     │
│ Bread & Butter Squash                 Pickles │
│   not started · 15 lines                      │
└───────────────────────────────────────────────┘
   (figures are illustrations, not data)
```

### One recipe

```
┌───────────────────────────────────────────────┐
│ ← Recipes   Kabayaki            Sauce · Saute │
│ Makes   [ 3   ] [ qt    ▾]  ☐ estimate        │
│ Portion [ 2   ] [ fl oz ▾]                    │
├───────────────────────────────────────────────┤
│ 4 cups mirin                                  │
│   Mirin · Birite     4 cup → 0.25 gal   $4.10 │
│ 4 cups sake                                   │
│   Sake · Birite        no price yet   Price → │
│ 2 ea onion                                    │
│   Yellow onions          needs a conversion   │
│   How much of what you buy is 1 each?         │
│ 2 pieces kombu                                │
│   not linked                         [ Link ] │
├───────────────────────────────────────────────┤
│ $22.10 so far · 3 of 8 lines not costed       │
│ 1 no price · 1 needs a conversion · 1 not linked │
└───────────────────────────────────────────────┘
   (figures are illustrations, not data)
```

- The recipe's own words are always the first line, exactly as the Recipe Database shows them.
  What costing made of them sits underneath.
- A multi-part recipe shows its part headers (`— CHEESE BASE —`) where the text has them.
- *Not costed* is the yellow highlighter (`.ing-pack.unset`'s fill in `kitchen.css`), not red.
  Complete is not green.
- **Price →** opens Ingredient Costs with its filter set to the item. Coming back, or refreshing,
  picks up the new price.

### How a line is costed

1. **Amount and unit**, confirmed by a person (proposed from the text).
2. **What it is**: one price-list row, **or** another recipe, **or** *not costed on purpose*.
3. **Same kind of measure** as the price's pack unit → converted automatically:
   *cost = amount in pack units × pack price ÷ pack quantity.*
4. **A different kind** (the recipe says quarts, the price is per lb) → the ingredient's
   conversion is used: *1 qt = 1.1 lb as bought*. None yet → *needs a conversion*.
5. **Another recipe** → the amount in that recipe's yield unit — through that recipe's own
   conversion when it is measured another way (*2 oz* of a sauce made by the quart) — × its cost
   per yield unit. That recipe must be complete and have a yield; otherwise the line says which it
   lacks.

A line is **not costed** — never $0 — and says why, when:

| reason | the line says |
|---|---|
| not linked yet | *not linked* |
| the linked item has no price | *no price yet* · Price → |
| units of different kinds, no conversion | *needs a conversion* |
| the price's pack unit, or a recipe's yield unit, changed kind since the conversion was made (re-entered from lb to case) | *conversion no longer matches — was lb, now case* |
| the ingredient's name changed since the link was made | *renamed — linked as Heirloom tomato, now Arrow cabbage — check* |
| the linked price row was retired | *price retired — relink* |
| a recipe inside is not complete, or has no yield | *uses Aioli base, which is not complete* |
| a recipe used by another measure than its yield, with no conversion for it | *needs a conversion — Aioli base is made by the qt* |

### Units

Built into the page. Standard conversions never change, so they are not a table.

| kind | units — any spelling; case, plurals and a trailing dot ignored |
|---|---|
| weight | g, kg, oz, lb (`#` = lb) |
| volume | tsp, tbsp, fl oz, cup, pt, qt, 1/2 gal, gal, ml, L |
| count | each (`ea`); dozen = 12 each. **Every other count word is its own unit** — bunch, clove, head, sprig, can, bottle, jug, tube, sheet, piece, bag, case, box, inch — and converts only to itself. |

- **`oz` always means weight.** A liquid measured in ounces is set to `fl oz` when the line is
  linked: the page proposes `oz` for `32 oz. soy`, and the person changes it. This is the one trap
  in the list, so a hint appears beside the unit box whenever an `oz` line meets a price sold by
  volume.
- Amounts read: `2`, `1.5`, `½`, `1½`, `1 1/2`, `1/2`. `5#` reads as 5 lb.

### Conversions

Asked from the line that needs one: *"How much of what you buy does it take to make 1 qt?"* —
answered in the price's pack unit, with an *estimate* box and an optional note (`sliced`,
`juiced`). Stored once per ingredient per kind of measure; every recipe that uses the ingredient
that way uses it. Changing one asks first when the new number is ≥10× or ≤1/10 of the old (the
costing page's magnitude check, carried over), and says how many recipes it moves.

Where the numbers come from is Stephen's call: weigh it once in the kitchen, or ask for a standard
starting figure and mark it *estimate*.

**A house recipe can have conversions too** (M1, approved 2026-11-02): *How much does 1 qt of
Spicy Green Sauce weigh?* · *How much does 1 each pork belly, cooked, weigh?* Asked from a line or a
portion that needs one, or set beside **Makes** on the recipe. It ties another measure to the
recipe's yield unit, measured **as made** rather than as bought, under the same rules: one per kind
of measure, the *estimate* box, the magnitude check, and a guard if the yield is later re-entered
in a different kind of unit.

### Yield and portion

Per recipe: **Makes** (amount, unit, *estimate* box) and **Portion** (amount, unit; optional).
From those:

- **cost per yield unit** = batch cost ÷ yield — shown only when the recipe is complete;
- **cost per portion** = cost per yield unit × the portion in yield units. A portion measured
  another way than the yield — a sauce made by the quart, portioned by the ounce — goes through the
  recipe's own conversion; with none yet, the cost per portion says *needs a conversion*.

Both say *estimate* if the yield, any conversion, or any recipe inside is an estimate.

---

## Tables — SQL Stephen runs; nothing is created from a session

Four new tables, `location`-scoped like everything else. **`Recipes` and `ingredient_costs` are
not altered.**

| table | one row per | key columns |
|---|---|---|
| `recipe_lines` | ingredient line of a recipe, once linked | `recipe_id, line_text, occurrence, component, qty, unit`, then `ingredient_cost_id` **or** `sub_recipe_id` **or** `skip`; `linked_name, active, updated_at`. Unique `(recipe_id, line_text, occurrence)` |
| `ingredient_conversions` | price-list row, per kind of measure | `ingredient_cost_id, from_kind, from_qty, from_unit, to_qty, to_unit, estimate, note, updated_at`. Unique `(ingredient_cost_id, from_kind)` |
| `recipe_conversions` | recipe, per kind of measure (M1) | `recipe_id, from_kind, from_qty, from_unit, to_qty, to_unit, estimate, note, updated_at` — `to_unit` in the yield unit's kind. Unique `(recipe_id, from_kind)` |
| `recipe_yields` | recipe | `recipe_id, yield_qty, yield_unit, yield_estimate, portion_qty, portion_unit, updated_at`. Unique `(recipe_id)` |

Choices worth saying out loud:

- **A line is keyed by its text.** `line_text` is the line exactly as the recipe had it (trimmed)
  when it was linked; `occurrence` is 2 for the second identical line in one recipe (Pork Belly
  lists `salt` twice). Every time a recipe opens, its current lines are matched to the stored ones
  by text. A current line with no match is *not linked*; a stored line with no match is listed
  under **No longer in the recipe** and counts for nothing. So an edit in the Recipe Database —
  even a typo fix — can unlink a line, but it can never leave an old amount silently costed. To
  keep re-linking quick, an unmatched old link is offered on the new line as one tap (*Use the old
  link: Mirin · Birite, 4 cup*), never applied by itself.
- **A line links to a price row, not an order-guide item**, and remembers `linked_name` — the name
  it was linked under. That catches renames in place (the order-ID reuse), relinks made on the
  price list, and off-guide items alike.
- **Saving is an upsert** on the unique key (PostgREST `on_conflict` with `Prefer:
  resolution=merge-duplicates`), as Inventory does, so a retry after a lost response cannot make a
  second row. The key is a **full** unique index, not a partial one, because PostgREST's
  `on_conflict` cannot target a partial index. A dismissed line is `active = false`; if its text
  comes back, the upsert reactivates it, and the name guard still applies.
- **Recipe conversions are a table of their own**, not a `recipe_id` column added to
  `ingredient_conversions`. One table would need a unique key over a column that is empty on half
  its rows; Postgres lets duplicates through such a key unless it is declared `nulls not distinct`
  (Postgres 15 and later), and PostgREST's upsert cannot aim at the usual workaround, a partial
  index. Two tables of the same shape keep plain keys, and the math sees no difference — a
  conversion reaches `lineCost()` as values either way.
- **No table has a delete policy** — the site's pattern.
- **Deleting a recipe in the Recipe Database.** `recipe_lines.recipe_id`,
  `recipe_yields.recipe_id` and `recipe_conversions.recipe_id` are `on delete cascade`: a deleted
  recipe takes its costing with it.
  `recipe_lines.sub_recipe_id` is `on delete restrict`: **a recipe used inside another cannot be
  hard-deleted** until that line is unlinked, and the Recipe Database will then say "Delete failed
  — try again" — a poor message for a correct refusal. Archive, the everyday path, is unaffected.
  See Risks, and the note for Kits.
- **The line's check constraint:** either `skip` with no target, or an amount, a unit and exactly
  one of `ingredient_cost_id` / `sub_recipe_id`; and `sub_recipe_id <> recipe_id`. Longer loops
  (A uses B uses A) are refused by the page when linking, and the math stops at depth 6 regardless.

---

## Where the math lives

**In one shared file, `assets/recipe-math.js`** (M5, approved by Stephen 2026-11-02), loaded by
every page that costs anything: this one, Inventory when it values prepared items, and Menu
Builder. Three small layers — units, `lineCost()`, `recipeCost()` — keeping the contract written
under Menu Builder, in the next section.

- **Pure functions only.** No page, no `api()`, no table, no screen. Every function is handed its
  data — prices, lines, yields, conversions — and returns numbers and reasons; each page does its
  own reading and its own display. That is what lets three different pages share it.
- **One name on the page.** Everything hangs off a single object, `RecipeMath`, so nothing in the
  file can collide with a page's own functions.
- **Loaded with a version**, `assets/recipe-math.js?v=N`, like `kitchen.css`. A change to the file
  bumps `?v=` on every page that loads it, and all of them must agree — otherwise a phone holding
  an old copy works out yesterday's arithmetic.
- **Its own check**, `scripts/check_recipe_math.py`, run the way the site's other checks run
  (headless Chrome): the fixtures to the cent, the deliberate breaks, and every page that loads the
  file loading the same `?v=`. It runs before any PR that touches the file, from whichever window.
- **The site's first in-house shared script.** `CLAUDE.md` says "there is no shared JS" (the
  vendored SortableJS and SheetJS in `assets/vendor/` are shared, but are not ours). That line is
  corrected in the same PR that creates the file — Slice 2 — and not left to the end, because
  every window reads `CLAUDE.md`.

Two other ways were weighed and set aside:

- **A database view** computing the costs. One source of truth — but every fix to the math becomes
  SQL Stephen pastes into the editor; recipes inside recipes and unit conversion are harder to test
  in SQL than in this repo's stubbed-browser harness; and nothing else on the site works that way.
- **A copy in each page**, kept honest by a check that runs every copy over the same fixtures — how
  the site already handles `api()`. This was the first choice, while only Inventory was going to
  share the math. With Menu Builder it would be three hand-kept copies of the unit table and the
  arithmetic, which is how one page ends up a cent off the others.

---

## What Kits, Inventory and Menu Builder can rely on

The Kits window reads this section: Kits (B5, *mise en place per recipe*) builds on the same
recipe library.

**Checked against `~/Developer/boxkitchen-kits/docs/kits.md`** (draft, unapproved, 2026-11-02),
whose "Overlap with Recipe Costing" was written before this plan existed. Its three needs all
hold: `Recipes.ingredients` stays one text field with its `— PART —` headings; recipe ids 5, 54,
43, 14, 19, 25, 24 and 46 stay the same rows; no ingredient name is rewritten. **Its question —
"how will a recipe's ingredient list be stored?" — is answered by its first option: a new table
beside the text, the text untouched. No change for Kits.** On its clean-up list: Kits uses
Chicken & Dumpling **#19**, by Stephen's choice, so Costing costs #19 too. The amounts it expected
Costing could not price — Honey Harissa Buffalo's `1 ea. butter`, `1 jug. honey`, `1 tube harissa
paste`; Pork Belly's `thyme` — need no edit to the recipe here: a count word is costed through a
conversion (*1 jug honey = 5 lb as bought*), and a line with no amount is linked with one, or marked
*not costed on purpose*. Editing the recipe text is still fine; it unlinks the edited lines here,
and Kits' keywords keep working as long as the names stay recognisable.

- **The `Recipes` table is not altered by this plan, and this page never writes to it.** A
  recipe's `id` is the shared key.
- **`recipe_lines`** holds each linked ingredient line as data: amount, unit, which price-list item
  it is (and through it the order-guide item and vendor) or which recipe it is, the part it belongs
  to (`component`), and the exact text it came from. **Only lines Stephen has linked exist** — a
  recipe not yet set up has none — so a reader must not assume a recipe's lines are complete, and
  must match `line_text` against the current recipe text the way this page does, or it will read
  stale lines.
- **`recipe_yields`** holds each set-up recipe's yield and portion, and **`recipe_conversions`**
  ties other measures to its yield (*1 qt = 2.1 lb*).
- **One door.** Only the recipe costing page writes these four tables, unless this plan changes.
- **If Kits wants structured ingredients to become the master** — replacing the text box, or
  editing amounts — that changes this plan's matching rule (`line_text`). Come back here first;
  the two plans change together.
- **If Kits changes `recipe_dashboard.html`:** a recipe used inside another can no longer be
  hard-deleted (see Tables). Kits may want a clearer message there than "Delete failed".
- **Inventory, prepared items:** value per container = cost per yield unit × the container in yield
  units. That needs a complete recipe with a yield, and a container unit that converts to it —
  directly (qt, pt, gal, lb, oz, each), or through the recipe's own conversion. A *1/6 pan* is not
  a unit here; Inventory would define it as a volume.
  Values freeze at close like every other line. The math is `assets/recipe-math.js` — Inventory
  loads it rather than copying it (M5).

### Menu Builder — `~/Developer/boxkitchen-menu`

A PIN-only sandbox for **draft dishes**, kept apart from the Recipe Database and Recipe Costing
until a dish is real (Stephen, 2026-11-02; its plan, `docs/menu-builder.md`, is not written yet).
A draft line is a raw ingredient at its live price (read only), a house recipe (a typed estimate
until that recipe is costed here), or an ingredient not bought yet, with a typed name and a
guessed price marked as a guess. It shows menu price → food cost %, and target % → suggested
price. It reuses this plan's **quantity-to-cost math**, and its draft lines are meant to match this
plan's line shape so a dish can later be promoted into a real recipe — by hand at first, by a
button later.

**What it can rely on — the math contract.** The math lives in `assets/recipe-math.js` (M5), which
Menu Builder loads; each part keeps this contract from the slice that adds it (2, 3, 5 and 6):

1. **Units** — normalise a spelling, name its kind, convert within a kind — exactly the table in
   "Units", and nothing else.
2. **`lineCost()`** looks nothing up and touches no table. In: an amount and unit; a price as
   *values* (`pack_qty, pack_unit, pack_price`), wherever it came from; a conversion as values,
   if one is needed. Out: the cost, **unrounded** — or no cost and the reason, from the reasons
   table under "How a line is costed" — and which inputs were soft. A guessed price is simply a
   price passed in marked as a guess.
3. **`recipeCost()`** is built on 2: the text matching, recipes inside recipes, the yield. Out: the
   cost so far, whether it is complete, every reason, the soft inputs, and the cost per yield unit
   when there is a yield. **It never returns nothing for an incomplete recipe.** Hiding a per-unit
   cost until a recipe is complete is this page's display rule, not the math's — so Menu Builder
   can see how far a recipe has got and fall back to its typed estimate.
4. **Rounding happens only on screen.** A dish summed from rounded lines would disagree with this
   page by cents.
5. **The loop stop at depth 6 counts from whoever calls**, a dish included.

And around it:

- **Draft dishes do not go into `Recipes` or `recipe_lines`.** Both are read as the real thing —
  by the cooks in the Recipe Database, by this page's list, by Kits. Menu Builder keeps its own
  tables.
- **Prices and conversions stay read only there.** A real ingredient that *needs a conversion*
  gets a link to Recipe Costing to add one — a link, not a second door, the way Inventory sends a
  missing price to Ingredient Costs. A guessed ingredient is not on the price list, so its guess is
  typed in the unit the dish uses, or Menu Builder keeps a conversion of its own beside the guess.
- **The line shape, for promotion later.** A draft line holds `qty`, `unit`, exactly one of
  `ingredient_cost_id` / `sub_recipe_id` / a guess, and `linked_name` — as `recipe_lines` does.
  Three things promotion will meet: it has to write the recipe's text first and key each line to it
  by `line_text` and `occurrence`; a guessed line cannot be promoted until the ingredient has a real
  price on Ingredient Costs; and a promote button would be a second writer of `recipe_lines`, which
  is a change to this plan when it comes.

**Choices in this plan that made Menu Builder's job hard.** M1 and M5 were approved by
Stephen on 2026-11-02 and are folded in; M2–M4 are fixed by the contract above.

| # | the choice | why it is hard for Menu Builder | recommended | status |
|---|---|---|---|---|
| **M1** | **Only price-list rows can have a conversion.** A recipe used inside another, and a portion, must be measured the same kind of way as the recipe's yield. | A dish is mostly portions of house recipes, by weight or by count — *4 oz pork belly*, *2 dumplings*, *2 oz Spicy Green Sauce* — and a yield is often in another measure. If Pork Belly's yield is entered as *2 each*, then *4 oz* of it cannot be costed at all. | Let a **recipe** have conversions, as a price row does (*1 qt Spicy Green Sauce = 2.1 lb*). That also lifts the same-kind rule for portions and for recipes inside recipes here, and gives Inventory's containers a way in. Built as a fourth table, `recipe_conversions` — see Tables for why not a column. | **Approved 2026-11-02, folded in** — Decisions, How a line is costed, Conversions, Yield and portion, Tables, Slices 0, 5 and 6. |
| **M2** | **The math was one recipe-shaped function**, `recipeCost(recipeId)`, reading the recipe text and `recipe_lines`. | A draft dish is neither; Menu Builder would have had to copy the text matching to reach the arithmetic. | Three layers. | Fixed — contract 1–3. |
| **M3** | **Prices and conversions would have been looked up by id inside the math.** | A guessed price has no row, and must not get one. | `lineCost()` takes values, not ids. | Fixed — contract 2. |
| **M4** | **"Estimate" was a single yes/no.** | Menu Builder adds a third kind of soft number — the guess — and Stephen wants it named. | The math says *which* inputs were soft (an estimated yield, an estimated conversion, a guessed price) and for which ingredient; each page picks its own words. | Fixed — contract 2–3. |
| **M5** | **The math is copied into every page that needs it** ("Where the math lives"). | Menu Builder is the third page, after this one and Inventory. Three hand-kept copies of the unit table and the arithmetic are how one page ends up a cent off the others. | One shared file, `assets/recipe-math.js`: pure functions only — no page, no `api()`, no table — loaded with a `?v=` like `kitchen.css`, with a check of its own. It would be the site's first shared script written in-house: `CLAUDE.md` says "there is no shared JS" (the vendored SortableJS and SheetJS in `assets/vendor/` are shared, but are not ours). The `CLAUDE.md` line is corrected in Slice 2. | **Approved 2026-11-02, folded in** — Decisions, Where the math lives, Slices 2–3, Constraints, Risks. |

**Found while planning**, for whoever next touches `recipe_dashboard.html`: `formatIngredients()`
and `formatMethod()` colour the part headers with an inline `#e85d3a` inside a JS string — a colour
from outside the token set, which `check_styling.py` does not see because it is built at runtime.

---

## Slices

Eight, small, safe before fast. Each is reviewable in one sitting and leaves things safer than it
found them. The new page stays **unlinked** — reachable only by its address — until Slice 7. From
Slice 2 on, every piece of arithmetic goes into `assets/recipe-math.js`, never into the page.

### Slice 0 — Ground truth and tables *(no app code)* · **blocks everything**

- **Read-only, Stephen runs:** one query over `pg_policies`, `information_schema.columns` and
  `pg_constraint` for `Recipes` and `ingredient_costs` — to confirm `Recipes.id`'s type, whether
  `Recipes` has a delete policy, and the RLS pattern to mirror.

  > **DONE 2026-11-02.** Stephen ran one read-only query over `pg_policies`, `pg_class`,
  > `information_schema.columns`, `pg_constraint` and `pg_indexes` for `Recipes` and
  > `ingredient_costs`, plus `version()`. It showed:
  >
  > - **PostgreSQL 17.6.**
  > - **`Recipes.id` is `bigint` identity**, primary key `Recipes_pkey`. No other constraints,
  >   no foreign keys. `location` is nullable with **no default** (all 55 rows read `Tempest`);
  >   `status text not null default 'active'`.
  > - **`Recipes` has a DELETE policy** (`Recipes delete`, `using (true)`), so hard delete from
  >   the Recipe Database is live. The cascade and restrict rules under Tables are therefore
  >   real paths, not theory. Its policies are for role `public`, with RLS on.
  > - **`ingredient_costs.id` is `bigint` identity.** `location text not null default
  >   'Tempest'`; `order_item_id` is a nullable FK to `order_items(id)`; the partial unique
  >   index `ingredient_costs_one_active_per_order_item`. Policies `ic_sel` / `ic_ins` / `ic_upd`
  >   are for **`anon` only** (with `using (true)` / `with check (true)`); no delete policy; RLS on.
  > - **The pattern to mirror:** RLS on; separate SELECT / INSERT / UPDATE policies,
  >   `using (true)` / `with check (true)`; no DELETE policy; `bigint` identity ids;
  >   `location text not null default 'Tempest'`. Roles **`anon, authenticated`**, as the plan
  >   says and as Inventory's newer tables do (a superset of `ingredient_costs`' `anon`).
- **The SQL:** the four tables, keys, checks, foreign keys and RLS (select / insert / update for
  `anon, authenticated`; no delete) in one transaction, ending with a select confirming each table
  exists with 0 rows. Dollar-quoted text. Proved first against a throwaway local Postgres shaped
  like Supabase, as Inventory's was: a duplicate line refused; an upsert retry updating one row; a
  line with two targets refused; a second conversion of one kind for one price row, or for one
  recipe, refused; delete refused; a recipe delete cascading to its lines, yield and conversions; a
  sub-recipe delete refused.

  > **WRITTEN 2026-11-02, not yet run.** `docs/recipe-costing-slice0.sql` (copy at
  > `~/Downloads/recipe_costing_setup.sql`). One transaction; a `do` block raises — undoing
  > everything — unless all four tables have 0 rows, there are exactly 12 policies, and none is a
  > delete policy. Choices the plan left open: `from_kind` is `volume`, `weight`, or the count
  > word itself (`clove`); a yield's and a portion's amount and unit are both set or both empty;
  > two extra indexes on `recipe_lines` (`ingredient_cost_id`, `sub_recipe_id`) for the
  > "where is this used" lookups. `ingredient_cost_id` has no on-delete rule (price rows are
  > never deleted; Postgres refuses it if one ever is).
  >
  > **Proved against a throwaway local Postgres 17** shaped like Supabase (`anon` and
  > `authenticated` roles; `Recipes` and `ingredient_costs` with their columns, policies and the
  > real 55 and 166 ids), the file sent as one message the way the SQL editor does — **41 of 41**:
  > as `anon`, a line saved by upsert and a retry updating that one row; a duplicate line
  > refused; a second identical line kept as occurrence 2; two targets, no target, skip with a
  > target, no amount, a zero amount, a recipe inside itself, an unknown recipe and an unknown
  > price row each refused; a sub-recipe line saved; a line dismissed by update; a second
  > same-kind conversion refused for a price row and for a recipe, another kind allowed, a
  > conversion upsert keeping one row; a second yield row and a yield without a unit refused;
  > delete refused on all four tables, both without a grant and with Supabase's default delete
  > grant (no policy → deletes nothing); `authenticated` can read; deleting a recipe used inside
  > another refused; deleting a recipe cascading to its line, yield and conversion; exactly
  > select / insert / update policies on each table. A copy with a check that cannot pass
  > raised and left **no tables and no policies**; the real file then applied cleanly.
  > Not proved: Supabase's own grants and PostgREST's schema reload, which only the real run
  > shows — hence the read-only GETs after it.
  >
  > **To undo it**, if ever needed (Stephen runs it; it deletes the four tables and their data):
  > `drop table public.recipe_lines, public.ingredient_conversions, public.recipe_conversions,
  > public.recipe_yields;`
- **Tidy-ups for Stephen, not blocking:** Bubu arare's pack (126.96 oz); ~~archiving Chicken and
  Dumpling #52~~ (done 2026-11-02; #19 stays, the one Kits uses); the three placeholder order items.

**Done when:** the tables exist (confirmed read-only, 0 rows each), RLS matches the existing
pattern, and the delete behaviour is proved.

### Slice 1 — The price list notices a rename *(`tempest_costing.html`)*

- A price row whose saved `name` is no longer its order item's name is marked on the Ingredient
  Costs list: *renamed on the order guide — priced as Heirloom tomato*. The yellow highlighter,
  not red.
- Editing a marked row asks once — *This price was saved for Heirloom tomato. Is it right for Arrow
  cabbage?* — because any save re-writes the name and clears the mark.
- Nothing changes by itself.

**Done when:** a renamed item is marked; editing it asks; an unrenamed item is untouched; proved
against a stubbed `api()` in `check_costing.py`, with all of its existing assertions still passing.

### Slice 2 — The recipes, read-only *(new page)*

- `tempest_recipe_costing.html`, copied from `tempest_costing.html` (PIN gate, `api()` with its
  timeout), unlinked.
- **`assets/recipe-math.js` begins here** (M5): the units and the amount reader, with
  `scripts/check_recipe_math.py`. `CLAUDE.md`'s "there is no shared JS" is corrected in the same PR.
- The list of active recipes. Open one to see each line as written, the amount and unit the page
  reads from it, the part headers, and *not linked* on every line.
- Writes nothing.

**Done when:** every active recipe (36 on 2026-11-02) renders from live data read-only; every line
(268) appears, in order, under its part; the proposed amount and unit are right on hand-checked lines (including
`5#`, `1½`, `1 1/2`, `Salt TT`, `32 oz. soy`, `2 bay leaves`) — read by the shared file and proved in
`check_recipe_math.py`; the `CLAUDE.md` line is corrected; nothing is written.

### Slice 3 — Link a line

- Tap a line: confirm or correct the amount and unit; pick the ingredient from the price list —
  the costing page's tap-to-pick list and word-by-word filter, started with the line's words,
  nothing picked — or mark it **not costed on purpose**. Unpriced order-guide items appear as *no
  price yet — price it first* and cannot be picked.
- **Change** clears the pick and the amount, as on the costing page.
- A linked line shows its cost when the units are the same kind; otherwise *needs a conversion*.
- The guards from day one: changed line text, changed name, retired price; **No longer in the
  recipe**; the old link offered as one tap.
- The write path as costing's Slice 4 left it: every control disabled in flight, a timeout, and
  an upsert so a retry cannot duplicate.
- `lineCost()` added to `assets/recipe-math.js`, to the contract under Menu Builder: it looks
  nothing up, and its result is unrounded.

**Done when:** no code path picks an ingredient; a line can be linked, changed and skipped; a
renamed item, an edited recipe line and a retired price each stop a line counting, each with its
reason; a dropped response cannot make two rows — all against a stubbed `api()`.

### Slice 4 — Conversions

- From *needs a conversion*: the question, the *estimate* box, the note. Saved once per
  ingredient per kind; every line that needs it costs at once.
- The pack-unit-changed guard. Changing a conversion: the magnitude check, and how many recipes
  it moves.

**Done when:** one conversion costs every line needing it across recipes; a ≥10× change asks;
re-entering a price in a different kind of unit stops the lines that relied on the old
conversion, with the reason.

### Slice 5 — Yield, portion and the numbers

- **Makes** and **Portion** on the recipe, with *estimate*.
- **The recipe's own conversions** (M1), set beside **Makes** or asked from a portion measured
  another way than the yield; the yield-changed guard.
- The batch total — *so far* while incomplete; cost per yield unit and per portion only when
  complete. The total says what it leaves out, by reason, and how many lines were skipped on
  purpose.
- The recipe list shows each recipe's state — not started / *so far* / complete — with its numbers.

**Done when:** totals match a hand calculation to the cent on fixtures covering every kind of unit
and every reason; an incomplete recipe never shows a per-unit cost; *estimate* appears whenever it
should; a portion by the ounce of a recipe made by the quart costs through the recipe's conversion,
and says *needs a conversion* without one.

### Slice 6 — Recipes inside recipes

- A line can link to another active recipe; its cost comes from that recipe's cost per yield unit,
  through that recipe's conversion when the line measures it another way.
- Loops refused when linking; the math stops at depth 6 regardless.
- The parent says it is incomplete, and why, until the recipe inside is complete with a yield;
  *estimate* carries up.

**Done when:** a two-level recipe (Jang Aioli on an aioli base) costs to the cent, including when
the parent measures the inner recipe another way than its yield; a loop is refused; an incomplete
inner recipe makes the parent say so.

### Slice 7 — Ship it *(shared files, last)*

- Bring the branch up to date with `main` first — the Inventory and Kits windows keep merging.
- `tempest_costing.html`: the **Ingredients | Recipes** tabs, in the shape of the existing
  segmented toggle; and back.
- `BUILD_PLAN.md` B4.3; `CLAUDE.md` (the new page and the four tables).

**Done when:** Stephen reaches Recipes from the Recipe Costing tile on his iPhone without entering
the PIN twice.

---

## Out of scope

- **Plate cost** — what one order of a dish costs. The next plan.
- **Pricing the missing items.** Done on Ingredient Costs, as now. Recipe costing links there and
  never writes a price.
- **Bulk set-up** — matching every line in a spreadsheet and loading them. Stephen's answer to
  question 3 is recipe by recipe, in the tool.
- **Cost history** — what a recipe cost last month, or an alert when it jumps. Costs follow
  today's prices.
- **More than one conversion per ingredient per kind** (sliced vs whole shallots by the quart).
- **Trim on weight lines.** `2 lb diced onion`, against onions bought by the lb, costs the diced
  weight at the as-bought price — a little low. Volume and count lines carry trim inside their
  conversion; weight lines do not. An optional trim % could come later.
- **Changing the Recipe Database or the `Recipes` table.**
- **Beverage costing.**

---

## Constraints

From `CLAUDE.md`, `docs/review-checklist.md`, and this window's rules:

- **The database is live. Never write test rows.** Read-only GETs are fine. Every write path is
  proved against a stubbed `api()` in `scripts/check_recipe_costing.py`.
- **Only this worktree.** Inventory and Kits run in parallel; `index.html` is not touched.
- **`assets/recipe-math.js` is shared.** Pure functions only. Any change bumps `?v=` on every page
  that loads it, and `check_recipe_math.py` runs before the PR — whichever window makes the change.
- **`kitchen.css` unchanged if at all possible.** Page-only rules live in the page's `<style>`.
  If it must change, bump `?v=` on every page, and every page must agree.
- **No `:root`, no redeclared core token. Class names are load-bearing** — add, never rename; new
  classes carry a `used by:` banner.
- **No input below 16px.** A new input in a modal is written qualified —
  `.modal input[type="text"].your-class,.your-class{… font-size:16px …}` — or it renders at
  15.2px and zooms iOS (#135). `FS_REGISTER` in `check_styling.py` must not grow.
- **State is fill, weight and border, never hue.** *Not costed* is the yellow highlighter.
  `--danger` is for destructive actions only; `--faint` for inactive text only.
- **Print:** the page prints as a plain list; every modal is hidden under `@media print`; nothing
  relies on white text on a fill.
- **`python3 scripts/check_styling.py`** before every PR (it needs Chrome).
- **Never write the manager PIN or the site password** in this document, a PR, or a comment.
- **SQL text is dollar-quoted.**

---

## Risks

| risk | why it matters | mitigation |
|---|---|---|
| Keying lines by text unlinks them on any recipe edit | A typo fix in the Recipe Database makes a costed recipe incomplete | It fails safe — incomplete, never stale; the old link is offered as one tap; *No longer in the recipe* lists what fell off |
| `oz`, weight vs fluid | `32 oz. soy` costed as weight against soy sold by the gal asks for a conversion it should not need | The unit is confirmed when linking; a hint appears when `oz` meets a price sold by volume |
| One conversion per kind is approximate | Sliced and whole by the quart can differ by a quarter or more | *estimate*; good enough to price a menu; listed in Out of scope |
| Estimates spread | One estimated yield marks every recipe that uses it, and Inventory's values | Intended — the mark is the point; it clears as numbers get measured |
| Costs move with prices, silently | A recipe's cost changes overnight when an invoice is entered | Intended; history is out of scope; Inventory freezes values at close |
| The math is one shared file | A mistake in `recipe-math.js` moves three pages at once | Pure functions with their own fixtures to the cent, run before any PR that touches the file; each page pinned by `?v=` until it is bumped on purpose |
| A recipe used inside another cannot be hard-deleted | The Recipe Database says "Delete failed — try again" | Archive is unaffected; noted for Kits; the message belongs to whoever next touches that page |
| Incompleteness cascades through recipes inside recipes | Mac & Cheese stays incomplete until roasted garlic is set up | Each line names the recipe it waits on; set up the bases first |
| The new page grows the way the costing page did | 1,448 lines and more than ten review rounds | Small slices; the costing page itself is touched twice, minimally |

---

## How to verify without touching live data

As in `docs/costing-bulk-entry.md` and `docs/inventory-guide.md`:

- **Stub `api()`** and assert on the payloads it is handed — the only way to prove the write path,
  dropped responses, and the upsert key.
- **Render real rows, read-only, every write blocked** — every active recipe and line (36 and 268 on 2026-11-02).
- **To the cent on fixtures**: one per kind of unit, one per reason, a two-level recipe, an
  estimate.
- **Break it on purpose**, and check the harness catches each break: $0 for an unpriced line; `oz`
  treated as volume; a stale line counted; a per-unit cost on an incomplete recipe; an estimate
  not carried up.
- **The SQL against a throwaway Postgres** before Stephen runs it.
- **A phone test by Stephen**, with every keystroke named.

---

## Questions still open

None blocks Slice 0. Most are answered recipe by recipe, as each is set up.

1. ~~Archive Chicken and Dumpling #52?~~ — **done by Stephen, 2026-11-02.** #19 *(Soup Base)*
   stays; Kits and Costing both use it.
2. **House-made or bought?** `aioli base`, `Aioli`, `mayo`, `roasted garlic` (is it Garlic
   Confit?), `chicken stock`, and Pork Belly's `cooking liquid`. A house-made one needs its own
   recipe, with a yield, set up first.
3. **Olive oil** is on neither the order guide nor the price list, but is in 10 active recipes.
   Where is it bought? It needs a price before those recipes can be complete.
4. ~~"Portions"~~ — **answered 2026-11-02: yes, a portion size per recipe** (*2 fl oz of aioli*),
   giving a cost per portion.
5. ~~Slice 1 in this plan?~~ — **yes, approved with the plan, 2026-11-02.**
6. ~~Menu Builder's two decisions~~ — **both answered yes, 2026-11-02** (M1: a house recipe can
   have its own conversion; M5: the math lives in one shared file), and folded in.
