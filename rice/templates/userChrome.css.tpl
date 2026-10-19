/* Zen browser chrome colours for {{ rice_theme_name }} (rice). */
:root {
  --toolbar-bgcolor: {{ background }} !important;
  --toolbar-color: {{ foreground }} !important;
  --toolbar-field-background-color: {{ ui_surface }} !important;
  --toolbar-field-color: {{ foreground }} !important;
  --toolbar-field-border-color: {{ ui_border }} !important;
  --toolbar-field-focus-background-color: {{ ui_surface }} !important;
  --toolbar-field-focus-border-color: {{ accent }} !important;
  --toolbar-field-focus-color: {{ foreground }} !important;

  --tab-selected-bgcolor: {{ ui_surface }} !important;
  --lwt-accent-color: {{ background }} !important;
  --lwt-text-color: {{ foreground }} !important;

  --arrowpanel-background: {{ ui_surface }} !important;
  --arrowpanel-color: {{ foreground }} !important;
  --arrowpanel-border-color: {{ ui_border }} !important;

  --sidebar-background-color: {{ background }} !important;
  --sidebar-text-color: {{ foreground }} !important;
  --sidebar-border-color: {{ ui_border }} !important;

  --zen-main-browser-background: {{ background }} !important;
  --zen-colors-primary: {{ background }} !important;
  --zen-colors-secondary: {{ ui_surface }} !important;
  --zen-colors-tertiary: {{ selection }} !important;
  --zen-colors-border: {{ ui_border }} !important;
  --zen-primary-color: {{ accent }} !important;
  --zen-urlbar-background-base: {{ ui_surface }} !important;
}

#zen-toolbar-background,
#zen-toolbar-background::after,
.zen-toolbar-background,
.zen-toolbar-background::after,
#sidebar-box,
#titlebar,
#navigator-toolbox {
  background-color: {{ background }} !important;
}

#tabbrowser-tabs .tabbrowser-tab[selected="true"] .tab-background {
  background-color: {{ ui_surface }} !important;
}
