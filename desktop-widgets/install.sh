#!/usr/bin/env bash
# Installs the widgets into Gtk4-DING and restarts it so they're picked up.
# Widgets are copied with symlinks resolved: Gtk4-DING won't serve symlinked
# files, and the shared/ files have to live inside each widget's folder.
set -euo pipefail
cd "$(dirname "$0")"

widgets_dir="${XDG_DATA_HOME:-$HOME/.local/share}/com.desktop.ding/widgets"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/com.desktop.ding"
mkdir -p "$widgets_dir" "$config_dir"

for widget in widgets/*/; do
    name=$(basename "$widget")
    rm -rf "${widgets_dir:?}/$name"
    cp -rL "$widget" "$widgets_dir/$name"
    echo "installed $name"
done

override="$config_dir/stylesheet-override.css"
if [[ -e "$override" ]] && ! cmp -s ding/stylesheet-override.css "$override"; then
    echo "kept your existing $override (see ding/stylesheet-override.css)"
else
    cp ding/stylesheet-override.css "$override"
fi

# Moves the widgets to an external display while one is connected.
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/desktop-widgets" "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
cp ding/widgets-follow-display.py "${XDG_DATA_HOME:-$HOME/.local/share}/desktop-widgets/"
cp ding/desktop-widgets-display.service "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable desktop-widgets-display.service >/dev/null 2>&1
systemctl --user restart desktop-widgets-display.service
echo "installed the display follower"

# Gtk4-DING relaunches its desktop process when it exits, which reloads the widgets.
# (Disabling and re-enabling the extension instead hits a bug in its disable(): the
# extension ends up in ERROR with an orphaned desktop process until the next login.)
if pkill -f 'gtk4-ding@smedius.gitlab.com/app/adw-ding.js'; then
    echo "restarted Gtk4-DING"
fi
