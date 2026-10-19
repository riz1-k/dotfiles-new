import json
import os
import unittest
from unittest import mock

import helpers  # noqa: F401
from rice import util


class SessionBus(unittest.TestCase):
    """In the sandbox the guard fails closed: only a bus the test names in
    RICE_SANDBOX_BUS, and never one that is really the desktop's."""

    def allowed(self, addr, named=None, sandbox=True):
        env = {"DBUS_SESSION_BUS_ADDRESS": addr, "RICE_SANDBOX_BUS": addr if named is None else named}
        with mock.patch.object(util, "SANDBOX", sandbox), mock.patch.dict(os.environ, env):
            return util.may_use_session_bus()

    def test_the_real_bus_in_any_spelling(self):
        uid = os.getuid()
        for addr in (f"unix:path=/run/user/{uid}/bus",
                     f"unix:path=/run/user/{uid}/bus,guid=0123456789abcdef0123456789abcdef",
                     f"unix:path=/run/user/{uid}//bus",
                     f"unix:path=/run/user/{uid}/%62us",
                     f"unix:path=/run/user/{uid}/../{uid}/bus",
                     "unix:runtime=yes",
                     "tcp:host=localhost,port=1234",
                     f"unix:path=/tmp/dbus-private;unix:path=/run/user/{uid}/bus"):
            self.assertFalse(self.allowed(addr), addr)

    def test_a_private_bus_only_when_named(self):
        private = "unix:path=/tmp/dbus-XXXXprivate,guid=0123"
        self.assertTrue(self.allowed(private))
        self.assertTrue(self.allowed("unix:abstract=/tmp/dbus-abc,guid=1"))
        self.assertFalse(self.allowed(private, named=""))
        self.assertFalse(self.allowed(private, named="unix:path=/tmp/other"))
        self.assertFalse(self.allowed(""))

    def test_no_sandbox_no_guard(self):
        self.assertTrue(self.allowed(f"unix:path=/run/user/{os.getuid()}/bus", named="", sandbox=False))

    def test_writes_are_refused(self):
        env = {"DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{os.getuid()}/bus,guid=1"}
        with mock.patch.object(util, "SANDBOX", True), mock.patch.dict(os.environ, env):
            os.environ.pop("RICE_SANDBOX_BUS", None)
            self.assertFalse(util.session_bus_ok())
            with mock.patch.object(util, "run") as run:
                with self.assertRaises(util.SandboxBusError):
                    util.gset("org.gnome.desktop.interface", "color-scheme", "prefer-dark")
                with self.assertRaises(util.SandboxBusError):
                    util.dset("/org/gnome/shell/extensions/x/y", "'z'")
                run.assert_not_called()


class StrictJson(unittest.TestCase):
    def test_empty_object(self):
        out = util.json_set("{}", "theme", "custom:rice")
        self.assertEqual(json.loads(out), {"theme": "custom:rice"})

    def test_order_kept_and_unchanged_is_untouched(self):
        text = '{\n  "model": "opus",\n  "theme": "dark",\n  "env": {"theme": "x"}\n}\n'
        out = util.json_set(text, "theme", "custom:rice")
        self.assertEqual(list(json.loads(out)), ["model", "theme", "env"])
        self.assertEqual(json.loads(out)["env"], {"theme": "x"})
        self.assertIs(util.json_set(out, "theme", "custom:rice"), out)

    def test_invalid_is_refused(self):
        for bad in ('{"a": 1,}', "// c\n{}", "[]", "{"):
            with self.assertRaises(util.ConfigEditError, msg=bad):
                util.json_set(bad, "theme", "custom:rice")


class Jsonc(unittest.TestCase):
    KEY = "workbench.colorTheme"

    def check(self, text, expect_kept=()):
        out = util.jsonc_set(text, self.KEY, "Rice")
        self.assertEqual(util.jsonc_get(out, self.KEY), "Rice", out)
        for piece in expect_kept:
            self.assertIn(piece, out)
        return out

    def test_empty_objects(self):
        for text in ("{}", "{\n}\n", "", "{ // nothing yet\n}\n"):
            self.check(text)

    def test_comments_strings_and_nesting_are_not_the_key(self):
        text = ('{\n  // "workbench.colorTheme": "Commented",\n'
                '  /* "workbench.colorTheme": "Block" */\n'
                '  "x": {"workbench.colorTheme": "Nested"},\n'
                '  "s": "\\"workbench.colorTheme\\": \\"InString\\" // no",\n'
                '  "workbench.colorTheme": "Old",\n}\n')
        out = self.check(text, ['"Commented"', '"Block"', '"Nested"', 'InString'])
        self.assertNotIn('"Old"', out)
        self.assertEqual(out.count('"Rice"'), 1)

    def test_added_key_keeps_trailing_commas_valid(self):
        out = self.check('{\n  "a": [1, 2, {"b": "}"}],\n  "c": true,\n}\n', ['"a": [1, 2, {"b": "}"}]'])
        self.assertEqual(util.jsonc_get(out, "c"), True)

    def test_the_last_duplicate_is_the_one_changed(self):
        out = self.check('{"workbench.colorTheme": "A", "workbench.colorTheme": "B"}')
        self.assertIn('"A"', out)

    def test_invalid_is_refused(self):
        for bad in ("[1]", '{"a": 1} x', '{"a" 1}', '{"a": 1', '{"a": /* open', '{"a": "open}'):
            with self.assertRaises(util.ConfigEditError, msg=bad):
                util.jsonc_set(bad, self.KEY, "Rice")
        self.assertIsNone(util.jsonc_get('{"a" 1}', "a"))


if __name__ == "__main__":
    unittest.main()
