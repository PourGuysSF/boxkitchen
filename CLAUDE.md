# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Safety

Boxkitchen is a live production site used during service. Never run write/deploy/migration commands without asking first. Read-only commands (grep, read, git status) are always fine — say so up front so I don't have to interrupt to check.

## What this is

boxkitchen is a kitchen operations system for the Tempest restaurant. It is a **static multi-page web app** — a set of standalone `.html` files, each with its own inline `<style>` and `<script>`. There is **no build system, no framework, no bundler, no package.json, and no tests**. `vendor/sortablejs-1.15.7.min.js` is the only third-party dependency (used by `tempest_prep.html` for drag-reordering).

## Running / developing

- Open any `.html` file directly in a browser, or serve the folder statically: `python3 -m http.server` then visit `http://localhost:8000`.
- There is nothing to build, lint, or test. Editing a file and reloading the browser is the entire dev loop.
- Deployment is static hosting of these files as-is.

## Architecture

**`index.html` is the hub.** It gates entry (see Auth below), links out to each tool page, renders day-of-week reminders (the `REMINDERS` map keyed by `getDay()`), and builds a 72-hour "Activity" feed by querying the `orders`, `meat_counts`, and `portion_counts` tables and merging them by timestamp. Each other page is a self-contained tool:

- `tempest_line.html` / `tempest_prep.html` — prep & cleaning checklists
- `tempest_orders.html` — daily order guides (Birite/Dairy, Produce/Protein)
- `tempest_portion.html` / `tempest_meat.html` — daily counts vs par
- `tempest_notes.html` — staff notes / equipment issues / 86'd items
- `recipe_dashboard.html` — searchable recipe library, fully backed by the Supabase **`Recipes`** table (capital R) — GET/POST/PATCH/DELETE like every other page. (localStorage is used only for the auth gate, not for recipes.)

**Backend is Supabase, accessed directly from the browser** via its PostgREST REST API — there is no server-side code in this repo. Every page embeds the **same** Supabase project URL and anon key inline and defines its own copy of a helper:

```js
api(method, table, query, data, cb)  // XMLHttpRequest to /rest/v1/<table>?<query>
```

REST verbs map to PostgREST semantics (`GET`/`POST`/`PATCH`/`DELETE`, filters like `location=eq.Tempest`, `count_date=gte.<date>`, `order=...desc`). This `api()` helper, the anon key, and the design tokens are **duplicated in each file** — there is no shared JS. A change to any shared pattern must be applied per-file, and a new page is best created by copying an existing one as a template.

## Data model conventions

Tables split into **definition/par** vs **daily-entry** pairs:

- `meat_items` (par definitions) ↔ `meat_counts` (daily counts)
- `portion_items` ↔ `portion_counts`
- `order_units` / `order_items` ↔ `orders`
- `prep_items` ↔ `prep_logs`
- plus `notes`, `staff`

Rows are scoped by a `location` column. The location is currently hardcoded to `Tempest` (`location=eq.Tempest`) throughout — the column exists so the same tables can serve multiple locations later.

## Supabase / SQL

When generating INSERT statements for the Recipes or any content table, always use dollar-quoting ($$...$$) for text fields — recipe text contains apostrophes that break single-quoted strings. Match the exact column format used in the app codebase before writing SQL.

## Auth

There are **two separate gates**:

1. **Site password** (`AUTH_PASSWORD`) — the entry gate, in `index.html` only. On success it writes a timestamp to `localStorage['boxkitchen_auth']` with a 30-day TTL. Inner tool pages are not re-gated; they rely on the user having entered through `index.html`.
2. **Manager PIN** (`MANAGER_PIN`, a.k.a. "manager mode" — see `MGR_KEY`, `mgrActions`) — present on the inner tool pages, gating destructive/admin actions (managing the item lists, edits, soft-retire, reorder). Regular staff can do the daily task (counts, check-offs) without it.

Both are shipped in public client code, so neither is real security — actual data protection depends on Supabase Row Level Security. **Secret hygiene:** never reproduce the password or PIN values in plans, summaries, comments, or output; refer to the latter only as "the manager PIN."

## Shared design system (duplicated per page)

Dark theme defined via CSS custom properties on `:root` (`--bg`, `--surface`, `--accent: #e85d3a`, etc.), DM Sans + Playfair Display from Google Fonts, mobile-first layout (these run on kitchen phones/tablets — note the `user-scalable=no`, sticky headers, and large touch targets). Keep new UI consistent by reusing these tokens and the existing `.card` / `.section` / `.activity-row` patterns.
