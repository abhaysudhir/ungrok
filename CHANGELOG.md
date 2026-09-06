# Changelog

## 0.2.0-alpha.1 (subscription-only alpha)

- Replace active API-compatible onboarding with subscription sign-in through official Claude Code or Codex clients.
- Configure only native provider, executable path, and optional model. Refuse legacy API configuration rather than importing or deleting credentials.
- Add native login and synthetic-probe commands. Keep doctor read-only and offline.
- Keep Grok's host as the tool executor; gate native runtimes until inference-only isolation is proven.
- Rewrite setup, assistant-guided onboarding, recovery, and security documentation around the native path.

Both native paths are implemented for Claude Code 2.1.263 and Codex 0.153.4. Codex passed all five local subscription checks. Claude passed text, tool proposal, two binary images, and image follow-up; provider safeguards refused tool-result follow-up, which remains incomplete. Linux Grok host end-to-end verification has not been completed. Earlier compatibility results do not certify this overhaul.

## Historical releases

The API-based design below is superseded. These notes describe previous releases, not current setup instructions.

## 0.1.0-rc.2 (prerelease)

- Start onboarding from the Grok Bot app and explain its remote computer in plain language.
- Add a copy-paste coding-assistant setup guide with private credential entry and verification steps.
- Add a no-proxy OpenRouter walkthrough and an optional, supervised LiteLLM proxy setup for Anthropic API access.
- Explain setup values, separate API billing, and technical terms; make terminal prompts clearer.
- Keep the same installer and adapter behavior as rc.1. The proxy recipe is documented from official sources, not claimed as live end-to-end verified.

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
