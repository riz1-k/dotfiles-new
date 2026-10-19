"""VS Code, Cursor and Obsidian (a port of omarchy-theme-set-vscode / -obsidian).

A theme can name a marketplace theme in vscode.json ({"name", "extension"}); rice
installs it once. Otherwise the generated vscode-theme.json becomes a local
extension, "Rice". With window.autoDetectColorScheme on, VS Code follows the OS
scheme through workbench.preferred{Dark,Light}ColorTheme, so the one for the
theme's mode is set too.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

from .. import util

EXT_NAME = "rice-theme"
EXT_ID = f"local.{EXT_NAME}"


def _installed(ext_dir, extension):
    registry = ext_dir / "extensions.json"
    try:
        entries = json.loads(registry.read_text())
    except (OSError, json.JSONDecodeError):
        entries = None
    if entries is None:
        return any(p.name.lower().startswith(extension.lower() + "-") for p in ext_dir.glob("*"))
    gone = {}
    try:
        gone = json.loads((ext_dir / ".obsolete").read_text())
    except (OSError, json.JSONDecodeError):
        pass
    for e in entries:
        if (e.get("identifier", {}).get("id", "")).lower() != extension.lower():
            continue
        rel = e.get("relativeLocation") or Path(e.get("location", {}).get("path", "")).name
        if rel and (ext_dir / rel).is_dir() and not gone.get(rel):
            return True
    return False


def _register(ext_dir, folder, version):
    registry = ext_dir / "extensions.json"
    try:
        entries = json.loads(registry.read_text())
    except (OSError, json.JSONDecodeError):
        entries = []
    entries = [e for e in entries if e.get("identifier", {}).get("id") != EXT_ID]
    entries.append({
        "identifier": {"id": EXT_ID},
        "version": version,
        "location": {"$mid": 1, "fsPath": str(folder), "external": folder.as_uri(),
                     "path": str(folder), "scheme": "file"},
        "relativeLocation": folder.name,
    })
    util.atomic_write(registry, json.dumps(entries))
    obsolete = ext_dir / ".obsolete"
    if obsolete.is_file():
        try:
            data = json.loads(obsolete.read_text())
            data.pop(f"{EXT_ID}-{version}", None)
            if data:
                util.atomic_write(obsolete, json.dumps(data))
            else:
                obsolete.unlink()
        except (OSError, json.JSONDecodeError):
            pass


def _generated_extension(ctx, ext_dir):
    theme = ctx.file("vscode-theme.json")
    if not theme:
        return None
    data = theme.read_bytes()
    # VS Code caches colour themes until the providing extension changes version.
    version = "1.0." + str(int(hashlib.sha1(data).hexdigest()[:8], 16))
    folder = ext_dir / EXT_NAME
    (folder / "themes").mkdir(parents=True, exist_ok=True)
    ui = "vs" if ctx.mode == "light" else "vs-dark"
    util.atomic_write(folder / "themes" / "rice-color-theme.json", data)
    util.atomic_write(folder / "package.json", json.dumps({
        "name": EXT_NAME, "displayName": "Rice", "description": "Colours of the current rice theme",
        "publisher": "local", "version": version, "engines": {"vscode": "^1.70.0"},
        "categories": ["Themes"],
        "contributes": {"themes": [{"label": "Rice", "uiTheme": ui,
                                    "path": "./themes/rice-color-theme.json", "_watch": True}]},
    }, indent=2))
    _register(ext_dir, folder, version)
    return "Rice"


def _editor(ctx, cli, settings_path, ext_dir):
    if not (shutil.which(cli) or ext_dir.is_dir()):
        return  # not installed
    name = None
    descriptor = ctx.file("vscode.json")
    if descriptor:
        try:
            d = json.loads(descriptor.read_text())
        except json.JSONDecodeError:
            d = {}
        name = d.get("name") if isinstance(d.get("name"), str) and re.fullmatch(r'[^\x00-\x1f"\\]+', d.get("name", "")) else None
        ext = d.get("extension", "")
        if name and isinstance(ext, str) and re.fullmatch(r"[a-zA-Z0-9._-]+", ext) and not _installed(ext_dir, ext):
            if shutil.which(cli) and not util.SANDBOX:
                util.run([cli, "--install-extension", ext], timeout=180, check=False)
            if not _installed(ext_dir, ext):
                name = None  # couldn't get it: fall back to the generated theme
    if not name:
        ext_dir.mkdir(parents=True, exist_ok=True)
        name = _generated_extension(ctx, ext_dir)
    if not name:
        return
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    text = settings_path.read_text() if settings_path.is_file() else "{\n}\n"
    # Root keys only, comments kept; a settings file that doesn't parse is left alone.
    new = text
    if util.jsonc_get(new, "workbench.colorTheme") != name:
        new = util.jsonc_set(new, "workbench.colorTheme", name)
    if util.jsonc_get(new, "window.autoDetectColorScheme") is True:
        key = "workbench.preferredDarkColorTheme" if ctx.mode == "dark" else "workbench.preferredLightColorTheme"
        if util.jsonc_get(new, key) != name:
            new = util.jsonc_set(new, key, name)
    if new != text:
        util.atomic_write(settings_path, new)


def vscode(ctx):
    _editor(ctx, "code", ctx.paths.config / "Code" / "User" / "settings.json", ctx.paths.home / ".vscode" / "extensions")


def cursor(ctx):
    _editor(ctx, "cursor", ctx.paths.config / "Cursor" / "User" / "settings.json", ctx.paths.home / ".cursor" / "extensions")


def obsidian(ctx):
    css = ctx.file("obsidian.css")
    registry = ctx.paths.config / "obsidian" / "obsidian.json"
    if not css or not registry.is_file():
        return
    try:
        vaults = json.loads(registry.read_text()).get("vaults", {})
    except (OSError, json.JSONDecodeError):
        return
    for vault in vaults.values():
        root = Path(vault.get("path", ""))
        if not (root / ".obsidian").is_dir():
            continue
        theme = root / ".obsidian" / "themes" / "Rice"
        theme.mkdir(parents=True, exist_ok=True)
        manifest = theme / "manifest.json"
        if not manifest.exists():
            util.atomic_write(manifest, json.dumps({
                "name": "Rice", "version": "1.0.0", "minAppVersion": "0.16.0",
                "description": "Follows the current rice theme", "author": "rice"}, indent=2))
        util.install_file(css, theme / "theme.css")
