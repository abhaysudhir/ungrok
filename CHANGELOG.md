# Changelog

## 0.1.0 — experimental

- Add a standard-library CLI with `doctor`, interactive `setup`, `repair`, `probe`, supervised `restart`, and hash-checked `rollback`.
- Preserve fresh host backups and reject unknown layouts, foreign patches, and changed rollback targets.
- Derive the inference adapter from BlockedPath's MIT-licensed source, with explicit private configuration, fixed model selection, and no implicit Grok login fallback.
- Remove silent fallback from the injected hook and suppress sensitive provider error bodies.
- Add local fixture tests, CI, setup/recovery docs, and security reporting guidance.
- Preserve structured image content across consecutive user messages, deliver stream events as they arrive, and settle interrupted/cancelled requests instead of leaving them pending.

The hardened public release is not yet live end-to-end verified. See `docs/compatibility.md` for the evidence boundary.
