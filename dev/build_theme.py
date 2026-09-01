#!/usr/bin/env python3
"""Regenerate theme.css from dev/theme_spec.py.

theme.css is GENERATED. Edit dev/theme_spec.py and re-run this, do not hand-edit
the .theme-dark block or the @settings block. Generating both from one table is
what guarantees that every Style Settings control writes a variable something
actually reads -- the class of bug that shipped silently in 1.1.0.

The embedded font blobs are read back out of the existing theme.css, so no font
files are needed and the payload is never re-encoded.

Usage:  python3 dev/build_theme.py     (run from the repo root)
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme_spec import S, FONTS, MONO

CSS = "theme.css"
blobs = dict(re.findall(
    r'font-family:\s*"([^"]+)";.*?base64,([A-Za-z0-9+/=]+)\)',
    open(CSS).read(), re.S))
assert set(blobs) == {"Bricolage Grotesque", "Roboto", "Montserrat"}, sorted(blobs)

decls, settings, docs = [], [], []
cur_section = None

def y(s):
    return "'" + str(s).replace("'", "''") + "'"

decls, settings, docs = [], [], []
cur_section = None

cur_section = None

def y(s):  # quote for YAML
    return "'" + str(s).replace("'", "''") + "'"

for e in S:
    k = e[0]
    if k == "H":
        _, sid, title, level, desc = e
        cur_section = title
        settings.append(("heading", sid, title, level, desc))
        docs.append(("H", title, desc))
        continue
    if k in ("CT", "CTON"):
        _, sid, title, desc = e
        settings.append(("class-toggle", sid, title, desc, k == "CTON"))
        docs.append(("R", cur_section, title, "toggle", "on" if k == "CTON" else "off", desc, sid))
        continue
    name = e[1]
    if k == "CX":
        _, name, hexv, title, desc = e
        rgb = ", ".join(str(int(hexv.lstrip("#")[i:i+2], 16)) for i in (0, 2, 4))
        decls.append((name, hexv))
        decls.append((name + "-rgb", rgb))
        settings.append(("CX", name, title, hexv, desc))
        docs.append(("R", cur_section, title, "colour", hexv, desc, name))
    elif k in ("C", "RGBA"):
        _, name, val, title, desc = e
        decls.append((name, val))
        settings.append(((k), name, title, val, desc))
        docs.append(("R", cur_section, title, "color", val, desc, name))
    elif k == "T":
        _, name, val, title, desc = e
        decls.append((name, val if val != "" else "initial"))
        settings.append(("T", name, title, val, desc))
        docs.append(("R", cur_section, title, "text", val if val != "" else "(empty)", desc, name))
    elif k == "S":
        _, name, val, opts, title, desc = e
        decls.append((name, val))
        settings.append(("S", name, title, val, opts, desc))
        docs.append(("R", cur_section, title, "dropdown", val, desc, name))
    elif k == "N":
        _, name, val, lo, hi, step, title, desc = e
        decls.append((name, str(val)))
        settings.append(("N", name, title, val, lo, hi, step, desc))
        docs.append(("R", cur_section, title, "slider", f"{val} ({lo}–{hi})", desc, name))

dmap = dict(decls)
# Backgrounds are declared ahead of the exposed settings (see assemble.py PRE)
# and must be resolvable here so color defaults come out as literals.
dmap.update({
    "background-primary": "var(--color-base-00)",
    "background-primary-alt": "var(--color-base-00)",
    "background-secondary": "var(--color-base-00)",
    "background-secondary-alt": "var(--color-base-00)",
    "titlebar-background": "var(--color-base-00)",
    "titlebar-background-focused": "var(--color-base-10)",
})

# ---- prove declared default == resolved CSS value for every color control ----
def resolve(v, depth=0):
    if depth > 12: return v
    m = re.fullmatch(r'var\((--[\w-]+)\)', v.strip())
    if m:
        tgt = m.group(1)[2:]
        return resolve(dmap[tgt], depth+1) if tgt in dmap else v
    return v.strip()

# ---- emit @settings YAML ----
out = []
out.append("/* @settings\n")
out.append("name: AMOLED Serenity")
out.append("id: amoled-serenity-style")
out.append("settings:")
for s in settings:
    t = s[0]
    out.append("    -")
    if t == "heading":
        _, sid, title, level, desc = s
        out.append(f"        id: {sid}")
        out.append(f"        title: {y(title)}")
        out.append("        type: heading")
        out.append(f"        level: {level}")
        out.append("        collapsed: true")
        if desc: out.append(f"        description: {y(desc)}")
        continue
    sid, title = s[1], s[2]
    out.append(f"        id: {sid}")
    out.append(f"        title: {y(title)}")
    if t == "class-toggle":
        out.append("        type: class-toggle")
        out.append(f"        default: {'true' if s[4] else 'false'}")
    elif t == "CX":
        out.append("        type: variable-color")
        out.append("        format: hex")
        out.append("        opacity: false")
        out.append(f"        default: {y(s[3])}")
        out.append("        alt-format:")
        out.append("            -")
        out.append(f"                id: {s[1]}-rgb")
        out.append("                format: rgb-values")
    elif t == "C":
        out.append("        type: variable-color")
        out.append("        format: hex")
        out.append("        opacity: false")
        out.append(f"        default: {y(resolve(s[3]))}")
    elif t == "RGBA":
        out.append("        type: variable-color")
        out.append("        format: rgb")
        out.append("        opacity: true")
        out.append(f"        default: {y(resolve(s[3]))}")
    elif t == "T":
        out.append("        type: variable-text")
        out.append(f"        default: {y(s[3])}")
    elif t == "S":
        out.append("        type: variable-select")
        out.append(f"        default: {y(s[3])}")
        out.append("        options:")
        for o in s[4]:
            out.append(f"            - {y(o)}")
    elif t == "N":
        _, sid, title, val, lo, hi, step, desc = s
        out.append("        type: variable-number-slider")
        out.append(f"        default: {val}")
        out.append(f"        min: {lo}")
        out.append(f"        max: {hi}")
        out.append(f"        step: {step}")
    d = s[-1]
    if d: out.append(f"        description: {y(d)}")
out.append("*/")
yaml_block = "\n".join(out)

print("settings controls:", sum(1 for s in settings if s[0] != "heading"))
print("declarations:", len(decls))

# verify color defaults resolve to literals
bad = [(s[1], s[3], resolve(s[3])) for s in settings
       if s[0] in ("C","RGBA") and not re.match(r'^(#|rgba?\()', resolve(s[3]))]
print("unresolved color defaults:", bad or "none")


# Declared before the exposed settings so they can be referenced by them.
PRE = [
 ("background-primary", "var(--color-base-00)", "Main background"),
 ("background-primary-alt", "var(--color-base-00)", "Active line, alternate panes"),
 ("background-secondary", "var(--color-base-00)", "Sidebars"),
 ("background-secondary-alt", "var(--color-base-00)", "Sidebar bottom, vault switcher"),
 ("titlebar-background", "var(--color-base-00)", "Titlebar"),
 ("titlebar-background-focused", "var(--color-base-10)", "Focused titlebar"),
]
# Aliases onto the names Obsidian actually paints with. Not user-facing.
POST = [
 ("text-normal", "var(--text-primary)", None),
 ("text-muted", "var(--text-secondary)", None),
 ("text-faint", "var(--text-tertiary)", None),
 ("text-on-accent", "var(--color-base-00)", None),
 ("text-selection", "var(--selection-background)", None),
 ("text-accent", "var(--primary-accent)", None),
 ("text-accent-hover", "var(--secondary-accent)", None),
 ("link-color", "var(--primary-accent)", None),
 ("link-color-hover", "var(--secondary-accent)", None),
 ("link-external-color", "var(--primary-accent)", None),
 ("link-external-color-hover", "var(--secondary-accent)", None),
 ("interactive-accent", "var(--primary-accent)", None),
 ("interactive-accent-hover", "var(--secondary-accent)", None),
 ("interactive-normal", "var(--button-background)", None),
 ("interactive-hover", "var(--color-base-25)", None),
 ("background-modifier-border", "var(--color-base-20)", None),
 ("background-modifier-border-hover", "var(--color-base-30)", None),
 ("background-modifier-border-focus", "var(--focus-border)", None),
 ("background-modifier-hover", "var(--color-base-20)", None),
 ("status-bar-text-color", "var(--status-bar-foreground)", None),
 # Obsidian derives callout colours, canvas node colours and much else from its
 # own eight-colour palette. Overriding the palette rather than the ~14
 # --callout-* variables means those all follow automatically, and it works on
 # every Obsidian version: old builds read the -rgb triplets, current builds
 # read the hex. Both are written from one picker via alt-format.
 ("color-red", "var(--red)", None),
 ("color-red-rgb", "var(--red-rgb)", None),
 ("color-orange", "var(--orange)", None),
 ("color-orange-rgb", "var(--orange-rgb)", None),
 ("color-yellow", "var(--yellow)", None),
 ("color-yellow-rgb", "var(--yellow-rgb)", None),
 ("color-green", "var(--green)", None),
 ("color-green-rgb", "var(--green-rgb)", None),
 ("color-cyan", "var(--frost0)", None),
 ("color-cyan-rgb", "var(--frost0-rgb)", None),
 ("color-blue", "var(--frost2)", None),
 ("color-blue-rgb", "var(--frost2-rgb)", None),
 ("color-purple", "var(--purple)", None),
 ("color-purple-rgb", "var(--purple-rgb)", None),
 ("color-pink", "var(--purple)", None),
 ("color-pink-rgb", "var(--purple-rgb)", None),
 ("callout-quote", "var(--color-base-60)", None),
 ("collapse-icon-color", "var(--icon-color)", None),
 ("nav-collapse-icon-color", "var(--icon-color)", None),
 ("tab-text-color-focused", "var(--tab-text-color-active)", None),
 ("tab-text-color-focused-active", "var(--tab-text-color-active)", None),
 ("tab-text-color-focused-active-current", "var(--tab-text-color-active)", None),
 ("code-size", "var(--font-smaller)", None),
 ("bold-weight", "700", None),
 ("blockquote-font-style", "normal", None),
 # Custom font fields win when the user fills them in; otherwise the dropdown does.
 ("h1-font", "var(--header-font-custom, var(--header-font))", None),
 ("h2-font", "var(--header-font-custom, var(--header-font))", None),
 ("h3-font", "var(--header-font-custom, var(--header-font))", None),
 ("h4-font", "var(--header-font-custom, var(--header-font))", None),
 ("h5-font", "var(--header-font-custom, var(--header-font))", None),
 ("h6-font", "var(--header-font-custom, var(--header-font))", None),
 ("inline-title-font", "var(--header-font-custom, var(--header-font))", None),
 ("font-text-theme", "var(--body-font-custom, var(--body-font))", None),
 ("file-header-font", "var(--body-font-custom, var(--body-font))", None),
 ("font-monospace-theme", "var(--monospace-font-custom, var(--monospace-font))", None),
]

lines = []
lines.append(""".theme-dark {
    /* ─── Backgrounds ─────────────────────────────── */""")
for n, v, c in PRE:
    lines.append(f"    --{n}: {v};")
    if c: lines.append(f"    /* {c} */")
lines.append("")
lines.append("    /* ─── User-configurable (see @settings above) ── */")
for n, v in decls:
    lines.append(f"    --{n}: {v};")
lines.append("")
lines.append("""    /* ─── Obsidian core variable mapping ──────────── */
    /* The names above are this theme's own vocabulary and Obsidian  */
    /* does not read most of them. These aliases are what actually   */
    /* paint the app, which is what makes the settings above take    */
    /* effect. Edit the names above, not these.                      */""")
for n, v, c in POST:
    lines.append(f"    --{n}: {v};")
lines.append("}")
theme_block = "\n".join(lines)

RULES = r'''
/* Style Settings applies its class to <body>, the same element that carries   */
/* .theme-dark, so these must be compound selectors and not descendant ones.   */
/* Overriding the base color makes every derived surface follow, rather than  */
/* only the window background.                                                 */
body.pure-amoled-background.theme-dark {
    --color-base-00: #000000;
}

html {
    background-color: var(--background-primary);
}

body {
    background-color: var(--background-primary) !important;
    /* Body background color */
    color: var(--text-primary);
    /* Body text color */
    line-height: 1.6;
    /* Improved line height for readability */
    margin: 0;
    /* Remove default margin */
}

/* ─────────────────────────────────────────────────── */
/* Custom background image (opt-in)                    */
/* The image sits on a fixed layer behind everything;  */
/* the app chrome is made transparent so it shows      */
/* through. Off by default, so the default theme stays */
/* a flat black with no extra compositing cost.        */
/* ─────────────────────────────────────────────────── */
body.custom-background.theme-dark {
    background-color: transparent !important;
}

body.custom-background.theme-dark::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    background-image: var(--custom-bg-image);
    background-size: var(--custom-bg-size);
    background-position: var(--custom-bg-position);
    background-repeat: no-repeat;
    opacity: var(--custom-bg-opacity);
    filter: blur(calc(var(--custom-bg-blur) * 1px));
}

body.custom-background.theme-dark .app-container,
body.custom-background.theme-dark .horizontal-main-container,
body.custom-background.theme-dark .workspace,
body.custom-background.theme-dark .workspace-split,
body.custom-background.theme-dark .workspace-tabs,
body.custom-background.theme-dark .workspace-leaf,
body.custom-background.theme-dark .workspace-leaf-content,
body.custom-background.theme-dark .workspace-tab-header-container,
body.custom-background.theme-dark .markdown-source-view,
body.custom-background.theme-dark .markdown-preview-view,
body.custom-background.theme-dark .cm-editor,
body.custom-background.theme-dark .cm-scroller,
body.custom-background.theme-dark .nav-files-container {
    background-color: transparent !important;
}

/* ─────────────────────────────────────────────────── */
/* Callouts                                            */
/* Type colours are NOT set here. Obsidian derives them */
/* from its own palette, which the core mapping block   */
/* overrides, so all fourteen callout types follow the  */
/* accent colours on every Obsidian version.            */
/*                                                      */
/* Only the background tint is overridden, because      */
/* Obsidian hardcodes it at 10% and a lit background is */
/* what an AMOLED theme is trying to avoid. Guarded, so */
/* builds without color-mix() keep the stock behaviour. */
/* ─────────────────────────────────────────────────── */
@supports (background-color: color-mix(in oklch, red 10%, transparent)) {
    .callout {
        background-color: color-mix(in oklch, var(--callout-color) calc(var(--callout-bg-opacity) * 100%), transparent);
    }
}

.callout-title {
    font-weight: var(--callout-title-weight);
}

/* ─────────────────────────────────────────────────── */
/* Feature toggles                                     */
/*                                                     */
/* These use body:not(.x) rather than scoping the      */
/* variables to body.x, so that switching a feature    */
/* off also overrides whatever the user set for it in  */
/* Style Settings. Style Settings writes to            */
/* body.css-settings-manager, specificity (0,1,1); the */
/* selectors below are (0,2,1), so off means off.      */
/*                                                     */
/* The values restore Obsidian's own defaults, taken   */
/* from its stylesheet rather than guessed.            */
/* ─────────────────────────────────────────────────── */

body:not(.style-tables).theme-dark {
    --table-background: rgba(0, 0, 0, 0);
    --table-row-background-hover: rgba(0, 0, 0, 0);
    --table-column-alt-background: rgba(0, 0, 0, 0);
    --table-selection: rgba(0, 0, 0, 0);
    --table-header-color: var(--text-normal);
    --table-text-color: var(--text-normal);
    --table-header-border-color: var(--background-modifier-border);
}

body:not(.style-tables).theme-dark,
body:not(.table-header-styling).theme-dark {
    --table-header-background: rgba(0, 0, 0, 0);
    --table-header-background-hover: rgba(0, 0, 0, 0);
}

body:not(.style-tables).theme-dark,
body:not(.table-zebra-striping).theme-dark {
    --table-row-alt-background: rgba(0, 0, 0, 0);
    --table-row-alt-background-hover: var(--table-row-background-hover);
}

/* Column striping is opt-in, and only inside styled tables. */
body.style-tables.table-column-striping.theme-dark {
    --table-column-alt-background: var(--table-column-alt-color);
}

body:not(.style-callouts).theme-dark {
    --callout-bg-opacity: 0.1;
    --callout-padding: var(--size-4-3) var(--size-4-3) var(--size-4-3) var(--size-4-6);
    --callout-radius: var(--radius-s);
    --callout-border-width: 0px;
    --callout-title-weight: calc(var(--font-weight) + var(--bold-modifier));
    --callout-blend-mode: var(--highlight-mix-blend-mode);
}

body:not(.style-canvas).theme-dark {
    --canvas-background: var(--background-primary);
    --canvas-dot-pattern: var(--color-base-30);
    --canvas-card-label-color: var(--text-faint);
    --canvas-controls-radius: var(--radius-s);
}

body:not(.style-graph).theme-dark {
    --graph-line: var(--color-base-35);
    --graph-node: var(--text-muted);
    --graph-node-focused: var(--text-accent);
    --graph-node-tag: var(--color-green);
    --graph-node-attachment: var(--color-yellow);
    --graph-node-unresolved: var(--text-faint);
    --graph-text: var(--text-normal);
}

/* ─────────────────────────────────────────────────── */
/* Tables                                              */
/* Obsidian paints the alternating-column background   */
/* on <th> as well as <td>, and that rule outranks the */
/* header background because :nth-child adds a class-  */
/* level specificity step. With column striping off    */
/* (the default) every second header cell would lose   */
/* its tint. Reassert it at equal specificity: this     */
/* rule is later in the cascade, so it wins.            */
/* ─────────────────────────────────────────────────── */
.markdown-rendered thead tr > th:nth-child(n),
.cm-html-embed thead tr > th:nth-child(n) {
    background-color: var(--table-header-background);
}

/* The rule above outranks Obsidian's own `thead tr:hover`, so the hover state */
/* has to be restated at higher specificity or the header stops responding.    */
.markdown-rendered thead tr:hover > th:nth-child(n),
.cm-html-embed thead tr:hover > th:nth-child(n) {
    background-color: var(--table-header-background-hover);
}

/* Enhanced Typography */
h1,
h2,
h3,
h4,
h5,
h6 {
    font-weight: bold;
    /* Bold headings */
    margin-top: 24px;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
    font-optical-sizing: auto;
    /* Bricolage Grotesque carries an `opsz` axis; let it track font-size */
}

p {
    margin: 10px 0;
    line-height: 1.8;
    /* Spacing for paragraphs */
}

/* Button Styles */
.side-dock-ribbon-action {
    background-color: var(--button-background);
    /* Button background */
    color: var(--button-text);
    /* Button text color */
    border: none;
    /* Remove default border */
    border-radius: var(--radius-s);
    /* Rounded corners for buttons */
    padding: 5px 5px;
    /* Button padding */
    cursor: pointer;
    /* Change cursor to pointer */
    transition: background-color 0.3s;
    /* Smooth transition */
}

.side-dock-ribbon-action:hover {
    background-color: var(--color-base-25);
}

/* Status Bar */
.status-bar {
    background-color: var(--status-bar-background);
    /* Status bar background */
    color: var(--status-bar-foreground);
    /* Status bar text color */
    padding: 5px;
    /* Padding for the status bar */
    border-radius: 5px;
    /* Rounded corners */
}
'''

HEADER = """/* ═══════════════════════════════════════════════════════════════════════════
   AMOLED Serenity — an Obsidian theme for AMOLED displays
   https://github.com/darthdemono/AMOLED-Serenity

   Theme:  MIT License · darthdemono · https://darthdemono.com
   Fonts:  the three faces embedded at the bottom of this file are NOT MIT.
           Bricolage Grotesque and Montserrat are SIL OFL 1.1; Roboto is
           Apache 2.0. See THIRD-PARTY.md and LICENSES/ before redistributing.
   ═══════════════════════════════════════════════════════════════════════════ */

/* ─────────────────────────────────────────────────── */
/* Style Settings for AMOLED Serenity                  */
/* Requires the "Style Settings" community plugin.     */
/*                                                     */
/* INVARIANT: every non-heading `id` below must match  */
/* a custom property declared in `.theme-dark`, and    */
/* every `class-toggle` id must match a selector in    */
/* this file. Break that and the control silently      */
/* writes a variable nothing reads.                    */
/* ─────────────────────────────────────────────────── */

"""


LATIN1 = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
          "U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")
FACES = f'''
/* ─────────────────────────────────────────────────── */
/* Embedded fonts                                      */
/* Opt-in via Style Settings -> Typography. Inter is   */
/* the default and ships with Obsidian, so none of     */
/* these load unless the user selects them.            */
/* Licences: see THIRD-PARTY.md.                       */
/* ─────────────────────────────────────────────────── */

/* Variable font: weight 200-800, width 75-100%, optical size 12-96.       */
/* The weight and stretch ranges MUST be declared, or the browser pins the */
/* face to its default instance (ExtraBold 800) and every glyph renders    */
/* extra-bold. Covers Latin-1 plus most of Latin Extended-A.               */
@font-face {{
    font-family: "Bricolage Grotesque";
    font-style: normal;
    font-weight: 200 800;
    font-stretch: 75% 100%;
    font-display: swap;
    src: url(data:font/woff2;base64,{blobs["Bricolage Grotesque"]}) format("woff2");
}}

/* Subset: Latin-1 only, single weight (400). Bold and italic are         */
/* synthesised by the renderer, and characters outside the range below    */
/* fall through to the next font in the stack.                            */
@font-face {{
    font-family: "Roboto";
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    unicode-range: {LATIN1};
    src: url(data:font/woff2;base64,{blobs["Roboto"]}) format("woff2");
}}

/* Subset: Latin-1 only, single weight (400). Same caveats as Roboto. */
@font-face {{
    font-family: "Montserrat";
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    unicode-range: {LATIN1};
    src: url(data:font/woff2;base64,{blobs["Montserrat"]}) format("woff2");
}}
'''

open("theme.css","w").write(HEADER + yaml_block + "\n\n" + theme_block + "\n" + RULES + FACES)
print("theme.css written")
