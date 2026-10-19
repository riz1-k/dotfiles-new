"""Picker thumbnails and the terminal palette preview.

Thumbnails are scaled once and cached in ~/.cache/rice/previews, keyed on the source
path, size and modification time (as Omarchy's picker does), so the shell never
decodes a 4K wallpaper to draw a carousel slot.
"""
import hashlib
import json

from . import colormath as cm
from . import themes as themes_mod

WIDTH, HEIGHT = 960, 540
KEEP = 600  # cached thumbnails kept


def thumb_path(paths, src):
    st = src.stat()
    key = f"{src.resolve()}:{st.st_mtime_ns}:{st.st_size}:{WIDTH}x{HEIGHT}"
    return paths.previews / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".jpg")


def thumbnail(paths, src, make=True):
    """The cached thumbnail for an image; the image itself when PIL can't make one
    (or make=False and none is cached yet)."""
    if src is None:
        return None
    try:
        out = thumb_path(paths, src)
    except OSError:
        return None
    if out.is_file():
        return out
    if not make:
        return src
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return src
    try:
        with Image.open(src) as im:
            im.draft("RGB", (WIDTH * 2, HEIGHT * 2))  # fast JPEG downscale on decode
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.fit(im, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + ".tmp")
            im.save(tmp, "JPEG", quality=86, optimize=True)
            tmp.replace(out)
        return out
    except Exception:  # noqa: BLE001 - a broken image just has no thumbnail
        return src


def prune(paths):
    if not paths.previews.is_dir():
        return
    files = sorted(paths.previews.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    for old in files[:-KEEP]:
        old.unlink(missing_ok=True)


def theme_rows(paths, make=False):
    current = themes_mod.current_name(paths)
    rows = []
    for name, t in themes_mod.all_themes(paths).items():
        palette = t.palette()
        if not palette:
            continue
        src = t.preview(paths)
        rows.append({
            "name": name,
            "display": t.display,
            "mode": palette.get("mode", "dark"),
            "origin": t.origin,
            "git": t.git,
            "removable": t.git or t.origin == "omarchy",
            "current": name == current,
            "accent": palette.get("accent"),
            "background": palette.get("background"),
            "foreground": palette.get("foreground"),
            "preview": str(src) if src else None,
            "thumb": str(thumbnail(paths, src, make)) if src else None,
        })
    return rows


def background_rows(paths, theme, make=False):
    from . import backgrounds
    now = backgrounds.current(paths)
    rows = []
    for p in backgrounds.candidates(paths, theme):
        rows.append({"name": p.stem, "path": str(p), "current": p == now,
                     "user": p.parent == paths.user_backgrounds / theme.name,
                     "thumb": str(thumbnail(paths, p, make))})
    return rows


def warm(paths):
    """Make every missing theme preview and the current theme's wallpaper thumbnails."""
    rows = theme_rows(paths, make=True)
    current = themes_mod.find(paths, themes_mod.current_name(paths))
    if current:
        background_rows(paths, current, make=True)
    prune(paths)
    return rows


# ---- preview.png for themes without one -------------------------------------------

def render_image(colors, wallpaper, out, size=(1600, 900)):
    """A picker preview in the spirit of Omarchy's: the wallpaper with the bar, a
    terminal and a monitor drawn in the theme's colours. Needs PIL."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    W, H = size
    c = colors
    rgb = lambda k: cm.to_rgb(c[k]) if cm.is_hex(c.get(k, "")) else cm.to_rgb(c["foreground"])
    if wallpaper:
        with Image.open(wallpaper) as im:
            im.draft("RGB", (W * 2, H * 2))
            base = ImageOps.fit(ImageOps.exif_transpose(im).convert("RGB"), size, Image.Resampling.LANCZOS)
    else:
        base = Image.new("RGB", size, rgb("background"))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = W / 1600

    def box(xy, fill, outline=None, r=14, width=2):
        d.rounded_rectangle([int(v * s) for v in xy], radius=int(r * s), fill=fill,
                            outline=outline, width=max(1, int(width * s)))

    surface = rgb("ui_surface") + (242,)
    border = rgb("foreground") + (36,)
    # the bar: two islands and the inverse capsule
    box((24, 16, 150, 58), surface, border, 14, 1)
    box((1360, 16, 1576, 58), surface, border, 14, 1)
    box((690, 16, 910, 58), rgb("ui_inverse") + (255,), None, 14)
    for i, x in enumerate((44, 70, 96)):
        box((x, 33, x + (18 if i == 0 else 8), 41), rgb("foreground") + (255,), None, 4)
    for x in (1380, 1420, 1460, 1500, 1540):
        box((x, 29, x + 16, 45), rgb("foreground") + (200,), None, 5)
    box((720, 31, 800, 43), rgb("ui_inverse_dim") + (255,), None, 5)
    box((812, 29, 880, 45), rgb("ui_inverse_fg") + (255,), None, 5)
    # terminal
    box((120, 120, 980, 820), rgb("background") + (250,), rgb("ui_border") + (255,), 14, 2)
    box((120, 120, 980, 168), rgb("ui_surface") + (255,), None, 14)
    d.rectangle([int(120 * s), int(150 * s), int(980 * s), int(168 * s)], fill=rgb("ui_surface") + (255,))
    for i, k in enumerate(("red", "yellow", "green")):
        x = 150 + i * 30
        d.ellipse([int(x * s), int(136 * s), int((x + 14) * s), int(150 * s)], fill=rgb(k) + (255,))
    lines = [("accent", 60, "foreground", 260), ("muted", 340, None, 0), ("magenta", 80, "blue", 200),
             ("yellow", 120, "green", 320), ("foreground", 90, "cyan", 160), ("muted", 280, None, 0),
             ("red", 70, "foreground", 380), ("blue", 150, "orange", 90), ("green", 240, "foreground", 120),
             ("magenta", 60, "yellow", 300), ("muted", 200, None, 0), ("accent", 40, "foreground", 180)]
    y = 200
    for k1, w1, k2, w2 in lines:
        box((160, y, 160 + w1, y + 16), rgb(k1) + (255,), None, 6)
        if k2:
            box((172 + w1, y, 172 + w1 + w2, y + 16), rgb(k2) + (255,), None, 6)
        y += 44
    box((160, y + 6, 176, y + 30), rgb("accent") + (255,), None, 3)
    # system monitor
    box((1040, 120, 1480, 520), rgb("background") + (250,), rgb("ui_border") + (255,), 14, 2)
    for i, k in enumerate(("blue", "magenta", "cyan", "green", "yellow")):
        top = 170 + i * 62
        box((1076, top, 1444, top + 18), rgb("ui_surface_alt") + (255,), None, 8)
        box((1076, top, 1076 + int(368 * (0.35 + 0.13 * ((i * 7) % 5))), top + 18), rgb(k) + (255,), None, 8)
    # a card in the accent
    box((1040, 560, 1480, 820), rgb("ui_surface") + (245,), rgb("ui_border") + (255,), 14, 2)
    box((1076, 600, 1260, 624), rgb("foreground") + (255,), None, 8)
    box((1076, 648, 1380, 664), rgb("ui_dim") + (255,), None, 6)
    box((1076, 680, 1320, 696), rgb("ui_dim") + (255,), None, 6)
    box((1076, 740, 1220, 784), rgb("accent") + (255,), None, 12)
    shadow = layer.split()[3].filter(ImageFilter.GaussianBlur(int(18 * s)))
    base.paste((0, 0, 0), (0, int(8 * s)), shadow.point(lambda a: int(a * 0.35)))
    base = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    base.save(tmp, "PNG", optimize=True)
    tmp.replace(out)
    return out


# ---- terminal preview (rice theme preview) ---------------------------------------

def _bg(h):
    r, g, b = cm.to_rgb(h)
    return f"\x1b[48;2;{r};{g};{b}m"


def _fg(h):
    r, g, b = cm.to_rgb(h)
    return f"\x1b[38;2;{r};{g};{b}m"


RESET = "\x1b[0m"


def ramp(name, colors):
    c = colors
    bg, fg = c["background"], c["foreground"]
    out = []
    width = 64

    def line(text, fgc=fg, bgc=bg):
        out.append(_bg(bgc) + _fg(fgc) + " " + text.ljust(width - 1) + RESET)

    line(f"{themes_mod.display_name(name)}  ({c.get('mode', 'dark')})", c.get("bright_foreground", fg))
    line("")
    for key in ("background", "dark_background", "darker_background", "lighter_background",
                "selection", "muted"):
        if cm.is_hex(c.get(key, "")):
            out.append(_bg(bg) + _fg(fg) + " " + _bg(c[key]) + "      " + _bg(bg)
                       + f" {key:<20}{c[key]}".ljust(width - 7) + RESET)
    line("")
    for key in ("foreground", "dark_foreground", "light_foreground", "bright_foreground", "accent"):
        if cm.is_hex(c.get(key, "")):
            line(f"{key:<20}{c[key]}  The quick brown fox", c[key])
    line("")
    names = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    for row in (range(0, 8), range(8, 16)):
        cells = ""
        for i in row:
            h = c.get(f"color{i}", bg)
            text = "#" if not cm.is_hex(h) else ("  " + str(i)).rjust(4) + "  "
            ink = cm.readable_on(h, bg, fg) if cm.is_hex(h) else fg
            cells += _bg(h) + _fg(ink) + text
        out.append(_bg(bg) + " " + cells + _bg(bg) + " " * (width - 1 - 6 * 8) + RESET)
    line("    " + "     ".join(n[:2] for n in names), c.get("dark_foreground", fg))
    line("")
    roles = [k for k in sorted(c) if k.startswith("ui_") and cm.is_hex(c[k])]
    for key in roles:
        h = c[key]
        out.append(_bg(bg) + _fg(fg) + " " + _bg(h) + "      " + _bg(bg)
                   + f" {key:<20}{h}".ljust(width - 7) + RESET)
    contrast = cm.contrast(fg, bg)
    line("")
    line(f"text contrast {contrast:.1f}:1" + ("" if contrast >= 4.5 else "  (low: aim for 4.5)"),
         c.get("dark_foreground", fg))
    return "\n".join(out)


def rows_json(rows):
    return json.dumps(rows, indent=1)
