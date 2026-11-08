# Schedule — the weekly staff schedule

Status: **plan v1, approved by Stephen 2026-11-02** ("everything looks good"), including the
suggested answers to the four questions at the end. **Slice 0 is closed** (2026-11-02): the four tables are live and seeded.
Every decision below was made by Stephen, in the brief that started this window or in the
four questions that followed it. Planned in one window; built in a second, from
`~/Developer/SCHEDULE-TICKET.md`. Worktree `~/Developer/boxkitchen-schedule`, branch
`schedule` (cut from `main` at `7fbd499`).

Target file: a new page, `tempest_schedule.html`, copied from `tempest_meat.html` as its
template. At the very end, and only then: the tile in `index.html`, `CLAUDE.md`, and
`BUILD_PLAN.md`. This plan needs **no change to `assets/kitchen.css`** (see Constraints).

---

## What it is for

Tempest's schedule lives in a Google spreadsheet, one tab per week. Staff check the kitchen
site for prep, orders and counts, and a separate spreadsheet for when they work. This page
puts the schedule on the site, so **everything staff need lives in one place**, and it
replaces the spreadsheet from the first week it is used.

---

## Decisions — 2026-11-02

| question | decided |
|---|---|
| Does the site replace the spreadsheet | **Yes.** From the first week on the site, the site is the schedule. Staff see a change the moment a manager saves it; there is no draft or publish step. |
| Old weeks | **Start fresh.** Nothing is copied over; the spreadsheet stays as the archive. |
| Phone numbers | **None.** The site and its database key are public, so anything stored is effectively public. **Stephen's own number is also left off** (asked 2026-11-02). |
| Who changes it | **Managers only, with the manager PIN.** Staff can only look. |
| Time off | **Asked for the way it is today**, by telling or texting a manager, who types REQUEST into the box. Staff write nothing on the site. |
| Day names | **English and Spanish, as the sheet has them**: SUNDAY / DOMINGO … SATURDAY / SABADO, no accents added. |
| Colour tags | **COVID is gone.** REQUEST stays (it is one of the three things a box can say). TRAINING stays, as the word under a shift. 49ers home, Giants home and Events stay as **day notes**, in words. **NO SHOW is not carried over**: next to a named person, on a page anyone can read, it would be a public HR record. Meaning shows as words, never colour (CLAUDE.md rule 4). |
| Peach OFF boxes | Not answered; **treated as decoration** and not carried over. See Questions. |
| Note rows | **Trash, compost and janitors are the same every week**: set once, shown every week. **Games, parties and conventions change weekly**: typed per day. |
| Extras | **Approved:** quick buttons for common entries; **Copy last week**; a print version for the wall; tap a name to see one person's week. **Later, as its own step:** who's on today and trash night on the home page's Today board. |

---

## Ground truth — read-only, 2026-11-02

**The spreadsheet** (`2026_Tempest_Schedule`, the 11.8–11.14 tab, from Stephen's screenshot):

- One tab per week, **Sunday to Saturday**, each day with its English name, Spanish name and
  date (`11/8`). Tab names run `11.8–11.14`, `11.1–11.7`, … back to August.
- **Two crews, listed separately.** Day crew, 4: Jose V., Rubidia, Isaac L., Ismael. Night
  crew, 7: Eddy V., Gilberto C., Carlos D., Chepe (Jose), Pablo, Evelin, Vidalio. Eleven people,
  77 boxes a week. A phone column sits beside every name; it is not carried over.
- **A box says one of three things**: a shift, **OFF**, or **REQUEST**.
- **Shifts are written by hand and not quite consistently.** Day crew on set hours: `9am-2pm`,
  `9am-3pm`, `9:30am-2pm`, `9:30am-3pm`, `10am-3pm`, `10am-4pm`, `10am-5pm`. Night crew mostly
  start-to-close: `4pm-CL`, `4:30pm-CL`, `5pm-CL`, `6pm-CL`, written `4 pm-CL` and `6 pm-CL` too.
  Also `4pm-10` (until 10pm), and a night-crew person on `10am-4pm` (Chepe, Sunday and
  Saturday) — the crew is the section a person is listed in, not a rule about their hours.
- **Three note rows** under the day crew. As read from this tab:
  - *Trash out by 8pm*: TRASH-OUT Sunday, Tuesday, Thursday; COMPOST OUT Monday.
  - *Cleaning crew*: JANITORS Sunday, Wednesday, Friday.
  - *49ers games*: "Bye week 49er" Sunday; "Football" Monday and Thursday.
- **A colour key across the top**: REQUEST, 49ers HOME, GIANTS HOME, COVID, EVENTS, NO SHOW,
  TRAINING. REQUEST boxes are filled in its colour. Some OFF boxes are peach, which is not in
  the key.

**The `staff` table** (read-only GET through the site's own key): 44 rows, 35 active, columns
`id, created_at, name, shift, location, active, sort_order`. **It is not a roster.** It is
the "Who" picker for the prep pages and the "Counted by" list on the counts, so it mixes
people with pairings ("Isaac & Jose", "Rubi, Jose & Isaac", "Everyone"), lists some people
twice (Chepe, Evelin and Eddy appear under both AM and PM), and spells some names differently
from the sheet ("Rubi" for Rubidia). **The schedule keeps its own list of people, and `staff`
is not touched.** Linking the two is a later question, not this build's.

**The table pattern** the new tables copy, recorded by the Inventory Guide's Slice 0 from
`pg_policies` on 2026-10-06: RLS on; separate SELECT / INSERT / UPDATE policies with
`using (true)` / `with check (true)` for roles `anon, authenticated`; **no DELETE policy**;
`bigint` identity ids; `location text not null default 'Tempest'`; foreign keys to parents.

**Pieces already on the site to reuse:** the page skeleton (gate, header, Manager switch, PIN
box) from `tempest_meat.html`; the `api()` with a timeout from `tempest_inventory.html`; the
◀ ▶ arrows and "Back to today" (`.date-arrow`, `.date-today`, already shared in `kitchen.css`)
from Flash; `scripts/check_inventory.py` as the model for this page's test harness.

---

## The spine

> **A schedule is a promise to eleven people about their week. Every slice makes a wrong box
> harder to save, easier to see, and impossible to miss.**

Three rules, and everything below obeys them:

1. **Blank is not OFF.** An empty box means *not scheduled yet*. OFF is something a manager
   chose. A week with empty boxes says so, in manager mode, before anyone mistakes it for
   finished.
2. **What is on the screen is what is saved.** A box changes only when the database says it
   took. A save that fails says so and leaves the old value showing.
3. **Nothing private goes in.** No phone numbers, no no-shows, no wages. The database can be
   read by anyone who opens the page's code, so the page only holds what could be pinned to
   the kitchen wall.

---

## The design

### What staff see — a day at a time

The week as a grid is eight columns wide, and a phone is about 390 pixels: each day would get
the width of "10am". So on a phone the page opens on **today**, as a list, and the week is one
tap away.

```
┌──────────────────────────────────────┐
│ ← Home    Tempest SCHEDULE  Manager ○ │
│ ◀   Nov 8 – 14, 2026   ▶  This week  │
│ [ Day ]  [ Week ]                    │
│  SU  MO  TU  WE  TH  FR  SA           │
│   8   9 [10] 11  12  13  14           │
├──────────────────────────────────────┤
│ TUESDAY · MARTES · 11/10              │
│ Trash out by 8pm                      │
│                                       │
│ DAY CREW                              │
│ Jose V.             10am-4pm          │
│ Rubidia             9am-3pm           │
│ Isaac L.            10am-3pm          │
│ Ismael              OFF               │
│ NIGHT CREW                            │
│ Eddy V.             REQUEST           │
│ Gilberto C.         4:30pm-CL         │
│ …                                     │
│ Updated Sat 3:12 PM                   │
└──────────────────────────────────────┘
  (shifts in this sketch are from the 11/8 tab, as an illustration)
```

- **People stay in the sheet's order every day**, OFF included, so everyone finds their own
  name in the same place.
- **A shift is ink. OFF is grey. REQUEST is the word on the yellow highlighter.** Nothing is
  told apart by colour alone; every state is also a word.
- **TRAINING** is a small word under the shift it belongs to.
- The day's notes sit at the top: the standing ones (trash, compost, janitors) and that day's
  games or events.
- **"Updated …"** is the time of the most recent save for that week, so a cook can trust what
  they are looking at.
- **The page refreshes itself when it comes back to the front**, so a phone left on the page
  since Saturday does not show Saturday's schedule.

### The week grid

**Week** shows the sheet as people know it: names down the side, Sunday to Saturday across,
English and Spanish day names and the date over each column, the two crews and the note rows.
On a phone it scrolls sideways with the names pinned; on the kitchen tablet or a laptop it
fits. Today's column header is filled (the site's "active" state). This is also what prints
(Slice 4).

### How a manager changes a box

With the manager PIN on, tapping any box (in Day or Week) opens a small picker:

```
┌───────────────────────────────┐
│ Pablo · Tuesday 11/10          │
│ [ OFF ]  [ REQUEST ]           │
│ [ 4pm-CL ] [ 5pm-CL ] [ 6pm-CL]│
│ Other: [               ]       │
│ ☐ Training                     │
│ [ Clear ]            [ Save ]  │
└───────────────────────────────┘
```

- **Quick buttons** are the shifts that person's crew has used most over the last four weeks
  on the site. Until there are four weeks, the shifts from the 11/8 tab (Ground truth) fill in.
- **Other** takes anything else. It is tidied on save: `4 pm-CL` becomes `4pm-CL`, `cl` becomes
  `CL`, `PM` becomes `pm`. It is **kept as words, not turned into clock times**: nothing on this
  page adds up hours, and turning text into times would add a way to get it wrong.
- **Clear** empties the box back to *not scheduled yet*, which is not the same as OFF.
- A day's games and events are changed the same way, by tapping the note row, with quick
  words (49ers home, Giants home, Football, Event) and a text box.

### Tables — SQL Stephen runs; nothing is created from a session

Four new tables, all `location`-scoped like everything else. **`staff` is not touched.**

| table | one row per | key columns |
|---|---|---|
| `schedule_people` | person, per location | `name, crew` (`day` / `night`), `sort_order, active`. **No phone column, on purpose.** Seeded with the eleven, in the sheet's order. |
| `schedule_shifts` | person per day | `person_id, work_date, kind` (`shift` / `off` / `request`, or empty once cleared), `shift_text, training, updated_at`; unique `(person_id, work_date)` |
| `schedule_day_notes` | day, per location | `note_date, note, updated_at`; unique `(location, note_date)`. Games, parties, conventions. |
| `schedule_standing` | note that repeats every week | `label, weekdays` (which days, Sunday = 0), `sort_order, active`. Seeded with trash, compost and janitors as read from the 11/8 tab. |

The database itself enforces the shape of a box, so a bad save cannot reach it: a shift
needs its text, OFF and REQUEST carry none, and Training only goes with a shift.

Saving is an **upsert** on `(person_id, work_date)`, the way the Inventory Guide saves a count
line: a retry after a lost response cannot make a second row. Clearing a box writes an empty
box rather than deleting the row, because no table on the site has a delete policy.

A person who leaves is **retired**, not deleted. A past week still shows everyone who had a
box in it, retired or not.

---

## Slices

Eight slices plus one for later, each small, ordered so nothing that writes ships before the
thing that makes it safe. **The first week can be made on the site after Slice 2.** The
spreadsheet can be retired when Slice 3b puts the tile on the home page (moved up from Slice 7,
2026-11-08); until then the page is live but unlinked, as Inventory's was.

### Slice 0 — The tables and the eleven *(no app code)* · **blocks everything**

- The SQL: four tables, the unique keys, the box-shape rules, RLS copied from the pattern in
  Ground truth, the eleven people seeded in two crews in the sheet's order, and the three
  standing notes — in one file, `docs/schedule-slice0.sql`, dollar-quoted text, in one
  transaction that undoes itself unless the counts come out right (11 people: 4 day and 7 night;
  3 standing notes; nothing else).
- Proved first against a throwaway local Postgres shaped like Supabase, as the Inventory Guide's
  was. Stephen runs it in the SQL Editor (source: **Database**).

**Done when:** the tables answer a read-only GET with the site's key (people 11, standing 3,
shifts 0, day notes 0), RLS matches the pattern, and no delete is allowed.

> **CLOSED 2026-11-02.** Stephen ran `docs/schedule-slice0.sql` in the SQL Editor (Database,
> production). Its closing select returned people 11, standing 3, shifts 0, day notes 0.
> Verified independently, read-only, through PostgREST with the site's anon key: all four
> tables answer; people 4 day + 7 night in the sheet's order, all active; standing notes
> Trash out by 8pm `[0,2,4]`, Compost out `[1]`, Janitors `[0,3,5]`; `weekdays` arrives as a
> JSON array of numbers. `pg_policies`: 12 policies (SELECT / INSERT / UPDATE × 4 tables,
> `{anon,authenticated}`), **no DELETE**. No row was written from a session.
>
> **Proved first** on a throwaway Postgres (pip `pgserver` in a scratch venv, no sudo) with
> `anon` / `authenticated` roles: the counts; as `anon`, a box insert, the upsert on
> `(person_id, work_date)` updating the same row (1 row after), `updated_at` moving on update;
> each box rule refusing a bad box (shift without text, blank text, OFF with text, empty with
> text, Training off a shift, unknown kind), bad weekdays and crew refused, a second note for a
> day refused; delete refused on all four; and a deliberately failed check leaving no tables.
>
> **Found and fixed in testing:** the first draft of the box-shape check let an *empty* box
> (kind NULL) carry shift text, because a NULL in a check counts as a pass. It is now written
> as `(kind is not distinct from 'shift') = (shift_text is not null)`, plus a not-blank rule.
>
> As built, beyond the plan: `updated_at` is set by the trigger function
> `schedule_touch_updated_at()` (the undo line in the file's header drops it too); boxes carry
> no `location` of their own, they inherit it from their person.

### Slice 1 — The week, read-only

The page exists, and writes nothing.

- `tempest_schedule.html`, copied from `tempest_meat.html`: gate, header, Manager switch,
  `kitchen.css` at the current `?v=`.
- ◀ ▶ through weeks, **This week** to come back; Day and Week views as designed; the standing
  notes on their days; "Updated …"; refresh on coming back to the front.
- With the tables empty, it shows the eleven names, the days and the standing notes, and every
  box empty.
- `scripts/check_schedule.py` started, modeled on `check_inventory.py`: the real page, a
  stubbed `XMLHttpRequest`, headless Chrome.

**Done when:** Stephen has looked at it on his phone and the kitchen tablet; the harness proves
the page makes **no request but GET**, renders a stubbed week correctly in both views, and puts
the right week under the right dates across a month end (Nov 29 – Dec 5).

> **Slice 1 as built (2026-11-02, committed 2026-11-05).** `tempest_schedule.html`, copied from
> `tempest_meat.html`: same gate, header (`Tempest <span>Schedule</span>`), Manager switch and PIN
> flow, `kitchen.css?v=2026-09-19`. Inventory's timeout `api()`; Flash's `.date-bar` /
> `.date-left` / `.date-arrow` row with `.date-today` as "This week"; the shared `.view-toggle`
> for Day / Week (remembered in `localStorage['boxkitchen_schedule_view']`, try/catch, Day
> fallback). Page-only rules in its own `<style>`, all prefixed `sched-`; no `:root`, no
> `kitchen.css` change. The PIN box is restated as `.modal input[type="tel"].pin-input`, as on
> Inventory, so it renders at 1.4rem rather than 15.2px (the styling guard caught it).
>
> Reads, GET only: people (all Tempest, retired included), then shifts by `person_id=in.(…)`
> and the week's dates, day notes and active standing notes together. Nothing is drawn until
> all four land; any failure shows "Couldn't load the schedule" with **Try again**; a newer load
> supersedes one in flight. A box with `kind` null (cleared) reads as empty, but its
> `updated_at` still counts toward "Updated …". The Week grid's note rows are each standing note
> (its label on its days) and a "Games & events" row for the day notes. Coming back to the
> page reloads the week quietly, keeping the view and the day.
>
> **`scripts/check_schedule.py`**: 69 assertions over 5 scenarios (`ok`, `monthend`, `yearend`,
> `fail`, `empty`), the real page in headless Chrome at 390px, `XMLHttpRequest` stubbed and the
> clock fixed **at 5:30 PM with `TZ=America/Los_Angeles`**, when UTC is already tomorrow.
> Proved able to fail: with `toISOString()` planted in the date key, it fails on today's day and
> column. `check_styling.py` clean (12 pages).
>
> Stephen looked on his laptop through `python3 -m http.server` on 2026-11-02 ("everything
> looks good"). Note for the next look: the local server is its own origin, so the site
> password is asked again at `index.html` before the page opens. The phone and kitchen-tablet
> look waits for a merge he approves.
>
> **Shipped 2026-11-05** as PR #172 (squash `dd33c0f`), with Slice 0's SQL; unlinked, no tile.
> Stephen looked at the live page on his devices the same day: "it looks fine right now."

### Slice 2 — Changing a box (manager)

- The picker, as designed: quick buttons, Other, Training, Clear, Save. Day notes the same way.
- Saves by upsert through the timeout `api()`. The box changes only on a confirmed answer with a
  row in it; a failure leaves the picker open with the reason.
- **The text box is a new class at 16px**, written qualified per CLAUDE.md
  (`.modal input[type="text"].x,.x`), so an iPhone does not zoom.
- In manager mode the week header counts empty boxes: *"9 boxes not filled yet."*

**Done when:** every write happens only in manager mode; the harness asserts each payload; a
retry leaves exactly one row; blank and OFF are stored differently; the text box measures 16px.
Then a hand test on Stephen's iPhone, on the first real week.

> **Slice 2 as built (2026-11-05).** Manager mode only; staff-mode HTML has no box or note
> buttons (built at render time, not hidden by CSS) and makes exactly Slice 1's four reads.
> - **Boxes:** in Day each `.sched-box` becomes `button.sched-boxbtn`; in Week each person cell holds
>   `button.sched-cellbtn` (≥44px). `aria-label` "Change Pablo, Tuesday 11/17". Retired people's
>   boxes are tappable in the weeks they show.
> - **Box picker** (`#boxModal`, static markup, shared modal classes): title "Pablo · Tuesday ·
>   Martes 11/17", "Now: …"; OFF, REQUEST, then up to 8 quick shifts. The quick shifts are the crew's
>   most-used `shift_text` over this week and the three before (one GET, `kind=eq.shift`, manager
>   mode only, cached per week, dropped after a save), topped up from the 11/8 defaults. Selection is
>   an ink fill + `aria-pressed`. Other (`.sched-other`, maxlength 20, Enter = Save) and Training
>   (only with a shift; OFF/REQUEST turn it off). Save, Clear (disabled on an empty box), Cancel,
>   and the backdrop closes it (not while saving).
> - **Tidy:** dashes → `-`, spaces collapsed and removed around `-` and before am/pm, am/pm lower
>   case, `cl` → `CL`; text that tidies to `off` / `request` saves as that kind.
> - **Save:** `POST schedule_shifts?on_conflict=person_id,work_date`, Prefer
>   `resolution=merge-duplicates,return=representation`, body exactly `{person_id, work_date,
>   kind, shift_text, training}` (never `updated_at`). Clear sends `kind:null`. Success = 2xx and
>   one row for that person and day; then `loadSeq++` (drops a quiet reload in flight), the row
>   goes into `shifts`, "Updated" moves, the picker closes, "✓ Saved". Otherwise the picker stays
>   open with "No answer. Check the wifi and try again." / "Not saved (error N). Try again." and
>   nothing on the page changes. One save at a time; unchanged = no request.
> - **Games & events** (`#noteModal`, `.sched-note-input`, maxlength 60): the Day line ("+ Add game
>   or event" when empty) and the Week row's cells are buttons. Quick words add to the text.
>   `POST schedule_day_notes?on_conflict=location,note_date`, body `{location:'Tempest',
>   note_date, note}`, spaces tidied; Clear sends `note:''`. Same success/failure rules.
> - **Count:** `#mgrCount` "N boxes not filled yet" / "Every box filled", over active people × 7.
>
> **`scripts/check_schedule.py`**: 151 assertions over 6 scenarios. The new `mgr` scenario (82
> assertions) enters manager mode via `sessionStorage['boxkitchen_mgr']` + the switch (never the
> PIN), with a stub that upserts on the real keys and can hold, drop or refuse an answer. It
> covers every payload, unchanged = no request, a double tap = one request, both failures with
> the box unchanged, the retry's identical upsert leaving one row, the quiet-reload race, 16px
> on both text boxes, the count and 44px Week buttons. **Proved able to fail:** without
> `loadSeq++` the race check fails (the stale reload painted `6pm-CL` over the save); without
> the unchanged check, the two no-request checks fail. `check_styling.py` clean (14 pages, 98
> inputs measured, both new ones ≥16px).
>
> Stephen looked on his laptop on 2026-11-05 ("everything works"), without saving: a read-only
> count afterwards showed 0 boxes and 0 day notes on the live tables. The iPhone hand test on
> Nov 15 – 21 waits for the merge.
>
> **Shipped 2026-11-07** as PR #179 (squash `5dd1fb9`). **iPhone hand test, same day, on the live
> page, week of Nov 15 – 21:** Stephen: "everything saved and worked". Verified read-only
> afterwards: 6 box rows, **no duplicates** — Jose V. and Rubidia OFF (11/15), Eddy V. REQUEST and
> Ismael `9:30am-2pm` + Training (11/16), Gilberto C. `4pm-CL` from typed `4 pm-cl`, and Jose V.
> 11/17 cleared (`kind` null, the row kept); one day note, 11/15. Every row has a server
> `updated_at`. Noticed: the note reads `49ers home1:25` — a quick word adds no trailing space, so
> a time typed straight after it runs on (follow-up below).

### Slice 3 — Copy last week (manager)

- On an **empty** week only, a button fills it from the week before: shifts and OFF copied;
  **REQUEST boxes left empty** (they were one-time asks); Training not copied; day notes not
  copied (the standing ones show anyway).
- One bulk upsert. A week with even one filled box does not offer the button, so a week someone
  started can never be overwritten.

**Done when:** the harness proves an empty week fills correctly, a started week cannot be
copied over, and a double tap cannot copy twice.

**Decisions, 2026-11-08 (Stephen):**
- The home tile goes live right after this slice, as **Slice 3b** (its own ticket and PR).
- The quick-word space is fixed inside this slice, as its own step and commit.
- Planner's calls, confirmed: **(1) look before it writes** — a confirm box names both weeks and
  the counts, nothing is written until Copy: yes. **(2) this week or later only** — a past
  empty week never offers the button: yes, *"for now that is fine"* (may be revisited).
  **(3) people who have left are not copied**: yes ("that's a good call").
- Copy can't help with Nov 15 – 21 (its week before lives in the sheet, and it's started);
  Copy starts saving time with Nov 22 – 28.

> **Slice 3 as built** (commits `d58aeb4`, `39745d6`):
>
> - **Quick-word space:** `addWord()` adds one space after the word and leaves the caret at the
>   end; `tidyNote()` trims on Save. "49ers home" + typed `1:25` saves `49ers home 1:25`.
> - **The button** (`#copyWrap` / `#copyBtn`, class `sched-copybtn`, ink border, ≥44px) sits under
>   `#mgrCount`, built at render time, so staff HTML holds none. Shown only when: manager mode;
>   `loadedKey === keyOf(weekStart)` (set when a load succeeds, cleared when a non-quiet load
>   starts or any load fails — the count and button hide at those moments too); there are people;
>   no row in the week has a `kind` (anyone's, retired included); the week is this week or later.
>   Label `Copy last week (<last week, no year>)`.
> - **The confirm box** (`#copyModal`, shared modal classes, info line `sched-copyinfo`, grey
>   `sched-copysub`; `.modal-err` only for failures): Checking → ready ("Fill A with B: N shifts
>   and M OFF.") / nothing to copy / started (quiet reload behind) / read failed (Copy stays on).
>   Cancel and the backdrop close it except while copying; a late read after closing does nothing.
> - **The read:** one GET of `schedule_shifts` for both weeks, every person, `ms=API_TIMEOUT`,
>   filtered in JS. Days mapped by index (`addDays(weekStart,i-7)` → `addDays(weekStart,i)`).
>   Shift → `{person_id, work_date, kind:'shift', shift_text, training:false}`; OFF → `shift_text
>   null`; REQUEST, `kind` null and retired people → nothing. Five keys, never `updated_at`.
> - **Copy:** reads again; started → no write, the started message, quiet reload; else one POST
>   `on_conflict=person_id,work_date` with `resolution=merge-duplicates,return=representation`
>   and the array. Success (2xx + array) → `loadSeq++`, returned rows into `shifts`, `bump()`,
>   drop the quick cache, close, render, toast "✓ Copied N boxes" (N = rows returned). Failure →
>   box stays open, "No answer…" / "Not copied (error N)…", page unchanged.
> - **Slice 4 must hide** `#copyWrap` and `#copyModal` in print (manager-only elements).
> - Fixed two stale comments (`api()`, MANAGER MODE).
>
> **`scripts/check_schedule.py`:** 215 assertions over 8 scenarios. The stub upserts array bodies
> row by row and has a new `'lost'` write fate (written, then `onerror`); `releaseLast()` lets the
> POST land before a held stale reload. New `copy` scenario (Tue Nov 17 clock; fixtures: a retired
> shift 11/16, a cleared Jose V. 11/24, a retired-only box 12/8) covers where the button shows,
> the preview counts, Cancel/backdrop, nothing-to-copy, both failures + identical retry, the lost
> answer (still one POST), started-at-write-time, double tap (one POST, buttons and backdrop
> locked), the exact payload as a set, the after-state (count 31, one row per box, escaped,
> no notes, retired absent), the quiet-reload race, month end (rows on 11/29 and 12/1) and
> Manager off. New `dst` scenario (Sun Nov 1 clock): Oct 25 – 31 → 11/2, 11/3, 11/4 exactly.
> `ok` asserts staff mode has no button on an empty future week. **Proved able to fail:**
> skipping the second read fails the started and lost checks; letting REQUEST through fails the
> preview, payload and toast checks. `check_styling.py` clean.
>
> **Shipped 2026-11-08** as PR #183 (squash `c437e03`). **Hand test part A, same day, Stephen's
> iPhone, live page, no Copy tapped:** Nov 8 – 14 offered "Copy last week (Nov 1 – 7)" →
> "Nothing to copy", Copy greyed; no button on Nov 1 – 7 (past) or Nov 15 – 21 (started); Nov
> 22 – 28 offered "Copy last week (Nov 15 – 21)" with the preview "2 shifts and 2 OFF" (matches
> the live rows: Ismael, Gilberto C. shifts; Jose V., Rubidia OFF; Eddy V.'s REQUEST and the
> cleared Jose V. box left out); button in Week view too; gone with Manager off. Quick-word fix:
> the real 11/15 note (49ers home game) retyped with the button and no space bar → `49ers home
> 1:25`, still right after closing Safari. **Verified read-only:** the 11/15 note is `49ers home
> 1:25` in one row; no `schedule_shifts` rows dated Nov 1 – 14 or Nov 22 – 28; Nov 15 – 21
> still 6 rows. **Part B** (the first real copy, Nov 22 – 28) is recorded when it happens.

### Slice 3b — The tile *(shared files; its own ticket and PR)*

Moved up from Slice 7 on 2026-11-08 so staff can find the page and the sheet can retire.
`index.html`: the Schedule tile, unlocked. Bring the branch up to date with `main` first. See
`~/Developer/SCHEDULE-SLICE-3B-TICKET.md`.

### Slice 4 — The paper copy

Printing the page gives the week for the wall: **one landscape page**, both crews, English and
Spanish day names, dates, the note rows, "Updated …". REQUEST prints as the word, with no
reliance on the highlighter (backgrounds do not print). Empty boxes are drawn as boxes, so a
manager can pencil one in. Nothing manager-only prints.

**Done when:** a print preview fits one landscape page with background graphics off, and
every state is readable in black and white.

### Slice 5 — The people and the standing notes (manager)

- Add a person, fix a name, move someone between crews, reorder within a crew (drag, as on
  Orders), retire.
- Change the standing notes: their words and their days.

Until this slice, a new hire is added by a line of SQL Stephen runs.

**Done when:** every action writes only in manager mode; the harness asserts each payload;
a retired person disappears from new weeks and stays in past ones.

### Slice 6 — One person's week

Tap a name, in either view, to see only that person's seven days, with the day's notes beside
each. Back returns to where you were.

**Done when:** it works from both views and from a month-end week, and writes nothing.

### Slice 7 — Finish in the shared files *(last)*

The tile moved to Slice 3b. What's left (unless 3b's ticket already did it):
- **Bring the branch up to date with `main` first.**
- `BUILD_PLAN.md`: a line for this build.
- The final shared-file check: `CLAUDE.md` page count, `assets/kitchen.css` `used by:` banners
  (no rule changes), and `python3 scripts/check_styling.py` clean.

### Later — the home page's Today board *(its own step, after this ships)*

Who's on today, and trash night, as tickets on the home page. It touches `index.html`'s
Today board, which other windows also change, so it waits until the page has been in use.

---

## Out of scope

- **Staff writing anything**, including asking for time off on the site.
- **Phone numbers, no-shows, wages, and hours or labour totals.**
- **Messages when the schedule changes.** No texts, emails or alerts; staff look at the page.
- **The `staff` table** and the prep pages' "Who" picker. Untouched.
- **Old weeks.** The spreadsheet is the archive.
- **A history of who changed which box.** Each box keeps when it was last saved, not by whom.
  Easy to add later if a dispute ever needs it.
- **Other locations.** Everything is `location`-scoped, so Phase C inherits it.

---

## Constraints

From `CLAUDE.md`, `docs/review-checklist.md`, and Stephen's rules for this window:

- **The database is live. Never write test rows.** Read-only GETs are fine. Every write path is
  proved against a stubbed `api()` in `scripts/check_schedule.py`.
- **Any new table is SQL Stephen runs.** No DDL from a session.
- **Ask before any push, PR, merge or deploy.** Stay on branch `schedule`; never touch the
  other windows' folders (`boxkitchen-costing`, `-inventory`, `-kits`, `-menu`).
- **Shared files last**: `index.html`, `assets/kitchen.css`, `scripts/check_styling.py`,
  `CLAUDE.md`, `BUILD_PLAN.md`. The page's own rules live in its own `<style>`.
- **16px** for every new input, written qualified wherever it could sit in a modal.
- **No new `:root`**, no redeclared core token. **State is fill, weight and border, never hue.**
  `--faint` only for inactive text; OFF is live information, so it is `--grey`.
- **Print**: every manager-only element and every modal hidden under `@media print`.
- **The manager PIN and site password are never written into this doc, a PR, or output.**

---

## Risks

| risk | why it matters | mitigation |
|---|---|---|
| Anyone with the page's code could write to the tables | The database key is public; the PIN only hides the buttons | The same as every table on the site today. No delete policy; the database enforces the box's shape; every box keeps its last-saved time |
| A phone shows an old week | A cook comes in on a shift that was changed | Refresh on coming back to the front; "Updated …" on every week |
| Blank read as OFF | Someone thinks they are off when the week isn't finished | Blank is stored as *empty*, not OFF; manager mode counts empty boxes |
| Copy last week overwrites real work | A manager's week is lost | Offered only on an empty week, this week or later; Copy reads the week again right before writing and refuses if any box is filled. **Accepted (2026-11-08):** in the moment between that read and the write landing (under a second on wifi), a box another manager saves in the same week could be overwritten. `ignore-duplicates` would close it but skip a cleared box, so the screen would disagree with the preview — not re-opened |
| Eight columns on a phone | Unreadable grid | Day view first; the grid scrolls with names pinned |
| Names on a public page | Staff names are readable by anyone | Names only, as the sheet writes them; nothing else about a person is stored |
| Other windows change `index.html` | Conflicting tiles | Tile last; update from `main` first |

---

## How to verify without touching live data

As the Inventory Guide does it:

- **`scripts/check_schedule.py`** loads the real page, stubs `XMLHttpRequest` before the page's
  script runs, drives it in headless Chrome, and asserts on payloads and the page.
- **Real rows, read-only**, for rendering: GETs against the live tables are fine.
- **Phone width** inside a 390px wrapper.
- **Assert, don't eyeball**: only GETs in read-only slices; computed font size on the text box;
  the right dates across a month end.
- **Hand test on Stephen's iPhone** before each write slice merges, with every step spelled out.

---

## Questions — answered 2026-11-02

Stephen approved the plan with these as written ("everything looks good"):

1. **The first week on the site** is the first one a manager builds after Slice 2 ships,
   probably **Nov 15 – 21**. 11/8 – 11/14 stays in the spreadsheet.
2. **The standing notes** are as read from the 11/8 tab: trash out by 8pm Sunday, Tuesday and
   Thursday; compost out Monday; janitors Sunday, Wednesday and Friday.
3. **Peach OFF boxes** are decoration, and are not carried over.
4. **Names as the sheet writes them**, in normal capitals: Jose V., Rubidia, Isaac L., Ismael,
   Eddy V., Gilberto C., Carlos D., Chepe (Jose), Pablo, Evelin, Vidalio.
