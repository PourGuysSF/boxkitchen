# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Safety

Boxkitchen is a live production site used during service. Never run write/deploy/migration commands without asking first. Read-only commands (grep, read, git status) are always fine — say so up front so I don't have to interrupt to check.

## Architecture

**`index.html` is the hub.** Each other page (`tempest_*.html`, `recipe_dashboard.html`) is a self-contained tool.

**Backend is Supabase, accessed directly from the browser** via its PostgREST REST API — there is no server-side code in this repo. Every page embeds the **same** Supabase project URL and anon key inline and defines its own copy of a helper:

```js
api(method, table, query, data, cb)  // XMLHttpRequest to /rest/v1/<table>?<query>
```

**This `api()` helper and the anon key are duplicated in each file — there is no shared JS.** A change to any shared pattern must be applied per-file, and a new page is best created by copying an existing one as a template. Note the per-page `api()` copies differ: flash/orders/counts pass the HTTP status to their callback, the others don't.

## Data model conventions

Rows are scoped by a `location` column. The location is currently hardcoded to `Tempest` (`location=eq.Tempest`) throughout — the column exists so the same tables can serve multiple locations later.

## Supabase / SQL

When generating INSERT statements for the Recipes or any content table, always use dollar-quoting ($$...$$) for text fields — recipe text contains apostrophes that break single-quoted strings. Match the exact column format used in the app codebase before writing SQL.

## Auth

There are **two separate gates**:

1. **Site password** (`AUTH_PASSWORD`) — the entry gate, in `index.html` only. On success it writes a timestamp to `localStorage['boxkitchen_auth']` with a 30-day TTL. Inner tool pages are not re-gated; they rely on the user having entered through `index.html`.
2. **Manager PIN** (`MANAGER_PIN`, a.k.a. "manager mode" — see `MGR_KEY`, `mgrActions`) — present on the inner tool pages, gating destructive/admin actions (managing the item lists, edits, soft-retire, reorder). Regular staff can do the daily task (counts, check-offs) without it.

Both are shipped in public client code, so neither is real security — actual data protection depends on Supabase Row Level Security. **Secret hygiene:** never reproduce the password or PIN values in plans, summaries, comments, or output; refer to the latter only as "the manager PIN."

## Styling — one stylesheet, and rules that outlive it

**The migration is finished.** All ten pages share `assets/kitchen.css` — 9 core tokens, the
font import, the reset, and every shared component. There is no second palette anywhere in the
repo and no page carries an inline dark `<style>` block. A page's own `<style>` holds page-only
rules and a handful of justified overrides, nothing more.

Run this before opening any PR that touches a page or the stylesheet:

```
python3 scripts/check_styling.py
```

It is the #114 consistency sweep, made runnable. CI runs it too.

### The four rules that matter

**1. Never bulk-delete "unused" CSS from `kitchen.css`.** Many class names are composed at
runtime and appear in no markup: SortableJS injects `.sortable-ghost` / `-chosen` / `-drag`;
stations are built as `'st-'+station`, categories as `'cat-'+category`; also
`cleaning`/`daily`/`weekly`, `mode-kit`/`mode-make`, `filled`, `locked`, `has-qty`, `retired`,
`assigned`, `tempest`/`showdown`. A rule is only dead once you have proven no page composes
that name at runtime. Grep the JS for the *string fragment*, not the full class name.

**2. Class names are load-bearing.** The JS reaches for them by name — `classList.add('done')`,
`querySelector('.modal')`. Renaming a CSS class silently breaks behaviour that no visual review
will catch. Change rules, never names.

**3. A new page links `kitchen.css` and declares no `:root` of its own.** Scoped tokens are
fine (`--cat-*` on Notes, `--sec-*` / `--st-*` in the shared sheet); redeclaring a core token
is not, because then there are two sources of truth. `color-scheme:light` on `:root` must stay
— without it Chrome's Auto Dark Theme inverts the whole site on any Android phone in dark mode.

**4. State is expressed by fill, weight and border — never hue.** Filled / checked / active is
an ink fill. "Done" is never green; it is struck through, because opacity washes out on paper.

### What each colour is for

| token | for | never |
|---|---|---|
| `--ink` 17.9:1 | body text, filled/active state | — |
| `--grey` 5.18:1 | live secondary text | — |
| `--faint` 2.31:1 | inactive or locked text **only** | live content, placeholders that carry meaning |
| `--hair` 1.27:1 | list separators **only** | the edge of anything you tap |
| `--edge` 3.23:1 | the visible boundary of a control (WCAG 1.4.11 wants 3:1) | text |
| `--tomato` 3.32:1 | "the thing you meant to do" — Save, primary | destructive actions, small text |
| `--danger` 6.29:1 | destructive and error only | anything reversible (retire stays tomato) |
| `--yellow` 1.21:1 | highlighter fill behind text | text, or a signal on its own |

One rule, many class names: the segmented toggle serves `.filter-btn` / `.mode-btn` /
`.shift-btn` / `.guide-btn` / `.view-toggle button` across six pages; the fixed bottom bar
serves `.submit-bar` and `.save-bar`. **`.toast.err, .toast.error` must stay grouped** — Flash
sets `.err`, every other page sets `.error`, and an error rendering as a success is the worst
failure this stylesheet can produce.

### Printing is a backup, not a nicety

`kitchen.css` ends with an `@media print` block. Paper is what the kitchen falls back to
when the power, the wifi or the site is gone, so it has to be a document someone can run a
shift from with a pen.

The trap to remember when adding anything: **browsers do not print background colours by
default.** Anything drawn as white text on a filled block prints as white on white and
disappears. Every such state has to be re-expressed for print as a border or a glyph, which
always print. Nothing in that block relies on `print-color-adjust`.

Print has its own greyscale palette (`PRINT_PALETTE` in `scripts/check_styling.py`), allowed
only inside that block — those greys must never appear on a screen rule.

### Where the detail lives

- **`docs/page-restyle.md`** — what was built, slice by slice, and the justified page overrides.
- **`docs/review-checklist.md`** — how to review a change to this site: the failure shapes
  worth hunting, why contrast is arithmetic, and the class names that exist only at runtime.
  Read it before reviewing anything here.
- **GitHub issues** — what the restyle review left open. Don't assume the restyle is
  finished business.
