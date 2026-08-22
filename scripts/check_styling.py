#!/usr/bin/env python3
"""
Styling guard for the Expo Board look.

The restyle (PRs #98-#114) collapsed ten inline dark stylesheets into one
shared assets/kitchen.css. Nothing was stopping page eleven - or the next
feature on an existing page - from quietly reintroducing a second palette.
The #114 sweep was one manual pass typed into a terminal and saved nowhere.
This is that pass, made runnable.

    python3 scripts/check_styling.py

Exit 0 = clean. Exit 1 = something drifted, with the file and line.

Adding a colour is meant to be a deliberate edit to PALETTE below, not a
thing that happens by accident in a JS template string at 6am.
"""
import re, sys, glob, os

SHEET = "assets/kitchen.css"

# The only colours that may appear anywhere in the repo. Anything else is
# either drift from the old dark theme or a new palette nobody agreed to.
PALETTE = {
    # core tokens
    "#fbfaf6", "#121212", "#6a6a6a", "#e2e0d8", "#a9a7a0",
    "#b8b6ae", "#ffe600", "#e85d3a", "#f3f1ea",
    "#8e8c84",              # --edge, control boundaries
    "#b42318",              # --danger, destructive + error
    # retuned accents, chosen against cream
    "#a25c00", "#22457f", "#5f4589", "#2d6a4f",
    # plain white, used as button text on filled controls
    "#fff", "#ffffff",
}

# Tokens that live in :root in kitchen.css and nowhere else. A page may
# declare its own scoped tokens (--cat-*, --sec-*, --st-*); it may not
# redeclare one of these, because then there are two sources of truth.
CORE_TOKENS = {
    "--paper", "--ink", "--grey", "--hair", "--faint", "--dash",
    "--yellow", "--tomato", "--press", "--edge", "--danger",
}

# Selectors that are the visible edge of something you tap. These may never
# use --hair. The heuristic below also catches new ones, but it is a
# heuristic - .money-wrap slipped past it because nothing in the selector
# or the rule says "control". This list is the authoritative half.
CONTROL_SELECTORS = {
    ".cat-opt,.nb-cat", ".count-input", ".money-wrap", ".station-assign",
    ".mode-pill", ".checkbox", ".who-select", ".task-input", ".note-btn",
    ".note-input", ".move-btn", ".shelf-btn", ".unit-select",
    ".unit-row .u-btn", ".link-btn", ".vname-input",
    ".card-mgr-actions .mgr-edit-btn,.mgr-archive-btn,"
    ".mgr-unarchive-btn,.card-mgr-actions .mgr-delete-btn",
}

# Fingerprints of the pre-2026-08 dark theme.
DEAD = ["--surface", "--surface2", "--bg:", "--dim:", "--muted:", "--accent:",
        "--accent-dim", "--green-dim", "--yellow-dim",
        "#0f1115", "#1a1d24", "#22262f", "#2a2d35", "#e8e6e3", "#8a8a8a",
        "DM Sans", "DM+Sans", "black-translucent"]

fails = []
def fail(f, line, msg):
    fails.append(f"{f}:{line}: {msg}")

def strip_comments(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", t)   # keep https:// intact

def lineno(text, idx):
    return text.count("\n", 0, idx) + 1

pages = sorted(glob.glob("*.html"))
assert pages, "run me from the repo root"
sheet = open(SHEET).read()
sheet_bare = strip_comments(sheet)

# 1 - every page loads the shared sheet
for f in pages:
    if 'href="%s"' % SHEET not in open(f).read():
        fail(f, 1, f"does not link {SHEET}")

# 2 - the shared sheet still opts out of OS re-theming
if "color-scheme:light" not in sheet_bare:
    fail(SHEET, 1, "color-scheme:light is missing - Chrome Auto Dark Theme "
                   "will invert the site on Android phones in dark mode")

for f in pages + [SHEET]:
    raw = open(f).read()
    bare = strip_comments(raw)

    # 3 - no fingerprints of the dark theme
    for d in DEAD:
        i = bare.find(d)
        if i != -1:
            fail(f, lineno(bare, i), f"dark-theme leftover: {d}")

    # 4 - only sanctioned colours (covers %23 inside SVG data URIs too)
    for m in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|%23[0-9a-fA-F]{6}\b", bare):
        h = m.group(0).replace("%23", "#").lower()
        if h not in PALETTE:
            fail(f, lineno(bare, m.start()),
                 f"colour {h} is not in the palette - add it to PALETTE in "
                 f"scripts/check_styling.py on purpose, or use a token")

    # 5 - no page redeclares a core token
    if f != SHEET:
        for m in re.finditer(r"(--[a-z0-9-]+)\s*:", bare):
            if m.group(1) in CORE_TOKENS:
                fail(f, lineno(bare, m.start()),
                     f"redeclares core token {m.group(1)} - it belongs in {SHEET} only")

    # 6 - head metas agree with a paper-coloured page
    if f != SHEET and 'name="theme-color"' not in raw:
        fail(f, 1, 'missing <meta name="theme-color" content="#fbfaf6">')

# 7 - every var() resolves
defined, used = set(), {}
for f in pages + [SHEET]:
    bare = strip_comments(open(f).read())
    defined |= set(re.findall(r"(--[a-z0-9-]+)\s*:", bare))
    for m in re.finditer(r"var\((--[a-z0-9-]+)", bare):
        used.setdefault(m.group(1), (f, lineno(bare, m.start())))
for v, (f, ln) in used.items():
    if v not in defined:
        fail(f, ln, f"var({v}) is never defined - it silently resolves to nothing")

# 8 - a control's edge must be visible (WCAG 1.4.11 wants 3:1; --hair is 1.27:1)
for i, ln in enumerate(sheet_bare.split("\n"), 1):
    if "border:" not in ln or "solid var(--hair)" not in ln:
        continue                      # border-bottom on a list row is fine
    sel = ln.split("{")[0].strip()
    if (sel in CONTROL_SELECTORS or "cursor:pointer" in ln or "outline:none" in ln
            or re.search(r"\b(input|select|btn|button|checkbox)\b", sel, re.I)):
        fail(SHEET, i, f"{sel} uses --hair (1.27:1) as a control edge - use --edge")

# 9 - and every selector on that list must still exist, so renaming one
#     doesn't silently retire its check
for sel in CONTROL_SELECTORS:
    if sel + "{" not in sheet_bare.replace("\n", ""):
        fail(SHEET, 1, f"CONTROL_SELECTORS lists {sel}, which no longer exists - "
                       f"update scripts/check_styling.py")

if fails:
    print(f"styling guard: {len(fails)} problem(s)\n")
    for x in fails:
        print("  " + x)
    print("\nsee docs/page-restyle.md and the Styling section of CLAUDE.md")
    sys.exit(1)
print(f"styling guard: clean ({len(pages)} pages + {SHEET})")
