# Last done — every prep task says when it was last done, and a built kit says "make today"

Status: **plan v1, 2026-11-20; Slice 1 built (see the end).** Written in the Last Done planner window from Stephen's requests
and answers on 2026-11-20. Every decision in the Decisions table is Stephen's; everything under
"Planner rulings" is the planner's, with the reason. It goes into the repo as `docs/last-done.md`
with Slice 1's PR. Nothing is built yet.

It is part of BUILD_PLAN **B1, Prep shift hand-off + history** (`~/Developer/PROJECT-LIST.md`
item 3, "WANTED SOONER"). B2, the nightly prep email (item 2), comes later and is not in this plan.

---

## What it is for

Stephen, 2026-11-20: "the prep sheets stating when the prep task was previously done. For
example if parm cubes where cut on the 19th then on the 20th it would state that parm cubes
were done yesterday. also if a kit was made on the 19th then on the 20th it will show up as
needing to make." Why: "It is getting hard for me to keep up with what was done and not done
each day without having to look back which can be a bit time consuming."

Today each list shows only the day on screen. To know whether Parm cubes was done yesterday,
you tap ◀ and look. This puts the answer on the row, under every task on both prep pages:

```
[ ]  Parm cubes                 [Jose   ▾] [Qty] [📝]
     Last done: yesterday · Jose
[ ]  Clean shallots             [Who    ▾] [Qty] [📝]
     Last done: Tue 11/17 · 3 days ago
```

A skipped task stands out on its own, because it says "3 days ago" where its neighbours say
"yesterday".

Kits: the PM line checks "Kit - Pork belly" when it builds the kit. The pan sits in the cooler
overnight. The next morning, the kit's own row on the **Line AM** list ("Cook pork belly")
says so:

```
[ ]  Cook pork belly            [Who    ▾] [Qty] [📝]
     KIT READY  Kit built yesterday · Jose
```

---

## Decisions (Stephen, 2026-11-20)

| question | decided |
|---|---|
| What the note says | **When + who**, e.g. "Last done: yesterday · Jose". |
| What counts as done | **Only a checked-off task.** A Who picked or an amount typed, without the check, does not count. |
| Which tasks | **Every task, both pages**: `tempest_prep.html` and `tempest_line.html`, prep and cleaning. A skipped task stands out because it says "3 days ago" instead of "yesterday". |
| Kits | A kit checked off on Line PM on the 19th shows on the 20th as **needing to be made**, because its pan is waiting in the cooler. |
| Where the kit shows (asked 2026-11-20) | **On the kit's existing row on the Line AM list** ("Make - Mac and cheese", "Cook pork belly", "Buffalo sauce"…), as a bold **KIT READY** on its note line. Not on the Prep page: Prep has no task for making any kit recipe (see ground truth). |
| The KIT/MAKE pill (asked 2026-11-20) | **MAKE means the PM cook made the recipe instead of kitting it, so nothing is waiting.** A kit row checked while its pill says MAKE puts no KIT READY on the morning row. A row checked on KIT (the normal case) does. |
| When | **Start now**, alongside the Schedule and Recipe Costing builds. |

*Correction to the pill question as asked:* Stephen was told the pill had been flipped to MAKE
6 times, not since Sept 18. That read hit the 1,000-row cut-off (below). The full history is
**13 times**, most recently 11/16 and 11/17 (Suadero, note "cook"), and one MAKE row's note
reads "Make the spicy green sauce." That supports the meaning he chose. He was told this when
the plan was handed over.

---

## Ground truth — read-only GETs, 2026-11-20

**Two corrections to the planner brief, both from the same cause.**

1. **The server answers at most 1,000 rows per request.** A read with no `limit`, or with
   `limit=5000`, comes back with `Content-Range: 0-999/<total>`, and nothing says it was cut.
2. **Every day is worked.** The brief's per-day counts ("11-14: none, 11-16: 3, 11-18: none")
   came from a read that hit that cut-off. Counted page by page, every day since 10/01 has
   about 200–250 check-offs: 11/14 had 214 (Line 114, Prep 100), 11/16 had 251, and 11/18 had 243.
   So "yesterday" is the normal case, and the new read **must page** past 1,000 rows or it
   will quietly report tasks as not done.

**`prep_logs`**: columns `id, prep_item_id, date, completed, assigned_to, quantity, notes, mode,
special_text, created_at`. No team or location column, so a page's rows are picked out by
`prep_item_id`. History starts 2026-04-30 (35,936 rows, 33,448 completed).

| fact | number | what it means here |
|---|---|---|
| Check-offs per day, Line | 101–140 (Oct–Nov) | |
| Check-offs per day, Prep | 79–128 | |
| The proposed 14-day read, Line (205 tasks) | 1,789 rows · 2 requests · 7.2 KB on the wire (gzip) · 0.59 s | measured |
| The proposed 14-day read, Prep (163 tasks) | 1,461 rows · 2 requests · 6.4 KB · 0.42 s | measured |
| Check-offs with **no Who** (Oct 1 – Nov 20) | 7,443 of 11,222 (**66%**) | two notes in three will show the day only |
| Same task, same day, two rows (11/06–11/20) | 40 pairs | pick a non-blank Who from that day |
| Rows not checked (Who/amount only, or ticked then unticked), 11/06–11/20 | 194 | must not count |

**The pages** (`main` at `ad3ee57`):
- The two pages are the same code apart from the team (`kitchen` / `line`), Line's Kits station
  on PM, Line's `#pm` open and its SHEET → button (`docs/kits-line-link.md`).
- Load: `prep_items` → `staff` → `prep_sections` → `loadLogs()`, which reads one day
  (`api('GET','prep_logs','date=eq.'+dateStr,…)`) and calls `render()`. ◀ ▶ and
  "↩ Back to today" call `loadLogs()` again. AM/PM only re-renders: no read.
- A row (`bTask()`): `.task` is a flex row: drag handle (manager only), `.checkbox`,
  `.task-info` (`.task-name` + the hidden rename input `#ni<id>`, then SHEET → on Line PM kits),
  `.task-fields` (Who 132px, Qty 48px, 📝, ✕ manager only). `.note-row` follows as a sibling.
  `saveN()` finds the name again through `#ni<id>.previousElementSibling`.
- **At a 390px phone the name column is 96px wide** (measured on a stubbed copy). Names are
  already cut to "Make - Chick…". A note squeezed in there wraps to 2–3 lines. On its own
  full-width line under the row, it reads in one line and moves nothing (planner rendered
  three positions; picture B won).
- Guards: `scripts/check_line.py` covers Line (18 → 154 assertions, Kits link); it answers
  every `prep_logs` read with `[]`. **Nothing guards `tempest_prep.html`** except
  `check_styling.py`.

**Kits: what is really there.** The 11 kit rows on Line PM are unchanged from
`docs/kits-line-link.md` (668–678). **No Prep (kitchen) task makes a kit recipe.** Prep has only side
steps ("Wrap pork belly", "Shallots for gastrique"). Every kit recipe has its own row on the
**Line AM** list, every day, and the morning crew checks it almost daily:

| kit row (Line PM) | its morning row (Line AM) | station | kit checked | make checked |
|---|---|---|---|---|
| 668 Kit - Mac and Cheese | 571 Make - Mac and cheese | Sauté | 34 / 50 days | 46 / 50 |
| 669 Kit - Buffalo sauce | 583 Buffalo sauce | Grill | 35 | 44 |
| 670 Kit - Pork belly | 573 Cook pork belly | Sauté | 38 | 49 |
| 671 Kit - Gastrique | 615 Bacon Gastrique | Grill | 34 | 50 |
| 672 Kit - Chicken & Dumpling soup | 620 Make - Chicken and Dumpling soup | Sauté | 36 | 49 |
| 678 Kit - Dumpling | 570 Make - Dumpling | Sauté | 41 | 47 |
| 673 Kit - Spicy green sauce | 567 Make - Spicy green sauce | Sauté | 42 | 45 |
| 674 Kit - Pickle onions& peppers | 568 Make - Pickle peppers & onions | Sauté | 45 | 48 |
| 675 Kit - Suadero | 759 Cook Suadero | Sauté | 43 | 46 |
| 676 Kit- Chilorio | 596 Cook Chilorio pork | Sauté | 46 | 49 |
| 677 Kit- New prep coming soon | — (placeholder) | | 47 | — |

(50 days = 10/01–11/19.) Two things Stephen may want to know, neither of which changes the build:
- **The placeholder 677 is ticked 47 nights out of 50**, so a tick on the kits station isn't
  always a real build.
- **Spicy green sauce** came off the menu on 11/16, but its kit row and its make row were both
  checked every day through 11/19 (11/20's make row too).

**The KIT/MAKE pill** (`prep_logs.mode`, kit rows only, resets daily): set on 26 rows ever, 13
of them MAKE (all checked), most recently 11/16 and 11/17. Never on a non-kit row.

---

## The design

### Slice 1: the Last done line (both pages)

**The read.** It runs once per day shown, right after that day's list has drawn, so the list
appears exactly as fast as today:

```
prep_logs?prep_item_id=in.(<this page's tasks, specials left out, ascending>)
  &completed=eq.true
  &date=gte.<viewed day − 14>&date=lt.<viewed day>
  &select=prep_item_id,date,assigned_to,mode
  &order=date.desc,id.desc
  &limit=1000&offset=0        ← then 1000, 2000… while a full page of 1,000 comes back (max 5)
```

It goes through the page's own `api()`, GET only. From it, each task's **latest day** before the
viewed day, that day's **Who**, and its **mode** (kept for Slice 2). One read covers both shifts,
so AM/PM switches need nothing new. ◀ ▶ makes one new read for the new day.

**The words** (counted from the day being viewed, not from today):

| latest check-off before the viewed day | the line reads |
|---|---|
| the day before | `Last done: yesterday · Jose` |
| 2–14 days before | `Last done: Tue 11/17 · 3 days ago · Jose` |
| no Who on that day's check-off | the same without ` · Jose` |
| none in the 14 days before | `Not done in the last 2 weeks` (a brand-new task says this too, and it's true) |
| the read hasn't landed, failed, or was cut short | nothing (the line stays blank) |
| a Specials row | no line at all |

**Where and how it looks.**
- Its own line, the last thing inside the row (`.task`), full width, lined up under the task
  name: `<div class="last-done">…</div>`. A page-only `.task{flex-wrap:wrap}` lets it drop to
  its own line. Checkbox, name, Who, Qty and 📝 stay exactly where they are. It's not inside
  `.task-info`, so `saveN()`'s `previousElementSibling` and the SHEET → button are untouched.
- 12px (`0.75rem`), `var(--grey)` (5.18:1), one line, cut with "…" if it ever runs long. No new
  colour, no weight change. It prints as plain text: it's useful on paper, and it uses no
  background.
- **Space is reserved**: the line is there, blank, from the first draw, so rows don't jump when
  the read lands, and checking a box never changes a row's height.

### Slice 2: KIT READY on the Line AM row (Line only)

- A map in `tempest_line.html`, `KIT_MAKE`, keyed by kit row id: its morning row's id, plus
  a word each name must still contain (case, punctuation and spacing ignored), so a renamed row
  drops out instead of pointing at the wrong dish. That's the same trick as `KIT_SHEETS`. 10 pairs, from the table
  above: 668→571 `mac` · 669→583 `buffalo` · 670→573 `pork belly` · 671→615 `gastrique` ·
  672→620 `soup` · 678→570 `dumpling`, not `soup` (both sides) · 673→567 `green` ·
  674→568 `pickle` · 675→759 `suadero` · 676→596 `chilorio`. 677 has no entry.
- **The rule**, for the viewed day: the kit row's latest check-off (from Slice 1's read) is **on
  or after** its morning row's latest check-off (or the morning row has none in the 14 days),
  **and** that kit check-off's pill was not MAKE. Then the pan is still in the cooler. "On or after"
  because the morning makes the recipe at the start of a day and the PM builds the next kit at
  the end of it. A pan built two nights ago and never made still shows, with its real day:
  `KIT READY  Kit built Wed 11/18 · 2 days ago`.
- **What shows**: on the morning row, the Last done line becomes
  `[KIT READY]  Kit built yesterday · Jose` (Who = the PM cook who checked the kit). KIT READY
  is an outlined ink tag, bold condensed capitals: no fill, so it prints, and no hue. It stays
  all day, also once the morning row is checked (the strike-through says it's done).
- **No new request.** Slice 1's read already holds both rows.

No database change, no SQL, no new table, no change to `assets/kitchen.css`, `index.html`
untouched.

---

## Planner rulings

1. **Window: the 14 days before the viewed day.** Weekly tasks come round every 7 days, so 14
   still shows a weekly task skipped once. Past two weeks the exact day stops mattering: it's
   overdue. Cost: about 1,800 rows (Line) / 1,500 (Prep), 2 requests, 7 KB, half a second,
   after the list is on screen.
2. **Page the read.** 1,000 rows a request (the server's cap), newest first, with `id` as the
   tie-break so pages don't overlap. Ask for the next page while a full one comes back, at most
   5. If the 5th is still full, treat the read as cut short. **Never say "Not done" from a read
   that failed or was cut short**: the line stays blank, with no toast. The list still works.
3. **Count calendar days, show the real weekday.** Every day is worked (ground truth), so
   "yesterday" is the norm. If one ever isn't, the weekday shows the gap.
4. **Dates by their parts.** Parse `YYYY-MM-DD` as year, month, day, never `new Date('YYYY-MM-DD')`
   (that is UTC midnight: the day before in San Francisco). Build the window and count "days
   ago" by calendar, so a clock change (Nov 1 2026, Mar 14 2027) never shifts a day. The guard
   pins the clock and runs Chrome in `America/Los_Angeles`, so CI (UTC) sees what the kitchen
   sees.
5. **Fill in place, never redraw.** When the read lands, the page writes each row's line into the
   existing `.last-done` element. No `render()`, so a Qty or note being typed is never wiped, and
   progress and confetti are untouched. `bTask()` draws the line from the same function, so the
   two can't disagree.
6. **A late answer is thrown away.** Each read carries the day it was for. If the day on screen
   has changed (◀ tapped twice fast), its answer is dropped. A date change blanks the lines
   until the new read lands, so another day's notes are never shown.
7. **Today's own check-off doesn't change the line.** It's about before today. Checking a box
   never moves anything.
8. **Who**: from that day's check-off. If that day has two rows, a non-blank Who wins.
   Escaped like every other name on the page.
9. **Specials rows get no line.** Their text changes every day.
10. **`mode` is read from Slice 1**, unused until Slice 2, so Slice 2 doesn't touch the read.
11. **One code block, two copies.** The last-done code is the same in both pages, between
    `// LAST DONE start` / `// LAST DONE end` markers (and `/* LAST DONE start */` … in each
    `<style>`). The guard fails if the two copies differ. Each page has a one-line
    `ldNote(id)` outside the block, which Slice 2 widens on Line for KIT READY, so the copies
    stay identical.
12. **One guard for both pages**: a new `scripts/check_last_done.py`, running the same scenarios
    on each page, with its own workflow. `check_line.py` is unchanged and must still pass.
    Prep gets its first behaviour guard.
13. **`.task{flex-wrap:wrap}` is a justified page override**, recorded in `docs/page-restyle.md`.
    Known edge: on a 320px phone in manager mode the row's fields already overflow; with wrap
    they drop under the name instead. No current kitchen phone is that narrow.
14. **Kits map includes Spicy green sauce** (673→567): both rows exist and are checked daily.
    It drops out by itself when the menu update renames or removes them.
15. **KIT READY replaces the morning row's Last done line** on days a kit is waiting. On a
    Line PM kit row itself, nothing changes beyond its own Last done line.
16. **Docs**: `docs/last-done.md` (this plan + "as built") in Slice 1's PR. Slice 2's PR also
    updates `docs/kits.md` "Adding a kit" (add the pair to `KIT_MAKE`) and BUILD_PLAN **B1**.

---

## Slices

**Two, each small.** Every slice is its own PR from `origin/main`, names its files up front,
adds its promises to the guard, passes `check_styling.py` and `check_line.py`, and **stops
before pushing**.

### Slice 1: the Last done line (both pages; the crew sees it on merge)

- `tempest_prep.html`, `tempest_line.html`: the shared block, the hook in `loadLogs()`, the line in
  `bTask()`, `ldNote()`, the page-only rules. Nothing else.
- `scripts/check_last_done.py` (new) + `.github/workflows/last-done-guard.yml` (new):
  yesterday, 3 days ago, 14 and 15 days ago, a blank Who, a ticked-then-unticked task,
  duplicate rows, nothing found, a Specials row, a weekly task, a past date, a read that needs
  two pages, a failed read, a late answer after ◀ ◀, typing in Qty while the read lands, a
  clock change, the phone layout, and GETs only. Plus "fails when it should" copies.
- `docs/last-done.md` (new), `docs/page-restyle.md` (one line).
- **This merge puts the line under every task on both pages, in front of the whole crew.**
  Stephen's phone check: a task he knows was done yesterday, one he knows was skipped, a past
  date, Line PM's kit rows, the Prep page, and Dark Mode.

### Slice 2: KIT READY on the Line AM row (Line only; the morning line sees it on merge)

- `tempest_line.html`: `KIT_MAKE`, the rule, the tag, one page-only rule, `ldNote()` widened.
  Prep untouched. No new request.
- Guard scenarios: built last night → tag; built 2 nights ago, not made → tag with its day;
  built 2 nights ago, made yesterday → no tag; made yesterday morning and built yesterday
  evening → tag; checked on MAKE → no tag; Who picked but not checked → no tag; either row
  renamed → no tag; 677 ticked → nothing; PM view → no tag; a past date; the tag whole at
  390px and outlined in print; no extra request.
- `docs/kits.md` "Adding a kit": add the pair to `KIT_MAKE`. BUILD_PLAN B1 line.
- Ticket written after Slice 1 is live and phone-checked.

---

## Constraints

- Both pages are live in every service. Smallest change that works. Rename no class, and change no
  existing `api()` call. Check-off, Who, Qty, notes, Assign ▾, KIT/MAKE, SHEET →, reorder,
  Specials, the progress bar and confetti all keep working. The guard proves nothing is written.
- **Never write to the database**, from the build window or the guard: GETs only, no test rows.
- No new input, so the 16px rule (#135) isn't touched.
- No `:root`, no hue, no class renamed; `kitchen.css` unchanged.
- Never write the manager PIN or site password anywhere. Grepping these pages prints them, so
  filter with `grep -v -i 'pin\|password'`.
- Never `git add -A`. Merge `origin/main` before pushing. Never rebase, reset or force-push. Ask
  before every push, PR and merge.

## Later — not this plan

- **B2: the nightly prep email** (PROJECT-LIST item 2). It can reuse this read's idea.
- **Item 1: the usual cleaning crew fills itself in.** It would raise the 34% of check-offs that
  carry a Who.
- **A database view for "last done"** (one row per task) if the lists ever outgrow two pages.
  Today it would be a schema change for no gain.
- **Promote `.last-done` into `kitchen.css`** at the next `?v=` bump (e.g. the #135 pass).
- **Kits menu update** (`docs/kits-line-link.md` "Later"): when 673 goes, its `KIT_MAKE`
  pair goes with it.

---

## Status

**Slice 1 BUILT 2026-11-20 on `prep-last-done`, not pushed.** Slice 2 not started.

## Slice 1 as built

**`tempest_line.html`, `tempest_prep.html`** (about 50 lines each, the same change in both):
- `<style>`: `/* LAST DONE start */ … /* LAST DONE end */`: `.task{flex-wrap:wrap}` and `.last-done`
  (full width, `padding-left:34px`, 64px in manager mode, 0.75rem, `var(--grey)`, line-height
  1.25, `min-height:1.25em`, one line with ellipsis, `margin-top:-4px`).
- `// LAST DONE start … // LAST DONE end`, byte-identical in both pages: `LD` (the day the
  result is for, and the map), `ldParts`, `ldDays` (calendar days by `Date.UTC`), `ldText` (the
  words; empty unless `LD.day` is the viewed day), `ldFill` (writes into existing lines, no
  `render()`), `ldLoad` (the paged GET; drops an answer whose day is no longer on screen, or that
  isn't an array; a 5th full page leaves the lines empty).
- Outside the block, only: `ldLoad();` after `render()` in `loadLogs()`'s callback; the line in
  `bTask()` as the last child of `.task` (not on Specials); `function ldNote(id){return ldText(id);}`.

**`scripts/check_last_done.py`** + **`.github/workflows/last-done-guard.yml`**: 13 scenarios
(`words past paged cut fail failp2 race typing dst dst2 phone phonemgr tap`) on both pages, plus
the `copies` check: **1,297 assertions**, clean. Clock pinned, Chrome in `America/Los_Angeles`,
the stub answers `prep_logs` like the server (filters, order, limit/offset, 1,000-row cap),
refuses every write.

**Fails when it should** (each a throwaway copy in the scratchpad; all 13 fail):
1 `completed=eq.true` dropped · 2 counting from today (`past`) · 3 `lte` for `lt` · 4 no paging
(`paged`) · 5 "Not done" on a failed (`fail`) or cut (`cut`) read · 6 `new Date('YYYY-MM-DD')`
weekday · 7 days ago from ms rounded down (`dst`) · 8 `render()` on landing (`typing`) · 9 a
late answer applied (`race`; needed a task ticked only 11/18 and two taps 0.1s apart, since two
taps in the same instant never send an 11/19 read) · 10 the line inside `.task-name`, or between
it and `#ni<id>` (`phone`) · 11 a line on Specials · 12 a write on load · 13 the copies differing
by one character.

**Hand check** (local Chrome, live data, read-only; nothing tapped that saves): Line, 74 rows
all with a line (Parm cubes "Last done: yesterday"); ◀ to 11/19 recounts from that day and agrees
with that day's tick; PM kit rows show the line, SHEET → still in `.task-info`; AM/PM sent no
request; load = the same reads plus the new read in 2 pages; ◀ = one day read plus 2 pages; no
writes. Prep, 55 rows all with a line, with Who where picked. Not seen by hand: a true 390px
window (Chrome wouldn't go below ~830px), Slow 4G, print preview, a Specials row; the guard covers
the first, the reserved space and Specials.

**Found, not this slice's:** on Line PM in manager mode at 390px, the name column is ~39px and
SHEET → (59px) spills past `.task-info` (still inside its row). Already so on `main` `ad3ee57`.
The guard checks the stricter rule in staff mode only.

**`docs/page-restyle.md`**: one sentence in "Justified page overrides".
