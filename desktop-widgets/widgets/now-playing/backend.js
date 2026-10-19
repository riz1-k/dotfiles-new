// Backend for the Now Playing widget. Follows the MPRIS players on the session
// bus (Zen, Spotify, mpv...) and pushes the active one's track to the widget.
//
// Gtk4-DING runs this with `gjs -m backend.js` and talks to it with one JSON
// object per line: hello/request/shutdown on stdin, response/event/log on stdout.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GioUnix from 'gi://GioUnix';
import GdkPixbuf from 'gi://GdkPixbuf';
import Soup from 'gi://Soup?version=3.0';

import {watchRiceTheme} from './riceTheme.js';

Gio._promisify(Gio.DataInputStream.prototype, 'read_line_async');
Gio._promisify(Gio.DBusConnection.prototype, 'call');
Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Soup.Session.prototype, 'send_and_read_async');

const MPRIS_PREFIX = 'org.mpris.MediaPlayer2.';
const MPRIS_PATH = '/org/mpris/MediaPlayer2';
const ROOT_IFACE = 'org.mpris.MediaPlayer2';
const PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player';

// Players don't signal Position changes, so poll it while playing and only push
// when it drifts from what the widget is extrapolating.
const RESYNC_SECONDS = 5;
const DRIFT_US = 1.5e6;

// The widget can only show data: images. Art is scaled down before encoding so
// state events stay small.
const ART_SIZE = 192;
const MAX_ART_BYTES = 8 * 1024 * 1024;

const encoder = new TextEncoder();
const decoder = new TextDecoder();
const stdout = new GioUnix.OutputStream({fd: 1, close_fd: false});

function send(message) {
    stdout.write_all(encoder.encode(`${JSON.stringify(message)}\n`), null);
    stdout.flush(null);
}

function log(level, message) {
    send({type: 'log', level, message});
}

function isCancelled(e) {
    return e?.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED);
}

class Player {
    constructor(busName, owner) {
        this.busName = busName;
        this.owner = owner;
        this.identity = busName.slice(MPRIS_PREFIX.length).split('.')[0];
        this.props = {};
        this.positionUs = 0;
        this.positionAt = Date.now();
        this.lastActive = 0;
        this.signalIds = [];
    }

    get status() {
        return this.props.PlaybackStatus ?? 'Stopped';
    }

    get metadata() {
        return this.props.Metadata ?? {};
    }

    setPosition(us) {
        this.positionUs = Number(us) || 0;
        this.positionAt = Date.now();
    }

    expectedPosition() {
        if (this.status !== 'Playing')
            return this.positionUs;
        return this.positionUs + (Date.now() - this.positionAt) * 1000 * (this.props.Rate ?? 1);
    }
}

function encodeArt(bytes) {
    if (bytes.length > MAX_ART_BYTES)
        throw new Error(`art is ${bytes.length} bytes`);
    const loader = new GdkPixbuf.PixbufLoader();
    loader.write_bytes(new GLib.Bytes(bytes));
    loader.close();
    let pixbuf = loader.get_pixbuf();
    const scale = ART_SIZE / Math.min(pixbuf.width, pixbuf.height);
    if (scale < 1) {
        pixbuf = pixbuf.scale_simple(Math.round(pixbuf.width * scale),
            Math.round(pixbuf.height * scale), GdkPixbuf.InterpType.BILINEAR);
    }
    const [format, type] = pixbuf.hasAlpha ? ['png', 'image/png'] : ['jpeg', 'image/jpeg'];
    const [, buffer] = format === 'jpeg'
        ? pixbuf.save_to_bufferv(format, ['quality'], ['90'])
        : pixbuf.save_to_bufferv(format, [], []);
    return `data:${type};base64,${GLib.base64_encode(buffer)}`;
}

class Backend {
    constructor(loop) {
        this._loop = loop;
        this._bus = Gio.DBus.session;
        this._cancellable = new Gio.Cancellable();
        this._http = new Soup.Session({timeout: 15});
        this._players = new Map();
        this._selected = null;
        this._art = {url: null, data: null};
        this._pushId = 0;
        this._resyncId = 0;
        this._nameOwnerId = 0;
    }

    async start() {
        this._readLoop();
        this._nameOwnerId = this._bus.signal_subscribe('org.freedesktop.DBus', 'org.freedesktop.DBus',
            'NameOwnerChanged', '/org/freedesktop/DBus', 'org.mpris.MediaPlayer2',
            Gio.DBusSignalFlags.MATCH_ARG0_NAMESPACE,
            (_conn, _sender, _path, _iface, _signal, params) => {
                const [name, oldOwner, newOwner] = params.deepUnpack();
                if (oldOwner)
                    this._removePlayer(name);
                if (newOwner)
                    this._addPlayer(name, newOwner);
            });

        try {
            const [names] = (await this._call('org.freedesktop.DBus', '/org/freedesktop/DBus',
                'org.freedesktop.DBus', 'ListNames')).deepUnpack();
            await Promise.all(names.filter(n => n.startsWith(MPRIS_PREFIX)).map(async name => {
                const [owner] = (await this._call('org.freedesktop.DBus', '/org/freedesktop/DBus',
                    'org.freedesktop.DBus', 'GetNameOwner', new GLib.Variant('(s)', [name]))).deepUnpack();
                await this._addPlayer(name, owner);
            }));
        } catch (e) {
            if (!isCancelled(e))
                log('warn', `listing players: ${e.message}`);
        }

        this._resyncId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, RESYNC_SECONDS, () => {
            this._resyncPosition();
            return GLib.SOURCE_CONTINUE;
        });
        this._schedulePush();
    }

    _call(dest, path, iface, method, params = null) {
        return this._bus.call(dest, path, iface, method, params, null,
            Gio.DBusCallFlags.NO_AUTO_START, 5000, this._cancellable);
    }

    async _getAll(player, iface) {
        try {
            const reply = await this._call(player.owner, MPRIS_PATH, 'org.freedesktop.DBus.Properties',
                'GetAll', new GLib.Variant('(s)', [iface]));
            return reply.recursiveUnpack()[0];
        } catch (e) {
            if (!isCancelled(e))
                log('warn', `${player.busName} ${iface}: ${e.message}`);
            return {};
        }
    }

    async _addPlayer(busName, owner) {
        if (!busName.startsWith(MPRIS_PREFIX))
            return;
        this._removePlayer(busName);
        const player = new Player(busName, owner);
        this._players.set(busName, player);

        player.signalIds.push(this._bus.signal_subscribe(owner, 'org.freedesktop.DBus.Properties',
            'PropertiesChanged', MPRIS_PATH, null, Gio.DBusSignalFlags.NONE,
            (_conn, _sender, _path, _iface, _signal, params) => this._onPropertiesChanged(player, params)));
        player.signalIds.push(this._bus.signal_subscribe(owner, PLAYER_IFACE, 'Seeked', MPRIS_PATH,
            null, Gio.DBusSignalFlags.NONE, (_conn, _sender, _path, _iface, _signal, params) => {
                player.setPosition(params.deepUnpack()[0]);
                this._schedulePush();
            }));

        const [root, props] = await Promise.all([
            this._getAll(player, ROOT_IFACE),
            this._getAll(player, PLAYER_IFACE),
        ]);
        if (this._players.get(busName) !== player)
            return;
        player.identity = root.Identity || player.identity;
        Object.assign(player.props, props);
        player.setPosition(props.Position);
        if (player.status === 'Playing')
            player.lastActive = Date.now();
        this._schedulePush();
    }

    _removePlayer(busName) {
        const player = this._players.get(busName);
        if (!player)
            return;
        player.signalIds.forEach(id => this._bus.signal_unsubscribe(id));
        this._players.delete(busName);
        if (this._selected === busName)
            this._selected = null;
        this._schedulePush();
    }

    _onPropertiesChanged(player, params) {
        const [iface, changed, invalidated] = params.recursiveUnpack();
        if (iface === ROOT_IFACE && changed.Identity) {
            player.identity = changed.Identity;
        } else if (iface === PLAYER_IFACE) {
            Object.assign(player.props, changed);
            if ('Position' in changed)
                player.setPosition(changed.Position);
            if (player.status === 'Playing' && ('PlaybackStatus' in changed || 'Metadata' in changed))
                player.lastActive = Date.now();
            // Pausing, skipping or changing speed moves the position without a Seeked signal.
            if ('PlaybackStatus' in changed || 'Metadata' in changed || 'Rate' in changed)
                this._syncPosition(player);
            if (invalidated.length) {
                this._getAll(player, PLAYER_IFACE).then(props => {
                    Object.assign(player.props, props);
                    this._schedulePush();
                });
            }
        }
        this._schedulePush();
    }

    async _readPosition(player) {
        try {
            const reply = await this._call(player.owner, MPRIS_PATH, 'org.freedesktop.DBus.Properties',
                'Get', new GLib.Variant('(ss)', [PLAYER_IFACE, 'Position']));
            return Number(reply.recursiveUnpack()[0]);
        } catch {
            return null;  // some players don't implement Position
        }
    }

    async _syncPosition(player) {
        const position = await this._readPosition(player);
        if (position === null)
            return;
        player.setPosition(position);
        this._schedulePush();
    }

    async _resyncPosition() {
        const player = this._activePlayer();
        if (player?.status !== 'Playing')
            return;
        const position = await this._readPosition(player);
        if (position === null || Math.abs(position - player.expectedPosition()) < DRIFT_US)
            return;
        player.setPosition(position);
        this._schedulePush();
    }

    // A player the user switched to stays active unless it stops playing while
    // another one is; otherwise the most recently playing player wins.
    _activePlayer() {
        const players = [...this._players.values()];
        const anyPlaying = players.some(p => p.status === 'Playing');
        const selected = this._players.get(this._selected);
        if (selected && (selected.status === 'Playing' || !anyPlaying))
            return selected;
        const rank = p => ({Playing: 2, Paused: 1}[p.status] ?? 0);
        return players.sort((a, b) => rank(b) - rank(a) || b.lastActive - a.lastActive)[0] ?? null;
    }

    _schedulePush() {
        // Coalesce the bursts of PropertiesChanged signals players send on track changes.
        if (this._pushId || this._stopped)
            return;
        this._pushId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
            this._pushId = 0;
            this._updateArt();
            send({type: 'event', name: 'state', payload: this.snapshot()});
            return GLib.SOURCE_REMOVE;
        });
    }

    async _updateArt() {
        const url = this._activePlayer()?.metadata['mpris:artUrl'] || null;
        if (url === this._art.url)
            return;
        this._art = {url, data: null};
        if (!url)
            return;
        let data = null;
        try {
            data = await this._loadArt(url);
        } catch (e) {
            if (isCancelled(e))
                return;
            log('warn', `art ${url.slice(0, 120)}: ${e.message}`);
        }
        if (this._art.url !== url)
            return;
        this._art.data = data;
        this._schedulePush();
    }

    async _loadArt(url) {
        if (url.startsWith('file://')) {
            const [bytes] = await Gio.File.new_for_uri(url).load_contents_async(this._cancellable);
            return encodeArt(bytes);
        }
        if (url.startsWith('https://') || url.startsWith('http://')) {
            const message = Soup.Message.new('GET', url);
            const body = await this._http.send_and_read_async(message, GLib.PRIORITY_DEFAULT, this._cancellable);
            if (message.get_status() !== Soup.Status.OK)
                throw new Error(`HTTP ${message.get_status()}`);
            return encodeArt(body.toArray());
        }
        if (url.startsWith('data:image/'))
            return url;
        throw new Error('unsupported art URL');
    }

    snapshot() {
        const p = this._activePlayer();
        if (!p)
            return {player: null, playerCount: 0};
        const m = p.metadata;
        const artUrl = m['mpris:artUrl'] || null;
        return {
            playerCount: this._players.size,
            player: {
                id: p.busName,
                name: p.identity,
                status: p.status,
                title: m['xesam:title'] ?? '',
                artist: [].concat(m['xesam:artist'] ?? []).filter(Boolean).join(', '),
                album: m['xesam:album'] ?? '',
                art: artUrl && this._art.url === artUrl ? this._art.data : null,
                lengthUs: Number(m['mpris:length'] ?? 0),
                positionUs: p.positionUs,
                positionAt: p.positionAt,
                rate: p.props.Rate ?? 1,
                canPlayPause: Boolean(p.props.CanPlay || p.props.CanPause),
                canGoPrevious: Boolean(p.props.CanGoPrevious),
                canGoNext: Boolean(p.props.CanGoNext),
            },
        };
    }

    async _control(method) {
        const player = this._activePlayer();
        if (!player)
            return;
        this._selected = player.busName;
        await this._call(player.owner, MPRIS_PATH, PLAYER_IFACE, method);
    }

    _switchPlayer() {
        const names = [...this._players.keys()].sort();
        if (names.length < 2)
            return;
        const current = names.indexOf(this._activePlayer()?.busName);
        this._selected = names[(current + 1) % names.length];
        this._updateArt();
    }

    async _readLoop() {
        const stdin = new Gio.DataInputStream({
            base_stream: new GioUnix.InputStream({fd: 0, close_fd: false}),
        });
        for (;;) {
            let line;
            try {
                [line] = await stdin.read_line_async(GLib.PRIORITY_DEFAULT, this._cancellable);
            } catch {
                break;
            }
            if (line === null)  // host closed our stdin
                break;
            let message;
            try {
                message = JSON.parse(decoder.decode(line));
            } catch {
                continue;
            }
            this._handle(message);
        }
        this.stop();
    }

    async _handle(message) {
        switch (message.type) {
        case 'request': {
            const {id, method} = message;
            const controls = {playPause: 'PlayPause', next: 'Next', previous: 'Previous'};
            try {
                if (method in controls)
                    await this._control(controls[method]);
                else if (method === 'switchPlayer')
                    this._switchPlayer();
                else if (method !== 'getState')
                    throw new Error(`unknown method ${JSON.stringify(method)}`);
                send({type: 'response', id, ok: true, result: this.snapshot()});
            } catch (e) {
                send({type: 'response', id, ok: false, error: e.message});
            }
            break;
        }
        case 'shutdown':
            this.stop();
            break;
        }
    }

    stop() {
        if (this._stopped)
            return;
        this._stopped = true;
        this._cancellable.cancel();
        for (const id of [this._pushId, this._resyncId]) {
            if (id)
                GLib.source_remove(id);
        }
        if (this._nameOwnerId)
            this._bus.signal_unsubscribe(this._nameOwnerId);
        for (const name of [...this._players.keys()])
            this._removePlayer(name);
        this._http.abort();
        this._loop.quit();
    }
}

const riceTheme = watchRiceTheme(send);  // referenced so the file monitor keeps firing
const loop = new GLib.MainLoop(null, false);
new Backend(loop).start();
await loop.runAsync();
