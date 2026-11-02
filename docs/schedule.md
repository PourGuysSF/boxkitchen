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
spreadsheet can be retired when Slice 7 puts the tile on the home page; until then the page is
live but unlinked, as Inventory's was.

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

### Slice 3 — Copy last week (manager)

- On an **empty** week only, a button fills it from the week before: shifts and OFF copied;
  **REQUEST boxes left empty** (they were one-time asks); Training not copied; day notes not
  copied (the standing ones show anyway).
- One bulk upsert. A week with even one filled box does not offer the button, so a week someone
  started can never be overwritten.

**Done when:** the harness proves an empty week fills correctly, a started week cannot be
copied over, and a double tap cannot copy twice.

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

### Slice 7 — Ship it into the site *(shared files, last)*

- **Bring the branch up to date with `main` first**: the Kits and Menu Builder windows add home
  tiles too.
- `index.html`: the Schedule tile, unlocked, because staff read it.
- `CLAUDE.md`: the page count wherever it is stated. `BUILD_PLAN.md`: a line for this build.
- `assets/kitchen.css`: add *schedule* to the `used by:` banner of each shared section the page
  uses. No rule changes.
- `python3 scripts/check_styling.py` runs clean.

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
| Copy last week overwrites real work | A manager's week is lost | Offered only on an empty week |
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
