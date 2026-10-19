// Small bridge to the Gtk4-DING host shared by every widget.
//
// Inside Gtk4-DING, window.ding is injected and the widget's backend pushes data.
// Opened in a normal browser (see preview/), there is no host: the theme comes
// from ?theme= or the browser's color scheme, and the widget feeds itself fake data.

export const ding = window.ding?.instanceId ? window.ding : null;

export function connect({event, request, render, fake, fakeIntervalMs}) {
    if (ding) {
        ding.onBackendEvent((name, payload) => {
            if (name === 'rice-theme')
                applyRiceTheme(payload);
            else if (name === event)
                render(payload);
        });
        ding.backendRequest(request)
            .then(render)
            .catch(e => ding.log(`${request} failed: ${e?.message ?? e}`));
        return;
    }

    const theme = new URLSearchParams(location.search).get('theme') ??
        (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.body.dataset.theme = theme;
    render(fake());
    setInterval(() => render(fake()), fakeIntervalMs);
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
