"""Offline safety and lifecycle tests; no host processes or providers are used."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ungrok_cli", ROOT / "ungrok.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
NODE = shutil.which("node")
VALUES = {"SAND_XAI_BASE_URL": "http://127.0.0.1:8317/v1",
          "SAND_XAI_MODEL": "example-model", "XAI_API_KEY": "test-only-secret"}


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
        mock.patch.object(cli.urllib.request, "build_opener",
                          side_effect=AssertionError("Unexpected network access")).start()
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
        self.assertNotIn(VALUES["XAI_API_KEY"], self.stdout.getvalue())

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
        for target in (self.installation.config, self.installation.adapter,
                       self.installation.image_helper, self.installation.manifest):
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
        for helper in (self.installation.adapter, self.installation.image_helper):
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
                self.installation.install(dict(VALUES, XAI_API_KEY="changed-test-key"), lambda message: None)
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
    def test_supported_urls(self):
        for url in ("https://api.example.com/v1", "http://localhost:8317/v1",
                    "http://127.0.0.1:8317/v1", "http://[::1]:8317/v1"):
            with self.subTest(url=url):
                self.assertEqual(cli.validate_config(dict(VALUES, SAND_XAI_BASE_URL=url))["SAND_XAI_THINKING"], "disabled")

    def test_unsafe_urls_refused(self):
        for url in ("http://api.example.com/v1", "ftp://localhost/v1", "https://user:secret@example.com/v1",
                    "https://example.com/v1?key=secret", "https://example.com/v1#fragment", "https://",
                    "https://example.com:invalid/v1", "https://example.com:99999/v1",
                    "https://bad host.example/v1", "https://example.com/bad path"):
            with self.subTest(url=url), self.assertRaises(cli.Failure):
                cli.validate_config(dict(VALUES, SAND_XAI_BASE_URL=url))

    def test_invalid_fields_and_model_cap(self):
        changes = [{"UNKNOWN": "value"}, {"SAND_XAI_MODEL": "x" * 201},
                   {"SAND_XAI_MODEL": "display name"}, {"XAI_API_KEY": ""},
                   {"XAI_API_KEY": "secret\nINJECT=value"}, {"XAI_API_KEY": '"quoted"'},
                   {"XAI_API_KEY": " leading"}, {"SAND_XAI_THINKING": "enabled"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(cli.Failure):
                cli.validate_config(dict(VALUES, **change))
        with self.assertRaises(cli.Failure):
            cli.validate_config({})

    def test_config_field_and_file_caps(self):
        with self.assertRaises(cli.Failure):
            cli.validate_config(dict(VALUES, XAI_API_KEY="a" * 16385))
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
    def probe_response(self, payload):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = payload
        opener = mock.Mock()
        opener.open.return_value = response
        return opener, response

    def test_probe_sends_only_synthetic_prompt_and_disables_proxies(self):
        opener, response = self.probe_response(b'{"choices":[{"message":{"content":"UNGROK_OK"}}]}')
        output = io.StringIO()
        with mock.patch.object(cli.urllib.request, "build_opener", return_value=opener) as build, \
                contextlib.redirect_stdout(output):
            cli.probe(VALUES)
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], cli.NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, VALUES["SAND_XAI_BASE_URL"] + "/chat/completions")
        self.assertEqual(json.loads(request.data)["messages"],
                         [{"role": "user", "content": "Reply exactly UNGROK_OK"}])
        response.read.assert_called_once_with(1024 * 1024 + 1)
        self.assertNotIn(VALUES["XAI_API_KEY"], output.getvalue())

    def test_probe_response_cap_and_invalid_sentinels(self):
        for payload in (b"x" * (1024 * 1024 + 1), b"not json", b"{}",
                        b'{"choices":[{"message":{"content":"wrong"}}]}'):
            opener, _ = self.probe_response(payload)
            with self.subTest(length=len(payload)), \
                    mock.patch.object(cli.urllib.request, "build_opener", return_value=opener), \
                    self.assertRaises(cli.Failure):
                cli.probe(VALUES)

    def test_redirect_handler_refuses_credential_forwarding(self):
        self.assertIsNone(cli.NoRedirect().redirect_request(None, None, 302, "redirect", {},
                                                          "https://other.example/collect"))


if __name__ == "__main__":
    unittest.main()
