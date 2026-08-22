# Reviewing a change to this site

Distilled from the adversarial review of the 2026-08 Expo Board restyle, which found 22
real issues across ten pages. This file is not about that project — it is the set of
methods that found them, kept for the next one.

Open work from that review lives in **GitHub issues**, not here. A checklist that also
tries to be a to-do list becomes wrong the moment something ships.

---

## 1. Know which failure you're hunting

Four shapes, in order of how badly they bite:

1. **A control that renders but no longer works** — a class the JS needed was renamed or lost.
2. **Two states that now look identical** — a cook can't tell done from not-done.
3. **Something unreachable on a phone** — hidden behind a fixed bar, or in a scroll dead zone.
4. **The OS renders your page differently than you do** — Chrome's Auto Dark Theme, iOS
   dark-mode native pickers, `apple-mobile-web-app-status-bar-style` on a home-screen
   install, safe-area insets, forced-colors mode.

Nobody reports any of these as a bug. They report *"the prep list is being weird."*

Shape 4 is the one that gets missed, because it never appears when you open the page on
your own phone, in daylight, with the OS in light mode — which is how every restyle slice
was verified.

## 2. Review the diff **and** the absence

A diff shows what moved. It cannot show what should be there and never was in either
version. Both questions have to be asked:

- *What did this change take away?* — finds regressions. This is what caught four pages
  silently losing their bottom clearance.
- *What does this kind of page need that the old one didn't?* — finds omissions. This is
  where `color-scheme`, safe-area insets, focus styles and print rules live. `git diff`
  shows nothing for any of them.

A change that alters the **class** of page (dark → light, desktop → mobile) mostly creates
requirements rather than breaking existing ones, and requirements are exactly what a diff
hides.

## 3. Run the guard before anything else

```
python3 scripts/check_styling.py
```

Nine mechanical checks: every page links the shared sheet, no dark-theme leftovers, every
colour is in the sanctioned palette, no page redeclares a core token, every `var()`
resolves, no control edge on `--hair`. If it's red, stop and fix that first.

It is not a formality — it caught a `:hover` rule that two careful passes had missed.

## 4. Contrast is arithmetic. Never eyeball it.

Compute it. Judging by eye at a desk tells you what *you* can read in *that* light, which
is the least reliable instrument available.

And check **both** kinds:

- **Text contrast** — 4.5:1 normal, 3:1 for large.
- **Non-text contrast (WCAG 1.4.11)** — **3:1 for the visible boundary of a control.**

The second one is the one that gets forgotten. `--hair` sat at 1.27:1 as the border of the
checkbox — the most-tapped control in the kitchen — through nine slices and a consistency
sweep, because only text was ever checked.

Token roles are in `CLAUDE.md`. `--hair` is separators; `--edge` is control boundaries.

## 5. Class names are load-bearing

The JS reaches for them by name. Renaming a CSS class breaks behaviour no visual review
will catch. Change rules, never names.

**Many class names appear in no markup at all** — they're built at runtime:

`.sortable-ghost` / `-chosen` / `-drag` (injected by SortableJS) · `'st-'+station` ·
`'cat-'+category` · `cleaning` / `daily` / `weekly` · `mode-kit` / `mode-make` ·
`filled` · `locked` · `has-qty` · `retired` · `assigned` · `tempest` / `showdown`

Grep the JS for the **string fragment**, not the full class name. A rule is only dead once
you've proven no page composes that name at runtime.

## 6. Check the state pairs render obviously differently

State is expressed by fill, weight and border — never hue — so it's easy for an "on" state
to collapse into its base.

| page | pair |
|---|---|
| portion / meat | `.count-input` vs `.filled` |
| orders | `.qty-input` vs `.filled` vs `.locked`; `.item-row` vs `.has-qty` |
| flash | `.money-wrap` vs `.filled` |
| prep / line | `.checkbox` vs `.checked`; `.task` vs `.task.done` |
| notes | categories; resolved vs open |
| recipes | `.card` vs `.card.archived` |
| costing | `.uc` vs `.uc.none`; `.ing-pack.unset` |
| all | `.toast` vs `.toast.err` **and** `.toast.error` |

That last row matters most: Flash sets `.err`, every other page sets `.error`, and an error
rendering as a success is the worst thing this stylesheet can do.

## 7. `touch-action` belongs on the drag handles only

`.drag-handle` and `.staff-grip`, nowhere else. Widened → the kitchen can't scroll prep,
line or orders. Deleted → drag fights the scroll. Test it with a finger, manager mode on;
this cannot be checked on a desktop.

## 8. One stylesheet, one blast radius

`kitchen.css` is loaded by all ten pages. A change made for the page in front of you can
break a different one. **Walk more than the page you changed** — especially Notes and the
count sheets, which were converted first and have been restyled underneath the most.

## 9. Review read-only. The database is live.

Every page writes to production and the kitchen is using them.

- **Never** press Submit/Save, check a task off, drag a row, or use the ＋ note button.
- **Orders: typing a quantity writes** after a 400ms debounce. Do not type.
- **Flash: Manage Vendors writes instantly, no confirmation.** Open, look, Cancel.
- Prefer verifying from history: prep/line and flash keep past days; orders has a
  Previous view.
- The site password and manager PIN are plain text in these files — never print or repeat
  them.

## 10. To see a state you can't safely create

Run a local copy with a stubbed `api()`:

```
python3 -m http.server 8000     # in a worktree, then open on a phone over Wi-Fi
```

That lets you fill every state, in both OS themes, with zero write risk.

Toggling a class in the console is the fallback, but be honest about what it proves: it
confirms the CSS rule exists, not that a cook can tell the states apart mid-service with a
real list. Say which claim you're making.

## 11. Rank findings by damage, not by how easy they are to fix

1. **Breaks a task** — a control that doesn't work, or content unreachable on a phone.
2. **Misleads** — two states that look alike, an error styled as success, a number that
   reads wrong.
3. **Cosmetic** — spacing, contrast, drift between pages.

For each: page, selector, how to reproduce, and what a cook would experience.
**A finding with no reproduction path is a guess — say so.**

---

## And when the review is done

Say what "passed" means, and give tier-3 findings an owner. Findings without a closing
condition become a document nobody re-reads — which is how the last one ended up needing
its own review.
