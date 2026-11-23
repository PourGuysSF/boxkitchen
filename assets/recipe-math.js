/* assets/recipe-math.js — the site's one in-house shared script.
 *
 * Pure costing math for Recipe Costing (docs/recipe-costing.md, "Where the math
 * lives", M5). Loaded with ?v=N by every page that costs anything; every page
 * that loads it must load the same ?v=. Checked by scripts/check_recipe_math.py,
 * which runs before any PR that touches this file. Changed only through
 * docs/recipe-costing.md.
 *
 * Rules: pure functions only — no api(), no DOM, no table, no screen. Every
 * function is handed its data and returns values. Results are UNROUNDED;
 * rounding happens only on screen.
 *
 * Slice 2: the units and the amount reader. Slice 3: lineCost().
 * Slice 4: conversionChange(), and measureOf() exported.
 * Slice 5a: recipeCost() - the text matching, the guards, the total and the yield.
 */
var RecipeMath = (function () {
  'use strict';

  // ---- Units: exactly the plan's table ("Units"). ------------------------
  // factor = how many of the kind's base (ml, g, each) one unit holds.
  // Exact US customary definitions: 1 fl oz = 29.5735295625 ml, 1 lb = 453.59237 g.
  var FL_OZ = 29.5735295625;
  var UNIT_TABLE = {
    // weight, base g
    'g':       { kind: 'weight', factor: 1 },
    'kg':      { kind: 'weight', factor: 1000 },
    'oz':      { kind: 'weight', factor: 28.349523125 },   // oz is ALWAYS weight
    'lb':      { kind: 'weight', factor: 453.59237 },
    // volume, base ml
    'tsp':     { kind: 'volume', factor: FL_OZ / 6 },
    'tbsp':    { kind: 'volume', factor: FL_OZ / 2 },
    'fl oz':   { kind: 'volume', factor: FL_OZ },
    'cup':     { kind: 'volume', factor: FL_OZ * 8 },
    'pt':      { kind: 'volume', factor: FL_OZ * 16 },
    'qt':      { kind: 'volume', factor: FL_OZ * 32 },
    '1/2 gal': { kind: 'volume', factor: FL_OZ * 64 },
    'gal':     { kind: 'volume', factor: FL_OZ * 128 },
    'ml':      { kind: 'volume', factor: 1 },
    'L':       { kind: 'volume', factor: 1000 },
    // count: each and dozen convert to each other ...
    'each':    { kind: 'count', factor: 1 },
    'dozen':   { kind: 'count', factor: 12 },
    // ... every other count word is its own unit and converts only to itself.
    'bunch':   { kind: 'count', own: true },
    'clove':   { kind: 'count', own: true },
    'head':    { kind: 'count', own: true },
    'sprig':   { kind: 'count', own: true },
    'can':     { kind: 'count', own: true },
    'bottle':  { kind: 'count', own: true },
    'jug':     { kind: 'count', own: true },
    'tube':    { kind: 'count', own: true },
    'sheet':   { kind: 'count', own: true },
    'piece':   { kind: 'count', own: true },
    'bag':     { kind: 'count', own: true },
    'case':    { kind: 'count', own: true },
    'box':     { kind: 'count', own: true },
    'inch':    { kind: 'count', own: true }
  };

  // Spellings, keyed lower-case with dots removed. Plurals ending in s/es are
  // also tried by stripping, so only irregular or short forms are listed.
  var SPELLINGS = {
    'g': 'g', 'gram': 'g', 'gr': 'g',
    'kg': 'kg', 'kilo': 'kg', 'kilogram': 'kg',
    'oz': 'oz', 'ounce': 'oz',
    'lb': 'lb', 'lbs': 'lb', 'pound': 'lb', '#': 'lb',
    'tsp': 'tsp', 'teaspoon': 'tsp',
    'tbsp': 'tbsp', 'tb': 'tbsp', 'tbs': 'tbsp', 'tablespoon': 'tbsp',
    'fl oz': 'fl oz', 'floz': 'fl oz', 'fluid ounce': 'fl oz',
    'c': 'cup', 'cup': 'cup',
    'pt': 'pt', 'pint': 'pt',
    'qt': 'qt', 'quart': 'qt',
    '1/2 gal': '1/2 gal', '½ gal': '1/2 gal', 'half gal': '1/2 gal',
    'gal': 'gal', 'gallon': 'gal',
    'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml',
    'l': 'L', 'liter': 'L', 'litre': 'L',
    'ea': 'each', 'each': 'each',
    'dozen': 'dozen', 'doz': 'dozen', 'dz': 'dozen',
    'bunch': 'bunch', 'bu': 'bunch',
    'clove': 'clove', 'head': 'head', 'sprig': 'sprig', 'can': 'can',
    'bottle': 'bottle', 'jug': 'jug', 'tube': 'tube', 'sheet': 'sheet',
    'piece': 'piece', 'bag': 'bag', 'case': 'case', 'box': 'box',
    'inch': 'inch'
  };

  function key(s) {
    return String(s).toLowerCase().replace(/\./g, '').replace(/\s+/g, ' ').trim();
  }

  /** A spelling ("TB.", "cups", "Lb", "1/2 gal", "#") -> its unit, or null. */
  function normaliseUnit(s) {
    if (s === null || s === undefined) return null;
    var k = key(s);
    if (!k) return null;
    if (SPELLINGS.hasOwnProperty(k)) return SPELLINGS[k];
    if (/es$/.test(k) && SPELLINGS.hasOwnProperty(k.slice(0, -2))) return SPELLINGS[k.slice(0, -2)];
    if (/s$/.test(k) && SPELLINGS.hasOwnProperty(k.slice(0, -1))) return SPELLINGS[k.slice(0, -1)];
    return null;
  }

  /** 'weight' | 'volume' | 'count' for any spelling, or null. */
  function unitKind(s) {
    var u = normaliseUnit(s);
    return u ? UNIT_TABLE[u].kind : null;
  }

  /** Amount in one unit -> amount in another of the same kind, unrounded; null if they don't convert. */
  function convert(amount, from, to) {
    var a = normaliseUnit(from), b = normaliseUnit(to);
    if (!a || !b || typeof amount !== 'number' || !isFinite(amount)) return null;
    if (a === b) return amount;
    var A = UNIT_TABLE[a], B = UNIT_TABLE[b];
    if (A.kind !== B.kind || A.own || B.own) return null;
    return amount * A.factor / B.factor;
  }

  /** Every known unit with its kind, in table order — for a page's unit box. */
  function units() {
    var out = [];
    for (var u in UNIT_TABLE) if (UNIT_TABLE.hasOwnProperty(u)) out.push({ unit: u, kind: UNIT_TABLE[u].kind });
    return out;
  }

  // ---- The amount reader. ----------------------------------------------
  var VULGAR = { '½': 1/2, '⅓': 1/3, '⅔': 2/3, '¼': 1/4, '¾': 3/4, '⅕': 1/5, '⅖': 2/5,
                 '⅗': 3/5, '⅘': 4/5, '⅙': 1/6, '⅚': 5/6, '⅛': 1/8, '⅜': 3/8, '⅝': 5/8, '⅞': 7/8 };
  var VF = '[½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]';
  // 1 1/2 | 1/2 | 1½ | 1 ½ | ½ | 1.5 | 2   — then an optional # (5#, 1# butter)
  var AMOUNT_RE = new RegExp('^(?:(\\d+)\\s+(\\d+)\\/(\\d+)|(\\d+)\\/(\\d+)|(\\d+)?\\s?(' + VF + ')|(\\d+(?:\\.\\d+)?|\\.\\d+))(\\s*#)?(?=$|[\\s#]|[^\\w/.])');

  /** A part header line, e.g. "— CHEESE BASE —" (as recipe_dashboard.html's formatIngredients()). */
  function isPartHeader(line) {
    return /^—.+—$/.test(String(line || '').trim());
  }

  /**
   * One ingredient line -> what it says.
   *   { amount, unit, kind, words, unitWord }  — unitWord false when no unit word was
   *       written and 'each' was assumed ("2 bay leaves", "20 large guajillo chiles").
   *   { amount: null, unit: null, kind: null, words, why }  — no amount; why is
   *       'no number' (Salt TT, AP flour) or 'two amounts' ("1 Tbsp + 1 tsp ...",
   *       left for a person to enter, ruling (a), 2026-11-08) or 'unreadable'.
   * words is the rest of the line, for the picker filter (Slice 3).
   */
  function readAmount(line) {
    var text = String(line || '').trim();
    var none = function (why) { return { amount: null, unit: null, kind: null, words: text, why: why }; };
    var m = AMOUNT_RE.exec(text);
    if (!m) return none(/^[\d½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]/.test(text) ? 'unreadable' : 'no number');

    var amount;
    if (m[1] !== undefined) {
      if (+m[3] === 0) return none('unreadable');
      amount = +m[1] + (+m[2]) / (+m[3]);
    } else if (m[4] !== undefined) {
      if (+m[5] === 0) return none('unreadable');
      amount = (+m[4]) / (+m[5]);
    } else if (m[7] !== undefined) {
      amount = (m[6] !== undefined ? +m[6] : 0) + VULGAR[m[7]];
    } else {
      amount = parseFloat(m[8]);
    }

    var rest = text.slice(m[0].length).trim();
    var unit = null, unitWord = true;
    if (m[9]) {
      unit = 'lb';
    } else {
      // two-word units first ("fl oz", "fl. oz."), then one word
      var two = /^(\S+\s+\S+)(?:\s+|$)/.exec(rest);
      if (two && normaliseUnit(two[1]) === 'fl oz') {
        unit = 'fl oz'; rest = rest.slice(two[0].length);
      } else {
        var one = /^([^\s,()]+)(?:\s+|$|(?=[,(]))/.exec(rest);
        var u = one ? normaliseUnit(one[1]) : null;
        if (u && u !== '1/2 gal') { unit = u; rest = rest.slice(one[0].length); }
      }
    }
    rest = rest.trim();
    if (/^\+/.test(rest)) return none('two amounts');
    if (!unit) { unit = 'each'; unitWord = false; }
    return { amount: amount, unit: unit, kind: UNIT_TABLE[unit].kind, words: rest, unitWord: unitWord };
  }

  // ---- lineCost(): one line's cost, from values only (Slice 3). ------------
  // The Menu Builder math contract, part 2: looks nothing up, touches no table.
  //
  //   lineCost(qty, unit, price, conversion)
  //     qty, unit   the line's amount and unit (any spelling)
  //     price       { pack_qty, pack_unit, pack_price, guess }  — guess: true for a
  //                 guessed price (Menu Builder); null/absent = no price
  //     conversion  { from_kind, from_qty, from_unit, to_qty, to_unit, estimate }
  //                 — "from_qty from_unit = to_qty to_unit as bought", as the
  //                 ingredient_conversions / recipe_conversions rows; optional
  //
  //   -> { cost, reason, soft, was, now }
  //     cost    unrounded number, or null — never 0 for a line that is not costed
  //     reason  null | 'no amount' | 'no price yet' | 'needs a conversion'
  //             | 'conversion no longer matches'
  //     soft    the soft inputs actually used: 'guessed price', 'estimated conversion'
  //     was/now on 'conversion no longer matches': the conversion's unit and the
  //             price's pack unit ("was lb, now case")
  function measureOf(u) {          // the from_kind a line's unit needs a conversion for
    var n = normaliseUnit(u);
    if (!n) return null;
    var t = UNIT_TABLE[n];
    if (t.kind !== 'count') return t.kind;
    return t.own ? n : 'each';
  }
  function lineCost(qty, unit, price, conversion) {
    var out = { cost: null, reason: null, soft: [], was: null, now: null };
    if (typeof qty !== 'number' || !isFinite(qty) || qty <= 0 || !normaliseUnit(unit)) {
      out.reason = 'no amount'; return out;
    }
    if (!price || typeof price.pack_price !== 'number' || !isFinite(price.pack_price) || price.pack_price < 0 ||
        typeof price.pack_qty !== 'number' || !isFinite(price.pack_qty) || price.pack_qty <= 0 ||
        !normaliseUnit(price.pack_unit)) {
      out.reason = 'no price yet'; return out;
    }
    var inPack = convert(qty, unit, price.pack_unit);
    if (inPack === null) {
      var c = conversion;
      if (!c || c.from_kind !== measureOf(unit)) { out.reason = 'needs a conversion'; return out; }
      var inFrom = convert(qty, unit, c.from_unit);
      if (inFrom === null || !(c.from_qty > 0) || !(c.to_qty > 0)) { out.reason = 'needs a conversion'; return out; }
      var perPack = convert(1, c.to_unit, price.pack_unit);
      if (perPack === null) {
        out.reason = 'conversion no longer matches';
        out.was = normaliseUnit(c.to_unit) || String(c.to_unit);
        out.now = normaliseUnit(price.pack_unit);
        return out;
      }
      inPack = inFrom / c.from_qty * c.to_qty * perPack;
      if (c.estimate) out.soft.push('estimated conversion');
    }
    if (price.guess) out.soft.push('guessed price');
    out.cost = inPack / price.pack_qty * price.pack_price;
    return out;
  }

  // ---- conversionChange(): how far a new conversion moves from the old (Slice 4).
  //
  //   conversionChange(oldConv, newConv) -> ratio, or null
  //     both  { from_qty, from_unit, to_qty, to_unit } (any spelling), as the
  //           ingredient_conversions rows
  //     ratio new ÷ old, both read as "as-bought per from-side amount" in the
  //           NEW row's units, so 1 qt = 0.8 lb and 1 cup = 4 oz compare
  //           correctly (1.25). Unrounded. null when there is no old row, or
  //           the two cannot be compared (different measures, a bad amount).
  //   The page asks before saving when ratio >= 10 or <= 0.1.
  function perFrom(c, fromUnit, toUnit) {
    if (!c) return null;
    var f = convert(c.from_qty, c.from_unit, fromUnit);
    var t = convert(c.to_qty, c.to_unit, toUnit);
    if (f === null || t === null || !(f > 0) || !(t > 0)) return null;
    return t / f;
  }
  function conversionChange(oldConv, newConv) {
    if (!oldConv || !newConv) return null;
    var nu = perFrom(newConv, newConv.from_unit, newConv.to_unit);
    var ol = perFrom(oldConv, newConv.from_unit, newConv.to_unit);
    if (nu === null || ol === null) return null;
    return nu / ol;
  }

  // ---- recipeCost(): a whole recipe, from values only (Slice 5a). ----------
  // The Menu Builder math contract, part 3. Every page that costs a recipe
  // calls this, so the text matching and the guards live here, once.
  //
  //   recipeCost({ recipeId, text, links, prices, conversions, yield })
  //     recipeId     the recipe's id
  //     text         Recipes.ingredients, exactly as read
  //     links        recipe_lines rows (any recipes; only active rows with this
  //                  recipe_id count)
  //     prices       { <ingredient_cost_id>: {pack_qty, pack_unit, pack_price,
  //                  active, name, guess?} } - name = the name the caller shows
  //     conversions  ingredient_conversions rows
  //     yield        the recipe_yields row, or null
  //
  //   -> { lines, orphans, total, complete, costed, skipped, notCosted, reasons,
  //        soft, estimate, perYield, yieldUnit, portion }
  //     lines     in text order: {header:true, text} or {text, occurrence, part,
  //               read, link, kind, cost, soft, was, now, conv}
  //     kind      'not linked' | 'skip' | 'recipe inside' | 'price retired'
  //               | 'renamed' | 'costed' | lineCost()'s reasons
  //     total     unrounded sum of the costed lines (0 when none)
  //     complete  at least one ingredient line, and every one costed or skipped
  //     soft      [{input:'estimated conversion'|'guessed price'|'estimated yield', text, name}]
  //     perYield  unrounded cost of ONE yield unit, or null with no yield -
  //               returned even when incomplete; hiding it is the page's rule
  //     portion   null, or {qty, unit, cost, reason} - reason null | 'no yield'
  //               | 'needs a conversion'
  function normName(x) { return String(x == null ? '' : x).toLowerCase().replace(/\s+/g, ' ').trim(); }
  function num(v) { return v === null || v === undefined || v === '' ? null : Number(v); }
  function recipeLines(text) {
    var out = [], part = null, seen = {}, raw = String(text == null ? '' : text).split(/\r?\n/);
    for (var i = 0; i < raw.length; i++) {
      var t = raw[i].trim();
      if (!t) continue;
      if (isPartHeader(t)) { part = t; out.push({ header: true, text: t }); continue; }
      seen[t] = (seen[t] || 0) + 1;
      out.push({ header: false, text: t, occurrence: seen[t], part: part, read: readAmount(t) });
    }
    return out;
  }
  function convFor(conversions, costId, unit) {
    var kind = measureOf(unit);
    if (!kind || costId === null || costId === undefined) return null;
    for (var i = 0; i < (conversions || []).length; i++) {
      var c = conversions[i];
      if (Number(c.ingredient_cost_id) === Number(costId) && c.from_kind === kind) return c;
    }
    return null;
  }
  function amountUnit(q, u) {
    var qty = num(q), unit = normaliseUnit(u);
    return (qty !== null && isFinite(qty) && qty > 0 && unit) ? { qty: qty, unit: unit } : null;
  }
  function recipeCost(o) {
    o = o || {};
    var prices = o.prices || {}, rid = Number(o.recipeId);
    var mine = (o.links || []).filter(function (k) { return k.active !== false && Number(k.recipe_id) === rid; });
    var byKey = {};
    mine.forEach(function (k) { byKey[k.line_text + '\u0000' + Number(k.occurrence)] = k; });
    var out = { lines: [], orphans: [], total: 0, complete: false, costed: 0, skipped: 0, notCosted: 0,
                reasons: {}, soft: [], estimate: false, perYield: null, yieldUnit: null, portion: null };
    var cur = {};
    recipeLines(o.text).forEach(function (l) {
      if (l.header) { out.lines.push({ header: true, text: l.text }); return; }
      var key = l.text + '\u0000' + l.occurrence;
      cur[key] = true;
      var k = byKey[key] || null;
      var ln = { header: false, text: l.text, occurrence: l.occurrence, part: l.part, read: l.read, link: k,
                 kind: null, cost: null, soft: [], was: null, now: null, conv: null };
      var p = k && k.ingredient_cost_id !== null && k.ingredient_cost_id !== undefined ? prices[k.ingredient_cost_id] : null;
      if (!k) ln.kind = 'not linked';
      else if (k.skip) ln.kind = 'skip';
      else if (k.sub_recipe_id !== null && k.sub_recipe_id !== undefined) ln.kind = 'recipe inside';
      // the guards: a retired (or missing) price cannot cost anything; a name
      // changed since the link was made may be a different product (order-ID reuse)
      else if (!p || p.active === false) ln.kind = 'price retired';
      else if (normName(k.linked_name) !== normName(p.name)) { ln.kind = 'renamed'; ln.was = k.linked_name; ln.now = p.name; }
      else {
        var price = { pack_qty: num(p.pack_qty), pack_unit: p.pack_unit, pack_price: num(p.pack_price), guess: !!p.guess };
        var cv = convFor(o.conversions, k.ingredient_cost_id, k.unit), cvv = null;
        if (cv) cvv = { from_kind: cv.from_kind, from_qty: Number(cv.from_qty), from_unit: cv.from_unit,
                        to_qty: Number(cv.to_qty), to_unit: cv.to_unit, estimate: !!cv.estimate };
        var r = lineCost(num(k.qty), k.unit, price, cvv);
        ln.kind = r.reason || 'costed';
        ln.cost = r.cost; ln.soft = r.soft; ln.was = r.was; ln.now = r.now;
        // costed THROUGH the conversion only when the units don't meet on their own
        if (cv && convert(1, k.unit, p.pack_unit) === null) ln.conv = cv;
      }
      if (ln.kind === 'costed') {
        out.costed++;
        out.total += ln.cost;
        ln.soft.forEach(function (s) { out.soft.push({ input: s, text: ln.text, name: p.name }); });
      } else if (ln.kind === 'skip') {
        out.skipped++;
      } else {
        out.notCosted++;
        out.reasons[ln.kind] = (out.reasons[ln.kind] || 0) + 1;
      }
      out.lines.push(ln);
    });
    mine.forEach(function (k) { if (!cur[k.line_text + '\u0000' + Number(k.occurrence)]) out.orphans.push(k); });
    out.complete = (out.costed + out.skipped) > 0 && out.notCosted === 0;
    var y = o.yield || null, mk = y ? amountUnit(y.yield_qty, y.yield_unit) : null;
    if (mk) {
      out.yieldUnit = mk.unit;
      out.perYield = out.total / mk.qty;
      if (y.yield_estimate) out.soft.push({ input: 'estimated yield', text: null, name: null });
    }
    var pt = y ? amountUnit(y.portion_qty, y.portion_unit) : null;
    if (pt) {
      out.portion = { qty: pt.qty, unit: pt.unit, cost: null, reason: null };
      if (!mk) out.portion.reason = 'no yield';
      else {
        var inY = convert(pt.qty, pt.unit, mk.unit);
        if (inY === null) out.portion.reason = 'needs a conversion';
        else out.portion.cost = out.perYield * inY;
      }
    }
    out.estimate = out.soft.length > 0;
    return out;
  }

  return {
    recipeCost: recipeCost,
    lineCost: lineCost,
    conversionChange: conversionChange,
    measureOf: measureOf,
    normaliseUnit: normaliseUnit,
    unitKind: unitKind,
    convert: convert,
    units: units,
    isPartHeader: isPartHeader,
    readAmount: readAmount
  };
})();
