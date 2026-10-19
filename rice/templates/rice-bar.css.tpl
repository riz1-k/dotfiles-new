/* rice-shell colours for {{ rice_theme_name }} (rice template). Appended to the
   theme's shell stylesheet; the layout lives in the extension's stylesheet.css.
   Colours are !important so they win over the extension's stylesheet and over
   shell themes that mark their panel colours !important. */

/* ---- bar islands ------------------------------------------------------------ */

#panelBox #panel.rice-bar #panelLeft,
#panelBox #panel.rice-bar #panelRight {
  border-color: rgba({{ foreground_rgb }}, 0.14) !important;
  background-color: rgba({{ ui_surface_rgb }}, 0.95) !important;
}

#panelBox #panel.rice-bar .panel-button {
  background-color: transparent !important;
  box-shadow: none !important;
}

#panelBox #panel.rice-bar .panel-button,
#panelBox #panel.rice-bar .panel-button StIcon,
#panelBox #panel.rice-bar .panel-button StLabel {
  color: {{ foreground }} !important;
}

#panelBox #panel.rice-bar .panel-button:hover,
#panelBox #panel.rice-bar .panel-button:focus {
  box-shadow: inset 0 0 0 100px rgba({{ foreground_rgb }}, 0.08) !important;
}

#panelBox #panel.rice-bar .panel-button:active,
#panelBox #panel.rice-bar .panel-button:checked {
  box-shadow: inset 0 0 0 100px rgba({{ foreground_rgb }}, 0.13) !important;
}

#panelBox #panel.rice-bar .panel-button#panelActivities .workspace-dot {
  background-color: {{ foreground }} !important;
}

#panelBox #panel.rice-bar .rice-sep {
  background-color: {{ ui_border }} !important;
}

#panelBox #panel.rice-bar .ai-usage-value.ai-usage-warn { color: {{ ui_warning }} !important; }
#panelBox #panel.rice-bar .ai-usage-value.ai-usage-crit,
#panelBox #panel.rice-bar .ai-usage-alert { color: {{ ui_danger }} !important; }
#panelBox #panel.rice-bar .ai-usage-value.ai-usage-dim { color: {{ ui_faint }} !important; }

/* ---- the capsule (the inverse surface) ----------------------------------------- */

#panelBox #panel.rice-bar .panel-button.rice-capsule {
  background-color: {{ ui_inverse }} !important;
}

#panelBox #panel.rice-bar .panel-button.rice-capsule:hover,
#panelBox #panel.rice-bar .panel-button.rice-capsule:focus {
  box-shadow: none !important;
  background-color: {{ mix ui_inverse ui_inverse_fg 7% }} !important;
}

#panelBox #panel.rice-bar .panel-button.rice-capsule:active,
#panelBox #panel.rice-bar .panel-button.rice-capsule:checked {
  box-shadow: none !important;
  background-color: {{ mix ui_inverse ui_inverse_fg 12% }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-main {
  color: {{ ui_inverse_fg }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-lead,
#panelBox #panel.rice-bar .rice-capsule .rice-trail {
  color: {{ ui_inverse_dim }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-meeting .rice-trail,
#panelBox #panel.rice-bar .rice-capsule .messages-indicator {
  color: {{ ui_inverse_accent }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-meeting .rice-badge {
  background-color: {{ ui_inverse_accent }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-meeting .rice-badge-icon {
  color: {{ ui_inverse_on_accent }} !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-flash .rice-badge {
  background-color: rgba({{ ui_inverse_fg_rgb }}, 0.12) !important;
}

#panelBox #panel.rice-bar .rice-capsule .rice-flash .rice-badge-icon {
  color: {{ ui_inverse_fg }} !important;
}

/* ---- pickers ------------------------------------------------------------------- */

.rice-picker {
  background-color: rgba({{ background_rgb }}, 0.86) !important;
}

.rice-picker-card {
  background-color: {{ ui_surface }} !important;
  border-color: rgba({{ foreground_rgb }}, 0.10) !important;
}

.rice-picker-card.rice-picker-selected {
  border-color: {{ accent }} !important;
}

.rice-picker-title {
  color: {{ foreground }} !important;
}

.rice-picker-subtitle,
.rice-picker-hint {
  color: {{ ui_dim }} !important;
}

.rice-picker-filter {
  color: {{ ui_on_accent }} !important;
  background-color: {{ accent }} !important;
}

.rice-picker-confirm {
  color: {{ foreground }} !important;
  background-color: {{ ui_surface }} !important;
  border-color: {{ ui_danger }} !important;
}

.rice-picker-badge {
  color: {{ ui_on_accent }} !important;
  background-color: {{ accent }} !important;
}
