"""End to end: bin/rice against a throwaway HOME (see helpers.sandbox_env)."""
import json
import subprocess
import sys
import unittest

import helpers

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

    def test_list_json(self):
        rows = json.loads(self.rice("theme", "list", "--json"))
        names = {r["name"] for r in rows}
        self.assertTrue({"vesper", "flexoki-light"} <= names)

    def test_unknown_theme_fails(self):
        r = subprocess.run([*RICE, "theme", "set", "no-such-theme"], env=self.env,
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
