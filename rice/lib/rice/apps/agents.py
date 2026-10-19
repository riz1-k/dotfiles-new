"""Claude Code, Codex and T3 Code.

Each gets one theme file whose name never changes (rice) and whose contents do.
Claude Code and T3 Code watch their theme folders and retint running sessions;
Codex reads its theme when a session starts.
"""
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
    problems = []
    for home in claude_dirs(ctx.paths):
        util.install_file(src, home / "themes" / "rice.json")
        settings = home / "settings.json"
        if settings.is_file():
            text = settings.read_text()
            try:
                new = util.json_set(text, "theme", "custom:rice")
            except util.ConfigEditError as e:
                problems.append(f"{settings}: {e}")
                continue
            if new != text:
                util.atomic_write(settings, new)
    if problems:
        raise RuntimeError("; ".join(problems))


# [tui] with an optional comment after it; any table header ends the table.
TUI_HEADER = re.compile(r"(?m)^[ \t]*\[[ \t]*tui[ \t]*\][ \t]*(?:#.*)?$")
TABLE_HEADER = re.compile(r"(?m)^[ \t]*\[")
THEME_LINE = re.compile(r"(?m)^([ \t]*)theme[ \t]*=.*$")


def codex_set_theme(text, name):
    """config.toml with [tui] theme = name. The edit keeps every other line as it is
    and is checked with tomllib: a file that doesn't parse, or an edit that wouldn't
    (tui set with dotted keys or an inline table), is refused, never guessed at."""
    import tomllib
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise util.ConfigEditError(f"not valid TOML ({e}); left alone") from None
    tui = data.get("tui")
    if isinstance(tui, dict) and tui.get("theme") == name:
        return text
    line = f'theme = "{name}"'
    m = TUI_HEADER.search(text)
    if m:
        end = TABLE_HEADER.search(text, m.end())
        stop = end.start() if end else len(text)
        block = text[m.end():stop]
        if THEME_LINE.search(block):
            block = THEME_LINE.sub(lambda t: t.group(1) + line, block, count=1)
        else:
            block = "\n" + line + block
        new = text[:m.end()] + block + text[stop:]
    else:
        # No [tui] header: a new table at the end (fine after [tui.x] sub-tables; not
        # if tui is set with dotted keys or inline, which the check below refuses).
        new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + f"[tui]\n{line}\n"
    try:
        check = tomllib.loads(new)
    except tomllib.TOMLDecodeError as e:
        hint = f"; add {line} under tui yourself" if tui is not None else ""
        raise util.ConfigEditError(f"the edit wouldn't parse ({e}){hint}; left alone") from None
    if check.get("tui", {}).get("theme") != name:
        raise util.ConfigEditError("the edit didn't take; left alone")
    return new


def codex_home(paths):
    return Path(os.environ.get("CODEX_HOME") or paths.home / ".codex")


def t3_userdata(paths):
    return Path(os.environ.get("T3CODE_HOME") or paths.home / ".t3") / "userdata"


def codex(ctx):
    src = ctx.file("codex.tmTheme")
    home = codex_home(ctx.paths)
    if not src or not home.is_dir():
        return
    util.install_file(src, home / "themes" / "rice.tmTheme")
    cfg = home / "config.toml"
    if not cfg.is_file():
        return
    text = cfg.read_text()
    new = codex_set_theme(text, "rice")
    if new != text:
        util.atomic_write(cfg, new)


def t3code(ctx):
    src = ctx.file("t3code.json")
    userdata = t3_userdata(ctx.paths)
    if not src or not userdata.is_dir():
        return
    if "{{" in src.read_text():
        raise RuntimeError("t3code.json has unresolved colours; kept the previous theme")
    util.install_file(src, userdata / "themes" / "rice.json")
    # `t3 theme set rice` writes the same key: connected clients switch to it.
    settings = userdata / "settings.json"
    text = settings.read_text() if settings.is_file() else ""
    new = util.json_set(text, "defaultTheme", "rice")
    if new != text:
        util.atomic_write(settings, new)
