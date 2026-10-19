import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {Api, UsageError, discoverClaudeAccounts} from './api.js';

const REFRESH_SECONDS = 180;
const STALE_MS = 15 * 60 * 1000;
const BAR_WIDTH = 110;
// Only these providers get a chip in the panel; the rest stay in the dropdown.
const PANEL_PROVIDERS = new Set(['claude:.claude']);

const SERVICES = {
    claude: {
        name: 'Claude',
        statusApi: 'https://status.claude.com/api/v2/summary.json',
        statusPage: 'https://status.claude.com',
    },
    openai: {
        name: 'OpenAI',
        statusApi: 'https://status.openai.com/api/v2/summary.json',
        statusPage: 'https://status.openai.com',
    },
};

function buildProviders(claudeAccounts) {
    return [
        ...claudeAccounts.map(a => ({
            id: a.id,
            service: 'claude',
            name: a.tag ? `Claude ${a.tag}` : 'Claude',
            tag: a.tag,
            subtitle: a.email,
            icon: 'claude.svg',
            fetch: (api, c) => api.fetchClaude(a, c),
            usagePage: 'https://claude.ai/settings/usage',
        })),
        {
            id: 'codex',
            service: 'openai',
            name: 'Codex',
            tag: '',
            subtitle: null,
            icon: 'codex.svg',
            fetch: (api, c) => api.fetchCodex(c),
            usagePage: 'https://chatgpt.com/codex/settings/usage',
        },
    ];
}

function accountsKey(accounts) {
    return accounts.map(a => `${a.id}|${a.email}`).join(',');
}

function levelClass(percent) {
    if (percent >= 95)
        return 'ai-usage-crit';
    if (percent >= 80)
        return 'ai-usage-warn';
    return null;
}

function setLevel(actor, percent) {
    actor.remove_style_class_name('ai-usage-warn');
    actor.remove_style_class_name('ai-usage-crit');
    const cls = percent === null ? null : levelClass(percent);
    if (cls)
        actor.add_style_class_name(cls);
}

function formatReset(date) {
    if (!date)
        return '';
    const mins = Math.round((date.getTime() - Date.now()) / 60000);
    if (mins <= 0)
        return 'resetting';
    if (mins < 60)
        return `in ${mins}m`;
    if (mins < 24 * 60)
        return `in ${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, '0')}m`;
    const dt = GLib.DateTime.new_from_unix_local(Math.floor(date.getTime() / 1000));
    return dt.format('%a %H:%M');
}

function formatTime(ms) {
    return GLib.DateTime.new_from_unix_local(Math.floor(ms / 1000)).format('%H:%M');
}

function isCancelled(e) {
    return e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED);
}

const STATUS_DOT = {
    none: 'ai-usage-ok',
    minor: 'ai-usage-warn',
    major: 'ai-usage-crit',
    critical: 'ai-usage-crit',
    maintenance: 'ai-usage-info',
};

const UsageIndicator = GObject.registerClass(
class UsageIndicator extends PanelMenu.Button {
    _init(extension, claudeAccounts, onAccountsChanged) {
        super._init(0.5, 'AI Usage');
        this.add_style_class_name('ai-usage-bar');

        this._path = extension.path;
        this._accountsKey = accountsKey(claudeAccounts);
        this._onAccountsChanged = onAccountsChanged;
        this._providers = buildProviders(claudeAccounts);
        this._api = new Api();
        this._cancellable = new Gio.Cancellable();
        this._state = Object.fromEntries(this._providers.map(p => [p.id, {
            usage: null, usageAt: 0, error: null,
        }]));
        this._status = {};

        // Built once, up front: dash-to-panel converts these boxes to vertical
        // when the panel is on the left/right, so the structure must not change later.
        // A change in accounts recreates the whole indicator instead.
        const box = new St.BoxLayout({style_class: 'ai-usage-box'});
        this.add_child(box);
        this._chips = {};
        const centered = {x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER};
        for (const p of this._providers.filter(p => PANEL_PROVIDERS.has(p.id))) {
            const group = new St.BoxLayout({style_class: 'ai-usage-provider'});
            group.add_child(new St.Icon({gicon: this._icon(p.icon), style_class: 'ai-usage-icon', ...centered}));
            if (p.tag)
                group.add_child(new St.Label({text: p.tag.slice(0, 2), style_class: 'ai-usage-tag', ...centered}));
            const alert = new St.Label({text: '!', style_class: 'ai-usage-alert', visible: false, ...centered});
            const values = [0, 1].map(() =>
                new St.Label({text: '--', style_class: 'ai-usage-value ai-usage-dim', ...centered}));
            for (const a of [alert, ...values])
                group.add_child(a);
            box.add_child(group);
            this._chips[p.id] = {alert, values};
        }

        this.menu.box.add_style_class_name('ai-usage-menu');

        // Follow GNOME's light/dark style: stylesheet.css has .ai-usage-light overrides.
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._schemeId = this._interface.connect('changed::color-scheme', () => this._syncScheme());
        this._syncScheme();
        this.menu.connect('open-state-changed', (_m, open) => {
            if (!open)
                return;
            // Refresh relative reset times; refetch if the data is getting old.
            this._buildMenu();
            const oldest = Math.min(...this._providers.map(p => this._state[p.id].usageAt));
            if (Date.now() - oldest > 60 * 1000)
                this._refresh();
        });

        this._buildMenu();
        this._refresh();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, REFRESH_SECONDS, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _icon(file) {
        return Gio.FileIcon.new(Gio.File.new_for_path(`${this._path}/icons/${file}`));
    }

    async _refresh() {
        if (this._refreshing)
            return;
        this._refreshing = true;
        try {
            if (await this._checkAccounts())
                return;
            await Promise.all([
                ...this._providers.map(p => this._refreshUsage(p)),
                ...Object.keys(SERVICES).map(id => this._refreshStatus(id)),
            ]);
        } finally {
            this._refreshing = false;
        }
        if (this._destroyed)
            return;
        this._updatePanel();
        this._buildMenu();
    }

    // Returns true if the set of Claude accounts changed (the indicator gets replaced).
    async _checkAccounts() {
        let accounts;
        try {
            accounts = await discoverClaudeAccounts(this._cancellable);
        } catch (e) {
            if (!isCancelled(e))
                console.warn(`[ai-usage-bar] account discovery: ${e}`);
            return false;
        }
        if (this._destroyed || accountsKey(accounts) === this._accountsKey)
            return false;
        this._onAccountsChanged(accounts);
        return true;
    }

    async _refreshUsage(p) {
        const s = this._state[p.id];
        try {
            s.usage = await p.fetch(this._api, this._cancellable);
            s.usageAt = Date.now();
            s.error = null;
        } catch (e) {
            if (isCancelled(e))
                return;
            s.error = e instanceof UsageError ? e.message : `Fetch failed: ${e.message}`;
            if (!(e instanceof UsageError))
                console.warn(`[ai-usage-bar] ${p.id} usage: ${e}`);
        }
    }

    async _refreshStatus(serviceId) {
        try {
            this._status[serviceId] = await this._api.fetchStatus(
                SERVICES[serviceId].statusApi, this._cancellable);
        } catch (e) {
            if (isCancelled(e))
                return;
            this._status[serviceId] = {indicator: 'unknown', description: 'Status unavailable', problems: []};
        }
    }

    _updatePanel() {
        for (const p of this._providers) {
            const chip = this._chips[p.id];
            if (!chip)
                continue;
            const s = this._state[p.id];
            const {alert, values} = chip;
            const stale = !s.usage || Date.now() - s.usageAt > STALE_MS;
            values.forEach((label, i) => {
                const w = s.usage?.windows[i];
                const pct = w ? Math.round(w.percent) : null;
                label.text = pct === null ? '--' : String(pct);
                setLevel(label, pct);
                label[stale ? 'add_style_class_name' : 'remove_style_class_name']('ai-usage-dim');
                label[pct >= 100 ? 'add_style_class_name' : 'remove_style_class_name']('ai-usage-full');
            });
            const ind = this._status[p.service]?.indicator;
            alert.visible = !!ind && ind !== 'none' && ind !== 'unknown';
            alert.remove_style_class_name('ai-usage-crit');
            if (ind === 'major' || ind === 'critical')
                alert.add_style_class_name('ai-usage-crit');
        }
    }

    _buildMenu() {
        this.menu.removeAll();
        this._providers.forEach((p, i) => {
            if (i > 0)
                this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addProviderSection(p);
        });

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        for (const id of Object.keys(SERVICES))
            this._addStatusRows(id);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const updatedAt = Math.max(...this._providers.map(p => this._state[p.id].usageAt));
        const refresh = new PopupMenu.PopupMenuItem(
            this._refreshing ? 'Refreshing…'
                : `Refresh${updatedAt ? `  ·  updated ${formatTime(updatedAt)}` : ''}`);
        refresh.label.add_style_class_name('ai-usage-muted');
        refresh.connect('activate', () => this._refresh());
        this.menu.addMenuItem(refresh);
    }

    _addProviderSection(p) {
        const s = this._state[p.id];

        // Header: icon, name · plan, account email. Click opens the usage page.
        const header = new PopupMenu.PopupBaseMenuItem({style_class: 'ai-usage-header'});
        header.add_child(new St.Icon({gicon: this._icon(p.icon), style_class: 'ai-usage-menu-icon'}));
        header.add_child(new St.Label({
            text: s.usage?.plan ? `${p.name} · ${s.usage.plan}` : p.name,
            style_class: 'ai-usage-title',
            y_align: Clutter.ActorAlign.CENTER,
            x_expand: true,
        }));
        if (p.subtitle) {
            header.add_child(new St.Label({
                text: p.subtitle,
                style_class: 'ai-usage-muted ai-usage-subtitle',
                y_align: Clutter.ActorAlign.CENTER,
            }));
        }
        header.connect('activate', () => this._open(p.usagePage));
        this.menu.addMenuItem(header);

        if (s.usage) {
            for (const w of s.usage.windows)
                this.menu.addMenuItem(this._windowRow(w));
            for (const note of s.usage.notes)
                this.menu.addMenuItem(this._textRow(note, 'ai-usage-muted'));
        }
        if (s.error)
            this.menu.addMenuItem(this._textRow(s.error, 'ai-usage-warn'));
        else if (!s.usage)
            this.menu.addMenuItem(this._textRow('Loading…', 'ai-usage-muted'));
    }

    // One status line per service. Click opens the status page.
    _addStatusRows(serviceId) {
        const service = SERVICES[serviceId];
        const st = this._status[serviceId];
        const row = new PopupMenu.PopupBaseMenuItem({style_class: 'ai-usage-row'});
        const dot = new St.Label({text: '●', style_class: 'ai-usage-dot', y_align: Clutter.ActorAlign.CENTER});
        dot.add_style_class_name(STATUS_DOT[st?.indicator] ?? 'ai-usage-muted');
        row.add_child(dot);
        row.add_child(new St.Label({
            text: service.name,
            style_class: 'ai-usage-service',
            y_align: Clutter.ActorAlign.CENTER,
        }));
        row.add_child(new St.Label({
            text: st?.description ?? 'Checking status…',
            style_class: 'ai-usage-muted',
            y_align: Clutter.ActorAlign.CENTER,
        }));
        row.connect('activate', () => this._open(service.statusPage));
        this.menu.addMenuItem(row);
        for (const problem of (st?.problems ?? []).slice(0, 4))
            this.menu.addMenuItem(this._textRow(problem, 'ai-usage-warn'));
    }

    _windowRow(w) {
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        const pct = Math.max(0, Math.min(100, w.percent));

        const row = new PopupMenu.PopupBaseMenuItem({reactive: false, style_class: 'ai-usage-row'});
        row.add_child(new St.Label({
            text: `${w.name} (${w.short})`,
            style_class: 'ai-usage-window-name',
            y_align: Clutter.ActorAlign.CENTER,
        }));

        const trough = new St.Widget({
            style_class: 'ai-usage-trough',
            width: BAR_WIDTH * scale,
            y_align: Clutter.ActorAlign.CENTER,
        });
        const fill = new St.Widget({
            style_class: 'ai-usage-fill',
            width: Math.round(BAR_WIDTH * scale * pct / 100),
        });
        setLevel(fill, w.percent);
        trough.add_child(fill);
        // Keep the fill as tall as the trough.
        fill.add_constraint(new Clutter.BindConstraint({
            source: trough, coordinate: Clutter.BindCoordinate.HEIGHT,
        }));
        row.add_child(trough);

        const pctLabel = new St.Label({
            text: `${Math.round(w.percent)}%`,
            style_class: 'ai-usage-pct',
            y_align: Clutter.ActorAlign.CENTER,
        });
        setLevel(pctLabel, w.percent);
        row.add_child(pctLabel);

        row.add_child(new St.Label({
            text: formatReset(w.resetsAt),
            style_class: 'ai-usage-reset ai-usage-muted',
            y_align: Clutter.ActorAlign.CENTER,
        }));
        return row;
    }

    _textRow(text, cls) {
        const row = new PopupMenu.PopupBaseMenuItem({reactive: false, style_class: 'ai-usage-row'});
        row.add_child(new St.Label({text, style_class: cls}));
        return row;
    }

    _open(uri) {
        try {
            Gio.AppInfo.launch_default_for_uri(uri, global.create_app_launch_context(0, -1));
        } catch (e) {
            console.warn(`[ai-usage-bar] failed to open ${uri}: ${e}`);
        }
    }

    _syncScheme() {
        const light = this._interface.get_string('color-scheme') !== 'prefer-dark';
        for (const actor of [this, this.menu.box])
            actor[light ? 'add_style_class_name' : 'remove_style_class_name']('ai-usage-light');
    }

    destroy() {
        this._destroyed = true;
        if (this._schemeId) {
            this._interface.disconnect(this._schemeId);
            this._schemeId = 0;
        }
        if (this._timer) {
            GLib.source_remove(this._timer);
            this._timer = 0;
        }
        this._cancellable.cancel();
        this._api.destroy();
        super.destroy();
    }
});

export default class AiUsageBarExtension extends Extension {
    enable() {
        this._cancellable = new Gio.Cancellable();
        discoverClaudeAccounts(this._cancellable)
            .catch(e => {
                if (!isCancelled(e))
                    console.warn(`[ai-usage-bar] account discovery: ${e}`);
                return null;
            })
            .then(accounts => {
                if (!this._cancellable.is_cancelled())
                    this._show(accounts ?? []);
            });
    }

    _show(accounts) {
        this._indicator?.destroy();
        this._indicator = new UsageIndicator(this, accounts, newAccounts => {
            // Defer so the old indicator finishes its current callback first.
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                if (!this._cancellable.is_cancelled())
                    this._show(newAccounts);
                return GLib.SOURCE_REMOVE;
            });
        });
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'right');
    }

    disable() {
        this._cancellable?.cancel();
        this._cancellable = null;
        this._indicator?.destroy();
        this._indicator = null;
    }
}
