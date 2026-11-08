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
 * Slice 2: the units and the amount reader.
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

  return {
    normaliseUnit: normaliseUnit,
    unitKind: unitKind,
    convert: convert,
    units: units,
    isPartHeader: isPartHeader,
    readAmount: readAmount
  };
})();
