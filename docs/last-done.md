# Last done — every prep task says when it was last done, and a built kit says "make today"

Status: **Slice 1 LIVE (#193, 2026-11-21). Slice 1b LIVE (#194, `58d9235`, 2026-11-22), phone check passed 2026-11-22. Slice 2 BUILT 2026-11-22 on `prep-last-done-2`, not pushed.** (Plan v1 2026-11-20, changed 2026-11-21 and 2026-11-22.) Written in the Last Done planner window from Stephen's requests
and answers on 2026-11-20. Every decision in the Decisions table is Stephen's; everything under
"Planner rulings" is the planner's, with the reason. It goes into the repo as `docs/last-done.md`
with Slice 1's PR. Slice 1 is built: see "Slice 1 as built" at the end.

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
| What counts as done | ~~Only a checked-off task.~~ **Changed 2026-11-21: a tick with a name in Who.** A tick with no name means "not needed". A Who picked or an amount typed without the tick still doesn't count. See "Change, 2026-11-21". |
| Which tasks | **Every task, both pages**: `tempest_prep.html` and `tempest_line.html`, prep and cleaning. A skipped task stands out because it says "3 days ago" instead of "yesterday". |
| Kits | A kit checked off on Line PM on the 19th shows on the 20th as **needing to be made**, because its pan is waiting in the cooler. |
| Where the kit shows (asked 2026-11-20) | **On the kit's existing row on the Line AM list** ("Make - Mac and cheese", "Cook pork belly", "Buffalo sauce"…), as a bold **KIT READY** on its note line. Not on the Prep page: Prep has no task for making any kit recipe (see ground truth). |
| The KIT/MAKE pill (asked 2026-11-20) | **MAKE means the PM cook made the recipe instead of kitting it, so nothing is waiting.** A kit row checked while its pill says MAKE puts no KIT READY on the morning row. A row checked on KIT (the normal case) does. |
| When | **Start now**, alongside the Schedule and Recipe Costing builds. |
| How old a kit can be and still show (asked 2026-11-22) | **Up to 2 days**: built last night, or the night before if no morning has made it since. Older kits show nothing. See "Slice 2 check, 2026-11-22". |

*Correction to the pill question as asked:* Stephen was told the pill had been flipped to MAKE
6 times, not since Sept 18. That read hit the 1,000-row cut-off (below). The full history is
**13 times**, most recently 11/16 and 11/17 (Suadero, note "cook"), and one MAKE row's note
reads "Make the spicy green sauce." That supports the meaning he chose. He was told this when
the plan was handed over.

---

## Change, 2026-11-21: a tick alone doesn't mean done

Stephen, 2026-11-21: "we check off all prep each day even if it does not need done that way they
hit the goal of completing the task at the end of the night at 100%, if they actually check
everything off. also it makes the prep sheet easier to read if items that are not needed are
checked off as well."

And to the build window, after Slice 1 went live: "boxes that are not asigned to anyone get check
off and then the next day say 'done yesterday'. id rather see that it was not done yesterday and
when it was actully last done."

So a tick means "dealt with", not "made". Slice 1 as built counts any tick, so most lines say
"yesterday", and Slice 2 would put KIT READY on every kit every morning (the placeholder kit is
ticked most nights). Asked what should count, **Stephen chose: a tick with a name in Who**. The
crew keeps ticking everything for 100%, and picks their name on what they actually made or
cleaned.

**Read-only GETs, 2026-11-21, that back it:**

| fact | number |
|---|---|
| Morning lists ticked | 100% most days (Line AM 74/74, 77/77, 76/76; Prep AM 55/55, 62/62). PM lists 74–98%. |
| Ticks with a name, last 30 days | Line prep 29%, Prep prep 28%, Line cleaning 84%, Prep cleaning 63%, Prep weekly 54% |
| Ticks with an amount (Qty) | Line prep 1%, Prep prep 9%, cleaning 0%: no use as a signal |
| Is Who set for a whole station at once ("Assign ▾")? | No: in 93% of station-days some rows have a name and some don't; 0% look like Assign ▾ |
| Placeholder kit 677 | ticked 28 times in 30 days, **never** with a name |
| Kit rows / their morning rows with a name | 29% / 30% |
| The read, named ticks only (14 days to 11/21) | Line 627 rows, Prep 539: **one request each** (was 2) |
| `assigned_to=neq.` on the server | works; drops `''` and `null`; no space-only names in the data |

**What the lines will say the day 1b goes live** (Sat 11/21, from those reads):

| list | rows | yesterday | 2–6 days | 7–14 days | Not done in the last 2 weeks |
|---|---|---|---|---|---|
| Line AM | 74 | 24 | 26 | 6 | 18 |
| Line PM | 68 | 17 | 26 | 9 | 16 |
| Prep AM | 59 | 21 | 9 | 9 | 20 |
| Prep PM | 56 | 30 | 11 | 5 | 10 |

A real mix, not a wall of "not done", and it sharpens as the crew picks Who.

**Rulings for the change:**
- **The read gains `assigned_to=neq.`** (the server leaves out ticks with no name). Each row is
  also skipped if its name is only spaces. Everything else in Slice 1 stays: the words, the
  14 days, paging, fill in place.
- **"Not done in the last 2 weeks" now means "no named tick in 2 weeks"**, the same words.
- **Assign ▾ fills every row's Who in a station**, so a station assigned that way counts as
  done wherever it's ticked. Nobody uses it that way today (0% of station-days). Stephen
  should know before using it.
- **PROJECT-LIST item 1 (names fill themselves in) now clashes with this.** If Who is filled
  automatically, every tick would count as done. Item 1 must be redesigned before it's built.
- **Slice 2 inherits it**: a kit counts as built only when its row is ticked with a name, and as
  made only when its morning row is ticked with a name. The PM line must pick a name on the
  kits it really built.

**Settled with Stephen, 2026-11-21 (after the build window's note
`~/Developer/LAST-DONE-NOTE-NAMED-TICKS.md`):**
- **Slice 1's phone check passed** ("looks as you stated").
- **Shared entries count.** The Who list holds about 30 entries naming several people ("Rubi,
  Jose & Isaac", "Gilberto, Vidalio & Evelin"). Stephen's "if its the whole crew and it gets
  ticked off then yes it is done" meant these. They're names, so they count, with no special
  handling. A long one may end in "…" on a phone.
- **"Everyone"** is already in the Who list on both shifts (picked once in 30 days). **No special
  handling for now** (Stephen: "we can worry about the everyone later on"). It's an entry like
  any other, so a tick with it counts.


---

## Slice 2 check, 2026-11-22: KIT READY under the named-tick rule

Slice 2's rule was written before 1b. Re-run on live data (read-only GETs, all 646 rows of the
20 paired rows since 10/20) with only named ticks counting, it found one problem: **no age
limit.** A kit ticked with a name, whose morning row is then only ticked bare, stayed KIT READY
for the whole 14-day window. Pickle (674) showed on every morning 11/06–11/13, reaching "Kit
built 14 days ago". Asked how old a kit can be, **Stephen chose up to 2 days.**

| fact | number |
|---|---|
| The 20 paired rows | all exist, names unchanged (kits `station` `kits` PM; morning rows `saute`/`grill` AM) |
| Kits ticked a night (10 paired kits) | 5–10; **with a name: 1–7, about 4 in 10** |
| Morning rows ticked a day | 9–10 of 10; **with a name: 1–6, about 1 in 3** |
| Names on kit rows (since 10/20) | Gilberto 37, Pablo 17, Chepe 15, Evelin 13, Eddy 3, Carlos 2, "Gilberto & Chepe" 2 |
| KIT/MAKE pill set since 10/20 | 4 times: KIT 11/09 (675), KIT 11/16 (670), **MAKE 11/16 and 11/17 (675, Suadero)**, all named |

**What the morning would have seen** (final rule: named ticks, up to 2 days, MAKE excluded):

| morning | tags | | morning | tags |
|---|---|---|---|---|
| Mon 11/09 | 1 | | Mon 11/16 | 4 |
| Tue 11/10 | 2 | | Tue 11/17 | 4 (Gastrique 2 days) |
| Wed 11/11 | 3 | | Wed 11/18 | 3 |
| Thu 11/12 | 4 | | Thu 11/19 | 8 (Pickle 2 days) |
| Fri 11/13 | 5 | | Fri 11/20 | 4 (Pork belly 2 days) |
| Sat 11/14 | 3 | | Sat 11/21 | 5 |
| Sun 11/15 | 2 | | Sun 11/22 | 3 (Chilorio 2 days) |

About 4 a morning, nearly all "yesterday". Under "any tick" it would have been 5–10 every
morning, all "yesterday", which is the problem 1b fixed. **Kits ticked with no name don't
show** (3–9 a night today), so the PM line must pick a name on the kits it really builds, and
the morning on what it really makes, or a tag stays up to 2 days.

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

*Rewritten in v3 (2026-11-22) for the named-tick rule and the 2-day limit.*

- A map in `tempest_line.html`, `KIT_MAKE`, keyed by kit row id: its morning row's id, plus
  a word both names must still contain (case, punctuation and spacing ignored), so a renamed row
  drops out instead of pointing at the wrong dish. That's the same trick as `KIT_SHEETS`. 10 pairs, from the table
  above: 668→571 `mac` · 669→583 `buffalo` · 670→573 `pork belly` · 671→615 `gastrique` ·
  672→620 `soup` · 678→570 `dumpling`, not `soup` (both sides) · 673→567 `green` ·
  674→568 `pickle` · 675→759 `suadero` · 676→596 `chilorio`. 677 has no entry.
- **The rule**, for the viewed day, from Slice 1's read (named ticks only): the kit row's latest
  named tick is **1 or 2 days** before the viewed day, its pill was not MAKE, and the morning
  row has **no named tick after it** (none in the 14 days, or one on or before the kit's day).
  Then the pan is still in the cooler. "On or before" because the morning makes the recipe at
  the start of a day and the PM builds the next kit at the end of it.
- **What shows**: on the morning row, the Last done line becomes
  `[KIT READY] Kit built yesterday · Gilberto`, or `[KIT READY] Kit built Wed 11/18 · 2 days ago ·
  Pablo` (Who = the PM cook who ticked the kit). KIT READY is an outlined ink tag, bold condensed
  capitals: no fill, so it prints, and no hue. It stays all day, also once the morning row is
  checked (the strike-through says it's done).
- **No new request.** Slice 1's read already holds both rows, their Who and the pill.

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

### Slice 1b: only a named tick counts (both pages; the crew sees it on merge) — added 2026-11-21

- `tempest_prep.html`, `tempest_line.html`: inside the shared block only, `&assigned_to=neq.` in
  the read, and a row whose name is only spaces is skipped. The blocks stay byte-identical.
- `scripts/check_last_done.py`: the stub honours `assigned_to=neq.`; fixtures get names so
  dates are still tested; new cases (a bare tick doesn't count, a space-only name doesn't
  count); the exact query; two new fails-when-it-should.
- `docs/last-done.md`: the change, the decision, "Slice 1b as built", and Slice 1's phone check
  (passed 2026-11-21).
- **Before the merge, Stephen tells the crew: pick your name in Who on what you actually make or
  clean; just tick what isn't needed.**

### Slice 2: KIT READY on the Line AM row (Line only; the morning line sees it on merge)

**Ticket: `~/Developer/LAST-DONE-2-TICKET.md`** (2026-11-22).

- `tempest_line.html`: `KIT_MAKE`, `kitReady()`, the `.kit-ready` rule, `ldNote()` widened. All
  outside the LAST DONE blocks. Prep untouched. No new request.
- Guard scenarios (Line only): built last night → tag; made yesterday and built last night →
  tag; the morning row ticked today → tag stays; built 2 nights ago, not made → tag with its
  day; built 2 nights ago, made yesterday → no tag; built 3 nights ago → no tag; made yesterday
  with no name → tag; built with no name → no tag; checked on MAKE → no tag; Who picked but not
  checked → no tag; either row renamed → no tag; 677 ticked → nothing; PM view → no tag; a past
  date; typing; the tag whole at 390px, outlined, the line no taller; no extra request; Prep
  has none. 7 new fails-when-it-should (22 in all).
- `docs/last-done.md` (1b live + phone check, the 2-day decision, this section, "as built"),
  `docs/kits.md` "Adding a kit" (add the pair to `KIT_MAKE`), BUILD_PLAN B1 line.
- **Before the merge, Stephen tells the crew: PM, pick your name on the kits you actually
  build; AM, pick your name on what you actually make.**

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
- **Item 1: the usual cleaning crew fills itself in.** Since 2026-11-21 a name in Who means
  "actually done", so this idea clashes with Last done as it stands: auto-filled names would make
  every tick count. It needs a new design (e.g. a suggested name that only counts once the cook
  confirms it) before it's planned.
- **A database view for "last done"** (one row per task) if the lists ever outgrow two pages.
  Today it would be a schema change for no gain.
- **Promote `.last-done` into `kitchen.css`** at the next `?v=` bump (e.g. the #135 pass).
- **Kits menu update** (`docs/kits-line-link.md` "Later"): when 673 goes, its `KIT_MAKE`
  pair goes with it.

---

## Status

**Slice 1 LIVE** (#193, `d023c85`, merged 2026-11-21). **Slice 1b LIVE** (#194, `58d9235`, merged 2026-11-22), phone check passed. **Slice 2 BUILT 2026-11-22 on `prep-last-done-2`, not pushed.** It is the last slice of this plan.

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

## Slice 1: phone check

**Passed** (Stephen, 2026-11-21: "looks as you stated").

Settled with Stephen in the planner window on 2026-11-21:
- **Shared Who entries count.** "Rubi, Jose & Isaac", "Gilberto, Vidalio & Evelin" and the
  other entries that list several people are names, so a tick with one counts. ("Whole crew"
  in the build window's note was a misunderstanding of this.)
- **"Everyone"** gets no special handling for now. It's an entry like any other, so a tick with
  it counts.
- **Slice 2 uses the same rule**: a kit counts as built, and its morning row as made, only when
  ticked with a name.

## Slice 1b as built

**`tempest_line.html`, `tempest_prep.html`**: inside the LAST DONE block only, 2 lines each,
still byte-identical. `ldLoad()`'s query gains `&assigned_to=neq.` straight after
`completed=eq.true`, and the loop over a page's rows skips any row whose `assigned_to` is
empty after trimming, before it can set the task's day. Nothing else changed.

**`scripts/check_last_done.py`**: the stub honours `assigned_to=neq.` like the server (drops
`null` and `''`, keeps `'  '`). Every tick that must count has a name (fillers too, so `paged`
still needs 2 pages and `cut` 5), and the expected words carry ` · <name>`. New tasks on both
pages: 115 (bare tick 11/19, Pablo 11/15 → `Last done: Sun 11/15 · 5 days ago · Pablo`), 116
(spaces-only name → `Not done…`), 117 (ticked daily 11/07–11/19, never named → `Not done…`), 118
(`Gilberto, Vidalio & Evelin` → `Last done: yesterday · Gilberto, Vidalio & Evelin`). The exact
query in `words` includes `assigned_to=neq.`. **1,457 assertions**, 13 scenarios × 2 pages plus
`copies`, clean.

**Fails when it should**: Slice 1's 13 again, plus 14 (`assigned_to=neq.` dropped) and 15 (the
spaces-only skip removed): **all 15 fail.** On 14: the page's own skip also drops bare ticks
(`''` trims to empty), so 115 and 117 still read right without the server filter. The read is
caught by the exact-query check, and the rule holds twice over.

**Hand check** (local Chrome, live data, read-only, 2026-11-22):
- **Line:** "Cut Citrus" (Ismael yesterday) → `Last done: yesterday · Ismael`. "Make - Marinated
  egg", ticked yesterday with no name → `Last done: Wed 11/18 · 4 days ago · Rubi`. "Brussels
  sprouts", bare ticks only → `Not done in the last 2 weeks`. Of 72 rows: 14 yesterday, 20 not
  done, none without a name.
- **Prep:** "Clean grease trap" → `Last done: yesterday · Chepe`. "Clean out Compost trash bins",
  bare tick → `Not done…`. Of 58 rows: 19 yesterday, 20 not done.
- **Requests:** the last-done read carries `assigned_to=neq.` and comes back in one page. GETs
  only.

## Slice 1b: phone check

**Passed** (Stephen, 2026-11-22: "everything looks good").

## Slice 2 as built

**`tempest_line.html`** (about 30 lines; outside both LAST DONE blocks, which are untouched, so
`copies` still passes; `tempest_prep.html` unchanged):
- `KIT_MAKE`, next to `KIT_SHEETS`: the 10 pairs (kit row → morning row, word, `not` for
  678/570), with 677 left out.
- `kitReady(id)`: `''` unless `LD.day` is the viewed day and `LD.map` is set; the row must be a
  pair's morning row, both rows in `items`, the kit row's station `kits`, both names keep the
  word and neither has the `not` word. The kit's named tick must exist, not be on MAKE, and be 1
  or 2 days back (`ldDays`); the morning row's named tick, if any, must be on or before the
  kit's day. Text: `<span class="kit-ready">KIT READY</span> Kit built yesterday · Who` or
  `… Kit built Wed 11/18 · 2 days ago · Who`, weekday by parts, Who through `esc()`.
- `ldNote(id)` → `kitReady(id)||ldText(id)`. `bTask()` and `ldFill()` already call `ldNote()`,
  so the tag fills in place with no new request.
- `.kit-ready` in Line's `<style>` next to `.kit-sheet-link`: an inline-block, 1px solid
  `--ink` border, radius 3px, no background, `--ink`, `--font-cond` 700 uppercase,
  `.06em`, 0.75rem, `line-height:1`, `vertical-align:top`, `0 4px` padding. Measured: a tagged
  line is 15px, the same as an untagged one.

**`scripts/check_last_done.py`**: the Line fixtures gain the 10 real morning rows. Six new
Line-only scenarios: `kits` (built last night; made yesterday + built last night; ticked today,
where the tag stays and the row is struck; built 2 nights ago; 2 nights ago but made yesterday; too
old; made with no name; built with no name; MAKE; Who without a tick; 677; no tag on PM; no
extra request), `kitpast` (◀ to 11/19), `kitrename` (kit 673 → "Kit - Nachos"; 570 → "Make -
Dumpling soup" with 678 built), `kittyping`, `kitphone`, `kitphonemgr` (tag whole, line and row
heights equal to an untagged one, solid ink border, no fill, ink text, ≥12px). `words` checks
Line's 571 tag from the base fixture, and that Prep has no `.kit-ready` and no `KIT_MAKE`.
**1,757 assertions** (19 scenarios on Line, 13 on Prep, + `copies`), clean. The no-extra-request
check allows for Line already reading `staff` twice on load (as on `main`).

**Fails when it should**: 1b's 15 again, plus 16 (2-day limit removed), 17 ("on or before" →
"before"), 18 (MAKE check removed), 19 (word check removed), 20 (tag hidden once the morning row is
ticked today), 21 (a background fill), 22 (the tag making the line taller): **all 22 fail.**

**Hand check** (local Chrome, live data, read-only, Sun 2026-11-22):
- **Line AM today:** three tags. Bacon Gastrique `KIT READY Kit built yesterday · Eddy`;
  Make - Chicken and Dumpling soup `… yesterday · Evelin`; Cook Chilorio pork `… Fri 11/20 ·
  2 days ago · Chepe`.
- **Matches last night's Line PM:** only Gastrique (Eddy) and Chicken & Dumpling soup (Evelin)
  were ticked with a name. Dumpling had Evelin but wasn't ticked, so no tag. The other 7 were
  ticked with no name, so no tag.
- **Sat 11/21 view:** five tags (Mac and cheese, Pork belly, Dumpling by Pablo; Chilorio,
  Suadero by Chepe).
- **Elsewhere:** PM shows no tag. A tagged line is 15px, the same as an untagged one. The same
  requests as before; GETs only.
