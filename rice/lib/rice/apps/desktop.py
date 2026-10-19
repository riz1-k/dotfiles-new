"""Vicinae and the Gtk4-DING desktop widgets."""
import re
import subprocess

from .. import util


def vicinae(ctx):
    theme = ctx.file("vicinae.toml")
    if not theme or not util.have("vicinae"):
        return
    settings = ctx.paths.config / "vicinae" / "settings.json"
    if not settings.is_file():
        return  # vicinae isn't set up for this user
    changed = util.install_file(theme, ctx.paths.data / "vicinae" / "themes" / "rice.toml")
    text = settings.read_text()
    # One theme id for both schemes: its contents follow the rice theme.
    new = re.sub(r'("(?:light|dark)"\s*:\s*\{[^{}]*?"name"\s*:\s*)"[^"]*"', r'\1"rice"', text)
    if new != text:
        util.atomic_write(settings, new)
        changed = True
    # Vicinae parses theme files once at startup, so a new palette needs a server restart.
    if changed and not util.SANDBOX:
        subprocess.run(["systemctl", "--user", "try-restart", "vicinae.service"],
                       capture_output=True, timeout=15)


def widgets(ctx):
    """Each widget folder gets the palette as a real file (Gtk4-DING won't serve
    symlinks) for the next page load; running widgets get it pushed by their
    backend, which watches theme.generation (desktop-widgets/shared/rice_theme.*)."""
    css = ctx.file("widgets.css")
    root = ctx.paths.data / "com.desktop.ding" / "widgets"
    if not css or not root.is_dir():
        return
    for w in root.iterdir():
        if (w / "widget.json").is_file() and (w / "rice.css").exists():
            util.install_file(css, w / "rice-theme.css")
