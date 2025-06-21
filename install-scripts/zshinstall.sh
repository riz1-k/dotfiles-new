#!/bin/bash

# This script installs zsh, eza, zoxide, Oh My Zsh, and useful plugins

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root. Please run as a regular user."
    exit 1
fi

# Check if we have sudo access
if ! sudo -n true 2>/dev/null; then
    echo "This script requires sudo access. You may be prompted for your password."
fi

echo -e "${BLUE}Starting shell environment setup...${NC}\n"

# Step 1: Install zsh
print_progress "Installing zsh..."
if command -v zsh >/dev/null 2>&1; then
    print_warning "zsh is already installed"
else
    sudo apt update -qq
    sudo apt install -y zsh
    print_success "zsh installed successfully"
fi

# Step 2: Install eza (modern replacement for ls)
print_progress "Installing eza..."
if command -v eza >/dev/null 2>&1; then
    print_warning "eza is already installed"
else
    # Install GPG if not present
    sudo apt install -y gpg
    
    # Create keyrings directory
    sudo mkdir -p /etc/apt/keyrings
    
    # Add eza repository
    if [ ! -f /etc/apt/keyrings/gierens.gpg ]; then
        wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | sudo gpg --dearmor -o /etc/apt/keyrings/gierens.gpg
        echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" | sudo tee /etc/apt/sources.list.d/gierens.list
        sudo chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list
    fi
    
    sudo apt update -qq
    sudo apt install -y eza
    print_success "eza installed successfully"
fi

# Step 3: Install zoxide (smart cd command)
print_progress "Installing zoxide..."
if command -v zoxide >/dev/null 2>&1; then
    print_warning "zoxide is already installed"
else
    sudo apt install -y zoxide
    print_success "zoxide installed successfully"
fi

# Step 4: Install Oh My Zsh
print_progress "Installing Oh My Zsh..."
if [ -d "$HOME/.oh-my-zsh" ]; then
    print_warning "Oh My Zsh is already installed"
else
    # Download and run Oh My Zsh installer non-interactively
    RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    print_success "Oh My Zsh installed successfully"
fi

# Set ZSH_CUSTOM if not set
export ZSH_CUSTOM=${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}

# Step 5: Install zsh-autosuggestions plugin
print_progress "Installing zsh-autosuggestions plugin..."
if [ -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
    print_warning "zsh-autosuggestions is already installed"
else
    git clone https://github.com/zsh-users/zsh-autosuggestions.git "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    print_success "zsh-autosuggestions installed successfully"
fi

# Step 6: Install zsh-syntax-highlighting plugin
print_progress "Installing zsh-syntax-highlighting plugin..."
if [ -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
    print_warning "zsh-syntax-highlighting is already installed"
else
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
    print_success "zsh-syntax-highlighting installed successfully"
fi

# Step 7: Install fast-syntax-highlighting plugin
print_progress "Installing fast-syntax-highlighting plugin..."
if [ -d "$ZSH_CUSTOM/plugins/fast-syntax-highlighting" ]; then
    print_warning "fast-syntax-highlighting is already installed"
else
    git clone https://github.com/zdharma-continuum/fast-syntax-highlighting.git "$ZSH_CUSTOM/plugins/fast-syntax-highlighting"
    print_success "fast-syntax-highlighting installed successfully"
fi

#Step 8: Install Powerlevel10k
print_progress "Installing Powerlevel10k..."
if [ -d "$ZSH_CUSTOM/plugins/powerlevel10k" ]; then
    print_warning "Powerlevel10k is already installed"
else
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k
    echo 'source ~/powerlevel10k/powerlevel10k.zsh-theme' >> ~/.zshrc
    print_success "Powerlevel10k installed successfully"
fi


echo -e "\n${GREEN}✓ Setup completed successfully!${NC}"

# Optional: Offer to change default shell
echo -e "\n${BLUE}Would you like to set zsh as your default shell now? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    if chsh -s "$(which zsh)"; then
        print_success "Default shell changed to zsh. Please log out and log back in for the change to take effect."
    else
        print_error "Failed to change default shell. You can do this manually later with: chsh -s \$(which zsh)"
    fi
fi

echo "Restart your terminal or run: source ~/.zshrc"
echo ""
echo -e "\n${GREEN}Enjoy your enhanced shell environment! 🚀${NC}"
