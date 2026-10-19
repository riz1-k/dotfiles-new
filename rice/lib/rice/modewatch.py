"""rice mode-watch: keep GNOME's Dark Style toggle working (rice-mode-watch.service).

The theme is the master: setting a theme writes color-scheme from its mode. When
color-scheme changes and no longer matches the current theme's mode, someone flipped
Dark Style (Quick Settings, Settings > Appearance, an auto-dark extension), so switch
to the remembered theme for that mode. rice's own writes already match, and while a
switch is running rice holds a flag file (set before the new theme is visible); the
watcher waits for it to clear, compares the real state, and checks again once it
holds the switch lock, so there's no loop and no race with a switch in flight.
"""
import json
import subprocess
import sys
import time

from . import activate, settings as settings_mod, themes, util
from . import paths as paths_mod
from .apps.gnome import IFACE

FLAG_MAX_AGE = 20  # seconds; a crashed switch can't block the watcher for longer


def scheme_mode():
    value = (util.gget(IFACE, "color-scheme") or "").strip("'")
    return "dark" if value == "prefer-dark" else "light"


def theme_mode(paths):
    try:
        return json.loads((paths.current_theme / "colors.json").read_text()).get("mode", "dark")
    except (OSError, json.JSONDecodeError):
        t = themes.find(paths, themes.current_name(paths))
        return t.mode if t else None


def target_for(paths, settings, mode):
    pair = activate.pairs(paths, settings).get(mode)
    all_ = themes.all_themes(paths)
    if pair in all_ and all_[pair].mode == mode:
        return pair
    return next((n for n, t in all_.items() if t.mode == mode), None)


def wait_for_flag(paths):
    flag = paths.mode_watch_flag
    while flag.exists():
        try:
            if time.time() - flag.stat().st_mtime > FLAG_MAX_AGE:
                return
        except OSError:
            return
        time.sleep(0.1)


def reconcile(paths, verbose=True):
    settings = settings_mod.load(paths)
    if not settings["mode"].get("follow_toggle", True):
        return None
    wait_for_flag(paths)
    want = scheme_mode()
    have = theme_mode(paths)
    if have is None or want == have:
        return None
    target = target_for(paths, settings, want)
    if not target:
        if verbose:
            print(f"rice mode-watch: no {want} theme to switch to", file=sys.stderr)
        return None
    if verbose:
        print(f"rice mode-watch: Dark Style is now {want}: switching to {target}", file=sys.stderr)

    def still_needed():
        # Checked again under the switch lock: a switch that was running while the
        # state above was read has finished by then, and may have settled it.
        have_now = theme_mode(paths)
        return scheme_mode() == want and have_now is not None and have_now != want

    try:
        activate.set_theme(target, wait=False, only_if=still_needed)
    except Exception as e:  # noqa: BLE001 - keep watching
        print(f"rice mode-watch: {e}", file=sys.stderr)
    return target


def run():
    paths = paths_mod.get()
    reconcile(paths)  # something may have changed while the watcher was down
    while True:
        proc = subprocess.Popen(["gsettings", "monitor", IFACE, "color-scheme"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            for _ in proc.stdout:
                time.sleep(0.4)  # Ubuntu rewrites the gtk/icon themes right after the scheme flips: let it finish
                reconcile(paths)
        finally:
            proc.kill()
        time.sleep(2)  # gsettings monitor died (dconf restart?): start again
