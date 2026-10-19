"""Small helpers shared by the engine and the app retints."""
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote


# RICE_SANDBOX=1 (tests): never touch other processes (signals, tmux servers,
# services, notifications, editor CLIs) or the session bus. Files still get
# written, so point HOME/XDG_* at a temporary folder. A test that wants a bus runs
# under dbus-run-session and names that bus in RICE_SANDBOX_BUS.
SANDBOX = os.environ.get("RICE_SANDBOX") == "1"


def atomic_write(path, data, follow=True, mode=None):
    """Write via a temp file + rename, so watchers never see half a file.

    follow=True writes through a symlink (e.g. a config that lives in ~/dotfiles);
    follow=False replaces the link itself with a real file."""
    path = Path(path)
    if follow and path.is_symlink():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb" if isinstance(data, bytes) else "w") as f:
            f.write(data)
        if mode is not None:
            os.chmod(tmp, mode)
        elif path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o777)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def install_file(src, dst, follow=False):
    """Copy a generated file into an app's config, atomically. Unchanged files are
    left alone so file watchers (Claude, T3 Code, Vencord) don't fire for nothing."""
    data = Path(src).read_bytes()
    dst = Path(dst)
    target = dst.resolve() if (follow and dst.is_symlink()) else dst
    if target.is_file() and not target.is_symlink():
        try:
            if target.read_bytes() == data:
                return False
        except OSError:
            pass
    atomic_write(dst, data, follow=follow)
    return True


def pids(name):
    """PIDs whose comm is exactly `name` and that belong to us (pkill -x)."""
    found = []
    if SANDBOX:
        return found
    uid = os.getuid()
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            with open(f"/proc/{entry.name}/comm") as f:
                if f.read().strip() == name:
                    found.append(int(entry.name))
        except OSError:
            continue
    return found


def signal_all(name, sig):
    n = 0
    for pid in pids(name):
        try:
            os.kill(pid, sig)
            n += 1
        except OSError:
            pass
    return n


def run(cmd, timeout=10, check=True, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))}: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def have(cmd):
    return shutil.which(cmd) is not None


# ---- GSettings / dconf ---------------------------------------------------------

def gget(schema, key):
    r = run(["gsettings", "get", schema, key], check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def _real_bus_paths():
    uid = os.getuid()
    paths = {f"/run/user/{uid}/bus"}
    if os.environ.get("XDG_RUNTIME_DIR"):
        paths.add(os.path.join(os.environ["XDG_RUNTIME_DIR"], "bus"))
    out = set()
    for p in paths:
        out.add(p)
        try:
            out.add(os.path.realpath(p))
        except OSError:
            pass
    return out


def may_use_session_bus():
    """Outside the sandbox, yes. In it (tests), no, unless the test names its private
    bus (dbus-run-session) in RICE_SANDBOX_BUS, that is the bus in use, and it isn't
    the desktop's: gsettings/dconf/gdbus on the real bus would change the real desktop.
    Fails closed: anything unexpected means no bus."""
    if not SANDBOX:
        return True
    addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not addr or os.environ.get("RICE_SANDBOX_BUS") != addr:
        return False
    real = _real_bus_paths()
    for part in addr.split(";"):
        transport, _, params = part.partition(":")
        if transport not in ("unix",):
            return False  # tcp, launchd, autolaunch...: could be anything
        for kv in params.split(","):
            k, _, v = kv.partition("=")
            v = unquote(v)  # addresses may percent-encode any byte
            if k in ("path", "dir", "tmpdir") and (v in real or os.path.realpath(v) in real):
                return False
            if k == "runtime":
                return False  # unix:runtime=yes is the real one
    return True


class SandboxBusError(OSError):
    pass


def _bus_guard():
    if not may_use_session_bus():
        raise SandboxBusError("RICE_SANDBOX=1 without a private session bus (run under dbus-run-session)")


def gset(schema, key, value):
    """Set a key from its plain value (strings are quoted for you). Only writes on change."""
    _bus_guard()
    gvalue = gvariant(value)
    if gget(schema, key) == gvalue:
        return False
    run(["gsettings", "set", schema, key, gvalue])
    return True


def dset(path, value):
    """dconf write for keys of extensions whose schemas aren't installed system-wide."""
    _bus_guard()
    gvalue = value if isinstance(value, str) and value[:1] in "{[(@" else gvariant(value)
    r = run(["dconf", "read", path], check=False)
    if r.stdout.strip() == gvalue:
        return False
    run(["dconf", "write", path, gvalue])
    return True


def gvariant(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---- JSON(C) edits ----------------------------------------------------------------

class ConfigEditError(ValueError):
    """A config file rice won't edit (it doesn't parse, or the edit wouldn't)."""


def json_set(text, key, value):
    """Set a root key of a strict JSON object (Claude's settings.json). Key order
    is kept; the file is re-indented with two spaces."""
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as e:
        raise ConfigEditError(f"not valid JSON ({e}); left alone") from None
    if not isinstance(data, dict):
        raise ConfigEditError("not a JSON object; left alone")
    if data.get(key) == value:
        return text
    data[key] = value
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _jsonc_scan(text):
    """Tokens of a JSONC document: (kind, start, end) with kind one of '{', '}', '[',
    ']', ':', ',', 'str', 'lit'. Comments and whitespace are skipped."""
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise ConfigEditError("unterminated comment")
            i = j + 2
        elif ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise ConfigEditError("unterminated string")
            yield "str", i, j + 1
            i = j + 1
        elif ch in "{}[]:,":
            yield ch, i, i + 1
            i += 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n{}[]:,\"/":
                j += 1
            if j == i:
                raise ConfigEditError(f"unexpected {ch!r}")
            yield "lit", i, j
            i = j


def _jsonc_members(text):
    """The root object's members: (key, value_start, value_end), plus the offsets
    just inside its braces."""
    tokens = list(_jsonc_scan(text))
    if not tokens or tokens[0][0] != "{":
        raise ConfigEditError("not a JSON object")
    members, depth, k = [], 0, 1
    open_end = tokens[0][2]
    while k < len(tokens):
        kind, a, b = tokens[k]
        if kind == "}":
            if k != len(tokens) - 1:
                raise ConfigEditError("text after the closing brace")
            return members, open_end, a
        if kind == ",":
            k += 1
            continue
        if kind != "str" or k + 2 >= len(tokens) or tokens[k + 1][0] != ":":
            raise ConfigEditError("expected a key")
        key = json.loads(text[a:b])
        k += 2
        start = tokens[k][1]
        while k < len(tokens):  # the value: a scalar or a balanced {...}/[...]
            kind2 = tokens[k][0]
            depth += kind2 in "{[" and 1 or 0
            depth -= kind2 in "}]" and 1 or 0
            if depth < 0:
                raise ConfigEditError("unbalanced brackets")
            if depth == 0:
                break
            k += 1
        end = tokens[k][2]
        members.append((key, start, end))
        k += 1
    raise ConfigEditError("missing closing brace")


def _jsonc_strict(text):
    """text as strict JSON: comments and trailing commas dropped."""
    out, prev = [], None
    for kind, a, b in _jsonc_scan(text):
        if kind in "}]" and prev == ",":
            out.pop()  # the trailing comma
        out.append(text[a:b])
        prev = kind
    return " ".join(out)


def jsonc_get(text, key):
    """A root key's value in a JSONC document, or None."""
    try:
        return json.loads(_jsonc_strict(text)).get(key)
    except (ConfigEditError, json.JSONDecodeError, AttributeError):
        return None


def jsonc_set(text, key, value):
    """Set a root key in a JSONC document (VS Code's settings.json) without
    reformatting it: comments, trailing commas and nested keys of the same name
    are left alone. A new key goes first, after the opening brace."""
    if not text.strip():
        text = "{\n}\n"
    members, inside, close = _jsonc_members(text)
    encoded = json.dumps(value, ensure_ascii=False)
    found = [m for m in members if m[0] == key]
    if found:
        _, a, b = found[-1]  # the last one wins in JSON
        new = text[:a] + encoded + text[b:]
    elif members:
        new = text[:inside] + f'\n  {json.dumps(key)}: {encoded},' + text[inside:]
    else:
        body = text[inside:close]
        new = text[:inside] + f'\n  {json.dumps(key)}: {encoded}' + (body.rstrip() or "") + "\n" + text[close:]
    try:
        check = json.loads(_jsonc_strict(new))
    except (ConfigEditError, json.JSONDecodeError) as e:
        raise ConfigEditError(f"the edit wouldn't parse ({e}); left alone") from None
    if not isinstance(check, dict) or check.get(key) != value:
        raise ConfigEditError("the edit didn't take; left alone")
    return new


def notify(summary, body="", urgency="normal"):
    if have("notify-send") and not SANDBOX:
        subprocess.run(["notify-send", "-a", "Rice", "-u", urgency, "-i", "preferences-desktop-theme",
                        summary, body], capture_output=True, timeout=5)


def session_bus_ok():
    """There is a session bus, and rice may use it (see may_use_session_bus)."""
    have_bus = bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS")) or Path(
        os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"), "bus").exists()
    return have_bus and may_use_session_bus()


SIGNALS = {"USR1": signal.SIGUSR1, "USR2": signal.SIGUSR2}
