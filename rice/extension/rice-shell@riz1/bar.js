// The top bar as three floating islands that line up with the desktop widgets
// (from rice-bar). Left: workspaces and the focused app. Right: the status icons.
// Centre: a capsule in the clock's place that shows, in order of priority, a
// notification for a few seconds, a meeting about to start, the music that's
// playing, or the date and time. Clicking it still opens GNOME's calendar menu.
//
// Layout is in stylesheet.css; colours come from the theme (rice-bar.css, which
// rice appends to the shell stylesheet of every theme).
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GnomeDesktop from 'gi://GnomeDesktop';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Pango from 'gi://Pango';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as Mpris from 'resource:///org/gnome/shell/ui/mpris.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

const MEETING_LEAD_MS = 10 * 60 * 1000;   // show a meeting this long before it starts
const MEETING_GRACE_MS = 5 * 60 * 1000;   // and until this long after
const FLASH_MS = 5000;                     // how long a notification stays in the capsule
const FADE_MS = 140;

const FocusedApp = GObject.registerClass(
class FocusedApp extends PanelMenu.Button {
    _init() {
        super._init(0, 'Focused app', true);
        this.add_style_class_name('rice-app');
        this.setSensitive(false);

        const box = new St.BoxLayout({style_class: 'rice-app-box'});
        box.add_child(new St.Widget({style_class: 'rice-sep', y_align: Clutter.ActorAlign.CENTER}));
        this._label = new St.Label({y_align: Clutter.ActorAlign.CENTER});
        this._label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        box.add_child(this._label);
        this.add_child(box);

        this._tracker = Shell.WindowTracker.get_default();
        global.display.connectObject('notify::focus-window', () => this._sync(), this);
        this._tracker.connectObject('notify::focus-app', () => this._sync(), this);
        this._sync();
    }

    _sync() {
        const win = global.display.focus_window;
        // The desktop (Gtk4-DING) and its widgets are windows too; they aren't "the app".
        if (!win || win.skip_taskbar || win.get_window_type() !== Meta.WindowType.NORMAL) {
            this.hide();
            return;
        }
        this._label.text = this._tracker.get_window_app(win)?.get_name() ?? win.title ?? '';
        this.visible = this._label.text !== '';
    }
});

// The capsule's contents: an optional badge, then lead · main · trail labels.
const Capsule = GObject.registerClass(
class Capsule extends St.BoxLayout {
    _init() {
        super._init({style_class: 'rice-capsule-box', y_align: Clutter.ActorAlign.CENTER});

        this._badge = new St.Bin({style_class: 'rice-badge', y_align: Clutter.ActorAlign.CENTER});
        this._badgeIcon = new St.Icon({style_class: 'rice-badge-icon'});
        this._badge.set_child(this._badgeIcon);
        this._lead = this._label('rice-lead');
        this._main = this._label('rice-main');
        this._trail = this._label('rice-trail');
        this.add_child(this._badge);
        this.add_child(this._lead);
        this.add_child(this._main);
        this.add_child(this._trail);
        this._key = null;
    }

    _label(styleClass) {
        const label = new St.Label({style_class: styleClass, y_align: Clutter.ActorAlign.CENTER});
        label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        return label;
    }

    // state: {kind, lead, main, trail, gicon, image}. A new kind, or a new title within
    // one, fades the old content out and the new in; the ticking clock updates in place.
    show(state) {
        const key = state.kind === 'idle' ? 'idle' : `${state.kind}\n${state.main}`;
        if (this._key === null || key === this._key) {
            this._key = key;
            this._apply(state);
            return;
        }
        this._key = key;
        this._pending = state;
        if (this._fading)
            return;
        this._fading = true;
        this.ease({
            opacity: 0,
            duration: FADE_MS,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onComplete: () => {
                this._fading = false;
                this._apply(this._pending);
                this.ease({opacity: 255, duration: FADE_MS, mode: Clutter.AnimationMode.EASE_IN_QUAD});
            },
        });
    }

    _apply({kind, lead = '', main = '', trail = '', gicon = null, image = null}) {
        for (const k of ['idle', 'media', 'meeting', 'flash'])
            this[k === kind ? 'add_style_class_name' : 'remove_style_class_name'](`rice-${k}`);

        this._badge.visible = Boolean(gicon || image);
        this._badge.style = image ? `background-image: url("${image}");` : null;
        this._badgeIcon.visible = !image;
        this._badgeIcon.gicon = image ? null : gicon;

        for (const [label, text] of [[this._lead, lead], [this._main, main], [this._trail, trail]]) {
            label.text = text;
            label.visible = text !== '';
        }
    }
});

export class RiceBar {
    constructor(path) {
        this._path = path;
    }

    enable() {
        // Everything _sync() reads, before anything that can call it.
        this._events = [];
        this._flash = null;
        this._players = new Set();
        this._sources = new Set();

        this._panel = Main.panel;
        this._dateMenu = this._panel.statusArea.dateMenu;

        Main.layoutManager.panelBox.add_style_class_name('rice-bar-box');
        this._panel.add_style_class_name('rice-bar');
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._interface.connectObject('changed::clock-format', () => this._sync(), this);

        this._app = new FocusedApp();
        this._panel.addToStatusArea('rice-bar-app', this._app, 1, 'left');

        // The capsule takes the clock's place inside the date menu button, so the
        // button, its menu and the unread-notifications dot all keep working.
        this._capsule = new Capsule();
        this._dateMenu.add_style_class_name('rice-capsule');
        this._dateMenu._clockDisplay.hide();
        this._dateMenu._clockDisplay.get_parent().insert_child_above(this._capsule, this._dateMenu._clockDisplay);

        this._clock = new GnomeDesktop.WallClock();
        this._clock.connectObject('notify::clock', () => this._sync(), this);

        this._watchMedia();
        this._watchNotifications();
        this._startCalendarHelper();

        this._sync();
    }

    // Also undoes a partial enable() (one that threw), so every step checks.
    disable() {
        this._stopCalendarHelper();

        if (this._flashTimeout) {
            GLib.source_remove(this._flashTimeout);
            this._flashTimeout = 0;
        }
        this._flash = null;
        Main.messageTray.disconnectObject(this);
        for (const source of this._sources ?? [])
            source.disconnectObject(this);
        this._sources = null;

        this._media?.disconnectObject(this);
        for (const player of this._players ?? [])
            player.disconnectObject(this);
        this._players = null;
        this._media = null;

        this._clock?.disconnectObject(this);
        this._clock = null;

        this._capsule?.destroy();
        this._capsule = null;
        this._dateMenu?._clockDisplay.show();
        this._dateMenu?.remove_style_class_name('rice-capsule');

        this._app?.destroy();
        this._app = null;

        this._interface?.disconnectObject(this);
        this._interface = null;
        this._panel?.remove_style_class_name('rice-bar');
        Main.layoutManager.panelBox.remove_style_class_name('rice-bar-box');
        this._panel = null;
        this._dateMenu = null;
    }

    // ---- media ------------------------------------------------------------

    _watchMedia() {
        // The calendar menu already watches the players for its media card; share it.
        this._media = this._dateMenu._messageList?._messageView?._mediaSource ?? new Mpris.MprisSource();
        this._players = new Set();
        this._media.connectObject(
            'player-added', (_, player) => this._addPlayer(player),
            'player-removed', (_, player) => {
                player.disconnectObject(this);
                this._players.delete(player);
                this._sync();
            },
            this);
        this._media.players.forEach(player => this._addPlayer(player));
    }

    _addPlayer(player) {
        if (this._players.has(player))
            return;
        this._players.add(player);
        player.connectObject('changed', () => this._sync(), this);
        this._sync();
    }

    _mediaState() {
        const player = [...this._players].find(p => p.canPlay && p.status === 'Playing');
        if (!player)
            return null;
        const art = player.trackCoverUrl;
        return {
            kind: 'media',
            main: player.trackTitle,
            trail: player.trackArtists?.join(', ') ?? '',
            // Browsers and most players hand over a cached file; anything else gets the app's icon.
            image: art?.startsWith('file://') ? art : null,
            gicon: player.app?.get_icon() ?? new Gio.ThemedIcon({name: 'audio-x-generic-symbolic'}),
        };
    }

    // ---- notifications -----------------------------------------------------

    _watchNotifications() {
        this._sources = new Set();
        Main.messageTray.connectObject(
            'source-added', (_, source) => this._watchSource(source),
            'source-removed', (_, source) => {
                source.disconnectObject(this);
                this._sources.delete(source);
            },
            this);
        Main.messageTray.getSources().forEach(source => this._watchSource(source));
    }

    _watchSource(source) {
        this._sources.add(source);
        source.connectObject('notification-request-banner', (_, notification) => {
            // Same rule as the banners: muted apps and Do Not Disturb only let critical ones through.
            if (!source.policy.showBanners && notification.urgency !== MessageTray.Urgency.CRITICAL)
                return;
            this._showFlash(notification);
        }, this);
    }

    _showFlash(notification) {
        const body = (notification.body ?? '').replace(/<[^>]*>/g, '').split('\n')[0].trim();
        this._flash = {
            kind: 'flash',
            main: notification.title || notification.source?.title || '',
            trail: body,
            gicon: notification.gicon ?? notification.source?.icon ??
                new Gio.ThemedIcon({name: 'preferences-system-notifications-symbolic'}),
        };
        if (this._flashTimeout)
            GLib.source_remove(this._flashTimeout);
        this._flashTimeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FLASH_MS, () => {
            this._flashTimeout = 0;
            this._flash = null;
            this._sync();
            return GLib.SOURCE_REMOVE;
        });
        this._sync();
    }

    // ---- calendar ----------------------------------------------------------

    _startCalendarHelper() {
        const helper = GLib.getenv('RICE_BAR_CALENDAR_HELPER') ?? `${this._path}/calendar_helper.py`;
        try {
            this._helper = Gio.Subprocess.new(['python3', '-I', helper],
                Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE);
        } catch (e) {
            console.warn(`rice-shell: calendar helper failed to start: ${e.message}`);
            return;
        }
        this._helperCancel = new Gio.Cancellable();
        this._helperOut = new Gio.DataInputStream({base_stream: this._helper.get_stdout_pipe()});
        this._readHelper();
    }

    _readHelper() {
        this._helperOut.read_line_async(GLib.PRIORITY_DEFAULT, this._helperCancel, (stream, result) => {
            let line;
            try {
                [line] = stream.read_line_finish_utf8(result);
            } catch (e) {
                if (!e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    console.warn(`rice-shell: calendar helper: ${e.message}`);
                return;
            }
            if (line === null)
                return;  // the helper exited
            try {
                this._events = JSON.parse(line).events ?? [];
                this._sync();
            } catch (e) {
                console.warn(`rice-shell: bad calendar helper output: ${e.message}`);
            }
            this._readHelper();
        });
    }

    _stopCalendarHelper() {
        this._helperCancel?.cancel();
        // Closing stdin tells the helper to exit.
        this._helper?.get_stdin_pipe()?.close(null);
        this._helper = null;
        this._helperOut = null;
        this._helperCancel = null;
    }

    _meetingState(now) {
        const event = this._events.find(e => e.start - MEETING_LEAD_MS <= now && now < e.start + MEETING_GRACE_MS);
        if (!event)
            return null;
        const minutes = Math.ceil((event.start - now) / 60000);
        return {
            kind: 'meeting',
            main: event.title,
            trail: minutes > 0 ? `in ${minutes}m` : 'now',
            gicon: new Gio.ThemedIcon({name: 'x-office-calendar-symbolic'}),
        };
    }

    // ---- capsule -----------------------------------------------------------

    _idleState() {
        const now = GLib.DateTime.new_now_local();
        const twelveHour = this._interface.get_string('clock-format') === '12h';
        return {
            kind: 'idle',
            lead: now.format('%a %-d %b'),
            main: now.format(twelveHour ? '%-l:%M %p' : '%H:%M'),
        };
    }

    _sync() {
        if (!this._capsule)
            return;
        const state = this._flash ?? this._meetingState(Date.now()) ?? this._mediaState() ?? this._idleState();
        this._capsule.show(state);
    }
}
