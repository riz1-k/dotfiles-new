#!/bin/bash

# Builds Vicinae (Raycast-style launcher) from source, installs it to /usr/local,
# links the Vesper theme + settings from this repo and binds it to Alt+Space on GNOME.
#
# Usage: ./vicinae.sh            # latest release
#        ./vicinae.sh v0.29.1    # specific tag
#
# Re-run it to upgrade. The prebuilt release tarball targets a newer glibc than
# Ubuntu 26.04 ships, hence the source build against the distro's Qt 6.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TOTAL_STEPS=6
CURRENT_STEP=0

print_progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "${BLUE}[${CURRENT_STEP}/${TOTAL_STEPS}] $1${NC}"
}
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ Error: $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ Warning: $1${NC}"; }

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/vicinae-src"
TAG="${1:-$(curl -fsSL https://api.github.com/repos/vicinaehq/vicinae/releases/latest | grep -Po '"tag_name": *"\K[^"]*')}"

if [ -z "$TAG" ]; then
    print_error "Could not resolve the latest Vicinae release tag"
    exit 1
fi

# 1: Build dependencies
print_progress "Installing build dependencies..."
sudo apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git pkg-config \
    qt6-base-dev qt6-base-private-dev qt6-declarative-dev qt6-declarative-private-dev \
    qt6-svg-dev qt6-wayland-dev qt6-wayland-private-dev qt6-shadertools-dev \
    qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools qt6-wayland qt6-qpa-plugins \
    qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts \
    qml6-module-qtquick-shapes qml6-module-qtquick-effects qml6-module-qtquick-dialogs \
    qml6-module-qtquick-window qml6-module-qtquick-templates qml6-module-qtquick-vectorimage \
    qml6-module-qtqml-workerscript qml6-module-qtqml-models qml6-module-qt-labs-folderlistmodel \
    liblayershellqtinterface-dev qtkeychain-qt6-dev libkf6syntaxhighlighting-dev \
    libcmark-gfm-dev libcmark-gfm-extensions-dev libqalculate-dev libsecret-1-dev libssl-dev \
    libwayland-dev wayland-protocols extra-cmake-modules \
    libx11-dev libxcb1-dev libxcb-xkb-dev libxcb-keysyms1-dev libxkbcommon-dev libxkbcommon-x11-dev \
    pulseaudio-utils
if ! command -v npm >/dev/null 2>&1 && [ -s "$HOME/.nvm/nvm.sh" ]; then
    \. "$HOME/.nvm/nvm.sh"
fi
command -v npm >/dev/null 2>&1 || { print_error "npm is required to build the extension API (run clitools.sh first)"; exit 1; }
print_success "Dependencies installed"

# 2: Source
print_progress "Fetching Vicinae $TAG..."
if [ -d "$SRC_DIR/.git" ]; then
    git -C "$SRC_DIR" fetch --depth 1 origin tag "$TAG"
    git -C "$SRC_DIR" checkout -q "$TAG"
else
    git clone --depth 1 --branch "$TAG" https://github.com/vicinaehq/vicinae.git "$SRC_DIR"
fi
print_success "Source ready at $SRC_DIR"

# 3: Build + install
print_progress "Building (takes a while)..."
cmake -S "$SRC_DIR" -B "$SRC_DIR/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DVICINAE_NODE_RUNTIME_DOWNLOAD=ON
cmake --build "$SRC_DIR/build" -j"$(nproc)"
sudo cmake --install "$SRC_DIR/build"
print_success "Installed $(vicinae version 2>/dev/null | head -1)"

# 4: Config + Vesper theme (themes are only discovered under data dirs)
print_progress "Linking config and Vesper theme..."
if [ -e "$HOME/.config/vicinae" ] && [ ! -L "$HOME/.config/vicinae" ]; then
    mv "$HOME/.config/vicinae" "$HOME/.config/vicinae.bak.$(date +%s)"
    print_warning "Existing ~/.config/vicinae moved aside"
fi
ln -sfn ../dotfiles-new/.config/vicinae "$HOME/.config/vicinae"
mkdir -p "$HOME/.local/share/vicinae/themes"
ln -sf "$DOTFILES/.config/vicinae/themes/vesper.toml" "$HOME/.local/share/vicinae/themes/vesper.toml"
print_success "Config linked"

# 5: GNOME integration
print_progress "Configuring GNOME (Alt+Space + companion extension)..."
if [ "${XDG_CURRENT_DESKTOP#*GNOME}" != "$XDG_CURRENT_DESKTOP" ]; then
    # Alt+Space opens the window menu by default; it's still available via titlebar right-click
    gsettings set org.gnome.desktop.wm.keybindings activate-window-menu "[]"

    KB_PATH=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vicinae/
    CURRENT=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    if [[ "$CURRENT" != *"$KB_PATH"* ]]; then
        if [[ "$CURRENT" == "@as []" || "$CURRENT" == "[]" ]]; then
            NEW="['$KB_PATH']"
        else
            NEW="${CURRENT%]}, '$KB_PATH']"
        fi
        gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW"
    fi
    KB_SCHEMA=org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KB_PATH
    gsettings set "$KB_SCHEMA" name "Vicinae"
    gsettings set "$KB_SCHEMA" command "vicinae toggle"
    gsettings set "$KB_SCHEMA" binding "<Alt>space"

    # Clipboard history, window switching and launcher placement on Mutter
    if ! gnome-extensions info vicinae@dagimg-dot >/dev/null 2>&1; then
        print_warning "Approve the 'Install Vicinae' dialog GNOME is about to show"
        gdbus call --session --timeout 600 --dest org.gnome.Shell.Extensions \
            --object-path /org/gnome/Shell/Extensions \
            --method org.gnome.Shell.Extensions.InstallRemoteExtension "vicinae@dagimg-dot" || true
    fi
    gnome-extensions enable vicinae@dagimg-dot 2>/dev/null || true
    EXT_SCHEMAS="$HOME/.local/share/gnome-shell/extensions/vicinae@dagimg-dot/schemas"
    if [ -d "$EXT_SCHEMAS" ]; then
        gsettings --schemadir "$EXT_SCHEMAS" set org.gnome.shell.extensions.vicinae show-status-indicator false
        # The extension samples mutter's focus on idle and reacts to transient focus flickers by
        # closing the launcher right after it opens. Vicinae's own close_on_focus_loss (settings.json)
        # follows real keyboard focus on its surface instead.
        gsettings --schemadir "$EXT_SCHEMAS" set org.gnome.shell.extensions.vicinae launcher-auto-close-focus-loss false
    fi
    # Deja Window restores each app's last workspace and switches to it. Vicinae creates a fresh
    # window on every open, so it would keep dragging you to whatever workspace it was last seen on.
    if gnome-extensions info deja-window@mcast.gnomext.com >/dev/null 2>&1; then
        python3 - <<'EOF'
import json, subprocess
D = "/org/gnome/shell/extensions/deja-window"
def read(k):
    v = subprocess.check_output(["dconf", "read", f"{D}/{k}"], text=True).strip()
    return json.loads(v[1:-1].encode().decode("unicode_escape")) if v else None
def write(k, obj):
    s = json.dumps(obj, separators=(",", ":"))
    subprocess.check_call(["dconf", "write", f"{D}/{k}", "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"])
g = read("window-global-defaults")
if g is not None:
    g["excluded_wm_classes"] = sorted(set(g.get("excluded_wm_classes", [])) | {"vicinae"})
    write("window-global-defaults", g)
states = read("window-app-states")
if states and states.pop("vicinae", None) is not None:
    write("window-app-states", states)
EOF
    fi
    print_success "Alt+Space bound to vicinae toggle"
else
    print_warning "Not GNOME: bind 'vicinae toggle' to Alt+Space in your compositor"
fi

# 6: Daemon
print_progress "Enabling the vicinae daemon..."
systemctl --user daemon-reload
systemctl --user enable vicinae.service >/dev/null 2>&1
systemctl --user restart vicinae.service
print_success "vicinae.service running ($(systemctl --user is-active vicinae.service))"

echo -e "${GREEN}Done. Press Alt+Space.${NC}"
