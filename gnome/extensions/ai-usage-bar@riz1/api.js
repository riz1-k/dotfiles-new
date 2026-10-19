// Data fetching for Claude / Codex usage and service status.
// Only depends on GLib/Gio/Soup so it can be tested outside gnome-shell with `gjs -m`.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Soup from 'gi://Soup?version=3.0';

Gio._promisify(Soup.Session.prototype, 'send_and_read_async');
Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'enumerate_children_async');
Gio._promisify(Gio.FileEnumerator.prototype, 'next_files_async');

const HOME = GLib.get_home_dir();
const CODEX_AUTH = GLib.build_filenamev([HOME, '.codex', 'auth.json']);

const CLAUDE_USAGE_URL = 'https://api.anthropic.com/api/oauth/usage';
const CODEX_USAGE_URL = 'https://chatgpt.com/backend-api/wham/usage';

const decoder = new TextDecoder();

export class UsageError extends Error {}

class HttpError extends Error {
    constructor(status, body) {
        super(`HTTP ${status}`);
        this.status = status;
        this.body = body;
    }
}

async function readJson(path, cancellable) {
    const [contents] = await Gio.File.new_for_path(path).load_contents_async(cancellable);
    return JSON.parse(decoder.decode(contents));
}

// Every Claude Code config dir in $HOME (~/.claude, ~/.claude-<tag>, as used via
// CLAUDE_CONFIG_DIR) that holds an OAuth login. ~/.claude is always included so a
// missing login still shows up as an error row.
export async function discoverClaudeAccounts(cancellable) {
    const names = new Set(['.claude']);
    const enumerator = await Gio.File.new_for_path(HOME).enumerate_children_async(
        'standard::name,standard::type', Gio.FileQueryInfoFlags.NONE,
        GLib.PRIORITY_DEFAULT, cancellable);
    for (;;) {
        const infos = await enumerator.next_files_async(100, GLib.PRIORITY_DEFAULT, cancellable);
        if (!infos.length)
            break;
        for (const info of infos) {
            const name = info.get_name();
            if (name.startsWith('.claude-') && info.get_file_type() === Gio.FileType.DIRECTORY)
                names.add(name);
        }
    }

    const accounts = [];
    for (const name of [...names].sort()) {
        const dir = GLib.build_filenamev([HOME, name]);
        const credentialsPath = GLib.build_filenamev([dir, '.credentials.json']);
        const isDefault = name === '.claude';
        if (!isDefault) {
            try {
                if (!(await readJson(credentialsPath, cancellable)).claudeAiOauth)
                    continue;
            } catch (e) {
                continue;
            }
        }
        // The default dir keeps its global config at ~/.claude.json, others inside the dir.
        const configPath = isDefault
            ? GLib.build_filenamev([HOME, '.claude.json'])
            : GLib.build_filenamev([dir, '.claude.json']);
        let email = null;
        try {
            email = (await readJson(configPath, cancellable)).oauthAccount?.emailAddress ?? null;
        } catch (e) {}
        accounts.push({
            id: `claude:${name}`,
            tag: isDefault ? '' : name.slice('.claude-'.length),
            credentialsPath,
            email,
        });
    }
    return accounts;
}

function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : null;
}

function windowLabel(seconds) {
    if (!seconds)
        return '';
    return seconds % 86400 === 0 ? `${seconds / 86400}d` : `${Math.round(seconds / 3600)}h`;
}

// A rate-limit window: {name, short, percent, resetsAt: Date|null}
function makeWindow(name, short, percent, resetsAt) {
    if (percent === null || percent === undefined)
        return null;
    return {name, short, percent, resetsAt: resetsAt ? new Date(resetsAt) : null};
}

// `limits` lists every window that applies to the account, including ones scoped
// to a model or surface (e.g. the weekly Fable limit on Max). Session and the
// overall weekly limit come first so the panel can show them.
function claudeLimits(limits) {
    const order = {session: 0, weekly_all: 1};
    return limits
        .map(l => {
            const short = {session: '5h', weekly: '7d'}[l.group] ?? l.group;
            const scope = [l.scope?.model?.display_name, l.scope?.surface?.display_name]
                .filter(Boolean).join(' ');
            let name = l.kind === 'session' ? 'Session' : 'Weekly';
            if (scope)
                name = `${name} ${scope}`;
            return {rank: order[l.kind] ?? 2, w: makeWindow(name, short, l.percent, l.resets_at)};
        })
        .filter(x => x.w)
        .sort((a, b) => a.rank - b.rank)
        .map(x => x.w);
}

function claudeLegacyWindows(data) {
    const w = (key, name, short) =>
        makeWindow(name, short, data[key]?.utilization, data[key]?.resets_at);
    return [
        w('five_hour', 'Session', '5h'),
        w('seven_day', 'Weekly', '7d'),
        w('seven_day_opus', 'Weekly Opus', '7d'),
        w('seven_day_sonnet', 'Weekly Sonnet', '7d'),
    ].filter(Boolean);
}

export class Api {
    constructor() {
        this._session = new Soup.Session({timeout: 20, user_agent: 'ai-usage-bar/1'});
    }

    destroy() {
        this._session.abort();
    }

    async _getJson(url, headers, cancellable) {
        const msg = Soup.Message.new('GET', url);
        for (const [k, v] of Object.entries(headers ?? {}))
            msg.request_headers.append(k, v);
        const bytes = await this._session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, cancellable);
        const text = decoder.decode(bytes.get_data() ?? new Uint8Array());
        // status_code, not get_status(): the latter maps to the Soup.Status
        // enum and GJS throws for codes it lacks (e.g. 429 Too Many Requests).
        const status = msg.status_code;
        if (status < 200 || status >= 300)
            throw new HttpError(status, text);
        return JSON.parse(text);
    }

    async fetchClaude(account, cancellable) {
        let creds;
        try {
            creds = (await readJson(account.credentialsPath, cancellable)).claudeAiOauth;
        } catch (e) {
            throw new UsageError('No Claude login found. Run `claude` and /login');
        }
        if (!creds?.accessToken)
            throw new UsageError('No Claude login found. Run `claude` and /login');
        if (creds.expiresAt && creds.expiresAt < Date.now())
            throw new UsageError('Claude token expired. Open Claude Code to refresh it');

        let data;
        try {
            data = await this._getJson(CLAUDE_USAGE_URL, {
                'Authorization': `Bearer ${creds.accessToken}`,
                'anthropic-beta': 'oauth-2025-04-20',
                'Content-Type': 'application/json',
            }, cancellable);
        } catch (e) {
            if (e.status === 401 || e.status === 403)
                throw new UsageError('Claude token rejected. Open Claude Code to refresh it');
            if (e.status === 429)
                throw new UsageError('Usage API rate limited, retrying later');
            throw e;
        }

        const extra = data.extra_usage;
        return {
            plan: capitalize(creds.subscriptionType),
            windows: Array.isArray(data.limits) ? claudeLimits(data.limits) : claudeLegacyWindows(data),
            notes: extra?.is_enabled
                ? [`Extra usage on${extra.utilization != null ? ` · ${Math.round(extra.utilization)}% used` : ''}`]
                : [],
        };
    }

    async fetchCodex(cancellable) {
        let tokens;
        try {
            tokens = (await readJson(CODEX_AUTH, cancellable)).tokens;
        } catch (e) {
            throw new UsageError('No Codex login found. Run `codex login`');
        }
        if (!tokens?.access_token)
            throw new UsageError('No ChatGPT login found. Run `codex login`');

        let data;
        try {
            const headers = {'Authorization': `Bearer ${tokens.access_token}`};
            if (tokens.account_id)
                headers['ChatGPT-Account-Id'] = tokens.account_id;
            data = await this._getJson(CODEX_USAGE_URL, headers, cancellable);
        } catch (e) {
            if (e.status === 401 || e.status === 403)
                throw new UsageError('Codex token rejected. Run `codex` to refresh it');
            if (e.status === 429)
                throw new UsageError('Usage API rate limited, retrying later');
            throw e;
        }

        const rl = data.rate_limit ?? {};
        const w = (win, name) => win && makeWindow(
            name, windowLabel(win.limit_window_seconds), win.used_percent,
            win.reset_at ? win.reset_at * 1000 : null);
        const notes = [];
        if (rl.limit_reached)
            notes.push('Rate limit reached');
        if (data.credits?.has_credits)
            notes.push(data.credits.unlimited ? 'Credits: unlimited' : `Credits: ${data.credits.balance}`);
        return {
            plan: capitalize(data.plan_type),
            windows: [
                w(rl.primary_window, 'Session'),
                w(rl.secondary_window, 'Weekly'),
            ].filter(Boolean),
            notes,
        };
    }

    // Statuspage-style summary: {indicator, description, problems: [string]}
    async fetchStatus(url, cancellable) {
        const data = await this._getJson(url, {}, cancellable);
        const problems = [
            ...(data.incidents ?? []).map(i => i.name),
            ...(data.components ?? [])
                .filter(c => c.status && c.status !== 'operational' && !c.group)
                .map(c => `${c.name}: ${c.status.replace(/_/g, ' ')}`),
        ];
        return {
            indicator: data.status?.indicator ?? 'unknown',
            description: data.status?.description ?? 'Unknown',
            problems: [...new Set(problems)],
        };
    }
}
