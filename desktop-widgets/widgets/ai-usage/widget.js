import {connect} from './host.js';

const STALE_MS = 15 * 60 * 1000;

// Inline so they follow the theme: Claude in the rice accent, Codex in the text color.
const ICONS = {
    claude: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round">
        <g stroke-width="2.8"><path d="M12 2.5v19M2.5 12h19M5.4 5.4l13.2 13.2M18.6 5.4L5.4 18.6"/></g>
        <g stroke-width="2.2" transform="rotate(22.5 12 12)"><path d="M12 5v14M5 12h14M7 7l10 10M17 7L7 17"/></g>
    </svg>`,
    codex: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <ellipse cx="12" cy="12" rx="9.5" ry="4.3"/>
        <ellipse cx="12" cy="12" rx="9.5" ry="4.3" transform="rotate(60 12 12)"/>
        <ellipse cx="12" cy="12" rx="9.5" ry="4.3" transform="rotate(120 12 12)"/>
    </svg>`,
};

// Same thresholds as the panel extension.
function level(percent) {
    if (percent >= 95)
        return 'crit';
    if (percent >= 80)
        return 'warn';
    return 'ok';
}

const STATUS_LEVEL = {none: 'ok', minor: 'warn', major: 'crit', critical: 'crit', maintenance: 'info'};

function formatReset(ms) {
    if (!ms)
        return '';
    const minutes = Math.round((ms - Date.now()) / 60000);
    if (minutes <= 0)
        return 'resetting';
    if (minutes < 60)
        return `${minutes}m`;
    if (minutes < 24 * 60)
        return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`;
    const date = new Date(ms);
    const day = date.toLocaleDateString(undefined, {weekday: 'short'});
    const time = date.toLocaleTimeString(undefined, {hour: '2-digit', minute: '2-digit', hour12: false});
    return `${day} ${time}`;
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className)
        node.className = className;
    if (text !== undefined)
        node.textContent = text;
    return node;
}

function windowRow(w) {
    const row = el('div', 'window');
    const name = el('span', 'window-name', w.name);
    name.append(el('span', 'muted', w.short));
    row.append(name);

    const bar = el('div', 'bar');
    const fill = el('i', level(w.percent));
    fill.style.width = `${Math.max(0, Math.min(100, w.percent))}%`;
    bar.append(fill);
    row.append(bar);

    row.append(el('span', `mono pct ${level(w.percent)}`, `${Math.round(w.percent)}%`));
    row.append(el('span', 'mono muted small reset', formatReset(w.resetsAt)));
    return row;
}

function providerSection(p) {
    const section = el('section', 'provider');
    if (!p.usageAt || Date.now() - p.usageAt > STALE_MS)
        section.classList.add('stale');

    const head = el('header', 'provider-head');
    const icon = el('span', `icon ${p.icon}`);
    icon.innerHTML = ICONS[p.icon] ?? '';
    head.append(icon, el('span', 'title', p.name));
    if (p.plan)
        head.append(el('span', 'muted', p.plan));
    section.append(head);

    for (const w of p.windows)
        section.append(windowRow(w));
    for (const note of p.notes)
        section.append(el('div', 'note muted small', note));
    if (p.error)
        section.append(el('div', 'note warn small', p.error));
    else if (!p.windows.length)
        section.append(el('div', 'note muted small', 'Loading…'));
    return section;
}

function serviceRow(s) {
    const row = el('div', 'service small');
    const lvl = STATUS_LEVEL[s.indicator] ?? 'unknown';
    row.append(el('span', `dot ${lvl}`, '●'), el('span', 'name', s.name));
    const description = el('span', `description ${lvl === 'ok' ? 'muted' : lvl}`, s.description);
    if (s.problems?.length)
        row.title = s.problems.join('\n');
    row.append(description);
    return row;
}

// Shrink the content if more accounts show up than the widget has room for.
function fitToCard() {
    const card = document.querySelector('.card');
    const content = document.getElementById('content');
    content.style.transform = '';
    content.style.width = '';
    const style = getComputedStyle(card);
    const available = card.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
    const scale = Math.min(1, available / content.scrollHeight);
    if (scale < 1) {
        content.style.transform = `scale(${scale})`;
        content.style.width = `${100 / scale}%`;
    }
}

let last = null;

function render(snapshot) {
    last = snapshot;

    const error = document.getElementById('error');
    error.hidden = !snapshot.error;
    error.textContent = snapshot.error ?? '';

    document.getElementById('updated').textContent = snapshot.updatedAt
        ? new Date(snapshot.updatedAt).toLocaleTimeString(undefined, {hour: '2-digit', minute: '2-digit', hour12: false})
        : '';
    document.getElementById('providers').replaceChildren(...snapshot.providers.map(providerSection));
    document.getElementById('status').replaceChildren(...Object.values(snapshot.status).map(serviceRow));
    fitToCard();
}

// Keep the reset countdowns current between backend refreshes.
setInterval(() => last && render(last), 30 * 1000);
window.addEventListener('resize', () => last && fitToCard());

function fakeUsage() {
    const now = Date.now();
    const hours = h => now + h * 3600 * 1000;
    const limit = (name, short, percent, resetsAt) => ({name, short, percent, resetsAt});
    return {
        error: null,
        updatedAt: now,
        providers: [
            {id: 'claude:.claude', name: 'Claude', icon: 'claude', plan: 'Pro', usageAt: now, notes: [], error: null,
                windows: [limit('Session', '5h', 42, hours(2.3)), limit('Weekly', '7d', 67, hours(28))]},
            {id: 'claude:.claude-2', name: 'Claude 2', icon: 'claude', plan: 'Max', usageAt: now, notes: [], error: null,
                windows: [limit('Session', '5h', 86, hours(1.1)), limit('Weekly', '7d', 53, hours(52)),
                    limit('Weekly Fable', '7d', 97, hours(52))]},
            {id: 'codex', name: 'Codex', icon: 'codex', plan: 'Plus', usageAt: now, notes: [], error: null,
                windows: [limit('Session', '5h', 12, hours(4.2)), limit('Weekly', '7d', 31, hours(130))]},
        ],
        status: {
            claude: {name: 'Claude', indicator: 'none', description: 'All Systems Operational', problems: []},
            openai: {name: 'OpenAI', indicator: 'minor', description: 'Partial System Degradation',
                problems: ['Compliance API: degraded performance']},
        },
    };
}

connect({event: 'usage', request: 'getUsage', render, fake: fakeUsage, fakeIntervalMs: 60 * 1000});
