#!/usr/bin/env python3
"""A reversible Grok Bot host mod. Python standard library only."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

VERSION = "0.2.0-alpha.1"
ROOT = Path(__file__).resolve().parent
BEGIN = "      // ungrok:begin v1"
END = "      // ungrok:end v1"
ANCHOR = """      const requestedModel = resolveSandRequestedModel({
        sessionOptions,
        envModelOverride: process.env.SAND_AGENT_MODEL,
        storedDefaultModel: options2.getDefaultModel?.(),
        storedComputerUseModel: options2.getComputerUseModel?.(),
        storedBrowserUseModel: options2.getBrowserUseModel?.(),
        experimentModelOverride
      });
      const session = createCursorInferencePromptSession({"""
CALL = "      const session = createCursorInferencePromptSession({"
KEYS = {"UNGROK_PROVIDER", "UNGROK_MODEL", "UNGROK_CLI"}
RUNTIME_TIMEOUTS = {"status": 45, "probe": 210}
RUNTIME_STOP_GRACE = 5
CLIENTS = {
    "claude": ("@anthropic-ai/claude-code", "2.1.263", "claude", "2.1.263 (Claude Code)"),
    "chatgpt": ("@openai/codex", "0.153.4", "codex", "codex-cli 0.153.4"),
}


class Failure(Exception):
    """An actionable, secret-free failure safe to print."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise Failure(f"Expected a regular file, not a symlink: {path}")
    return path.read_bytes()


def secure_dir(path):
    if path.is_symlink():
        raise Failure(f"Refusing symlink directory: {path}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid():
        raise Failure(f"Directory must belong to the current user: {path}")
    if path.stat().st_mode & 0o077:
        raise Failure(f"Private state directory needs mode 700: {path}")


def atomic_write(path, data, mode=0o600):
    if path.is_symlink():
        raise Failure(f"Refusing to replace a symlink: {path}")
    fd, name = tempfile.mkstemp(prefix=".ungrok-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_config(values):
    if any(key.startswith("SAND_") or "API_KEY" in key for key in values):
        raise Failure("Legacy API configuration is unsupported. It was not migrated or deleted. Use subscription setup with a new config.")
    missing = {"UNGROK_PROVIDER", "UNGROK_CLI"} - values.keys()
    if missing:
        raise Failure("Missing provider fields: " + ", ".join(sorted(missing)))
    for key, value in values.items():
        if key not in KEYS or not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise Failure("Invalid or unsupported provider field; use the example configuration.")
        if value != value.strip() or value.startswith(("'", '"')) or value.endswith(("'", '"')):
            raise Failure("Provider values must not contain outer quotes or whitespace.")
        if len(value.encode("utf-8")) > 16384:
            raise Failure("Provider field exceeds the 16 KiB limit.")
    if values["UNGROK_PROVIDER"] not in {"claude", "chatgpt"}:
        raise Failure("Choose the claude or chatgpt subscription provider.")
    if not Path(values["UNGROK_CLI"]).is_absolute():
        raise Failure("UNGROK_CLI must be an absolute official CLI executable path.")
    if "UNGROK_MODEL" in values and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\[\]-]{0,199}", values["UNGROK_MODEL"]):
        raise Failure("Invalid native model alias.")
    return dict(values)


def native_env():
    """No API keys, provider overrides, injected tokens, or proxy inheritance."""
    allowed = {"HOME", "PATH", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "COLORTERM",
               "TMPDIR", "TMP", "TEMP", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR",
               "DBUS_SESSION_BUS_ADDRESS", "CLAUDE_CONFIG_DIR", "CODEX_HOME"}
    clean = {key: value for key, value in os.environ.items() if key in allowed or key.startswith("LC_")}
    clean.update(CLAUDE_CODE_SAFE_MODE="1", DISABLE_TELEMETRY="1", DISABLE_ERROR_REPORTING="1")
    return clean


def resolve_cli(provider, supplied=None):
    command = "claude" if provider == "claude" else "codex"
    found = str(supplied) if supplied else shutil.which(command)
    if not found or not Path(found).is_absolute() or not Path(found).is_file() or not os.access(found, os.X_OK):
        raise Failure(f"Official {command} CLI not found. Install it on Grok Bot's computer using docs/providers.md, then retry with --cli /absolute/path/{command}.")
    return found


def login(provider, supplied=None, node=None):
    if sys.platform != "linux":
        raise Failure("Run login in Grok Bot's remote Linux computer terminal, not on your Mac.")
    executable = resolve_cli(provider, supplied)
    args = ["auth", "login", "--claudeai"] if provider == "claude" else ["login", "--device-auth"]
    result = subprocess.run([executable, *args], env=native_env())
    if result.returncode:
        raise Failure("Official CLI login did not complete. No credential files were read or copied by ungrok.")
    runtime_check({"UNGROK_PROVIDER": provider, "UNGROK_CLI": executable}, "status", node)
    print(f"Native {provider} subscription login verified. Credentials remain with the official CLI.")


def read_config(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise Failure("Provider configuration must be a regular file under 64 KiB.")
    raw = read_regular(path)
    if len(raw) > 65536:
        raise Failure("Provider configuration exceeds 64 KiB.")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Failure(f"Credential file must belong to you and have mode 600: {path}")
    result = {}
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise Failure("Provider configuration must be UTF-8.") from None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            raise Failure("Invalid provider configuration. Expected KEY=value lines.")
        key, value = line.split("=", 1)
        if key in result:
            raise Failure("Duplicate provider configuration key.")
        result[key] = value
    return validate_config(result)


def encode_config(values):
    return ("# ungrok private provider config. Never commit this file.\n" +
            "\n".join(f"{k}={v}" for k, v in sorted(values.items())) + "\n").encode()


def hook(config):
    return "\n".join([
        BEGIN,
        '      return require("./ungrok-session.cjs").createXaiPromptSession({',
        "        requestedModel, onRequestId, sessionOptions,",
        f"        envFile: {json.dumps(str(config))}",
        "      });",
        END,
        "",
    ])


def patch_bytes(original, config):
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError:
        raise Failure("Host bundle is not valid UTF-8; unsupported layout.") from None
    if BEGIN in text or "createXaiPromptSession" in text:
        raise Failure("Host already has a provider patch. Inspect it; do not stack patches. See docs/updates.md.")
    if text.count(ANCHOR) != 1 or text.count(CALL) != 1:
        raise Failure("Unsupported host layout: expected exactly one known insertion point. Nothing changed.")
    return text.replace(ANCHOR, ANCHOR.replace(CALL, hook(config) + CALL), 1).encode()


class Installation:
    def __init__(self, args):
        self.host_dir = Path(args.host_dir).expanduser().absolute()
        self.data_dir = Path(args.data_dir).expanduser().absolute()
        self.state_dir = Path(args.state_dir).expanduser().absolute()
        self.host = self.host_dir / "host-main.cjs"
        self.adapter = self.host_dir / "ungrok-session.cjs"
        self.image_helper = self.host_dir / "ungrok-resize-image.py"
        self.subscription_helper = self.host_dir / "subscription-runtime.cjs"
        self.codex_helper = self.host_dir / "codex-subscription.cjs"
        self.config = self.data_dir / "ungrok.env"
        self.manifest = self.state_dir / "install.json"
        self.node = args.node

    def preflight(self):
        if sys.platform != "linux":
            raise Failure("Run inside Grok Bot > Computer > Terminal on Linux, not on your Mac. Nothing changed.")
        for path in (self.host_dir, self.data_dir, self.state_dir):
            if path.is_symlink() or path.resolve() != path:
                raise Failure(f"Use a real directory path without symlink components: {path}")
        if not self.host_dir.is_dir() or not self.data_dir.is_dir():
            raise Failure("Grok host/data directories are missing. Open the remote Computer terminal, or check path overrides.")
        original = read_regular(self.host)
        if self.host.stat().st_uid != os.getuid():
            raise Failure("Host file must belong to the current user. Do not run ungrok with sudo.")
        if not self.node or not Path(self.node).is_file():
            raise Failure("Node runtime not found. Supply --node /absolute/path/to/node before the command.")
        return original

    def syntax(self, data, label):
        with tempfile.TemporaryDirectory(prefix="ungrok-check-") as scratch:
            candidate = Path(scratch) / "candidate.cjs"
            candidate.write_bytes(data)
            try:
                result = subprocess.run([self.node, "--check", str(candidate)], capture_output=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                raise Failure(f"Could not syntax-check {label}. Nothing changed.") from None
            if result.returncode:
                raise Failure(f"Node rejected {label}. Unsupported runtime or host layout. Nothing changed.")

    def load_manifest(self):
        try:
            info = json.loads(read_regular(self.manifest))
            required = {"version", "host", "config", "backup", "original_sha256", "patched_sha256",
                        "adapter_sha256", "image_helper_sha256", "subscription_helper_sha256", "codex_helper_sha256"}
            if not isinstance(info, dict) or not required.issubset(info) or any(
                not isinstance(info[key], str) or not info[key] for key in required
            ) or any(not re.fullmatch(r"[0-9a-f]{64}", info[key]) for key in required if key.endswith("_sha256")):
                raise Failure("Invalid or older installation record. For an older ungrok release, roll back with that release's checkout before migrating. Private files were not changed.")
            if info["host"] != str(self.host) or info["config"] != str(self.config):
                raise Failure("Saved installation belongs to different paths. Use its original path overrides.")
            return info
        except (KeyError, ValueError, TypeError):
            raise Failure("Invalid installation record. Inspect private backups before proceeding.") from None

    def original_backup(self, info):
        backup = Path(info["backup"])
        if backup.resolve().parent.parent != self.state_dir.resolve():
            raise Failure("Backup path is outside this installation's private state.")
        restored = read_regular(backup)
        if digest(restored) != info["original_sha256"]:
            raise Failure("Backup checksum mismatch. Nothing changed.")
        return restored

    def is_current(self, original):
        if BEGIN.encode() not in original:
            return False
        info = self.load_manifest()
        if digest(original) != info["patched_sha256"]:
            raise Failure("Patched host changed since installation. Refusing to overwrite it.")
        return True

    def install(self, values, confirm):
        original = self.preflight()
        if self.config.exists():
            read_config(self.config)  # Never overwrite a legacy API configuration.
        if self.is_current(original):
            info = self.load_manifest()
            self.original_backup(info)
            bundled = read_regular(ROOT / "vendor/xai-prompt-session.cjs")
            if digest(bundled) != info["adapter_sha256"]:
                raise Failure("This checkout has a different adapter. Roll back with the installed version before upgrading.")
            if self.adapter.exists() and digest(read_regular(self.adapter)) != info["adapter_sha256"]:
                raise Failure("Installed adapter was modified. Refusing to overwrite it.")
            if self.image_helper.exists() and digest(read_regular(self.image_helper)) != info.get("image_helper_sha256"):
                raise Failure("Installed image helper was modified. Refusing to overwrite it.")
            if self.subscription_helper.exists() and digest(read_regular(self.subscription_helper)) != info["subscription_helper_sha256"]:
                raise Failure("Installed subscription runtime was modified. Refusing to overwrite it.")
            if self.codex_helper.exists() and digest(read_regular(self.codex_helper)) != info["codex_helper_sha256"]:
                raise Failure("Installed Codex runtime was modified. Refusing to overwrite it.")
            candidate = original
        else:
            candidate = patch_bytes(original, self.config)
            info = None
            if self.adapter.exists():
                # Only replace an adapter previously recorded by this installation.
                previous = self.load_manifest()
                if digest(read_regular(self.adapter)) != previous["adapter_sha256"]:
                    raise Failure("Existing adapter is not the recorded ungrok version. Nothing changed.")
        vendor = read_regular(ROOT / "vendor/xai-prompt-session.cjs")
        image_helper = read_regular(ROOT / "scripts/resize_image.py")
        subscription_helper = read_regular(ROOT / "vendor/subscription-runtime.cjs")
        codex_helper = read_regular(ROOT / "vendor/codex-subscription.cjs")
        if info and digest(codex_helper) != info["codex_helper_sha256"]:
            raise Failure("Codex runtime differs from installation. Roll back with the installed checkout before upgrading.")
        if not info and self.codex_helper.exists():
            previous = self.load_manifest()
            if digest(read_regular(self.codex_helper)) != previous["codex_helper_sha256"]:
                raise Failure("Existing Codex runtime is not the recorded version. Nothing changed.")
        if info and digest(subscription_helper) != info["subscription_helper_sha256"]:
            raise Failure("Subscription runtime differs from installation. Roll back with the installed checkout before upgrading.")
        if not info and self.subscription_helper.exists():
            previous = self.load_manifest()
            if digest(read_regular(self.subscription_helper)) != previous["subscription_helper_sha256"]:
                raise Failure("Existing subscription runtime is not the recorded version. Nothing changed.")
        if info and digest(image_helper) != info.get("image_helper_sha256"):
            raise Failure("Image helper version differs from installation. Roll back with the installed checkout before upgrading.")
        if not info and self.image_helper.exists():
            previous = self.load_manifest()
            if digest(read_regular(self.image_helper)) != previous.get("image_helper_sha256"):
                raise Failure("Existing image helper is not the recorded ungrok version. Nothing changed.")
        values = validate_config(values)
        self.syntax(candidate, "patched host")
        self.syntax(vendor, "provider adapter")
        self.syntax(subscription_helper, "subscription runtime")
        self.syntax(codex_helper, "Codex runtime")
        runtime_check(values, "status", self.node)
        watched = (self.adapter, self.image_helper, self.subscription_helper, self.codex_helper, self.config, self.manifest)
        before = {path: (read_regular(path), stat.S_IMODE(path.stat().st_mode))
                  if path.exists() or path.is_symlink() else None for path in watched}
        confirm("This changes the shared host for ALL bots. If ungrok is already running, saved provider/model changes can affect new sessions immediately, before restart. Prompts and tool results use your native subscription CLI. Have all bot work finished and scheduled routines been paused, and may setup continue?")
        secure_dir(self.state_dir)
        with self.lock():
            if read_regular(self.host) != original:
                raise Failure("Host changed during preflight. Retry doctor; nothing changed.")
            for path in watched:
                current = (read_regular(path), stat.S_IMODE(path.stat().st_mode)) if path.exists() or path.is_symlink() else None
                if current != before[path]:
                    raise Failure("Installation files changed during confirmation. Nothing overwritten; retry doctor.")
            backup = Path(tempfile.mkdtemp(prefix="backup-", dir=self.state_dir))
            atomic_write(backup / "host-main.cjs", original)
            targets = [(self.adapter, vendor, 0o600), (self.image_helper, image_helper, 0o600),
                       (self.subscription_helper, subscription_helper, 0o600), (self.config, encode_config(values), 0o600),
                       (self.codex_helper, codex_helper, 0o600),
                       (self.host, candidate, stat.S_IMODE(self.host.stat().st_mode))]
            old = {}
            for target, _, _ in targets:
                old[target] = (read_regular(target), stat.S_IMODE(target.stat().st_mode)) if target.exists() else None
                if target == self.config and old[target]:
                    atomic_write(backup / "provider.env", old[target][0])
                elif target in (self.adapter, self.image_helper, self.subscription_helper, self.codex_helper) and old[target]:
                    atomic_write(backup / target.name, old[target][0])
            record = info or {
                "version": VERSION, "host": str(self.host), "config": str(self.config),
                "backup": str(backup / "host-main.cjs"), "original_sha256": digest(original),
                "patched_sha256": digest(candidate), "adapter_sha256": digest(vendor), "image_helper_sha256": digest(image_helper),
                "subscription_helper_sha256": digest(subscription_helper),
                "codex_helper_sha256": digest(codex_helper),
            }
            changed = []
            try:
                for target, data, mode in targets:
                    atomic_write(target, data, mode)
                    changed.append(target)
                atomic_write(self.manifest, (json.dumps(record, indent=2) + "\n").encode())
            except BaseException as install_error:
                failures = []
                for target in reversed(changed):
                    try:
                        if old[target] is None:
                            target.unlink(missing_ok=True)
                        else:
                            atomic_write(target, *old[target])
                    except (OSError, Failure):
                        failures.append(str(target))
                if failures:
                    raise Failure("Install failed and some files could not be restored: " + ", ".join(failures) +
                                  f". Do not restart. Inspect private backup {backup}.") from install_error
                raise
        print("Installed. Host and adapter syntax checks passed. No host was restarted.")
        print("Next: ./ungrok probe, then ./ungrok restart --pid <verified-host-pid> --yes")
        print("Finally send a diagnostic in the app and check fresh [ungrok] session logs.")

    @contextlib.contextmanager
    def lock(self):
        import fcntl
        lock_path = self.state_dir / "lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Failure("Another ungrok operation is running.") from None
            yield

    def doctor(self):
        original = self.preflight()
        if self.is_current(original):
            info = self.load_manifest()
            self.original_backup(info)
            if not self.adapter.exists() or digest(read_regular(self.adapter)) != info["adapter_sha256"]:
                raise Failure("Host is patched but adapter is missing or changed. Inspect it, then use repair.")
            if not self.image_helper.exists() or digest(read_regular(self.image_helper)) != info.get("image_helper_sha256"):
                raise Failure("Image helper is missing or changed. Inspect it, then use repair.")
            if not self.subscription_helper.exists() or digest(read_regular(self.subscription_helper)) != info["subscription_helper_sha256"]:
                raise Failure("Subscription runtime is missing or changed. Inspect it, then use repair.")
            if not self.codex_helper.exists() or digest(read_regular(self.codex_helper)) != info["codex_helper_sha256"]:
                raise Failure("Codex runtime is missing or changed. Inspect it, then use repair.")
            self.syntax(original, "installed host")
            self.syntax(read_regular(self.adapter), "installed adapter")
            state = "Installed files match recorded hashes."
        else:
            patch_bytes(original, self.config)
            state = "Known host insertion point found; ungrok is not installed."
        print(state)
        if self.config.exists():
            values = read_config(self.config)
            print(f"Subscription config valid: provider={values['UNGROK_PROVIDER']} model={values.get('UNGROK_MODEL', 'CLI default')}")
        else:
            raise Failure("No ungrok provider configuration. Run setup. No network request was made.")
        print("Read-only check. Provider access and live app routing are NOT verified.")
        image_python = shutil.which("python3")
        image_runtime = subprocess.run([image_python, "-c", "import PIL"], capture_output=True, timeout=10) if image_python else None
        print("Pillow available for image resizing." if image_runtime is not None and image_runtime.returncode == 0 else
              "Pillow is missing: large inline images will fail. See optional image setup in docs/getting-started.md.")
        if BEGIN.encode() not in original:
            raise Failure("Run setup or repair before restarting the host.")

    def rollback(self, confirm):
        original = self.preflight()
        if not self.is_current(original):
            raise Failure("Current host is not the recorded patched host. Refusing cross-version rollback.")
        info = self.load_manifest()
        restored = self.original_backup(info)
        self.syntax(restored, "rollback host")
        confirm("Restore this host version's original inference code? Default-provider routing resumes after restart.")
        secure_dir(self.state_dir)
        with self.lock():
            if read_regular(self.host) != original:
                raise Failure("Host changed during rollback checks. Nothing changed.")
            atomic_write(self.host, restored, stat.S_IMODE(self.host.stat().st_mode))
        print("Original host restored. Restart through the verified supervisor to activate.")
        print("Private config, adapter, and backups were retained. No credentials were deleted.")

    def restart(self, pid, confirm):
        original = self.preflight()
        self.syntax(original, "host")
        adapter_before = None
        config_before = None
        helper_before = None
        subscription_before = None
        codex_before = None
        if BEGIN.encode() in original:
            if not self.is_current(original):
                raise Failure("Unknown patch; refusing restart.")
            info = self.load_manifest()
            if digest(read_regular(self.adapter)) != info["adapter_sha256"]:
                raise Failure("Adapter does not match installation. Repair before restart.")
            read_config(self.config)
            adapter_before = read_regular(self.adapter)
            config_before = read_regular(self.config)
            helper_before = read_regular(self.image_helper)
            if digest(helper_before) != info.get("image_helper_sha256"):
                raise Failure("Image helper does not match installation. Repair before restart.")
            subscription_before = read_regular(self.subscription_helper)
            if digest(subscription_before) != info["subscription_helper_sha256"]:
                raise Failure("Subscription runtime does not match installation. Repair before restart.")
            codex_before = read_regular(self.codex_helper)
            if digest(codex_before) != info["codex_helper_sha256"]:
                raise Failure("Codex runtime does not match installation. Repair before restart.")
        else:
            # A rollback restores this known layout. Do not restart foreign hooks
            # just because their bundle happens to pass Node's syntax check.
            patch_bytes(original, self.config)
        process = verified_process(pid, self.host)
        existing = set()
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                try:
                    existing.add((int(entry.name), verified_process(int(entry.name), self.host)))
                except (Failure, OSError):
                    pass
        confirm(f"Restart verified host PID {pid}? Active bot work may be interrupted.")
        # Recheck after the human confirmation to reduce PID-reuse risk.
        if verified_process(pid, self.host) != process:
            raise Failure("Host process changed before restart. Nothing signaled.")
        if read_regular(self.host) != original or (adapter_before is not None and (
            read_regular(self.adapter) != adapter_before or read_regular(self.config) != config_before
            or read_regular(self.image_helper) != helper_before
            or read_regular(self.subscription_helper) != subscription_before
            or read_regular(self.codex_helper) != codex_before
        )):
            raise Failure("Host/adapter/config changed during confirmation. Nothing signaled; run doctor again.")
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            for entry in Path("/proc").iterdir():
                if entry.name.isdigit() and int(entry.name) != pid:
                    try:
                        replacement = verified_process(int(entry.name), self.host)
                        try:
                            old_alive = verified_process(pid, self.host) == process
                        except (Failure, OSError):
                            old_alive = False
                        if (not old_alive and replacement[0] == process[0]
                                and (int(entry.name), replacement) not in existing):
                            print(f"Supervisor started host PID {entry.name}. Verify a new app message and fresh route logs.")
                            return
                    except (Failure, OSError):
                        pass
            time.sleep(0.5)
        raise Failure("Host was signaled, but a supervised replacement was not confirmed in 20s. Inspect supervisor logs; do not start a duplicate.")


def verified_process(pid, host):
    try:
        proc = Path("/proc") / str(pid)
        if pid <= 1 or proc.stat().st_uid != os.getuid():
            raise Failure("Host PID must belong to the current user.")
        args = (proc / "cmdline").read_bytes().decode().split("\0")
        if str(host) not in args or Path(args[0]).name not in {"node", "nodejs"}:
            raise Failure("PID is not the specified Node host process.")
        status = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        parent, start = int(status[1]), status[19]
        parent_proc = Path("/proc") / str(parent)
        parent_args = (parent_proc / "cmdline").read_bytes().decode().split("\0")
        if parent_proc.stat().st_uid != os.getuid() or not any(
            arg.endswith("/sand-supervisor.mjs") for arg in parent_args
        ):
            raise Failure("Host parent is not the expected same-user sand supervisor. Nothing signaled.")
        return parent, start
    except (FileNotFoundError, PermissionError, IndexError, ValueError):
        raise Failure("Cannot verify host PID and supervisor. Refresh the process list.") from None


def stop_runtime(process):
    """The CLI runtime and its native descendants share this isolated session."""
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=RUNTIME_STOP_GRACE)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # Kill the group even if its leader exited: a descendant can still hold
        # pipes open or continue native work. Never target the caller's group.
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=RUNTIME_STOP_GRACE)
        except subprocess.TimeoutExpired:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            process.wait(timeout=RUNTIME_STOP_GRACE)


def runtime_check(values, command, node=None):
    values = validate_config(values)
    executable = node or ("/exec-daemon/node" if Path("/exec-daemon/node").is_file() else shutil.which("node"))
    if not executable:
        raise Failure("Node is required for native subscription checks.")
    with tempfile.TemporaryDirectory(prefix="ungrok-auth-") as directory:
        config = Path(directory) / "subscription.env"
        atomic_write(config, encode_config(values))
        process = None
        try:
            process = subprocess.Popen([executable, str(ROOT / "vendor/subscription-runtime.cjs"), command, str(config)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=native_env(),
                                       start_new_session=os.name == "posix")
            stdout, _ = process.communicate(timeout=RUNTIME_TIMEOUTS[command])
            data = json.loads(stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            raise Failure("Native subscription check failed. Inspect the official CLI; diagnostic contents were withheld.") from None
        finally:
            if process is not None:
                stop_runtime(process)
        if process.returncode or not isinstance(data, dict) or data.get("ok") is not True or data.get("provider") != values["UNGROK_PROVIDER"]:
            raise Failure("Native subscription check failed. Run login and consult docs/providers.md; no API fallback is available.")
        if command == "probe" and data.get("sentinel") != "UNGROK_OK":
            raise Failure("Native probe did not return the exact test sentinel. Response contents were withheld.")
        if command == "status" and data.get("subscription") is not True:
            raise Failure("Subscription authentication was not verified; API authentication is unsupported.")


def probe(values, node=None):
    runtime_check(values, "probe", node)
    print("Native subscription probe passed: UNGROK_OK. This uses subscription allowance; live Grok Bot routing and tool support are NOT verified.")


def confirmation(yes):
    def ask(message):
        if yes:
            return
        if not sys.stdin.isatty() or input(message + " [y/N] ").lower() not in {"y", "yes"}:
            raise Failure("Cancelled. No changes applied.")
    return ask


def wizard_yes(message):
    return input(message + " [y/N] ").strip().lower() in {"y", "yes"}


def wizard_confirm(message):
    if not wizard_yes(message):
        raise Failure("Stopped at your request. Earlier completed steps are retained; run ./ungrok start to continue.")


def wizard_choice(message, choices, default):
    while True:
        answer = input(message + f" [{default}]: ").strip().lower() or default
        if answer in choices:
            return choices[answer]
        print("Choose " + ", ".join(choices) + ".")


def validated_client(provider, candidate):
    """Check npm package identity and exact executable version, without login."""
    package, version, _, expected = CLIENTS[provider]
    try:
        executable = resolve_cli(provider, candidate)
        resolved = Path(executable).resolve(strict=True)
        matched = False
        for parent in resolved.parents:
            manifest = parent / "package.json"
            if manifest.is_file() and manifest.stat().st_size < 65536:
                metadata = json.loads(read_regular(manifest))
                if isinstance(metadata, dict) and metadata.get("name") == package and metadata.get("version") == version:
                    matched = True
                    break
        if not matched:
            return None
        result = subprocess.run([executable, "--version"], env=native_env(),
                                capture_output=True, timeout=20)
        if result.returncode == 0 and result.stdout.decode().strip() == expected:
            return executable
    except (Failure, OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def wizard_client(provider, saved=None):
    package, version, command, _ = CLIENTS[provider]
    candidates = [saved, shutil.which(command)]
    base = Path.home() / ".local/share/ungrok/wizard-clients"
    if base.is_dir() and base.resolve() == base and base.stat().st_uid == os.getuid() and not base.stat().st_mode & 0o077:
        # Resume a prior completed download without trusting partial directories.
        previous = sorted(base.glob(f"{command}-{version}-*"), reverse=True)[:20]
        for prefix in previous:
            if prefix.is_dir() and not prefix.is_symlink() and prefix.stat().st_uid == os.getuid() and not prefix.stat().st_mode & 0o077:
                candidates.append(prefix / "node_modules/.bin" / command)
    for candidate in dict.fromkeys(item for item in candidates if item):
        executable = validated_client(provider, candidate)
        if executable:
            print(f"Found compatible {command} {version}.")
            return executable
    npm = shutil.which("npm")
    if not npm:
        raise Failure("npm is missing on this remote computer. Ask your setup helper to install a user-local Node/npm runtime using docs/providers.md, then run ./ungrok start again. Do not use sudo or replace Grok's Node runtime.")
    wizard_confirm(f"Download official {package}@{version} and its platform dependencies from registry.npmjs.org into a new private user-local folder? No sudo, global install, or package scripts will be used.")
    if base.resolve() != base:
        raise Failure("The user-local client directory has symlink components. Ask your setup helper to inspect it; nothing installed.")
    secure_dir(base)
    prefix = Path(tempfile.mkdtemp(prefix=f"{command}-{version}-", dir=base))
    print("Downloading the official client. This can take a few minutes.")
    env = native_env()
    env.update(NPM_CONFIG_USERCONFIG="/dev/null", NPM_CONFIG_GLOBALCONFIG="/dev/null")
    try:
        result = subprocess.run([npm, "install", "--prefix", str(prefix), "--ignore-scripts",
                                 "--no-audit", "--no-fund", "--registry=https://registry.npmjs.org",
                                 f"{package}@{version}"], env=env, cwd=prefix,
                                capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        raise Failure(f"Client download did not complete. Partial files remain at {prefix}; they will not be overwritten. Check network access and retry ./ungrok start.") from None
    executable = validated_client(provider, prefix / "node_modules/.bin" / command) if result.returncode == 0 else None
    if not executable:
        raise Failure(f"The downloaded client did not pass its exact-version check. Files remain at {prefix}; nothing was patched. Ask your setup helper to check Linux/Node compatibility in docs/providers.md.")
    return executable


def discover_host_pid(host):
    matches = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                verified_process(int(entry.name), host)
                matches.append(int(entry.name))
            except (Failure, OSError):
                pass
    if len(matches) != 1:
        raise Failure(f"Found {len(matches)} verified Grok host processes; expected exactly one. No process was signaled. Keep this terminal open and ask your setup helper to inspect the host/supervisor, then rerun ./ungrok start.")
    return matches[0]


def start(installation):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Failure("Open Grok Bot > Computer > Terminal and run ./ungrok start interactively. Piped or unattended setup is not supported. Nothing changed.")
    original = installation.preflight()
    if os.environ.get("CODEX_HOME") or os.environ.get("CLAUDE_CONFIG_DIR"):
        raise Failure("This terminal uses a custom CODEX_HOME or CLAUDE_CONFIG_DIR. The running Grok host may use a different sign-in profile. Ask your setup helper to align the terminal and supervisor profiles before continuing; nothing changed.")
    if not installation.is_current(original):
        patch_bytes(original, installation.config)
    saved = read_config(installation.config) if installation.config.exists() else {}
    python = shutil.which("python3")
    pillow = subprocess.run([python, "-c", "import PIL"], capture_output=True, timeout=10) if python else None
    if pillow is None or pillow.returncode:
        print("Image warning: the image helper cannot use Pillow from PATH python3. Most photos/screenshots may fail until your setup helper follows the optional image setup in docs/getting-started.md.")
    print("ungrok guided setup (experimental). This affects ALL bots on this remote computer.")
    print("You need your own supported Claude Pro/Max or ChatGPT subscription. Never paste a password, API key, or token here.")
    default = "2" if saved.get("UNGROK_PROVIDER") == "claude" else "1"
    provider = wizard_choice("Choose 1 = ChatGPT, 2 = Claude", {"1": "chatgpt", "2": "claude"}, default)
    model = saved.get("UNGROK_MODEL") if saved.get("UNGROK_PROVIDER") == provider else None
    print(f"Model: {model or 'official client default'}. Available models depend on your account.")
    selection = wizard_choice("Choose 1 = keep this setting, 2 = client default, 3 = custom model", {"1": "keep", "2": "default", "3": "custom"}, "1")
    if selection == "default":
        model = None
    elif selection == "custom":
        model = input("Enter an exact model name supported by your official client: ").strip()
        if not model:
            raise Failure("No model name entered. Run ./ungrok start again to choose the client default.")
    # Validate user input before downloads or login.
    values = {"UNGROK_PROVIDER": provider, "UNGROK_CLI": "/pending/client"}
    if model:
        values["UNGROK_MODEL"] = model
    validate_config(values)
    values["UNGROK_CLI"] = wizard_client(provider, saved.get("UNGROK_CLI") if saved.get("UNGROK_PROVIDER") == provider else None)
    try:
        runtime_check(values, "status", installation.node)
        print("Existing subscription sign-in verified.")
    except Failure:
        wizard_confirm("Subscription sign-in could not be verified. Open the official client's sign-in flow now? Complete it yourself in your browser.")
        login(provider, values["UNGROK_CLI"], installation.node)
    wizard_confirm("Run a small test prompt now? This uses a little of your subscription allowance.")
    try:
        probe(values, installation.node)
    except Failure as error:
        raise Failure(f"{error} This setup attempt has not changed the Grok host. Check your selected model/subscription, then rerun ./ungrok start.") from None
    pid = discover_host_pid(installation.host)
    wizard_confirm("Before changing this shared host, finish ALL active bot work and pause scheduled routines. If ungrok is already running, provider/model changes can affect new sessions immediately, before restart. Are all bots idle and routines paused?")
    installation.install(values, wizard_confirm)
    print("Settings installed on disk. If ungrok is already running, new sessions may already use these settings before restart. Keep bots idle and routines paused until restart and app verification are complete.")
    recovery = "Settings are installed on disk. If ungrok is already running, new sessions may already use them; otherwise a later restart can activate them. Keep bots idle and routines paused. Run ./ungrok start to retry, or ./ungrok rollback and follow its restart instructions to restore original routing."
    try:
        installation.restart(pid, wizard_confirm)
    except Failure as error:
        raise Failure(f"{error} {recovery}") from None
    except (OSError, subprocess.SubprocessError):
        raise Failure(f"Restart could not be confirmed. {recovery} Diagnostic contents were withheld.") from None
    except (KeyboardInterrupt, EOFError):
        raise Failure(f"Stopped after installation. {recovery}") from None
    print("Setup and supervised restart completed. Live app routing, tools, and images are NOT yet verified.")
    print("Return to Grok Bot and send a new message, then test a simple tool task and an image. Have your setup helper check fresh [ungrok] route logs. Do not call setup fully verified until those pass.")


def parser():
    home = Path.home()
    result = argparse.ArgumentParser(description="ungrok: bring your Claude or ChatGPT subscription to Grok Bot. Run in its remote Linux terminal.")
    result.add_argument("--version", action="version", version=VERSION)
    result.add_argument("--host-dir", default=str(home / "sand-host"))
    result.add_argument("--data-dir", default=str(home / "sand-data"))
    result.add_argument("--state-dir", default=str(home / ".local/state/ungrok"))
    result.add_argument("--node", default="/exec-daemon/node" if Path("/exec-daemon/node").is_file() else shutil.which("node"))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("start", help="guided interactive setup, sign-in, test, and confirmed restart")
    commands.add_parser("doctor", help="read-only file/config/layout checks; no network")
    auth = commands.add_parser("login", help="sign in through the official native subscription CLI")
    auth.add_argument("provider", choices=("claude", "chatgpt"))
    auth.add_argument("--cli", type=Path, help="absolute official CLI executable path")
    setup = commands.add_parser("setup", help="configure and patch; does not restart")
    setup.add_argument("--config", type=Path, help="private mode-600 subscription KEY=value file; legacy API config is refused")
    setup.add_argument("--provider", choices=("claude", "chatgpt"))
    setup.add_argument("--cli", type=Path, help="absolute official CLI executable path")
    setup.add_argument("--model", help="optional native model alias; otherwise the CLI default")
    setup.add_argument("--yes", action="store_true")
    for command in ("repair", "rollback"):
        child = commands.add_parser(command)
        child.add_argument("--yes", action="store_true")
    commands.add_parser("probe", help="test native inference with a synthetic prompt; uses subscription allowance")
    restart = commands.add_parser("restart", help="signal one verified supervised host PID")
    restart.add_argument("--pid", type=int, required=True)
    restart.add_argument("--yes", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    installation = Installation(args)
    try:
        if args.command == "start":
            start(installation)
        elif args.command == "doctor":
            installation.doctor()
        elif args.command == "login":
            login(args.provider, args.cli, installation.node)
        elif args.command == "setup":
            original = installation.preflight()
            if not installation.is_current(original):
                patch_bytes(original, installation.config)
            if args.config:
                if args.provider or args.cli or args.model:
                    raise Failure("Choose --config or --provider/--cli/--model, not both.")
                values = read_config(args.config.expanduser().absolute())
            else:
                provider = args.provider
                if not provider:
                    if not sys.stdin.isatty():
                        raise Failure("Choose --provider claude or --provider chatgpt, or use a private subscription --config file.")
                    provider = input("Subscription provider (claude/chatgpt): ").strip().lower()
                if provider not in {"claude", "chatgpt"}:
                    raise Failure("Choose claude or chatgpt.")
                values = {"UNGROK_PROVIDER": provider, "UNGROK_CLI": resolve_cli(provider, args.cli)}
                if args.model:
                    values["UNGROK_MODEL"] = args.model
                values = validate_config(values)
            installation.install(values, confirmation(args.yes))
        elif args.command == "repair":
            installation.install(read_config(installation.config), confirmation(args.yes))
        elif args.command == "probe":
            probe(read_config(installation.config), installation.node)
        elif args.command == "rollback":
            installation.rollback(confirmation(args.yes))
        elif args.command == "restart":
            installation.restart(args.pid, confirmation(args.yes))
        return 0
    except Failure as error:
        print(f"ungrok: {error}", file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError):
        print("ungrok: filesystem/runtime operation failed. Check permissions and paths. No diagnostic contents were printed.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nungrok: cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
