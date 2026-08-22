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
    "--font", "--font-cond", "--font-display",
}

# Greyscale allowed ONLY inside the @media print block. Print is a separate,
# deliberate palette: paper is white not cream, and every hue collapses to
# black because we assume a mono printer. These stay out of PALETTE so they
# can never leak onto a screen rule, where --ink and --grey are the answer.
PRINT_PALETTE = {"#fff", "#ffffff", "#eee", "#bbb", "#999", "#555", "#333", "#000"}

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

def print_span(text):
    """(start, end) of the @media print block in comment-stripped text, or None."""
    i = text.find("@media print")
    if i == -1:
        return None
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return (i, k)
    return (i, len(text))          # unbalanced; treat the rest as print

_spans = {}
def in_print(f, idx):
    """Is this offset inside that file's @media print block?"""
    if f not in _spans:
        _spans[f] = print_span(strip_comments(open(f).read()))
    sp = _spans[f]
    return bool(sp and sp[0] <= idx <= sp[1])

pages = sorted(glob.glob("*.html"))
assert pages, "run me from the repo root"
sheet = open(SHEET).read()
sheet_bare = strip_comments(sheet)

# 1 - every page loads the shared sheet, at the same cache-busting version.
#     The version matters: HTML and CSS are now separate cacheable files on
#     GitHub Pages (max-age=600), so without it a phone can hold old CSS
#     against new HTML for ten minutes after a deploy. Bump ?v= whenever
#     kitchen.css changes. Nine pages bumped and one forgotten is the real
#     failure mode, so they must all agree.
versions = {}
for f in pages:
    raw = open(f).read()
    m = re.search(r'href="%s(\?v=[^"]*)?"' % re.escape(SHEET), raw)
    if not m:
        fail(f, 1, f"does not link {SHEET}")
    else:
        versions[f] = m.group(1) or ""
        if not m.group(1):
            fail(f, 1, f"links {SHEET} with no ?v= cache-busting version")
if len(set(versions.values())) > 1:
    for f, v in sorted(versions.items()):
        fail(f, 1, f'kitchen.css version "{v}" disagrees with other pages '
                   f'- all ten must match')

# 1b - fonts must be <link>ed from the head, not @import-ed from the sheet.
#      An @import serialises: HTML -> kitchen.css -> fonts CSS -> font files.
if "@import" in sheet_bare:
    fail(SHEET, 1, "@import re-introduced - it costs a serialised round trip "
                   "before any text renders in the right face")
for f in pages:
    # Must be the stylesheet <link>, not just any mention: the preconnect hint
    # also contains fonts.googleapis.com, so a bare substring test passes even
    # when the actual stylesheet link has been removed.
    if not re.search(r'<link[^>]+rel="stylesheet"[^>]+fonts\.googleapis\.com/css2', open(f).read()):
        fail(f, 1, "no Google Fonts stylesheet <link> in <head> - every face "
                   "falls back, and the fallbacks are not condensed")

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

    # 4 - only sanctioned colours (covers %23 inside SVG data URIs too).
    #     Inside @media print, PRINT_PALETTE is allowed as well.
    for m in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|%23[0-9a-fA-F]{6}\b", bare):
        h = m.group(0).replace("%23", "#").lower()
        allowed = PALETTE | PRINT_PALETTE if in_print(f, m.start()) else PALETTE
        if h not in allowed:
            where = " (inside @media print)" if in_print(f, m.start()) else ""
            fail(f, lineno(bare, m.start()),
                 f"colour {h} is not in the palette{where} - add it to PALETTE in "
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

# 10 - every section banner in the sheet says which pages use it. The file is
#      one address shared by ten pages' rules; without the map, the next person
#      cannot tell a shared component from a page-private one, and the
#      never-delete rule leaves them no safe way to find out.
_raw_sheet = open(SHEET).read().split("\n")
_banner = re.compile(r"/\* \u2500\u2500 ([A-Z][A-Z /\u2014\u2013-]+?) \u2500")
for _i, _l in enumerate(_raw_sheet):
    _m = _banner.match(_l)
    if not _m:
        continue
    _j = _i
    while _j < len(_raw_sheet) and "*/" not in _raw_sheet[_j]:
        _j += 1
    _next = _raw_sheet[_j + 1] if _j + 1 < len(_raw_sheet) else ""
    if not _next.startswith("/* used by:"):
        fail(SHEET, _i + 1,
             f'section "{_m.group(1).strip()}" has no "/* used by: ... */" line - '
             f"say which pages reference it")

if fails:
    print(f"styling guard: {len(fails)} problem(s)\n")
    for x in fails:
        print("  " + x)
    print("\nsee docs/page-restyle.md and the Styling section of CLAUDE.md")
    sys.exit(1)
print(f"styling guard: clean ({len(pages)} pages + {SHEET})")
