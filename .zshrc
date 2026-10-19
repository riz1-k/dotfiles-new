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

# Prompt: powerlevel10k "purepower" (ANSI colors, so it follows the terminal theme)
PURE_POWER_MODE=modern
source ~/powerlevel10k/powerlevel10k.zsh-theme

# Autosuggestions performance
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE="20"
ZSH_AUTOSUGGEST_USE_ASYNC=1
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# Command-line colors follow the rice theme (~/dotfiles/rice): `rice theme set`
# renders them to zsh-highlight.zsh; re-checked before each prompt.
# The prompt itself uses ANSI colors, so it follows the terminal palette.
__rice_state="${XDG_STATE_HOME:-$HOME/.local/state}/rice/current"
typeset -gA ZSH_HIGHLIGHT_STYLES
__rice_check_theme() {
  local gen
  [[ -r $__rice_state/theme.generation ]] && gen=$(<$__rice_state/theme.generation)
  [[ $gen == $__rice_generation ]] && return
  __rice_generation=$gen
  [[ -r $__rice_state/theme/zsh-highlight.zsh ]] && source $__rice_state/theme/zsh-highlight.zsh
}
__rice_check_theme
autoload -Uz add-zsh-hook
add-zsh-hook precmd __rice_check_theme

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
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
[[ -x /home/linuxbrew/.linuxbrew/bin/brew ]] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# bun completions
[ -s "/home/riz1/.bun/_bun" ] && source "/home/riz1/.bun/_bun"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
