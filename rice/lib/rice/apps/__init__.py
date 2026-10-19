"""The retints: one function per app, split into Omarchy's two groups.

VISIBLE runs in parallel and the switch waits for it (what's on screen: the shell,
wallpaper, terminals, tmux, btop). OTHER runs afterwards in the background
(icons, GTK, editors, agents, browsers...). A retint raises on failure; the
engine logs it and names it in a notification.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Context:
    paths: object
    settings: dict
    name: str
    display: str
    colors: dict
    mode: str
    dir: Path            # ~/.local/state/rice/current/theme
    generation: str
    background: Path | None = None
    gnome: dict = field(default_factory=dict)
    log: object = print

    def file(self, name):
        p = self.dir / name
        return p if p.is_file() else None


from . import agents, desktop, editors, gnome, terminal, tuis, web  # noqa: E402

# (name, settings key, function)
VISIBLE = [
    ("shell", "shell", gnome.shell),
    ("ghostty", "ghostty", terminal.ghostty),
    ("kitty", "kitty", terminal.kitty),
    ("tmux", "tmux", terminal.tmux),
    ("btop", "btop", terminal.btop),
    ("herdr", "herdr", terminal.herdr),
]

OTHER = [
    ("gnome", "gnome", gnome.extras),
    ("gtk", "gtk", gnome.gtk),
    ("claude", "claude", agents.claude),
    ("codex", "codex", agents.codex),
    ("t3code", "t3code", agents.t3code),
    ("vscode", "vscode", editors.vscode),
    ("cursor", "cursor", editors.cursor),
    ("obsidian", "obsidian", editors.obsidian),
    ("vencord", "vencord", web.vencord),
    ("zen", "zen", web.zen),
    ("chromium", "chromium", web.chromium),
    ("vicinae", "vicinae", desktop.vicinae),
    ("widgets", "widgets", desktop.widgets),
    ("lazygit", "lazygit", tuis.lazygit),
    ("gitui", "gitui", tuis.gitui),
    ("yazi", "yazi", tuis.yazi),
]

ALL = {name: fn for name, _, fn in VISIBLE + OTHER}
