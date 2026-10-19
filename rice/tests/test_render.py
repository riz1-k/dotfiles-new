import unittest

import helpers
from rice import render


COLORS = {"background": "#102030", "foreground": "#f0e0d0", "name": "x"}


class Tokens(unittest.TestCase):
    def setUp(self):
        self.r = render.Renderer(COLORS)

    def test_values(self):
        self.assertEqual(self.r.text("bg={{ background }}"), "bg=#102030")
        self.assertEqual(self.r.text("{{ background_strip }}"), "102030")
        self.assertEqual(self.r.text("{{ background_rgb }}"), "16,32,48")

    def test_mix(self):
        self.assertEqual(self.r.text("{{ mix background foreground 0% }}").lower(), "#102030")
        self.assertEqual(self.r.text("{{ mix_strip background foreground 100% }}").lower(), "f0e0d0")

    def test_unknown_spans_stay(self):
        self.assertEqual(self.r.text("{{ nope }} {{ background }}"), "{{ nope }} #102030")
        self.assertEqual(self.r.text("{ {{ background } }"), "{ {{ background } }")

    def test_line_endings_kept(self):
        self.assertEqual(self.r.text("a {{ name }}\r\nb\n"), "a x\r\nb\n")


class RenderInto(unittest.TestCase):
    def test_user_first_and_shipped_files_kept(self):
        d = helpers.tempdir(self)
        user, stock, out = d / "user", d / "stock", d / "out"
        for p in (user, stock, out):
            p.mkdir()
        (user / "a.conf.tpl").write_text("user {{ background }}\n")
        (stock / "a.conf.tpl").write_text("stock {{ background }}\n")
        (stock / "b.conf.tpl").write_text("stock b\n")
        (out / "b.conf").write_text("shipped by the theme\n")
        written = render.render_into(out, COLORS, render.template_files(user, stock))
        self.assertEqual(written, ["a.conf"])
        self.assertEqual((out / "a.conf").read_text(), "user #102030\n")
        self.assertEqual((out / "b.conf").read_text(), "shipped by the theme\n")


if __name__ == "__main__":
    unittest.main()
