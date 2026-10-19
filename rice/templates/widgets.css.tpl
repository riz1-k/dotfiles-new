/* Desktop widget palette for {{ rice_theme_name }} (rice). Loaded after the widgets'
   shared/rice.css and overrides its variables; the widget backends push a new copy
   into open widgets when the theme changes. */
html body,
html body[data-theme] {
    --bg: rgba({{ ui_surface_rgb }}, 0.95);
    --border: rgba({{ foreground_rgb }}, 0.14);
    --fg: {{ foreground }};
    --muted: {{ ui_dim }};
    --faint: {{ ui_faint }};
    --track: {{ ui_surface_alt }};
    --divider: {{ ui_border }};
    --accent: {{ accent }};
    --ok: {{ ui_success }};
    --warn: {{ ui_warning }};
    --crit: {{ ui_danger }};
    --info: {{ ui_info }};
    --cpu-start: {{ cyan }};
    --cpu-mid: {{ accent }};
    --cpu-end: {{ red }};
    --mem: {{ green }};
    --disk: {{ blue }};
    --down: {{ magenta }};
    --up: {{ accent }};
    --temp-start: {{ green }};
    --temp-mid: {{ yellow }};
    --temp-end: {{ red }};
}
