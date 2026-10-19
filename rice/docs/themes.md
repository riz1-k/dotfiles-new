# Themes

A theme is a folder in [Omarchy's format](https://learn.omacom.io/2/the-omarchy-manual/92/making-your-own-theme).
Only `colors.toml` is required; everything else is optional, and rice renders
whatever's missing from the palette.

```text
my-theme/
  colors.toml        the palette (required)
  backgrounds/       wallpapers, cycled with rice bg next
  preview.png        the picker card (else the first background)
  light.mode         present = a light theme
  icons.theme        an icon theme name (Yaru-<colour> becomes Colloid-<colour>)
  neovim.lua         a LazyVim-style spec: the colorscheme plugin + colorscheme
  vscode.json        {"name": "Theme Name", "extension": "publisher.extension"}
  btop.theme, ghostty.conf, kitty.conf, ...   app files used as they are
  gnome.toml         rice extras for GNOME (below)
```

Where they live, later wins: stock (`rice/themes`), imported from Omarchy
(`~/.local/share/rice/themes`), yours (`~/.config/rice/themes`). A folder of yours with
the same name as a stock or imported theme overlays it file by file.

## colors.toml

Flat `key = "value"` lines. Values are colours: `#rrggbb`, or `#rgb`, `#rrggbbaa`
and `rgb()`/`rgba()`, which become `#rrggbb` (alpha is dropped); `mode` is `light` or
`dark`. Anything else is skipped with a warning. The keys are Omarchy's:

```toml
accent = "#7aa2f7"
background = "#1a1b26"
foreground = "#a9b1d6"
selection_background = "#33467c"
color0 = "#32344a"   # ... through color15: the terminal palette
```

Omarchy's names work too (`red`, `bright_blue`, `dark_background`, `muted`, ...), and
anything left out is derived the way `omarchy-theme-color` does it. Older themes with
only an `alacritty.toml` still work.

rice adds `ui_*` roles for its own templates (the bar, GTK, the widgets). They're
derived from the palette, and you can pin any of them:

| key | used for |
| --- | --- |
| `ui_surface`, `ui_surface_alt`, `ui_border` | cards, bar islands, popovers |
| `ui_dim`, `ui_faint` | secondary and disabled text |
| `ui_on_accent`, `ui_accent_soft` | text on the accent, tinted selections |
| `ui_success`, `ui_warning`, `ui_danger`, `ui_info` | status colours |
| `ui_inverse`, `ui_inverse_fg`, `ui_inverse_dim`, `ui_inverse_accent` | the bar's centre capsule |

## gnome.toml

```toml
accent = "orange"               # GNOME accent; else the nearest to the theme's accent
icons = "Colloid-Orange-Dark"   # an exact icon theme
css = """                       # extra GNOME Shell CSS, appended last
#panel { font-weight: 600; }
"""
```

`css` (like a `gnome-shell.css` or `rice-bar.css` of the theme's own) is only used
from your own themes, never from one installed with git, and `rice theme new --from`
doesn't copy it from one.

## Templates

A file the theme doesn't ship is rendered from `rice/templates/<file>.tpl`, or from
`~/.config/rice/themed/<file>.tpl` if you have one (yours win). The syntax is Omarchy's:

```text
{{ background }}  {{ background_strip }}  {{ background_rgb }}
{{ mix background foreground 30% }}  {{ mix_strip a b 0.3 }}  {{ mix_rgb a b 30 }}
{{ rice_theme }}  {{ rice_theme_name }}
```

## Making one

```sh
rice theme new "My Theme"                     # a copy of the current palette
rice theme new dusk --image ~/Pictures/x.jpg  # palette from the wallpaper (Aether)
rice theme new dawn --image x.jpg --light     # ... a light one
rice theme preview my-theme                   # the palette in the terminal
rice theme set my-theme
```

To share it, push the folder to a git repo named `<name>-theme`. Anyone can then
`rice theme install` it, and `omarchy-theme-install` works too.
