# powerlevel10k configuration
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export ZSH="$HOME/.oh-my-zsh"

DISABLE_AUTO_UPDATE="true"
DISABLE_MAGIC_FUNCTIONS="true"
DISABLE_COMPFIX="true"
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE="20"
ZSH_AUTOSUGGEST_USE_ASYNC=1

# utils
eval "$(zoxide init zsh)"

# plugins
plugins=(git zsh-autosuggestions zsh-syntax-highlighting fast-syntax-highlighting )

# aliases
alias n="nvim"
alias gt="git"
alias c="clear"
alias su="sudo"
alias e="exit"
alias tm="tmux"
alias ff="fastfetch"
alias lg="lazygit"
alias cd="z"
alias ls='eza -lh --group-directories-first --icons=auto'

# history setup
HISTFILE=$HOME/.zhistory
SAVEHIST=32767
HISTSIZE=32768
setopt share_history
setopt hist_expire_dups_first
setopt hist_ignore_dups
setopt hist_verify

[[ ! -f ~/dotfiles/.p10k.zsh ]] || source ~/dotfiles/.p10k.zsh
source ~/.oh-my-zsh
source ~/powerlevel10k/powerlevel10k.zsh-theme

