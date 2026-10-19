"""Colour helpers: hex parsing, Omarchy-compatible mixing, contrast and OKLab.

`mix` rounds exactly like Omarchy's awk renderer (int(x + 0.5) per channel), so a
template renders the same bytes here as it does on Omarchy.
"""
import math
import re

HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")


def is_hex(value):
    return isinstance(value, str) and bool(HEX6.match(value))


def to_rgb(value):
    """'#rrggbb' or '#rgb' -> (r, g, b) ints."""
    h = value.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:  # rrggbbaa: drop the alpha
        h = h[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def strip(value):
    return value[1:] if value.startswith("#") else value


def rgb_string(value):
    return "%d,%d,%d" % to_rgb(value)


def parse_amount(amount):
    """Omarchy accepts 30%, 0.3 and 30 (anything over 1 is a percentage)."""
    amount = str(amount).strip()
    if amount.endswith("%"):
        a = float(amount[:-1]) / 100
    else:
        a = float(amount)
        if a > 1:
            a = a / 100
    return max(0.0, min(1.0, a))


def mix(start, end, amount):
    """Mix two hex colours; amount is how far toward `end` (Omarchy semantics)."""
    a = parse_amount(amount)
    s, e = to_rgb(start), to_rgb(end)
    return to_hex(int(s[i] * (1 - a) + e[i] * a + 0.5) for i in range(3))


def rgba(value, alpha):
    r, g, b = to_rgb(value)
    alpha = round(alpha, 3)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


# ---- luminance and contrast (WCAG) --------------------------------------------

def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(value):
    r, g, b = (_lin(c) for c in to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def omarchy_is_light(value):
    """Omarchy's mode auto-detect: r + g + b > 382."""
    return sum(to_rgb(value)) > 382


# ---- OKLab / OKLCH (https://bottosson.github.io/posts/oklab/) ----------------

def _to_srgb_channel(x):
    x = max(0.0, min(1.0, x))
    v = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return v * 255


def oklab(value):
    r, g, b = (_lin(c) for c in to_rgb(value))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return to_hex(round(_to_srgb_channel(c)) for c in (r, g, bb))


def oklch(value):
    L, a, b = oklab(value)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def from_oklch(L, C, h):
    return from_oklab((L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))))


def oklab_distance(x, y):
    a, b = oklab(x), oklab(y)
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def mix_oklab(start, end, amount):
    """Perceptual mix, used for ramps where sRGB mixing goes muddy."""
    a = parse_amount(amount)
    s, e = oklab(start), oklab(end)
    return from_oklab(tuple(s[i] * (1 - a) + e[i] * a for i in range(3)))


def hue_distance(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def readable_on(bg, *candidates):
    """The candidate with the best contrast against bg."""
    return max(candidates, key=lambda c: contrast(bg, c))


def legible(color, bg, target=3.0):
    """color, moved in OKLCH lightness (away from bg) until it has `target` contrast
    on bg. Chroma is kept, and lifted a little for pale colours that darken, so a
    peach becomes a burnt orange rather than a brown."""
    if contrast(color, bg) >= target:
        return color
    L, C, h = oklch(color)
    step = -0.02 if luminance(bg) > 0.18 else 0.02
    if step < 0:
        C = max(C, min(0.15, C * 1.6))
    out = color
    for _ in range(45):
        L = max(0.0, min(1.0, L + step))
        out = from_oklch(L, C, h)
        if contrast(out, bg) >= target:
            break
    return out
