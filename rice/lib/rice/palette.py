"""colors.toml parsing and the palette cascade.

A line-for-line port of Omarchy's `omarchy-theme-color` (basecamp/omarchy, MIT), so
every theme resolves to the same palette here as there: legacy color0-15 and short
names, derived shades, the mode precedence. On top of that come the `ui_*` keys,
rice's own semantic roles for desktop surfaces (cards, borders, text on the
accent...). They are only derived when a theme doesn't set them, so an Omarchy
theme never needs to know about them.
"""
import re

from . import colormath as cm

KEY_OK = re.compile(r"^[A-Za-z0-9_-]+$")
# Values end up inside configs that run code (tmux formats, zsh, shell CSS), so only
# colours get through, and they're stored as #rrggbb (what every template and the
# colour maths expect): #rgb, #rrggbb, #rrggbbaa (alpha dropped) and rgb()/rgba().
# `mode` is light or dark. ui_shade alone keeps an rgba() (it's a CSS shadow colour).
# Never a quote, $, backtick, #( or #{.
_HEX = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
_RGB = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*((?:\d*\.)?\d+)\s*)?\)$")
MODE_KEYS = ("mode", "theme_type")
ALPHA_KEYS = ("ui_shade",)


def colour_value(key, value):
    """The stored form of a colors.toml value, or None if it isn't allowed."""
    if value == "":
        return ""
    if key in MODE_KEYS:
        return value if value in ("light", "dark") else None
    if _HEX.match(value):
        return value if len(value) == 7 else cm.to_hex(cm.to_rgb(value))
    m = _RGB.match(value)
    if m and all(int(x) <= 255 for x in m.group(1, 2, 3)):
        if key in ALPHA_KEYS and m.group(4) is not None and float(m.group(4)) <= 1:
            return f"rgba({m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)})"
        return cm.to_hex(int(x) for x in m.group(1, 2, 3))
    return None


LEGACY_PALETTE_ALIAS = {
    "background": "bg",
    "dark_background": "dark_bg",
    "darker_background": "darker_bg",
    "lighter_background": "lighter_bg",
    "foreground": "fg",
    "dark_foreground": "dark_fg",
    "light_foreground": "light_fg",
    "bright_foreground": "bright_fg",
}
LEGACY_ALIAS = {
    "red": "color1", "green": "color2", "yellow": "color3", "blue": "color4",
    "magenta": "color5", "cyan": "color6",
    "bright_red": "color9", "bright_green": "color10", "bright_yellow": "color11",
    "bright_blue": "color12", "bright_magenta": "color13", "bright_cyan": "color14",
}
ANSI_ALIAS = {
    "color0": "background", "color1": "red", "color2": "green", "color3": "yellow",
    "color4": "blue", "color5": "magenta", "color6": "cyan", "color7": "foreground",
    "color8": "muted", "color9": "bright_red", "color10": "bright_green",
    "color11": "bright_yellow", "color12": "bright_blue", "color13": "bright_magenta",
    "color14": "bright_cyan", "color15": "bright_foreground",
}

# The keys a complete Omarchy palette defines, in Omarchy's documented order.
CANONICAL = [
    "mode", "accent", "selection", "muted",
    "background", "dark_background", "darker_background", "lighter_background",
    "foreground", "dark_foreground", "light_foreground", "bright_foreground",
    "red", "yellow", "orange", "green", "cyan", "blue", "magenta", "brown",
    "bright_red", "bright_yellow", "bright_green", "bright_cyan", "bright_blue",
    "bright_magenta",
]

# OKLCH hues for filling in hues a palette leaves out.
HUES = {"red": 25, "yellow": 90, "green": 145, "cyan": 195, "blue": 255, "magenta": 330}

# rice's semantic roles. Documented in docs/themes.md.
UI_KEYS = [
    "ui_surface", "ui_surface_alt", "ui_border", "ui_dim", "ui_faint",
    "ui_success", "ui_danger", "ui_warning", "ui_info", "ui_on_accent", "ui_accent_soft",
    "ui_inverse", "ui_inverse_fg", "ui_inverse_dim", "ui_inverse_accent", "ui_inverse_on_accent",
    "ui_shade",
]


def parse(text, warnings=None):
    """Omarchy's colors.toml reader: flat `key = value` lines, last one wins.

    It's deliberately not a TOML parser: Omarchy themes in the wild hold
    duplicate keys and stray section headers, which tomllib would reject.
    """
    colors = {}
    for raw in text.splitlines():
        if "=" not in raw:
            key, value = raw, ""
        else:
            key, value = raw.split("=", 1)
        key = re.sub(r"[\"' ]", "", key)
        if not key or key.startswith("#"):
            continue
        if re.search(r"[\"']", value):
            value = re.split(r"[\"']", value, maxsplit=1)[1]
            value = re.split(r"[\"']", value, maxsplit=1)[0]
        else:
            value = value.strip()
        if not KEY_OK.match(key):
            if warnings is not None:
                warnings.append(f"skipping key with unsupported characters: {key[:40]}")
            continue
        stored = colour_value(key, value)
        if stored is None:
            if warnings is not None:
                warnings.append(f"skipping {key}: " + ("not light or dark" if key in MODE_KEYS else "not a colour"))
            continue
        colors[key] = stored
    return colors


def _mix(a, b, amount):
    return cm.mix(a, b, amount) if cm.is_hex(a) and cm.is_hex(b) else ""


def resolve(raw, light_mode_file=False):
    """The full palette for a theme, following omarchy-theme-color step by step."""
    c = dict(raw)

    def get(key):
        return c.get(key, "")

    def alias(key, fallback):
        if not get(key):
            c[key] = get(fallback)

    for key, short in LEGACY_PALETTE_ALIAS.items():
        alias(key, short)

    if not get("background"):
        c["background"] = get("color0")
    if not get("foreground"):
        c["foreground"] = get("color7")
    if get("background"):
        c["color0"] = get("background")
    if get("foreground"):
        c["color7"] = get("foreground")

    for key, legacy in LEGACY_ALIAS.items():
        alias(key, legacy)
    alias("magenta", "purple")
    alias("bright_magenta", "bright_purple")

    if not get("light_foreground"):
        c["light_foreground"] = get("color7") or get("foreground")
    if not get("bright_foreground"):
        c["bright_foreground"] = get("color15") or get("foreground")
    c["cursor"] = get("bright_foreground")
    if not get("lighter_background"):
        c["lighter_background"] = get("color0") or get("background")
    if not get("dark_foreground"):
        c["dark_foreground"] = get("color8") or get("foreground")
    if not get("muted"):
        c["muted"] = get("color8") or get("dark_foreground")
    if not get("selection"):
        c["selection"] = (get("selection_background") or get("color8") or get("color0")
                          or get("background"))
    if not get("selection_background"):
        c["selection_background"] = get("selection")
    if not get("selection_foreground"):
        c["selection_foreground"] = get("bright_foreground")
    if not get("orange"):
        c["orange"] = get("yellow")
    if not get("brown"):
        c["brown"] = _mix(get("orange"), "#000000", "50%")

    if not get("dark_background"):
        c["dark_background"] = _mix(get("background"), "#000000", "25%")
    if not get("darker_background"):
        c["darker_background"] = _mix(get("background"), "#000000", "50%")
    for key in ("red", "yellow", "green", "cyan", "blue", "magenta"):
        if not get(f"bright_{key}"):
            c[f"bright_{key}"] = _mix(get(key), "#ffffff", "20%")
    alias("purple", "magenta")
    alias("bright_purple", "bright_magenta")

    for key, target in ANSI_ALIAS.items():
        alias(key, target)

    for key, short in LEGACY_PALETTE_ALIAS.items():
        if get(key):
            c[short] = get(key)

    if not get("mode"):
        c["mode"] = get("theme_type")
    if not get("mode"):
        if light_mode_file:
            c["mode"] = "light"
        elif cm.is_hex(get("background")):
            c["mode"] = "light" if cm.omarchy_is_light(get("background")) else "dark"
        else:
            c["mode"] = "dark"
    c["theme_type"] = c["mode"]

    _derive_ui(c)
    return c


def _valid(c, key):
    return cm.is_hex(c.get(key, ""))


def _derive_ui(c):
    """Fill rice's ui_* roles from the Omarchy palette where a theme leaves them out."""
    bg = c.get("background") if _valid(c, "background") else ("#ffffff" if c.get("mode") == "light" else "#101010")
    fg = c.get("foreground") if _valid(c, "foreground") else ("#101010" if c.get("mode") == "light" else "#ffffff")
    light = c.get("mode") == "light"

    def put(key, value):
        if not _valid(c, key):
            c[key] = value

    # A palette without some hues (a minimal colors.toml) still renders every
    # template: missing hues get a neutral colour at the theme's text lightness.
    # Complete Omarchy palettes never reach this.
    text_l = max(0.42, min(0.80, cm.oklch(fg)[0] - (0.08 if not light else -0.30)))
    for key, hue in HUES.items():
        put(key, cm.from_oklch(text_l, 0.13, hue))
    put("orange", c["yellow"])
    put("brown", cm.mix(c["orange"], "#000000", "50%"))
    for key in HUES:
        put(f"bright_{key}", cm.mix(c[key], "#ffffff", "20%"))
    c["purple"], c["bright_purple"] = c["magenta"], c["bright_magenta"]
    for key, target in ANSI_ALIAS.items():
        if not _valid(c, key) and _valid(c, target):
            c[key] = c[target]

    surface = c.get("dark_background" if light else "lighter_background", "")
    if not cm.is_hex(surface) or surface.lower() == bg.lower() or cm.oklab_distance(surface, bg) < 0.012:
        surface = cm.mix(bg, fg, "5%")
    put("ui_surface", surface)
    put("ui_surface_alt", cm.mix(c["ui_surface"], fg, "7%"))
    put("ui_border", cm.mix(bg, fg, "14%"))

    # dark_foreground is the dimmer text on a dark theme, but on a light theme it
    # can be the darker (stronger) one: only use it if it sits between fg and bg.
    dim = c.get("dark_foreground", "")
    if not cm.is_hex(dim) or not 3 <= cm.contrast(dim, bg) < cm.contrast(fg, bg):
        dim = cm.mix(fg, bg, "38%")
    put("ui_dim", dim)
    put("ui_faint", cm.mix(fg, bg, "62%"))

    for key, src in (("ui_success", "green"), ("ui_danger", "red"),
                     ("ui_warning", "yellow"), ("ui_info", "blue")):
        put(key, c[src] if _valid(c, src) else fg)

    accent = c.get("accent") if _valid(c, "accent") else (c.get("blue") if _valid(c, "blue") else fg)
    if not _valid(c, "accent"):
        c["accent"] = accent
    on = [x for x in (bg, c.get("bright_foreground", ""), "#ffffff", "#000000") if cm.is_hex(x)]
    # Prefer the theme's own colours over pure black/white when they read well enough.
    best = cm.readable_on(accent, *on)
    for x in on[:2]:
        if cm.contrast(accent, x) >= 4.0:
            best = x
            break
    put("ui_on_accent", best)
    put("ui_accent_soft", cm.mix(bg, accent, "22%"))
    # The inverse surface: the bar's centre capsule is light on a dark theme and dark
    # on a light one, with an accent that still reads on it.
    bright = c.get("bright_foreground") if _valid(c, "bright_foreground") else fg
    put("ui_inverse", fg if light else cm.mix(bright, bg, "6%"))
    put("ui_inverse_fg", c["ui_surface"] if light else bg)
    put("ui_inverse_dim", cm.mix(c["ui_inverse_fg"], c["ui_inverse"], "38%"))
    put("ui_inverse_accent", cm.legible(accent, c["ui_inverse"], 3.2))
    put("ui_inverse_on_accent", cm.readable_on(c["ui_inverse_accent"], c["ui_inverse"], c["ui_inverse_fg"]))
    # Drop shadows (GTK4 shade colours): black in dark themes, a light ink wash in light ones.
    if not c.get("ui_shade"):
        c["ui_shade"] = ("rgba(%d, %d, %d, 0.08)" % cm.to_rgb(fg)) if light else "rgba(0, 0, 0, 0.36)"


def load(theme_dir, warnings=None):
    """Resolved palette for a theme folder ({} without a colors.toml)."""
    path = theme_dir / "colors.toml"
    if not path.is_file():
        return {}
    raw = parse(path.read_text(errors="replace"), warnings)
    return resolve(raw, light_mode_file=(theme_dir / "light.mode").exists())


def template_values(colors):
    """Every `{{ token }}` a template may use, as Omarchy builds its value table."""
    values = {}
    for key, value in colors.items():
        values[f"{{{{ {key} }}}}"] = value
        values[f"{{{{ {key}_strip }}}}"] = value[1:] if value.startswith("#") else value
        if cm.is_hex(value):
            values[f"{{{{ {key}_rgb }}}}"] = cm.rgb_string(value)
    return values
