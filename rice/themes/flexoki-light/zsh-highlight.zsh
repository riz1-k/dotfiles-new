# zsh-syntax-highlighting / autosuggestions colours for Flexoki Light (rice).
# ~/.zshrc sources this before the next prompt whenever the theme changes.
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#b7b5ac"
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES=(
  default "fg=#100f0f"
  unknown-token "fg=#af3029"
  reserved-word "fg=#6f6e69"
  command "fg=#bc5215,bold"
  alias "fg=#bc5215"
  builtin "fg=#bc5215"
  function "fg=#bc5215"
  precommand "fg=#bc5215,underline"
  path "fg=#100f0f,underline"
  path_prefix "fg=#100f0f"
  globbing "fg=#24837b"
  history-expansion "fg=#24837b"
  single-hyphen-option "fg=#6f6e69"
  double-hyphen-option "fg=#6f6e69"
  single-quoted-argument "fg=#24837b"
  double-quoted-argument "fg=#24837b"
  dollar-quoted-argument "fg=#24837b"
  dollar-double-quoted-argument "fg=#bc5215"
  assign "fg=#6f6e69"
  redirection "fg=#6f6e69"
  comment "fg=#878580"
)
