import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("release", Path(__file__).parents[1] / "scripts/build_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_clean_committed_reproducible_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "ungrok.py").write_text('VERSION = "0.1.0-rc.1"\n')
            release.git(root, "add", "ungrok.py")
            release.git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            first, sums = release.build(root, base / "one")
            second, _ = release.build(root, base / "two")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(sums.read_text(), hashlib.sha256(first.read_bytes()).hexdigest() + "  " + first.name + "\n")
            with tarfile.open(first) as archive:
                self.assertIn("ungrok-0.1.0-rc.1/ungrok.py", archive.getnames())
                self.assertFalse(any(".git/" in name for name in archive.getnames()))
            with self.assertRaisesRegex(ValueError, "already exists"):
                release.build(root, base / "one")
            (root / "private.env").write_text("test-only")
            with self.assertRaisesRegex(ValueError, "working-tree"):
                release.build(root, base / "three")
