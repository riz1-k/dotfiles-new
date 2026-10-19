"""End to end: bin/rice against a throwaway HOME (see helpers.sandbox_env), and the
switch's locking and generations in-process with every retint faked."""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import helpers
from rice import activate, apps, themes, util
from rice import paths as paths_mod
from rice import settings as settings_mod

RICE = [sys.executable, str(helpers.ROOT / "bin" / "rice")]


class Switch(unittest.TestCase):
    def setUp(self):
        self.home = helpers.tempdir(self)
        self.env = helpers.sandbox_env(self.home)
        (self.home / ".config/btop").mkdir(parents=True)
        (self.home / ".config/btop/btop.conf").write_text('color_theme = "Default"\n')
        self.state = self.home / ".local/state/rice/current"

    def rice(self, *args):
        r = subprocess.run([*RICE, *args], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_set_and_toggle(self):
        self.rice("theme", "set", "vesper", "--wait")
        self.assertEqual((self.state / "theme.name").read_text().strip(), "vesper")
        self.assertTrue((self.state / "theme.generation").read_text().strip())
        theme = self.state / "theme"
        for f in ("gnome.json", "colors.json", "gnome-shell.css", "gtk4.css", "tmux.conf", "widgets.css"):
            self.assertTrue((theme / f).is_file(), f)
        g = json.loads((theme / "gnome.json").read_text())
        self.assertEqual(g["color_scheme"], "prefer-dark")
        self.assertIn("rice additions", (theme / "gnome-shell.css").read_text())
        gtk4 = (theme / "gtk4.css").read_text()
        self.assertIn("prefers-color-scheme: dark", gtk4)
        self.assertIn("prefers-color-scheme: light", gtk4)
        self.assertIn('color_theme = "rice"', (self.home / ".config/btop/btop.conf").read_text())

        self.rice("theme", "set", "flexoki-light", "--wait")
        self.assertEqual(json.loads((theme / "gnome.json").read_text())["color_scheme"], "prefer-light")
        self.rice("mode", "toggle")
        self.assertEqual((self.state / "theme.name").read_text().strip(), "vesper")

    def test_generations(self):
        for name in ("vesper", "flexoki-light", "vesper", "flexoki-light", "vesper"):
            self.rice("theme", "set", name, "--wait")
        link = self.state / "theme"
        self.assertTrue(link.is_symlink())
        gens = sorted(p.name for p in (self.state / "generations").iterdir())
        self.assertLessEqual(len(gens), activate.KEEP_GENERATIONS)
        self.assertEqual(link.resolve().parent, (self.state / "generations").resolve())
        self.assertEqual(link.resolve().name, (self.state / "theme.generation").read_text().strip())
        self.assertEqual(gens[-1], link.resolve().name)
        self.assertEqual(json.loads((link / "gnome.json").read_text())["name"], "vesper")

    def test_migrates_a_theme_folder(self):
        """Installs from before generations have a real current/theme folder."""
        old = self.state / "theme"
        old.mkdir(parents=True)
        (old / "colors.json").write_text("{}")
        (self.state / "next-theme").mkdir()
        self.rice("theme", "set", "vesper", "--wait")
        self.assertTrue(old.is_symlink())
        self.assertTrue((old / "gnome.json").is_file())
        self.assertFalse((self.state / "next-theme").exists())
        legacy = list((self.state / "generations").glob("0-legacy-*"))
        self.assertEqual(len(legacy), 1)
        self.assertTrue((legacy[0] / "colors.json").is_file())
        # Again, as an older rice still running would leave it.
        os.replace(old, self.state / ".tmp-link")
        os.unlink(self.state / ".tmp-link")
        old.mkdir()
        self.rice("theme", "set", "flexoki-light", "--wait")
        self.assertTrue(old.is_symlink())

    def test_list_json(self):
        rows = json.loads(self.rice("theme", "list", "--json"))
        names = {r["name"] for r in rows}
        self.assertTrue({"vesper", "flexoki-light"} <= names)

    def test_unknown_theme_fails(self):
        r = subprocess.run([*RICE, "theme", "set", "no-such-theme"], env=self.env,
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0)


class InProcess(unittest.TestCase):
    """set_theme itself, with the retints replaced by recorders (nothing outside the
    throwaway HOME is touched: RICE_SANDBOX, no bus, fake apps)."""

    def setUp(self):
        self.home = helpers.tempdir(self)
        for patch in (mock.patch.dict(os.environ, helpers.sandbox_env(self.home), clear=True),
                      mock.patch.object(util, "SANDBOX", True),
                      mock.patch.object(activate, "warm_previews", lambda paths: None),
                      mock.patch.object(apps, "OTHER", [("fake-other", "gtk", self.record_other)]),
                      mock.patch.object(apps, "VISIBLE", [("fake-btop", "btop", self.record_visible)])):
            patch.start()
            self.addCleanup(patch.stop)
        self.paths = paths_mod.get()
        self.visible, self.other = [], []
        self.slow = None          # theme whose first visible retint waits
        self.entered = threading.Event()

    def record_visible(self, ctx):
        if ctx.name == self.slow and not self.entered.is_set():
            self.entered.set()
            time.sleep(0.6)
        self.visible.append(ctx.name)

    def record_other(self, ctx):
        self.other.append((ctx.name, ctx.colors["background"], json.loads((ctx.dir / "gnome.json").read_text())["name"]))

    def test_concurrent_switches_end_on_the_last(self):
        """B, started while A's visible retints are still running, waits for them, so
        A can't finish after B and leave its colours on screen."""
        self.slow = "vesper"
        a = threading.Thread(target=activate.set_theme, args=("vesper",), kwargs={"wait": True})
        a.start()
        self.assertTrue(self.entered.wait(5))
        activate.set_theme("flexoki-light", wait=True)
        a.join(10)
        self.assertEqual(self.visible, ["vesper", "flexoki-light"])
        self.assertEqual(themes.current_name(self.paths), "flexoki-light")
        self.assertEqual(self.other[-1][0], "flexoki-light")
        backgrounds = {n: themes.find(self.paths, n).palette()["background"] for n in ("vesper", "flexoki-light")}
        for name, bg, staged in self.other:  # each batch read its own generation, whole
            self.assertEqual((bg, staged), (backgrounds[name], name))

    def test_a_replaced_batch_stops(self):
        with mock.patch.object(subprocess, "Popen"):
            activate.set_theme("vesper", wait=False)
            old = activate.current_generation(self.paths)
            activate.set_theme("flexoki-light", wait=False)
        self.assertEqual(activate.other_group(self.paths, old, detached=False), [])
        self.assertEqual(self.other, [])
        ctx = activate.context(self.paths, settings_mod.load(self.paths), old)
        self.assertEqual(ctx.name, "vesper")  # its own files, not the current theme's
        self.assertEqual(ctx.dir, self.paths.generations / old)

    def test_lock_never_follows_a_symlink(self):
        run = activate.private_dir(self.paths.runtime)
        victim = self.home / "victim"
        victim.write_text("precious\n")
        lock = run / "rice-theme-set.lock"
        lock.symlink_to(victim)
        with self.assertRaises(OSError):
            with activate.locked(lock):
                pass
        self.assertEqual(victim.read_text(), "precious\n")

    def test_private_runtime_dir(self):
        d = self.home / "shared"
        d.mkdir(mode=0o777)
        os.chmod(d, 0o777)
        activate.private_dir(d)
        self.assertEqual(d.stat().st_mode & 0o777, 0o700)
        f = self.home / "file"
        f.write_text("")
        with self.assertRaises((activate.ThemeError, OSError)):
            activate.private_dir(f)
        link = self.home / "link"
        link.symlink_to(d)
        with self.assertRaises(activate.ThemeError):
            activate.private_dir(link)

    def test_background_only_touches_the_active_generation(self):
        with mock.patch.object(subprocess, "Popen"):
            activate.set_theme("vesper", wait=False)
            first = activate.current_generation(self.paths)
            activate.set_theme("flexoki-light", wait=False)
        before = (self.paths.generations / first / "gnome.json").read_text()
        image = self.home / "wall.png"
        image.write_bytes(b"\x89PNG")
        activate.set_background(image)
        g = json.loads((self.paths.current_theme / "gnome.json").read_text())
        self.assertEqual((g["name"], g["background"]), ("flexoki-light", str(image.resolve())))
        self.assertEqual((self.paths.generations / first / "gnome.json").read_text(), before)
        self.assertEqual(self.paths.background_link.resolve(), image.resolve())
        self.assertEqual([p.name for p in self.paths.current.glob(".background*")], [])

    def test_a_failed_publish_puts_everything_back(self):
        with mock.patch.object(subprocess, "Popen"):
            activate.set_theme("vesper", wait=False)
        before = {"gen": activate.current_generation(self.paths), "name": themes.current_name(self.paths),
                  "marker": self.paths.generation.read_text(), "link": os.readlink(self.paths.current_theme)}
        real = util.atomic_write

        def failing(path, *a, **kw):
            if Path(path) == self.paths.generation:
                raise OSError(28, "No space left on device")
            return real(path, *a, **kw)

        with mock.patch.object(util, "atomic_write", failing), mock.patch.object(subprocess, "Popen"):
            with self.assertRaises(OSError):
                activate.set_theme("flexoki-light", wait=False)
        after = {"gen": activate.current_generation(self.paths), "name": themes.current_name(self.paths),
                 "marker": self.paths.generation.read_text(), "link": os.readlink(self.paths.current_theme)}
        self.assertEqual(after, before)
        self.assertEqual(sorted(p.name for p in self.paths.generations.iterdir()), [before["gen"]])
        self.assertFalse(self.paths.mode_watch_flag.exists())

    def test_the_mode_watch_flag_is_up_before_the_theme_is(self):
        seen = []
        real = activate.activate_generation

        def watching(paths, generation):
            seen.append(paths.mode_watch_flag.exists())
            return real(paths, generation)

        with mock.patch.object(activate, "activate_generation", watching), mock.patch.object(subprocess, "Popen"):
            activate.set_theme("vesper", wait=False)
        self.assertEqual(seen, [True])
        self.assertFalse(self.paths.mode_watch_flag.exists())

    def test_mode_watch_checks_again_under_the_lock(self):
        """It read a dark scheme against a light theme, but by the time it holds the
        lock the switch that caused it has settled things: nothing happens."""
        from rice import modewatch
        with mock.patch.object(subprocess, "Popen"):
            activate.set_theme("flexoki-light", wait=False)
        scheme = ["dark"]
        real_set = activate.set_theme

        def settling(name, **kw):
            scheme[0] = "light"  # the running switch finished and wrote the scheme
            return real_set(name, **kw)

        with mock.patch.object(modewatch, "scheme_mode", lambda: scheme[0]), \
                mock.patch.object(activate, "set_theme", settling), mock.patch.object(subprocess, "Popen"):
            self.assertEqual(modewatch.reconcile(self.paths, verbose=False), "vesper")
        self.assertEqual(themes.current_name(self.paths), "flexoki-light")
        scheme[0] = "dark"  # a real Dark Style flip still switches
        with mock.patch.object(modewatch, "scheme_mode", lambda: scheme[0]), mock.patch.object(subprocess, "Popen"):
            modewatch.reconcile(self.paths, verbose=False)
        self.assertEqual(themes.current_name(self.paths), "vesper")

    def test_a_pinned_generation_survives_pruning(self):
        with mock.patch.object(subprocess, "Popen"):
            activate.set_theme("vesper", wait=False)
            old = activate.current_generation(self.paths)
            with activate.pinned(self.paths, old) as present:
                self.assertTrue(present)
                for name in ("flexoki-light", "vesper", "flexoki-light", "vesper"):
                    activate.set_theme(name, wait=False)
                self.assertTrue((self.paths.generations / old / "gnome.json").is_file())
            activate.set_theme("flexoki-light", wait=False)
        self.assertFalse((self.paths.generations / old).exists())
        self.assertLessEqual(len(list(self.paths.generations.iterdir())), activate.KEEP_GENERATIONS)
        with activate.pinned(self.paths, old) as present:
            self.assertFalse(present)

    def test_migration_without_exchange_rolls_back(self):
        old = self.paths.current_theme
        old.mkdir(parents=True)
        (old / "colors.json").write_text("{}")
        self.paths.generations.mkdir(parents=True)
        real_replace = os.replace

        def failing_replace(a, b, *args, **kw):
            if Path(b) == self.paths.current_theme:
                raise OSError(5, "I/O error")
            return real_replace(a, b, *args, **kw)

        with mock.patch.object(activate, "_exchange", lambda a, b: False), \
                mock.patch.object(os, "replace", failing_replace):
            with self.assertRaises(OSError):
                activate.activate_generation(self.paths, "123-1")
        self.assertTrue(old.is_dir() and not old.is_symlink())
        self.assertTrue((old / "colors.json").is_file())

    def test_migration_with_exchange(self):
        old = self.paths.current_theme
        old.mkdir(parents=True)
        (old / "colors.json").write_text("{}")
        (self.paths.generations / "123-1").mkdir(parents=True)
        previous = activate.activate_generation(self.paths, "123-1")
        self.assertTrue(old.is_symlink())
        self.assertTrue(previous.startswith("0-legacy-"))
        self.assertTrue((self.paths.generations / previous / "colors.json").is_file())

    def stranger(self, git):
        t = self.paths.user_themes / "stranger"
        t.mkdir(parents=True)
        if git:
            (t / ".git").mkdir()
        (t / "colors.toml").write_text('background = "#101010"\nforeground = "#eeeeee"\naccent = "#ff8800"\n')
        (t / "rice-bar.css").write_text("#panel { opacity: 0; } /* STRANGER-BAR */\n")
        (t / "gnome.toml").write_text('icons = "../../../etc"\ncss = "/* STRANGER-TOML */"\n')
        (t / "icons.theme").write_text("../evil\n")
        return themes.find(self.paths, "stranger")

    def build(self, theme):
        out = self.paths.generations / "test"
        activate.build(self.paths, settings_mod.load(self.paths), theme, "", out)
        return (out / "gnome-shell.css").read_text(), json.loads((out / "gnome.json").read_text())

    def test_git_theme_cannot_add_shell_css(self):
        css, g = self.build(self.stranger(git=True))
        self.assertNotIn("STRANGER", css)
        self.assertIn("rice-shell colours", css)  # the bar's CSS, from rice's template
        self.assertNotIn("..", g["icon_theme"])

    def test_own_theme_can(self):
        css, _ = self.build(self.stranger(git=False))
        self.assertIn("STRANGER-BAR", css)
        self.assertIn("STRANGER-TOML", css)


if __name__ == "__main__":
    unittest.main()
