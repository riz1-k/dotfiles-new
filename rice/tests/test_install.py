"""install.sh's backup, run against a throwaway HOME, and its restore.sh."""
import os
import re
import stat
import subprocess
import unittest

import helpers

INSTALL = (helpers.ROOT / "install.sh").read_text()
BACKUP_BLOCK = INSTALL[INSTALL.index("# ---- 1. backup"):INSTALL.index("# ---- 2. the command")]


class Backup(unittest.TestCase):
    def setUp(self):
        self.root = helpers.tempdir(self)
        self.home = self.root / "home"
        self.env = helpers.sandbox_env(self.home)
        h = self.home
        dot = self.root / "dotfiles"
        (dot / ".codex").mkdir(parents=True)
        (dot / "lazygit").mkdir()
        (dot / ".codex" / "config.toml").write_text('model = "x"\n')
        (dot / "lazygit" / "config.yml").write_text("gui:\n  showIcons: true\n")
        (h / ".codex").mkdir(parents=True)
        (h / ".codex" / "config.toml").symlink_to(dot / ".codex" / "config.toml")
        (h / ".config" / "lazygit").mkdir(parents=True)
        (h / ".config" / "lazygit" / "config.yml").symlink_to(dot / "lazygit" / "config.yml")
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text('{"token": "secret"}\n')
        os.chmod(h / ".claude" / "settings.json", 0o600)
        # A Zen profile outside the profile root, as profiles.ini allows.
        elsewhere = self.root / "zen-profile"
        elsewhere.mkdir()
        (elsewhere / "user.js").write_text('user_pref("a", 1);\n')
        (h / ".zen").mkdir()
        (h / ".zen" / "profiles.ini").write_text(f"[Profile0]\nName=x\nIsRelative=0\nPath={elsewhere}\n")
        self.dot, self.elsewhere = dot, elsewhere

    def bash(self, script):
        env = dict(self.env, ROOT=str(helpers.ROOT), STATE=str(self.home / ".local/state"))
        prelude = 'set -euo pipefail\nstep() { echo "== $*"; }\ndconf() { echo "[dconf dump]"; }\n'
        r = subprocess.run(["bash", "-c", prelude + script], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def test_backup_and_restore(self):
        self.bash(BACKUP_BLOCK)
        backup = self.home / ".local/state/rice/backup"
        listing = subprocess.run(["tar", "-tzPf", str(backup / "pre-rice.tar.gz")],
                                 capture_output=True, text=True, check=True).stdout.split("\n")
        self.assertIn(str(self.dot / ".codex" / "config.toml"), listing)      # the real file
        self.assertIn(str(self.elsewhere / "user.js"), listing)              # profiles.ini's path
        self.assertIn(str(self.home / ".claude" / "settings.json"), listing)
        links = (backup / "pre-rice.links").read_text()
        self.assertIn(f"{self.home}/.config/lazygit/config.yml\t{self.dot}/lazygit/config.yml", links)

        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        for f in ("pre-rice.tar.gz", "pre-rice.links", "pre-rice.dconf"):
            self.assertEqual(stat.S_IMODE((backup / f).stat().st_mode), 0o600, f)

        # What rice does: writes through the Codex link, replaces lazygit's link with a file.
        (self.dot / ".codex" / "config.toml").write_text('model = "x"\n[tui]\ntheme = "rice"\n')
        lazygit = self.home / ".config" / "lazygit" / "config.yml"
        lazygit.unlink()
        lazygit.write_text("gui:\n  theme: {}\n")
        (self.elsewhere / "user.js").write_text("changed\n")

        out = subprocess.run([str(backup / "restore.sh")], env=self.env, capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual((self.dot / ".codex" / "config.toml").read_text(), 'model = "x"\n')
        self.assertTrue(lazygit.is_symlink())
        self.assertEqual(lazygit.read_text(), "gui:\n  showIcons: true\n")
        self.assertEqual((self.elsewhere / "user.js").read_text(), 'user_pref("a", 1);\n')

    def test_existing_backup_is_made_private(self):
        backup = self.home / ".local/state/rice/backup"
        backup.mkdir(parents=True)
        for f in ("pre-rice.tar.gz", "pre-rice.dconf"):
            (backup / f).write_text("old")
            os.chmod(backup / f, 0o664)
        os.chmod(backup, 0o775)
        self.bash(BACKUP_BLOCK)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((backup / "pre-rice.tar.gz").stat().st_mode), 0o600)
        self.assertEqual((backup / "pre-rice.tar.gz").read_text(), "old")  # never overwritten

    def test_targets_follow_the_retints(self):
        names = self.bash(f'"{helpers.ROOT}/bin/rice" _backup-targets | tr "\\0" "\\n"')
        self.assertIn(str(self.elsewhere / "user.js"), names)
        self.assertTrue(re.search(r"/\.codex/config\.toml$", names, re.M))


if __name__ == "__main__":
    unittest.main()
