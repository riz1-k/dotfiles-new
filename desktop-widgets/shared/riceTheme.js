// Live theme for widgets with a gjs backend (symlinked into each widget).
//
// `rice theme set` writes the new palette to ~/.local/state/rice/current/theme/widgets.css
// and bumps theme.generation; this pushes the palette to the page as a "rice-theme"
// event, and host.js swaps it in. On a page load the palette comes from the
// rice-theme.css that rice copies into each installed widget.
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';

const STATE = GLib.build_filenamev([GLib.get_user_state_dir(), 'rice', 'current']);

function read(...parts) {
    try {
        const [, bytes] = GLib.file_get_contents(GLib.build_filenamev([STATE, ...parts]));
        return new TextDecoder().decode(bytes);
    } catch {
        return null;
    }
}

// Push the palette with send(message) whenever the theme changes. Keep the
// returned monitor referenced, or it stops firing.
export function watchRiceTheme(send) {
    GLib.mkdir_with_parents(STATE, 0o755);
    let last = read('theme.generation');
    let timeout = 0;
    const monitor = Gio.File.new_for_path(STATE).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, null);
    monitor.connect('changed', () => {
        if (timeout)
            GLib.source_remove(timeout);
        timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            timeout = 0;
            const generation = read('theme.generation');
            if (generation !== last) {
                last = generation;
                const css = read('theme', 'widgets.css');
                if (css !== null)
                    send({type: 'event', name: 'rice-theme', payload: {css}});
            }
            return GLib.SOURCE_REMOVE;
        });
    });
    return monitor;
}
