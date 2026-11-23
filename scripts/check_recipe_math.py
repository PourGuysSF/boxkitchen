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

# lineCost(qty, unit, price, conversion) -> (cost, reason, soft, was, now).
# Slice 3, the Menu Builder math contract. cost is compared UNROUNDED.
def P(q, u, pr, guess=False):
    d = {"pack_qty": q, "pack_unit": u, "pack_price": pr}
    if guess:
        d["guess"] = True
    return d


def CONV(kind, fq, fu, tq, tu, est=False):
    return {"from_kind": kind, "from_qty": fq, "from_unit": fu,
            "to_qty": tq, "to_unit": tu, "estimate": est}


LINE_COSTS = [
    # same kind: weight, volume, count, dozen, own count word, spellings
    ("weight", 2.5, "lb", P(5, "lb", 18.47), None, (9.235, None, [], None, None)),
    ("weight oz->lb", 8, "oz", P(36, "lb", 72), None, (1.0, None, [], None, None)),
    ("weight # vs Lb", 5, "#", P(50, "Lb", 30), None, (3.0, None, [], None, None)),
    ("volume", 4, "cup", P(1, "gal", 16.40), None, (4.10, None, [], None, None)),
    ("volume, unrounded", 1, "tsp", P(1, "gal", 16.40), None, (16.40 / 768, None, [], None, None)),
    ("volume 1/2 gal", 1, "qt", P(1, "1/2 gal", 6), None, (3.0, None, [], None, None)),
    ("count", 10, "each", P(115, "each", 45), None, (450 / 115, None, [], None, None)),
    ("dozen", 18, "ea", P(15, "dozen", 54), None, (5.4, None, [], None, None)),
    ("own count word", 1, "bunch", P(1, "bunch", 2.25), None, (2.25, None, [], None, None)),
    # cross kind, no conversion
    ("qt vs lb, none", 2, "qt", P(50, "lb", 30), None, (None, "needs a conversion", [], None, None)),
    ("bunch vs each, none", 1, "bunch", P(12, "each", 9), None, (None, "needs a conversion", [], None, None)),
    ("oz is weight", 32, "oz", P(1, "gal", 20), None, (None, "needs a conversion", [], None, None)),
    ("conversion for another measure", 2, "each", P(50, "lb", 30), CONV("volume", 1, "qt", 1.1, "lb"),
     (None, "needs a conversion", [], None, None)),
    # cross kind, with a conversion
    ("qt -> lb, estimated", 2, "qt", P(50, "lb", 30), CONV("volume", 1, "qt", 1.1, "lb", True),
     (1.32, None, ["estimated conversion"], None, None)),
    ("cup -> oz via qt = lb", 1, "cup", P(16, "oz", 5), CONV("volume", 1, "qt", 2, "lb"),
     (2.5, None, [], None, None)),
    ("jug -> lb", 1, "jug", P(5, "lb", 20), CONV("jug", 1, "jug", 5, "lb"), (20.0, None, [], None, None)),
    ("dozen -> lb via each", 1, "dozen", P(30, "lb", 60), CONV("each", 4, "each", 1, "lb"),
     (6.0, None, [], None, None)),
    # the pack unit changed kind since the conversion was made
    ("conversion no longer matches", 2, "qt", P(1, "case", 40), CONV("volume", 1, "qt", 1.1, "lb"),
     (None, "conversion no longer matches", [], "lb", "case")),
    # no price: never $0
    ("no price row", 2, "cup", None, None, (None, "no price yet", [], None, None)),
    ("price missing", 2, "cup", {"pack_qty": 1, "pack_unit": "gal", "pack_price": None}, None,
     (None, "no price yet", [], None, None)),
    ("pack qty missing", 2, "cup", {"pack_qty": None, "pack_unit": "gal", "pack_price": 5}, None,
     (None, "no price yet", [], None, None)),
    # soft inputs
    ("guessed price", 4, "cup", P(1, "gal", 10, True), None, (2.5, None, ["guessed price"], None, None)),
    ("guess + estimate", 2, "qt", P(50, "lb", 30, True), CONV("volume", 1, "qt", 1.1, "lb", True),
     (1.32, None, ["estimated conversion", "guessed price"], None, None)),
    # Slice 4: a cup line against a lb price, through 1 qt = 0.8 lb (0.5 qt -> 0.4 lb)
    ("cup -> lb via 1 qt = 0.8 lb", 2, "cup", P(50, "lb", 30), CONV("volume", 1, "qt", 0.8, "lb"),
     (0.24, None, [], None, None)),
    # no amount
    ("no amount", None, "cup", P(1, "gal", 10), None, (None, "no amount", [], None, None)),
    ("unknown unit", 2, "splodge", P(1, "gal", 10), None, (None, "no amount", [], None, None)),
]

# conversionChange(old, new) -> ratio new/old, unrounded, or None (Slice 4)
Q08 = CONV("volume", 1, "qt", 0.8, "lb")
CHANGES = [
    ("same conversion", Q08, Q08, 1),
    ("x10 exactly", Q08, CONV("volume", 1, "qt", 8, "lb"), 10),
    ("/10 exactly", Q08, CONV("volume", 1, "qt", 0.08, "lb"), 0.1),
    ("9.99x", Q08, CONV("volume", 1, "qt", 7.992, "lb"), 9.99),
    ("same thing, other spellings", Q08, CONV("volume", 1, "quart", 12.8, "oz"), 1),
    ("same thing, other amounts", Q08, CONV("volume", 4, "cups", 0.8, "#"), 1),
    ("1 cup = 4 oz vs 1 qt = 0.8 lb", Q08, CONV("volume", 1, "cup", 4, "oz"), 1.25),
    ("no old row", None, Q08, None),
    ("no new row", Q08, None, None),
    ("count word", CONV("jug", 1, "jug", 5, "lb"), CONV("jug", 1, "jug", 50, "lb"), 10),
    ("each vs dozen", CONV("each", 4, "each", 1, "lb"), CONV("each", 1, "dozen", 3, "lb"), 1),
    ("different measure", Q08, CONV("jug", 1, "jug", 5, "lb"), None),
    ("pack side changed kind", Q08, CONV("volume", 1, "qt", 1, "case"), None),
    ("old answer zero", CONV("volume", 1, "qt", 0, "lb"), Q08, None),
]
# measureOf(unit) -> the from_kind a line's unit needs (exported in Slice 4)
MEASURES = [("cup", "volume"), ("TB.", "volume"), ("oz", "weight"), ("#", "weight"),
            ("each", "each"), ("dozen", "each"), ("jug", "jug"), ("bunch", "bunch"),
            ("splodge", None)]


# ---- recipeCost() (Slice 5a) ------------------------------------------------
# Built from check_recipe_costing.py's own fixtures, so the parity cases are the
# very recipes the page's tests use. Expected values worked by hand.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_recipe_costing as RC  # noqa: E402  (constants only; its main() is guarded)

def PRICES(costs=None, orders=None):
    costs = RC.COSTS if costs is None else costs
    orders = {o["id"]: o for o in (RC.ORDERS if orders is None else orders)}
    out = {}
    for c in costs:
        o = orders.get(c.get("order_item_id"))
        out[str(c["id"])] = {"pack_qty": c["pack_qty"], "pack_unit": c["pack_unit"], "pack_price": c["pack_price"],
                             "active": c["active"], "name": o["name"] if o else c["name"]}
    return out

def TXT(rid, extra=()):
    for r in list(RC.RECIPES) + [RC.PORK, RC.PASTA] + list(extra):
        if r["id"] == rid:
            return r["ingredients"]

def Y(q=None, u=None, est=False, pq=None, pu=None):
    return {"yield_qty": q, "yield_unit": u, "yield_estimate": est, "portion_qty": pq, "portion_unit": pu}

H = "H"   # a part header in an expected line list
# expected line: (kind, cost or None[, was, now]) ; H for a header
RECIPE_COSTS = [
  # parity: the page's "links" scenario, Mac & Cheese, line for line
  ("parity: Mac & Cheese, every state", dict(recipeId=104, text=TXT(104), links=RC.LINKS, prices=PRICES(), conversions=[], yield_=None),
   dict(lines=[H, ("costed", 4.5), ("costed", 9.235), ("costed", 1.0), H, ("needs a conversion", None),
               ("no price yet", None), ("not linked", None), ("skip", None)],
        total=14.735, complete=False, costed=3, skipped=1, notCosted=3,
        reasons={"needs a conversion": 1, "no price yet": 1, "not linked": 1}, soft=[], perYield=None, portion=None, orphans=[])),
  # parity: the page's "guards" scenario - renamed, retired, a name that only differs by case/space, orphans
  ("parity: guards", dict(recipeId=104, text=TXT(104), links=RC.LINKS_GUARDS, prices=PRICES(), conversions=[], yield_=None),
   dict(lines=[H, ("not linked", None), ("renamed", None, "Heirloom tomato", "Velveeta"), ("costed", 1.0), H,
               ("not linked", None), ("not linked", None), ("price retired", None), ("not linked", None)],
        total=1.0, complete=False, costed=1, skipped=0, notCosted=6,
        reasons={"not linked": 4, "renamed": 1, "price retired": 1}, orphans=[1, 5])),
  # a repeated line: the SECOND "salt" is the linked one
  ("parity: Pork Belly, occurrence 2", dict(recipeId=105, text=TXT(105), links=RC.LINKS_GUARDS, prices=PRICES(), conversions=[], yield_=None),
   dict(lines=[("not linked", None), ("not linked", None), ("no price yet", None)], total=0, complete=False,
        costed=0, skipped=0, notCosted=3, orphans=[])),
  # parity: the page's conversion scenarios - an estimated conversion, two recipes
  ("parity: Mac & Cheese through 1 qt = 0.8 lb", dict(recipeId=104, text=TXT(104), links=RC.LINKS_CONV, prices=PRICES(), conversions=[RC.CONV_OLD], yield_=None),
   dict(lines=[H, ("not linked", None), ("not linked", None), ("costed", 1.0), H, ("costed", 2.4), ("not linked", None),
               ("not linked", None), ("not linked", None)], total=3.4, complete=False,
        soft=[{"input": "estimated conversion", "text": "2 qt. dried macaroni noodles", "name": "Macaroni noodles"}], estimate=True)),
  # complete, a same-kind portion (2 fl oz of a recipe made by the qt)
  ("complete: Pasta Salad, 1 qt, 2 fl oz portion", dict(recipeId=106, text=TXT(106), links=RC.LINKS_CONV, prices=PRICES(), conversions=[RC.CONV_OLD], yield_=Y(1, "qt", False, 2, "fl oz")),
   dict(lines=[("costed", 0.3), ("costed", 1.5), ("skip", None)], total=1.8, complete=True, costed=2, skipped=1, notCosted=0,
        reasons={}, orphans=[5], perYield=1.8, yieldUnit="qt", portion={"qty": 2, "unit": "fl oz", "cost": 0.1125, "reason": None},
        soft=[{"input": "estimated conversion", "text": "1 cup macaroni", "name": "Macaroni noodles"}], estimate=True)),
  # the same with no estimate at all (conversion not estimated)
  ("complete, no estimate", dict(recipeId=106, text=TXT(106), links=RC.LINKS_CONV, prices=PRICES(), conversions=[dict(RC.CONV_OLD, estimate=False)], yield_=Y("1", "quart")),
   dict(total=1.8, complete=True, soft=[], estimate=False, perYield=1.8, yieldUnit="qt", portion=None)),
  # an other-kind portion (by the ounce, made by the quart) -> needs a conversion; estimated yield
  ("other-kind portion, estimated yield", dict(recipeId=106, text=TXT(106), links=RC.LINKS_CONV, prices=PRICES(), conversions=[dict(RC.CONV_OLD, estimate=False)], yield_=Y(1, "qt", True, 4, "oz")),
   dict(total=1.8, complete=True, perYield=1.8, portion={"qty": 4, "unit": "oz", "cost": None, "reason": "needs a conversion"},
        soft=[{"input": "estimated yield", "text": None, "name": None}], estimate=True)),
  # a portion with no Makes; a half-set yield is no yield
  ("portion with no yield", dict(recipeId=106, text=TXT(106), links=RC.LINKS_CONV, prices=PRICES(), conversions=[RC.CONV_OLD], yield_=Y(None, None, False, 2, "fl oz")),
   dict(perYield=None, yieldUnit=None, portion={"qty": 2, "unit": "fl oz", "cost": None, "reason": "no yield"})),
  ("half-set yield", dict(recipeId=106, text=TXT(106), links=RC.LINKS_CONV, prices=PRICES(), conversions=[RC.CONV_OLD], yield_=Y(3, None)),
   dict(perYield=None, yieldUnit=None, portion=None)),
  # incomplete: perYield is still returned (hiding it is the page's rule)
  ("incomplete still returns perYield", dict(recipeId=104, text=TXT(104), links=RC.LINKS, prices=PRICES(), conversions=[], yield_=Y(2, "qt", False, 1, "cup")),
   dict(complete=False, total=14.735, perYield=7.3675, yieldUnit="qt", portion={"qty": 1, "unit": "cup", "cost": 1.841875, "reason": None})),
  # every unit kind: own count word, each, volume, weight; a count yield
  ("every unit kind, count yield", dict(recipeId=7, text="3 bunch cilantro\n12 limes\n1 gal stock\n8 oz. butter",
       links=[{"recipe_id": 7, "line_text": "3 bunch cilantro", "occurrence": 1, "qty": 3, "unit": "bunch", "ingredient_cost_id": 21, "linked_name": "Cilantro", "skip": False, "active": True},
              {"recipe_id": 7, "line_text": "12 limes", "occurrence": 1, "qty": 12, "unit": "each", "ingredient_cost_id": 22, "linked_name": "Limes", "skip": False, "active": True},
              {"recipe_id": 7, "line_text": "1 gal stock", "occurrence": 1, "qty": 1, "unit": "gal", "ingredient_cost_id": 23, "linked_name": "Stock", "skip": False, "active": True},
              {"recipe_id": 7, "line_text": "8 oz. butter", "occurrence": 1, "qty": 8, "unit": "oz", "ingredient_cost_id": 3, "linked_name": "Butter", "skip": False, "active": True},
              {"recipe_id": 7, "line_text": "8 oz. butter", "occurrence": 1, "qty": 9, "unit": "oz", "ingredient_cost_id": 3, "linked_name": "Butter", "skip": False, "active": False}],
       prices=dict(PRICES(), **{"21": {"pack_qty": 12, "pack_unit": "bunch", "pack_price": 18, "active": True, "name": "Cilantro"},
                                "22": {"pack_qty": 100, "pack_unit": "each", "pack_price": 25, "active": True, "name": "Limes"},
                                "23": {"pack_qty": 4, "pack_unit": "qt", "pack_price": 10, "active": True, "name": "Stock"}}),
       conversions=[], yield_=Y(12, "each", False, 1, "each")),
   dict(lines=[("costed", 4.5), ("costed", 3.0), ("costed", 10.0), ("costed", 1.0)], total=18.5, complete=True,
        perYield=18.5 / 12, yieldUnit="each", portion={"qty": 1, "unit": "each", "cost": 18.5 / 12, "reason": None}, orphans=[])),
  # no amount, conversion no longer matches, recipe inside
  ("no amount, no longer matches, recipe inside", dict(recipeId=8, text="salt\n2 qt noodles\nhouse stock",
       links=[{"recipe_id": 8, "line_text": "salt", "occurrence": 1, "qty": None, "unit": None, "ingredient_cost_id": 3, "linked_name": "Butter", "skip": False, "active": True},
              {"recipe_id": 8, "line_text": "2 qt noodles", "occurrence": 1, "qty": 2, "unit": "qt", "ingredient_cost_id": 4, "linked_name": "Macaroni noodles", "skip": False, "active": True},
              {"recipe_id": 8, "line_text": "house stock", "occurrence": 1, "qty": 1, "unit": "qt", "ingredient_cost_id": None, "sub_recipe_id": 104, "linked_name": None, "skip": False, "active": True}],
       prices=dict(PRICES(), **{"4": dict(PRICES()["4"], pack_qty=1, pack_unit="case")}), conversions=[RC.CONV_OLD], yield_=None),
   dict(lines=[("no amount", None), ("conversion no longer matches", None, "lb", "case"), ("recipe inside", None)],
        total=0, complete=False, notCosted=3, reasons={"no amount": 1, "conversion no longer matches": 1, "recipe inside": 1}, soft=[], estimate=False)),
  # no lines; every line skipped
  ("no ingredient lines", dict(recipeId=103, text=None, links=[], prices={}, conversions=[], yield_=Y(1, "qt")),
   dict(lines=[], total=0, complete=False, costed=0, skipped=0, notCosted=0, perYield=0)),
  ("all skipped", dict(recipeId=9, text="salt TT\npepper TT",
       links=[{"recipe_id": 9, "line_text": "salt TT", "occurrence": 1, "skip": True, "active": True},
              {"recipe_id": 9, "line_text": "pepper TT", "occurrence": 1, "skip": True, "active": True}], prices={}, conversions=[], yield_=None),
   dict(lines=[("skip", None), ("skip", None)], total=0, complete=True, costed=0, skipped=2, notCosted=0)),
]
for _n, _i, _w in RECIPE_COSTS:
    _i["yield"] = _i.pop("yield_")

# deliberate breaks: (name, exact text in recipe-math.js, replacement)
BREAKS = [
    ("oz read as volume", "'oz':      { kind: 'weight', factor: 28.349523125 }",
     "'oz':      { kind: 'volume', factor: 29.5735295625 }"),
    ("# not read as lb", "'pound': 'lb', '#': 'lb',", "'pound': 'lb',"),
    ("# after an amount not read as lb", "if (m[9]) {", "if (false) {"),
    ("1 1/2 read as 1", "amount = +m[1] + (+m[2]) / (+m[3]);", "amount = +m[1];"),
    ("1 1/2 read as 2", "amount = +m[1] + (+m[2]) / (+m[3]);", "amount = +m[2];"),
    ("1 1/2 read as 1/2", "'^(?:(\\\\d+)\\\\s+(\\\\d+)\\\\/(\\\\d+)|", "'^(?:(\\\\d+)\\\\s+(\\\\d+)\\\\/(\\\\d+)(?!)|"),
    ("$0 for an unpriced line", "out.reason = 'no price yet'; return out;",
     "out.reason = 'no price yet'; out.cost = 0; return out;"),
    ("a rounded result", "out.cost = inPack / price.pack_qty * price.pack_price;",
     "out.cost = Math.round(inPack / price.pack_qty * price.pack_price * 100) / 100;"),
    ("an estimate not reported", "if (c.estimate) out.soft.push('estimated conversion');", ""),
    ("a guess not reported", "if (price.guess) out.soft.push('guessed price');", ""),
    ("ratio on raw to_qty, ignoring units", "var t = convert(c.to_qty, c.to_unit, toUnit);", "var t = c.to_qty;"),
    ("a rounded ratio", "return nu / ol;", "return Math.round(nu / ol);"),
    ("an uncosted line summed as $0 and reported complete", "out.notCosted++;\n", "out.costed++;\n"),
    ("a rounded line summed", "out.total += ln.cost;", "out.total += Math.round(ln.cost * 100) / 100;"),
    ("an orphan treated as a current line", "if (!cur[k.line_text + '\\u0000' + Number(k.occurrence)]) out.orphans.push(k);", ""),
    ("an estimated conversion not carried to estimate", "ln.soft.forEach(function (s) { out.soft.push({ input: s, text: ln.text, name: p.name }); });", ""),
    ("a renamed line costed", "else if (normName(k.linked_name) !== normName(p.name)) { ln.kind = 'renamed'; ln.was = k.linked_name; ln.now = p.name; }", ""),
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
    var SP = __SPELLINGS__, UN = __UNITS__, LN = __LINES__, CV = __CONV__, LC = __LC__, SCAN = __SCAN__;
    var CH = __CHANGES__, MS = __MEASURES__, RCS = __RECIPES__;
    RCS.forEach(function(x){
      var r = R.recipeCost(x[1]), w = x[2], nm = 'recipeCost ' + x[0] + ': ';
      if (w.lines) {
        out.n++;
        if (r.lines.length !== w.lines.length) fail(nm + r.lines.length + ' lines, want ' + w.lines.length);
        w.lines.forEach(function(e, i){
          out.n++;
          var g = r.lines[i] || {};
          if (e === 'H') { if (!g.header) fail(nm + 'line ' + i + ' should be a header'); return; }
          if (g.kind !== e[0] || !near(g.cost, e[1])) fail(nm + 'line ' + i + ' ' + JSON.stringify(g.text) + ' = ' + g.kind + ' ' + g.cost + ', want ' + e[0] + ' ' + e[1]);
          if (e[1] === null && g.cost === 0) fail(nm + 'line ' + i + ' is $0 but not costed');
          if (e.length > 2 && (g.was !== e[2] || g.now !== e[3])) fail(nm + 'line ' + i + ' was/now ' + g.was + '/' + g.now + ', want ' + e[2] + '/' + e[3]);
        });
      }
      ['total','perYield'].forEach(function(k){ if (k in w) { out.n++; if (!near(r[k], w[k])) fail(nm + k + ' = ' + r[k] + ', want ' + w[k]); } });
      ['complete','costed','skipped','notCosted','yieldUnit','estimate'].forEach(function(k){ if (k in w) { out.n++; if (r[k] !== w[k]) fail(nm + k + ' = ' + r[k] + ', want ' + w[k]); } });
      ['reasons','soft'].forEach(function(k){ if (k in w) { out.n++; if (JSON.stringify(r[k]) !== JSON.stringify(w[k])) fail(nm + k + ' = ' + JSON.stringify(r[k]) + ', want ' + JSON.stringify(w[k])); } });
      if ('orphans' in w) { out.n++; var ids = r.orphans.map(function(k){ return k.id; }); if (JSON.stringify(ids) !== JSON.stringify(w.orphans)) fail(nm + 'orphans ' + JSON.stringify(ids) + ', want ' + JSON.stringify(w.orphans)); }
      if ('portion' in w) {
        out.n++;
        var a = r.portion, b = w.portion;
        if ((a === null) !== (b === null) || (b && (a.qty !== b.qty || a.unit !== b.unit || !near(a.cost, b.cost) || a.reason !== b.reason)))
          fail(nm + 'portion ' + JSON.stringify(a) + ', want ' + JSON.stringify(b));
      }
      out.n++;
      if (r.estimate !== (r.soft.length > 0)) fail(nm + 'estimate does not match soft');
    });
    CH.forEach(function(x){
      out.n++;
      var r = R.conversionChange(x[1], x[2]);
      if (!near(r, x[3])) fail('conversionChange ' + x[0] + ' = ' + r + ', want ' + x[3]);
    });
    MS.forEach(function(x){
      out.n++;
      if (R.measureOf(x[0]) !== x[1]) fail('measureOf ' + x[0] + ' = ' + R.measureOf(x[0]) + ', want ' + x[1]);
    });
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
    LC.forEach(function(x){
      out.n++;
      var r = R.lineCost(x[1], x[2], x[3], x[4]), w = x[5];
      if (!near(r.cost, w[0]) || r.reason !== w[1] || JSON.stringify(r.soft) !== JSON.stringify(w[2]) || r.was !== w[3] || r.now !== w[4])
        fail('lineCost ' + x[0] + ' -> ' + JSON.stringify(r) + ', want ' + JSON.stringify(w));
      if (w[0] === null && r.cost === 0) fail('lineCost ' + x[0] + ' returned $0 for a line that is not costed');
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
    # The temp folder is removed by hand, ignoring errors: Chrome's helper
    # processes can outlive the one we waited for and still be writing its
    # profile, and TemporaryDirectory's cleanup then crashed with "Directory
    # not empty: 'Default'" after every assertion had passed (PR #187 CI).
    # check_styling.py hit and fixed the same race. (ignore_cleanup_errors
    # needs Python 3.10; macOS ships 3.9.)
    td = tempfile.mkdtemp()
    try:
        return _run_in(td, chrome, js_src, scan)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _run_in(td, chrome, js_src, scan):
    open(os.path.join(td, "recipe-math.js"), "w", encoding="utf-8").write(js_src)
    page = (HTML.replace("__SPELLINGS__", json.dumps(SPELLINGS))
                .replace("__UNITS__", json.dumps(UNITS))
                .replace("__LINES__", json.dumps(LINES))
                .replace("__CONV__", json.dumps(CONVERSIONS))
                .replace("__LC__", json.dumps(LINE_COSTS))
                .replace("__CHANGES__", json.dumps(CHANGES))
                .replace("__MEASURES__", json.dumps(MEASURES))
                .replace("__RECIPES__", json.dumps(RECIPE_COSTS))
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
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
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
