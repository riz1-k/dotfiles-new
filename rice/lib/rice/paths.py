"""Every path rice reads or writes, derived from $HOME and the XDG variables.

Nothing is hard-coded to a user, so tests point HOME and XDG_* at a temporary
folder and get a complete sandbox.
"""
import os
from dataclasses import dataclass
from pathlib import Path

# ~/dotfiles/rice (this file is lib/rice/paths.py)
ROOT = Path(__file__).resolve().parent.parent.parent


def _xdg(var, home, default):
    value = os.environ.get(var)
    return Path(value) if value else home / default


@dataclass(frozen=True)
class Paths:
    home: Path
    config: Path
    data: Path
    state: Path
    cache: Path
    runtime: Path
    root: Path = ROOT

    # -- sources -----------------------------------------------------------
    @property
    def stock_themes(self):
        return Path(os.environ.get("RICE_STOCK_THEMES", self.root / "themes"))

    @property
    def templates(self):
        return self.root / "templates"

    @property
    def imported_themes(self):
        return self.data / "rice" / "themes"

    @property
    def user_dir(self):
        return self.config / "rice"

    @property
    def user_themes(self):
        return self.user_dir / "themes"

    @property
    def user_backgrounds(self):
        return self.user_dir / "backgrounds"

    @property
    def user_templates(self):
        return self.user_dir / "themed"

    @property
    def hooks(self):
        return self.user_dir / "hooks"

    @property
    def settings(self):
        return self.user_dir / "settings.toml"

    # -- state -------------------------------------------------------------
    @property
    def state_dir(self):
        return self.state / "rice"

    @property
    def current(self):
        return self.state_dir / "current"

    @property
    def current_theme(self):
        return self.current / "theme"

    @property
    def next_theme(self):
        return self.current / "next-theme"

    @property
    def theme_name(self):
        return self.current / "theme.name"

    @property
    def generation(self):
        return self.current / "theme.generation"

    @property
    def background_link(self):
        return self.current / "background"

    @property
    def theme_backgrounds(self):
        return self.state_dir / "theme-backgrounds"

    @property
    def mode_pairs(self):
        return self.state_dir / "mode-pairs.json"

    @property
    def log(self):
        return self.state_dir / "theme-set.log"

    @property
    def cache_dir(self):
        return self.cache / "rice"

    @property
    def previews(self):
        return self.cache_dir / "previews"

    @property
    def lock(self):
        return self.runtime / "rice-theme-set.lock"

    @property
    def retint_lock(self):
        return self.runtime / "rice-theme-set-retint.lock"

    @property
    def mode_watch_flag(self):
        """Present while rice itself is changing color-scheme (the watcher ignores it)."""
        return self.runtime / "rice-mode-change"


def get():
    home = Path(os.environ.get("HOME") or Path.home())
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/rice-{os.getuid()}"
    return Paths(
        home=home,
        config=_xdg("XDG_CONFIG_HOME", home, ".config"),
        data=_xdg("XDG_DATA_HOME", home, ".local/share"),
        state=_xdg("XDG_STATE_HOME", home, ".local/state"),
        cache=_xdg("XDG_CACHE_HOME", home, ".cache"),
        runtime=Path(runtime),
    )
