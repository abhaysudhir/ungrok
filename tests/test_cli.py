"""Offline safety and lifecycle tests; no host processes or providers are used."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ungrok_cli", ROOT / "ungrok.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
NODE = shutil.which("node")
VALUES = {"UNGROK_PROVIDER": "claude", "UNGROK_MODEL": "sonnet", "UNGROK_CLI": "/test-only/claude"}


def host_source(extra=""):
    return ("function fixture(sessionOptions, options2, experimentModelOverride, onRequestId) {\n"
            + cli.ANCHOR + "\n      });\n}\n" + extra).encode()


@unittest.skipUnless(NODE, "Node is required for real JavaScript syntax checks")
class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.host_dir = self.root / "host"
        self.data_dir = self.root / "data"
        self.state_dir = self.root / "state"
        for path in (self.host_dir, self.data_dir):
            path.mkdir(mode=0o700)
        self.installation = cli.Installation(SimpleNamespace(
            host_dir=str(self.host_dir), data_dir=str(self.data_dir),
            state_dir=str(self.state_dir), node=NODE))
        self.original = host_source()
        self.installation.host.write_bytes(self.original)
        self.installation.host.chmod(0o640)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(cli.sys, "platform", "linux").start()
        self.auth_check = mock.patch.object(cli, "runtime_check").start()
        self.stdout = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.stdout)
        # Keep the context manager that actually entered alive through cleanup.
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def install(self):
        self.installation.install(VALUES, lambda message: None)

    def manifest(self):
        return json.loads(self.installation.manifest.read_bytes())

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in self.root.rglob("*") if p.is_file()}

    def assert_refusal_unchanged(self, action):
        before = self.snapshot()
        with self.assertRaises(cli.Failure):
            action()
        self.assertEqual(self.snapshot(), before)

    def test_fresh_install_records_original_and_private_files(self):
        self.install()
        record = self.manifest()
        self.assertEqual(Path(record["backup"]).read_bytes(), self.original)
        self.assertEqual(record["original_sha256"], cli.digest(self.original))
        self.assertEqual(record["patched_sha256"], cli.digest(self.installation.host.read_bytes()))
        self.assertEqual(self.installation.host.read_bytes().count(cli.BEGIN.encode()), 1)
        self.assertEqual(self.installation.host.stat().st_mode & 0o777, 0o640)
        for path in (self.installation.config, self.installation.adapter, self.installation.manifest):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state_dir.stat().st_mode & 0o777, 0o700)
        self.auth_check.assert_called_once_with(VALUES, "status", NODE)

    def test_idempotent_repair_keeps_original_backup_and_host(self):
        self.install()
        record = self.manifest()
        patched = self.installation.host.read_bytes()
        self.install()
        self.assertEqual(self.manifest(), record)
        self.assertEqual(self.installation.host.read_bytes(), patched)
        self.assertEqual(Path(record["backup"]).read_bytes(), self.original)

    def test_missing_module_is_repaired(self):
        self.install()
        record = self.manifest()
        self.installation.adapter.unlink()
        self.install()
        self.assertEqual(cli.digest(self.installation.adapter.read_bytes()), record["adapter_sha256"])
        self.assertEqual(self.manifest(), record)

    def test_subscription_helpers_missing_repair_and_tampering_refused(self):
        self.install()
        for helper, key in ((self.installation.subscription_helper, "subscription_helper_sha256"),
                            (self.installation.codex_helper, "codex_helper_sha256")):
            with self.subTest(helper=helper.name):
                helper.unlink()
                self.install()
                self.assertEqual(cli.digest(helper.read_bytes()), self.manifest()[key])
                original = helper.read_bytes()
                helper.write_bytes(b"// user changed runtime\n")
                self.assert_refusal_unchanged(self.install)
                helper.write_bytes(original)

    def test_subscription_auth_failure_does_not_patch_or_write(self):
        self.auth_check.side_effect = cli.Failure("Subscription auth not verified")
        self.assert_refusal_unchanged(self.install)

    def test_legacy_config_is_not_overwritten_by_new_setup(self):
        self.installation.config.write_bytes(b"XAI_API_KEY=test-only-legacy\n")
        self.installation.config.chmod(0o600)
        self.assert_refusal_unchanged(self.install)
        self.auth_check.assert_not_called()

    def test_updated_stock_host_gets_new_backup(self):
        self.install()
        first = self.manifest()
        updated = host_source("// new upstream version\n")
        self.installation.host.write_bytes(updated)
        self.install()
        second = self.manifest()
        self.assertNotEqual(first["backup"], second["backup"])
        self.assertEqual(Path(first["backup"]).read_bytes(), self.original)
        self.assertEqual(Path(second["backup"]).read_bytes(), updated)
        self.installation.rollback(lambda message: None)
        self.assertEqual(self.installation.host.read_bytes(), updated)

    def test_unsupported_duplicate_and_foreign_hooks_refuse_without_writes(self):
        candidates = [b"module.exports = {};\n", self.original + self.original,
                      self.original + b"// createXaiPromptSession foreign patch\n",
                      self.original + cli.BEGIN.encode()]
        for candidate in candidates:
            with self.subTest(candidate=candidate[-45:]):
                self.installation.host.write_bytes(candidate)
                self.assert_refusal_unchanged(self.install)

    def test_syntax_error_refuses_without_writes(self):
        self.installation.host.write_bytes(host_source("const = ;\n"))
        self.assert_refusal_unchanged(self.install)

    def test_confirmation_declined_leaves_no_files(self):
        def decline(message):
            raise cli.Failure("Cancelled")
        self.assert_refusal_unchanged(lambda: self.installation.install(VALUES, decline))

    def test_rollback_restores_exact_original_and_retains_private_state(self):
        self.install()
        self.installation.rollback(lambda message: None)
        self.assertEqual(self.installation.host.read_bytes(), self.original)
        self.assertTrue(self.installation.config.is_file())
        self.assertTrue(self.installation.adapter.is_file())
        self.assertTrue(self.installation.manifest.is_file())

    def test_tampered_host_refuses_repair_and_rollback(self):
        self.install()
        self.installation.host.write_bytes(self.installation.host.read_bytes() + b"// modified\n")
        self.assert_refusal_unchanged(self.install)
        self.assert_refusal_unchanged(lambda: self.installation.rollback(lambda message: None))

    def test_tampered_backup_refuses_rollback(self):
        self.install()
        Path(self.manifest()["backup"]).write_bytes(b"// tampered\n")
        self.assert_refusal_unchanged(lambda: self.installation.rollback(lambda message: None))

    def test_tampered_backup_refuses_repair_and_doctor(self):
        self.install()
        Path(self.manifest()["backup"]).write_bytes(b"// corrupted original\n")
        self.assert_refusal_unchanged(self.install)
        self.assert_refusal_unchanged(self.installation.doctor)

    def test_malformed_manifest_refuses_cleanly(self):
        self.install()
        record = self.manifest()
        for bad in ([], None, {}, dict(record, backup=12), dict(record, adapter_sha256="bad")):
            self.installation.manifest.write_text(json.dumps(bad))
            with self.subTest(type=type(bad).__name__):
                self.assert_refusal_unchanged(self.install)

    def test_changed_files_during_confirmation_are_preserved(self):
        self.install()
        for target in (self.installation.config, self.installation.adapter, self.installation.subscription_helper,
                       self.installation.codex_helper, self.installation.image_helper, self.installation.manifest):
            original = target.read_bytes()
            changed = original + b"\n"
            def concurrent_edit(message):
                target.write_bytes(changed)
            with self.subTest(target=target.name), self.assertRaisesRegex(cli.Failure, "changed during confirmation"):
                self.installation.install(VALUES, concurrent_edit)
            self.assertEqual(target.read_bytes(), changed)
            target.write_bytes(original)

    def test_missing_image_helper_repairs_and_tampering_refuses(self):
        self.install()
        original = self.installation.image_helper.read_bytes()
        self.installation.image_helper.unlink()
        self.install()
        self.assertEqual(self.installation.image_helper.read_bytes(), original)
        self.installation.image_helper.write_bytes(b"# user modified\n")
        self.assert_refusal_unchanged(self.install)

    def test_repair_saves_recovery_copies_of_existing_helpers(self):
        self.install()
        existing = set(self.state_dir.glob("backup-*"))
        self.install()
        new = set(self.state_dir.glob("backup-*")) - existing
        self.assertEqual(len(new), 1)
        backup = new.pop()
        for helper in (self.installation.adapter, self.installation.image_helper,
                       self.installation.subscription_helper, self.installation.codex_helper):
            self.assertEqual((backup / helper.name).read_bytes(), helper.read_bytes())

    def test_rollback_then_reinstall_lifecycle(self):
        self.install()
        self.installation.rollback(lambda message: None)
        self.install()
        self.installation.doctor()
        self.installation.rollback(lambda message: None)
        self.assertEqual(self.installation.host.read_bytes(), self.original)

    def test_tampered_adapter_refuses_repair(self):
        self.install()
        self.installation.adapter.write_bytes(b"// user changes\n")
        self.assert_refusal_unchanged(self.install)

    def test_transaction_failure_restores_prior_targets(self):
        self.install()
        prior = {p: p.read_bytes() for p in (self.installation.host, self.installation.adapter,
                                           self.installation.config, self.installation.manifest)}
        real_write = cli.atomic_write
        failed = False
        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == self.installation.host and not failed:
                failed = True
                raise OSError("injected failure")
            return real_write(path, data, mode)
        with mock.patch.object(cli, "atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError):
                self.installation.install(dict(VALUES, UNGROK_MODEL="opus"), lambda message: None)
        self.assertTrue(failed)
        for path, data in prior.items():
            self.assertEqual(path.read_bytes(), data)

    def test_doctor_is_read_only_and_never_calls_network(self):
        self.install()
        before = self.snapshot()
        self.installation.doctor()
        self.assertEqual(self.snapshot(), before)
        self.assertIn("NOT verified", self.stdout.getvalue())

    def test_manifest_write_failure_reverts_fresh_install(self):
        real_write = cli.atomic_write
        def fail_manifest(path, data, mode=0o600):
            if path == self.installation.manifest:
                raise OSError("injected manifest failure")
            return real_write(path, data, mode)
        with mock.patch.object(cli, "atomic_write", side_effect=fail_manifest):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(self.installation.host.read_bytes(), self.original)
        self.assertFalse(self.installation.config.exists())
        self.assertFalse(self.installation.adapter.exists())
        self.assertFalse(self.installation.subscription_helper.exists())
        self.assertFalse(self.installation.codex_helper.exists())
        self.assertFalse(self.installation.manifest.exists())

    def test_non_linux_is_refused_without_writes(self):
        with mock.patch.object(cli.sys, "platform", "darwin"):
            self.assert_refusal_unchanged(self.install)

    def test_restart_refuses_unverified_pid_without_signaling(self):
        self.install()
        with mock.patch.object(cli, "verified_process", side_effect=cli.Failure("wrong PID")), \
                mock.patch.object(cli.os, "kill") as kill:
            with self.assertRaises(cli.Failure):
                self.installation.restart(42, lambda message: None)
            kill.assert_not_called()

    def test_restart_refuses_foreign_hook_without_process_inspection(self):
        self.installation.host.write_bytes(self.original + b"// createXaiPromptSession foreign hook\n")
        with mock.patch.object(cli, "verified_process") as process, mock.patch.object(cli.os, "kill") as kill:
            with self.assertRaises(cli.Failure):
                self.installation.restart(42, lambda message: None)
            process.assert_not_called()
            kill.assert_not_called()

    def test_restart_refuses_pid_reused_during_confirmation(self):
        self.install()
        with mock.patch.object(cli, "verified_process", side_effect=[(12, "100"), (12, "101")]), \
                mock.patch.object(Path, "iterdir", return_value=iter(())), \
                mock.patch.object(cli.os, "kill") as kill:
            with self.assertRaises(cli.Failure):
                self.installation.restart(42, lambda message: None)
            kill.assert_not_called()


class ConfigurationTests(unittest.TestCase):
    def test_supported_subscription_providers_and_default_model(self):
        for provider in ("claude", "chatgpt"):
            config = {"UNGROK_PROVIDER": provider, "UNGROK_CLI": "/test-only/native-cli"}
            with self.subTest(provider=provider):
                self.assertEqual(cli.validate_config(config), config)
        self.assertEqual(cli.validate_config(dict(VALUES, UNGROK_MODEL="opus[1m]"))["UNGROK_MODEL"], "opus[1m]")

    def test_legacy_api_configuration_refused(self):
        for key in ("XAI_API_KEY", "SAND_XAI_BASE_URL", "OPENAI_API_KEY"):
            with self.subTest(key=key), self.assertRaisesRegex(cli.Failure, "Legacy API"):
                cli.validate_config(dict(VALUES, **{key: "test-only"}))

    def test_invalid_fields_and_model_cap(self):
        changes = [{"UNKNOWN": "value"}, {"UNGROK_MODEL": "x" * 201},
                   {"UNGROK_MODEL": "display name"}, {"UNGROK_CLI": ""},
                   {"UNGROK_CLI": "/path\nINJECT=value"}, {"UNGROK_MODEL": '"quoted"'},
                   {"UNGROK_MODEL": " leading"}, {"UNGROK_PROVIDER": "openrouter"},
                   {"UNGROK_CLI": "relative/path"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(cli.Failure):
                cli.validate_config(dict(VALUES, **change))
        with self.assertRaises(cli.Failure):
            cli.validate_config({})

    def test_config_field_and_file_caps(self):
        with self.assertRaises(cli.Failure):
            cli.validate_config(dict(VALUES, UNGROK_CLI="/" + "a" * 16385))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config"
            path.write_bytes(b"#" * 65537)
            path.chmod(0o600)
            with self.assertRaises(cli.Failure):
                cli.read_config(path)

    def test_private_config_roundtrip_and_invalid_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "provider.env"
            path.write_bytes(cli.encode_config(VALUES))
            path.chmod(0o600)
            self.assertEqual(cli.read_config(path), cli.validate_config(VALUES))
            path.chmod(0o644)
            with self.assertRaises(cli.Failure):
                cli.read_config(path)
            path.chmod(0o600)
            for raw in (b"XAI_API_KEY=a\nXAI_API_KEY=b\n", b"not-an-assignment\n", b"\xff",
                        b"export XAI_API_KEY=secret\n"):
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(cli.Failure):
                    cli.read_config(path)

    def test_symlink_config_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(cli.encode_config(VALUES))
            source.chmod(0o600)
            link = Path(directory) / "link"
            link.symlink_to(source)
            with self.assertRaises(cli.Failure):
                cli.read_config(link)


class ProbeTests(unittest.TestCase):
    def process(self, payload):
        process = mock.Mock(returncode=0)
        process.communicate.return_value = (payload, b"")
        return process

    def test_native_probe_uses_shared_runtime_and_scrubs_api_environment(self):
        reply = self.process(b'{"ok":true,"provider":"claude","sentinel":"UNGROK_OK"}')
        with mock.patch.dict(cli.os.environ, {"ANTHROPIC_API_KEY": "secret", "OPENAI_API_KEY": "secret",
                                            "CLAUDE_CODE_OAUTH_TOKEN": "secret", "HTTP_PROXY": "secret",
                                            "CLAUDE_CONFIG_DIR": "/test-only/claude-profile", "CODEX_HOME": "/test-only/codex-profile"}), \
                mock.patch.object(cli.subprocess, "Popen", return_value=reply) as run, \
                mock.patch.object(cli, "stop_runtime"), \
                contextlib.redirect_stdout(io.StringIO()):
            cli.probe(VALUES, "/test-only/node")
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["/test-only/node", str(ROOT / "vendor/subscription-runtime.cjs"), "probe"])
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "HTTP_PROXY"):
            self.assertNotIn(key, run.call_args.kwargs["env"])
        self.assertFalse(Path(command[3]).exists())
        self.assertEqual(run.call_args.kwargs["env"]["CLAUDE_CONFIG_DIR"], "/test-only/claude-profile")
        self.assertEqual(run.call_args.kwargs["env"]["CODEX_HOME"], "/test-only/codex-profile")

    def test_wrong_auth_or_probe_sentinel_is_refused_without_contents(self):
        cases = [("status", {"ok": True, "provider": "claude", "subscription": False}),
                 ("status", {"ok": True, "provider": "chatgpt", "subscription": True}),
                 ("probe", {"ok": True, "provider": "claude", "sentinel": "PRIVATE_RESPONSE"})]
        for command, payload in cases:
            reply = self.process(json.dumps(payload).encode())
            with self.subTest(command=command), mock.patch.object(cli.subprocess, "Popen", return_value=reply), \
                    mock.patch.object(cli, "stop_runtime"):
                with self.assertRaises(cli.Failure) as error:
                    cli.runtime_check(VALUES, command, "/test-only/node")
                self.assertNotIn("PRIVATE_RESPONSE", str(error.exception))

    def test_login_delegates_only_to_official_subscription_flow(self):
        with mock.patch.object(cli.sys, "platform", "linux"), \
                mock.patch.object(cli, "resolve_cli", return_value="/test-only/claude"), \
                mock.patch.object(cli.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run, \
                mock.patch.object(cli, "runtime_check") as status, contextlib.redirect_stdout(io.StringIO()):
            cli.login("claude", node="/test-only/node")
        self.assertEqual(run.call_args.args[0], ["/test-only/claude", "auth", "login", "--claudeai"])
        status.assert_called_once_with({"UNGROK_PROVIDER": "claude", "UNGROK_CLI": "/test-only/claude"}, "status", "/test-only/node")

    def test_missing_official_cli_has_actionable_error(self):
        with mock.patch.object(cli.shutil, "which", return_value=None), self.assertRaisesRegex(cli.Failure, "docs/providers.md"):
            cli.resolve_cli("chatgpt")

    @unittest.skipUnless(cli.os.name == "posix", "Process-group cleanup is for the supported Linux host")
    def test_runtime_timeout_kills_native_descendant_that_ignores_term(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vendor").mkdir()
            heartbeat = root / "heartbeat"
            child_code = (
                "import signal,time\n"
                "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                "for _ in range(500):\n"
                f" with open({str(heartbeat)!r},'a') as stream: stream.write('x')\n"
                " time.sleep(0.02)\n"
            )
            # Test-only native descendant shares the session, just like runtime
            # CLI mode. Both leader and child deliberately ignore graceful stop.
            (root / "vendor/subscription-runtime.cjs").write_text(
                "import signal,subprocess,sys,time\n"
                "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                f"subprocess.Popen([sys.executable,'-c',{child_code!r}])\n"
                "time.sleep(10)\n"
            )
            with mock.patch.object(cli, "ROOT", root), \
                    mock.patch.object(cli, "RUNTIME_TIMEOUTS", {"probe": 0.5}), \
                    mock.patch.object(cli, "RUNTIME_STOP_GRACE", 0.1):
                with self.assertRaises(cli.Failure):
                    cli.runtime_check(VALUES, "probe", cli.sys.executable)
            self.assertTrue(heartbeat.exists(), "fake native child never started")
            count = len(heartbeat.read_bytes())
            time.sleep(0.15)
            self.assertEqual(len(heartbeat.read_bytes()), count, "native descendant survived timeout")


if __name__ == "__main__":
    unittest.main()
