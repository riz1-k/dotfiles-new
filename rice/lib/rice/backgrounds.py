"""Wallpapers: which one a theme gets, and remembering it per theme (Omarchy's rules).

- Setting the theme that's already current moves to its next wallpaper.
- Switching to another theme brings back the wallpaper it had last time.
- Otherwise the theme's first wallpaper.

GNOME only reloads a wallpaper when its URI changes, so rice always hands GNOME the
wallpaper's real source file (unique per theme), never the copy in current/theme.
"""
import os
import time

from . import themes as themes_mod
from . import util


def candidates(paths, theme, staged_dir=None):
    """Every wallpaper for a theme, as source paths, in Omarchy's order."""
    extras = themes_mod.image_files(paths.user_backgrounds / theme.name)
    if staged_dir is not None:
        staged = themes_mod.image_files(staged_dir / "backgrounds")
        own = [source_of(theme, p) for p in staged]
    else:
        own = [p for p in theme.backgrounds(paths) if p not in extras]
    return extras + own


def source_of(theme, staged_file):
    """The theme folder's own copy of a staged wallpaper, if it's a plain file."""
    for d in reversed(theme.dirs):
        p = d / "backgrounds" / staged_file.name
        if p.is_file() and not p.is_symlink():
            return p
        if p.is_symlink() and theme.trusted and p.resolve().is_file():
            return p.resolve()
    return staged_file


def current(paths):
    link = paths.background_link
    try:
        target = link.resolve(strict=True)
        return target if target.is_file() else None
    except OSError:
        return None


def remembered(paths, name):
    if not themes_mod.valid(name):
        return None
    try:
        from pathlib import Path
        p = Path((paths.theme_backgrounds / name).read_text().strip())
        return p if p.is_file() else None
    except OSError:
        return None


def remember(paths, name, path):
    if not themes_mod.valid(name) or path is None:
        return
    util.atomic_write(paths.theme_backgrounds / name, f"{path}\n", follow=False)


def choose(paths, theme, previous_name, staged_dir=None):
    files = candidates(paths, theme, staged_dir)
    if not files:
        return None
    if previous_name == theme.name:
        now = current(paths)
        if now in files:
            return files[(files.index(now) + 1) % len(files)]
        return files[0]
    back = remembered(paths, theme.name)
    if back in files or (back is not None and back.is_file() and back.parent == paths.user_backgrounds / theme.name):
        return back
    return files[0]


def step(paths, theme, offset):
    """The wallpaper `offset` places from the current one (bg next / previous)."""
    files = candidates(paths, theme)
    if not files:
        return None
    now = current(paths)
    i = files.index(now) if now in files else -offset
    return files[(i + offset) % len(files)]


def link(paths, path):
    """Point current/background at path in one rename (the temp name is unique)."""
    paths.current.mkdir(parents=True, exist_ok=True)
    tmp = paths.current / f".background.{os.getpid()}.{time.time_ns()}"
    tmp.symlink_to(path)
    try:
        tmp.replace(paths.background_link)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
