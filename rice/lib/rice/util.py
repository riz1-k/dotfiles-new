"""Small helpers shared by the engine and the app retints."""
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path


# RICE_SANDBOX=1 (tests): never touch other processes (signals, tmux servers,
# services, notifications, editor CLIs). Files and settings still get written, so
# point HOME/XDG_* at a temporary folder and run under dbus-run-session.
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


def may_use_session_bus():
    """In the sandbox, only use a private session bus (dbus-run-session): the real
    one belongs to the real desktop, and gsettings/dconf/gdbus would change it."""
    if not SANDBOX:
        return True
    addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    return bool(addr) and addr != f"unix:path=/run/user/{os.getuid()}/bus"


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

def jsonc_set_string(text, key, value):
    """Set "key": "value" in a JSONC document without reformatting it (comments and
    trailing commas survive). Adds the key after the first { when missing."""
    esc = json.dumps(value)[1:-1]
    pattern = re.compile(r'("' + re.escape(key) + r'"\s*:\s*)"(?:[^"\\]|\\.)*"')
    if pattern.search(text):
        return pattern.sub(lambda m: m.group(1) + '"' + esc + '"', text, count=1)
    return re.sub(r"\{", lambda m: '{\n  "' + key + '": "' + esc + '",', text, count=1)


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
