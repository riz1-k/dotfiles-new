"""Backend for the Notes widget.

Gtk4-DING starts this when the widget appears and talks to it with one JSON
object per line: hello/request/shutdown arrive on stdin, and response/event
messages go back on stdout.

The notes live in a plain Markdown file (config "file", ~/Notes/inbox.md by
default), so they can be edited anywhere: "- [ ] x" is a todo, "- [x] x" a
done one, any other line a note. The widget never rewrites the whole file
from its own copy. Every change names the line it touches and that line's
text, and is refused if the file has moved on since, so edits made in an
editor at the same time are never lost.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading

_write_lock = threading.Lock()

DEFAULT_FILE = "~/Notes/inbox.md"
POLL_SECONDS = 1.5

# "- [ ] text", "* [x] text", "1. [ ] text", "- text"; group 1 is the marker
# and indent, group 2 the checkbox state if there is one, group 3 the text.
ITEM = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)(?:\[([ xX])\]\s*)?(.*)$")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")


def send(message):
    with _write_lock:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()


def parse_line(line):
    """What one line of the file shows as, or None for blank lines."""
    if not line.strip():
        return None
    heading = HEADING.match(line)
    if heading:
        return {"kind": "heading", "text": heading.group(1).strip()}
    item = ITEM.match(line)
    if item and item.group(2) is not None:
        return {"kind": "task", "done": item.group(2) != " ", "text": item.group(3).strip()}
    if item:
        return {"kind": "note", "text": item.group(3).strip()}
    return {"kind": "note", "text": line.strip()}


def task_line(text, done=False):
    return f"- [{'x' if done else ' '}] {text}"


def clean(text):
    # One item is one line; pasted newlines become spaces.
    return " ".join(str(text or "").split())


class Conflict(Exception):
    """The line a change was aimed at isn't there any more."""


class Notes:
    def __init__(self, path):
        self.path = os.path.expanduser(path)
        self._lock = threading.Lock()
        self._mtime = None
        self._lines = []
        self._undo = None  # (text before the change, text after it, label)
        self.reload()

    # ---- file -------------------------------------------------------------

    def _stat(self):
        try:
            st = os.stat(self.path)
            return st.st_mtime_ns, st.st_size
        except FileNotFoundError:
            return None

    def reload(self):
        """Read the file again if it changed on disk; True if it did."""
        with self._lock:
            stat = self._stat()
            if stat == self._mtime:
                return False
            self._mtime = stat
            try:
                with open(self.path, encoding="utf-8") as f:
                    self._lines = f.read().splitlines()
            except FileNotFoundError:
                self._lines = []
            return True

    def _text(self, lines):
        return "\n".join(lines) + "\n" if lines else ""

    def _write(self, lines):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # Write next to the file and rename over it, so an editor watching it
        # never sees half a file.
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), prefix=".notes-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self._text(lines))
            mode = os.stat(self.path).st_mode & 0o777 if os.path.exists(self.path) else 0o644
            os.chmod(tmp, mode)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self._lines = lines
        self._mtime = self._stat()

    def _change(self, lines, label=None):
        before = self._text(self._lines)
        self._write(lines)
        self._undo = (before, self._text(lines), label) if label else None

    def _find(self, index, raw):
        """The current index of the line the widget saw at index with text raw."""
        if 0 <= index < len(self._lines) and self._lines[index] == raw:
            return index
        # Lines above it were added or removed in an editor: look for the same
        # text, nearest first, but only if it's unambiguous.
        matches = [i for i, line in enumerate(self._lines) if line == raw]
        if len(matches) == 1:
            return matches[0]
        raise Conflict("That item changed in the file; showing the latest version.")

    # ---- what the widget sees ---------------------------------------------

    def snapshot(self):
        items = []
        for index, line in enumerate(self._lines):
            parsed = parse_line(line)
            if parsed:
                items.append(dict(parsed, line=index, raw=line))
        return {
            "file": self.path,
            "name": os.path.basename(self.path),
            "items": items,
            "undo": self._undo[2] if self._undo and self._undo[1] == self._text(self._lines) else None,
        }

    # ---- changes -----------------------------------------------------------

    def add(self, text, kind="task"):
        text = clean(text)
        if not text:
            return
        line = task_line(text) if kind == "task" else f"- {text}"
        lines = list(self._lines)
        # Newest first, but below a title the file starts with.
        at = 1 if lines and HEADING.match(lines[0]) else 0
        while at < len(lines) and not lines[at].strip():
            at += 1
        lines.insert(at, line)
        self._change(lines)

    def toggle(self, index, raw):
        index = self._find(index, raw)
        item = ITEM.match(self._lines[index])
        if not item or item.group(2) is None:
            return
        done = item.group(2) == " "
        lines = list(self._lines)
        lines[index] = f"{item.group(1)}[{'x' if done else ' '}] {item.group(3)}".rstrip()
        self._change(lines)

    def edit(self, index, raw, text):
        index = self._find(index, raw)
        text = clean(text)
        if not text:
            return self.delete(index, raw)
        old = self._lines[index]
        item = ITEM.match(old)
        heading = HEADING.match(old)
        if heading:
            new = old[:heading.start(1)] + text
        elif item and item.group(2) is not None:
            new = f"{item.group(1)}[{item.group(2)}] {text}"
        elif item:
            new = f"{item.group(1)}{text}"
        else:
            new = text
        lines = list(self._lines)
        lines[index] = new
        self._change(lines)

    def delete(self, index, raw):
        index = self._find(index, raw)
        lines = list(self._lines)
        del lines[index]
        self._change(lines, "Deleted")

    def clear_done(self):
        lines = [line for line in self._lines
                 if not ((p := parse_line(line)) and p["kind"] == "task" and p["done"])]
        count = len(self._lines) - len(lines)
        if count:
            self._change(lines, f"Cleared {count}")

    def undo(self):
        if not self._undo:
            return
        before, after, _label = self._undo
        if self._text(self._lines) != after:
            raise Conflict("The file changed since then, so there's nothing to undo.")
        self._write(before.splitlines())
        self._undo = None

    def run(self, method, params):
        with self._lock:
            if method == "add":
                self.add(params.get("text"), params.get("kind", "task"))
            elif method == "toggle":
                self.toggle(int(params["line"]), params["raw"])
            elif method == "edit":
                self.edit(int(params["line"]), params["raw"], params.get("text"))
            elif method == "delete":
                self.delete(int(params["line"]), params["raw"])
            elif method == "clearDone":
                self.clear_done()
            elif method == "undo":
                self.undo()
            return self.snapshot()


def launch(argv):
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


class Backend:
    def __init__(self):
        self._notes = None
        self._draft = {"text": "", "kind": "task"}
        self._stop = threading.Event()
        self._ready = threading.Event()

    def _respond(self, message, ok, result=None, error=None):
        reply = {"type": "response", "id": message.get("id"), "ok": ok}
        if ok:
            reply["result"] = result
        else:
            reply["error"] = error
        send(reply)

    def _watch(self):
        """Pick up edits made to the file elsewhere."""
        self._ready.wait()
        while not self._stop.wait(POLL_SECONDS):
            if self._notes.reload():
                with self._notes._lock:
                    send({"type": "event", "name": "notes", "payload": self._notes.snapshot()})

    def _request(self, message):
        method = message.get("method")
        params = message.get("params") or {}
        notes = self._notes
        try:
            if method == "getNotes":
                notes.reload()
                with notes._lock:
                    result = dict(notes.snapshot(), draft=self._draft)
                self._respond(message, True, result)
            elif method == "setDraft":
                # Kept here, not in the page, so a host reload mid-typing keeps it.
                self._draft = {"text": str(params.get("text") or ""), "kind": params.get("kind", "task")}
                self._respond(message, True, None)
            elif method == "openFile":
                if not os.path.exists(notes.path):
                    with notes._lock:
                        notes._write(notes._lines)
                launch(["gio", "open", notes.path])
                self._respond(message, True, None)
            elif method == "openUrl":
                url = str(params.get("url") or "")
                if not re.match(r"^https?://", url):
                    raise ValueError("only http(s) links open")
                launch(["gio", "open", url])
                self._respond(message, True, None)
            else:
                self._respond(message, True, notes.run(method, params))
        except Conflict as e:
            notes.reload()
            with notes._lock:
                send({"type": "event", "name": "notes", "payload": notes.snapshot()})
            self._respond(message, False, error=str(e))
        except (KeyError, ValueError, OSError) as e:
            self._respond(message, False, error=str(e))

    def _handle(self, message):
        kind = message.get("type")
        if kind == "hello":
            config = message.get("config") or {}
            self._notes = Notes(config.get("file") or DEFAULT_FILE)
            self._ready.set()
        elif kind == "request":
            if not self._notes:  # a request before hello: use the default file
                self._notes = Notes(DEFAULT_FILE)
                self._ready.set()
            self._request(message)
        elif kind == "shutdown":
            self._stop.set()

    def run(self):
        threading.Thread(target=self._watch, daemon=True).start()
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if not line:  # host closed our stdin
                break
            try:
                self._handle(json.loads(line))
            except (ValueError, AttributeError):
                continue
        self._stop.set()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rice_theme
    rice_theme.watch(send)
    Backend().run()
