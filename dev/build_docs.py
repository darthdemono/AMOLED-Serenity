#!/usr/bin/env python3
"""Regenerate the settings reference in README.md from dev/theme_spec.py.

Rewrites everything between the SETTINGS markers, so the documented controls can
never drift from the ones the theme actually ships.

Usage:  python3 dev/build_docs.py     (run from the repo root)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme_spec import S

BEGIN, END = "<!-- BEGIN SETTINGS -->", "<!-- END SETTINGS -->"

out, rows, section, n = [], [], None, 0

def flush():
    if rows:
        out.append("| Setting | Control | Default | Variable | Notes |")
        out.append("|---|---|---|---|---|")
        out.extend(rows)
        out.append("")
        rows.clear()

for e in S:
    k = e[0]
    if k == "H":
        _, sid, title, level, desc = e
        flush(); section = title
        out.append(f"#### {title}")
        if desc:
            out.append(f"\n{desc}\n")
        continue
    if k in ("CT", "CTON"):
        _, sid, title, desc = e
        d = "on" if k == "CTON" else "off"
        rows.append(f"| {title} | toggle | `{d}` | *(class)* | {desc or ''} |"); n += 1
        continue
    if k == "CX":
        _, name, hexv, title, desc = e
        rows.append(f"| {title} | colour | `{hexv}` | `--{name}` + `--{name}-rgb` | {desc or ''} |"); n += 1
    elif k in ("C", "RGBA"):
        _, name, val, title, desc = e
        rows.append(f"| {title} | colour | `{val}` | `--{name}` | {desc or ''} |"); n += 1
    elif k == "T":
        _, name, val, title, desc = e
        rows.append(f"| {title} | text | `{val or '(empty)'}` | `--{name}` | {desc or ''} |"); n += 1
    elif k == "S":
        _, name, val, opts, title, desc = e
        rows.append(f"| {title} | dropdown | `{val}` | `--{name}` | {desc or ''} |"); n += 1
    elif k == "N":
        _, name, val, lo, hi, step, title, desc = e
        rows.append(f"| {title} | slider | `{val}` ({lo}–{hi}) | `--{name}` | {desc or ''} |"); n += 1
flush()

body = f"{BEGIN}\n\n{n} controls, grouped as they appear in the Style Settings panel.\n\n" + "\n".join(out) + f"\n{END}"
rd = open("README.md").read()
i, j = rd.index(BEGIN), rd.index(END) + len(END)
open("README.md", "w").write(rd[:i] + body + rd[j:])
print(f"README settings reference regenerated: {n} controls")
