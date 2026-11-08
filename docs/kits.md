# Kits — what goes in each kit

Status: **built and shipped.** The plan (v1) was approved by Stephen on 2026-11-02, with one
change: the build is split into five small slices, so each can be checked before the next
starts ("Slices"). All five are built; see each slice's "as built". Written from
Stephen's interview in the Kits window (2026-10-28 and 2026-11-02). Every decision below is
Stephen's.

**Slice 1 is live** (`8e6f3ea`, #168), and so is the one-keyword-one-line rule (`72dfef2`,
#169). Stephen checked Slice 1 on a phone and on the kitchen tablet before Slice 2 began. See
"Slice 1 as built". **Slice 2 is live** (`d399dda`, #174); Stephen walked all 8 kits on
2026-11-05 and approved them. **Slice 3 is live** (`fcfd09d`, #178); Stephen passed the
Airplane Mode test on 2026-11-07. **Slice 4 is live** (`b092421`, #182); Stephen passed the
iPhone print-preview check on 2026-11-08. **Slice 5 BUILT 2026-11-08** on `kits-slice5`, not
pushed: the home-page tile goes live with it. See "Slice 5 as built". Still waiting: Stephen's
phone check of the tile once it is live.

Target file: a new page, `tempest_kits.html`. At the very end, and only then: the Kits tile in
`index.html`, `BUILD_PLAN.md` (B5), and the page count in `CLAUDE.md`. This plan needs **no
database change** and **no change to `assets/kitchen.css`** rules.

---

## What it is for

A kit is one recipe's mise en place, built ahead so the recipe can be made fast. The PM line
builds it at night: spices measured together in one container, each liquid in its own, things
that go into the pot at the same moment sharing one. All the containers go into **one hotel
pan in the cooler**. The morning crew pulls the pan and makes the recipe.

Today the only record is the "Kit – …" item on the Line PM list, with its KIT/MAKE pill. It
says *that* a kit was built, not *what goes in it*. That lives in people's heads. The Kits page
writes it down: for each kit, which containers, what goes in each and how much, and what is
deliberately left out.

It is BUILD_PLAN **B5** ("mise en place per recipe; depends on the recipe library").

---

## Decisions

| question | decided |
|---|---|
| Who uses it | **The PM line cook** building the kit; **the morning cook** making the recipe, who checks the pan against the sheet before starting; **managers / chef** checking kits or training; **new staff** learning how Tempest sets up each recipe. |
| When | **Built on the PM shift, cooked from the next morning.** |
| On what | **Cooks' own phones and the kitchen tablet.** Not paper day to day, but the page prints, because paper is the site's backup (`CLAUDE.md`). |
| What a kit sheet shows | **Numbered containers**, then the last step: every container into one hotel pan, label, date, cooler. Spices together; each liquid on its own; things added at the same moment share a container. |
| Which kits | **Fixed to today's 8** (the real Line PM kit items). More will come as the menu changes; each is a small code change (see "Adding a kit"). |
| Batch size | **One batch**, exactly as the recipe says. |
| Raw meat | **Not in the kit.** Pulled from the meat shelf at make time; listed under "Not in the kit". |
| Lines with no amount | Salt & pepper to taste, stock "to cover", tap water: **left for the stove**, listed under "Not in the kit" so nobody wonders whether they were forgotten. |
| Big items | A whole bottle or jug (honey, Frank's, red wine) goes **next to the hotel pan, labelled** with the kit. |
| Method steps | **Not on the kit sheet.** Kit contents only. |
| Tick boxes | **None in v1.** The Line PM item already records that a kit was built. Ticks can come with the link. |
| Link from Line PM | **A later step**, not this build. Each kit gets its own address now so the link is easy later. |
| The drafts | Stephen approved the Spicy Green Sauce draft as the pattern, then the other 7 as written (2026-10-28). They are in "The 8 kits". |
| Which recipe | "Buffalo sauce" = **Honey Harissa Buffalo**. "Chicken & Dumpling soup" = **Chicken & Dumpling (Soup Base)**, id 19, not the near-duplicate id 52. |

---

## Ground truth — read-only, 2026-10-28

**Line PM kit items** (`prep_items`, `station='kits'`): **11** rows, all `team=line`,
`category=daily`. **8 real, 3 placeholders** ("Kit - New prep soon", "Kit- New prep coming
soon" ×2). Each has a per-day KIT/MAKE pill backed by `prep_logs.mode`: any cook flips it, and
it resets daily (`toggleMode()`, shared by `tempest_line.html` and `tempest_prep.html`). The
item's checkbox is today's only "kit built" record. **Nothing links an item to a recipe**, and
the names differ ("Gastrique" vs "Bacon Shallot Gastrique").

**The recipe library** (`Recipes`): **55** rows, 37 active, 18 archived. `ingredients` is **one
text field, one ingredient per line**. A recipe in parts gets heading lines written by the
editor's `buildCombined()` (`— DRY —`, `— PICKLING LIQUID —`) with a blank line between parts.
Editing a recipe in the Recipe Database rewrites the whole field. `recipe_dashboard.html` has
**no per-recipe address**: no hash or query handling, so nothing can link to one recipe.

**The 8 kits**, in Line PM order (the order the page lists them):

| kit | recipe | id |
|---|---|---|
| Buffalo sauce | Honey Harissa Buffalo | 5 |
| Pork belly | Pork Belly | 54 |
| Gastrique | Bacon Shallot Gastrique | 43 |
| Dumpling | Dumpling | 14 |
| Chicken & dumpling soup | Chicken & Dumpling (Soup Base) | 19 |
| Spicy green sauce | Spicy Green Sauce | 25 |
| Pickled onions & peppers | Pickled Onion & Pepper | 24 |
| Mac & cheese | Mac & Cheese | 46 |

---

## The spine

> **A kit that is missing something is found out at the stove the next morning, by someone
> who didn't build it, when it is too late to fix. Every part of this page makes a missing
> ingredient impossible to miss.**

Three rules:

1. **The recipe is the one source of amounts.** The page never keeps its own copy of an amount.
   It reads the recipe every time it opens; the kit definition only says *which container*
   each ingredient goes in. Change "2 cups" to "3 cups" in the Recipe Database and the kit says
   3 cups.
2. **Every recipe line lands somewhere you can see**: in a container, under "Not in the kit",
   or under "Not sorted yet". Nothing is dropped quietly. A line added or renamed in the recipe
   that the kit doesn't know shows in "Not sorted yet", loudly, until someone sorts it.
3. **The page only reads.** No writes, no PIN, no new table.

---

## The design

### What the builder and the morning cook see

**The list.** Header "Kits", back to the hub. The 8 kits in Line PM order, each a big tap
target with the kit's name and its container count ("5 containers").

**A kit sheet** (`tempest_kits.html#pork-belly`), top to bottom:

- **The kit's name**, and the recipe it comes from beneath it ("from Honey Harissa Buffalo").
- **Containers**, numbered ① ② ③ in rings (a border, so it prints). Each has a name ("Spices"),
  how it is kept ("measure together", "own container", "next to the pan, labelled"), and the
  recipe's lines **exactly as written in the recipe**.
- Where a recipe is in parts, its containers sit under those parts (Mac & Cheese: Cheese base
  / Roux base / Noodles & assembly).
- **Into the hotel pan** — the last step, always there: "All *N* containers into one hotel
  pan", the next-to-the-pan items by name, then "Label and date the pan · into the cooler".
- **Not in the kit — at make time**: each line with its reason (raw meat, pull from the meat
  shelf · to taste, at the stove · comes from the braise · from the tap).
- **Not sorted yet** — only when something is in it: the line, and "This is in the recipe but
  not in the kit yet — tell a manager." It stands out by weight and border, not colour alone
  (`CLAUDE.md` rule 4).

**One sheet for both people.** The builder works down it; the morning cook checks the pan
against it.

**Phone and tablet**: one column, wider on a tablet, no second layout to maintain. **The page
has no inputs**, so #135 (the iPhone 16px zoom) cannot happen here. If a search box is ever
added, it is written qualified, as `CLAUDE.md` describes.

### How a recipe line finds its container

Each kit is defined in the page as a list of containers, each with a few **keywords**. When
the page reads the recipe:

- Heading lines (`— DRY —`) and blank lines are skipped.
- A keyword matches **at the start of a word**, ignoring case, accents (jalapeño = jalapeno)
  and curly vs straight apostrophes. So `carrot` finds "carrots" and `bay` finds "bay leaves".
- **Longest keywords claim lines first**, so "red wine vinegar" is taken before "red wine",
  "buttermilk" before "butter", "peppercorns" before "pepper".
- A keyword used twice in one kit (Mac & Cheese's two half & half, Pork Belly's two salt)
  claims lines in recipe order, in the order the kit lists them.
- **Each line is claimed once.** A line nobody claims goes to "Not sorted yet". A keyword that
  finds nothing shows nothing (the recipe dropped that ingredient); a container left empty
  disappears and the numbers close up.
- **Each keyword picks up exactly one recipe line**: the first line, in recipe order, that it
  matches and that no other keyword has already picked up. If a recipe has two lines that
  match one keyword, the kit must list that keyword twice (as Pork Belly does with salt and
  Mac & Cheese with half & half), or the second line shows in "Not sorted yet". A keyword
  never picks up more than one line.
- **A recipe that is missing or archived** makes that kit say "Recipe not found in the Recipe
  Database — tell a manager", never an empty sheet.
- **Recipes that fail to load** show a message and a Try again button.

Keywords rather than exact text, so a changed amount or prep note ("small dice" → "fine
dice") still lands in the right container.

### The 8 kits

As approved by Stephen 2026-10-28. Keywords in `code`. **⇢** = next to the pan, labelled.

**Buffalo sauce** — Honey Harissa Buffalo (5)
- ① Butter — own container, melts first — `butter`
- ② Harissa + garlic — together — `harissa` `garlic`
- ③ Honey — ⇢ — `honey`
- ④ Lemon juice — own container — `lemon juice`
- ⑤ Frank's Red Hot — ⇢ — `frank`

**Pork belly** — Pork Belly (54)
- ① Braise veg — together — `white onion` `carrot` `celery` `heads of garlic`
- ② Braise seasoning — together — `bay` `salt` `peppercorns` `parsley stems`
- ③ Roasting herbs — together — `thyme` `rosemary` `garlic cloves`
- Not in the kit: `pork belly` (raw meat) · `stock` (to cover, at the stove) · `cooking liquid`
  (comes from the braise) · the second `salt` and `pepper` (to finish)

**Gastrique** — Bacon Shallot Gastrique (43)
- ① Bacon — own container — `bacon`
- ② Shallots — own container — `shallot`
- ③ Herbs — together — `thyme` `bay`
- ④ Red wine — ⇢ — `red wine`
- ⑤ Red wine vinegar — own container — `red wine vinegar`
- ⑥ Sugar — own container — `sugar`
- ⑦ Horseradish — own container — `horseradish`

**Dumpling** — Dumpling (14)
- ① Dry mix — together — `baking powder` `baking soda` `salt` `black pepper` `flour`
- ② Butter — own container — `butter`
- ③ Buttermilk — own container — `buttermilk`

**Chicken & dumpling soup** — Chicken & Dumpling (Soup Base) (19)
- ① Olive oil — own container — `olive oil`
- ② Butter — own container — `butter`
- ③ Aromatics — together — `thyme` `bay`
- ④ Vegetables — together — `carrot` `celery` `white onion` `garlic`
- ⑤ Flour — own container — `flour`
- Not in the kit: `chicken thigh` (raw meat) · `chicken stock` (cans, from the shelf) · `salt`
  and `black pepper` (to taste)
- *Changed 2026-11-05 by Stephen:* the stock comes in cans, grabbed at make time, so it is no
  longer a next-to-the-pan container. The kit has 5 containers.

**Spicy green sauce** — Spicy Green Sauce (25)
- ① Spices — together — `coriander` `cumin` `salt`
- ② Herbs & veg — together — `parsley` `cilantro` `jalapeño` `garlic`
- ③ Olive oil blend — own container — `olive oil`
- ④ Lemon juice — own container — `lemon juice`
- ⑤ Greek yogurt — own container — `yogurt`

**Pickled onions & peppers** — Pickled Onion & Pepper (24)
- ① Veg — together — `red onion` `mini pepper` `garlic`
- ② Pickling spices — together — `sugar` `salt` `coriander`
- ③ Cider vinegar — own container — `cider vinegar`
- Not in the kit: `water` (from the tap)

**Mac & cheese** — Mac & Cheese (46), 11 containers. *Decided 2026-11-05 by Stephen:* the
sub-headings are the kit's own groups below, not the recipe's parts (so ⑪ Herbs sits under
Noodles & assembly, where it is used, though the recipe lists chives and parsley under Roux
base); and ④ ⑤ ⑥ ⑦ ⑨ ⑩ are each "own container".
- *Cheese base* — ① Half & half, labelled "cheese base" — `half & half` · ② Cheeses — together
  — `velveeta` `mixed cheese` · ③ Seasoning — together — `chipotle peppers` `salt`
  `chipotle chili powder` `ancho`
- *Roux base* — ④ Butter — `butter` · ⑤ Onion — `white onion` · ⑥ Roasted garlic —
  `roasted garlic` · ⑦ Flour — `flour` · ⑧ Half & half, labelled "roux" — `half & half`
- *Noodles & assembly* — ⑨ Macaroni — `macaroni` · ⑩ Salt for the water — `salt` · ⑪ Herbs —
  together — `chives` `parsley`

**Checked 2026-11-02** against the live recipe text (a read-only GET, with a scratch script
following the rule above): every line of all 8 recipes lands in the container listed here or
in "Not in the kit", every keyword finds its line, and nothing lands in "Not sorted yet".

### Adding a kit when the menu changes

1. Stephen names the recipe (it must be in the Recipe Database first) and where it sits on
   the Line PM list.
2. A session drafts its containers in this shape, from the recipe and its method; Stephen
   corrects them.
3. A small PR adds it to the page's kit list and to the guard's fixture. Pushing it live is
   Stephen's call, as always.

Removing a kit is the reverse. If this happens often enough to be a chore, manager-editable
kits is the build after (see "Later").

### Addresses

Each kit has its own: `tempest_kits.html#buffalo-sauce`, `#pork-belly`, `#gastrique`,
`#dumpling`, `#chicken-dumpling-soup`, `#spicy-green-sauce`, `#pickled-onions-peppers`,
`#mac-and-cheese`. Back returns to the list. The later Line PM link points here.

### Printing

Print from the list prints all 8 kit sheets, one per page. Print from a kit prints that kit.
Container numbers are rings and "Not sorted yet" is a heavy border, so nothing relies on a
background fill (`CLAUDE.md`, "Printing is a backup").

---

## Slices

**Five, each small**, so a mistake is caught in the slice that made it and not three slices
later. Nothing writes, so the order is about what can be checked: the one piece of logic
everything rests on comes first, on one kit; then the other seven; then what happens when
things go wrong; then paper; then the shared files, last.

**Every slice:**

- is its own branch and PR, and **starts only after the one before is merged and Stephen has
  walked it**;
- names its files up front (`MODIFIED: …`) and touches nothing else;
- adds its promises to `scripts/check_kits.py` before the PR, and passes it and
  `python3 scripts/check_styling.py`;
- **stops before pushing.** Pushing rebuilds the live site, and Stephen approves that every
  time.

**Slices 1–4 go live unlinked.** The page exists at its address, but no tile or link leads to
it, so staff cannot find a half-built page. It is the same path Inventory took.

### Slice 1 — One kit, end to end: Spicy Green Sauce

The kit Stephen already approved, built all the way through, so the sorting rule is proved and
the look is settled once, not eight times.

- `tempest_kits.html`, using `recipe_dashboard.html` as its template (it already reads
  `Recipes`; its search box and editor are removed, leaving a page with no inputs).
- The kit list in the page holds one kit. The one read asks only for the recipes that list
  names: `Recipes?id=in.(…)&location=eq.Tempest&select=id,name,status,ingredients`. So the
  next slice adds kits without touching the read.
- **The sorting rule**, all of "How a recipe line finds its container".
- **The sheet**: kit name and the recipe it comes from, numbered containers in rings, the hotel
  pan step, "Not in the kit", "Not sorted yet".
- **`scripts/check_kits.py`** and `.github/workflows/kits-guard.yml`, the same shape as
  `check_inventory.py`: the real page in headless Chrome against a stubbed `api()`, so no
  request can reach the live database. It proves:
  - with today's Spicy Green Sauce text, exactly the 5 containers in "The 8 kits", with
    nothing in "Not sorted yet";
  - a changed amount stays in its container and shows the new amount;
  - a renamed ingredient goes to "Not sorted yet", and the box appears only then;
  - heading lines and blank lines are skipped; "jalapeno" and "jalapeño" both match;
  - **the page sends no write request of any kind.**
- `check_styling.py` picks the page up by itself (`glob("*.html")`) and must run clean.
- **Stephen opens it by its address on a phone and on the kitchen tablet** and says whether
  the sheet reads right in the kitchen before seven more kits are entered.

### Slice 1 as built

`tempest_kits.html` (new), `scripts/check_kits.py` (new), `.github/workflows/kits-guard.yml`
(new, mirrors the inventory guard), and this section. **No shared file touched**:
`kitchen.css`, `index.html`, `check_styling.py`, `CLAUDE.md` and `BUILD_PLAN.md` are as they
were. The page is reachable only by its address; no tile links to it.

**What it does**

- One GET: `Recipes?id=in.(25)&location=eq.Tempest&select=id,name,status,ingredients`. The id
  list is built from the kit list, so Slice 2 adds kits without touching the read.
- `api()` is cut down to **GET only**: it takes no method and no body, so the page cannot
  send a write. No PIN, no Manager switch, no inputs.
- The sorting rule exactly as "How a recipe line finds its container", including "each
  keyword picks up exactly one recipe line" (added to the plan from the planning window after
  Slice 1 merged, with its guard scenario `twogarlic`).
- The sheet: kit name, "from <recipe>", numbered containers in bordered rings (CSS circles
  holding the digit, so they print), the hotel pan step (counting only containers that are
  not next to the pan), "Not in the kit" when the kit has any, and "Not sorted yet" at the
  **top**, above the containers, in a 4px ink border, only when something is in it.
- Phone header (`.header`), not the Recipe Database's desktop masthead, since this is a
  phone page.

**Two small things ahead of their slice**, because a blank screen breaks the spine:
a failed load shows "Could not load the recipes" with **Try again**, and a missing or
archived recipe shows "Recipe not found in the Recipe Database — tell a manager". Both are
unguarded until Slice 3 adds their scenarios.

**Proved**

- `check_kits.py`: **81 assertions, 5 scenarios, clean** (ok, amount, renamed, headings, twogarlic).
  Every scenario: exactly one request, a GET with no body and no write headers, to the one
  URL above; no `fetch`/`sendBeacon`; no inputs on the page; every recipe line lands exactly
  once. Then: today's text gives exactly the 5 containers with nothing unsorted; 2→3 cups
  of yogurt stays in ⑤ and the old amount is gone; yogurt renamed to Skyr appears in "Not
  sorted yet" (heavy border, tell-a-manager line), ⑤ disappears and the pan says 4;
  headings and blank lines skipped, "Jalapeno" and a curly apostrophe still match; a second
  "garlic" line goes to "Not sorted yet" while the first stays in ② and nothing else moves.
- **It fails when it should**, each in a throwaway copy: a POST instead of a GET (32
  failures), accents not stripped (caught), heading lines not skipped (caught), one keyword picking up two lines (caught). Breaking
  longest-first is **not** caught: Spicy Green Sauce has no overlapping keywords. That
  proof is Slice 2's (red wine / red wine vinegar, butter / buttermilk).
- `check_styling.py`: clean, 12 pages.
- The fixture is recipe 25's live text from a read-only GET on 2026-11-02.

### Slice 2 — All 8 kits, the list, and the addresses

- The other 7 kits, exactly as in "The 8 kits".
- **The list**: the 8 in Line PM order, each with its container count.
- **The addresses** (`#pork-belly` and the rest); Back returns to the list; an address that
  names no kit shows the list.
- A recipe's parts become sub-headings over its containers (Mac & Cheese); next-to-the-pan
  items are named in the hotel pan step.
- The guard adds:
  - with today's text, every line of all 8 kits lands where "The 8 kits" says, and nothing in
    "Not sorted yet". This is the check run by hand on 2026-11-02, made automatic;
  - the longest keyword wins: red wine / red wine vinegar, butter / buttermilk, pepper /
    peppercorns;
  - a keyword used twice claims lines in recipe order: Mac & Cheese's two half & half, Pork
    Belly's two salt;
  - each address opens its own kit.
- **Stephen walks all 8** on a phone and checks each one against how the kitchen actually kits
  it. Any change goes into "The 8 kits" in this document first, then the page.

### Slice 2 as built

`tempest_kits.html`, `scripts/check_kits.py`, and this file. **No shared file touched**, the
kits-guard workflow included. The page is still reachable only by its address.

**Decided by Stephen before the build (2026-11-05)**, and written into "The 8 kits" first:
the chicken stock is **not in the kit** (cans, from the shelf, at make time), so Chicken &
dumpling soup has 5 containers; Mac & Cheese's sub-headings are **the kit's own groups**, so
Herbs sits under Noodles & assembly; its six containers with no wording say "own container".

**What it does**

- All 8 kits in `KITS`, in Line PM order, word for word from "The 8 kits". A box may carry a
  `group` (its sub-heading); numbering runs straight through the groups (Mac & Cheese 1–11).
- **The list** (no address, or an address that names no kit): "Kits", then 8 edged tap
  targets (≥60px), each with the kit's name and its real container count, worked out from the
  loaded recipe (5, 3, 7, 3, 5, 5, 3, 11).
- **Addresses** by hash. `hashchange` redraws from the recipes already loaded: **one read for
  all 8**, never a second. The sheet has "← All kits" (`href="#"`); the browser's back works
  too, because every kit is its own history entry.
- "Not in the kit" reasons: raw meat — pull from the meat shelf; to cover, at the stove;
  comes from the braise; to finish / to taste, at the stove; cans, from the shelf; from the tap.
- Unchanged from Slice 1: the GET-only `api()`, the sorting rule, the "could not load" and
  "recipe not found" messages (Slice 3 guards them).

**Live text check, 2026-11-05.** A read-only GET of recipes 5, 54, 43, 14, 19, 24 and 46, run
through the rule: every line lands where "The 8 kits" says, nothing in "Not sorted yet", every
keyword finds a line. No keyword was changed.

**Proved**

- `check_kits.py`: **254 assertions, 10 scenarios, clean**. New: `all8` opens every kit by its
  address in turn and checks it against an expectation **written out by hand** from "The 8
  kits" (not by running the page's sort): each container's part, name, keep line and lines;
  numbering; "Not in the kit" lines and reasons; the pan count and next-to-the-pan names;
  Back; then the browser's back. `reorder` swaps red wine / red wine vinegar and butter /
  buttermilk in the recipe, because in today's text the shorter word's line always comes first,
  so longest-first is only proved when it isn't. `list`, `direct` (opens `#mac-and-cheese`
  cold), `nope` (an unknown address). Every scenario: exactly one request, a GET, all 8 ids.
  Longest-first on pepper / peppercorns is checked in `all8` but **can't be broken by line
  order** with these kits: `peppercorns` sits in a container and `pepper` in "Not in the kit",
  and containers claim before "Not in the kit" on a tie, so either order gives the same answer.
- **It fails when it should**, each in a throwaway copy: longest-first off (caught by `reorder`;
  today's text alone does **not** catch it), twice-listed claims reversed, every address showing
  the list, a bad address opening a kit, refetching on every kit, a POST, the stock dropped
  from "Not in the kit", sub-headings dropped. All caught.
- `check_styling.py`: clean, 13 pages.

### Slice 3 — When the recipe or the wifi lets it down

- **A recipe that is missing or archived**: that kit says "Recipe not found in the Recipe
  Database — tell a manager", never an empty sheet, and the list marks it too.
- **A recipe that lost an ingredient**: the keyword shows nothing, a container left empty
  disappears, and the numbers close up.
- **Recipes that fail to load** (no signal, Supabase down): a plain message and a Try again
  button that works.
- The guard adds a scenario for each, and re-proves that nothing is written.
- **Stephen tries it in Airplane Mode**, as with Inventory's Slice 4.

### Slice 3 as built

`tempest_kits.html`, `scripts/check_kits.py`, and this file. No shared file touched.

**Decided by Stephen (2026-11-05):** a missing or archived recipe shows **"Recipe not found"**
on the list in bold ink, in place of the count; a kit where nothing sorts shows "Not sorted
yet" with every line, no containers and no pan step, and **"Needs sorting"** on the list; the
no-signal wording stays ("Could not load the recipes. Check the signal, then try again." +
**Try again**).

**What changed on the page.** Most of this slice was already built in Slice 1 and only
needed proving. New: the list's two bold marks (`.kit-flag`, ink and weight, never a hue);
the empty-kit screen (never "All 0 containers into one hotel pan"); the bare `&nbsp;`
under a not-found kit's title is now an empty line. Try again redraws **the address you were
on**, because the load ends in `route()`.

**Proved**

- `check_kits.py`: **346 assertions, 18 scenarios, clean**. New: `missing` (Gastrique's recipe
  absent) and `archived` (Dumpling's), on the list and on the sheet, with Back; `lost`
  (celery deleted from Pork Belly: ① keeps its other lines; sugar from Gastrique: ⑥ goes,
  Horseradish becomes ⑥, the pan says 5 with the red wine beside; macaroni from Mac & Cheese:
  10 containers, Noodles & assembly keeps two); `emptied` (Pickled rewritten so no container
  keyword matches); `fail` (no answer), `e500`, `hang` (the page's own timeout, ≤60s, fires),
  each then Try again; `failaddr` (fail at `#mac-and-cheese`, Try again lands on Mac &
  Cheese). Every scenario: GETs only, and exactly 1 (2 after a Try again).
- **It fails when it should**, each in a throwaway copy: a dead Try again, no list mark,
  "All 0 containers" shown, an empty container left in, Try again landing on the list, no
  timeout, the mark in tomato instead of bold ink. All caught.
- `check_styling.py`: clean, 14 pages.
- The missing/archived screens can't be seen live without changing a recipe, so the guard is
  their proof. Stephen's Airplane Mode test covers the no-signal path on a real phone.

### Slice 4 — The paper backup

- Print rules in the page's own `<style>`, inside `@media print`, with greys from
  `PRINT_PALETTE` only.
- Print from the list prints all 8 kit sheets, one per page. Print from a kit prints that kit.
- Rings and borders, never background fills, so nothing disappears on paper.
- **Checked in iOS print preview**, as Inventory's Slice 5 was.

### Slice 4 as built

`tempest_kits.html`, `scripts/check_kits.py`, and this file. No shared file touched; no
database change; still one GET.

**Decided by Stephen (2026-11-08):** a **Print button** — "Print all 8 kits" on the list,
"Print this kit" on a kit — that calls `window.print()`; and a print-only **"printed on"
line** at the bottom of every sheet ("Printed Nov 8, 2026 · from the Recipe Database"). No
"Built by" line, no tick boxes.

**What changed on the page.**
- `drawKit()` now wraps `kitHtml(kit, recipe, ids)`, which returns one `.kit-sheet`. The
  screen kit and all 8 printed sheets use it, so there is no second layout. Only the screen
  kit gets ids (`pan`, `unsorted`, `notFound`), so the print sheets never repeat one.
- The list holds a print-only `#printAll` (hidden on screen) with all 8 sheets, drawn when
  the list is drawn. A missing or unsorted kit prints as it shows on screen, so the paper
  says "tell a manager" too.
- The button is a `<button class="link-btn kit-print-btn">`: the shared outline look, 44px,
  no new colour. `kitchen.css` already hides `.link-btn` in print.
- `@media print` in the page's `<style>`: header, Back, button and the list are hidden;
  sheets 2–8 `break-before:page`; `break-inside:avoid` on each container, the pan step, the
  loud box and each left-out line; rings and the 4px "Not sorted yet" stay borders; greys
  `#000`/`#555`/`#bbb` only. Paper spacing is tighter than the screen, and on paper the
  "together / own container" note sits beside the container name. That is what fits Mac &
  Cheese (11 containers) on one page.

**Proved**

- Desktop Chrome, printed to PDF with background graphics off (US Letter): **8 pages from
  the list**, one kit each, in Line PM order; **1 page** from Mac & Cheese and from Pork
  belly. With Gastrique's recipe missing, or Pickled emptied, the list still prints 8.
  Screen spacing was 11 pages first; the tighter paper spacing fixed it.
- `check_kits.py`: **455 assertions, 19 scenarios, clean**. Headless Chrome can't switch to
  print media from inside the page, so the harness lifts every `@media print` rule (the
  page's and `kitchen.css`'s) into a plain `<style>` (needs `--allow-file-access-from-files`).
  New `print` scenario: list (8 sheets, in order, list hidden, page breaks), `#pork-belly`
  and `#mac-and-cheese` (1 sheet each, all 11 rings), and back to the list. In each: the
  button's label, ≥44px; header, Back and button hidden in print; the printed-on line on every
  sheet and hidden on screen; no printing element with a background fill or image; rings keep
  their digit and border; the button calls `window.print()` once and sends no request. Print
  checks added to `renamed`, `missing` and `archived` (the loud box prints with its heavy
  border). Every scenario still ends in `common()`: GETs only, exactly 1.
- **It fails when it should**, each in a throwaway copy: a background fill left on a ring in
  print, the list printing instead of the sheets, no page break between sheets, the Print
  button visible in print, the printed-on line missing. All caught.
- `check_styling.py`: clean, 14 pages.
- **Stephen's iPhone print-preview check, 2026-11-08, live:** "Print all 8 kits" showed all
  8 kits; Mac & Cheese → "Print this kit" showed only Mac & Cheese. Passed.

### Slice 5 — Ship it into the site *(shared files, last)*

- **Bring the branch up to date with `main` first.** Several windows add to the same shared
  files: the Inventory tile is already live (`7fbd499`, #166), and Costing, Schedule and Menu
  Builder are planned.
- `index.html`: the Kits tile becomes a link. It stays in "Recipes & Reference", unlocked,
  because staff use it. Whether the subtitle stays "Mise en place per recipe" is Stephen's call
  then.
- `BUILD_PLAN.md`: B5 status.
- `CLAUDE.md`: the page count. On 2026-11-02 it still says "ten" while `main` has eleven
  pages. Count the `.html` files on the day and write the true number. Costing alone adds
  one more page before Kits may land.
- `assets/kitchen.css`: add *kits* to the `used by:` banner of each shared section the page
  uses. Banners only, no rule changes.
- **Stephen opens the home page on a phone and taps the tile.** That push is the one that puts
  Kits in front of the staff.

### Slice 5 as built

`index.html`, `BUILD_PLAN.md`, `CLAUDE.md`, `assets/kitchen.css` (one comment), and this
file. `tempest_kits.html` and the guards are untouched; no database change.

**Decided by Stephen (2026-11-08):** the tile keeps its subtitle, **"Mise en place per
recipe"**.

**What changed.**
- `index.html`: the Kits tile in "Recipes & Reference" is now `<a class="tile"
  href="tempest_kits.html">`, as the Inventory tile became in #166: the same title and
  subtitle, no "Coming soon" pill, no `soon` class, no lock (staff use it), no
  `.tile-status` (the page has no daily state to report). No other tile changed.
- `BUILD_PLAN.md`: B5 marked done, with its PRs.
- `CLAUDE.md`: "ten" pages became **fifteen**, in all four places. Counted with
  `ls *.html | wc -l` at the repo root on 2026-11-08, `index.html` included, which is how
  `check_styling.py` counts (`glob("*.html")`); all fifteen link `kitchen.css`. The "75
  inputs on nine…" figures still match `FS_REGISTER` (75 entries on 9 pages), so they stayed.
- `assets/kitchen.css`: one banner. Every shared class the page uses (including those built in
  JS strings) was mapped to its section: `.header`, `.header-row` and `.home-link` sit in
  HEADER ("every page"); `.empty`, `.loading` and `.spinner` in EMPTY / LOADING ("every tool
  page"); print and reduced motion carry no `used by:` line. The one gap was **`.link-btn`**
  (Try again, the Print buttons), in COSTING MODAL, whose banner said `used by: costing`. It
  now says `used by: costing — .link-btn also kits`. Comment only: no rule change and no `?v=`
  bump, because nothing a browser draws changes. Every other `kit-*` class is the page's own.

**Proved**

- `check_kits.py`: **455 assertions, 19 scenarios, clean** (unchanged from Slice 4).
- `check_styling.py`: **clean, 15 pages** + `kitchen.css`; 99 inputs measured, 75 on the #135
  register.
- The home page rendered in headless Chrome: the Kits tile is an `<a>` to `tempest_kits.html`
  with the subtitle, and no pill, lock or status inside it.
- `git diff --stat` touched only the named files; `git diff assets/kitchen.css` is one
  comment line.
- Pending: Stephen's phone check (home page → Recipes & Reference → **Kits** → a kit →
  **← All kits** → back to home), once it is live.

---

## Later — not this build

- **The Line PM link** (the next step, named by Stephen): tapping "Kit – Pork belly" on Line PM
  opens `#pork-belly`. The item names don't match recipe names, so it needs a small item → kit
  map, in `tempest_line.html` and `tempest_prep.html` (they share the code) or as a column on
  `prep_items`. That is the shortcut Stephen described ("so they make sure everything needed
  has been kitted"), and the natural moment to reconsider ticks.
- **Ticks** on the kit sheet. Needs a table.
- **Manager-editable kits.** Needs a table; worth it once menu changes make code changes a
  chore.
- **Scaling** (×½, ×2).
- **Method steps** on the sheet (decided against for now).
- **A last-loaded copy for a dead spot** (the walk-in). Once loaded, the page stays on screen;
  only a reload with no signal fails, and it says so with Try again.
- **Other locations.** The read is location-scoped; kits are defined per recipe id, so another
  location brings its own list.
- **Where to pull each thing from.** Once Costing has linked a kit recipe's lines to the price
  list (and through it the order guide), a kit could say which shelf or cooler each ingredient
  comes from. Only for recipes Costing has fully linked (see "Overlap with Recipe Costing").

---

## Overlap with Recipe Costing

**What Kits relies on:**

1. `Recipes.ingredients` stays one text field, one ingredient per line, with `— PART —`
   headings.
2. Recipe ids 5, 54, 43, 14, 19, 25, 24 and 46 stay the same rows.
3. The ingredient names in those 8 recipes stay recognisable to the keywords above.

**Checked 2026-11-02 against Costing's plan** (`~/Developer/boxkitchen-costing/docs/recipe-costing.md`,
plan v1, written later that day, not yet approved). Costing also checked from its side, in its
"What Kits, Inventory and Menu Builder can rely on". **Compatible: no change for Kits.**

- **The ingredient list stays as it is.** Costing never alters `Recipes` and never writes to
  it. It keeps its own table beside the text, `recipe_lines` (one row per ingredient line it
  has linked to a price), plus `ingredient_conversions` and `recipe_yields`. All three needs
  above hold, and no ingredient name is rewritten.
- **Both use Chicken & Dumpling #19.** The duplicate (#52) is still worth archiving, but neither
  build waits on it.
- **The vague amounts** ("1 jug. honey", "1 ea. butter", Pork Belly's "thyme") need no recipe
  edit for Costing, which handles them with conversions. Kits shows them as written.
- **Editing recipe text stays safe for both.** It unlinks the edited line in Costing, which
  fails safe. In Kits it either still matches its keyword or drops to "Not sorted yet". Both
  pages refuse to show a stale answer, in their own way.

**Agreed, so the plans stay in step:**

- **Kits does not read `recipe_lines`.** Costing only holds lines Stephen has linked, so a
  recipe not yet set up has none. Read as a kit's ingredient list, it would look complete when
  it is not. Kits reads `Recipes.ingredients`, the text the cooks see. (Pointing containers at
  `recipe_lines` instead of keywords is possible once every kit recipe is fully linked. See
  "Later".)
- **If Kits ever wants structured ingredients to become the master** (replacing the text box,
  or editing amounts), that changes Costing's matching rule. Both plans change together;
  Costing's document comes first.
- **Kits does not touch `recipe_dashboard.html`.** If a later build does, Costing notes that a
  recipe used inside another can no longer be hard-deleted, and the page's "Delete failed"
  message would need to say why.

---

## Found while planning — not this build's to fix

- The duplicate Chicken & Dumpling recipes (above).
- 3 placeholder kit items on Line PM. When a real kit replaces one, it is a new kit here too
  ("Adding a kit").
- The Recipe Database can't open to a single recipe. Any future "see the full recipe" link
  needs that first.
- `CLAUDE.md` says "ten pages"; `main` has eleven (checked 2026-11-02 at `7fbd499`).

---

## Constraints

From `CLAUDE.md`, `docs/review-checklist.md`, and this window's rules:

- **Only files in `~/Developer/boxkitchen-kits`.** `index.html` is touched last, in Slice 5.
- **The database is live.** This page only reads; the guard proves it with a stubbed `api()`.
  Read-only GETs are fine; no test rows, ever.
- Links `assets/kitchen.css` and declares no `:root`. Page-only rules live in its own `<style>`.
- Never rename a class the JS reaches for. Never bulk-delete "unused" CSS.
- State is fill, weight and border, never hue.
- `python3 scripts/check_styling.py` before any PR.
- Never write the site password or the manager PIN anywhere.
- **Never push.** Pushing rebuilds the live site; Stephen approves that separately, every time.
