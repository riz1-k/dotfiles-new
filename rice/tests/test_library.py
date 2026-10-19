import os
import unittest
from unittest import mock

import helpers
from rice import library, stage, themes, util


class Urls(unittest.TestCase):
    def test_install_name(self):
        self.assertEqual(themes.install_name("https://github.com/a/omarchy-tide-theme.git"), "tide")
        self.assertEqual(themes.install_name("git@github.com:a/nord-theme"), "nord")
        # Omarchy strips -theme before lowercasing, so this keeps it
        self.assertEqual(themes.install_name("git@github.com:a/Nord-Theme"), "nord-theme")
        self.assertEqual(themes.install_name("https://github.com/a/b/"), "b")
        self.assertIsNone(themes.install_name("https://github.com/a/..."))

    def test_git_url_check(self):
        for bad in ("--upload-pack=touch /tmp/x", "ext::sh -c touch% /tmp/x", "fd::3", "evil://host/x", ""):
            self.assertIsNotNone(themes.check_git_url(bad), bad)
        for good in ("https://github.com/a/b", "git@github.com:a/b.git", "ssh://git@host/a/b", "file:///tmp/x"):
            self.assertIsNone(themes.check_git_url(good), good)


class New(unittest.TestCase):
    """rice theme new --from: the new theme is yours, so it must not carry what a git
    theme couldn't do itself."""

    def setUp(self):
        self.home = helpers.tempdir(self)
        for patch in (mock.patch.dict(os.environ, helpers.sandbox_env(self.home), clear=True),
                      mock.patch.object(util, "SANDBOX", True)):
            patch.start()
            self.addCleanup(patch.stop)
        self.themes = self.home / ".config/rice/themes"

    def stranger(self):
        t = self.themes / "stranger"
        (t / ".git").mkdir(parents=True)
        (t / "backgrounds").mkdir()
        (t / "colors.toml").write_text('background = "#101010"\nforeground = "#eeeeee"\n')
        (t / "gnome.toml").write_text('accent = "teal"\nicons = "../../etc"\ncss = "#panel { opacity: 0; }"\n')
        (t / "icons.theme").write_text("Colloid-Teal-Dark\n")
        secret = self.home / "secret.png"
        secret.write_bytes(b"\x89PNG secret")
        (t / "backgrounds" / "a.png").symlink_to(secret)
        return t

    def test_from_a_git_theme(self):
        self.stranger()
        dest, _ = library.new("mine", base="stranger")
        self.assertTrue(themes.find(library.paths_mod.get(), "mine").trusted)
        gnome = (dest / "gnome.toml").read_text()
        self.assertNotIn("css", gnome)
        self.assertNotIn("..", gnome)
        self.assertIn('accent = "teal"', gnome)
        self.assertEqual((dest / "icons.theme").read_text(), "Colloid-Teal-Dark\n")
        self.assertEqual(list((dest / "backgrounds").iterdir()), [])  # the symlinked "wallpaper" isn't copied

    def test_from_an_alacritty_only_theme(self):
        t = self.themes / "old"
        t.mkdir(parents=True)
        normal = "".join(f'{n} = "#{i}0{i}0{i}0"\n' for i, n in enumerate(stage.NAMES))
        (t / "alacritty.toml").write_text('[colors.primary]\nbackground = "#121212"\nforeground = "#eeeeee"\n'
                                          "[colors.normal]\n" + normal)
        dest, _ = library.new("newer", base="old")
        self.assertIn('background = "#121212"', (dest / "colors.toml").read_text())
        self.assertEqual(themes.find(library.paths_mod.get(), "newer").palette()["background"], "#121212")


if __name__ == "__main__":
    unittest.main()
