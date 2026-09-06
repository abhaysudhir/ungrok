# Historical compatibility repair

The 0.1 release included a hash-specific image/stream repair for the original BlockedPath/grok-bot-setup adapter. That repair preserved the original adapter's API transport; it does not implement native subscription sign-in and is not part of the 0.2 setup path.

For provenance or recovery of an exact historical install, see the [v0.1.0-rc.2 compatibility archive](https://github.com/abhaysudhir/ungrok/tree/v0.1.0-rc.2/compat). Its tests and September 5, 2026 live results apply only to that historical adapter, not to the native runtime.

Do not apply the archived patch to a new install. To migrate, first use the old checkout's verified same-version rollback, then follow [native migration](../docs/updates.md). Never restore an old host backup across an upstream update.
