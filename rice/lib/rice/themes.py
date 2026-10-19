"""Finding themes: stock (rice/themes), imported Omarchy themes and user themes.

A user theme in ~/.config/rice/themes/<name> overlays the stock or imported theme
of the same name, as ~/.config/omarchy/themes does on Omarchy. A user theme that
holds a .git folder was installed from someone else's repo and is staged through
the filter in stage.py.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from . import palette

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
INSTALL_NAME = re.compile(r"^[a-z0-9_][a-z0-9._+-]*$")


def normalize(name):
    """'Tokyo Night' and '<b>tokyo night</b>' both become 'tokyo-night' (Omarchy's rule)."""
    name = re.sub(r"<[^>]+>", "", name or "")
    return name.strip().lower().replace(" ", "-")


def valid(name):
    return bool(name) and not name.startswith(".") and "/" not in name and "\0" not in name


def display_name(name):
    return re.sub(r"(^|-)([a-z])", lambda m: m.group(1) + m.group(2).upper(), name).replace("-", " ")


@dataclass
class Theme:
    name: str
    base: Path | None = None    # stock or imported folder
    user: Path | None = None    # ~/.config/rice/themes/<name>
    origin: str = "stock"       # stock | omarchy | user

    @property
    def display(self):
        return display_name(self.name)

    @property
    def git(self):
        """Installed from a repo: a real folder (not a symlink to your own copy) with .git."""
        return self.user is not None and not self.user.is_symlink() and (self.user / ".git").is_dir()

    @property
    def trusted(self):
        return not self.git

    @property
    def dirs(self):
        """Folders in overlay order (later wins)."""
        return [d for d in (self.base, self.user) if d is not None]

    def file(self, name):
        """The winning copy of a file in the theme, or None."""
        for d in reversed(self.dirs):
            p = d / name
            if p.is_file():
                return p
        return None

    def palette(self, warnings=None):
        colors = self.file("colors.toml")
        if colors is None:
            return {}
        raw = palette.parse(colors.read_text(errors="replace"), warnings)
        light = any((d / "light.mode").exists() for d in self.dirs)
        return palette.resolve(raw, light_mode_file=light)

    @property
    def mode(self):
        return self.palette().get("mode", "dark")

    def backgrounds(self, paths):
        """Wallpapers in the order a staged theme lists them: your extras in
        ~/.config/rice/backgrounds/<name>/ first, then the theme's own (a user
        overlay's file replaces the stock file of the same name)."""
        merged = {}
        for d in self.dirs:
            merged.update({p.name: p for p in image_files(d / "backgrounds")})
        extras = image_files(paths.user_backgrounds / self.name)
        return extras + [merged[k] for k in sorted(merged)]

    def preview(self, paths):
        p = self.file("preview.png")
        if p:
            return p
        bgs = self.backgrounds(paths)
        return bgs[0] if bgs else None


def image_files(d):
    if not d.is_dir():
        return []
    return sorted((p for p in d.iterdir() if p.suffix.lower() in IMAGE_EXTS and p.is_file()),
                  key=lambda p: p.name)


def _dirs(root):
    if not root.is_dir():
        return {}
    return {p.name: p for p in root.iterdir() if p.is_dir() and valid(p.name)}


def all_themes(paths):
    stock = _dirs(paths.stock_themes)
    imported = _dirs(paths.imported_themes)
    user = _dirs(paths.user_themes)
    themes = {}
    for name in sorted(set(stock) | set(imported) | set(user)):
        base = stock.get(name) or imported.get(name)
        origin = "stock" if name in stock else ("omarchy" if name in imported else "user")
        themes[name] = Theme(name=name, base=base, user=user.get(name), origin=origin)
    return themes


def find(paths, name):
    return all_themes(paths).get(normalize(name))


def current_name(paths):
    try:
        return paths.theme_name.read_text().strip()
    except OSError:
        return ""


def install_name(url):
    """The theme name Omarchy derives from a repo URL, or None if it isn't usable."""
    path = url
    if "://" not in path and ":" in path and "/" not in path.split(":", 1)[0]:
        path = path.split(":", 1)[1]
    base = path.rstrip("/").rsplit("/", 1)[-1]
    if base.endswith(".git"):
        base = base[:-4]
    base = re.sub(r"^omarchy-", "", base)
    base = re.sub(r"-theme$", "", base).lower()
    return base if INSTALL_NAME.fullmatch(base) and base.isascii() else None


TRANSPORTS = {"ssh", "git", "git+ssh", "ssh+git", "http", "https", "ftp", "ftps", "file"}


def check_git_url(url):
    """Refuse URLs git would read as an option or as a transport helper to run
    (port of omarchy-git-url-check). Returns an error string or None."""
    if not url:
        return "a git URL is required"
    if url.startswith("-") or re.match(r"^[A-Za-z0-9][A-Za-z0-9+.-]*::", url):
        return f"'{url}' names a git option or transport helper, not a repository."
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9+.-]*)://", url)
    if m and m.group(1) not in TRANSPORTS:
        return f"'{url}' names the '{m.group(1)}' transport, which rice does not clone from."
    return None
