// Backend for the AI Usage widget. It imports api.js from the ai-usage-bar
// extension, so the panel and the widget fetch usage the same way.
//
// Gtk4-DING runs this with `gjs -m backend.js` and talks to it with one JSON
// object per line: hello/request/shutdown on stdin, response/event/log on stdout.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GioUnix from 'gi://GioUnix';

import {watchRiceTheme} from './riceTheme.js';

Gio._promisify(Gio.DataInputStream.prototype, 'read_line_async');

const API_PATH = GLib.build_filenamev([
    GLib.get_user_data_dir(), 'gnome-shell', 'extensions', 'ai-usage-bar@riz1', 'api.js',
]);
const DEFAULT_REFRESH_SECONDS = 300;
const MIN_REFRESH_SECONDS = 60;

// Same status pages as the panel extension.
const SERVICES = {
    claude: {name: 'Claude', statusApi: 'https://status.claude.com/api/v2/summary.json'},
    openai: {name: 'OpenAI', statusApi: 'https://status.openai.com/api/v2/summary.json'},
};

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

function buildProviders(claudeAccounts) {
    return [
        ...claudeAccounts.map(a => ({
            id: a.id,
            service: 'claude',
            icon: 'claude',
            name: a.tag ? `Claude ${a.tag}` : 'Claude',
            fetch: (api, c) => api.fetchClaude(a, c),
        })),
        {
            id: 'codex',
            service: 'openai',
            icon: 'codex',
            name: 'Codex',
            fetch: (api, c) => api.fetchCodex(c),
        },
    ];
}

class Backend {
    constructor(loop) {
        this._loop = loop;
        this._cancellable = new Gio.Cancellable();
        this._providers = [];
        this._state = new Map();
        this._status = {};
        this._updatedAt = 0;
        this._fatal = null;
        this._refreshing = null;
        this._timerId = 0;
        this._refreshSeconds = DEFAULT_REFRESH_SECONDS;
    }

    async start() {
        try {
            const module = await import(`file://${API_PATH}`);
            this._lib = module;
            this._api = new module.Api();
        } catch (e) {
            this._fatal = "Couldn't load api.js from the ai-usage-bar extension. Is it installed?";
            log('error', `importing ${API_PATH}: ${e.message}`);
        }
        this._readLoop();
        this._scheduleRefresh();
        await this.refresh();
    }

    _scheduleRefresh() {
        if (this._timerId)
            GLib.source_remove(this._timerId);
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, this._refreshSeconds, () => {
            this.refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    refresh() {
        if (!this._api)
            return Promise.resolve();
        this._refreshing ??= this._refreshInner().finally(() => {
            this._refreshing = null;
        });
        return this._refreshing;
    }

    async _refreshInner() {
        let accounts = null;
        try {
            accounts = await this._lib.discoverClaudeAccounts(this._cancellable);
        } catch (e) {
            if (isCancelled(e))
                return;
            log('warn', `account discovery: ${e}`);
        }
        if (accounts)
            this._providers = buildProviders(accounts);

        await Promise.all([
            ...this._providers.map(p => this._refreshUsage(p)),
            ...Object.keys(SERVICES).map(id => this._refreshStatus(id)),
        ]);
        if (this._cancellable.is_cancelled())
            return;
        this._updatedAt = Date.now();
        send({type: 'event', name: 'usage', payload: this.snapshot()});
    }

    async _refreshUsage(p) {
        const s = this._state.get(p.id) ?? {usage: null, usageAt: 0, error: null};
        this._state.set(p.id, s);
        try {
            s.usage = await p.fetch(this._api, this._cancellable);
            s.usageAt = Date.now();
            s.error = null;
        } catch (e) {
            if (isCancelled(e))
                return;
            // Keep the last good numbers and show the error next to them, like the panel does.
            s.error = e instanceof this._lib.UsageError ? e.message : `Fetch failed: ${e.message}`;
            if (!(e instanceof this._lib.UsageError))
                log('warn', `${p.id} usage: ${e}`);
        }
    }

    async _refreshStatus(serviceId) {
        try {
            this._status[serviceId] = await this._api.fetchStatus(
                SERVICES[serviceId].statusApi, this._cancellable);
        } catch (e) {
            if (!isCancelled(e))
                this._status[serviceId] = {indicator: 'unknown', description: 'Status unavailable', problems: []};
        }
    }

    snapshot() {
        return {
            error: this._fatal,
            updatedAt: this._updatedAt,
            providers: this._providers.map(p => {
                const s = this._state.get(p.id) ?? {};
                return {
                    id: p.id,
                    name: p.name,
                    service: p.service,
                    icon: p.icon,
                    plan: s.usage?.plan ?? null,
                    windows: (s.usage?.windows ?? []).map(w => ({
                        name: w.name,
                        short: w.short,
                        percent: w.percent,
                        resetsAt: w.resetsAt?.getTime() ?? null,
                    })),
                    notes: s.usage?.notes ?? [],
                    error: s.error ?? null,
                    usageAt: s.usageAt ?? 0,
                };
            }),
            status: Object.fromEntries(Object.entries(SERVICES).map(([id, service]) => [id, {
                name: service.name,
                ...(this._status[id] ?? {indicator: 'unknown', description: 'Checking status…', problems: []}),
            }])),
        };
    }

    async _readLoop() {
        const stdin = new Gio.DataInputStream({
            base_stream: new GioUnix.InputStream({fd: 0, close_fd: false}),
        });
        for (;;) {
            let line;
            try {
                [line] = await stdin.read_line_async(GLib.PRIORITY_DEFAULT, this._cancellable);
            } catch (e) {
                break;
            }
            if (line === null)  // host closed our stdin
                break;
            let message;
            try {
                message = JSON.parse(decoder.decode(line));
            } catch (e) {
                continue;
            }
            this._handle(message);
        }
        this.stop();
    }

    async _handle(message) {
        switch (message.type) {
        case 'hello': {
            const seconds = Number(message.config?.refreshSec ?? DEFAULT_REFRESH_SECONDS);
            this._refreshSeconds = Math.max(MIN_REFRESH_SECONDS, seconds || DEFAULT_REFRESH_SECONDS);
            this._scheduleRefresh();
            break;
        }
        case 'request': {
            const {id, method} = message;
            if (method === 'getUsage' || method === 'refresh') {
                if (method === 'refresh' || !this._updatedAt)
                    await this.refresh();
                send({type: 'response', id, ok: true, result: this.snapshot()});
            } else {
                send({type: 'response', id, ok: false, error: `unknown method ${JSON.stringify(method)}`});
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
        if (this._timerId)
            GLib.source_remove(this._timerId);
        this._api?.destroy();
        this._loop.quit();
    }
}

const riceTheme = watchRiceTheme(send);  // referenced so the file monitor keeps firing
const loop = new GLib.MainLoop(null, false);
new Backend(loop).start();
await loop.runAsync();
