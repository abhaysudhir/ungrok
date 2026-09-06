# Compatibility and evidence

**0.2.0-alpha.1 implements both native subscription paths. Linux Grok Bot host end-to-end verification is pending.** Real local native probes have passed with the exact clients below. Old adapter results do not certify this version.

| Path | Evidence boundary |
| --- | --- |
| Claude through official Claude Code 2.1.263 | Four of five real local checks passed: text, synthetic tool proposal, two binary images, and image follow-up. Tool-result follow-up was refused by provider safeguards and remains incomplete. Pro/Max auth required. |
| ChatGPT through official Codex 0.153.4 | All five real local native adapter cases passed: text, tool proposal, tool-result follow-up, two binary images, and image follow-up. No real Grok tool executed. |
| Installer, repair, restart, rollback | Automated fixture checks pass; installation and recovery on a real compatible Linux Grok host remain unverified. |
| Host tools, cancellation, and steering in the app | Native synthetic checks above do not establish actual Grok tool execution or in-app cancellation/steering. |
| Billing and every background/voice path | Not verified; no zero-charge guarantee. |

The optional five-case script's ChatGPT run passed. Claude's run stopped at a provider safeguard on tool-result follow-up. Separate image checks then passed: two actual binary images were identified in order, and an image follow-up answered correctly. The refused case was not retried, rephrased, or routed to another model. This does not establish that every follow-up fails or authorize bypassing safeguards. Neither script nor local client success verifies a Linux Grok host installation or executes real Grok tools.

Native steps are stateless and buffer the structured response before delivering text/tool results. This alpha does not promise real-time token streaming. Fresh client startup can add latency and consume subscription allowance on each host step.

Use a compatible remote Linux host, its owner's account, original Node runtime, and the selected official client. Path overrides cannot make unsupported internals safe.

Terminal probes do not verify the supervised host's environment. The native client may need Node on its execution PATH, and the image helper resolves `python3` from the host's PATH. A dependency installed only in an interactive shell may pass setup checks but fail in the app. Runtime-environment parity remains part of the pending clean-host verification.

Configuration uses `UNGROK_PROVIDER=claude|chatgpt`, absolute `UNGROK_CLI`, and optional `UNGROK_MODEL`. No API credential, endpoint, token import, or fallback route is supported. See [sign-in](providers.md) and [architecture](architecture.md).

## Images and uploads

Binary PNG inputs passed real local checks through both clients. Byte-format conversion, context retention, and bounded request-only resizing have automated coverage. This does not verify every image format or attachment workflow in the Grok app. Originals remain unchanged.

Desktop uploads happen before inference. The inspected desktop 0.43.0 uploaded files sequentially in 4 MiB chunks with a 120-second batch commit deadline. This version-specific observation can explain a pre-inference stall; changing the provider does not repair that transport.

## Historical evidence

The superseded compatibility repair had narrow live text, follow-up, and image results on September 5, 2026. It retained an older configuration/authentication path. [Historical record](../compat/README.md)

Those are regression cases, not native runtime, permission, or billing verification.

## Reports

Record the exact commit, native-client version, host layout, and checks actually performed. Separate probes from app tests. Use sanitized errors and synthetic content. Never publish auth files, raw conversations, full logs, private backups, or proprietary host bundles.
