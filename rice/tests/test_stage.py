"""Themes from git are strangers: nothing that runs code, and no symlinks, gets staged."""
import os
import unittest

import helpers
from rice import stage, themes


def make_stranger(root):
    t = root / "stranger"
    (t / ".git").mkdir(parents=True)
    (t / "backgrounds").mkdir()
    (t / "colors.toml").write_text('background = "#000000"\nforeground = "#ffffff"\n')
    (t / "backgrounds" / "a.png").write_bytes(b"\x89PNG")
    wallpaper = t / "backgrounds" / "b.jpg"
    wallpaper.write_bytes(b"\xff\xd8")
    wallpaper.chmod(0o755)  # repos made elsewhere often mark images executable
    (t / "neovim.lua").write_text('os.execute("touch /tmp/pwned")')
    (t / "hook.sh").write_text("#!/bin/sh\n")
    tool = t / "tool"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    (t / "btop.theme").symlink_to("/etc/passwd")
    (t / "backgrounds" / "c.png").symlink_to("/etc/hostname")
    (t / "ghostty.conf").write_text("background = #000000\n")
    return t


class Untrusted(unittest.TestCase):
    def test_copy_untrusted(self):
        root = helpers.tempdir(self)
        src, dst, ignored = make_stranger(root), root / "out", []
        stage.copy_untrusted(src, dst, ignored)
        kept = sorted(str(p.relative_to(dst)) for p in dst.rglob("*") if p.is_file())
        self.assertEqual(kept, ["backgrounds/a.png", "backgrounds/b.jpg", "colors.toml"])
        for name in ("neovim.lua", "hook.sh", "tool", "btop.theme", "backgrounds/c.png", "ghostty.conf"):
            self.assertIn(name, ignored)
        self.assertFalse(any(p.is_symlink() for p in dst.rglob("*")))
        self.assertFalse(os.access(dst / "backgrounds" / "b.jpg", os.X_OK))

    def test_denied(self):
        for name in ("neovim.lua", "x.sh", "x.py", "x.js", "ghostty.conf", "kitty.conf", "tmux.conf"):
            self.assertTrue(stage.denied(name), name)
        for name in ("colors.toml", "preview.png", "btop.theme", "light.mode"):
            self.assertFalse(stage.denied(name), name)

    def test_stage_git_theme_from_alacritty(self):
        root = helpers.tempdir(self)
        t = make_stranger(root)
        (t / "colors.toml").unlink()
        normal = "".join(f'{n} = "#{i}0{i}0{i}0"\n' for i, n in enumerate(stage.NAMES))
        (t / "alacritty.toml").write_text('[colors.primary]\nbackground = "#121212"\nforeground = "#eeeeee"\n'
                                          "[colors.normal]\n" + normal)
        theme = themes.Theme(name="stranger", user=t, origin="user")
        self.assertTrue(theme.git)
        ignored = stage.stage(theme, root / "next")
        self.assertIn("neovim.lua", ignored)
        self.assertIn("#121212", (root / "next" / "colors.toml").read_text())

    def test_trusted_theme_kept_whole(self):
        root = helpers.tempdir(self)
        t = root / "mine"
        t.mkdir()
        (t / "colors.toml").write_text('background = "#000000"\n')
        (t / "neovim.lua").write_text("return {}\n")
        theme = themes.Theme(name="mine", user=t, origin="user")
        self.assertTrue(theme.trusted)
        stage.stage(theme, root / "next")
        self.assertTrue((root / "next" / "neovim.lua").is_file())


class Overlay(unittest.TestCase):
    """An overlay replaces what the base staged; it never writes into the base."""

    def make_base(self, root):
        base = root / "stock" / "vesper"
        (base / "backgrounds").mkdir(parents=True)
        (base / "colors.toml").write_text('background = "#101010"\n')
        (base / "btop.theme").write_text("base btop\n")
        (base / "backgrounds" / "1.png").write_bytes(b"base")
        elsewhere = root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "kept.txt").write_text("outside\n")
        (base / "linked").symlink_to(elsewhere)
        (base / "notes").symlink_to(elsewhere / "kept.txt")
        return base, elsewhere

    def snapshot(self, *dirs):
        out = {}
        for d in dirs:
            for p in sorted(d.rglob("*")):
                if p.is_file() and not p.is_symlink():
                    out[str(p)] = p.read_bytes()
        return out

    def overlay(self, root, git):
        user = root / "user" / "vesper"
        (user / "backgrounds").mkdir(parents=True)
        if git:
            (user / ".git").mkdir()
        (user / "colors.toml").write_text('background = "#ff0000"\n')
        (user / "btop.theme").write_text("stranger btop\n")
        (user / "backgrounds" / "1.png").write_bytes(b"stranger")
        (user / "linked").mkdir()  # a folder where the base has a symlink to a folder
        (user / "linked" / "kept.txt").write_text("stranger\n")
        (user / "notes").mkdir()   # a folder where the base has a symlink to a file
        return user

    def check(self, git):
        root = helpers.tempdir(self)
        base, elsewhere = self.make_base(root)
        user = self.overlay(root, git)
        before = self.snapshot(base, elsewhere)
        theme = themes.Theme(name="vesper", base=base, user=user, origin="stock")
        self.assertEqual(theme.git, git)
        out = root / "out"
        stage.stage(theme, out)
        self.assertEqual(self.snapshot(base, elsewhere), before)
        self.assertEqual((out / "btop.theme").read_text(), "stranger btop\n")
        self.assertEqual((out / "backgrounds" / "1.png").read_bytes(), b"stranger")
        self.assertFalse((out / "linked").is_symlink())
        self.assertEqual((out / "linked" / "kept.txt").read_text(), "stranger\n")
        self.assertTrue((out / "notes").is_dir() and not (out / "notes").is_symlink())
        # And writing to the staged copies (as rendering does, by replacing) leaves the base alone.
        for p in out.rglob("*"):
            if p.is_file() and not p.is_symlink():
                tmp = p.with_name(p.name + ".new")
                tmp.write_text("changed")
                tmp.replace(p)
        self.assertEqual(self.snapshot(base, elsewhere), before)

    def test_git_overlay(self):
        self.check(git=True)

    def test_trusted_overlay(self):
        self.check(git=False)


class Classification(unittest.TestCase):
    def test_every_template_output_is_classified(self):
        """A file rice renders is either refused from git themes or plain colours."""
        outputs = {p.name[:-4] for p in (helpers.ROOT / "templates").glob("*.tpl")}
        outputs |= {"gnome-shell.css", "gnome.json", "colors.json"}
        for name in sorted(outputs):
            self.assertTrue(stage.denied(name) or name in stage.COLOUR_ONLY, f"{name} is unclassified")
            self.assertFalse(stage.denied(name) and name in stage.COLOUR_ONLY, f"{name} is both")

    def test_shell_css_is_refused(self):
        for name in ("gnome-shell.css", "rice-bar.css", "vscode.json"):
            self.assertTrue(stage.denied(name), name)


class Discovery(unittest.TestCase):
    def test_alacritty_only_theme(self):
        root = helpers.tempdir(self)
        t = root / "old-light"
        t.mkdir()
        normal = "".join(f'{n} = "#{i}0{i}0{i}0"\n' for i, n in enumerate(stage.NAMES))
        (t / "alacritty.toml").write_text('[colors.primary]\nbackground = "#f8f8f0"\nforeground = "#202020"\n'
                                          "[colors.normal]\n" + normal)
        theme = themes.Theme(name="old-light", user=t, origin="user")
        colors = theme.palette()
        self.assertEqual(colors["background"], "#f8f8f0")
        self.assertEqual(theme.mode, "light")
        (t / "light.mode").write_text("")
        self.assertEqual(theme.mode, "light")

    def test_git_theme_symlinks_are_not_read(self):
        root = helpers.tempdir(self)
        secret = root / "secret.toml"
        secret.write_text('background = "#123456"\n')
        t = root / "stranger"
        (t / ".git").mkdir(parents=True)
        (t / "colors.toml").symlink_to(secret)
        theme = themes.Theme(name="stranger", user=t, origin="user")
        self.assertEqual(theme.palette(), {})

    def test_names_with_control_characters(self):
        self.assertFalse(themes.valid("evil\nrun-shell x"))
        self.assertTrue(themes.valid("tokyo-night"))


if __name__ == "__main__":
    unittest.main()
