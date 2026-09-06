# Provenance

The historical `xai-prompt-session.cjs` derives from [BlockedPath/grok-bot-setup](https://github.com/BlockedPath/grok-bot-setup), commit `d9119f9632c635473213c57ace336028f7278abd`, file `xai-prompt-session.cjs` (Git blob `e3fe55b30e294248474dc27f0621565009473622`). Its MIT notice remains in [LICENSE](LICENSE).

The superseded 0.1 design added explicit configuration, request bounds, image/context fixes, streaming/cancellation, and hash-checked recovery over an API-compatible transport.

0.2.0-alpha.1 moves inference to official native Claude Code/Codex clients. They own the user's subscription sign-in. It must not reuse the older credential-discovery/proxy path. Config selects provider, native executable, and optional model.

Grok remains the tool executor. Native tools must be disabled and structured responses validated. See [architecture](../docs/architecture.md) and [evidence](../docs/compatibility.md).

Historical source and compatibility patches are not recommended onboarding. Their live results do not certify native permissions, authentication, billing, or host compatibility.

## OpenClaw design reference

The native runtime policy was informed by OpenClaw's official-client integration, particularly its isolated Claude side-question execution path and Codex app-server policy. Reviewed commit: `b8cbece8fb8de577d9ff33cedf8d8250585c55e4`. References: [Anthropic CLI policy source](https://github.com/openclaw/openclaw/blob/b8cbece8fb8de577d9ff33cedf8d8250585c55e4/extensions/anthropic/cli-shared.ts), [Codex app-server policy source](https://github.com/openclaw/openclaw/blob/b8cbece8fb8de577d9ff33cedf8d8250585c55e4/extensions/codex/src/app-server/app-server-policy.ts), and [MIT license](https://github.com/openclaw/openclaw/blob/b8cbece8fb8de577d9ff33cedf8d8250585c55e4/LICENSE).

This is design provenance, not a claim that ungrok inherits OpenClaw's compatibility or verification. Any copied code must retain the applicable MIT notice; runtime behavior must be tested independently against the exact client versions used here.
