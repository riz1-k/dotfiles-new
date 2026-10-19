import os
import unittest
from unittest import mock

import helpers  # noqa: F401
from rice import util


class SessionBus(unittest.TestCase):
    def test_sandbox_never_uses_the_real_bus(self):
        real = f"unix:path=/run/user/{os.getuid()}/bus"
        with mock.patch.object(util, "SANDBOX", True):
            with mock.patch.dict(os.environ, {"DBUS_SESSION_BUS_ADDRESS": real}):
                self.assertFalse(util.may_use_session_bus())
                self.assertFalse(util.session_bus_ok())
                with self.assertRaises(util.SandboxBusError):
                    util.gset("org.gnome.desktop.interface", "color-scheme", "prefer-dark")
            with mock.patch.dict(os.environ, {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/tmp/dbus-private"}):
                self.assertTrue(util.may_use_session_bus())
        with mock.patch.object(util, "SANDBOX", False):
            with mock.patch.dict(os.environ, {"DBUS_SESSION_BUS_ADDRESS": real}):
                self.assertTrue(util.may_use_session_bus())


if __name__ == "__main__":
    unittest.main()
