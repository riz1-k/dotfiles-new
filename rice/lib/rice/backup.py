"""What install.sh backs up before the first switch: every existing file a retint
edits in place, found with the same lookups the retints use (Claude accounts,
CODEX_HOME, T3CODE_HOME, Zen profiles from profiles.ini...). Files rice only adds
(its own theme files) aren't listed; nothing needs them to go back.
"""
from .apps import agents, web


def targets(paths):
    c, h = paths.config, paths.home
    files = [c / "gtk-4.0" / "gtk.css", c / "gtk-4.0" / "gtk-dark.css", c / "gtk-3.0" / "gtk.css",
             c / "btop" / "btop.conf"]
    files += [d / "settings.json" for d in agents.claude_dirs(paths)]
    files += [agents.codex_home(paths) / "config.toml", agents.t3_userdata(paths) / "settings.json"]
    for app, ext in (("Code", ".vscode"), ("Cursor", ".cursor")):
        files += [c / app / "User" / "settings.json", h / ext / "extensions" / "extensions.json",
                  h / ext / "extensions" / ".obsolete"]
    files += [c / "Vencord" / "settings" / "quickCss.css", c / "vesktop" / "settings" / "quickCss.css",
              c / "vicinae" / "settings.json", c / "lazygit" / "config.yml", c / "gitui" / "theme.ron",
              c / "yazi" / "theme.toml"]
    for profile in web.zen_profiles(paths):
        files += [profile / "chrome" / "userChrome.css", profile / "chrome" / "userContent.css",
                  profile / "user.js"]
    files += sorted((c / "kitty").glob("*-theme.auto.conf"))  # install.sh removes these
    seen, out = set(), []
    for f in files:
        if (f.exists() or f.is_symlink()) and f not in seen:
            seen.add(f)
            out.append(f)
    return out
