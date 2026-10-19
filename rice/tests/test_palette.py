import re
import unittest

import helpers
from rice import colormath as cm
from rice import palette


def resolved(text, light_file=False):
    return palette.resolve(palette.parse(text), light_mode_file=light_file)


MINIMAL_DARK = 'background = "#1a1b26"\nforeground = "#a9b1d6"\naccent = "#7aa2f7"\n'
MINIMAL_LIGHT = 'background = "#f2f0f9"\nforeground = "#2c314c"\naccent = "#5e6884"\n'


class Parse(unittest.TestCase):
    def test_omarchy_quirks(self):
        text = """
# comment
[section]
accent = "#111111"
accent = '#222222'   # last one wins
background=#333333
"bad key!" = "#444444"
foreground = "#555555; rm -rf ~"
"""
        warnings = []
        c = palette.parse(text, warnings)
        self.assertEqual(c["accent"], "#222222")
        self.assertEqual(c["background"], "#333333")
        self.assertNotIn("foreground", c)
        self.assertTrue(any("unsupported" in w for w in warnings))


class Resolve(unittest.TestCase):
    def test_every_ui_key(self):
        for text in (MINIMAL_DARK, MINIMAL_LIGHT, (helpers.FIXTURES / "sample-colors.toml").read_text()):
            c = resolved(text)
            for key in palette.UI_KEYS:
                self.assertIn(key, c)
                if key != "ui_shade":
                    self.assertTrue(cm.is_hex(c[key]), (key, c[key]))

    def test_mode(self):
        self.assertEqual(resolved(MINIMAL_DARK)["mode"], "dark")
        self.assertEqual(resolved(MINIMAL_LIGHT)["mode"], "light")
        self.assertEqual(resolved(MINIMAL_DARK, light_file=True)["mode"], "light")

    def test_dim_sits_between_fg_and_bg(self):
        # Aether writes dark_fg darker than fg on light themes: it must not become ui_dim.
        light = MINIMAL_LIGHT + 'dark_fg = "#212539"\n'
        for text in (MINIMAL_DARK, light):
            c = resolved(text)
            dim, fg, bg = c["ui_dim"], c["foreground"], c["background"]
            self.assertLess(cm.contrast(dim, bg), cm.contrast(fg, bg), text)
            self.assertGreaterEqual(cm.contrast(dim, bg), 2.5, text)

    def test_inverse_capsule_is_readable(self):
        for text in (MINIMAL_DARK, MINIMAL_LIGHT):
            c = resolved(text)
            self.assertGreaterEqual(cm.contrast(c["ui_inverse_fg"], c["ui_inverse"]), 4.5)
            self.assertGreaterEqual(cm.contrast(c["ui_inverse_accent"], c["ui_inverse"]), 3.0)

    def test_pinned_ui_keys_win(self):
        c = resolved(MINIMAL_DARK + 'ui_dim = "#abcdef"\n')
        self.assertEqual(c["ui_dim"], "#abcdef")


class Injection(unittest.TestCase):
    """Palette values reach tmux formats, zsh and the shell CSS: only colours pass."""
    EVIL = ['#(touch /tmp/rice-pwned)', '#{pane_current_path}', '$(touch /tmp/rice-pwned)',
            '`touch /tmp/rice-pwned`', '#ffffff" ; touch /tmp/rice-pwned ; "', "#ffffff'",
            '#ffffff #(touch /tmp/rice-pwned)', 'rgb(1,2,3);touch', 'red', '#ffffff\\']

    def test_values_are_refused(self):
        for value in self.EVIL + ["#111111 #222222 45deg", "0.95", "light", "rgb(300, 0, 0)"]:
            self.assertIsNone(palette.colour_value("accent", value), value)
        for value in self.EVIL + ["#ffffff", "bright"]:
            self.assertIsNone(palette.colour_value("mode", value), value)

    def test_colours_are_stored_as_hex(self):
        """Every form a theme may use comes out as #rrggbb, so the colour maths and
        the templates work with it (ui_shade may keep its alpha)."""
        cases = {"#A1B2C3": "#A1B2C3", "#fff": "#ffffff", "#a1b2c3dd": "#a1b2c3",
                 "rgb(16, 16, 16)": "#101010", "rgba(255,0,0,0.5)": "#ff0000", "": ""}
        for value, stored in cases.items():
            self.assertEqual(palette.colour_value("background", value), stored, value)
        self.assertEqual(palette.colour_value("ui_shade", "rgba(0,0,0,0.36)"), "rgba(0, 0, 0, 0.36)")
        self.assertEqual(palette.colour_value("mode", "light"), "light")

    def test_rgb_palette_renders_everything(self):
        from rice import render, shellcss
        text = ('background = "rgb(16, 16, 16)"\nforeground = "rgb(238, 238, 238)"\n'
                'accent = "#f80"\ncolor8 = "rgba(80, 80, 80, 1)"\n')
        colors = palette.resolve(palette.parse(text))
        self.assertEqual((colors["background"], colors["accent"]), ("#101010", "#ff8800"))
        r = render.Renderer(colors, {"rice_theme": "x", "rice_theme_name": "X"})
        leftover = re.compile(r"\{\{\s*[a-z][a-z0-9_]*(\s+[^}]*)?\s*\}\}")
        for tpl in render.template_files(helpers.ROOT / "templates"):
            self.assertIsNone(leftover.search(r.text(tpl.read_text())), tpl.name)
        out = helpers.tempdir(self)
        self.assertIn("#101010", shellcss.build(colors, colors["mode"], out / "shell", ""))

    def test_nothing_reaches_the_templates(self):
        from rice import render
        lines = ['background = "#101010"', 'foreground = "#eeeeee"']
        keys = ["muted", "accent", "color8", "selection", "ui_dim", "red", "mode"]
        for i, value in enumerate(self.EVIL):
            lines.append(f"{keys[i % len(keys)]} = {value}")
            lines.append(f"{keys[(i + 1) % len(keys)]} = '{value}'")
        warnings = []
        colors = palette.resolve(palette.parse("\n".join(lines), warnings))
        self.assertTrue(warnings)
        r = render.Renderer(colors, {"rice_theme": "x", "rice_theme_name": "X"})
        for tpl in render.template_files(helpers.ROOT / "templates"):
            out = r.text(tpl.read_text())
            self.assertNotIn("rice-pwned", out, tpl.name)
            self.assertNotIn("pane_current_path}\"", out, tpl.name)


if __name__ == "__main__":
    unittest.main()
