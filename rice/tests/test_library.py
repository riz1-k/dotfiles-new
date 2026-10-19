import unittest

import helpers  # noqa: F401
from rice import themes


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


if __name__ == "__main__":
    unittest.main()
