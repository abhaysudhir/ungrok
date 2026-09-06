# Changelog

## 0.1.0-rc.1 (prerelease)

- Add a standard-library CLI with `doctor`, interactive `setup`, `repair`, `probe`, supervised `restart`, and hash-checked `rollback`.
- Preserve fresh host backups and reject unknown layouts, foreign patches, and changed rollback targets.
- Derive the inference adapter from BlockedPath's MIT-licensed source, with explicit private configuration, fixed model selection, and no implicit Grok login fallback.
- Remove silent fallback from the injected hook and suppress sensitive provider error bodies.
- Add local fixture tests, CI, setup/recovery docs, and security reporting guidance.
- Preserve structured image content across consecutive user messages, deliver stream events as they arrive, and settle interrupted/cancelled requests instead of leaving them pending.
- Resize large inline request-image copies in memory with optional Pillow; enforce per-image and final request limits without changing original files.
- Keep up to 20 recent images outside the text character budget and preserve the latest real request through tool/follow-up turns.
- Reject malformed images, unfinished or malformed streams, and invalid tool arguments instead of dropping content or reporting success.
- Preserve confirmation-time edits, validate recovery records and backups, and retain prior helper/adapter copies for failed-install recovery.
- Add repeatable source-archive packaging with SHA-256 checksums and correct the banner's plug mark.
- Document separate narrow live results for the legacy compatibility repair. These do not establish live coverage of the hardened installer or adapter.

The hardened new-install path is not yet live end-to-end verified. See [compatibility and evidence](docs/compatibility.md) for release limits. This is a release candidate, not stable support.
