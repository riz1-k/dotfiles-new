"""rice: Omarchy-style themes for this GNOME desktop.

  rice theme list | current | set <name> | next | prev | picker | refresh
  rice theme install <git-url> | remove [name] | update [name...]
  rice theme import-omarchy [name... | --all | --list]
  rice theme new <name> [--from <theme>] [--image <file>]
  rice theme preview [name]
  rice bg next | prev | set <file> | picker | open | list
  rice mode toggle | dark | light | status
  rice doctor
  rice settings
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import activate, backgrounds, library, previews, settings as settings_mod, themes
from . import paths as paths_mod
from .apps import gnome as gnome_app


def die(msg, code=1):
    print(f"rice: {msg}", file=sys.stderr)
    sys.exit(code)


def _name(args):
    return " ".join(args.name) if isinstance(args.name, list) else args.name


def _apply(name, args=None):
    failed = activate.set_theme(name, wait=getattr(args, "wait", None) or None)
    return 1 if failed else 0


def _menu(items, prompt):
    """A numbered menu for the terminal fallback of the pickers."""
    if not sys.stdin.isatty():
        die("the picker needs the rice-shell extension (or a terminal)")
    for i, (label, _) in enumerate(items, 1):
        print(f"{i:3}  {label}")
    try:
        pick = input(f"{prompt} [1-{len(items)}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if pick.isdigit() and 1 <= int(pick) <= len(items):
        return items[int(pick) - 1][1]
    matches = [v for label, v in items if pick.lower() in label.lower()]
    return matches[0] if len(matches) == 1 else None


# ---- theme -------------------------------------------------------------------------

def theme_list(args):
    paths = paths_mod.get()
    rows = previews.theme_rows(paths, make=args.thumbs)
    if args.json:
        print(previews.rows_json(rows))
        return 0
    if args.names:
        print("\n".join(r["name"] for r in rows))
        return 0
    w = max((len(r["name"]) for r in rows), default=10)
    for r in rows:
        origin = r["origin"] + (" (git)" if r["git"] else "")
        print(f"{'*' if r['current'] else ' '} {r['name']:<{w}}  {r['mode']:<5}  {origin}")
    return 0


def theme_current(args):
    name = themes.current_name(paths_mod.get())
    if not name:
        return 1
    print(themes.display_name(name) if args.display else name)
    return 0


def theme_set(args):
    return _apply(_name(args), args)


def theme_step(offset):
    def run(args):
        paths = paths_mod.get()
        names = list(themes.all_themes(paths))
        if not names:
            die("no themes")
        cur = themes.current_name(paths)
        i = names.index(cur) if cur in names else -offset
        return _apply(names[(i + offset) % len(names)], args)
    return run


def theme_picker(args):
    if not args.terminal:
        try:
            if gnome_app.dbus_call("OpenThemePicker").returncode == 0:
                return 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    paths = paths_mod.get()
    cur = themes.current_name(paths)
    items = [(("* " if n == cur else "  ") + t.display + f"  ({t.mode})", n)
             for n, t in themes.all_themes(paths).items()]
    pick = _menu(items, "Theme")
    return _apply(pick, args) if pick else 1


def theme_refresh(args):
    failed = activate.refresh(wait=args.wait or None)
    return 1 if failed else 0


def theme_install(args):
    name = library.install(args.url, force=args.force)
    print(f"Installed {name}")
    return 0 if args.no_set else _apply(name, args)


def theme_remove(args):
    paths = paths_mod.get()
    name = _name(args) if args.name else None
    if not name:
        items = [(t.display + f"  ({'git' if t.git else t.origin})", n)
                 for n, t in themes.all_themes(paths).items() if library.removable(t)]
        if not items:
            die("no installed or imported themes to remove")
        name = _menu(items, "Remove")
        if not name:
            return 1
    theme = themes.find(paths, name)
    if theme and not args.yes and sys.stdin.isatty():
        if input(f"Remove {theme.display}? [y/N] ").strip().lower() not in ("y", "yes"):
            return 1
    switched = library.remove(name)
    print(f"Removed {themes.normalize(name)}" + (f"; switched to {switched}" if switched else ""))
    return 0


def theme_update(args):
    result = library.update(args.name or None)
    if not result:
        print("No git-installed themes.")
    for name, status in result.items():
        print(f"{name}: {status}")
    cur = themes.current_name(paths_mod.get())
    if result.get(cur) == "updated":
        activate.refresh()
    return 1 if any(s.startswith("failed") for s in result.values()) else 0


def theme_import(args):
    if args.list:
        print("\n".join(library.omarchy_available(args.ref)))
        return 0
    if not args.name and not args.all:
        names = library.omarchy_available(args.ref)
        print("Omarchy's themes:\n  " + "\n  ".join(names))
        print("\nrice theme import-omarchy <name...>  or  --all")
        return 0
    done = library.import_omarchy(None if args.all else args.name, args.ref)
    for src, dest in done:
        print(f"imported {src}" + (f" as {dest}" if dest != src else ""))
    previews.warm(paths_mod.get())
    return 0


def theme_new(args):
    d, origin = library.new(_name(args), base=args.base, image=args.image, light=args.light,
                            extract_mode=args.extract_mode)
    print(f"Created {d} (palette: {origin})\nEdit {d / 'colors.toml'}, then: rice theme set {d.name}")
    if args.image and not args.base and not library.aether():
        print("Install Aether (github.com/bjarneo/aether) to get the palette from the image.")
    if args.edit:
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nvim"
        subprocess.run([editor, str(d / "colors.toml")])
    return 0


def theme_preview(args):
    paths = paths_mod.get()
    name = _name(args) if args.name else themes.current_name(paths)
    t = themes.find(paths, name or "")
    if t is None:
        die(f"Theme '{name}' does not exist")
    colors = t.palette()
    if not colors:
        die(f"{t.name} has no colors.toml")
    if args.image:
        bgs = t.backgrounds(paths)
        out = previews.render_image(colors, bgs[0] if bgs else None, Path(args.image).expanduser())
        print(out)
    elif args.json:
        print(json.dumps(dict(sorted(colors.items())), indent=1))
    else:
        print(previews.ramp(t.name, colors))
    return 0


# ---- bg --------------------------------------------------------------------------------

def _current_theme(paths):
    t = themes.find(paths, themes.current_name(paths))
    if t is None:
        die("no theme set (rice theme set <name>)")
    return t


def bg_step(offset):
    def run(args):
        paths = paths_mod.get()
        p = backgrounds.step(paths, _current_theme(paths), offset)
        if p is None:
            die("this theme has no backgrounds")
        activate.set_background(p)
        return 0
    return run


def bg_set(args):
    activate.set_background(args.file)
    return 0


def bg_list(args):
    paths = paths_mod.get()
    rows = previews.background_rows(paths, _current_theme(paths), make=args.thumbs)
    if args.json:
        print(previews.rows_json(rows))
    else:
        for r in rows:
            print(("* " if r["current"] else "  ") + r["path"])
    return 0


def bg_picker(args):
    if not args.terminal:
        try:
            if gnome_app.dbus_call("OpenBackgroundPicker").returncode == 0:
                return 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    paths = paths_mod.get()
    rows = previews.background_rows(paths, _current_theme(paths))
    pick = _menu([(("* " if r["current"] else "  ") + r["name"], r["path"]) for r in rows], "Background")
    if pick:
        activate.set_background(pick)
    return 0 if pick else 1


def bg_open(args):
    paths = paths_mod.get()
    d = paths.user_backgrounds / _current_theme(paths).name
    d.mkdir(parents=True, exist_ok=True)
    print(d)
    subprocess.Popen(["xdg-open", str(d)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return 0


# ---- mode ------------------------------------------------------------------------------

def mode_cmd(args):
    from . import modewatch
    paths = paths_mod.get()
    settings = settings_mod.load(paths)
    have = modewatch.theme_mode(paths) or "dark"
    if args.action == "status":
        pair = activate.pairs(paths, settings)
        print(f"{have} ({themes.current_name(paths)}); dark = {pair.get('dark')}, light = {pair.get('light')}")
        return 0
    want = {"toggle": "light" if have == "dark" else "dark"}.get(args.action, args.action)
    target = modewatch.target_for(paths, settings, want)
    if not target:
        die(f"no {want} theme installed")
    if target == themes.current_name(paths):
        return 0
    return _apply(target, args)


def mode_watch(args):
    from . import modewatch
    modewatch.run()


def retint(args):
    paths = paths_mod.get()
    failed = activate.other_group(paths, args.generation, detached=True)
    return 1 if failed else 0


def backup_targets(args):
    """Every file a retint edits, NUL-separated (install.sh backs them up)."""
    from . import backup
    for f in backup.targets(paths_mod.get()):
        sys.stdout.write(f"{f}\0")
    return 0


def apply_only(args):
    """Re-run some retints against the current theme (debugging / after editing an app config)."""
    paths = paths_mod.get()
    settings = settings_mod.load(paths)
    from . import apps
    unknown = set(args.apps) - set(apps.ALL)
    if unknown:
        die(f"unknown apps: {', '.join(sorted(unknown))} (known: {', '.join(apps.ALL)})")
    # Both locks: neither a switch nor a background batch can run alongside.
    with activate.locked(paths.lock), activate.locked(paths.retint_lock):
        ctx = activate.context(paths, settings, activate.current_generation(paths))
        failed = activate.run_group(ctx, apps.VISIBLE + apps.OTHER, only=set(args.apps))
    return 1 if failed else 0


def doctor(args):
    from . import doctor as doc
    text, rows = doc.report(paths_mod.get(), as_json=args.json)
    print(text)
    return 1 if any(s == doc.FAIL for s, _, _ in rows) else 0


def settings_cmd(args):
    paths = paths_mod.get()
    if not paths.settings.is_file():
        paths.settings.parent.mkdir(parents=True, exist_ok=True)
        paths.settings.write_text(settings_mod.TEMPLATE)
    print(paths.settings)
    return 0


# ---- parser ----------------------------------------------------------------------------

def parser():
    p = argparse.ArgumentParser(prog="rice", description="Omarchy-style themes for GNOME.")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="{theme,bg,mode,doctor,settings,apply,mode-watch}")

    t = sub.add_parser("theme", help="list, set and manage themes").add_subparsers(dest="action", required=True)
    s = t.add_parser("list", help="every theme (* = current)")
    s.add_argument("--json", action="store_true")
    s.add_argument("--names", action="store_true")
    s.add_argument("--thumbs", action="store_true", help="make missing picker thumbnails")
    s.set_defaults(fn=theme_list)
    s = t.add_parser("current")
    s.add_argument("--display", action="store_true", help="the display name (Tokyo Night)")
    s.set_defaults(fn=theme_current)
    s = t.add_parser("set", help="switch theme (display names work: rice theme set Tokyo Night)")
    s.add_argument("name", nargs="+")
    s.add_argument("--wait", action="store_true", help="wait for every app, not just what's on screen")
    s.set_defaults(fn=theme_set)
    for action, offset in (("next", 1), ("prev", -1)):
        s = t.add_parser(action)
        s.add_argument("--wait", action="store_true")
        s.set_defaults(fn=theme_step(offset))
    s = t.add_parser("picker", help="the theme carousel (Super+Ctrl+Shift+Space)")
    s.add_argument("--terminal", action="store_true")
    s.add_argument("--wait", action="store_true")
    s.set_defaults(fn=theme_picker)
    s = t.add_parser("refresh", help="re-apply the current theme (after editing it)")
    s.add_argument("--wait", action="store_true")
    s.set_defaults(fn=theme_refresh)
    s = t.add_parser("install", help="clone an Omarchy theme repo and switch to it")
    s.add_argument("url")
    s.add_argument("--force", action="store_true", help="replace your own theme of the same name")
    s.add_argument("--no-set", action="store_true")
    s.add_argument("--wait", action="store_true")
    s.set_defaults(fn=theme_install)
    s = t.add_parser("remove", help="remove an installed or imported theme")
    s.add_argument("name", nargs="*")
    s.add_argument("--yes", "-y", action="store_true")
    s.set_defaults(fn=theme_remove)
    s = t.add_parser("update", help="git pull installed themes")
    s.add_argument("name", nargs="*")
    s.set_defaults(fn=theme_update)
    s = t.add_parser("import-omarchy", help="bring in Omarchy's own themes (pinned commit)")
    s.add_argument("name", nargs="*")
    s.add_argument("--all", action="store_true")
    s.add_argument("--list", action="store_true")
    s.add_argument("--ref", help="another basecamp/omarchy commit")
    s.set_defaults(fn=theme_import)
    s = t.add_parser("new", help="start a theme of your own in ~/.config/rice/themes")
    s.add_argument("name", nargs="+")
    s.add_argument("--from", dest="base", help="theme to copy the palette from (default: current)")
    s.add_argument("--image", help="wallpaper for its backgrounds/; with Aether installed (and no --from), "
                                   "the palette is extracted from it")
    s.add_argument("--light", action="store_true", help="with --image: extract a light palette")
    s.add_argument("--extract-mode", metavar="MODE",
                   help="with --image: Aether's extraction mode (normal, pastel, colorful, muted, ...)")
    s.add_argument("--edit", action="store_true", help="open colors.toml in $EDITOR")
    s.set_defaults(fn=theme_new)
    s = t.add_parser("preview", help="draw a theme's palette in the terminal")
    s.add_argument("name", nargs="*")
    s.add_argument("--json", action="store_true", help="the resolved palette")
    s.add_argument("--image", metavar="FILE", help="draw a preview.png (wallpaper + palette) to FILE")
    s.set_defaults(fn=theme_preview)

    b = sub.add_parser("bg", help="wallpapers of the current theme").add_subparsers(dest="action", required=True)
    b.add_parser("next").set_defaults(fn=bg_step(1))
    b.add_parser("prev").set_defaults(fn=bg_step(-1))
    s = b.add_parser("set")
    s.add_argument("file")
    s.set_defaults(fn=bg_set)
    s = b.add_parser("picker", help="the background carousel (Super+Ctrl+Space)")
    s.add_argument("--terminal", action="store_true")
    s.set_defaults(fn=bg_picker)
    b.add_parser("open", help="open the folder for your own wallpapers for this theme").set_defaults(fn=bg_open)
    s = b.add_parser("list")
    s.add_argument("--json", action="store_true")
    s.add_argument("--thumbs", action="store_true")
    s.set_defaults(fn=bg_list)

    s = sub.add_parser("mode", help="switch to the paired dark or light theme")
    s.add_argument("action", choices=["toggle", "dark", "light", "status"])
    s.add_argument("--wait", action="store_true")
    s.set_defaults(fn=mode_cmd)

    sub.add_parser("mode-watch", help="follow GNOME's Dark Style toggle (the systemd service)").set_defaults(fn=mode_watch)
    s = sub.add_parser("doctor", help="check that every app is wired up")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=doctor)
    sub.add_parser("settings", help="create/print ~/.config/rice/settings.toml").set_defaults(fn=settings_cmd)
    s = sub.add_parser("apply", help="re-run some app retints for the current theme")
    s.add_argument("apps", nargs="+")
    s.set_defaults(fn=apply_only)
    sub.add_parser("_backup-targets").set_defaults(fn=backup_targets)  # for install.sh
    s = sub.add_parser("_retint")  # the detached second group of a switch
    s.add_argument("generation", nargs="?", default="")
    s.set_defaults(fn=retint)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return args.fn(args) or 0
    except (activate.ThemeError, library.LibraryError) as e:
        die(str(e))
    except KeyboardInterrupt:
        return 130
