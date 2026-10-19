"""Setting a theme: a port of omarchy-theme-set's flow.

 1. Take the lock, so quick successive switches queue instead of racing.
 2. Remember the outgoing theme's wallpaper.
 3. Stage next-theme (stock/imported copy, user overlay, git filter, alacritty fallback).
 4. Render the templates; build gnome-shell.css, gnome.json, colors.json and the
    dual-mode files; choose the wallpaper.
 5. Swap next-theme in as current/theme, write theme.name and theme.generation.
 6. Release the lock.
 7. Run the visible group in parallel (inside a shell cross-fade) and wait for it.
 8. Run the other group: in a detached process unless run from a terminal or with
    RICE_THEME_WAIT=1. Batches run one at a time and a batch whose theme was
    replaced in the meantime skips its retints.
 9. Run the hooks, log failures and notify about them.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from . import backgrounds, palette, render, settings as settings_mod, shellcss, stage, themes, util
from . import apps
from . import paths as paths_mod
from .apps import gnome as gnome_app

# Files that carry both themes of the dark/light pair (see make_dual).
DUAL = ("gtk4.css", "quickCss.css", "userChrome.css", "userContent.css")


class ThemeError(Exception):
    pass


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def put(path, text):
    """Replace a staged file. Staged files can be hardlinks or symlinks into a theme
    folder, so they are never written in place."""
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def log(paths, message):
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    with open(paths.log, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {message}\n")


# ---- mode pairs -----------------------------------------------------------------

def pairs(paths, settings):
    pair = {"dark": settings["mode"]["dark"], "light": settings["mode"]["light"]}
    try:
        pair.update(json.loads(paths.mode_pairs.read_text()))
    except (OSError, json.JSONDecodeError):
        pass
    return pair


def remember_pair(paths, mode, name):
    pair = {}
    try:
        pair = json.loads(paths.mode_pairs.read_text())
    except (OSError, json.JSONDecodeError):
        pass
    if pair.get(mode) != name:
        pair[mode] = name
        util.atomic_write(paths.mode_pairs, json.dumps(pair, indent=2) + "\n")


# ---- rendering -------------------------------------------------------------------

def templates(paths):
    return render.template_files(paths.user_templates, paths.templates)


def render_theme(paths, theme, out_dir, colors):
    extra = {"rice_theme": theme.name, "rice_theme_name": theme.display}
    return render.render_into(out_dir, colors, templates(paths), extra)


def _other_mode_block(paths, settings, name, mode, filename, colors_cache):
    """filename's content for the paired theme of the other mode (for dual files)."""
    other = "light" if mode == "dark" else "dark"
    pair_name = pairs(paths, settings).get(other)
    theme = themes.find(paths, pair_name) if pair_name else None
    if theme is None or theme.name == name:
        return None
    if theme.trusted:
        shipped = theme.file(filename)
        if shipped:
            return shipped.read_text()
    colors = colors_cache.get(theme.name) or theme.palette()
    if not colors or colors.get("mode") != other:
        return None
    for tpl in templates(paths):
        if tpl.name == filename + ".tpl":
            r = render.Renderer(colors, {"rice_theme": theme.name, "rice_theme_name": theme.display})
            return r.text(tpl.read_text())
    return None


def _wrap(css, mode):
    return f"@media (prefers-color-scheme: {mode}) {{\n{css.rstrip()}\n}}\n"


def make_dual(paths, settings, theme, next_dir, colors):
    """GTK4, Vencord, Zen and widget CSS carry both themes of the pair, so apps that
    only re-read on Dark Style changes flip to the right palette live."""
    mode = colors["mode"]
    cache = {}
    for filename in DUAL:
        f = next_dir / filename
        if not f.is_file():
            continue
        own = f.read_text()
        if "prefers-color-scheme" in own:
            continue  # the theme ships its own dual file
        other = _other_mode_block(paths, settings, theme.name, mode, filename, cache)
        text = f"/* rice: {theme.name} ({mode})" + (" + its pair for the other mode" if other else "") + " */\n"
        text += _wrap(own, mode)
        if other:
            text += _wrap(other, "light" if mode == "dark" else "dark")
        else:
            text += _wrap(own, "light" if mode == "dark" else "dark")
        put(f, text)


def gnome_json(paths, settings, theme, next_dir, colors, background):
    mode = colors["mode"]
    pins = {}
    gnome_toml = next_dir / "gnome.toml"
    if gnome_toml.is_file():
        import tomllib
        try:
            pins = tomllib.loads(gnome_toml.read_text())
        except tomllib.TOMLDecodeError:
            pins = {}
    accent = pins.get("accent") if pins.get("accent") in gnome_app.ACCENTS else gnome_app.nearest_accent(colors.get("accent"))
    icons_file = next_dir / "icons.theme"
    theme_icons = icons_file.read_text().strip().splitlines()[0] if icons_file.is_file() and icons_file.read_text().strip() else ""
    icon_theme = gnome_app.choose_icons(theme_icons, colors.get("accent"), mode, settings, paths,
                                        pinned=pins.get("icons") if isinstance(pins.get("icons"), str) else None)
    return {
        "name": theme.name,
        "display": theme.display,
        "mode": mode,
        "color_scheme": "prefer-dark" if mode == "dark" else "prefer-light",
        "accent": accent,
        "accent_hex": colors.get("accent"),
        "icon_theme": icon_theme,
        "gtk_theme": "Yaru-dark" if mode == "dark" else "Yaru",
        "background": str(background) if background else None,
        "stylesheet": str(paths.current_theme / "gnome-shell.css"),
        "transition": bool(settings.get("shell", {}).get("transition", True)),
        "extra_css": pins.get("css", "") if isinstance(pins.get("css"), str) else "",
    }


def build(paths, settings, theme, previous, keep_background=False):
    """Stage and render next-theme. Returns (colors, background, ignored files)."""
    ignored = stage.stage(theme, paths.next_theme)
    warnings = []
    colors = palette.load(paths.next_theme, warnings)
    if not colors:
        raise ThemeError(f"theme '{theme.name}' has no colors.toml (or alacritty.toml to make one from)")
    render_theme(paths, theme, paths.next_theme, colors)
    make_dual(paths, settings, theme, paths.next_theme, colors)
    background = backgrounds.current(paths) if keep_background else None
    if background is None:
        background = backgrounds.choose(paths, theme, previous, staged_dir=paths.next_theme)
    g = gnome_json(paths, settings, theme, paths.next_theme, colors, background)
    # Shell stylesheet: recoloured Yaru + the bar (+ the theme's extra CSS).
    bar = paths.next_theme / "rice-bar.css"
    tail = (bar.read_text() if bar.is_file() else "") + "\n" + g.pop("extra_css", "")
    shell_css = paths.next_theme / "gnome-shell.css"
    if shell_css.is_file():
        # A (trusted) theme's own shell stylesheet: keep it, add the bar.
        css = shell_css.read_text(errors="replace") + "\n\n/* ---- rice additions ---- */\n" + tail
    else:
        css = shellcss.build(colors, colors["mode"], paths.cache_dir / "shell", tail)
    if css:
        put(shell_css, css)
    put(paths.next_theme / "gnome.json", json.dumps(g, indent=2) + "\n")
    put(paths.next_theme / "colors.json", json.dumps(dict(sorted(colors.items())), indent=2) + "\n")
    for w in warnings:
        print(f"rice: {theme.name}: {w}", file=sys.stderr)
    return colors, background, ignored


def swap(paths):
    if paths.current_theme.exists():
        old = paths.current / ".old-theme"
        if old.exists():
            shutil.rmtree(old)
        paths.current_theme.rename(old)
        paths.next_theme.rename(paths.current_theme)
        shutil.rmtree(old, ignore_errors=True)
    else:
        paths.next_theme.rename(paths.current_theme)


def write_generation(paths):
    gen = f"{os.getpid()}-{time.time_ns()}"
    try:
        util.atomic_write(paths.generation, gen + "\n")
    except OSError:
        return ""
    return gen


def current_generation(paths):
    try:
        return paths.generation.read_text().strip()
    except OSError:
        return ""


def context(paths, settings, generation, log_fn=print):
    d = paths.current_theme
    colors = json.loads((d / "colors.json").read_text()) if (d / "colors.json").is_file() else palette.load(d)
    g = json.loads((d / "gnome.json").read_text()) if (d / "gnome.json").is_file() else {}
    name = themes.current_name(paths)
    return apps.Context(paths=paths, settings=settings, name=name, display=themes.display_name(name),
                        colors=colors, mode=colors.get("mode", "dark"), dir=d, generation=generation,
                        background=Path(g["background"]) if g.get("background") else None,
                        gnome=g, log=log_fn)


def run_group(ctx, group, only=None):
    """Run a group's retints in parallel. Returns the names that failed."""
    jobs = [(n, fn) for n, key, fn in group
            if settings_mod.app_enabled(ctx.settings, key) and (only is None or n in only)]
    failed = []

    def one(item):
        n, fn = item
        t = time.monotonic()
        try:
            fn(ctx)
            return n, None, time.monotonic() - t
        except Exception as e:  # noqa: BLE001 - a retint must never take the switch down
            return n, f"{type(e).__name__}: {e}", time.monotonic() - t

    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        for n, err, secs in pool.map(one, jobs):
            if err:
                failed.append(n)
                log(ctx.paths, f"{n} failed after {secs:.2f}s: {err}")
                print(f"rice: {n}: {err}", file=sys.stderr)
            elif os.environ.get("RICE_DEBUG"):
                print(f"rice: {n} {secs * 1000:.0f}ms", file=sys.stderr)
    return failed


def run_hooks(paths, name):
    hooks = sorted(p for p in paths.hooks.glob("theme-set*") if p.is_file() and os.access(p, os.X_OK)) \
        if paths.hooks.is_dir() else []
    for hook in hooks:
        try:
            subprocess.run([str(hook), name], timeout=60, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(paths, f"hook {hook.name} failed: {e}")


def other_group(paths, generation, detached):
    """The background batch (also `rice _retint`)."""
    settings = settings_mod.load(paths)
    with locked(paths.retint_lock):
        still_current = not generation or current_generation(paths) == generation
        failed = []
        if still_current:
            ctx = context(paths, settings, generation)
            failed = run_group(ctx, apps.OTHER)
            warm_previews(paths)
    run_hooks(paths, themes.current_name(paths))
    if failed and (not generation or current_generation(paths) == generation):
        msg = f"Theme not applied everywhere: {', '.join(failed)} failed (see {paths.log})"
        print(f"rice: {msg}", file=sys.stderr)
        if detached:
            util.notify("Theme not applied everywhere", f"{', '.join(failed)} failed. Details: {paths.log}")
    return failed


def warm_previews(paths):
    try:
        from . import previews
        previews.warm(paths)
    except Exception as e:  # noqa: BLE001
        log(paths, f"preview cache: {e}")


def shell_transition(method):
    try:
        gnome_app.dbus_call(method, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        pass


def set_theme(name, wait=None, keep_background=False):
    paths_ = paths_mod.get()
    settings = settings_mod.load(paths_)
    norm = themes.normalize(name)
    if not themes.valid(norm):
        raise ThemeError(f"Invalid theme name: {name}")
    theme = themes.find(paths_, norm)
    if theme is None:
        raise ThemeError(f"Theme '{norm}' does not exist (rice theme list)")

    t0 = time.monotonic()
    transition = False
    with locked(paths_.lock):
        paths_.state_dir.mkdir(parents=True, exist_ok=True)
        paths_.log.write_text("")  # the log covers the latest switch only
        previous = themes.current_name(paths_)
        backgrounds.remember(paths_, previous, backgrounds.current(paths_))
        colors, background, ignored = build(paths_, settings, theme, previous, keep_background)
        if ignored:
            print(f"rice: ignored in {theme.user}: {' '.join(ignored)}", file=sys.stderr)
            print("rice: a theme installed from a git repo cannot supply code (Lua, terminal, "
                  "tmux, zsh or browser configs, scripts); those files are generated instead.", file=sys.stderr)
        # Snapshot the screen before anything on it changes; the shell fades the
        # snapshot out once the visible group is done (or after a timeout).
        if settings_mod.app_enabled(settings, "shell") and settings.get("shell", {}).get("transition", True) \
                and os.environ.get("RICE_NO_TRANSITION") != "1" and util.session_bus_ok():
            shell_transition("BeginTransition")
            transition = True
        swap(paths_)
        generation = write_generation(paths_)
        util.atomic_write(paths_.theme_name, theme.name + "\n")
        if background:
            backgrounds.link(paths_, background)
        remember_pair(paths_, colors["mode"], theme.name)
    # The lock only covers the shared staging and current paths; retints queue behind
    # their own lock, like Omarchy.
    ctx = context(paths_, settings, generation)
    failed = []
    # Tell the mode watcher the colour-scheme change it's about to see is ours.
    try:
        util.atomic_write(paths_.mode_watch_flag, generation + "\n")
    except OSError:
        pass
    try:
        failed = run_group(ctx, apps.VISIBLE)
    finally:
        if transition:
            shell_transition("EndTransition")
        try:
            paths_.mode_watch_flag.unlink()
        except OSError:
            pass
    visible_ms = (time.monotonic() - t0) * 1000
    log(paths_, f"{theme.name}: visible group done in {visible_ms:.0f}ms" + (f", failed: {failed}" if failed else ""))
    if os.environ.get("RICE_DEBUG"):
        print(f"rice: visible in {visible_ms:.0f}ms", file=sys.stderr)

    if wait is None:
        wait = sys.stdin.isatty() or os.environ.get("RICE_THEME_WAIT") == "1"
    if wait:
        failed += other_group(paths_, generation, detached=False)
    else:
        paths_.state_dir.mkdir(parents=True, exist_ok=True)
        rice_bin = Path(__file__).resolve().parents[2] / "bin" / "rice"
        with open(paths_.log, "a") as logf:
            subprocess.Popen([sys.executable, str(rice_bin), "_retint", generation],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=logf,
                             start_new_session=True, close_fds=True)
    return failed


def refresh(wait=None):
    """Re-apply the current theme without moving to its next wallpaper."""
    name = themes.current_name(paths_mod.get())
    if not name:
        raise ThemeError("No theme set yet (rice theme set <name>)")
    return set_theme(name, wait=wait, keep_background=True)


def set_background(path):
    """Switch wallpaper only (bg next / bg set / the background picker)."""
    paths_ = paths_mod.get()
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ThemeError(f"No such file: {path}")
    backgrounds.link(paths_, path)
    backgrounds.remember(paths_, themes.current_name(paths_), path)
    g_file = paths_.current_theme / "gnome.json"
    if g_file.is_file():
        g = json.loads(g_file.read_text())
        g["background"] = str(path)
        util.atomic_write(g_file, json.dumps(g, indent=2) + "\n")
    try:
        r = gnome_app.dbus_call("SetBackground", str(path))
        if r.returncode == 0:
            return
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not util.session_bus_ok():
        return
    uri = path.as_uri()
    util.gset(gnome_app.BG, "picture-uri", uri)
    util.gset(gnome_app.BG, "picture-uri-dark", uri)
    util.gset(gnome_app.SCREENSAVER, "picture-uri", uri)
