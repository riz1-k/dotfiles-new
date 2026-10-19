// Applying rice themes inside the shell.
//
// `rice theme set` stages the theme in ~/.local/state/rice/current/theme and then
// calls ApplyTheme over D-Bus. The shell stylesheet (a recoloured Yaru plus the bar
// colours) is swapped with Main.setThemeStylesheet, the way the user-theme
// extension does it, and the colour scheme, accent and wallpaper are set from the
// same call, so everything lands together. BeginTransition/EndTransition wrap the
// whole switch in a cross-fade from a snapshot of the screen, like GNOME's own
// Dark Style toggle.
//
// If a switch happens without D-Bus (no session bus in that process), the
// generation file changing is picked up a moment later.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Mtk from 'gi://Mtk';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export const VERSION = 'rice-shell 1';
export const STATE_DIR = GLib.build_filenamev([GLib.get_user_state_dir(), 'rice', 'current']);
const THEME_DIR = GLib.build_filenamev([STATE_DIR, 'theme']);

const TRANSITION_TIMEOUT_MS = 4000;  // a switch that never says it's done can't freeze the screen
const TRANSITION_FADE_MS = 420;
const FALLBACK_DELAY_MS = 1500;      // let the D-Bus call win; this only catches switches without one

const IFACE = `
<node>
  <interface name="org.riz1.Rice">
    <method name="Ping"><arg type="s" direction="out" name="version"/></method>
    <method name="ApplyTheme">
      <arg type="s" direction="in" name="generation"/>
      <arg type="b" direction="out" name="applied"/>
    </method>
    <method name="BeginTransition"/>
    <method name="EndTransition"/>
    <method name="OpenThemePicker"/>
    <method name="OpenBackgroundPicker"/>
    <method name="SetBackground"><arg type="s" direction="in" name="path"/></method>
    <method name="ReloadPalette"/>
    <signal name="ThemeApplied"><arg type="s" name="name"/></signal>
  </interface>
</node>`;

function readText(path) {
    try {
        const [, bytes] = GLib.file_get_contents(path);
        return new TextDecoder().decode(bytes);
    } catch {
        return null;
    }
}

function readJson(path) {
    const text = readText(path);
    if (text === null)
        return null;
    try {
        return JSON.parse(text);
    } catch {
        return null;
    }
}

export class ThemeManager {
    // pickers: {theme(), background()} open the carousels.
    constructor(pickers) {
        this._pickers = pickers;
    }

    enable() {
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._background = new Gio.Settings({schema_id: 'org.gnome.desktop.background'});
        this._screensaver = new Gio.Settings({schema_id: 'org.gnome.desktop.screensaver'});

        // At login the settings are already right; only the stylesheet is ours to load.
        this._loadStylesheet();
        this._generation = this._readGeneration();

        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, '/org/riz1/Rice');

        GLib.mkdir_with_parents(STATE_DIR, 0o755);
        try {
            this._monitor = Gio.File.new_for_path(STATE_DIR).monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, null);
            this._monitor.connect('changed', (_m, file, other) => {
                if (file?.get_basename() === 'theme.generation' || other?.get_basename() === 'theme.generation')
                    this._scheduleFallback();
            });
        } catch (e) {
            console.warn(`rice-shell: can't watch ${STATE_DIR}: ${e.message}`);
        }
    }

    disable() {
        this._endTransition(true);
        if (this._fallbackId) {
            GLib.source_remove(this._fallbackId);
            this._fallbackId = 0;
        }
        this._monitor?.cancel();
        this._monitor = null;
        this._dbus?.unexport();
        this._dbus = null;
        Main.setThemeStylesheet(null);
        Main.loadTheme();
        this._interface = null;
        this._background = null;
        this._screensaver = null;
    }

    // ---- D-Bus ---------------------------------------------------------------

    Ping() {
        return VERSION;
    }

    ApplyTheme(generation) {
        this._apply();
        this._generation = generation || this._readGeneration();
        return true;
    }

    BeginTransition() {
        if (Main.sessionMode.isLocked)
            return;
        const t = Main.layoutManager.screenTransition;
        if (!t.visible) {
            // GNOME's own transition actor: while it's up, a new wallpaper swaps in
            // without its usual one-second fade (background.js checks for it).
            Main.uiGroup.set_child_above_sibling(t, null);
            const rect = new Mtk.Rectangle({x: 0, y: 0, width: global.screen_width, height: global.screen_height});
            const [, , , scale] = global.stage.get_capture_final_size(rect);
            t.content = global.stage.paint_to_content(rect, scale, null, Clutter.PaintFlag.NO_CURSORS);
            t.remove_all_transitions();
            t.opacity = 255;
            t.show();
        }
        if (this._transitionId)
            GLib.source_remove(this._transitionId);
        this._transitionId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, TRANSITION_TIMEOUT_MS, () => {
            this._transitionId = 0;
            this._endTransition();
            return GLib.SOURCE_REMOVE;
        });
    }

    EndTransition() {
        this._endTransition();
    }

    OpenThemePicker() {
        this._pickers.theme();
    }

    OpenBackgroundPicker() {
        this._pickers.background();
    }

    SetBackground(path) {
        if (!GLib.path_is_absolute(path) || !GLib.file_test(path, GLib.FileTest.IS_REGULAR))
            throw new Error(`not a file: ${path}`);
        this._setBackground(path);
    }

    ReloadPalette() {
        this._apply();
    }

    // ---- applying --------------------------------------------------------------

    reloadStylesheet() {
        this._loadStylesheet();
    }

    _readGeneration() {
        return (readText(GLib.build_filenamev([STATE_DIR, 'theme.generation'])) ?? '').trim();
    }

    _loadStylesheet() {
        const css = GLib.build_filenamev([THEME_DIR, 'gnome-shell.css']);
        Main.setThemeStylesheet(GLib.file_test(css, GLib.FileTest.EXISTS) ? css : null);
        Main.loadTheme();
    }

    _apply() {
        const g = readJson(GLib.build_filenamev([THEME_DIR, 'gnome.json']));
        if (!g)
            throw new Error(`no theme in ${THEME_DIR}`);
        // The stylesheet first, so the reload a colour-scheme change triggers already uses it.
        this._loadStylesheet();
        if (g.accent && this._interface.get_string('accent-color') !== g.accent)
            this._interface.set_string('accent-color', g.accent);
        if (g.color_scheme && this._interface.get_string('color-scheme') !== g.color_scheme)
            this._interface.set_string('color-scheme', g.color_scheme);
        if (g.background && GLib.file_test(g.background, GLib.FileTest.IS_REGULAR))
            this._setBackground(g.background);
        this._dbus?.emit_signal('ThemeApplied', new GLib.Variant('(s)', [g.name ?? '']));
        this._pickers.invalidate?.();
    }

    _setBackground(path) {
        const uri = GLib.filename_to_uri(path, null);
        for (const [settings, key] of [[this._background, 'picture-uri'], [this._background, 'picture-uri-dark'],
            [this._screensaver, 'picture-uri']]) {
            if (settings.get_string(key) !== uri)
                settings.set_string(key, uri);
        }
    }

    _endTransition(now = false) {
        if (this._transitionId) {
            GLib.source_remove(this._transitionId);
            this._transitionId = 0;
        }
        const t = Main.layoutManager.screenTransition;
        if (!t?.visible)
            return;
        if (now) {
            t.remove_all_transitions();
            t.hide();
            return;
        }
        t.ease({
            opacity: 0,
            duration: TRANSITION_FADE_MS,
            delay: 40,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onStopped: () => t.hide(),
        });
    }

    _scheduleFallback() {
        if (this._fallbackId)
            GLib.source_remove(this._fallbackId);
        this._fallbackId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FALLBACK_DELAY_MS, () => {
            this._fallbackId = 0;
            const generation = this._readGeneration();
            if (generation && generation !== this._generation) {
                this._generation = generation;
                try {
                    this._apply();
                } catch (e) {
                    console.warn(`rice-shell: ${e.message}`);
                }
            }
            return GLib.SOURCE_REMOVE;
        });
    }
}
