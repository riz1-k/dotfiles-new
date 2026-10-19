"""Claude Code, Codex and T3 Code.

Each gets one theme file whose name never changes (rice) and whose contents do.
Claude Code and T3 Code watch their theme folders and retint running sessions;
Codex reads its theme when a session starts.
"""
import json
import os
import re
from pathlib import Path

from .. import util


def claude_dirs(paths):
    """Every Claude Code config folder: ~/.claude, extra accounts in ~/.claude-*,
    and $CLAUDE_CONFIG_DIR."""
    dirs = [paths.home / ".claude", *sorted(paths.home.glob(".claude-*"))]
    if os.environ.get("CLAUDE_CONFIG_DIR") and not util.SANDBOX:
        dirs.append(Path(os.environ["CLAUDE_CONFIG_DIR"]))
    seen, out = set(), []
    for d in dirs:
        if d.is_dir() and ((d / "settings.json").exists() or (d / ".claude.json").exists()):
            key = d.resolve()
            if key not in seen:
                seen.add(key)
                out.append(d)
    return out


def claude(ctx):
    """Claude watches its themes folder, so running sessions retint live."""
    src = ctx.file("claude.json")
    if not src:
        return
    for home in claude_dirs(ctx.paths):
        util.install_file(src, home / "themes" / "rice.json")
        settings = home / "settings.json"
        if settings.is_file():
            text = settings.read_text()
            if not re.search(r'"theme"\s*:\s*"custom:rice"', text):
                util.atomic_write(settings, util.jsonc_set_string(text, "theme", "custom:rice"))


def codex(ctx):
    src = ctx.file("codex.tmTheme")
    home = Path(os.environ.get("CODEX_HOME") or ctx.paths.home / ".codex")
    if not src or not home.is_dir():
        return
    util.install_file(src, home / "themes" / "rice.tmTheme")
    cfg = home / "config.toml"
    if not cfg.is_file():
        return
    text = cfg.read_text()
    m = re.search(r"(?ms)^\[tui\]\s*$(.*?)(?=^\[|\Z)", text)
    if m:
        block = m.group(1)
        if re.search(r'(?m)^theme\s*=\s*"rice"\s*$', block):
            return
        if re.search(r"(?m)^theme\s*=", block):
            new_block = re.sub(r'(?m)^theme\s*=.*$', 'theme = "rice"', block, count=1)
        else:
            # right under the [tui] header
            new_block = '\ntheme = "rice"' + block
        text = text[:m.start(1)] + new_block + text[m.end(1):]
    else:
        text = text.rstrip("\n") + '\n\n[tui]\ntheme = "rice"\n'
    util.atomic_write(cfg, text)


def t3code(ctx):
    src = ctx.file("t3code.json")
    userdata = Path(os.environ.get("T3CODE_HOME") or ctx.paths.home / ".t3") / "userdata"
    if not src or not userdata.is_dir():
        return
    if "{{" in src.read_text():
        raise RuntimeError("t3code.json has unresolved colours; kept the previous theme")
    util.install_file(src, userdata / "themes" / "rice.json")
    # `t3 theme set rice` writes the same key: connected clients switch to it.
    settings = userdata / "settings.json"
    try:
        data = json.loads(settings.read_text()) if settings.is_file() else {}
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(data, dict) and data.get("defaultTheme") != "rice":
        data["defaultTheme"] = "rice"
        util.atomic_write(settings, json.dumps(data, indent=2) + "\n")
