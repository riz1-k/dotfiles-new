// rice-shell: the GNOME Shell side of rice (~/dotfiles/rice).
//
// - The bar (bar.js): rice-bar's floating islands and centre capsule.
// - Themes (theme.js): applies `rice theme set` inside the shell: stylesheet,
//   colour scheme, accent and wallpaper in one go, under a cross-fade. D-Bus
//   org.riz1.Rice at /org/riz1/Rice on org.gnome.Shell.
// - Pickers (picker.js): the theme carousel (Super+Ctrl+Shift+Space) and the
//   background carousel (Super+Ctrl+Space).
//
// It also runs on the lock screen, so the lock screen keeps the theme's
// stylesheet; the bar and the pickers are only there in the normal session.
//
// It replaces rice-bar (bar.js is rice-bar) and the user-theme extension (the
// shell stylesheet is theme.js's job) and switches them off when it starts. A new
// extension only loads at a login, so that's when the swap happens; the bar waits
// until they're gone so two bars never fight over the panel.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {ExtensionState} from 'resource:///org/gnome/shell/misc/extensionUtils.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {RiceBar} from './bar.js';
import {Carousel} from './picker.js';
import {ThemeManager} from './theme.js';

// Only exported when the shell runs with RICE_SHELL_DEBUG=1 (the nested-shell tests).
const DEBUG_IFACE = `
<node>
  <interface name="org.riz1.Rice.Debug">
    <method name="Screenshot"><arg type="s" direction="in" name="path"/></method>
    <method name="PickerMove"><arg type="i" direction="in" name="delta"/></method>
    <method name="PickerType"><arg type="s" direction="in" name="text"/></method>
    <method name="PickerActivate"/>
    <method name="PickerState"><arg type="s" direction="out" name="json"/></method>
  </interface>
</node>`;

const SUPERSEDES = ['rice-bar@riz1', 'user-theme@gnome-shell-extensions.gcampax.github.com'];
// States in which a superseded extension may still hold the panel or the stylesheet.
// GNOME sets DEACTIVATING before calling its disable(), INACTIVE after.
const BUSY = [ExtensionState.ACTIVE, ExtensionState.ACTIVATING, ExtensionState.DEACTIVATING];

const THEME_HINT = '←/→ move  ·  type to filter  ·  Enter apply  ·  Del remove  ·  Esc close';
const BACKGROUND_HINT = '←/→ move  ·  type to filter  ·  Enter set  ·  Esc close';

export default class RiceShellExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._rows = {theme: null, background: null};
        this._themes = new ThemeManager({
            theme: () => this._openPicker('theme'),
            background: () => this._openPicker('background'),
            invalidate: () => {
                this._rows.background = null;
                this._refresh('theme');
            },
        });
        this._themes.enable();

        this._retireSuperseded();
        Main.extensionManager.connectObject('extension-state-changed', (_m, extension) => {
            if (!SUPERSEDES.includes(extension.uuid))
                return;
            // user-theme's disable() resets the shell stylesheet to the default; the
            // state only leaves DEACTIVATING once disable() has returned.
            if (!BUSY.includes(extension.state))
                this._themes?.reloadStylesheet();
            this._syncSessionMode();
        }, this);
        Main.sessionMode.connectObject('updated', () => this._syncSessionMode(), this);
        this._syncSessionMode();
        // Warm the theme list so the first picker opens instantly.
        this._refresh('theme');

        if (GLib.getenv('RICE_SHELL_DEBUG') === '1') {
            this._debug = Gio.DBusExportedObject.wrapJSObject(DEBUG_IFACE, this._debugMethods());
            this._debug.export(Gio.DBus.session, '/org/riz1/Rice');
        }
    }

    _debugMethods() {
        return {
            ScreenshotAsync: ([path], invocation) => {
                const shot = new Shell.Screenshot();
                const stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.NONE, null);
                shot.screenshot(false, stream, (o, res) => {
                    try {
                        o.screenshot_finish(res);
                        stream.close(null);
                        invocation.return_value(null);
                    } catch (e) {
                        invocation.return_error_literal(Gio.DBusError, Gio.DBusError.FAILED, e.message);
                    }
                });
            },
            PickerMove: delta => this._picker?._move(delta),
            PickerType: text => this._picker?._setFilter(text),
            PickerActivate: () => this._picker?._activate(),
            PickerState: () => JSON.stringify(this._picker?.isOpen ? {
                kind: this._picker.kind,
                title: this._picker._title.text,
                detail: this._picker._detail.text,
                count: this._picker._count.text,
                filter: this._picker._filter,
            } : null),
        };
    }

    disable() {
        this._debug?.unexport();
        this._debug = null;
        Main.extensionManager.disconnectObject(this);
        Main.sessionMode.disconnectObject(this);
        this._disableSession();
        this._themes.disable();
        this._themes = null;
        this._settings = null;
        this._rows = null;
    }

    _retireSuperseded() {
        const enabled = global.settings.get_strv('enabled-extensions');
        const keep = enabled.filter(uuid => !SUPERSEDES.includes(uuid));
        if (keep.length !== enabled.length)
            global.settings.set_strv('enabled-extensions', keep);
    }

    _supersededActive() {
        return SUPERSEDES.some(uuid => BUSY.includes(Main.extensionManager.lookup(uuid)?.state));
    }

    // The bar, keybindings and pickers only in the normal session; the theme always.
    _syncSessionMode() {
        const locked = Main.sessionMode.isLocked || Main.sessionMode.currentMode === 'unlock-dialog';
        if (locked || this._supersededActive())
            this._disableSession();
        else
            this._enableSession();
    }

    _enableSession() {
        if (this._bar)
            return;
        const bar = new RiceBar(this.path);
        try {
            bar.enable();
        } catch (e) {
            // Undo whatever part of the bar got built; the theme and D-Bus keep working.
            console.error(`rice-shell: the bar failed to start: ${e.message}`);
            try {
                bar.disable();
            } catch (e2) {
                console.error(`rice-shell: cleaning up the bar: ${e2.message}`);
            }
            return;
        }
        this._bar = bar;
        const mode = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW;
        Main.wm.addKeybinding('theme-picker', this._settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, mode,
            () => this._openPicker('theme'));
        Main.wm.addKeybinding('background-picker', this._settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, mode,
            () => this._openPicker('background'));
    }

    _disableSession() {
        if (!this._bar)
            return;
        Main.wm.removeKeybinding('theme-picker');
        Main.wm.removeKeybinding('background-picker');
        this._picker?.destroy();
        this._picker = null;
        // A picker still fading out after being replaced: it has no grab left, but
        // its actor is still on the stage.
        for (const closing of this._closing ?? [])
            closing.destroy();
        this._closing = null;
        this._bar.disable();
        this._bar = null;
    }

    // ---- the rice CLI -------------------------------------------------------------

    _riceCommand() {
        const configured = this._settings.get_string('rice-command');
        if (configured)
            return configured;
        const home = GLib.get_home_dir();
        return GLib.find_program_in_path('rice') ??
            [`${home}/.local/bin/rice`, `${home}/dotfiles/rice/bin/rice`].find(p =>
                GLib.file_test(p, GLib.FileTest.IS_EXECUTABLE)) ?? 'rice';
    }

    _run(args) {
        return new Promise((resolve, reject) => {
            let proc;
            try {
                proc = Gio.Subprocess.new([this._riceCommand(), ...args],
                    Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            } catch (e) {
                reject(e);
                return;
            }
            proc.communicate_utf8_async(null, null, (p, result) => {
                try {
                    const [, stdout, stderr] = p.communicate_utf8_finish(result);
                    if (p.get_successful())
                        resolve(stdout);
                    else
                        reject(new Error((stderr || stdout || 'failed').trim().split('\n').pop()));
                } catch (e) {
                    reject(e);
                }
            });
        });
    }

    async _refresh(kind) {
        const args = kind === 'theme' ? ['theme', 'list', '--json', '--thumbs'] : ['bg', 'list', '--json', '--thumbs'];
        try {
            const rows = JSON.parse(await this._run(args));
            if (!this._rows)
                return null;
            this._rows[kind] = rows;
            if (this._picker?.isOpen && this._picker.kind === kind)
                this._picker.setRows(rows);
            return rows;
        } catch (e) {
            console.warn(`rice-shell: rice ${args.join(' ')}: ${e.message}`);
            return null;
        }
    }

    // ---- pickers ---------------------------------------------------------------------

    _openPicker(kind) {
        if (!this._bar || Main.sessionMode.isLocked)
            return;
        if (this._picker?.isOpen) {
            const same = this._picker.kind === kind;
            const old = this._picker;
            // Fading out: onClosed drops it from _closing (and only clears _picker if
            // it is still the current one, not its replacement).
            (this._closing ??= new Set()).add(old);
            old.close();
            if (same)
                return;  // the shortcut toggles its picker
        }
        const rows = this._rows[kind] ?? [];
        const current = rows.find(r => r.current);
        let picker = null;
        const common = {
            rows,
            key: r => r.name ?? r.path,
            image: r => r.thumb ?? r.preview ?? r.path ?? null,
            onClosed: () => {
                this._closing?.delete(picker);
                if (this._picker === picker)
                    this._picker = null;
            },
        };
        picker = this._picker = new Carousel(kind === 'theme' ? {
            ...common,
            heading: 'Theme',
            hint: THEME_HINT,
            empty: 'No themes (rice theme import-omarchy)',
            selectedKey: current?.name,
            key: r => r.name,
            label: r => r.display,
            detail: r => [r.mode, r.origin === 'omarchy' ? 'from Omarchy' : r.git ? 'installed' : null,
                r.current ? 'current' : null].filter(Boolean).join('  ·  '),
            canDelete: r => r.removable,
            onActivate: r => this._run(['theme', 'set', r.name]).catch(e => Main.notifyError('Rice', e.message)),
            onDelete: async r => {
                await this._run(['theme', 'remove', '--yes', r.name]);
                return this._refresh('theme');
            },
        } : {
            ...common,
            heading: 'Background',
            hint: BACKGROUND_HINT,
            empty: 'This theme has no backgrounds (rice bg open)',
            selectedKey: current?.path,
            key: r => r.path,
            label: r => r.name,
            detail: r => [r.user ? 'yours' : 'from the theme', r.current ? 'current' : null].filter(Boolean).join('  ·  '),
            canDelete: () => false,
            onActivate: r => this._run(['bg', 'set', r.path]).catch(e => Main.notifyError('Rice', e.message)),
        });
        picker.kind = kind;
        if (!picker.open()) {
            if (this._picker === picker)
                this._picker = null;
            return;
        }
        // Open from what we have, then refresh (new themes, new thumbnails).
        this._refresh(kind);
    }
}
