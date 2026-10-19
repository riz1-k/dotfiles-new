# zsh-syntax-highlighting / autosuggestions colours for Sample (rice).
# ~/.zshrc sources this before the next prompt whenever the theme changes.
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#636360"
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES=(
  default "fg=#d8d4c6"
  unknown-token "fg=#e06c6c"
  reserved-word "fg=#908e88"
  command "fg=#5fa8d3,bold"
  alias "fg=#5fa8d3"
  builtin "fg=#5fa8d3"
  function "fg=#5fa8d3"
  precommand "fg=#5fa8d3,underline"
  path "fg=#d8d4c6,underline"
  path_prefix "fg=#d8d4c6"
  globbing "fg=#8cc085"
  history-expansion "fg=#8cc085"
  single-hyphen-option "fg=#908e88"
  double-hyphen-option "fg=#908e88"
  single-quoted-argument "fg=#8cc085"
  double-quoted-argument "fg=#8cc085"
  dollar-quoted-argument "fg=#8cc085"
  dollar-double-quoted-argument "fg=#5fa8d3"
  assign "fg=#908e88"
  redirection "fg=#908e88"
  comment "fg=#5c6370"
)
