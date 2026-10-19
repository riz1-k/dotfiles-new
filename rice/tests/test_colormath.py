import unittest

import helpers  # noqa: F401
from rice import colormath as cm


class ColorMath(unittest.TestCase):
    def test_hex(self):
        self.assertTrue(cm.is_hex("#a0B1c2"))
        self.assertFalse(cm.is_hex("a0b1c2"))
        self.assertFalse(cm.is_hex("rgba(0, 0, 0, 0.3)"))
        self.assertEqual(cm.to_rgb("#ff8000"), (255, 128, 0))
        self.assertEqual(cm.strip("#ff8000"), "ff8000")
        self.assertEqual(cm.rgb_string("#ff8000"), "255,128,0")  # Omarchy's format

    def test_mix_ends(self):
        self.assertEqual(cm.mix("#102030", "#f0e0d0", "0%").lower(), "#102030")
        self.assertEqual(cm.mix("#102030", "#f0e0d0", "100%").lower(), "#f0e0d0")
        self.assertEqual(cm.mix("#000000", "#ffffff", "50%"), cm.mix("#000000", "#ffffff", "0.5"))

    def test_contrast(self):
        self.assertAlmostEqual(cm.contrast("#000000", "#ffffff"), 21, places=1)
        self.assertAlmostEqual(cm.contrast("#777777", "#777777"), 1, places=3)

    def test_legible_reaches_target(self):
        for color, bg in (("#3a3d4a", "#1b1d22"), ("#e0e0d0", "#fffcf0"), ("#ffc799", "#f2f0e5")):
            out = cm.legible(color, bg, 3.2)
            self.assertGreaterEqual(cm.contrast(out, bg), 3.2 - 0.05, (color, bg, out))

    def test_readable_on(self):
        self.assertEqual(cm.readable_on("#101010", "#ffffff", "#000000"), "#ffffff")
        self.assertEqual(cm.readable_on("#fafafa", "#ffffff", "#000000"), "#000000")


if __name__ == "__main__":
    unittest.main()
