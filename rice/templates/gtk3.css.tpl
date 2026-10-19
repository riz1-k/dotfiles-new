/* {{ rice_theme_name }}: GTK3 named colours (rice template) */

@define-color theme_bg_color {{ background }};
@define-color theme_fg_color {{ foreground }};
@define-color theme_base_color {{ background }};
@define-color theme_text_color {{ foreground }};

@define-color theme_selected_bg_color {{ accent }};
@define-color theme_selected_fg_color {{ ui_on_accent }};

@define-color insensitive_bg_color {{ ui_surface }};
@define-color insensitive_fg_color {{ muted }};
@define-color insensitive_base_color {{ background }};

@define-color theme_unfocused_bg_color {{ background }};
@define-color theme_unfocused_fg_color {{ ui_dim }};
@define-color theme_unfocused_base_color {{ background }};
@define-color theme_unfocused_selected_bg_color {{ selection }};
@define-color theme_unfocused_selected_fg_color {{ accent }};

@define-color borders {{ ui_border }};
@define-color unfocused_borders {{ ui_border }};

@define-color warning_color {{ ui_warning }};
@define-color error_color {{ ui_danger }};
@define-color success_color {{ ui_success }};

@define-color accent_color {{ accent }};
@define-color accent_bg_color {{ accent }};
@define-color accent_fg_color {{ ui_on_accent }};

/* Subtle window corners for GTK3 CSD windows */
decoration,
window.csd,
window.background.csd {
  border-radius: 6px;
}
