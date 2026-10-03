# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

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
# Resolve through the ~/.zshrc symlink so this works wherever the repo lives.
__ef_p10k_theme_dir="${${(%):-%x}:A:h}/.zsh-theme"
__ef_p10k_read_mode() {
  [[ -r $__ef_p10k_mode_file ]] && REPLY=$(<$__ef_p10k_mode_file) || REPLY=
}
__ef_p10k_load_theme() {
  __ef_p10k_read_mode
  local theme
  if [[ $REPLY == *light* ]]; then
    theme=tokyonight-light
  else
    theme=vesper-dark
  fi
  [[ -r $__ef_p10k_theme_dir/$theme.zsh ]] && source "$__ef_p10k_theme_dir/$theme.zsh"
}
__ef_p10k_read_mode
__ef_p10k_last_mode=$REPLY
__ef_p10k_load_theme
__ef_p10k_check_mode() {
  __ef_p10k_read_mode
  if [[ -n $REPLY && $REPLY != $__ef_p10k_last_mode ]]; then
    __ef_p10k_last_mode=$REPLY
    __ef_p10k_load_theme
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd __ef_p10k_check_mode

# Autosuggestions performance
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE="20"
ZSH_AUTOSUGGEST_USE_ASYNC=1
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# Vesper (https://github.com/raunofreiberg/vesper)
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#505050"
typeset -A ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[default]='fg=#ffffff'
ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#ff8080'
ZSH_HIGHLIGHT_STYLES[reserved-word]='fg=#a0a0a0'
ZSH_HIGHLIGHT_STYLES[command]='fg=#ffc799,bold'
ZSH_HIGHLIGHT_STYLES[alias]='fg=#ffc799'
ZSH_HIGHLIGHT_STYLES[builtin]='fg=#ffc799'
ZSH_HIGHLIGHT_STYLES[function]='fg=#ffc799'
ZSH_HIGHLIGHT_STYLES[precommand]='fg=#ffc799,underline'
ZSH_HIGHLIGHT_STYLES[path]='fg=#ffffff,underline'
ZSH_HIGHLIGHT_STYLES[path_prefix]='fg=#ffffff'
ZSH_HIGHLIGHT_STYLES[globbing]='fg=#99ffe4'
ZSH_HIGHLIGHT_STYLES[history-expansion]='fg=#99ffe4'
ZSH_HIGHLIGHT_STYLES[single-hyphen-option]='fg=#a0a0a0'
ZSH_HIGHLIGHT_STYLES[double-hyphen-option]='fg=#a0a0a0'
ZSH_HIGHLIGHT_STYLES[single-quoted-argument]='fg=#99ffe4'
ZSH_HIGHLIGHT_STYLES[double-quoted-argument]='fg=#99ffe4'
ZSH_HIGHLIGHT_STYLES[dollar-quoted-argument]='fg=#99ffe4'
ZSH_HIGHLIGHT_STYLES[dollar-double-quoted-argument]='fg=#ffc799'
ZSH_HIGHLIGHT_STYLES[assign]='fg=#a0a0a0'
ZSH_HIGHLIGHT_STYLES[redirection]='fg=#a0a0a0'
ZSH_HIGHLIGHT_STYLES[comment]='fg=#7e7e7e'

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
export TERMINAL='ghostty'

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
alias codex="codex --yolo"

# Lazy load zoxide
eval "$(zoxide init zsh --hook prompt)"

# Turso
export PATH="$PATH:/home/riz1/.turso"

# >>> railway initialize >>>
[[ -f "$HOME/.railway/env" ]] && source "$HOME/.railway/env"
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
[[ -x /home/linuxbrew/.linuxbrew/bin/brew ]] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# bun completions
[ -s "/home/riz1/.bun/_bun" ] && source "/home/riz1/.bun/_bun"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
