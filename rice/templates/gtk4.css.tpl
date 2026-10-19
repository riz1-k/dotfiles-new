/* libadwaita / GTK4 colours for {{ rice_theme_name }} (rice). */
:root {
  --accent-color: {{ accent }};
  --accent-bg-color: {{ accent }};
  --accent-fg-color: {{ ui_on_accent }};
  --destructive-color: {{ ui_danger }};
  --destructive-bg-color: {{ ui_danger }};
  --destructive-fg-color: {{ background }};
  --success-color: {{ ui_success }};
  --success-bg-color: {{ ui_success }};
  --success-fg-color: {{ background }};
  --warning-color: {{ ui_warning }};
  --warning-bg-color: {{ ui_warning }};
  --warning-fg-color: {{ background }};
  --error-color: {{ ui_danger }};
  --error-bg-color: {{ ui_danger }};
  --error-fg-color: {{ background }};
  --window-bg-color: {{ background }};
  --window-fg-color: {{ foreground }};
  --view-bg-color: {{ background }};
  --view-fg-color: {{ foreground }};
  --headerbar-bg-color: {{ background }};
  --headerbar-fg-color: {{ ui_dim }};
  --headerbar-border-color: {{ ui_border }};
  --headerbar-backdrop-color: {{ background }};
  --headerbar-shade-color: {{ ui_shade }};
  --card-bg-color: {{ ui_surface }};
  --card-fg-color: {{ foreground }};
  --card-shade-color: {{ ui_shade }};
  --dialog-bg-color: {{ background }};
  --dialog-fg-color: {{ foreground }};
  --popover-bg-color: {{ ui_surface }};
  --popover-fg-color: {{ foreground }};
  --popover-shade-color: {{ ui_shade }};
  --shade-color: {{ ui_shade }};
  --scrollbar-outline-color: rgba({{ foreground_rgb }}, 0.08);
  --sidebar-bg-color: {{ background }};
  --sidebar-fg-color: {{ foreground }};
  --sidebar-backdrop-color: {{ background }};
  --sidebar-shade-color: {{ ui_shade }};
  --sidebar-border-color: {{ ui_border }};
}

/* Subtle window corners for libadwaita / GTK4 CSD windows */
window,
window.background,
window.csd,
window.background.csd,
window.csd > decoration {
  border-radius: 6px;
}
