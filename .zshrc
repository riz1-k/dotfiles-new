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

source ~/powerlevel10k/powerlevel10k.zsh-theme
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

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

# Lazy load NVM 
export NVM_DIR="$HOME/.nvm"
nvm() {
  unset -f nvm node
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
  nvm "$@"
}
node() { 
  unset -f nvm node
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  node "$@"
}

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

# Lazy load zoxide
eval "$(zoxide init zsh --hook prompt)"
