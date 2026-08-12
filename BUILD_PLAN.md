# Box Kitchen — Build Plan (updated 2026-07-21)

Ordering principle: **get Tempest airtight first** (correctness + daily-use polish),
then the bigger ops modules and "coming soon" build-outs, then multi-location **last**.
Each line item = **one build / one prompt** (per the working playbook). SQL-first where a
migration is involved. Goal tags: **[Consistency]** labor consistency · **[Cost]** food-cost
control · **[Time]** frees your time / remote · **[Sellable]** documented & scalable.

Effort: XS (minutes) · S (small) · M (medium) · L (large).

---

## ✅ Done
- **Build #1 — Order-submit email notifications.** Live via Supabase Edge Function
  `notify-order-submit` + Database Webhook + Resend. [Time]
- **Build #2 — Kitchen Notes & Issues email notifications (A4).** Live via Supabase
  Edge Function `notify-note-submit` + Database Webhook on `notes` (Insert) + Resend.
  Emails all categories to stephen@pourguys.com; one webhook covers all 5 note entry
  points (Notes page + the "+" modals on Line/Prep/Orders). No HTML changed. Still sends
  from `onboarding@resend.dev` (spam) until A3 verifies the domain. [Time]

---

## PHASE A — Make Tempest airtight (near-term, mostly the brain-dump)

### A1. Fix the Birite "items at the bottom under dry goods" bug  · ✅ DONE 2026-07-21 · [Consistency][Cost]
**Resolved:** diagnosis was NOT a mislabel — categories were correct. Root cause was
duplicate/interleaved `sort_order` (late-added Birite items got peg numbers colliding with
other shelves; the previous-order card sorts flat by `sort_order`, so food sank below
supplies). Fix = SQL renumber of Birite `order_items.sort_order` into contiguous gap-of-10
blocks in category order. Verified: shelves now non-overlapping (Cooler 840–1030 < Paper
Goods 1040+). Durable code hardening (group the previous-order card by category so it can't
re-drift when new items are added) folded into A5. Dairy was already clean. **Produce &
Protein guide also renumbered 2026-07-21** (Cooks Produce had Veggies 93–117 overlapping Dry
Storage 115–119; Schmitz/Asia were single-shelf) — all three produce vendors now clean
gap-of-10 blocks. Both order guides done.
_Original analysis below:_
Root cause (confirmed in code): the order guide groups items by the free-text
`order_items.category` value, and there is **no canonical category order** — a section
appears wherever its first item falls in `sort_order`, and new items get `sort_order =
max+1` (the end). So a mis-labeled food item (e.g. category `"dry goods"` / a typo /
blank) forms its own section that renders last.
- **SQL-first:** first list the distinct `category` values per vendor, correct the
  mislabeled food items with an `UPDATE`, and re-gap `sort_order` (10/20/30).
- **Optional code follow-up:** add a canonical category order so sections can't drift to
  the bottom again (this is really closed for good by A5).
- *Do this first — it's a correctness bug staff hit daily, and largely a data fix.*

### A2. Widen the "who" / assignee dropdowns so full names fit · XS · [Consistency]
Exact cause: `.who-select { width: 78px }` (hard cap) plus small font, in
`tempest_prep.html:91` and `tempest_line.html:93`. One-line CSS change per file (widen /
auto-size). No SQL. *Trivial quick win.*

### A3. Email deliverability — get alerts out of spam · ✅ DONE · [Time]
Resolved by the owner — alerts land in the inbox. **Closed — do not resurface as an open item.**

### ✅ A4. Kitchen Notes & Issues — email notification · M · [Time] — DONE 2026-07-21 (Build #2)
Same pattern as Build #1: a Database Webhook on the `notes` table → a new Edge Function →
Resend. High remote value (equipment down / 86'd items / urgent notes reach you
instantly). Cheap now that the Resend + webhook plumbing exists. SQL-first: none (webhook
config only). **DECIDED: email on ALL notes (every category).**

### A5a. Managed shelf (category) system — ORDER GUIDES · ✅ DONE 2026-07-22 (PR #75) · [Consistency][Sellable]
Shipped live on `tempest_orders.html`. New Supabase `order_categories` table (label +
sort_order + active, keyed by location/vendor; RLS mirrors order_units; seeded preserving
current on-screen order). `render()` now orders sections from the registry (graceful
fallback to first-seen if it doesn't load); manager-mode **"Manage shelves"** modal does
rename (with item-cascade, encodeURIComponent-safe), up/down reorder, add, retire; add-item
dropdown sourced from the registry (kills typo-shelves). Permanently fixes A1's root cause
on the order guides. Chose a managed **text registry** over a category_id FK (lower live-site
risk, graceful degradation). Design/plan: `~/.claude/plans/radiant-popping-scott.md`.

### A5b. Editable section headers — PREP LISTS · ✅ DONE 2026-07-22 (PR #76) · [Consistency]
Shipped live on `tempest_prep.html` (kitchen) and `tempest_line.html` (line). New Supabase
`prep_sections` table (label per location/team/category; RLS like the others; seeded to the
old defaults for both teams). Each page loads its own team's labels via `loadSections()`,
uses them in `render()` (escaped; fallback to hardcoded defaults if the table doesn't load),
and a manager-mode **"Section names"** modal (3 inputs) PATCHes them. Weekly keeps its auto
day prefix. Category keys (cleaning/daily/weekly) + shift/day logic untouched — labels only.
Kitchen & line have independent labels.

### A6. Group prep items by station · ✅ DONE 2026-07-23 (PR #78) · [Consistency]
Shipped live on both prep pages. New `prep_items.station` tag (salad/grill/saute/kits;
daily items only). Prep List renders as station sub-groups via `bDaily()` — Salad→Grill→Sauté
everywhere, Kits→Salad→Grill→Sauté on Line PM; color-coded (green/red/blue/purple) with
per-station done/total counts. Also shipped in the same PR: **View-as-Station filter**
(mirrors the cook filter), manager **assign-a-whole-station** (batch `assigned_to` on
prep_logs, confirm-gated), an add-item **station picker**, and reorder constrained
within-station (drag on prep, arrows on line). Graceful fallback → "Unassigned" group if a
tag is missing. 211 daily items mapped verify-first from real DB names; 8 junk rows deleted,
a few items recategorized. **Kit/Make toggle** also shipped (same PR): the 11 PM-line kit
items (station=kits) get a tap KIT⇄MAKE pill backed by per-day `prep_logs.mode` (resets
daily, any cook flips). Cleaning/Weekly, shift/day logic, Who, checkboxes, progress, confetti
all untouched.

### A7. Drag-to-reorder toggle (replace the slow arrows) · M · [Time] · ✅ DONE 2026-07-23 (all 3 pages)
**Line page ✅ DONE 2026-07-23 (PR #80, merged):** `tempest_line.html` now uses drag-to-reorder
(mirrors prep) — ▲▼ arrows removed, SortableJS + drag grip + `initSortables()`/`persistOrder()`
ported from prep, `mItem()` deleted. Manager-mode-only + within-station; no SQL needed
(persist self-heals legacy sort_order); Line loads only team=line so kitchen order untouched.
**Order Guide ✅ DONE 2026-07-23 (PR #81):** `tempest_orders.html` — same drag ported; extra
step was wrapping each shelf's rows in a new `.shelf-body` container (they were flat siblings in
`.vendor-body`) so SortableJS has one list per vendor+category. Drag-only (arrows removed),
within-shelf/vendor, manager-mode only, no SQL. Manage Shelves modal's own `.move-btn` untouched.
**Prep, Line, and Orders now all reorder identically. A7 complete.**
**DECIDED:** reordering is **manager-mode only** (which already exists on the site) — staff
can never reorder. Behind that switch, drag is the primary gesture (grab handle, slide).
Rollout order for ease + low upkeep: **prep first** (already has drag; just gate it behind
the manager switch) → **line next** (same codebase as prep, inherits cheaply) → **order
guide last & carefully** (live service screen — accidental slides riskiest). **Keep arrows
as fallback** on any page where full drag isn't safe. SQL-first prep: re-gap `sort_order` to
even tens (10/20/30) so items always have room to slide between.

### ✅ A8. Confetti / reward at 75% / 90% / 100% prep completion · S · [Consistency] — DONE 2026-07-22 (PR #74)
Live on **both `tempest_prep.html` and `tempest_line.html`**: confetti burst + milestone
banner at 75/90/100%. Fires once per upward crossing from a check-off; silent on load,
un-check, and shift/filter switches. Self-contained vanilla JS (rAF canvas + banner, no
libraries). PR #74 also shipped the `tempest_notes.html` delete-confirmation message.

---

## PHASE B — Bigger modules & "coming soon" build-outs (after Tempest is airtight)

- **B1. Prep shift hand-off + history** (roadmap #2). [Consistency][Time]
- **B2. Prep hand-off email notification** (roadmap #3) — reuses A4's plumbing. [Time]
- **B3. Inventory Guide** (coming-soon card; roadmap #4 monthly inventory). [Cost]
- **B4. Recipe Costing v1** (coming-soon card; roadmap #5) — manual pricing tied to
  invoices; live food cost. Depends on recipes being complete. [Cost][Sellable]
- **B5. Kits** (coming-soon card) — mise en place per recipe; depends on the recipe
  library. [Consistency]
- **✅ B6. Flash Reports — DONE 2026-07-23 (PR #77).** Live `tempest_flash.html` (PIN-gated,
  linked from the Admin card): daily food-cost entry (per-vendor invoices + food sales) with
  live daily/running %, month report (daily grid + weekly summary + vendor breakdown),
  manager vendor editor, and monthly Excel export (vendored SheetJS). Manual-entry data source
  (POS integration deferred). New Supabase `flash_vendors` + `flash_days` tables. [Cost][Time]

### Parallel / ongoing track
- **Recipes into the library** (brain-dump #9). *Correction:* recipes are **already in a
  Supabase table `Recipes`** (not hardcoded — CLAUDE.md is out of date). So adding recipes
  = inserting rows (batch SQL, or the in-app Add modal). Easy; do in batches as you paste
  them. Feeds B4 (costing) and B5 (kits). [Consistency][Cost][Sellable]
- **Color / layout refresh** (brain-dump #6, "eventually"). Best done as a systematized
  design pass **before** multi-location so all four bars inherit it. Deferred. [Sellable]

---

## PHASE C — Multi-location rollout (LAST)
Roll the airtight, systemized Tempest out to **Showdown, Louie's, CT Yankee**. A5's
editable section model + A6's station model make this clean. Do only after Phase A/B are
stable. [Sellable]

---

## Decisions locked (2026-07-21)
1. **Four prep lists** = Kitchen Prep, Kitchen Cleaning, Line Prep, Line Cleaning. (A6)
2. **Notes email** = all notes, every category. (A4)
3. **Reorder** = manager-mode only (staff can't reorder); drag primary, arrows as fallback
   where drag isn't safe. (A7)
