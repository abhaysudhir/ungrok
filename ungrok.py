#!/usr/bin/env python3
"""A reversible Grok Bot host mod. Python standard library only."""
from __future__ import annotations

import argparse
import contextlib
import getpass
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
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0-rc.1"
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
KEYS = {"SAND_XAI_BASE_URL", "SAND_XAI_MODEL", "XAI_API_KEY", "SAND_XAI_THINKING"}


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
    missing = {"SAND_XAI_BASE_URL", "SAND_XAI_MODEL", "XAI_API_KEY"} - values.keys()
    if missing:
        raise Failure("Missing provider fields: " + ", ".join(sorted(missing)))
    for key, value in values.items():
        if key not in KEYS or not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise Failure("Invalid or unsupported provider field; use the example configuration.")
        if value != value.strip() or value.startswith(("'", '"')) or value.endswith(("'", '"')):
            raise Failure("Provider values must not contain outer quotes or whitespace.")
        if len(value.encode("utf-8")) > 16384:
            raise Failure("Provider field exceeds the 16 KiB limit.")
    try:
        if any(c.isspace() for c in values["SAND_XAI_BASE_URL"]):
            raise ValueError("Whitespace in endpoint")
        base = urllib.parse.urlsplit(values["SAND_XAI_BASE_URL"])
        port = base.port
    except ValueError:
        raise Failure("Invalid endpoint URL.") from None
    del port
    if not base.hostname or base.username is not None or base.password is not None or base.query or base.fragment:
        raise Failure("Endpoint needs a hostname and cannot contain credentials, a query, or a fragment.")
    if base.scheme != "https" and not (
        base.scheme == "http" and base.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise Failure("Use HTTPS, or HTTP on localhost/127.0.0.1/::1 for a local proxy.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}", values["SAND_XAI_MODEL"]):
        raise Failure("Invalid model identifier. Use the provider's model ID, not a display name.")
    if values.get("SAND_XAI_THINKING", "disabled") != "disabled":
        raise Failure("v0.1 supports SAND_XAI_THINKING=disabled only.")
    return dict(values, SAND_XAI_THINKING="disabled")


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
                        "adapter_sha256", "image_helper_sha256"}
            if not isinstance(info, dict) or not required.issubset(info) or any(
                not isinstance(info[key], str) or not info[key] for key in required
            ) or any(not re.fullmatch(r"[0-9a-f]{64}", info[key]) for key in required if key.endswith("_sha256")):
                raise Failure("Invalid installation record. Inspect private backups before proceeding.")
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
        if info and digest(image_helper) != info.get("image_helper_sha256"):
            raise Failure("Image helper version differs from installation. Roll back with the installed checkout before upgrading.")
        if not info and self.image_helper.exists():
            previous = self.load_manifest()
            if digest(read_regular(self.image_helper)) != previous.get("image_helper_sha256"):
                raise Failure("Existing image helper is not the recorded ungrok version. Nothing changed.")
        values = validate_config(values)
        self.syntax(candidate, "patched host")
        self.syntax(vendor, "provider adapter")
        watched = (self.adapter, self.image_helper, self.config, self.manifest)
        before = {path: (read_regular(path), stat.S_IMODE(path.stat().st_mode))
                  if path.exists() or path.is_symlink() else None for path in watched}
        confirm("This changes the shared host for ALL bots. Prompts and tool results go to your endpoint. Continue?")
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
            targets = [(self.adapter, vendor, 0o600), (self.image_helper, image_helper, 0o600), (self.config, encode_config(values), 0o600),
                       (self.host, candidate, stat.S_IMODE(self.host.stat().st_mode))]
            old = {}
            for target, _, _ in targets:
                old[target] = (read_regular(target), stat.S_IMODE(target.stat().st_mode)) if target.exists() else None
                if target == self.config and old[target]:
                    atomic_write(backup / "provider.env", old[target][0])
                elif target in (self.adapter, self.image_helper) and old[target]:
                    atomic_write(backup / target.name, old[target][0])
            record = info or {
                "version": VERSION, "host": str(self.host), "config": str(self.config),
                "backup": str(backup / "host-main.cjs"), "original_sha256": digest(original),
                "patched_sha256": digest(candidate), "adapter_sha256": digest(vendor), "image_helper_sha256": digest(image_helper),
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
            self.syntax(original, "installed host")
            self.syntax(read_regular(self.adapter), "installed adapter")
            state = "Installed files match recorded hashes."
        else:
            patch_bytes(original, self.config)
            state = "Known host insertion point found; ungrok is not installed."
        print(state)
        if self.config.exists():
            values = read_config(self.config)
            base = urllib.parse.urlsplit(values["SAND_XAI_BASE_URL"])
            print(f"Provider config valid: model={values['SAND_XAI_MODEL']} endpoint={base.scheme}://{base.netloc}")
        else:
            raise Failure("No ungrok provider configuration. Run setup. No network request was made.")
        print("Read-only check. Provider access and live app routing are NOT verified.")
        image_runtime = subprocess.run([sys.executable, "-c", "import PIL"], capture_output=True, timeout=10)
        print("Pillow available for image resizing." if image_runtime.returncode == 0 else
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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(values):
    values = validate_config(values)
    body = json.dumps({"model": values["SAND_XAI_MODEL"], "stream": False, "max_tokens": 32,
                       "messages": [{"role": "user", "content": "Reply exactly UNGROK_OK"}]}).encode()
    request = urllib.request.Request(values["SAND_XAI_BASE_URL"].rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + values["XAI_API_KEY"]})
    # Do not inherit machine-wide HTTP proxies that might receive local proxy credentials.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise Failure("Provider response exceeded probe limit.")
            data = json.loads(raw)
        text = data["choices"][0]["message"]["content"]
        if not isinstance(text, str) or text.strip() != "UNGROK_OK":
            raise Failure("Provider replied, but not with the exact test sentinel. Response body was not printed.")
    except urllib.error.HTTPError as error:
        raise Failure(f"Provider probe returned HTTP {error.code}. Body withheld; check endpoint, model, and credentials.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise Failure("Provider probe could not connect. Check the endpoint/proxy; no credentials were printed.") from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise Failure("Provider response was not compatible Chat Completions JSON. Body withheld.") from None
    print("Provider probe passed: UNGROK_OK. This tests the endpoint, not Grok Bot routing or tool support.")


def confirmation(yes):
    def ask(message):
        if yes:
            return
        if not sys.stdin.isatty() or input(message + " [y/N] ").lower() not in {"y", "yes"}:
            raise Failure("Cancelled. No changes applied.")
    return ask


def parser():
    home = Path.home()
    result = argparse.ArgumentParser(description="ungrok: bring your own model to Grok Bot. Run in its remote Linux terminal.")
    result.add_argument("--version", action="version", version=VERSION)
    result.add_argument("--host-dir", default=str(home / "sand-host"))
    result.add_argument("--data-dir", default=str(home / "sand-data"))
    result.add_argument("--state-dir", default=str(home / ".local/state/ungrok"))
    result.add_argument("--node", default="/exec-daemon/node" if Path("/exec-daemon/node").is_file() else shutil.which("node"))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="read-only file/config/layout checks; no network")
    setup = commands.add_parser("setup", help="configure and patch; does not restart")
    setup.add_argument("--config", type=Path, help="private mode-600 KEY=value file; never pass keys as arguments")
    setup.add_argument("--yes", action="store_true")
    for command in ("repair", "rollback"):
        child = commands.add_parser(command)
        child.add_argument("--yes", action="store_true")
    commands.add_parser("probe", help="send a synthetic prompt to the configured endpoint; may incur provider cost")
    restart = commands.add_parser("restart", help="signal one verified supervised host PID")
    restart.add_argument("--pid", type=int, required=True)
    restart.add_argument("--yes", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    installation = Installation(args)
    try:
        if args.command == "doctor":
            installation.doctor()
        elif args.command == "setup":
            original = installation.preflight()
            if not installation.is_current(original):
                patch_bytes(original, installation.config)
            if args.config:
                values = read_config(args.config.expanduser().absolute())
            else:
                if not sys.stdin.isatty():
                    raise Failure("Interactive setup needs a terminal. Or use --config /private/provider.env --yes.")
                print("All bots sharing this computer will send prompts and tool output to the endpoint you choose.")
                print("Use an authorized OpenAI-compatible API endpoint. No subscription logins are imported.")
                values = validate_config({"SAND_XAI_BASE_URL": input("Base URL, including /v1 if required: ").strip(),
                                          "SAND_XAI_MODEL": input("Provider model ID: ").strip(),
                                          "XAI_API_KEY": getpass.getpass("API key or local proxy key, hidden: ")})
            installation.install(values, confirmation(args.yes))
        elif args.command == "repair":
            installation.install(read_config(installation.config), confirmation(args.yes))
        elif args.command == "probe":
            probe(read_config(installation.config))
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
