# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Safety

Boxkitchen is a live production site used during service. Never run write/deploy/migration commands without asking first. Read-only commands (grep, read, git status) are always fine — say so up front so I don't have to interrupt to check.

## Architecture

**`index.html` is the hub.** It gates entry (see Auth below), links out to each tool page, renders day-of-week reminders (the `REMINDERS` map keyed by `getDay()`), and builds a 72-hour "Activity" feed by querying the `orders`, `meat_counts`, and `portion_counts` tables and merging them by timestamp. Each other page (`tempest_*.html`, `recipe_dashboard.html`) is a self-contained tool.

**Backend is Supabase, accessed directly from the browser** via its PostgREST REST API — there is no server-side code in this repo. Every page embeds the **same** Supabase project URL and anon key inline and defines its own copy of a helper:

```js
api(method, table, query, data, cb)  // XMLHttpRequest to /rest/v1/<table>?<query>
```

REST verbs map to PostgREST semantics (`GET`/`POST`/`PATCH`/`DELETE`, filters like `location=eq.Tempest`, `count_date=gte.<date>`, `order=...desc`). **This `api()` helper and the anon key are duplicated in each file — there is no shared JS.** A change to any shared pattern must be applied per-file, and a new page is best created by copying an existing one as a template. Note the per-page `api()` copies differ: flash/orders/counts pass the HTTP status to their callback, the others don't.

## Data model conventions

Rows are scoped by a `location` column. The location is currently hardcoded to `Tempest` (`location=eq.Tempest`) throughout — the column exists so the same tables can serve multiple locations later.

## Supabase / SQL

When generating INSERT statements for the Recipes or any content table, always use dollar-quoting ($$...$$) for text fields — recipe text contains apostrophes that break single-quoted strings. Match the exact column format used in the app codebase before writing SQL.

## Auth

There are **two separate gates**:

1. **Site password** (`AUTH_PASSWORD`) — the entry gate, in `index.html` only. On success it writes a timestamp to `localStorage['boxkitchen_auth']` with a 30-day TTL. Inner tool pages are not re-gated; they rely on the user having entered through `index.html`.
2. **Manager PIN** (`MANAGER_PIN`, a.k.a. "manager mode" — see `MGR_KEY`, `mgrActions`) — present on the inner tool pages, gating destructive/admin actions (managing the item lists, edits, soft-retire, reorder). Regular staff can do the daily task (counts, check-offs) without it.

Both are shipped in public client code, so neither is real security — actual data protection depends on Supabase Row Level Security. **Secret hygiene:** never reproduce the password or PIN values in plans, summaries, comments, or output; refer to the latter only as "the manager PIN."

## Styling — in migration, do not assume

The site is mid-migration from the original dark theme to a light "Expo Board" look (paper `#fbfaf6` / ink / yellow / tomato, Barlow + Playfair), moving to a **shared stylesheet at `assets/kitchen.css`** one page per PR.

**Do not copy styling from a page without checking which side of the migration it is on.** Converted pages link `assets/kitchen.css`; unconverted pages still carry an inline dark `<style>` block. `recipe_dashboard.html` is the outlier — it hard-codes hex values with no CSS variables at all.

Plan, slice order, decisions, and per-page detail: **`docs/page-restyle.md`**.
