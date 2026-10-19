// The bridge to Gtk4-DING, shared by the right-hand widgets; keep the copies identical.
//
// Inside Gtk4-DING, window.ding is injected and requests go to backend.py.
// Opened in a normal browser there is no host: the widget registers fake
// answers, and the theme comes from ?theme= or the browser.

export const ding = window.ding?.instanceId ? window.ding : null;

let fake = null;
const handlers = new Map([['rice-theme', payload => applyRiceTheme(payload)]]);

export function registerFake(answer) {
    fake = answer;
}

export function request(method, params) {
    if (ding)
        return ding.backendRequest(method, params);
    return Promise.resolve(fake?.(method, params ?? {}) ?? null);
}

export function onEvent(name, callback) {
    handlers.set(name, callback);
}

export function log(message) {
    if (ding)
        ding.log(message);
    else
        console.log(message);
}

export function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className)
        node.className = className;
    if (text !== undefined)
        node.textContent = text;
    return node;
}

if (ding) {
    ding.onBackendEvent((name, payload) => handlers.get(name)?.(payload));
} else {
    document.body.dataset.theme = new URLSearchParams(location.search).get('theme') ??
        (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

// The rice theme's palette, pushed by the backend when `rice theme set` runs
// (shared/rice_theme.py, shared/riceTheme.js).
export function applyRiceTheme({css}) {
    let style = document.getElementById('rice-theme');
    if (!style) {
        style = document.createElement('style');
        style.id = 'rice-theme';
        document.head.append(style);
    }
    style.textContent = css;
}
