"""The config edits the retints make: other people's settings files survive them."""
import json
import tomllib
import unittest
from pathlib import Path

import helpers
from rice import paths as paths_mod
from rice import util
from rice.apps import Context, agents, editors, tuis, web

THEME_LAZYGIT = """# Sample (rice template)
gui:
  theme:
    activeBorderColor:
      - '#ff0000'
      - bold
    inactiveBorderColor:
      - '#00ff00'
"""


def context(home, theme_dir, mode="dark"):
    p = paths_mod.Paths(home=home, config=home / ".config", data=home / ".local/share",
                        state=home / ".local/state", cache=home / ".cache", runtime=home / "run")
    return Context(paths=p, settings={}, name="sample", display="Sample", colors={"mode": mode},
                   mode=mode, dir=theme_dir, generation="1-1")


class Codex(unittest.TestCase):
    def ok(self, text):
        out = agents.codex_set_theme(text, "rice")
        self.assertEqual(tomllib.loads(out)["tui"]["theme"], "rice", out)
        return out

    def test_commented_header(self):
        out = self.ok('[tui] # terminal settings\nanimations = false\n\n[mcp]\nx = 1\n')
        self.assertEqual(out.count("[tui]"), 1)
        self.assertEqual(tomllib.loads(out)["mcp"], {"x": 1})
        self.assertFalse(tomllib.loads(out)["tui"]["animations"])

    def test_existing_theme_line_and_other_tables(self):
        out = self.ok('[tui]\n  theme = "old"\n[other]\ntheme = "keep"\n')
        self.assertEqual(tomllib.loads(out)["other"]["theme"], "keep")

    def test_missing_and_subtables(self):
        self.ok("")
        self.ok('model = "x"\n')
        self.ok('model = "x"\n[tui.notifications]\na = 1\n')

    def test_refused_rather_than_broken(self):
        for text in ('tui.theme = "x"\n', 'tui = { theme = "x" }\n', "[tui\n", "a = \n"):
            with self.assertRaises(util.ConfigEditError, msg=text):
                agents.codex_set_theme(text, "rice")

    def test_unchanged_is_untouched(self):
        text = '[tui]\ntheme = "rice" # mine\n'
        self.assertIs(agents.codex_set_theme(text, "rice"), text)


class Claude(unittest.TestCase):
    def setUp(self):
        self.home = helpers.tempdir(self)
        self.theme = self.home / "theme"
        self.theme.mkdir()
        (self.theme / "claude.json").write_text('{"name": "rice"}\n')

    def test_empty_settings_stay_valid(self):
        d = self.home / ".claude"
        d.mkdir()
        (d / "settings.json").write_text("{}")
        agents.claude(context(self.home, self.theme))
        self.assertEqual(json.loads((d / "settings.json").read_text()), {"theme": "custom:rice"})

    def test_one_broken_account_is_left_alone_and_reported(self):
        good, bad = self.home / ".claude", self.home / ".claude-work"
        for d in (good, bad):
            d.mkdir()
        (good / "settings.json").write_text('{"model": "opus"}\n')
        (bad / "settings.json").write_text('{"model": "opus",}\n')
        with self.assertRaises(RuntimeError):
            agents.claude(context(self.home, self.theme))
        self.assertEqual(json.loads((good / "settings.json").read_text())["theme"], "custom:rice")
        self.assertEqual((bad / "settings.json").read_text(), '{"model": "opus",}\n')


class VsCode(unittest.TestCase):
    def test_jsonc_settings(self):
        home = helpers.tempdir(self)
        theme = home / "theme"
        theme.mkdir()
        (theme / "vscode-theme.json").write_text('{"colors": {}}')
        settings = home / ".config/Code/User/settings.json"
        settings.parent.mkdir(parents=True)
        text = ('{\n  // "workbench.colorTheme": "Commented",\n  "window.autoDetectColorScheme": true,\n'
                '  "[python]": {"workbench.colorTheme": "Nested"},\n  "workbench.colorTheme": "Default Dark+",\n}\n')
        settings.write_text(text)
        (home / ".vscode/extensions").mkdir(parents=True)
        editors.vscode(context(home, theme))
        out = settings.read_text()
        self.assertEqual(util.jsonc_get(out, "workbench.colorTheme"), "Rice")
        self.assertEqual(util.jsonc_get(out, "workbench.preferredDarkColorTheme"), "Rice")
        self.assertIn('"Commented"', out)
        self.assertIn('"Nested"', out)


class Lazygit(unittest.TestCase):
    def test_everything_else_is_kept(self):
        text = ("# my config\ngui:\n    nerdFontsVersion: '3'\n    theme:\n        activeBorderColor:\n"
                "            - '#000000'\n        # old note\n    showIcons: true\ngit:\n  paging:\n"
                "    pager: delta\ncustomCommands:\n  - key: 'C'\n    command: 'git cz'\n")
        out = tuis.lazygit_set_theme(text, THEME_LAZYGIT)
        self.assertIn("# my config", out)
        self.assertIn("    showIcons: true", out)
        self.assertIn("    command: 'git cz'", out)
        self.assertIn("pager: delta", out)
        self.assertNotIn("#000000", out)
        self.assertNotIn("old note", out)
        self.assertEqual(out.count("theme:"), 1)
        self.assertEqual(tuis.lazygit_set_theme(out, THEME_LAZYGIT), out)
        try:
            import yaml
        except ImportError:
            return
        d = yaml.safe_load(out)
        self.assertEqual(d["gui"]["theme"]["activeBorderColor"], ["#ff0000", "bold"])
        self.assertEqual(d["gui"]["nerdFontsVersion"], "3")
        self.assertEqual(d["customCommands"][0]["command"], "git cz")

    def test_old_generated_file_and_missing_gui(self):
        old = tuis.OLD_HEADER + "gui:\n  nerdFontsVersion: '3'\n  theme:\n    x:\n      - '#000'\n"
        out = tuis.lazygit_set_theme(old, THEME_LAZYGIT)
        self.assertNotIn("GENERATED", out)
        self.assertIn("nerdFontsVersion", out)
        out = tuis.lazygit_set_theme("git:\n  autoFetch: false\n", THEME_LAZYGIT)
        self.assertTrue(out.startswith("git:\n  autoFetch: false\n"))
        self.assertIn("gui:\n  theme:\n    activeBorderColor:", out)

    def test_inline_gui_is_refused(self):
        with self.assertRaises(util.ConfigEditError):
            tuis.lazygit_set_theme("gui: {showIcons: true}\n", THEME_LAZYGIT)

    def test_quoted_keys(self):
        for text in ('"gui":\n  showIcons: true\ngit:\n  autoFetch: false\n',
                     "'gui':  # ui\n  showIcons: true\n",
                     'gui:\n  "theme":\n    x: ["#000"]\n  showIcons: true\n'):
            out = tuis.lazygit_set_theme(text, THEME_LAZYGIT)
            tuis._yaml_check(text, out)
            self.assertEqual(sum(1 for ln in out.splitlines() if "gui" in ln and ":" in ln and not ln[0].isspace()), 1)
            self.assertNotIn("#000", out)
            self.assertIn("showIcons: true", out)

    def test_what_it_cant_be_sure_of_is_refused(self):
        for text in ("gui:\n  showIcons: true\ngui:\n  nerdFontsVersion: '3'\n",   # two gui keys
                     "gui: &g\n  showIcons: true\n",                               # an anchor
                     "gui:\n  showIcons: true\n---\ngit: {}\n",                     # two documents
                     "gui:\n  theme: {x: 1}\n",                                    # inline theme
                     "gui:\n  theme:\n    x: 1\n  theme:\n    y: 2\n",              # two themes
                     "? gui\n: {showIcons: true}\n"):                              # a complex key
            with self.assertRaises(util.ConfigEditError, msg=text):
                out = tuis.lazygit_set_theme(text, THEME_LAZYGIT)
                tuis._yaml_check(text, out)

    def test_yaml_check_catches_lost_settings(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("no PyYAML")
        old = "gui:\n  showIcons: true\ngit:\n  autoFetch: false\n"
        tuis._yaml_check(old, "gui:\n  theme:\n    a: 1\n  showIcons: true\ngit:\n  autoFetch: false\n")
        with self.assertRaises(util.ConfigEditError):
            tuis._yaml_check(old, "gui:\n  theme:\n    a: 1\n  showIcons: true\n")
        with self.assertRaises(util.ConfigEditError):
            tuis._yaml_check(old, old + "gui:\n  theme: {}\n")  # a duplicate key

    def test_retint_preserves_the_file(self):
        home = helpers.tempdir(self)
        theme = home / "theme"
        theme.mkdir()
        (theme / "lazygit.yml").write_text(THEME_LAZYGIT)
        cfg = home / ".config/lazygit/config.yml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("git:\n  autoFetch: false\nkeybinding:\n  universal:\n    quit: 'Q'\n")
        tuis.lazygit(context(home, theme))
        out = cfg.read_text()
        self.assertIn("quit: 'Q'", out)
        self.assertIn("#ff0000", out)


class Yazi(unittest.TestCase):
    def test_leading_comment_keeps_the_rest(self):
        text = '# my yazi theme\n[mgr]\ncwd = { fg = "red" }\n'
        out = tuis.yazi_set_flavor(text)
        self.assertEqual(tomllib.loads(out)["mgr"], {"cwd": {"fg": "red"}})
        self.assertIn("# my yazi theme", out)
        self.assertEqual(tomllib.loads(out)["flavor"], {"dark": "rice", "light": "rice"})

    def test_old_flavor_replaced(self):
        out = tuis.yazi_set_flavor('[flavor] # theme-sync\ndark = "x"\nlight = "y"\n\n[status]\nsep = 1\n')
        self.assertEqual(tomllib.loads(out)["status"], {"sep": 1})
        self.assertEqual(tomllib.loads(out)["flavor"]["light"], "rice")
        self.assertEqual(tuis.yazi_set_flavor(out), out)

    def test_root_keys_stay_at_the_root(self):
        out = tuis.yazi_set_flavor("# top\nkey = 1\n[mgr]\nx = 2\n")
        self.assertEqual(tomllib.loads(out)["key"], 1)
        self.assertNotIn("key", tomllib.loads(out)["flavor"])

    def test_refused_rather_than_broken(self):
        for text in ('flavor.dark = "x"\n', "[mgr\n"):
            with self.assertRaises(util.ConfigEditError, msg=text):
                tuis.yazi_set_flavor(text)


class Zen(unittest.TestCase):
    PREF = 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'

    def test_false_becomes_true(self):
        out = web.zen_enable_stylesheets('user_pref("a", 1);\n'
                                         'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);\n')
        self.assertIn(self.PREF, out)
        self.assertNotIn("false", out)
        self.assertIn('user_pref("a", 1);', out)

    def test_a_comment_doesnt_count(self):
        text = '// user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);\n'
        out = web.zen_enable_stylesheets(text)
        self.assertTrue(out.startswith(text))
        self.assertTrue(out.rstrip().endswith(self.PREF))

    def test_block_comments_dont_count(self):
        text = '/*\nuser_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);\n*/\n'
        out = web.zen_enable_stylesheets(text)
        self.assertTrue(out.startswith(text))
        self.assertTrue(out.rstrip().endswith(self.PREF))
        text = 'user_pref("x", "/* not a comment");\nuser_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);\n'
        self.assertEqual(web.zen_enable_stylesheets(text), text.replace("false", "true"))

    def test_already_on(self):
        text = "  user_pref('toolkit.legacyUserProfileCustomizations.stylesheets' , true );\n"
        self.assertEqual(web.zen_enable_stylesheets(text), text)
        self.assertEqual(web.zen_enable_stylesheets(""), self.PREF + "\n")


if __name__ == "__main__":
    unittest.main()
