"""GNOME: the shell (via the rice-shell extension), colour scheme, accent, wallpaper,
icons, GTK and the window-border extensions."""
import json
import re
import subprocess
from pathlib import Path

from .. import colormath as cm
from .. import util

IFACE = "org.gnome.desktop.interface"
BG = "org.gnome.desktop.background"
SCREENSAVER = "org.gnome.desktop.screensaver"

DBUS_DEST = "org.gnome.Shell"
DBUS_PATH = "/org/riz1/Rice"
DBUS_IFACE = "org.riz1.Rice"

# GNOME's accent colours (libadwaita's values), for the nearest match.
ACCENTS = {
    "blue": "#3584e4", "teal": "#2190a4", "green": "#3a944a", "yellow": "#c88800",
    "orange": "#ed5b00", "red": "#e62d42", "pink": "#d56199", "purple": "#9141ac",
    "slate": "#6f8396", "brown": "#986a44",
}

# Omarchy themes name Yaru icon colours; Colloid's matching colour variant.
YARU_TO_COLLOID = {
    "": "Orange", "blue": "", "purple": "Purple", "magenta": "Pink", "red": "Red",
    "yellow": "Yellow", "olive": "Green", "sage": "Grey", "prussiangreen": "Teal",
    "wartybrown": "Orange", "bark": "Orange", "viridian": "Teal",
}
COLLOID_HUES = {  # rough hue of each Colloid variant's folder colour (OKLCH degrees)
    "": 258, "Purple": 310, "Pink": 355, "Red": 25, "Orange": 50, "Yellow": 95,
    "Green": 145, "Teal": 190,
}


def nearest_accent(hexcolor):
    if not cm.is_hex(hexcolor):
        return "blue"
    L, C, h = cm.oklch(hexcolor)
    if C < 0.035:
        return "slate"
    best, score = "blue", 1e9
    for name, ref in ACCENTS.items():
        if name == "slate":
            continue
        rL, rC, rh = cm.oklch(ref)
        # Hue matters most; brown is the dark, low-chroma orange.
        d = cm.hue_distance(h, rh) / 30 + abs(C - rC) * 3 + abs(L - rL) * 0.8
        if d < score:
            best, score = name, d
    return best


def icon_installed(name, paths):
    dirs = [paths.data / "icons", paths.home / ".icons", Path("/usr/share/icons"),
            Path("/usr/local/share/icons")]
    return bool(name) and re.fullmatch(r"[A-Za-z0-9._+-]+", name) is not None and any(
        (d / name / "index.theme").is_file() for d in dirs)


def colloid_name(colour, mode):
    return "Colloid" + (f"-{colour}" if colour else "") + ("-Dark" if mode == "dark" else "-Light")


def choose_icons(theme_icons, accent, mode, settings, paths, pinned=None):
    """The icon theme for a theme, following settings [icons] style."""
    if pinned and icon_installed(pinned, paths):
        return pinned
    style = settings.get("icons", {}).get("style", "colloid")
    name = (theme_icons or "").strip()
    if style == "colloid":
        colour = None
        m = re.fullmatch(r"Yaru(?:-([a-z]+))?(?:-dark)?", name)
        if m:
            colour = YARU_TO_COLLOID.get(m.group(1) or "")
        elif name.startswith("Colloid"):
            base = re.sub(r"-(Dark|Light)$", "", name)
            candidate = f"{base}-{'Dark' if mode == 'dark' else 'Light'}"
            if icon_installed(candidate, paths):
                return candidate
        if colour is None and not name and cm.is_hex(accent):
            L, C, h = cm.oklch(accent)
            colour = "Grey" if C < 0.04 else min(COLLOID_HUES, key=lambda k: cm.hue_distance(h, COLLOID_HUES[k]))
        if colour is not None:
            for candidate in (colloid_name(colour, mode), colloid_name("Orange", mode)):
                if icon_installed(candidate, paths):
                    return candidate
    if name and icon_installed(name, paths):
        if mode == "dark" and name.startswith("Yaru") and not name.endswith("-dark") and icon_installed(name + "-dark", paths):
            return name + "-dark"
        return name
    return None


def gnome_settings(ctx):
    """color-scheme, accent and wallpaper, straight through gsettings."""
    if not util.session_bus_ok():
        return  # the sandbox without its own session bus
    g = ctx.gnome
    util.gset(IFACE, "color-scheme", g["color_scheme"])
    if g.get("accent"):
        util.gset(IFACE, "accent-color", g["accent"])
    if g.get("background"):
        uri = Path(g["background"]).as_uri()
        util.gset(BG, "picture-uri", uri)
        util.gset(BG, "picture-uri-dark", uri)
        util.gset(SCREENSAVER, "picture-uri", uri)


def dbus_call(method, *args, timeout=4):
    util._bus_guard()
    cmd = ["gdbus", "call", "--session", "--dest", DBUS_DEST, "--object-path", DBUS_PATH,
           "--method", f"{DBUS_IFACE}.{method}", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def shell_available():
    try:
        r = dbus_call("Ping", timeout=2)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def shell(ctx):
    """The rice-shell extension swaps the shell stylesheet and applies the colour
    scheme, accent and wallpaper in the same frame. Without it, gsettings does the
    settings and the shell keeps its stylesheet."""
    if not util.session_bus_ok():
        return  # the sandbox without its own session bus
    try:
        r = dbus_call("ApplyTheme", ctx.generation)
        if r.returncode == 0:
            return
        err = r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        err = str(e)
    gnome_settings(ctx)
    if "UnknownMethod" not in err and "ServiceUnknown" not in err and "No such interface" not in err \
            and "Object does not exist" not in err and "UnknownObject" not in err:
        raise RuntimeError(f"rice-shell: {err}")


def extras(ctx):
    """Icons, the GTK3 theme and the window-border extensions."""
    if not util.session_bus_ok():
        return  # the sandbox without its own session bus
    g = ctx.gnome
    accent = ctx.colors.get("accent", "#888888")
    if g.get("icon_theme"):
        util.gset(IFACE, "icon-theme", g["icon_theme"])
    util.gset(IFACE, "gtk-theme", g.get("gtk_theme") or ("Yaru-dark" if ctx.mode == "dark" else "Yaru"))

    r, gg, b = cm.to_rgb(accent)
    ext = "/org/gnome/shell/extensions"
    util.dset(f"{ext}/p7-borders/default-active-color", f"rgba({r}, {gg}, {b}, 0.5)")
    util.dset(f"{ext}/tilingshell/window-border-color", accent)
    util.dset(f"{ext}/tiling-assistant/focus-hint-color", f"rgb({r},{gg},{b})")
    rwc = f"{ext}/rounded-window-corners-reborn"
    if ctx.mode == "dark":
        util.dset(f"{rwc}/focused-shadow", "{'horizontalOffset': 0, 'verticalOffset': 4, 'blurOffset': 28, 'spreadRadius': 4, 'opacity': 60}")
        util.dset(f"{rwc}/unfocused-shadow", "{'horizontalOffset': 0, 'verticalOffset': 2, 'blurOffset': 12, 'spreadRadius': -1, 'opacity': 65}")
    else:
        # Softer shadows: the dark ones look muddy on light backgrounds.
        util.dset(f"{rwc}/focused-shadow", "{'horizontalOffset': 0, 'verticalOffset': 3, 'blurOffset': 22, 'spreadRadius': 1, 'opacity': 22}")
        util.dset(f"{rwc}/unfocused-shadow", "{'horizontalOffset': 0, 'verticalOffset': 2, 'blurOffset': 10, 'spreadRadius': -1, 'opacity': 18}")


def gtk(ctx):
    """GTK user CSS. GTK reads it at startup; gtk4.css carries both the dark and the
    light theme of the pair in prefers-color-scheme blocks, so open GTK4 apps
    follow Dark Style live and pick up a new palette on their next launch."""
    for name, target in (("gtk4.css", ctx.paths.config / "gtk-4.0" / "gtk.css"),
                         ("gtk3.css", ctx.paths.config / "gtk-3.0" / "gtk.css")):
        src = ctx.file(name)
        if src:
            util.install_file(src, target)
    dark = ctx.paths.config / "gtk-4.0" / "gtk-dark.css"
    if not dark.exists() and not dark.is_symlink():
        dark.symlink_to("gtk.css")
