"""Discord (Vencord / Vesktop), Zen and, if enabled, Chrome/Edge's toolbar colour."""
import json
import re
import subprocess
from pathlib import Path

from .. import colormath as cm
from .. import util


def vencord(ctx):
    css = ctx.file("quickCss.css")
    if not css:
        return
    for d in (ctx.paths.config / "Vencord" / "settings", ctx.paths.config / "vesktop" / "settings"):
        if d.is_dir():
            # Vencord watches this file and swaps the CSS in every open window.
            util.install_file(css, d / "quickCss.css")


def zen_profiles(paths):
    for root in (paths.home / ".var/app/app.zen_browser.zen/.zen", paths.home / ".zen"):
        ini = root / "profiles.ini"
        if not ini.is_file():
            continue
        for m in re.finditer(r"(?m)^Path=(.+)$", ini.read_text()):
            p = root / m.group(1).strip()
            if p.is_dir():
                yield p


def zen(ctx):
    chrome, content = ctx.file("userChrome.css"), ctx.file("userContent.css")
    if not chrome:
        return
    for profile in zen_profiles(ctx.paths):
        d = profile / "chrome"
        d.mkdir(exist_ok=True)
        util.install_file(chrome, d / "userChrome.css")
        if content:
            util.install_file(content, d / "userContent.css")
        # userChrome.css is only read when this pref is on.
        user_js = profile / "user.js"
        text = user_js.read_text() if user_js.is_file() else ""
        new = zen_enable_stylesheets(text)
        if new != text:
            util.atomic_write(user_js, new)


STYLESHEETS_PREF = "toolkit.legacyUserProfileCustomizations.stylesheets"
# An active user_pref line for it (not one in a comment), any quoting and spacing.
_PREF_LINE = re.compile(r'(?m)^([ \t]*user_pref\(\s*(["\'])' + re.escape(STYLESHEETS_PREF)
                        + r'\2\s*,\s*)(true|false)(\s*\)\s*;?)')


def _without_comments(text):
    """text with // and /* */ comments blanked out (same length, newlines kept), so
    matches in it are active code. Strings are skipped while looking for comments."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < n and text[j] != ch and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = [c if c == "\n" else " " for c in text[i:j]]
            i = j
        else:
            i += 1
    return "".join(out)


def zen_enable_stylesheets(text):
    """user.js with the stylesheet pref on; the last active line wins in Firefox, so
    every active one is set to true. Comments (// and /* */) and other prefs are kept."""
    spans = [m for m in _PREF_LINE.finditer(_without_comments(text))]
    if spans:
        for m in reversed(spans):  # same offsets in text: blanking keeps lengths
            a, b = m.span(3)
            text = text[:a] + "true" + text[b:]
        return text
    pref = f'user_pref("{STYLESHEETS_PREF}", true);'
    return text + ("\n" if text and not text.endswith("\n") else "") + pref + "\n"


POLICY_DIRS = ["/etc/opt/chrome/policies/managed", "/etc/opt/edge/policies/managed",
               "/etc/chromium/policies/managed", "/etc/brave/policies/managed"]


def chromium(ctx):
    """Off unless [apps] chromium = true: writes a root-owned policy with sudo -n."""
    theme = ctx.file("chromium.theme")
    if not theme:
        return
    parts = theme.read_text().strip().split(",")
    if len(parts) != 3 or not all(p.strip().isdigit() and 0 <= int(p) <= 255 for p in parts):
        raise RuntimeError(f"chromium.theme is not r,g,b: {theme.read_text()[:40]!r}")
    color = cm.to_hex(int(p) for p in parts)
    policy = json.dumps({"BrowserThemeColor": color, "BrowserColorScheme": "device"})
    if util.SANDBOX:
        return
    dirs = [d for d in POLICY_DIRS if Path(d).parent.parent.is_dir()]
    for d in dirs:
        current = Path(d) / "color.json"
        if current.is_file() and current.read_text() == policy:
            continue
        r = subprocess.run(["sudo", "-n", "sh", "-c",
                            f'mkdir -p "{d}" && cat > "{d}/color.json" && chmod 644 "{d}/color.json"'],
                           input=policy, text=True, capture_output=True, timeout=10)
        if r.returncode != 0:
            raise RuntimeError(f"browser policy needs sudo: {r.stderr.strip()[:120]}")
    for cli in ("google-chrome", "microsoft-edge"):
        if util.have(cli) and util.pids("chrome" if "chrome" in cli else "msedge"):
            subprocess.run([cli, "--refresh-platform-policy", "--no-startup-window"],
                           capture_output=True, timeout=10)
