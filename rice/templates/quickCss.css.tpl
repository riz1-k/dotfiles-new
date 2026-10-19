/* Discord (Vencord QuickCSS) colours for {{ rice_theme_name }} (rice). */
:root {
    /* Core surfaces */
    --background-primary: {{ background }};
    --background-secondary: {{ ui_surface }};
    --background-secondary-alt: {{ background }};
    --background-tertiary: {{ ui_surface }};
    --background-floating: {{ ui_surface }};
    --background-mobile-primary: {{ background }};
    --background-mobile-secondary: {{ ui_surface }};
    --background-accent: {{ selection }};
    --background-modifier-hover: rgba({{ foreground_rgb }}, 0.05);
    --background-modifier-selected: {{ selection }};
    --background-modifier-active: {{ ui_border }};
    --background-modifier-accent: {{ ui_border }};
    --channeltextarea-background: {{ ui_surface }};

    /* Brand / accent (peach replaces blurple) */
    --brand-experiment: {{ accent }};
    --brand-experiment-560: {{ mix accent background 12% }};
    --brand-500: {{ accent }};
    --brand-560: {{ mix accent background 12% }};

    /* Text */
    --header-primary: {{ foreground }};
    --header-secondary: {{ ui_dim }};
    --text-normal: {{ foreground }};
    --text-muted: {{ muted }};
    --text-link: {{ accent }};
    --text-positive: {{ ui_success }};
    --text-warning: {{ ui_warning }};
    --text-danger: {{ ui_danger }};

    /* Interactive */
    --interactive-normal: {{ ui_dim }};
    --interactive-hover: {{ foreground }};
    --interactive-active: {{ accent }};
    --interactive-muted: {{ ui_faint }};

    /* Status dots */
    --status-online: {{ ui_success }};
    --status-idle: {{ ui_warning }};
    --status-dnd: {{ ui_danger }};
    --status-positive-background: {{ ui_success }};
    --status-warning-background: {{ ui_warning }};
    --status-danger-background: {{ ui_danger }};

    /* Scrollbars */
    --scrollbar-thin-thumb: {{ ui_border }};
    --scrollbar-auto-thumb: {{ ui_border }};
    --scrollbar-auto-track: {{ background }};
}
