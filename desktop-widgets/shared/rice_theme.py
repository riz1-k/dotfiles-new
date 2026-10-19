"""Live theme for widgets with a Python backend (symlinked into each widget).

`rice theme set` writes the new palette to ~/.local/state/rice/current/theme/widgets.css
and bumps theme.generation; this pushes the palette to the page as a "rice-theme"
event, and api.js/host.js swap it in. On a page load the palette comes from the
rice-theme.css that rice copies into each installed widget.
"""
import os
import threading
import time

STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
                     "rice", "current")


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _loop(send, interval):
    last = _read(os.path.join(STATE, "theme.generation"))
    while True:
        time.sleep(interval)
        generation = _read(os.path.join(STATE, "theme.generation"))
        if generation == last:
            continue
        last = generation
        css = _read(os.path.join(STATE, "theme", "widgets.css"))
        if css is not None:
            send({"type": "event", "name": "rice-theme", "payload": {"css": css}})


def watch(send, interval=1.0):
    """Push the palette with send(message) whenever the theme changes."""
    threading.Thread(target=_loop, args=(send, interval), daemon=True).start()
