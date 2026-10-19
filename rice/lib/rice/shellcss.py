"""The GNOME Shell stylesheet for a theme: Ubuntu's Yaru shell theme, recoloured.

Yaru (light themes) or Yaru-dark (dark themes) is read from /usr/share/themes and
every colour in it is mapped onto the palette:

- greys go through a lightness ramp anchored on Yaru's own roles (its darkest
  panel grey, its base, its popover grey, its text, white), so a theme keeps
  Yaru's structure: raised popovers, dark OSDs in light mode and so on;
- colours go to the palette colour of the nearest hue, keeping Yaru's lightness
  steps between normal, hover and pressed shades;
- -st-accent-color becomes the theme's exact accent.

St's own functions (st-mix, st-lighten...) stay in place and work on the new
colours at runtime. The rice-bar rules and a theme's extra CSS go at the end.
This is how the hand-made Vesper and Flexoki Light shell themes were made,
generalised to any palette. Results are cached per palette.
"""
import hashlib
import json
import re
from pathlib import Path

from . import colormath as cm

SOURCES = {
    "dark": [Path("/usr/share/themes/Yaru-dark/gnome-shell/gnome-shell.css")],
    "light": [Path("/usr/share/themes/Yaru/gnome-shell/gnome-shell.css")],
}
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")
NAMED = re.compile(r"(?<![-\w])(white|black)(?![-\w])")
# Yaru's reference colour for each hue family (lightness steps are kept relative to it).
FAMILY_REF = {"red": "#c7162b", "orange": "#e95420", "yellow": "#f99b11", "green": "#0e8420",
              "cyan": "#1b9aaa", "blue": "#19b6ee", "magenta": "#b34cb3"}
VERSION = "3"  # bump to invalidate cached stylesheets


def _anchors(c, mode):
    bg, fg = c["background"], c["foreground"]
    bright = c.get("bright_foreground") if cm.is_hex(c.get("bright_foreground", "")) else fg
    if mode == "dark":
        dark = c.get("dark_background") if cm.is_hex(c.get("dark_background", "")) else cm.mix(bg, "#000000", "25%")
        return [("#000000", cm.mix(dark, "#000000", "45%")), ("#131313", dark), ("#222222", bg),
                ("#36363a", cm.mix_oklab(bg, fg, "11%")), ("#f2f2f2", fg), ("#ffffff", bright)]
    dark = c.get("dark_background") if cm.is_hex(c.get("dark_background", "")) else cm.mix(bg, "#000000", "5%")
    return [("#000000", cm.mix(fg, "#000000", "55%")), ("#131313", cm.mix(fg, "#000000", "25%")),
            ("#222222", fg), ("#ededed", cm.mix_oklab(dark, fg, "6%")), ("#f2f2f2", dark), ("#ffffff", bg)]


class Mapper:
    def __init__(self, colors, mode):
        self.c = colors
        self.mode = mode
        pts = [(cm.oklab(s)[0], cm.oklab(t)) for s, t in _anchors(colors, mode)]
        self.ramp = sorted(pts)
        self.hues = {k: colors[k] for k in FAMILY_REF if cm.is_hex(colors.get(k, ""))}
        self.cache = {}

    def _grey(self, L):
        r = self.ramp
        if L <= r[0][0]:
            return cm.from_oklab(r[0][1])
        for (l0, t0), (l1, t1) in zip(r, r[1:]):
            if L <= l1:
                f = 0 if l1 == l0 else (L - l0) / (l1 - l0)
                return cm.from_oklab(tuple(t0[i] + (t1[i] - t0[i]) * f for i in range(3)))
        return cm.from_oklab(r[-1][1])

    def hex(self, h):
        h = h.lower()
        if h in self.cache:
            return self.cache[h]
        L, C, hue = cm.oklch(h)
        if C < 0.035 or not self.hues:
            out = self._grey(L)
        else:
            family = min(self.hues, key=lambda k: cm.hue_distance(hue, cm.oklch(FAMILY_REF[k])[2]))
            tL, tC, th = cm.oklch(self.hues[family])
            refL = cm.oklch(FAMILY_REF[family])[0]
            out = cm.from_oklch(max(0.05, min(0.97, tL + 0.6 * (L - refL))), tC, th)
        self.cache[h] = out
        return out


def remap(css, colors, mode):
    m = Mapper(colors, mode)
    accent = colors.get("accent", "#3584e4")
    on_accent = colors.get("ui_on_accent", "#ffffff")
    css = css.replace("-st-accent-fg-color", on_accent).replace("-st-accent-color", accent)

    def rgba(match):
        r, g, b, a = match.groups()
        t = cm.to_rgb(m.hex(cm.to_hex((int(r), int(g), int(b)))))
        return f"rgba({t[0]}, {t[1]}, {t[2]}, {a})" if a is not None else f"rgb({t[0]}, {t[1]}, {t[2]})"

    def hexsub(match):
        return m.hex(match.group(0))

    out = []
    # Only touch declarations, never selectors (#panel is an id, not a colour).
    for chunk in re.split(r"(\{[^{}]*\})", css):
        if chunk.startswith("{"):
            chunk = RGBA.sub(rgba, chunk)
            chunk = HEX.sub(hexsub, chunk)
            chunk = NAMED.sub(lambda x: m.hex("#ffffff" if x.group(1) == "white" else "#000000"), chunk)
        out.append(chunk)
    return "".join(out)


def source_css(mode):
    for p in SOURCES[mode]:
        if p.is_file():
            return p.read_text()
    return None


def build(colors, mode, cache_dir, tail=""):
    """The full stylesheet text, or None when no Yaru source is installed."""
    key = hashlib.sha1(json.dumps([VERSION, mode, sorted(colors.items())]).encode()).hexdigest()[:16]
    cached = cache_dir / f"shell-{key}.css"
    if cached.is_file():
        base = cached.read_text()
    else:
        src = source_css(mode)
        if src is None:
            return None
        base = ("/* Generated by rice from Yaru%s's gnome-shell.css. Do not edit. */\n"
                % ("-dark" if mode == "dark" else "")) + remap(src, colors, mode)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cached.with_suffix(".tmp")
        tmp.write_text(base)
        tmp.replace(cached)
        # keep the cache small
        files = sorted(cache_dir.glob("shell-*.css"), key=lambda p: p.stat().st_mtime)
        for old in files[:-40]:
            old.unlink(missing_ok=True)
    return base + "\n\n/* ---- rice additions ---- */\n" + tail
