#!/usr/bin/env python3
"""Recolor theme files into Flexoki Light (https://stephango.com/flexoki).

  remap.py vesper <in> <out>   explicit Vesper -> Flexoki Light table (app configs)
  remap.py shell  <in> <out>   perceptual remap of Yaru (light) gnome-shell.css

The generated files live in ../flexoki-light and are committed; rerun this
only when the Vesper source files change.
"""
import colorsys
import re
import sys

# Flexoki Light roles
PAPER, BG2 = "#FFFCF0", "#F2F0E5"
UI, UI2, UI3 = "#E6E4D9", "#DAD8CE", "#CECDC3"
TX3, B500, TX2, B700, TX = "#B7B5AC", "#878580", "#6F6E69", "#575653", "#100F0F"
ORANGE, ORANGE_DK, ORANGE_LT = "#BC5215", "#9D4310", "#DA702C"
RED, RED_LT = "#AF3029", "#D14D41"
YELLOW, YELLOW_LT = "#AD8301", "#D0A215"
GREEN, GREEN_LT = "#66800B", "#879A39"
CYAN, CYAN_LT = "#24837B", "#3AA99F"
BLUE = "#205EA6"
PURPLE, PURPLE_LT = "#5E409D", "#8B7EC8"
MAGENTA, MAGENTA_LT = "#A02F6F", "#CE5D97"

VESPER = {
    # neutrals, inverted
    "#101010": PAPER, "#161616": BG2, "#1a1a1a": BG2, "#1a1a1e": BG2,
    "#1c1c1c": UI, "#1f1f1f": UI, "#232323": UI,
    "#282828": UI2, "#2a2a2a": UI2, "#2c2c2c": UI2,
    "#333333": UI3, "#343434": UI3, "#505050": TX3, "#6b6b6b": B500,
    "#7e7e7e": TX2, "#a0a0a0": B700, "#acb1ab": TX2, "#b9beb8": B500,
    "#ffffff": TX,
    # accents
    "#ffc799": ORANGE, "#ffcfa8": ORANGE_DK, "#ffdabc": ORANGE_LT,
    "#e6a97a": ORANGE_DK, "#f5a191": ORANGE_LT, "#eed1bf": ORANGE_DK,
    "#e6b99d": YELLOW, "#988049": YELLOW_LT,
    "#99ffe4": CYAN, "#bcffed": CYAN_LT, "#90b99f": GREEN,
    "#ff8080": RED, "#ffacac": RED_LT,
    "#ecaad6": MAGENTA, "#e29eca": MAGENTA_LT, "#ea83a5": MAGENTA,
    "#f591b2": MAGENTA_LT, "#f1aec4": MAGENTA_LT,
    "#b9aeda": PURPLE, "#aca1cf": PURPLE, "#c9c1df": PURPLE_LT,
    # dim tints (btop meter backgrounds) -> pale Flexoki tints
    "#447266": "#BFE8D9", "#4d485d": "#E2D9E9", "#675346": "#FED3AF",
    "#693a4a": "#FCCFDA", "#723939": "#FFCABB", "#725944": "#FED3AF",
}
RGBA_VESPER = {  # rgba(r, g, b, a) bases
    (255, 255, 255): (16, 15, 15), (16, 16, 16): (255, 252, 240),
    (35, 35, 35): (230, 228, 217), (0, 0, 0): (16, 15, 15),
    (255, 199, 153): (188, 82, 21),
}

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(,\s*[\d.]+\s*)?\)")


def keep_case(src, dst):
    return dst.lower() if src[1:].islower() or src[1:].isdigit() else dst


def vesper(text):
    def hx(m):
        s = m.group(0)
        d = VESPER.get(s.lower())
        if d is None:
            sys.stderr.write(f"unmapped {s}\n")
            return s
        return keep_case(s, d)

    def rgba(m):
        rgb = tuple(int(m.group(i)) for i in (1, 2, 3))
        r, g, b = RGBA_VESPER.get(rgb, rgb)
        a = m.group(4) or ""
        return f"rgba({r}, {g}, {b}{a})" if a else f"rgb({r}, {g}, {b})"

    return RGBA.sub(rgba, HEX.sub(hx, text))


# ---- perceptual remap for the shell theme ----------------------------------
NEUTRALS = [PAPER, BG2, UI, UI2, UI3, TX3, B500, TX2, B700,
            "#403E3C", "#343331", "#282726", "#1C1B1A", TX]
HUES = [  # (max hue deg, dark, light)
    (15, RED, RED_LT), (45, ORANGE, ORANGE_LT), (65, YELLOW, YELLOW_LT),
    (160, GREEN, GREEN_LT), (200, CYAN, CYAN_LT), (250, BLUE, "#4385BE"),
    (290, PURPLE, PURPLE_LT), (345, MAGENTA, MAGENTA_LT), (361, RED, RED_LT),
]
NAMED = {"white": "#ffffff", "black": "#000000"}


def rgb_of(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))[1]


def nearest(rgb):
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    if s < 0.18 or l > 0.93 or l < 0.06:
        return min(NEUTRALS, key=lambda n: abs(lum(rgb_of(n)) - l))
    deg = h * 360
    for top, dark, light in HUES:
        if deg < top:
            return light if l > 0.55 else dark


def shell(text):
    def hx(m):
        return nearest(rgb_of(m.group(1))).lower()

    def named(m):
        return nearest(rgb_of(NAMED[m.group(2)])).lower()

    def rgba(m):
        rgb = tuple(int(m.group(i)) for i in (1, 2, 3))
        r, g, b = rgb_of(nearest(rgb))
        a = m.group(4) or ""
        return f"rgba({r}, {g}, {b}{a})" if a else f"rgb({r}, {g}, {b})"

    text = RGBA.sub(rgba, text)
    text = re.sub(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", hx, text)
    # only bare color keywords in declarations, not selectors
    text = re.sub(r"(:\s*[^;{}]*?)\b(white|black)\b", lambda m: m.group(1) + named(m), text)
    return text


if __name__ == "__main__":
    mode, src, dst = sys.argv[1:4]
    out = (vesper if mode == "vesper" else shell)(open(src).read())
    open(dst, "w").write(out)
