#!/bin/bash

# This script installs essential CLI tools

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Progress tracking
TOTAL_STEPS=7
CURRENT_STEP=0

# Keep user-installed binaries available in the current script and future shells.
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
export PATH="$LOCAL_BIN:$PATH"

# Function to print progress
print_progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "${BLUE}[${CURRENT_STEP}/${TOTAL_STEPS}] $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ Error: $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ Warning: $1${NC}"
}

#1: Install Node.js
print_progress "Installing Node.js..."
if command -v node >/dev/null 2>&1; then
    print_warning "Node.js is already installed"
else
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    \. "$HOME/.nvm/nvm.sh"
    nvm install 24
    print_success "Node.js installed successfully"
fi

#2: Install Bun
print_progress "Installing Bun..."
if command -v bun >/dev/null 2>&1; then
    print_warning "Bun is already installed"
else
    curl -fsSL https://bun.sh/install | bash
    echo "export PATH=\"$HOME/.bun/bin:\$PATH\"" >> ~/.zshrc
    print_success "Bun installed successfully"
fi

# 3: Install Lazygit
print_progress "Installing Lazygit..."
if command -v lazygit >/dev/null 2>&1; then
    print_warning "Lazygit is already installed"
else
    LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | \grep -Po '"tag_name": *"v\K[^"]*')
    curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
    tar xf lazygit.tar.gz lazygit
    sudo install lazygit -D -t /usr/local/bin/
    print_success "Lazygit installed successfully"
fi

# 4: Install Yazi
print_progress "Installing Yazi..."
if command -v yazi >/dev/null 2>&1; then
    print_warning "Yazi is already installed"
else
    case "$(uname -m)" in
        x86_64) YAZI_ARCH="x86_64" ;;
        aarch64) YAZI_ARCH="aarch64" ;;
        *) print_warning "Unsupported architecture for Yazi: $(uname -m)"; YAZI_ARCH="" ;;
    esac

    if [ -n "$YAZI_ARCH" ]; then
        # Recent Yazi releases require glibc 2.39; Pop!_OS 22.04 ships 2.35.
        GLIBC_VERSION=$(ldd --version 2>&1 | sed -n '1s/.* \([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')
        if [ -n "$GLIBC_VERSION" ] && [ "$(printf '%s\n' "$GLIBC_VERSION" "2.39" | sort -V | head -n1)" = "2.39" ]; then
            YAZI_VERSION=$(curl -fsSL https://api.github.com/repos/sxyazi/yazi/releases/latest | grep -m1 -Po '"tag_name":\s*"\K[^"]+')
        else
            YAZI_VERSION="v0.4.2"
        fi

        if ! command -v unzip >/dev/null 2>&1; then
            sudo apt update -qq
            sudo apt install -y unzip
        fi
        TMP_DIR=$(mktemp -d)
        curl -fsSL -o "$TMP_DIR/yazi.zip" "https://github.com/sxyazi/yazi/releases/download/${YAZI_VERSION}/yazi-${YAZI_ARCH}-unknown-linux-gnu.zip"
        unzip -q "$TMP_DIR/yazi.zip" -d "$TMP_DIR/yazi"
        YAZI_ROOT=$(find "$TMP_DIR/yazi" -type f -name yazi -printf '%h\n' | head -n1)
        install -m 0755 "$YAZI_ROOT/yazi" "$LOCAL_BIN/yazi"
        [ ! -f "$YAZI_ROOT/ya" ] || install -m 0755 "$YAZI_ROOT/ya" "$LOCAL_BIN/ya"
        rm -rf "$TMP_DIR"
        print_success "Yazi ${YAZI_VERSION} installed successfully"
    fi
fi

# 5: Install GitUI
print_progress "Installing GitUI..."
if command -v gitui >/dev/null 2>&1; then
    print_warning "GitUI is already installed"
else
    case "$(uname -m)" in
        x86_64) GITUI_ARCH="x86_64" ;;
        aarch64) GITUI_ARCH="aarch64" ;;
        *) print_warning "Unsupported architecture for GitUI: $(uname -m)"; GITUI_ARCH="" ;;
    esac

    if [ -n "$GITUI_ARCH" ]; then
        GITUI_VERSION=$(curl -fsSL https://api.github.com/repos/gitui-org/gitui/releases/latest | grep -m1 -Po '"tag_name":\s*"\K[^"]+')
        TMP_DIR=$(mktemp -d)
        curl -fsSL -o "$TMP_DIR/gitui.tar.gz" "https://github.com/gitui-org/gitui/releases/download/${GITUI_VERSION}/gitui-linux-${GITUI_ARCH}.tar.gz"
        tar -xzf "$TMP_DIR/gitui.tar.gz" -C "$TMP_DIR"
        install -m 0755 "$TMP_DIR/gitui" "$LOCAL_BIN/gitui"
        rm -rf "$TMP_DIR"
        print_success "GitUI ${GITUI_VERSION} installed successfully"
    fi
fi

# 6: Install GitHub CLI
print_progress "Installing GitHub CLI..."
if command -v gh >/dev/null 2>&1; then
    print_warning "GitHub CLI is already installed"
else
   (type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y
    print_success "GitHub CLI installed successfully"
fi

# 7: Install Tmux and Tmux Plugin Manager
print_progress "Installing Tmux and Tmux Plugin Manager..."
if command -v tmux >/dev/null 2>&1; then
    print_warning "Tmux is already installed"
else
    sudo apt install -y tmux
fi

TMUX_PLUGIN_DIR="$HOME/.config/tmux/.tmux/plugins"
if [ -d "$TMUX_PLUGIN_DIR/tpm" ]; then
    print_warning "Tmux Plugin Manager is already installed"
else
    mkdir -p "$TMUX_PLUGIN_DIR"
    git clone https://github.com/tmux-plugins/tpm "$TMUX_PLUGIN_DIR/tpm"
    print_success "Tmux Plugin Manager installed successfully"
fi

echo -e "\n${GREEN}✓ Setup completed successfully!${NC}"

