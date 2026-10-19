/* Zen browser page colours for {{ rice_theme_name }} (rice). */
:root {
  --in-content-page-background: {{ background }} !important;
  --in-content-page-color: {{ foreground }} !important;
  --in-content-box-background: {{ ui_surface }} !important;
  --in-content-box-background-hover: {{ selection }} !important;
  --in-content-box-border-color: {{ ui_border }} !important;
  --in-content-border-color: {{ ui_border }} !important;
  --in-content-accent-color: {{ accent }} !important;
  --in-content-link-color: {{ accent }} !important;
  --in-content-link-color-hover: {{ mix accent foreground 20% }} !important;
  --in-content-button-background: {{ ui_surface }} !important;
  --in-content-button-background-hover: {{ selection }} !important;
  --in-content-primary-button-background: {{ accent }} !important;
  --in-content-primary-button-text-color: {{ background }} !important;
}
