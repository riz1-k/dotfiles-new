# rice

One command recolours the whole desktop, Omarchy style. Pick a theme from a carousel
(<kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Space</kbd>). GNOME Shell,
GTK, the wallpaper, terminals, editors, TUIs, browsers, agents and the desktop widgets
all switch together under one cross-fade. Themes use [Omarchy's format](docs/themes.md),
so every Omarchy theme works as is: the stock ones (`rice theme import-omarchy`) and the
community ones (`rice theme install <git url>`).

```sh
./install.sh            # once; then log out and back in
rice theme set tokyo-night
```

## Using it

| | |
| --- | --- |
| <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Space</kbd> | theme carousel: ←/→, type to filter, Enter apply, Del remove, Esc close |
| <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>Space</kbd> | background carousel for the current theme |
| Quick Settings → Dark Style | switches to the current theme's light/dark pair |
| vicinae | "Pick Theme", "Next Theme", "Set Theme", "Next Background", "Install Theme", "Rice Doctor", … |

```text
rice theme list | current | set <name> | next | prev | picker | refresh
rice theme install <git url> | remove <name> | update | import-omarchy [--all|--list]
rice theme new <name> [--from <theme>] [--image <wallpaper> [--light]] [--edit]
rice theme preview [<name>] [--json | --image FILE]
rice bg next | prev | set <file> | picker | open | list
rice mode toggle | dark | light | status
rice apply <app>...      re-apply one app (e.g. rice apply tmux kitty)
rice doctor              is every app wired up?
rice settings            create ~/.config/rice/settings.toml (commented defaults), print its path
```

`rice theme set` returns as soon as what's on screen has switched (the shell,
wallpaper, terminals, tmux, btop; about 0.1 s). The rest (editors, browsers, agents,
GTK, widgets) finishes in the background. `--wait` (or a terminal) waits for all of
it. Problems go to `~/.local/state/rice/theme-set.log` and a notification.

`rice theme new` with `--image` gets its palette from the wallpaper via
[Aether](https://github.com/bjarneo/aether) (`aether` on your PATH); without Aether,
or with `--from`, it copies an existing theme's palette for you to edit.

## What follows the theme

| App | How |
| --- | --- |
| GNOME Shell | the `rice-shell` extension loads the theme's shell stylesheet (a recoloured Yaru plus the bar) and sets the colour scheme, accent and wallpaper in one go |
| GTK 4 / libadwaita | `~/.config/gtk-4.0/gtk.css`, both of the pair's palettes in `prefers-color-scheme` blocks, so open apps follow Dark Style live |
| GTK 3, icons | `~/.config/gtk-3.0/gtk.css`; Colloid icons in the theme's accent colour |
| ghostty, kitty | `config-file` / `include` of the theme's file, reloaded with a signal |
| tmux, btop, herdr | re-sourced / theme file + SIGUSR2 / `reload-config` |
| Neovim | `nvim/lua/rice`: loads the theme's colorscheme plugin, switches live |
| zsh | syntax highlighting re-sourced before the next prompt |
| VS Code, Cursor, Obsidian | the theme's `vscode.json` extension, or a generated theme |
| Claude Code, Codex, T3 Code | generated themes, set in each one's settings (every `~/.claude*` account) |
| Zen, Vencord, Chromium | `userChrome.css`/`userContent.css`, `quickCss.css`, a managed policy (off by default) |
| lazygit, gitui, yazi, vicinae | generated theme files |
| desktop widgets | `widgets.css`, pushed live by each widget's backend |
| window borders | p7-borders, tilingshell, tiling-assistant, rounded-window-corners |

`~/.config/rice/settings.toml` (`rice settings` creates it) turns apps off and picks the
light/dark pair and the icon style.

## Layout

```text
bin/rice            the command          lib/rice/        the engine (stdlib Python)
extension/          rice-shell@riz1      templates/       *.tpl for themes that lack a file
themes/             stock themes         nvim/            the Neovim side
vicinae/            script commands      systemd/         rice-mode-watch.service
tests/              python3 -m unittest discover -s tests
```

At run time: your themes in `~/.config/rice/themes`, Omarchy imports in
`~/.local/share/rice/themes`, the applied theme in `~/.local/state/rice/current`, your
own templates in `~/.config/rice/themed/*.tpl` (they win over the stock ones), and
hooks in `~/.config/rice/hooks/theme-set*` (run with the theme name after every switch).

## Safety

Themes installed with git are treated as untrusted. Nothing in them that runs code
(scripts, `*.lua`, executables, app configs that can run commands) and no symlink is
ever staged; rice generates those files from the palette instead and tells you what
it left out. Git runs without hooks, prompts or `ext::` transports, and URLs that git
would read as options are refused.

`install.sh` backs up every config rice manages to
`~/.local/state/rice/backup/pre-rice.tar.gz` (plus a `dconf dump` of `/org/gnome/`)
before the first switch.

## Credits

The theme format, palette rules, template syntax and several templates come from
[Omarchy](https://github.com/basecamp/omarchy) (MIT, see `templates/LICENSE.omarchy`).
