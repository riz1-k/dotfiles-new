#!/bin/bash

# This script installs essential CLI tools

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Progress tracking TOTAL_STEPS=7
CURRENT_STEP=0

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

# 1: Install Lazygit
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

# 2: Install Tmux and Tmux Plugin Manager
print_progress "Installing Tmux and Tmux Plugin Manager..."
if command -v tmux >/dev/null 2>&1; then
    print_warning "Tmux is already installed"
else
    sudo apt install -y tmux
fi

if command -v tmuxp >/dev/null 2>&1; then
    print_warning "Tmux Plugin Manager is already installed"
else
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
    echo "set -g @plugin 'tmux-plugins/tpm'" >> ~/.tmux.conf
    echo "run '~/.tmux/plugins/tpm/tpm'" >> ~/.tmux.conf
    print_success "Tmux Plugin Manager installed successfully"
fi

echo -e "\n${GREEN}✓ Setup completed successfully!${NC}"

