// Pull requests, and what needs you (review requests, @mentions), via the gh CLI (backend.py).
import {ding, el, log, onEvent, registerFake, request} from './api.js';

// Passing stays a quiet dot; failing and running get their own shapes so they stand out.
const CHECKS = {
    SUCCESS: ['ok', 'Checks passing'],
    FAILURE: ['crit', 'Checks failing'],
    ERROR: ['crit', 'Checks errored'],
    PENDING: ['warn', 'Checks running'],
    EXPECTED: ['warn', 'Checks waiting'],
};

const CHECK_GLYPHS = {
    crit: '<path d="M3 3l6 6M9 3 3 9"/>',
    warn: '<path d="M6 1.5a4.5 4.5 0 1 1-4.5 4.5"/>',
};

function checkMark(checks) {
    const [level, label] = CHECKS[checks] ?? ['', 'No checks'];
    let mark;
    if (CHECK_GLYPHS[level]) {
        mark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        mark.setAttribute('viewBox', '0 0 12 12');
        mark.setAttribute('class', `check ${level}`);
        mark.innerHTML = CHECK_GLYPHS[level];
    } else {
        mark = el('span', `dot ${level}`);
    }
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    if (mark instanceof SVGElement) {
        title.textContent = label;
        mark.append(title);
    } else {
        mark.title = label;
    }
    return mark;
}

const REVIEW = {
    APPROVED: ['ok', 'approved'],
    CHANGES_REQUESTED: ['crit', 'changes requested'],
};

const $ = id => document.getElementById(id);

function age(ms) {
    const minutes = Math.max(0, Math.round((Date.now() - ms) / 60000));
    if (minutes < 60)
        return minutes < 1 ? 'now' : `${minutes}m`;
    if (minutes < 24 * 60)
        return `${Math.round(minutes / 60)}h`;
    if (minutes < 7 * 24 * 60)
        return `${Math.round(minutes / (24 * 60))}d`;
    return new Date(ms).toLocaleDateString(undefined, {month: 'short', day: 'numeric'});
}

function prRow(pr, showBase) {
    const row = el('a', pr.draft ? 'gh-row draft' : 'gh-row');
    row.dataset.url = pr.url;
    row.title = `${pr.fullRepo}#${pr.number} by ${pr.author} into ${pr.base}\n${pr.title}`;

    // Repo names share long prefixes (smart-product-fe/-be): keep the end, which differs.
    const meta = el('span', 'meta', `${pr.repo.replace(/^LRL_light_k8s_/, '')} #${pr.number}`);
    if (showBase && pr.base)
        meta.append(' ', el('span', 'base', `→ ${pr.base}`));
    meta.append(` · ${pr.draft ? 'draft · ' : ''}${pr.reason ?? (pr.mine ? 'you' : pr.author)}`);
    if (CHECKS[pr.checks]?.[0] === 'crit')
        meta.append(' · ', el('span', 'crit', CHECKS[pr.checks][1].toLowerCase()));
    if (!pr.draft && REVIEW[pr.review])
        meta.append(' · ', el('span', REVIEW[pr.review][0], REVIEW[pr.review][1]));

    row.append(checkMark(pr.checks), el('span', 'pr-title', pr.title), el('span', 'age mono', age(pr.updatedAt)), meta);
    return row;
}

function group(section) {
    const node = el('section', 'gh-group');
    const head = el('a', 'gh-group-head');
    head.dataset.url = section.url;
    head.title = 'Open on GitHub';
    head.append(el('span', 'label', section.title));
    if (section.note)
        head.append(el('span', 'note', section.note));
    head.append(el('span', 'count mono', section.total ? `${section.total} ›` : ''));

    const rows = el('div', 'rows');
    if (section.items.length)
        rows.append(...section.items.map(pr => prRow(pr, section.showBase)));
    else
        rows.append(el('div', 'empty', section.empty));
    node.append(head, rows);
    return node;
}

// Every group gets all its rows, then rows come off the longest list until the part fits.
function trimToFit() {
    const body = $('gh-body');
    while (body.scrollHeight > body.clientHeight) {
        const lists = [...body.querySelectorAll('.rows')]
            .map(rows => ({rows, count: rows.querySelectorAll('.gh-row').length}))
            .filter(list => list.count > 1);
        if (!lists.length)
            return;
        const longest = lists.reduce((a, b) => (b.count >= a.count ? b : a));
        longest.rows.lastElementChild.remove();
    }
}

let last = null;
let requestedLogin = null;

function renderAccounts(snapshot) {
    const {accounts = [], activeLogin, accountError, switchingTo} = snapshot;
    const picker = $('account');
    const current = requestedLogin ?? switchingTo ?? activeLogin ?? snapshot.data?.login ?? '';
    const logins = accounts.map(account => account.login);
    if (current && !logins.includes(current))
        logins.unshift(current);
    const options = logins.length ? logins : [''];
    const key = JSON.stringify(options);
    if (picker.dataset.options !== key) {
        picker.replaceChildren(...options.map(login => {
            const option = el('option', '', login || 'No gh accounts');
            option.value = login;
            return option;
        }));
        picker.dataset.options = key;
    }
    picker.value = current;
    picker.disabled = Boolean(requestedLogin || switchingTo || accountError || logins.length < 2);
    picker.title = accountError ?? 'Switch the active GitHub CLI account';
}

function render(snapshot) {
    last = snapshot;
    const {data, error} = snapshot;
    const switchingTo = requestedLogin ?? snapshot.switchingTo;
    renderAccounts(snapshot);

    const message = error ?? snapshot.accountError;
    $('gh-error').hidden = !message;
    $('gh-error').textContent = message ?? '';
    document.querySelector('.github').classList.toggle('stale', Boolean(error && data));

    $('account-status').hidden = !switchingTo;
    $('account-status').textContent = switchingTo ? `Switching to ${switchingTo}…` : '';
    // The bell counts what needs you, not every unread notification (mostly stale review requests).
    const {reviews = 0, mentions = null} = data?.needsYou ?? {};
    const needsYou = reviews + (mentions ?? 0);
    const bell = $('notifications');
    $('notification-count').textContent = data && !switchingTo ? String(needsYou) : '–';
    bell.classList.toggle('unread', Boolean(data && !switchingTo && needsYou > 0));
    bell.hidden = Boolean(switchingTo || !data);
    bell.dataset.url = mentions
        ? 'https://github.com/notifications?query=reason%3Amention'
        : 'https://github.com/pulls/review-requested';
    bell.title = data
        ? [`${reviews} waiting on your review`,
            mentions === null ? '@mentions not counted yet' : `${mentions} unread @mention${mentions === 1 ? '' : 's'}`,
            `${data.notifications} unread notifications in all`].join('\n')
        : '';

    if (switchingTo) {
        $('gh-body').replaceChildren();
    } else if (data) {
        $('gh-body').replaceChildren(...data.sections.map(group));
        trimToFit();
    } else {
        $('gh-body').replaceChildren(el('div', 'empty muted', error ? 'GitHub data unavailable' : 'Loading…'));
    }
}

async function switchAccount() {
    requestedLogin = $('account').value;
    render(last);
    try {
        const snapshot = await request('switchAccount', {login: requestedLogin});
        requestedLogin = null;
        render(snapshot);
    } catch (e) {
        requestedLogin = null;
        render({...last, error: `Couldn't switch account: ${e?.message ?? e}`});
    }
}

function open(url) {
    if (ding)
        request('open', {url}).catch(e => log(`open failed: ${e?.message ?? e}`));
    else
        window.open(url, '_blank');
}

function fakeState(login = 'riz1-lilly') {
    const hoursAgo = h => Date.now() - h * 3600 * 1000;
    const pr = (repo, number, title, fields) => ({
        repo, fullRepo: `riz1/${repo}`, number, title, url: `https://github.com/riz1/${repo}/pull/${number}`,
        draft: false, author: 'octocat', mine: false, base: 'dev', reason: null, checks: 'SUCCESS', review: null,
        ...fields,
    });
    return {
        error: null,
        updatedAt: Date.now(),
        activeLogin: login,
        accounts: ['riz1-lilly', 'riz1-k', 'articys-labs'].map(user => ({login: user, active: user === login})),
        data: {
            login,
            notifications: 7,
            needsYou: {reviews: 1, mentions: 1},
            sections: [
                {title: 'Review', note: 'waiting on you', url: 'https://github.com/pulls/review-requested',
                    showBase: false, total: 1, empty: 'Nothing waiting on you', items: [
                        pr('product-fe', 358, 'Fix docker-publish failure from notification initiativeId type',
                            {updatedAt: hoursAgo(30), review: 'REVIEW_REQUIRED'}),
                    ]},
                {title: 'Infra', note: 'tagged · yours', url: 'https://github.com/pulls', showBase: false, total: 1,
                    empty: 'Nothing tagged to you', items: [
                        pr('infra-apps', 812, 'Bump ingress buffer sizes for the API gateway',
                            {updatedAt: hoursAgo(0.4), reason: 'review requested', base: 'main', checks: 'PENDING'}),
                    ]},
                {title: 'Smart Product', note: 'dev · qa · main', url: 'https://github.com/pulls', showBase: true,
                    total: 12, empty: 'No open pull requests', items: [
                        pr('product-be', 628, 'Harden authorization and CORS for the MCP server',
                            {updatedAt: hoursAgo(2), mine: true, author: 'riz1', checks: 'FAILURE'}),
                        pr('product-fe', 497, 'fix: extra space removed at initial render',
                            {updatedAt: hoursAgo(5), base: 'qa', review: 'CHANGES_REQUESTED'}),
                        pr('product-be', 523, 'Release: qa to main', {updatedAt: hoursAgo(9), base: 'main',
                            review: 'APPROVED'}),
                    ]},
            ],
        },
    };
}

let previewLogin = 'riz1-lilly';
registerFake((method, params) => {
    if (method === 'switchAccount')
        previewLogin = params.login;
    return method === 'getState' || method === 'switchAccount' ? fakeState(previewLogin) : null;
});

export function start() {
    $('account').addEventListener('change', switchAccount);
    document.querySelector('.github').addEventListener('click', event => {
        const target = event.target.closest('[data-url]');
        if (target) {
            event.preventDefault();
            open(target.dataset.url);
        }
    });

    // The part's height changes with the notes above it; refit the rows when it does.
    let height = 0;
    new ResizeObserver(([entry]) => {
        if (Math.abs(entry.contentRect.height - height) < 1)
            return;
        height = entry.contentRect.height;
        if (last)
            render(last);
    }).observe($('gh-body'));

    // Keep the "updated 3h ago" ages current between refreshes.
    setInterval(() => last && render(last), 60 * 1000);

    onEvent('github', render);
    request('getState')
        .then(render)
        .catch(e => log(`getState failed: ${e?.message ?? e}`));
}

start();
