# {{ rice_theme_name }} (rice template, from theme-sync's Vesper file)
[meta]
name = "{{ rice_theme_name }}"
description = "rice theme"
variant = "{{ mode }}"
inherits = "vicinae-{{ mode }}"

[colors.core]
background = "{{ background }}"
foreground = "{{ foreground }}"
secondary_background = "{{ ui_surface }}"
border = "{{ ui_border }}"
accent = "{{ accent }}"
accent_foreground = "{{ ui_on_accent }}"

[colors.main_window]
border = "{{ mix background foreground 14% }}"
footer = { background = "{{ background }}" }

[colors.settings_window]
border = "{{ mix background foreground 14% }}"

[colors.accents]
blue = "{{ blue }}"
green = "{{ green }}"
magenta = "{{ magenta }}"
orange = "{{ orange }}"
red = "{{ red }}"
yellow = "{{ yellow }}"
cyan = "{{ cyan }}"
purple = "{{ bright_magenta }}"

[colors.shortcut]
border = "{{ mix background foreground 14% }}"

[colors.text]
default = "{{ foreground }}"
muted = "{{ ui_dim }}"
danger = "{{ ui_danger }}"
success = "{{ ui_success }}"
placeholder = "{{ mix foreground background 55% }}"
selection = { background = "#59{{ accent_strip }}", foreground = "{{ foreground }}" }

[colors.text.links]
default = "{{ accent }}"
visited = "{{ mix accent foreground 20% }}"

[colors.input]
background = "{{ mix background foreground 4% }}"
border = "{{ ui_border }}"
border_focus = "{{ accent }}"
border_error = "{{ ui_danger }}"

[colors.button.primary]
background = "{{ mix background foreground 4% }}"
foreground = "{{ foreground }}"
hover = { background = "{{ ui_border }}", foreground = "{{ foreground }}" }
focus = { outline = "{{ accent }}" }

[colors.list.item.hover]
background = "{{ mix background foreground 3% }}"
foreground = "{{ foreground }}"
secondary_foreground = "{{ ui_dim }}"

[colors.list.item.selection]
background = "{{ selection }}"
foreground = "{{ foreground }}"
secondary_background = "{{ mix background foreground 10% }}"
secondary_foreground = "{{ ui_dim }}"

[colors.grid.item]
background = "{{ ui_surface }}"
hover = { outline = "{{ ui_faint }}" }
selection = { outline = "{{ accent }}" }

[colors.scrollbars]
background = "{{ mix background foreground 14% }}"

[colors.tooltip]
background = "{{ ui_surface }}"
foreground = "{{ foreground }}"
border = "{{ ui_border }}"

[colors.loading]
bar = "{{ accent }}"
spinner = "{{ accent }}"
