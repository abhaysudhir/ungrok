"""Offline guided setup tests: never install, authenticate, or signal real processes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("wizard_cli", Path(__file__).resolve().parents[1] / "ungrok.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class WizardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.installation = mock.Mock()
        self.installation.config = self.root / "ungrok.env"
        self.installation.host = self.root / "host-main.cjs"
        self.installation.is_current.return_value = True
        self.installation.node = "/node"
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(cli.sys.stdin, "isatty", return_value=True).start()
        mock.patch.dict(cli.os.environ, {}, clear=True).start()
        self.client = mock.patch.object(cli, "wizard_client", return_value="/official/client").start()
        self.check = mock.patch.object(cli, "runtime_check").start()
        self.login = mock.patch.object(cli, "login").start()
        self.probe = mock.patch.object(cli, "probe").start()
        self.pid = mock.patch.object(cli, "discover_host_pid", return_value=42).start()
        self.run = mock.patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)).start()
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        mock.patch.object(cli.sys.stdout, "isatty", return_value=True).start()

    def run_start(self, answers):
        with mock.patch("builtins.input", side_effect=answers):
            cli.start(self.installation)

    def test_noninteractive_stops_before_preflight(self):
        with mock.patch.object(cli.sys.stdin, "isatty", return_value=False):
            with self.assertRaises(cli.Failure):
                self.run_start([])
        self.installation.preflight.assert_not_called()
        self.client.assert_not_called()

    def test_custom_auth_profile_stops_before_download(self):
        with mock.patch.dict(cli.os.environ, {"CODEX_HOME": "/custom"}):
            with self.assertRaisesRegex(cli.Failure, "custom CODEX_HOME"):
                self.run_start([])
        self.client.assert_not_called()

    def test_linux_preflight_failure_stops_before_download(self):
        self.installation.preflight.side_effect = cli.Failure("wrong platform")
        with self.assertRaises(cli.Failure):
            self.run_start([])
        self.client.assert_not_called()

    def test_existing_provider_and_model_preserved(self):
        cli.atomic_write(self.installation.config, cli.encode_config({"UNGROK_PROVIDER": "claude", "UNGROK_CLI": "/old/claude", "UNGROK_MODEL": "custom-model"}))
        self.run_start(["", "", "yes", "yes"])
        values, confirm = self.installation.install.call_args.args
        self.assertEqual(values["UNGROK_PROVIDER"], "claude")
        self.assertEqual(values["UNGROK_MODEL"], "custom-model")
        self.assertIs(confirm, cli.wizard_confirm)
        self.installation.restart.assert_called_once_with(42, cli.wizard_confirm)
        self.assertIn("NOT yet verified", self.output.getvalue())

    def test_model_reset_explicit(self):
        cli.atomic_write(self.installation.config, cli.encode_config({"UNGROK_PROVIDER": "chatgpt", "UNGROK_CLI": "/old/codex", "UNGROK_MODEL": "custom-model"}))
        self.run_start(["", "2", "y", "y"])
        self.assertNotIn("UNGROK_MODEL", self.installation.install.call_args.args[0])

    def test_bad_model_stops_before_download(self):
        with self.assertRaisesRegex(cli.Failure, "model"):
            self.run_start(["1", "3", "bad model"])
        self.client.assert_not_called()

    def test_login_requires_confirmation(self):
        self.check.side_effect = cli.Failure("not signed in")
        with self.assertRaisesRegex(cli.Failure, "Stopped"):
            self.run_start(["1", "1", "n"])
        self.login.assert_not_called()
        self.installation.install.assert_not_called()

    def test_probe_decline_never_restarts(self):
        with self.assertRaisesRegex(cli.Failure, "Earlier completed"):
            self.run_start(["1", "1", "n"])
        self.probe.assert_not_called()
        self.installation.restart.assert_not_called()

    def test_probe_failure_never_patches(self):
        self.probe.side_effect = cli.Failure("test failed")
        with self.assertRaisesRegex(cli.Failure, "has not changed the Grok host"):
            self.run_start(["1", "1", "y"])
        self.installation.install.assert_not_called()

    def test_ambiguous_process_never_patches(self):
        self.pid.side_effect = cli.Failure("ambiguous host")
        with self.assertRaisesRegex(cli.Failure, "ambiguous"):
            self.run_start(["1", "1", "y"])
        self.installation.install.assert_not_called()

    def test_restart_decline_explains_disk_state(self):
        self.installation.restart.side_effect = cli.Failure("declined")
        with self.assertRaisesRegex(cli.Failure, "new sessions may already use them"):
            self.run_start(["1", "1", "y", "y"])

    def test_restart_process_race_explains_disk_state_without_diagnostics(self):
        self.installation.restart.side_effect = OSError("PRIVATE_DIAGNOSTIC")
        with self.assertRaises(cli.Failure) as caught:
            self.run_start(["1", "1", "y", "y"])
        self.assertIn("new sessions may already use them", str(caught.exception))
        self.assertNotIn("PRIVATE_DIAGNOSTIC", str(caught.exception))

    def test_pause_decline_never_installs_or_restarts(self):
        with self.assertRaisesRegex(cli.Failure, "Stopped"):
            self.run_start(["1", "1", "y", "n"])
        self.probe.assert_called_once()
        self.installation.install.assert_not_called()
        self.installation.restart.assert_not_called()

    def test_pause_acknowledgment_precedes_install(self):
        prompts = []

        def answer(prompt):
            prompts.append(prompt)
            if "Choose" in prompt:
                return "1"
            self.installation.install.assert_not_called()
            return "yes"

        def install(values, confirm):
            self.assertIn("Are all bots idle and routines paused?", prompts[-1])
            self.assertIn("immediately, before restart", prompts[-1])

        self.installation.install.side_effect = install
        with mock.patch("builtins.input", side_effect=answer):
            cli.start(self.installation)
        self.installation.install.assert_called_once()
        self.assertIn("new sessions may already use these settings before restart", self.output.getvalue())

    def test_restart_interruption_warns_settings_may_be_active(self):
        self.installation.restart.side_effect = KeyboardInterrupt
        with self.assertRaisesRegex(cli.Failure, "new sessions may already use them"):
            self.run_start(["1", "1", "y", "y"])


class ClientTests(unittest.TestCase):
    def test_version_and_package_required(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            client = base / "cli.js"
            client.write_text("fixture")
            client.chmod(0o700)
            (base / "package.json").write_text(json.dumps({"name": "@openai/codex", "version": "0.153.4"}))
            with mock.patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"codex-cli 0.153.4\n")):
                self.assertEqual(cli.validated_client("chatgpt", client), str(client))
            with mock.patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"codex-cli 999\n")):
                self.assertIsNone(cli.validated_client("chatgpt", client))

    def test_download_decline_no_files(self):
        with mock.patch.object(cli, "validated_client", return_value=None), mock.patch.object(cli.shutil, "which", return_value="/npm"), mock.patch("builtins.input", return_value="n"), mock.patch.object(cli.tempfile, "mkdtemp") as mkdir:
            with self.assertRaises(cli.Failure):
                cli.wizard_client("claude")
            mkdir.assert_not_called()

    def test_pinned_private_download_no_scripts_and_failure_retained(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(cli.Path, "home", return_value=Path(directory).resolve()), mock.patch.object(cli, "validated_client", return_value=None), mock.patch.object(cli.shutil, "which", return_value="/npm"), mock.patch("builtins.input", return_value="y"), mock.patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
            with self.assertRaisesRegex(cli.Failure, "nothing was patched"):
                cli.wizard_client("claude")
            command = run.call_args.args[0]
            self.assertIn("@anthropic-ai/claude-code@2.1.263", command)
            self.assertIn("--ignore-scripts", command)
            prefix = Path(command[command.index("--prefix") + 1])
            self.assertTrue(prefix.is_dir())
            self.assertEqual(prefix.stat().st_mode & 0o777, 0o700)

    def test_discovery_requires_exactly_one_verified_process(self):
        for count in (0, 1, 2):
            with self.subTest(count=count), mock.patch.object(cli.Path, "iterdir", return_value=[Path(str(10 + i)) for i in range(count)]), mock.patch.object(cli, "verified_process", return_value=(2, "start")):
                if count == 1:
                    self.assertEqual(cli.discover_host_pid(Path("/host")), 10)
                else:
                    with self.assertRaisesRegex(cli.Failure, "No process was signaled"):
                        cli.discover_host_pid(Path("/host"))


if __name__ == "__main__":
    unittest.main()
