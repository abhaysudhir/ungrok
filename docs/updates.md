# Updates and recovery

Computer updates can remove the host patch, installed packages, or the adapter. Treat each update as a new compatibility check. ungrok does not automatically reinstall itself or guarantee routing while an update is in progress.

The Grok Bot update notice says files and logins stay, installed apps and packages are removed, and all assistants update together. Verify what survived rather than assuming credentials or local files remain usable. **Reset** is a different operation: its notice says the computer is rebuilt from the last saved snapshot, which can lose recent changes.

## Before updating

1. Finish active bot work and pause routines through the app where possible.
2. Keep a copy of the ungrok source or its reviewed commit identifier outside the remote computer.
3. Keep provider configuration and recovery material in private storage. Never add credentials or host backups to a public repository.
4. Allow for downtime. Avoid new bot requests after the update until routing is verified. A stock host can use the default provider.

Updating the Mac desktop app and updating the shared remote computer are separate operations. ungrok changes the remote host; it does not modify the Mac app bundle.

## Migrating an existing provider patch

ungrok refuses hosts containing an existing `createXaiPromptSession` hook, including the earlier upstream `xai` patch. The error is `Host already has a provider patch. Inspect it; do not stack patches. See docs/updates.md.` Renaming files or deleting the hook marker does not make migration safe.

Start with a verified stock host for the **current** computer version. If the previous installer has a proven same-version rollback, use its documented recovery procedure and verify the result. An old `host-main.cjs.cursor-bak` may belong to a different version; do not restore it blindly. If you cannot establish the backup's provenance, obtain a fresh stock host through the app's supported computer-update/recovery process before running ungrok. That process may remove packages and interrupt every bot.

Keep prior credentials and provider configuration private. ungrok does not import upstream `xai-inference.env` or subscription credentials automatically. Configure an authorized endpoint through `setup`. It writes its own `ungrok.env` and `ungrok-session.cjs`, leaving the old upstream session module untouched.

Avoid new requests while moving between stock and custom routing. A stock host can use the default provider, and ungrok cannot apply a billing guard during migration.

## After updating

Open **Computer → Terminal** in Grok Bot. Return to the ungrok checkout and run:

```sh
./ungrok doctor
```

If the checkout was removed, download the reviewed source again. If the runtime, configuration, or provider service is missing, restore that prerequisite first. Repair does not install a proxy, recover credentials, or authenticate your provider.

For large inline images, also check that Pillow remains installed for the host's `python3`. Computer updates can remove that package even if the resize helper file survives. Restore it from the reviewed `requirements-images.txt`; `doctor` reports Pillow availability, but a text-only endpoint probe does not test image resizing.

If the current host layout is compatible and your saved ungrok configuration is intact:

```sh
./ungrok repair --yes
./ungrok probe
```

Repair reuses the saved configuration, checks the current host, and creates a fresh backup before patching. It does not restart the host. If configuration is gone, use [setup](getting-started.md) instead.

Stop on an unsupported or ambiguous host layout. Never copy an older patched `host-main.cjs` over a new host release or force an insertion past a failed check. A syntax check alone cannot establish runtime compatibility.

Inspect the current process and restart through ungrok, replacing `HOST_PID` with the verified numeric PID:

```sh
pgrep -af 'host-main.cjs'
./ungrok restart --pid HOST_PID --yes
```

Do not reuse a PID from before the update. Follow the [fresh app request and log verification](getting-started.md#6-verify-from-grok-bot) before resuming work. Re-test the tools you depend on.

## Roll back

```sh
./ungrok rollback --yes
```

Rollback restores the recorded pre-install host for the installed version only when its recorded hashes match the expected state. It refuses a tampered or subsequently updated host. Re-running setup on an intact installation retains that original rollback target. Private configuration, adapter, and backups remain in place; no credentials are deleted. Restarting remains a separate operation:

```sh
pgrep -af 'host-main.cjs'
./ungrok restart --pid HOST_PID --yes
```

If rollback refuses, preserve the files and inspect the mismatch. Do not substitute an old host backup just to get past the check.

Restoring stock host code resumes the stock inference path. **Rollback does not stop provider usage or guarantee zero charges.** The app's selected model may need to be changed to one its stock route supports.

## Updating ungrok itself

Keep the checkout used for the active installation until you finish rollback. If a newer checkout contains a different adapter, setup refuses to replace the installed version and tells you to roll back using the installed version first.

Pause work, use the original checkout to roll back, then inspect and install the new checkout against the restored stock host. Probe, restart separately, and verify a fresh app request. Do not bypass adapter-hash checks or delete installation records to force an upgrade.

## What remains uncertain

Host internals can change without a matching desktop version change. A supported insertion point is only a prerequisite. Future updates may change session APIs, streaming, tools, authentication, or supervision in ways a text check cannot detect.

See the [compatibility record](compatibility.md) for the distinction between the historical upstream repair and the new ungrok implementation.
