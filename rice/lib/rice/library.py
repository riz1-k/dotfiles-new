"""The theme library: install from git, remove, update, import Omarchy's own
themes, and scaffold a new theme. Ports of omarchy-theme-install / -remove /
-update, with the same URL checks.

- Installed themes are git clones in ~/.config/rice/themes/<name>. They're staged
  through the filter (stage.py), so a repo can't run code on your machine.
- Omarchy's own themes come from a sparse checkout of basecamp/omarchy at a pinned
  commit and live in ~/.local/share/rice/themes (outside dotfiles: wallpaper
  licences vary). A name that clashes with a stock rice theme gets "-omarchy".
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import paths as paths_mod
from . import settings as settings_mod
from . import themes as themes_mod

OMARCHY_REPO = "https://github.com/basecamp/omarchy.git"
OMARCHY_COMMIT = "81fd2d23ca6e3462183a4dc8360de3113fa8d80c"  # 2026-10-18


class LibraryError(Exception):
    pass


def _git(*args, cwd=None, timeout=600):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    cmd = ["git", "-c", "protocol.ext.allow=never", "-c", "core.hooksPath=/dev/null", *args]
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise LibraryError(f"git {args[0]}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r


def _is_theme(d):
    return (d / "colors.toml").is_file() or (d / "alacritty.toml").is_file()


# ---- install / remove / update ---------------------------------------------------

def install(url, force=False):
    """Clone a theme repo. Returns the theme name."""
    url = (url or "").strip()
    err = themes_mod.check_git_url(url)
    if err:
        raise LibraryError(err)
    name = themes_mod.install_name(url)
    if not name:
        raise LibraryError(f"Can't make a theme name from '{url}'")
    paths = paths_mod.get()
    dest = paths.user_themes / name
    if dest.exists() or dest.is_symlink():
        existing = themes_mod.Theme(name=name, user=dest)
        if not existing.git and not force:
            raise LibraryError(f"{dest} is your own theme (not a git clone). Move it away or use --force.")
    paths.user_themes.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".install-{name}-", dir=paths.user_themes))
    try:
        _git("clone", "--depth", "1", "--", url, str(tmp / "repo"))
        repo = tmp / "repo"
        if not _is_theme(repo):
            raise LibraryError(f"'{url}' has no colors.toml or alacritty.toml at its top level: not an Omarchy theme")
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        repo.rename(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return name


def removable(theme):
    return theme is not None and (theme.git or theme.origin == "omarchy")


def remove(name):
    """Remove a git-installed or imported theme. Returns the theme switched to, if the
    removed theme was the current one."""
    from . import activate
    paths = paths_mod.get()
    theme = themes_mod.find(paths, name)
    if theme is None:
        raise LibraryError(f"Theme '{themes_mod.normalize(name)}' does not exist")
    if not removable(theme):
        what = "a stock rice theme" if theme.origin == "stock" else f"your own theme ({theme.user})"
        raise LibraryError(f"'{theme.name}' is {what}; rice only removes themes it installed or imported.")
    switch_to = None
    if themes_mod.current_name(paths) == theme.name:
        mode = theme.mode
        settings = settings_mod.load(paths)
        pair = activate.pairs(paths, settings)
        candidates = [pair.get(mode), pair.get("dark"), pair.get("light")]
        others = [t for t in themes_mod.all_themes(paths) if t != theme.name]
        switch_to = next((c for c in candidates if c and c != theme.name and c in others), others[0] if others else None)
    if theme.git:
        shutil.rmtree(theme.user)
    if theme.origin == "omarchy" and theme.base and theme.base.is_relative_to(paths.imported_themes):
        shutil.rmtree(theme.base)
    if switch_to:
        activate.set_theme(switch_to)
    return switch_to


def update(names=None):
    """git pull every installed theme (or the named ones). Returns {name: status}."""
    paths = paths_mod.get()
    result = {}
    for name, theme in themes_mod.all_themes(paths).items():
        if not theme.git or (names and name not in {themes_mod.normalize(n) for n in names}):
            continue
        try:
            before = _git("rev-parse", "HEAD", cwd=theme.user).stdout.strip()
            _git("pull", "--ff-only", "--depth", "1", cwd=theme.user, timeout=300)
            after = _git("rev-parse", "HEAD", cwd=theme.user).stdout.strip()
            result[name] = "updated" if before != after else "up to date"
        except (LibraryError, subprocess.TimeoutExpired) as e:
            result[name] = f"failed: {e}"
    return result


# ---- Omarchy's themes ---------------------------------------------------------------

def omarchy_checkout(ref=None):
    """A sparse checkout of basecamp/omarchy's themes/ folder at the pinned commit."""
    paths = paths_mod.get()
    repo = os.environ.get("RICE_OMARCHY_REPO", OMARCHY_REPO)
    err = themes_mod.check_git_url(repo)
    if err:
        raise LibraryError(err)
    ref = ref or OMARCHY_COMMIT
    if ref.startswith("-"):
        raise LibraryError(f"bad ref: {ref}")
    d = paths.cache_dir / "omarchy"
    if (d / ".git").is_dir():
        try:
            if _git("rev-parse", "HEAD", cwd=d).stdout.strip() == ref:
                return d / "themes"
        except LibraryError:
            pass
        shutil.rmtree(d)
    elif d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    _git("init", "-q", cwd=d)
    _git("remote", "add", "origin", repo, cwd=d)
    _git("sparse-checkout", "set", "--no-cone", "/themes/", cwd=d)
    _git("fetch", "--depth", "1", "--filter=blob:none", "origin", ref, cwd=d)
    _git("checkout", "-q", "--detach", "FETCH_HEAD", cwd=d)
    return d / "themes"


def omarchy_available(ref=None):
    src = omarchy_checkout(ref)
    return sorted(p.name for p in src.iterdir() if p.is_dir() and _is_theme(p))


def import_omarchy(names=None, ref=None):
    """Copy Omarchy themes into ~/.local/share/rice/themes. Returns [(source, installed as)]."""
    paths = paths_mod.get()
    src = omarchy_checkout(ref)
    stock = {p.name for p in paths.stock_themes.iterdir() if p.is_dir()} if paths.stock_themes.is_dir() else set()
    wanted = {themes_mod.normalize(n) for n in names} if names else None
    available = {p.name: p for p in src.iterdir() if p.is_dir() and _is_theme(p)}
    if wanted:
        missing = sorted(wanted - set(available) - {n.removesuffix("-omarchy") for n in wanted if n.endswith("-omarchy")})
        missing = [m for m in missing if m.removesuffix("-omarchy") not in available]
        if missing:
            raise LibraryError(f"Not in Omarchy's themes: {', '.join(missing)} (rice theme import-omarchy --list)")
    done = []
    paths.imported_themes.mkdir(parents=True, exist_ok=True)
    for name, d in sorted(available.items()):
        target = f"{name}-omarchy" if name in stock else name
        if wanted and name not in wanted and target not in wanted:
            continue
        dest = paths.imported_themes / target
        tmp = paths.imported_themes / f".{target}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(d, tmp, symlinks=False, ignore=shutil.ignore_patterns(".*"))
        (tmp / ".source").write_text(f"{os.environ.get('RICE_OMARCHY_REPO', OMARCHY_REPO)} {ref or OMARCHY_COMMIT} themes/{name}\n")
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        done.append((name, target))
    return done


# ---- new ------------------------------------------------------------------------------

README = """# {display}

A rice theme (Omarchy's theme format). Edit colors.toml and run

    rice theme set {name}

to see it. Files:

- colors.toml     the palette. `rice theme preview {name}` draws it in the terminal.
- backgrounds/    wallpapers (any of jpg, png, webp...). The first one is the default.
- light.mode      present for a light theme (or set mode = "light" in colors.toml).
- icons.theme     optional: an icon theme name.
- preview.png     optional: the picker image (else the first background).
- gnome.toml      optional: accent = "orange", icons = "Colloid-Orange-Dark", css = "..." for the shell.

Any file named like a template output (ghostty.conf, btop.theme, neovim.lua...) replaces
what rice would generate for that app. See ~/dotfiles/rice/docs/themes.md.
"""


def aether():
    """Aether (github.com/bjarneo/aether), if installed: it extracts an Omarchy palette
    from a wallpaper. RICE_AETHER overrides where it is."""
    return os.environ.get("RICE_AETHER") or shutil.which("aether")


def aether_palette(image, light=False, extract_mode=None):
    """colors.toml text that Aether generated from image, or None without Aether."""
    exe = aether()
    if not exe:
        return None
    with tempfile.TemporaryDirectory(prefix="rice-aether-") as tmp:
        out = Path(tmp) / "theme"
        cmd = [exe, "--generate", str(image), "--no-apply", "--output", str(out)]
        if light:
            cmd.append("--light-mode")
        if extract_mode:
            cmd += ["--extract-mode", extract_mode]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise LibraryError(f"aether failed: {e}") from e
        colors = out / "colors.toml"
        if r.returncode != 0 or not colors.is_file():
            raise LibraryError(f"aether failed: {(r.stderr or r.stdout).strip()[-300:]}")
        return colors.read_text()


def new(name, base=None, image=None, light=False, extract_mode=None):
    """Start a theme in ~/.config/rice/themes. With an image (and no base), Aether
    makes the palette from it when installed. Returns (folder, where the palette came from)."""
    paths = paths_mod.get()
    name = themes_mod.normalize(name)
    if not themes_mod.valid(name) or not themes_mod.INSTALL_NAME.fullmatch(name):
        raise LibraryError(f"Invalid theme name: {name}")
    dest = paths.user_themes / name
    if dest.exists():
        raise LibraryError(f"{dest} already exists")
    if themes_mod.find(paths, name):
        raise LibraryError(f"A theme called '{name}' already exists (a folder in {paths.user_themes} would overlay it)")
    source = themes_mod.find(paths, base or themes_mod.current_name(paths) or "vesper")
    if source is None:
        raise LibraryError(f"Theme '{base}' does not exist")
    if image:
        image = Path(image).expanduser()
        if not image.is_file():
            raise LibraryError(f"No such image: {image}")
    generated = aether_palette(image, light, extract_mode) if image and not base else None
    dest.mkdir(parents=True)
    colors = source.file("colors.toml")
    if generated:
        origin = f"Aether, from {image.name}"
        (dest / "colors.toml").write_text(f"# {themes_mod.display_name(name)}: palette by Aether from {image.name}.\n"
                                          + generated)
    else:
        origin = source.display
        if colors:
            text = colors.read_text()
            header = f"# {themes_mod.display_name(name)}, started from {source.display}.\n"
            (dest / "colors.toml").write_text(header + text)
        if source.mode == "light" and "mode" not in (colors.read_text() if colors else ""):
            (dest / "light.mode").write_text("")
    for f in ("icons.theme", "gnome.toml"):
        p = source.file(f)
        if p and not generated:
            shutil.copyfile(p, dest / f)
    (dest / "backgrounds").mkdir()
    if image:
        shutil.copyfile(image, dest / "backgrounds" / image.name)
    else:
        bgs = source.backgrounds(paths)
        if bgs:
            shutil.copyfile(bgs[0].resolve(), dest / "backgrounds" / bgs[0].name)
    (dest / "README.md").write_text(README.format(name=name, display=themes_mod.display_name(name)))
    try:
        from . import previews
        theme = themes_mod.Theme(name=name, user=dest, origin="user")
        bgs = theme.backgrounds(paths)
        previews.render_image(theme.palette(), bgs[0] if bgs else None, dest / "preview.png")
    except Exception:  # noqa: BLE001 - no PIL: the picker uses the first background
        pass
    return dest, origin
