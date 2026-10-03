# Oh My Zsh configuration
export ZSH="$HOME/.oh-my-zsh"
DISABLE_AUTO_UPDATE="true"
DISABLE_MAGIC_FUNCTIONS="true"
DISABLE_COMPFIX="true"

plugins=(git zsh-autosuggestions zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh

# Prompt: sainnhe/dotfiles .zsh-theme (powerlevel10k-based "purepower"), recolored to Tokyo Night
# https://github.com/sainnhe/dotfiles/tree/master/.zsh-theme
PURE_POWER_MODE=modern
source ~/powerlevel10k/powerlevel10k.zsh-theme

# Auto-switch the prompt colors (light/dark) to match kitty's mode.
# ~/.local/bin/set-kitty-mode writes the active mode to this file whenever
# GNOME's light/dark setting changes (or you run it manually).
# Dark leg uses Vesper; light leg stays Tokyo Night Day.
__ef_p10k_mode_file="$HOME/.local/state/TERMINAL_MODE"
__ef_p10k_theme_dir="$HOME/dotfiles/.zsh-theme"
__ef_p10k_load_theme() {
  local mode=$(<$__ef_p10k_mode_file 2>/dev/null)
  local theme
  if [[ $mode == *light* ]]; then
    theme=tokyonight-light
  else
    theme=vesper-dark
  fi
  source "$__ef_p10k_theme_dir/$theme.zsh"
}
__ef_p10k_last_mode=$(<$__ef_p10k_mode_file 2>/dev/null)
__ef_p10k_load_theme
__ef_p10k_check_mode() {
  local mode=$(<$__ef_p10k_mode_file 2>/dev/null)
  if [[ -n $mode && $mode != $__ef_p10k_last_mode ]]; then
    __ef_p10k_last_mode=$mode
    __ef_p10k_load_theme
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd __ef_p10k_check_mode

# Autosuggestions performance
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE="20"
ZSH_AUTOSUGGEST_USE_ASYNC=1
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# History configuration
HISTFILE=$HOME/.zhistory
SAVEHIST=10000
HISTSIZE=10000
setopt share_history
setopt hist_expire_dups_first
setopt hist_ignore_dups
setopt hist_verify
setopt hist_ignore_space

# Path configuration (consolidated, avoiding duplicates)
typeset -U path
path=(
  $HOME/.local/bin
  $HOME/.bun/bin
  $HOME/.opencode/bin
  $path
)
export PATH
export EDITOR='nvim'

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

export PATH="$PATH:/home/riz1/.cache/.bun/bin"

# Aliases
alias n="nvim"
alias g="git"
alias gcam="git commit -am"
alias c="clear"
alias su="sudo"
alias e="exit"
alias tm="tmux"
alias lg="lazygit"
alias ls="eza --icons=auto"
alias oc="opencode --auto"
alias claude="claude --dangerously-skip-permissions"

# Lazy load zoxide
eval "$(zoxide init zsh --hook prompt)"

# Turso
export PATH="$PATH:/home/riz1/.turso"

# >>> railway initialize >>>
source "$HOME/.railway/env"
# <<< railway initialize <<<
export PATH="$HOME/go/go/bin:$HOME/go/bin:$PATH"


# Added by Antigravity CLI installer
export PATH="/home/riz1/.local/bin:$PATH"

# >>> grok installer >>>
export PATH="$HOME/.grok/bin:$PATH"
fpath=(~/.grok/completions/zsh $fpath)
autoload -Uz compinit && compinit -C
# <<< grok installer <<<

# Android / React Native / Expo development
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME="$HOME/.local/opt/android-studio/jbr"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$HOME/.local/opt/android-studio/bin:$PATH"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# bun completions
[ -s "/home/riz1/.bun/_bun" ] && source "/home/riz1/.bun/_bun"
