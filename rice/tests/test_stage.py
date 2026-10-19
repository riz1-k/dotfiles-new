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


if __name__ == "__main__":
    unittest.main()
