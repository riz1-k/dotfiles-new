"""Shared bits for the tests: rice's lib on sys.path and a sandbox HOME."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def sandbox_env(home):
    """Environment for running bin/rice against a throwaway HOME. Besides
    RICE_SANDBOX, there's no session bus and GSettings writes go to memory, so
    nothing can reach the real desktop."""
    home = Path(home)
    env = {k: v for k, v in os.environ.items()
           if k not in ("DBUS_SESSION_BUS_ADDRESS", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "T3CODE_HOME",
                        "TMUX", "VSCODE_IPC_HOOK_CLI", "DISPLAY", "WAYLAND_DISPLAY")}
    env.update({
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_RUNTIME_DIR": str(home / "run"),
        "RICE_SANDBOX": "1",
        "GSETTINGS_BACKEND": "memory",
        "TMUX_TMPDIR": str(home / "tmux"),
    })
    (home / "run").mkdir(parents=True, exist_ok=True, mode=0o700)
    return env


def tempdir(test):
    d = tempfile.TemporaryDirectory(prefix="rice-test-")
    test.addCleanup(d.cleanup)
    return Path(d.name)
