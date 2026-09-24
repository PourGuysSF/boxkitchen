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

Check 11 renders the pages in headless Chrome, so this script now NEEDS
Chrome (set CHROME=/path/to/chrome if it is somewhere unusual). Everything
before it is static text and runs without one; the 16px rule cannot be,
because the bug it exists to catch is a rule LOSING the cascade, and you
cannot see that by reading either rule on its own.
"""
import json, re, shutil, subprocess, sys, tempfile, time, glob, os

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

# 11 - NO INPUT MAY RENDER BELOW 16px. Below 16px, iOS Safari zooms the page
#      the moment the field takes focus, and the kitchen is on phones: issue
#      #135. This project has produced that regression FOUR times, and every
#      one was the same shape - a new input that did not get a selector
#      specific enough to out-rank kitchen.css's
#      `.modal textarea,.modal select,.modal input[type="tel"],
#       .modal input[type="text"]` (0.95rem = 15.2px), which is (0,2,1) and
#      beats a bare class's (0,1,0) whatever the source order. Slice 3's
#      .inv-input declared font-size:16px, lost, and rendered at 15.2.
#
#      Every check above this one is static text, and every one of them would
#      have passed that bug: the page says 16px and means it. The only way to
#      see a rule losing the cascade is to resolve the cascade, so this one
#      loads the real pages in headless Chrome and reads the computed value.
#
#      TWO LIMITS, both real:
#      - It sees only inputs that exist in the MARKUP. Pages that build a
#        field at runtime (.count-input, .task-input, .who-select) are invisible
#        here. That is worth knowing and not worth pretending otherwise; all
#        four #135 regressions so far were markup-declared inputs.
#      - getComputedStyle resolves font-size on a display:none element, so
#        fields inside closed modals are measured without opening anything.
#        Nothing here clicks, types, or depends on a modal being reachable.
FS_MIN = 16.0

# Types with no text you can type into, so nothing to zoom towards.
FS_SKIP_TYPES = {"hidden", "checkbox", "radio", "submit", "button", "reset",
                 "range", "color", "image", "file"}

# The debt register: every input that was ALREADY under 16px when this check
# was written, with the size each one measured. They are not exceptions on
# principle - they are #135, live, on nine of the ten pages.
#
# There are 75 of them, and the number is the point. The first version of this
# check keyed its gate neutralisation on a comment only two pages carry, so
# seven pages silently measured index.html instead of themselves and reported
# nothing wrong. The honest count is 75: 69 at 15.2px, 4 at 13.12px
# (#viewAs / #viewStation on prep and line, the smallest on the site) and 2 at
# 14.4px. **#135 is not a slice-3 bug that got fixed; it is the site's default.**
#
# Most of them share one cause: kitchen.css's `.modal textarea,.modal select,
# .modal input[type="tel"],.modal input[type="text"]` at 0.95rem. Raising that
# one rule to 16px would clear roughly 69 of the 75 in a single edit - which is
# exactly why it is not done here: it is a visible change to every form on ten
# pages and a ?v= bump on all of them, and it belongs in a pass of its own that
# can be measured and looked at, not slipped into a provenance slice.
#
# A registered entry is checked BOTH ways: it must still exist, and it must
# still measure exactly what is recorded. Fix one and the guard tells you to
# take it off the list; make one worse and the guard tells you that too. A
# register that can drift is a register that quietly grows.
FS_REGISTER = {
    # recipe_dashboard.html
    ("recipe_dashboard.html", "searchBox"):    "15.2px",
    ("recipe_dashboard.html", "pinInput"):     "15.2px",
    ("recipe_dashboard.html", "recipeName"):   "15.2px",
    ("recipe_dashboard.html", "recipeCategory"): "15.2px",
    ("recipe_dashboard.html", "recipeCategoryNew"): "15.2px",
    ("recipe_dashboard.html", "recipeStation"): "15.2px",
    ("recipe_dashboard.html", "recipeStationNew"): "15.2px",
    ("recipe_dashboard.html", "recipeYield"):  "15.2px",
    ("recipe_dashboard.html", "deleteConfirmInput"): "15.2px",
    # tempest_costing.html
    ("tempest_costing.html", "search"):        "15.2px",
    ("tempest_costing.html", "fName"):         "15.2px",
    ("tempest_costing.html", "fAlias"):        "15.2px",
    ("tempest_costing.html", "fQty"):          "15.2px",
    ("tempest_costing.html", "fUnit"):         "15.2px",
    ("tempest_costing.html", "fPrice"):        "15.2px",
    # tempest_flash.html
    ("tempest_flash.html", "enteredBy"):       "14.4px",
    ("tempest_flash.html", "newVendorName"):   "15.2px",
    # tempest_line.html
    ("tempest_line.html", "viewAs"):           "13.12px",
    ("tempest_line.html", "viewStation"):      "13.12px",
    ("tempest_line.html", "pinInput"):         "15.2px",
    ("tempest_line.html", "addName"):          "15.2px",
    ("tempest_line.html", "addCat"):           "15.2px",
    ("tempest_line.html", "addStation"):       "15.2px",
    ("tempest_line.html", "addDay"):           "15.2px",
    ("tempest_line.html", "staffName"):        "15.2px",
    ("tempest_line.html", "staffShift"):       "15.2px",
    ("tempest_line.html", "secDaily"):         "15.2px",
    ("tempest_line.html", "secCleaning"):      "15.2px",
    ("tempest_line.html", "secWeekly"):        "15.2px",
    ("tempest_line.html", "nbBody"):           "15.2px",
    ("tempest_line.html", "nbBy"):             "15.2px",
    # tempest_meat.html
    ("tempest_meat.html", "countedBy"):        "15.2px",
    ("tempest_meat.html", "pinInput"):         "15.2px",
    ("tempest_meat.html", "itemName"):         "15.2px",
    ("tempest_meat.html", "itemCategory"):     "15.2px",
    ("tempest_meat.html", "itemCategoryNew"):  "15.2px",
    ("tempest_meat.html", "itemPar"):          "15.2px",
    # tempest_notes.html
    ("tempest_notes.html", "noteBody"):        "15.2px",
    ("tempest_notes.html", "noteBy"):          "15.2px",
    ("tempest_notes.html", "pinInput"):        "15.2px",
    ("tempest_notes.html", "editNoteBody"):    "15.2px",
    # tempest_orders.html
    ("tempest_orders.html", "filledBy"):       "14.4px",
    ("tempest_orders.html", "pinInput"):       "15.2px",
    ("tempest_orders.html", "addItemName"):    "15.2px",
    ("tempest_orders.html", "addItemUnit"):    "15.2px",
    ("tempest_orders.html", "addItemPar"):     "15.2px",
    ("tempest_orders.html", "addItemCat"):     "15.2px",
    ("tempest_orders.html", "addItemVendor"):  "15.2px",
    ("tempest_orders.html", "moveShelf"):      "15.2px",
    ("tempest_orders.html", "newUnitName"):    "15.2px",
    ("tempest_orders.html", "newShelfVendor"): "15.2px",
    ("tempest_orders.html", "newShelfName"):   "15.2px",
    ("tempest_orders.html", "otherUnitName"):  "15.2px",
    ("tempest_orders.html", "nbBody"):         "15.2px",
    ("tempest_orders.html", "nbBy"):           "15.2px",
    # tempest_portion.html
    ("tempest_portion.html", "countedBy"):     "15.2px",
    ("tempest_portion.html", "pinInput"):      "15.2px",
    ("tempest_portion.html", "itemName"):      "15.2px",
    ("tempest_portion.html", "itemStation"):   "15.2px",
    ("tempest_portion.html", "itemStationNew"): "15.2px",
    ("tempest_portion.html", "itemPar"):       "15.2px",
    # tempest_prep.html
    ("tempest_prep.html", "viewAs"):           "13.12px",
    ("tempest_prep.html", "viewStation"):      "13.12px",
    ("tempest_prep.html", "pinInput"):         "15.2px",
    ("tempest_prep.html", "addName"):          "15.2px",
    ("tempest_prep.html", "addCat"):           "15.2px",
    ("tempest_prep.html", "addStation"):       "15.2px",
    ("tempest_prep.html", "addDay"):           "15.2px",
    ("tempest_prep.html", "staffName"):        "15.2px",
    ("tempest_prep.html", "staffShift"):       "15.2px",
    ("tempest_prep.html", "secDaily"):         "15.2px",
    ("tempest_prep.html", "secCleaning"):      "15.2px",
    ("tempest_prep.html", "secWeekly"):        "15.2px",
    ("tempest_prep.html", "nbBody"):           "15.2px",
    ("tempest_prep.html", "nbBy"):             "15.2px",
}

FS_COLLECT = r"""
<script>
/* injected by scripts/check_styling.py - reads the RESOLVED font-size of every
   field in the markup. No clicks, no typing, no modal opening. */
(function(){
  var out=[],els=document.querySelectorAll('input,textarea,select');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    out.push({type:(e.tagName==='INPUT'?(e.type||'text').toLowerCase()
                                       :e.tagName.toLowerCase()),
              id:e.id||'', cls:e.className||'',
              fs:getComputedStyle(e).fontSize});
  }
  var d=document.createElement('div');d.id='fsResults';
  /* which page this really is: tempest_costing and tempest_flash bounce to
     index.html when the site password has not been entered, and the dumped DOM
     would then be INDEX's - collector and all - reporting index's inputs under
     the other page's name. Stamped so that cannot pass silently. */
  d.textContent=JSON.stringify({page:location.pathname.split('/').pop(),fields:out});
  document.body.appendChild(d);
})();
</script>
"""

# Every page but index.html bounces to index.html when the site password has
# not been entered, so the bounce comes out. Matched on the REDIRECT, not on the
# comment above it: only two of the nine label that block, and the first version
# of this check keyed on the label - so seven pages silently measured index.html
# instead of themselves and reported "0 under 16px" for a page it never loaded.
# The page stamp in FS_COLLECT is what caught that, and is the real guard here.
FS_GATE = re.compile(r"window\.location\.replace\('index\.html'\)")
FS_GATE_OFF = "void 0 /* gate neutralised by check_styling.py */"
FS_RESULTS = re.compile(r'<div id="fsResults">(.*?)</div>', re.S)
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
]


def find_chrome():
    env = os.environ.get("CHROME")
    if env:
        return env if os.path.exists(env) else shutil.which(env)
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "google-chrome-stable", "chromium",
              "chromium-browser", "chrome"):
        found = shutil.which(n)
        if found:
            return found
    return None


def measure_inputs(chrome, tmp):
    """{page: [field, ...]} - one Chrome per page, all launched at once.

    --host-resolver-rules blocks every hostname: these pages talk to Supabase
    on load, and a styling check must never touch the live database (nor wait
    on the webfonts, which would otherwise hold each run open).
    """
    shutil.copytree(os.path.join(os.getcwd(), "assets"),
                    os.path.join(tmp, "assets"))
    procs = {}
    for f in pages:
        src = FS_GATE.sub(FS_GATE_OFF, open(f, encoding="utf-8").read())
        if "</body>" not in src:
            fail(f, 1, "no </body> - check 11 cannot measure this page")
            continue
        src = src.replace("</body>", FS_COLLECT + "</body>", 1)
        page_path = os.path.join(tmp, f)
        open(page_path, "w", encoding="utf-8").write(src)
        dom = os.path.join(tmp, "dom-" + f)
        fo, fe = open(dom, "w"), open(os.path.join(tmp, "err-" + f), "w")
        procs[f] = (subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions", "--disable-sync",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--host-resolver-rules=MAP * ~NOTFOUND",
             "--user-data-dir=" + os.path.join(tmp, "cd-" + f),
             "--window-size=390,844", "--virtual-time-budget=5000",
             "--dump-dom", "file://" + page_path],
            stdout=fo, stderr=fe), dom, fo, fe)

    # --dump-dom writes the finished DOM and then, on this machine, does not
    # exit. So poll each page's file for the results div and kill it there.
    found, deadline = {}, time.time() + 60
    while procs and time.time() < deadline:
        time.sleep(0.1)
        for f in list(procs):
            proc, dom, fo, fe = procs[f]
            m = FS_RESULTS.search(open(dom).read())
            if m:
                got = json.loads(m.group(1))
                if got.get("page") != f:
                    fail(f, 1, "check 11: measured %s instead - the page "
                               "redirected, so the site-password gate was not "
                               "neutralised (see FS_GATE)" % (got.get("page"),))
                else:
                    found[f] = got["fields"]
                proc.kill(); fo.close(); fe.close(); del procs[f]
    for f, (proc, dom, fo, fe) in procs.items():
        proc.kill(); fo.close(); fe.close()
        fail(f, 1, "check 11: the page never reported its fields - it may have "
                   "thrown before </body>; see the run's stderr")
    return found


chrome = find_chrome()
if not chrome:
    sys.exit("check_styling: no Chrome found, so the 16px input rule (check 11, "
             "issue #135) cannot run. Set CHROME=/path/to/chrome.")
with tempfile.TemporaryDirectory() as _tmp:
    measured = measure_inputs(chrome, _tmp)

seen = set()
for f, fields in sorted(measured.items()):
    for fld in fields:
        if fld["type"] in FS_SKIP_TYPES:
            continue
        key = (f, fld["id"])
        what = ("#" + fld["id"] if fld["id"]
                else "%s.%s" % (fld["type"], fld["cls"] or "(no class)"))
        px = float(fld["fs"].replace("px", ""))
        if key in FS_REGISTER:
            seen.add(key)
            if fld["fs"] != FS_REGISTER[key]:
                fail(f, 1, f"{what} is on the #135 register at "
                           f"{FS_REGISTER[key]} but now renders at {fld['fs']} - "
                           f"if it is fixed (>= 16px), take it off FS_REGISTER "
                           f"in scripts/check_styling.py; if it got smaller, "
                           f"that is a new #135")
            continue
        if px < FS_MIN:
            # one problem, one message: an id-less field gets the same failure
            # with the extra sentence it needs, not a second failure.
            fail(f, 1, f"{what} renders at {fld['fs']}, under 16px - iOS zooms "
                       f"the page when it takes focus (#135). It has most "
                       f"likely lost the cascade to kitchen.css's `.modal "
                       f'input[type="text"]` (0.95rem): qualify the selector, '
                       f'as `.modal input[type="text"].your-class,.your-class`, '
                       f"the way .pick-filter and .inv-input do"
                       + ("" if fld["id"] else
                          " (and give it an id: without one it cannot be named "
                          "on FS_REGISTER at all)"))

# 11b - the register must not rot: an entry whose input is gone (renamed,
#       removed) silently retires its own check, exactly as #9 guards against.
for (f, fid) in sorted(FS_REGISTER):
    if f not in pages:
        fail(SHEET, 1, f"FS_REGISTER lists {f}, which is not a page in this "
                       f"repo any more - update scripts/check_styling.py")
    elif f in measured and (f, fid) not in seen:
        fail(f, 1, f"FS_REGISTER lists #{fid}, which this page no longer has - "
                   f"update scripts/check_styling.py")

if fails:
    print(f"styling guard: {len(fails)} problem(s)\n")
    for x in fails:
        print("  " + x)
    print("\nsee docs/page-restyle.md and the Styling section of CLAUDE.md")
    sys.exit(1)
_n = sum(1 for fs in measured.values() for fld in fs
         if fld["type"] not in FS_SKIP_TYPES)
print(f"styling guard: clean ({len(pages)} pages + {SHEET}; "
      f"{_n} inputs measured, {len(FS_REGISTER)} on the #135 register)")
