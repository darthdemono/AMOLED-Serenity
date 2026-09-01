#!/usr/bin/env python3
"""Validate theme.css. Run from the repo root: python3 dev/validate_theme.py

Needs: pip install pyyaml tinycss2 fonttools brotli
Exits non-zero on any failure, so it works as a CI gate or a pre-commit hook.
"""
import re, sys, io, base64, yaml, tinycss2
from fontTools.ttLib import TTFont
css = open("theme.css").read(); fail = []

errs = [r for r in tinycss2.parse_stylesheet(css, skip_comments=False, skip_whitespace=True) if r.type=='error']
print("1. CSS parses:", "ok" if not errs else errs); fail += errs

m = re.search(r'/\*\s*@settings\s*\n(.*?)\n\*/', css, re.S)
doc = yaml.safe_load(m.group(1))
ctrls = [s for s in doc['settings'] if s.get('type') != 'heading']
print(f"2. YAML parses: ok — {len(doc['settings'])} entries, {len(ctrls)} controls")

declared = set(re.findall(r'^\s*(--[\w-]+)\s*:', css, re.M))
bad = [s['id'] for s in ctrls if s['type'] not in ('class-toggle','class-select') and '--'+s['id'] not in declared]
print("3. every control writes a declared var:", "ok" if not bad else bad); fail += bad

ct = [s['id'] for s in ctrls if s['type']=='class-toggle']
miss = [c for c in ct if f'.{c}' not in css]
print(f"4. class-toggles have selectors ({len(ct)}):", "ok" if not miss else miss); fail += miss

used = set(re.findall(r'var\((--[\w-]+)', css))
CORE = {"--font-smaller", "--callout-color", "--size-4-3", "--size-4-6",
        "--font-weight", "--bold-modifier", "--highlight-mix-blend-mode"}  # Obsidian-provided
undecl = sorted(used - declared - CORE)
print("5. no var() to undeclared:", "ok" if not undecl else undecl); fail += undecl

ids = [s['id'] for s in doc['settings']]
dupe = {i for i in ids if ids.count(i) > 1}
print("6. no duplicate setting ids:", "ok" if not dupe else dupe); fail += list(dupe)

req = {'variable-color':{'format','default'}, 'variable-select':{'default','options'},
       'variable-text':{'default'}, 'variable-number-slider':{'default','min','max','step'}}
sbad = [(s['id'],k) for s in ctrls for k in req.get(s['type'],set()) if k not in s]
print("7. controls have required keys:", "ok" if not sbad else sbad); fail += sbad

cbad=[s['id'] for s in ctrls if s['type']=='variable-color'
      and not re.match(r'^(#[0-9a-fA-F]{3,8}|rgba?\()', str(s['default']))]
print("8. colour defaults are literals:", "ok" if not cbad else cbad); fail += cbad

sel = [s for s in ctrls if s['type']=='variable-select']
obad = [s['id'] for s in sel if s['default'] not in s['options']]
print("9. select defaults are in options:", "ok" if not obad else obad); fail += obad

ct_on  = [s for s in ctrls if s['type']=='class-toggle' and s.get('default') is True]
ct_off = [s for s in ctrls if s['type']=='class-toggle' and s.get('default') is not True]
# A default-ON toggle only does something if a rule keys off its ABSENCE.
n_on = [s['id'] for s in ct_on if f":not(.{s['id']})" not in css]
# A default-OFF toggle only does something if a rule keys off its PRESENCE.
n_off = [s['id'] for s in ct_off if not re.search(r'\.'+re.escape(s['id'])+r'[.\s,:{]', css.replace(f":not(.{s['id']})",""))]
print(f"12. toggles wired ({len(ct_on)} on / {len(ct_off)} off):",
      "ok" if not (n_on or n_off) else {"default-on missing :not()": n_on, "default-off unused": n_off})
fail += n_on + n_off

fonts = re.findall(r'font-family:\s*"([^"]+)";.*?base64,([A-Za-z0-9+/=]+)\)', css, re.S)
gl = {f: TTFont(io.BytesIO(base64.b64decode(b)))['maxp'].numGlyphs for f,b in fonts}
ok = gl == {'Bricolage Grotesque':597,'Roboto':228,'Montserrat':243}
print("10. fonts intact:", "ok" if ok else gl); fail += [] if ok else ['fonts']

# every embedded family must be offered in a font dropdown
opts = {o for s in sel for o in s.get('options',[])}
nf = [f for f in gl if f not in opts]
print("11. embedded fonts are selectable:", "ok" if not nf else nf); fail += nf

print("\nRESULT:", "ALL CHECKS PASS" if not fail else f"{len(fail)} FAILURES")
sys.exit(1 if fail else 0)
