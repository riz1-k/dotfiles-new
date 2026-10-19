"""Terminals and what runs inside them: ghostty, kitty, tmux, btop, herdr.

ghostty and kitty include current/theme/<app>.conf from their main config, so a
reload signal is all a switch needs. Neovim and zsh watch theme.generation
themselves and need nothing here.
"""
import os
import re
import signal
from pathlib import Path

from .. import util


def ghostty(ctx):
    if not ctx.file("ghostty.conf"):
        return
    # SIGUSR2 makes every ghostty window re-read its config (ghostty >= 1.2).
    util.signal_all("ghostty", signal.SIGUSR2)


def kitty(ctx):
    if not ctx.file("kitty.conf"):
        return
    # SIGUSR1 reloads kitty.conf in every kitty window, which includes the theme.
    util.signal_all("kitty", signal.SIGUSR1)


def tmux_sockets():
    if util.SANDBOX:
        return []
    base = Path(os.environ.get("TMUX_TMPDIR") or "/tmp") / f"tmux-{os.getuid()}"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_socket()]


def tmux(ctx):
    conf = ctx.file("tmux.conf")
    if not conf or not util.have("tmux"):
        return
    errors = []
    for sock in tmux_sockets():
        r = util.run(["tmux", "-S", str(sock), "source-file", str(conf)], check=False, timeout=5)
        # A stale socket (no server) answers "no server running"/"error connecting": not our failure.
        if r.returncode != 0 and not re.search(r"no server|error connecting|No such file", r.stderr):
            errors.append(f"{sock.name}: {r.stderr.strip()}")
    if errors:
        raise RuntimeError("; ".join(errors))


def btop(ctx):
    theme = ctx.file("btop.theme")
    cfg_dir = ctx.paths.config / "btop"
    if not theme or not cfg_dir.is_dir():
        return
    util.install_file(theme, cfg_dir / "themes" / "rice.theme")
    conf = cfg_dir / "btop.conf"
    if conf.is_file():
        text = conf.read_text()
        new = re.sub(r'(?m)^color_theme\s*=.*$', 'color_theme = "rice"', text)
        if 'color_theme' not in text:
            new = text.rstrip("\n") + '\ncolor_theme = "rice"\n'
        if new != text:
            util.atomic_write(conf, new)
    # btop re-reads its config and theme on SIGUSR2.
    util.signal_all("btop", signal.SIGUSR2)


def herdr(ctx):
    # herdr's "terminal" theme follows the terminal palette; it only needs a nudge.
    if util.have("herdr") and util.pids("herdr"):
        util.run(["herdr", "server", "reload-config"], check=False, timeout=5)
