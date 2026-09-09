# Compatibility and evidence

**0.2.0-alpha.1 implements both native subscription paths. Linux Grok Bot host end-to-end verification is pending.** Real local native probes have passed with the exact clients below. Old adapter results do not certify this version.

## Grok Bot version

Earlier live compatibility work used **Grok Bot 0.43.0** on **September 5, 2026**. The same legacy installation was then tested on desktop **0.44.0** on **September 6**, with a routing repair and fresh text/tool verification on **September 9**. See the incident record below and the [older archived test record](https://github.com/abhaysudhir/ungrok/blob/v0.1.0-rc.2/docs/compatibility.md#test-status).

Those results apply to the previous integration, not the current native-subscription installer or bot-led setup. **No Grok Bot version is yet certified by a complete live test of the current setup path.** The desktop version also does not identify the separately updated remote host bundle; future reports must record both the app version and host compatibility evidence.

## Current integration checks

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

### September 2026 legacy host incident

This record concerns the previous API-based adapter, **not 0.2.0-alpha.1**, its native clients, or its installer/repair commands.

| Date | Observed result | What it establishes |
| --- | --- | --- |
| September 6, desktop 0.44.0 | Text, terminal results, one image, and image follow-up passed. Bot-reported file hashes matched an independent terminal check. | The running legacy integration worked after a desktop upgrade. It did not prove a clean install, restart survival, or zero Grok usage. |
| September 9, desktop 0.44.0 | The remote host bundle had changed. Its on-disk custom hook and installed adapter were absent; saved provider source and settings remained. | Desktop version alone does not identify the remote runtime. Old custom-route logs are insufficient evidence for the current process. |
| September 9, manual repair | The old repair script rejected the changed call site. A minimal routing patch and colocated image helper were restored, syntax-checked, and loaded through a verified host restart. A fresh app request passed text/tool checks and produced new custom-provider session logs. | Recovery was verified on that specific legacy host. The current native installer's repair path was not tested. Images were not retested in this repair session. |

The September 6 archived host also lacked the static hook. The earlier test therefore verified running-process behavior, not that the hook on disk would survive the next restart. The September 9 repair checked both installed files and a fresh process. It did not install an automatic repair watchdog; later managed host updates can remove the customization again.

**Billing remains a separate, unresolved question.** Displayed account usage was unchanged during the short repair test. That observation does not attribute prior usage or exclude delayed accounting. The legacy adapter returns token usage to the host, and the host records turn usage. The server-side weekly calculation was not established. No accounting fields, quota controls, billing settings, or routines were changed.

[Cursor's billing documentation](https://cursor.com/help/grok-bot/plans) says Grok Bot usage is metered on the Cursor account and shared between desktop and iOS. Do not promise that selecting a different inference provider stops that meter, refunds recorded usage, or avoids charges for every Grok path.

## Reports

Record the exact commit, native-client version, host layout, and checks actually performed. Separate probes from app tests. Use sanitized errors and synthetic content. Never publish auth files, raw conversations, full logs, private backups, or proprietary host bundles.
