# desktop-widgets

Desktop widgets for [Gtk4 Desktop Icons NG](https://extensions.gnome.org/extension/5263/gtk4-desktop-icons-ng-ding/),
styled to match the rice: Flexoki Light / Vesper, switching live with theme-sync.

| Widget | Shows | Backend |
| --- | --- | --- |
| `widgets/system-info` | CPU graph, RAM, disk, CPU temp, battery, network, load | `backend.py`, reads `/proc` and `/sys` |
| `widgets/ai-usage` | Claude / Codex limits and service status | `backend.js` (gjs), imports `api.js` from the ai-usage-bar extension |
| `widgets/clock-weather` | Clock, month calendar with upcoming events, current weather and the next 6 hours | `backend.py`, Open-Meteo (no API key), GNOME's clock settings and Evolution Data Server for events |
| `widgets/github` | Infra PRs you're tagged on, Smart Product PRs into dev/qa/main, unread notifications | `backend.py`, runs the logged-in `gh` CLI |
| `widgets/now-playing` | Track, art, progress and controls for the active MPRIS player | `backend.js` (gjs), session D-Bus |

## Layout

- `shared/rice.css`: the palette (from `~/dotfiles/theme-sync`) and card styles. `shared/host.js`
  wires up the Gtk4-DING bridge. Each widget symlinks both; `install.sh` copies the real files.
- `ding/stylesheet-override.css`: Gtk4-DING's edit-mode outline in the rice accent.
- `preview/`: both widgets in both themes over the wallpaper, with fake data.

## Install / update

Needs `gir1.2-webkit-6.0` (and `gir1.2-ecal-2.0` for calendar events) and Gtk4-DING with **Show Desktop Widgets** on.

```sh
./install.sh
```

Then right-click the desktop → **Edit Widgets** → **+** to add a widget, and allow its backend
the first time. Widget positions are saved in `~/.local/share/com.desktop.ding/widgets.json`.

## Preview while editing

```sh
python3 -m http.server 8766   # from this folder
# open http://127.0.0.1:8766/preview/
```

Inside Gtk4-DING, backend output and widget `ding.log()` calls show up in
`journalctl --user -f | grep -i ding`.

## Notes

- The AI widget refreshes every 5 minutes (`refreshSec` in `widget.json`, minimum 60), on top
  of the panel extension's own 3-minute refresh. If the usage API starts rate limiting,
  raise `refreshSec`.
- Weather is for Bengaluru: change `place`, `latitude` and `longitude` in the clock-weather
  `widget.json` (or the instance's `config` in `widgets.json`). The clock follows GNOME's
  12/24h and seconds settings, and the calendar starts on the locale's first weekday.
- Events come from the calendars GNOME knows about: add a Google account in Settings → Online
  Accounts with Calendar on, and Evolution Data Server syncs it (no API keys here). The widget
  uses the calendars switched on in GNOME Calendar and skips cancelled and declined events.
  - Under the forecast, the next six hours of events sit on the same time axis as the hours
    (starting with "Now"), so you can see what the weather does during a meeting. A line marks now.
  - The month dots each day with the colors of its calendars. ‹ ›, or scrolling over the grid,
    changes month; clicking a day lists its events, and clicking it again (or Today, or Esc)
    goes back. It drifts back to today after 45 seconds untouched.
  - Up next lists what's left of today, then tomorrow, with all-day events as chips on top. The
    event in progress has a progress bar and the time left; the next hour's events count down.
    Meet, Zoom and Teams links get a Join button from 10 minutes before. Rows that don't fit
    become "+N tomorrow", which opens that day.
  - Clicking an event opens it on calendar.google.com, in `browser` (a desktop file id, empty
    for the default browser), from the backend like the GitHub widget.
  - It rereads Evolution's local copy every minute; Evolution syncs with Google on its own.
- GitHub refreshes every 2 minutes (`refreshSec`). Clicking a row, a section title or the bell
  opens the page in Island (`browser`: a desktop file id; set it to `""` for the default
  browser). The backend launches the browser itself, because links opened by the widget make
  Gtk4-DING ask for confirmation every time. Only `https://github.com/` links are accepted.
  The username in the header is an account picker, populated from `gh auth status`. Choosing an
  account runs `gh auth switch --hostname github.com --user USER` and refreshes the lists and
  counts for that account. This also changes the active account for terminal `gh` commands.
  Accounts added with `gh auth login` appear on the next refresh. The picker is disabled while
  switching, with only one account, or when `GH_TOKEN` / `GITHUB_TOKEN` overrides saved accounts.
- Now Playing picks the player that's playing (or was most recently). With more than one player,
  the arrows button cycles through them. Widgets can only show `data:` images, so the backend
  reads the art (local file or https), scales it to 192px and sends it inline. With nothing
  playing, the card collapses to a one-line "Nothing playing".
- Gtk4-DING doesn't pass clicks to widgets on the desktop layer (only in Edit Widgets mode), so
  the widgets you click (GitHub, Now Playing) are **pinned**: each gets its own window, kept
  below apps with `keep-pinned-widgets-below-apps`. Deja Window must leave `com.desktop.ding`
  alone (an `excluded_apps` rule): otherwise it centers new pinned windows and Gtk4-DING saves
  that as their position.
- The GitHub lists come from `sections` (defaults in `widgets/github/backend.py`): Infra shows PRs
  where you're requested personally or @mentioned (team requests don't count); Smart Product
  shows every open PR into dev, qa or main. Override with a `sections` list in the instance
  config. The bell shows the exact unread count, read from the last-page link of a one-per-page
  request (GitHub returns at most 50 per page).
- With an external display connected, the widgets move there; unplug it and they move back to
  the laptop. `ding/widgets-follow-display.py` (the `desktop-widgets-display` user service, set
  up by `install.sh`) watches Mutter for display changes, places each widget at the same
  distance from the nearer side edge and the top, and restarts Gtk4-DING's desktop process.
  It relearns those distances whenever you move a widget (`~/.config/desktop-widgets/layout.json`).
  `python3 ding/widgets-follow-display.py --print` shows the displays it sees and its pick.
- Gtk4-DING clips every widget to an 8px rounded frame; `rice.css` insets the card by 2px so
  its 6px corners and border stay intact.
