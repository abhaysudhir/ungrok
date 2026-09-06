"""Friendly failures before Python can parse the application."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_missing_python_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["/bin/sh", str(ROOT / "ungrok"), "start"],
                env={**os.environ, "PATH": directory}, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python 3.10", result.stderr)
        self.assertIn("Nothing changed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_old_python_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "python3"
            executable.write_text("#!/bin/sh\nexit 1\n")
            executable.chmod(0o700)
            result = subprocess.run(
                ["/bin/sh", str(ROOT / "ungrok"), "start"],
                env={**os.environ, "PATH": directory}, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python 3.10", result.stderr)
        self.assertIn("Nothing changed", result.stderr)

    def test_supported_python_launches_help(self):
        result = subprocess.run([str(ROOT / "ungrok"), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
