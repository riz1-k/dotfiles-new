# zsh-syntax-highlighting / autosuggestions colours for {{ rice_theme_name }} (rice).
# ~/.zshrc sources this before the next prompt whenever the theme changes.
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg={{ ui_faint }}"
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES=(
  default "fg={{ foreground }}"
  unknown-token "fg={{ ui_danger }}"
  reserved-word "fg={{ ui_dim }}"
  command "fg={{ accent }},bold"
  alias "fg={{ accent }}"
  builtin "fg={{ accent }}"
  function "fg={{ accent }}"
  precommand "fg={{ accent }},underline"
  path "fg={{ foreground }},underline"
  path_prefix "fg={{ foreground }}"
  globbing "fg={{ ui_success }}"
  history-expansion "fg={{ ui_success }}"
  single-hyphen-option "fg={{ ui_dim }}"
  double-hyphen-option "fg={{ ui_dim }}"
  single-quoted-argument "fg={{ ui_success }}"
  double-quoted-argument "fg={{ ui_success }}"
  dollar-quoted-argument "fg={{ ui_success }}"
  dollar-double-quoted-argument "fg={{ accent }}"
  assign "fg={{ ui_dim }}"
  redirection "fg={{ ui_dim }}"
  comment "fg={{ muted }}"
)
