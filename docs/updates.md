# Updates, migration, and rollback

Keep the exact installed checkout and private current-version backup. Computer updates can replace the hook or remove native clients. A surviving login file does not prove usable authentication.

Before updating, finish active work, pause routines, and keep recovery instructions outside the computer. Expect downtime. Avoid requests until routing is verified; stock Grok routing may resume if the hook disappears. Computer Reset is not a routine repair step.

## After an update

Run `./ungrok doctor` in the remote terminal. Check current host compatibility, native executable/version, subscription auth, and configuration.

Reinstall missing clients through official methods with approval. Complete their own sign-in if necessary. Do not recover access by pasting tokens into ungrok.

After checks pass, run `./ungrok repair --yes` with shared-host consent, then `./ungrok probe`. Restart separately when idle and repeat real app verification. Stop on unknown layouts, changed hashes, auth failure, or unsupported native runtimes.

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
