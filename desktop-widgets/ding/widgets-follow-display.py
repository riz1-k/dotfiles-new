#!/usr/bin/python3 -I
"""Keeps the Gtk4-DING widgets on the external display when one is connected.

Gtk4-DING saves each widget against a monitor number and a position, so after
plugging in a screen the widgets stay on the laptop. This watches Mutter for
display changes and moves every widget to the first external display (or back
to the built-in one when it's gone), then restarts Gtk4-DING's desktop process
so it reads the new layout.

Positions are kept as offsets from the nearer side edge and from the top, in
~/.config/desktop-widgets/layout.json, and are relearned whenever you move a
widget yourself. Run by desktop-widgets-display.service.
"""
import json
import os
import signal
import subprocess
import sys

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

WIDGETS_JSON = os.path.join(GLib.get_user_data_dir(), "com.desktop.ding", "widgets.json")
LAYOUT_JSON = os.path.join(GLib.get_user_config_dir(), "desktop-widgets", "layout.json")
DING_PROCESS = "gtk4-ding@smedius.gitlab.com/app/adw-ding.js"
SETTLE_MS = 2000      # displays report several changes in a row when one is plugged in
QUIET_MS = 8000       # ignore widgets.json changes this long after we move things

display_config = Gio.DBusProxy.new_for_bus_sync(
    Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
    "org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig",
    "org.gnome.Mutter.DisplayConfig", None)


def log(message):
    print(message, flush=True)


def displays():
    """Logical monitors in Mutter's order, which is also Gtk4-DING's monitorIndex."""
    _serial, physical, logical, _props = display_config.call_sync(
        "GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None).unpack()
    builtin = {spec[0] for spec, _modes, props in physical if props.get("is-builtin")}
    sizes = {}
    for spec, modes, _props in physical:
        for mode in modes:
            if mode[6].get("is-current"):
                sizes[spec[0]] = (mode[1], mode[2])
    result = []
    for index, (x, y, scale, _transform, primary, monitors, _props) in enumerate(logical):
        connector = monitors[0][0]
        width, height = sizes.get(connector, (1920, 1080))
        result.append({"index": index, "x": x, "y": y, "width": round(width / scale),
                       "height": round(height / scale), "primary": primary,
                       "connector": connector, "builtin": connector in builtin})
    return result


def target_display(all_displays):
    external = [d for d in all_displays if not d["builtin"]]
    if external:
        return external[0]
    return next((d for d in all_displays if d["primary"]), all_displays[0])


def display_at(all_displays, x, y):
    for d in all_displays:
        if d["x"] <= x < d["x"] + d["width"] and d["y"] <= y < d["y"] + d["height"]:
            return d
    return None


def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def learn_layout():
    """Records where the widgets are now, relative to the display each one is on."""
    all_displays = displays()
    layout = read_json(LAYOUT_JSON, {})
    for inst in read_json(WIDGETS_JSON, {}).get("instances", []):
        x, y = inst.get("pinnedGlobalX"), inst.get("pinnedGlobalY")
        d = x is not None and y is not None and display_at(all_displays, x, y)
        if not d:
            continue
        from_left = x - d["x"]
        from_right = d["x"] + d["width"] - (x + inst["width"])
        layout[inst["instanceId"]] = {
            "anchor": "left" if from_left <= from_right else "right",
            "dx": min(from_left, from_right),
            "dy": y - d["y"],
        }
    write_json(LAYOUT_JSON, layout)


def apply_layout():
    """Moves every widget onto the target display. True if anything moved."""
    all_displays = displays()
    target = target_display(all_displays)
    layout = read_json(LAYOUT_JSON, {})
    widgets = read_json(WIDGETS_JSON, None)
    if not widgets:
        return False
    moved = False
    for inst in widgets.get("instances", []):
        place = layout.get(inst["instanceId"])
        if not place:
            continue
        width, height = inst["width"], inst["height"]
        if place["anchor"] == "left":
            x = target["x"] + place["dx"]
        else:
            x = target["x"] + target["width"] - width - place["dx"]
        x = min(max(x, target["x"]), target["x"] + target["width"] - width)
        y = min(max(target["y"] + place["dy"], target["y"]), target["y"] + target["height"] - height)
        new = {"monitorIndex": target["index"], "pinnedGlobalX": x, "pinnedGlobalY": y,
               "normX": (x - target["x"]) / target["width"], "normY": inst.get("normY", 0)}
        if any(inst.get(key) != value for key, value in new.items() if key != "normY"):
            inst.update(new)
            moved = True
    if moved:
        write_json(WIDGETS_JSON, widgets)
        log(f"moved widgets to {target['connector']} (monitor {target['index']})")
    return moved


def restart_ding():
    # SIGKILL, so it can't save its old layout over ours on the way out; the
    # extension relaunches it straight away and it reads widgets.json again.
    result = subprocess.run(["pgrep", "-f", DING_PROCESS], capture_output=True, text=True)
    for pid in result.stdout.split():
        os.kill(int(pid), signal.SIGKILL)


class Follower:
    def __init__(self):
        self._settle_id = 0
        self._quiet_until = 0
        self._monitor = Gio.File.new_for_path(WIDGETS_JSON).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self._on_widgets_changed)
        display_config.connect("g-signal", self._on_signal)
        if not os.path.exists(LAYOUT_JSON):
            learn_layout()
        self._settle()

    def _on_signal(self, _proxy, _sender, signal_name, _params):
        if signal_name == "MonitorsChanged":
            self._quiet_until = GLib.get_monotonic_time() + QUIET_MS * 1000
            if self._settle_id:
                GLib.source_remove(self._settle_id)
            self._settle_id = GLib.timeout_add(SETTLE_MS, self._settle)

    def _settle(self):
        self._settle_id = 0
        try:
            if apply_layout():
                self._quiet_until = GLib.get_monotonic_time() + QUIET_MS * 1000
                restart_ding()
        except GLib.Error as e:
            log(f"display change: {e.message}")
        return GLib.SOURCE_REMOVE

    def _on_widgets_changed(self, _monitor, _file, _other, event):
        # You moved or resized a widget: remember it. Our own writes, and Gtk4-DING
        # shuffling things while displays change, fall inside the quiet period.
        # Gtk4-DING may rewrite the file in place or replace it, which report differently.
        if event not in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED,
                         Gio.FileMonitorEvent.RENAMED, Gio.FileMonitorEvent.MOVED_IN):
            return
        if GLib.get_monotonic_time() < self._quiet_until:
            return
        try:
            learn_layout()
        except GLib.Error as e:
            log(f"learning layout: {e.message}")


if __name__ == "__main__":
    if "--print" in sys.argv:
        print(json.dumps({"displays": displays(), "target": target_display(displays())}, indent=2))
        sys.exit()
    Follower()
    GLib.MainLoop().run()
