# Updates, migration, and rollback

Keep the exact installed checkout and private current-version backup. Computer updates can replace the hook or remove native clients. A surviving login file does not prove usable authentication.

Before updating, finish active work, pause routines, and keep recovery instructions outside the computer. Expect downtime. Avoid requests until routing is verified; stock Grok routing may resume if the hook disappears. Computer Reset is not a routine repair step.

## After an update

First identify the installed integration. The commands in this section apply to the current native alpha, not a legacy API-based host. Do not run the current installer over a foreign hook or copy an old host bundle over a new one.

Run `./ungrok doctor` in the remote terminal. Check current host compatibility, native executable/version, subscription auth, and configuration. Inspect the installed hook and adapter even if the app still replies: a process may retain previously loaded code after files on disk have been replaced.

Reinstall missing clients through official methods with approval. Complete their own sign-in if necessary. Do not recover access by pasting tokens into ungrok.

After checks pass, run `./ungrok repair --yes` with shared-host consent, then `./ungrok probe`. Restart separately when idle and repeat real app verification. Stop on unknown layouts, changed hashes, auth failure, or unsupported native runtimes.

Record the old and new host PIDs and confirm a fresh request produces a new provider-route log after restart. Historical log lines, a surviving login, unchanged desktop version, or one successful pre-restart chat do not prove the integration survived. Keep routines paused until those checks pass.

The [September 9 legacy incident](compatibility.md#september-2026-legacy-host-incident) required a manual adaptation because the old repair script no longer matched the host call site. That specific recovery is not a general repair recipe or evidence that the native alpha supports the same host. No automatic update-survival mechanism was verified.

## If Grok usage increases

Check account usage and current routing separately. Record a baseline, inspect installed files, and correlate one bounded test with fresh route logs. Check scheduled work without assuming it is unwanted or pausing it without authorization. A missing hook can restore stock routing, but an increasing meter alone does not prove fallback.

Preserve usage reporting and billing controls. Restoring custom routing does not erase recorded usage or guarantee a flat weekly meter. A brief unchanged reading can reflect delayed reporting. See [billing evidence and limits](compatibility.md#september-2026-legacy-host-incident).

## Migration from 0.1 or upstream

The native alpha is a different inference and configuration path. Do not stack it over old hooks, import old credentials, or keep a proxy as the native route.

Use the original installer's verified same-version rollback to obtain a stock current host. If backup provenance is unknown, stop and inspect supported recovery options. Never restore `host-main.cjs.cursor-bak` blindly after a computer update.

The CLI refuses legacy API configuration even when new provider flags are supplied. Roll back using the **old release's checkout** first. Then privately move the old `ungrok.env` out of the active data directory, preserving it for recovery without printing its contents. Inspect the exact file and destination before moving it. The new CLI does not automatically migrate or delete keys.

Install the reviewed native alpha and sign in through the official client. Cleanup of historical credentials or proxies is a separate action and is not required merely to inspect the native alpha.

## Rollback

When current host and recorded backup hashes match:

```sh
./ungrok rollback --yes
```

Restart the verified host separately when idle. Stock routing resumes. Rollback neither stops all provider usage nor deletes native provider credentials.

If hashes differ, preserve files and investigate. Do not force a cross-version restore. Keep the old checkout until recovery is complete when upgrading ungrok itself.
