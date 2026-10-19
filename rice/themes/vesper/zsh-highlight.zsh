# zsh-syntax-highlighting / autosuggestions colours for Vesper (rice).
# ~/.zshrc sources this before the next prompt whenever the theme changes.
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#505050"
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES=(
  default "fg=#ffffff"
  unknown-token "fg=#ff8080"
  reserved-word "fg=#a0a0a0"
  command "fg=#ffc799,bold"
  alias "fg=#ffc799"
  builtin "fg=#ffc799"
  function "fg=#ffc799"
  precommand "fg=#ffc799,underline"
  path "fg=#ffffff,underline"
  path_prefix "fg=#ffffff"
  globbing "fg=#99ffe4"
  history-expansion "fg=#99ffe4"
  single-hyphen-option "fg=#a0a0a0"
  double-hyphen-option "fg=#a0a0a0"
  single-quoted-argument "fg=#99ffe4"
  double-quoted-argument "fg=#99ffe4"
  dollar-quoted-argument "fg=#99ffe4"
  dollar-double-quoted-argument "fg=#ffc799"
  assign "fg=#a0a0a0"
  redirection "fg=#a0a0a0"
  comment "fg=#7e7e7e"
)
