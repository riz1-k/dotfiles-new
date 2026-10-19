"""Building next-theme: the stock or imported theme, then the user overlay on top.

A user theme with a .git folder came from a stranger's repo. Like Omarchy, rice
never stages anything from it that runs code; the file is generated from a
template instead and named on stderr. On top of Omarchy's list (every *.lua, the
terminal configs, vscode.json, symlinks), rice also drops the files that rice's
own templates make and that its apps execute or trust (tmux, zsh, lazygit,
browser and Discord CSS, the shell stylesheet), every script and every
executable file.
"""
import os
import re
import shutil
import stat

# Generated files a git-installed theme may not replace. tests/test_stage.py fails
# when a template's output is in neither this set nor COLOUR_ONLY.
DENIED_NAMES = {
    # Omarchy's list
    "alacritty.toml", "foot.ini", "ghostty.conf", "kitty.conf", "vscode.json",
    # rice: these are executed or given control over a UI
    "tmux.conf",           # tmux runs run-shell / if-shell lines
    "zsh-highlight.zsh",   # sourced by zsh
    "lazygit.yml",         # customCommands run shell commands
    "quickCss.css",        # Discord client CSS
    "userChrome.css", "userContent.css",  # browser chrome CSS
    "widgets.css",         # desktop widget pages
    "gnome-shell.css",     # the shell, including the lock screen
    "neovim.json",         # names the plugin Neovim installs
    "vscode-theme.json",   # becomes a VS Code extension package
}
DENIED_SUFFIXES = (".lua", ".sh", ".bash", ".zsh", ".fish", ".py", ".js", ".mjs", ".cjs",
                   ".pl", ".rb", ".desktop", ".service", ".so", ".exe")
# Template outputs that are only colours, safe to take from any theme.
COLOUR_ONLY = {
    "btop.theme", "chromium.theme", "claude.json", "t3code.json", "codex.tmTheme",
    "gitui.ron", "yazi.toml", "vicinae.toml", "gtk3.css", "gtk4.css", "obsidian.css",
    "helix.toml", "colors.json", "gnome.json", "herdr.toml", "tmux-palette.json",
}
QUIET = re.compile(r"^(readme|license|licence|changelog|copying).*|.*\.(md|txt)$", re.I)


def denied(name):
    return name in DENIED_NAMES or name.lower().endswith(DENIED_SUFFIXES)


def _place(src, dst):
    """Hard-link when possible (wallpapers are big and every switch stages them), else copy."""
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def copy_trusted(src, dst):
    """Your own theme (or a stock one): copied as is, dotfiles skipped, symlinks kept."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name.startswith("."):
            continue
        target = dst / entry.name
        if entry.is_symlink():
            if target.exists() or target.is_symlink():
                shutil.rmtree(target) if target.is_dir() and not target.is_symlink() else target.unlink()
            os.symlink(os.readlink(entry), target)
        elif entry.is_dir():
            copy_trusted(entry, target)
        elif entry.is_file():
            _place(entry, target)


DATA_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".toml", ".json",
                 ".css", ".ron", ".theme", ".tmtheme", ".conf", ".ini", ".yml", ".yaml", ".md", ".txt")


def _runs_code(entry):
    """A script, or an executable that isn't plainly data (repos made on other
    systems often mark their wallpapers executable; copies never keep the bit)."""
    name = entry.name.lower()
    if name.endswith(DENIED_SUFFIXES):
        return True
    try:
        mode = entry.lstat().st_mode
    except OSError:
        return True
    return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)) and not name.endswith(DATA_SUFFIXES)


def copy_untrusted(src, dst, ignored, top=True, rel=""):
    """A stranger's theme: never follow a symlink, and drop anything that runs code."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src.iterdir(), key=lambda p: p.name):
        name = entry.name
        if name.startswith("."):
            continue
        shown = rel + name
        if entry.is_symlink() or (top and name in DENIED_NAMES) or (entry.is_file() and _runs_code(entry)):
            if not QUIET.match(name):
                ignored.append(shown)
            continue
        if entry.is_dir():
            copy_untrusted(entry, dst / name, ignored, top=False, rel=shown + "/")
        elif entry.is_file():
            shutil.copyfile(entry, dst / name)
        else:
            ignored.append(shown)


# ---- old themes: colors.toml from alacritty.toml (omarchy-theme-colors-from-alacritty)

NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
_HEX_VALUE = re.compile(r"""^["'](0[xX]|#)?[0-9a-fA-F]{6}(["']([ \t]*#.*)?)?$|^(0[xX])?[0-9a-fA-F]{6}([ \t]*#.*)?$""")


def colors_from_alacritty(text):
    """colors.toml text from an alacritty.toml, or None if the normal colours are incomplete."""
    direct, dotted, section = {}, {}, ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            m = re.match(r"^\[([^]]*)\]\s*$", s)
            section = m.group(1) if m else ""
            continue
        if not section or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key.startswith("#") or not _HEX_VALUE.match(value):
            continue
        hexval = "#" + re.search(r"[0-9a-fA-F]{6}", value).group(0).lower()
        path = f"{section}.{key}"
        target = dotted if section == "colors" and "." in key else direct
        target.setdefault(path, hexval)
    colors = {**dotted, **direct}
    c = {}
    for i, n in enumerate(NAMES):
        v = colors.get(f"colors.normal.{n}")
        if not v:
            return None
        c[i] = v
    for i, n in enumerate(NAMES):
        c[i + 8] = colors.get(f"colors.bright.{n}") or c[i]
    background = colors.get("colors.primary.background") or c[0]
    foreground = colors.get("colors.primary.foreground") or c[7]
    c[0], c[7] = background, foreground
    selection = colors.get("colors.selection.background") or foreground
    lines = [f'accent = "{c[4]}"', f'selection = "{selection}"', "",
             f'background = "{background}"', f'foreground = "{foreground}"', ""]
    lines += [f'color{i} = "{c[i]}"' for i in range(16)]
    return "\n".join(lines) + "\n"


def stage(theme, next_dir):
    """Fill next_dir with the theme. Returns the files left out of a git theme."""
    if next_dir.exists():
        shutil.rmtree(next_dir)
    next_dir.mkdir(parents=True)
    ignored = []
    if theme.base:
        copy_trusted(theme.base, next_dir)
    if theme.user:
        if theme.git:
            copy_untrusted(theme.user, next_dir, ignored)
        else:
            copy_trusted(theme.user, next_dir)
    if not (next_dir / "colors.toml").exists():
        source = None
        if theme.user and theme.git:
            a = theme.user / "alacritty.toml"
            if a.is_file() and not a.is_symlink():
                source = a
        elif (next_dir / "alacritty.toml").is_file():
            source = next_dir / "alacritty.toml"
        if source:
            text = colors_from_alacritty(source.read_text(errors="replace"))
            if text:
                (next_dir / "colors.toml").write_text(text)
    return ignored
