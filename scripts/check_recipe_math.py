#!/usr/bin/env python3
"""
Guard for assets/recipe-math.js — the shared costing math (docs/recipe-costing.md,
"Where the math lives", M5). Slice 2: the units and the amount reader.

    python3 scripts/check_recipe_math.py              # the check (CI runs this)
    python3 scripts/check_recipe_math.py --scan FILE  # read every line in a saved
                                                      # copy of the live recipes and report

The file is run in headless Chrome, the engine the kitchen's phones use, the
same way the site's other checks run. Four things are checked:

  1. fixtures — every unit, every spelling on the live price list and in the
     live recipe text, and every hand-checked line in Slice 2's "Done when";
  2. within-kind conversions against exact factors;
  3. deliberate breaks — the file is copied, broken on purpose (oz as volume,
     # not lb, 1 1/2 read wrong), and each break must be caught by (1)/(2);
  4. every page that loads the file loads the same ?v=.

Exit 0 = clean. Exit 1 = a failure, named.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(ROOT, "assets", "recipe-math.js")

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
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


# ---- fixtures -------------------------------------------------------------
# spelling -> (unit, kind). Includes every pack_unit on the live price list
# (Ground truth, 2026-11-02, re-read 2026-11-08) and every recipe spelling.
SPELLINGS = {
    # price list pack units
    "lb": ("lb", "weight"), "Lb": ("lb", "weight"), "oz": ("oz", "weight"),
    "each": ("each", "count"), "Each": ("each", "count"), "gal": ("gal", "volume"),
    "bunch": ("bunch", "count"), "1/2 gal": ("1/2 gal", "volume"),
    "fl oz": ("fl oz", "volume"), "qt": ("qt", "volume"), "can": ("can", "count"),
    "ml": ("ml", "volume"), "bottle": ("bottle", "count"), "L": ("L", "volume"),
    "g": ("g", "weight"), "bag": ("bag", "count"), "dozen": ("dozen", "count"),
    "pt": ("pt", "volume"),
    # recipe spellings
    "C": ("cup", "volume"), "c.": ("cup", "volume"), "cup": ("cup", "volume"),
    "cups": ("cup", "volume"), "Tbsp": ("tbsp", "volume"), "TB.": ("tbsp", "volume"),
    "Tb.": ("tbsp", "volume"), "tsp": ("tsp", "volume"), "tsp.": ("tsp", "volume"),
    "#": ("lb", "weight"), "lb.": ("lb", "weight"), "oz.": ("oz", "weight"),
    "g.": ("g", "weight"), "ea": ("each", "count"), "ea.": ("each", "count"),
    "qt.": ("qt", "volume"), "quart": ("qt", "volume"), "pint": ("pt", "volume"),
    "pints": ("pt", "volume"), "bu.": ("bunch", "count"),
    "sprigs": ("sprig", "count"), "cloves": ("clove", "count"),
    "pieces": ("piece", "count"), "piece": ("piece", "count"),
    "sheets": ("sheet", "count"), "jug.": ("jug", "count"), "tube": ("tube", "count"),
    "case": ("case", "count"), "inch": ("inch", "count"), "heads": ("head", "count"),
    "box": ("box", "count"), "boxes": ("box", "count"), "kg": ("kg", "weight"),
    # not units
    "TT": (None, None), "large": (None, None), "bay": (None, None), "": (None, None),
}

# every unit in the plan's table, with its kind — units() must return exactly these
UNITS = [
    ("g", "weight"), ("kg", "weight"), ("oz", "weight"), ("lb", "weight"),
    ("tsp", "volume"), ("tbsp", "volume"), ("fl oz", "volume"), ("cup", "volume"),
    ("pt", "volume"), ("qt", "volume"), ("1/2 gal", "volume"), ("gal", "volume"),
    ("ml", "volume"), ("L", "volume"),
    ("each", "count"), ("dozen", "count"), ("bunch", "count"), ("clove", "count"),
    ("head", "count"), ("sprig", "count"), ("can", "count"), ("bottle", "count"),
    ("jug", "count"), ("tube", "count"), ("sheet", "count"), ("piece", "count"),
    ("bag", "count"), ("case", "count"), ("box", "count"), ("inch", "count"),
]

# line -> (amount, unit, words, unitWord) ; amount None = no amount (words, why)
LINES = [
    # Slice 2 "Done when"
    ("5# Sweet onion, cut into rings on mandolin", 5, "lb", "Sweet onion, cut into rings on mandolin", True),
    ("1½ Tbsp Salt", 1.5, "tbsp", "Salt", True),
    ("1 1/2 cups flour", 1.5, "cup", "flour", True),
    ("Salt TT", None, "no number", "Salt TT", None),
    ("32 oz. soy", 32, "oz", "soy", True),
    ("2 bay leaves", 2, "each", "bay leaves", False),
    # planner's rulings, 2026-11-05
    ("1# butter", 1, "lb", "butter", True),
    ("1 bu. chives", 1, "bunch", "chives", True),
    ("¼ bu. parsley", 0.25, "bunch", "parsley", True),
    ("6 sprigs thyme", 6, "sprig", "thyme", True),
    ("10 cloves garlic", 10, "clove", "garlic", True),
    ("2 pieces kombu", 2, "piece", "kombu", True),
    ("4 sheets nori", 4, "sheet", "nori", True),
    ("20 large guajillo chiles, stemmed and seeded", 20, "each", "large guajillo chiles, stemmed and seeded", False),
    ("Pepper TT", None, "no number", "Pepper TT", None),
    # Stephen's ruling (a), 2026-11-08: two amounts added -> no amount
    ("1 Tbsp + 1 tsp dried Mexican oregano", None, "two amounts", "1 Tbsp + 1 tsp dried Mexican oregano", None),
    # amounts: 2, 1.5, ½, 1½, 1 1/2, 1/2, and any fraction character
    ("2 C Lentils", 2, "cup", "Lentils", True),
    ("1.5 qt. half & half", 1.5, "qt", "half & half", True),
    ("½ cup olive oil", 0.5, "cup", "olive oil", True),
    ("1/2 tsp salt", 0.5, "tsp", "salt", True),
    ("1⅓ cups cider vinegar", 4/3, "cup", "cider vinegar", True),
    ("¾ C Water", 0.75, "cup", "Water", True),
    ("2.5 lb. Velveeta cheese", 2.5, "lb", "Velveeta cheese", True),
    # spellings in context
    ("2 qt. sliced shallots", 2, "qt", "sliced shallots", True),
    ("4 c. red wine vinegar", 4, "cup", "red wine vinegar", True),
    ("1 TB. dried Mexican oregano", 1, "tbsp", "dried Mexican oregano", True),
    ("4 Tb. gochujang", 4, "tbsp", "gochujang", True),
    ("1 tsp. ground cinnamon", 1, "tsp", "ground cinnamon", True),
    ("8 g. Thai chili, smashed", 8, "g", "Thai chili, smashed", True),
    ("10 ea Garlic clove, chopped", 10, "each", "Garlic clove, chopped", True),
    ("2 ea. bay leaf", 2, "each", "bay leaf", True),
    ("8 each bay leaves", 8, "each", "bay leaves", True),
    ("½ pint garlic, sliced", 0.5, "pt", "garlic, sliced", True),
    ("4 pints cherry tomato", 4, "pt", "cherry tomato", True),
    ("2 quart Red onion, thin julienne", 2, "qt", "Red onion, thin julienne", True),
    ("1 bottle red wine", 1, "bottle", "red wine", True),
    ("1 can chipotle chiles in adobo", 1, "can", "chipotle chiles in adobo", True),
    ("1 jug. honey", 1, "jug", "honey", True),
    ("1 tube harissa paste", 1, "tube", "harissa paste", True),
    ("2 bag Mini peppers, sliced", 2, "bag", "Mini peppers, sliced", True),
    ("1 case Mixed squash, cut in ½ lengthways", 1, "case", "Mixed squash, cut in ½ lengthways", True),
    ("3 inch ginger", 3, "inch", "ginger", True),
    ("1 piece slab bacon, roasted and small diced", 1, "piece", "slab bacon, roasted and small diced", True),
    ("1 each (2 cups) mascarpone cheese", 1, "each", "(2 cups) mascarpone cheese", True),
    ("2 fl oz lime juice", 2, "fl oz", "lime juice", True),
    ("2 fl. oz. lime juice", 2, "fl oz", "lime juice", True),
    ("1 ea onion medium dice.", 1, "each", "onion medium dice.", True),
    ("2 ea onion", 2, "each", "onion", True),
    # no amount
    ("Salt", None, "no number", "Salt", None),
    ("AP flour", None, "no number", "AP flour", None),
    ("bundle of thyme and rosemary", None, "no number", "bundle of thyme and rosemary", None),
    ("pork or veg stock to cover", None, "no number", "pork or veg stock to cover", None),
    ("1/0 cup nonsense", None, "unreadable", "1/0 cup nonsense", None),
]

# within-kind conversions, exact: (amount, from, to, expected)
CONVERSIONS = [
    (1, "lb", "oz", 16), (1, "kg", "g", 1000), (1, "lb", "g", 453.59237),
    (1, "oz", "g", 28.349523125), (5, "#", "oz", 80),
    (1, "tbsp", "tsp", 3), (1, "cup", "tbsp", 16), (1, "cup", "fl oz", 8),
    (1, "pt", "cup", 2), (1, "qt", "pt", 2), (1, "gal", "qt", 4),
    (1, "1/2 gal", "qt", 2), (1, "gal", "1/2 gal", 2), (1, "L", "ml", 1000),
    (1, "fl oz", "ml", 29.5735295625), (1, "gal", "ml", 3785.411784),
    (1, "dozen", "each", 12), (24, "ea", "dozen", 2), (2, "bunch", "bunch", 2),
    (3, "C", "qt", 0.75),
    # across kinds, or between different count words: no conversion
    (1, "oz", "fl oz", None), (1, "oz", "cup", None), (1, "lb", "qt", None),
    (1, "bunch", "each", None), (1, "can", "bottle", None), (1, "each", "g", None),
    (1, "lb", "splodge", None),
]

# deliberate breaks: (name, exact text in recipe-math.js, replacement)
BREAKS = [
    ("oz read as volume", "'oz':      { kind: 'weight', factor: 28.349523125 }",
     "'oz':      { kind: 'volume', factor: 29.5735295625 }"),
    ("# not read as lb", "'pound': 'lb', '#': 'lb',", "'pound': 'lb',"),
    ("# after an amount not read as lb", "if (m[9]) {", "if (false) {"),
    ("1 1/2 read as 1", "amount = +m[1] + (+m[2]) / (+m[3]);", "amount = +m[1];"),
    ("1 1/2 read as 2", "amount = +m[1] + (+m[2]) / (+m[3]);", "amount = +m[2];"),
    ("1 1/2 read as 1/2", "'^(?:(\\\\d+)\\\\s+(\\\\d+)\\\\/(\\\\d+)|", "'^(?:(\\\\d+)\\\\s+(\\\\d+)\\\\/(\\\\d+)(?!)|"),
]

HTML = """<!doctype html><html><head><meta charset="utf-8">
<script src="recipe-math.js"></script></head><body>
<div id="harnessResults"></div>
<script>
(function(){
  var out = {fails: [], n: 0, scan: null};
  function fail(m){ out.fails.push(m); }
  function near(a, b){ return a === b || (a !== null && b !== null && Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(b))); }
  try {
    var R = RecipeMath;
    var SP = __SPELLINGS__, UN = __UNITS__, LN = __LINES__, CV = __CONV__, SCAN = __SCAN__;
    Object.keys(SP).forEach(function(s){
      out.n++;
      var u = R.normaliseUnit(s), k = R.unitKind(s);
      if (u !== SP[s][0] || k !== SP[s][1]) fail('spelling ' + JSON.stringify(s) + ' -> ' + u + '/' + k + ', want ' + SP[s][0] + '/' + SP[s][1]);
    });
    out.n++;
    var got = R.units().map(function(x){ return x.unit + ':' + x.kind; }).join(',');
    var want = UN.map(function(x){ return x[0] + ':' + x[1]; }).join(',');
    if (got !== want) fail('units() is ' + got + ', want ' + want);
    UN.forEach(function(x){ out.n++; if (R.normaliseUnit(x[0]) !== x[0]) fail('unit ' + x[0] + ' does not normalise to itself'); });
    LN.forEach(function(x){
      out.n++;
      var r = R.readAmount(x[0]);
      if (x[1] === null) {
        if (r.amount !== null || r.why !== x[2] || r.words !== x[3]) fail('line ' + JSON.stringify(x[0]) + ' -> ' + JSON.stringify(r) + ', want no amount (' + x[2] + ')');
      } else if (!near(r.amount, x[1]) || r.unit !== x[2] || r.words !== x[3] || r.unitWord !== x[4] || r.kind !== R.unitKind(x[2])) {
        fail('line ' + JSON.stringify(x[0]) + ' -> ' + JSON.stringify(r) + ', want ' + x[1] + ' ' + x[2] + ' / ' + JSON.stringify(x[3]));
      }
    });
    CV.forEach(function(x){
      out.n++;
      var r = R.convert(x[0], x[1], x[2]);
      if (!near(r, x[3])) fail('convert ' + x[0] + ' ' + x[1] + ' -> ' + x[2] + ' = ' + r + ', want ' + x[3]);
    });
    out.n++;
    if (!R.isPartHeader('— CHEESE BASE —') || R.isPartHeader('2 C Lentils') || R.isPartHeader('—')) fail('isPartHeader');
    if (SCAN) out.scan = SCAN.map(function(l){ var r = R.readAmount(l.text); r.recipe = l.recipe; r.text = l.text; return r; });
  } catch (e) { fail('threw: ' + e); }
  document.getElementById('harnessResults').textContent = JSON.stringify(out);
})();
</script></body></html>"""

RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run(chrome, js_src, scan=None):
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "recipe-math.js"), "w", encoding="utf-8").write(js_src)
        page = (HTML.replace("__SPELLINGS__", json.dumps(SPELLINGS))
                    .replace("__UNITS__", json.dumps(UNITS))
                    .replace("__LINES__", json.dumps(LINES))
                    .replace("__CONV__", json.dumps(CONVERSIONS))
                    .replace("__SCAN__", json.dumps(scan)))
        path = os.path.join(td, "t.html")
        open(path, "w", encoding="utf-8").write(page)
        dom = os.path.join(td, "dom.html")
        with open(dom, "w") as fo, open(os.devnull, "w") as fe:
            proc = subprocess.Popen(
                [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--no-first-run", "--disable-extensions",
                 "--disable-background-networking", "--disable-component-update",
                 "--disable-default-apps", "--disable-sync",
                 "--user-data-dir=" + os.path.join(td, "cd"),
                 "--virtual-time-budget=4000", "--dump-dom", "file://" + path],
                stdout=fo, stderr=fe)
            deadline, m = time.time() + 120, None
            try:
                while time.time() < deadline:
                    m = RESULT_RE.search(open(dom, encoding="utf-8", errors="replace").read())
                    if (m and m.group(1)) or proc.poll() is not None:
                        break
                    time.sleep(0.25)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
            m = RESULT_RE.search(open(dom, encoding="utf-8", errors="replace").read())
        if not m or not m.group(1):
            return None
        body = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"'))
        return json.loads(body)


def check_versions():
    """Every page that loads recipe-math.js loads the same ?v=."""
    seen = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        src = open(p, encoding="utf-8").read()
        refs = re.findall(r'src=["\']assets/recipe-math\.js(\?v=(\d+))?["\']', src)
        for full, v in refs:
            seen.setdefault(v or "(none)", []).append(os.path.basename(p))
    fails = []
    if "(none)" in seen:
        fails.append("loaded without ?v=: " + ", ".join(seen["(none)"]))
    if len(seen) > 1:
        fails.append("pages disagree on recipe-math.js ?v=: " + json.dumps(seen))
    return fails, seen


def scan(chrome, src, path):
    rows = json.load(open(path, encoding="utf-8"))
    lines = []
    for r in rows:
        if r.get("status") == "archived":
            continue
        for l in (r.get("ingredients") or "").splitlines():
            l = l.strip()
            if l and not re.match(r"^—.+—$", l):
                lines.append({"recipe": r["name"], "text": l})
    res = run(chrome, src, lines)
    if res is None:
        sys.exit("check_recipe_math: harness never reported")
    out = res["scan"]
    kinds = {}
    for r in out:
        kinds[r["kind"] or "no amount"] = kinds.get(r["kind"] or "no amount", 0) + 1
    print("%d lines in %d active recipes" % (len(out), sum(1 for r in rows if r.get("status") != "archived")))
    for k in ("volume", "count", "weight", "no amount"):
        print("  %-10s %d" % (k, kinds.get(k, 0)))
    units = {}
    for r in out:
        if r["unit"]:
            units[r["unit"]] = units.get(r["unit"], 0) + 1
    print("\nby unit: " + ", ".join("%s %d" % (u, n) for u, n in sorted(units.items(), key=lambda x: -x[1])))
    print("\nno amount:")
    for r in out:
        if r["amount"] is None and r.get("why") != "unreadable":
            print("  [%s] %s   (%s)" % (r["recipe"], r["text"], r["why"]))
    print("\nread as each because no unit word:")
    for r in out:
        if r["amount"] is not None and not r["unitWord"]:
            print("  [%s] %s" % (r["recipe"], r["text"]))
    bad = [r for r in out if r.get("why") == "unreadable"]
    print("\ncould not read: " + ("none" if not bad else ""))
    for r in bad:
        print("  [%s] %s" % (r["recipe"], r["text"]))
    return 0


def main():
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_recipe_math: no Chrome found. Set CHROME=/path/to/chrome.")
    src = open(MATH, encoding="utf-8").read()
    if len(sys.argv) == 3 and sys.argv[1] == "--scan":
        return scan(chrome, src, sys.argv[2])

    fails = []
    res = run(chrome, src)
    if res is None:
        print("recipe math guard: harness never reported")
        return 1
    fails += res["fails"]
    n = res["n"]

    for name, old, new in BREAKS:
        if old not in src:
            fails.append("break '%s': its target text is no longer in recipe-math.js - update BREAKS" % name)
            continue
        b = run(chrome, src.replace(old, new, 1))
        if b is None or not b["fails"]:
            fails.append("break '%s' was NOT caught" % name)

    vfails, seen = check_versions()
    fails += vfails

    if fails:
        print("recipe math guard: %d failure(s)\n" % len(fails))
        for x in fails:
            print("  " + x)
        print("\nsee docs/recipe-costing.md, 'Where the math lives'")
        return 1
    print("recipe math guard: clean (%d assertions, %d breaks caught, pages loading it: %s)"
          % (n, len(BREAKS), json.dumps(seen) if seen else "none yet"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
