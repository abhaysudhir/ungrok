<p align="center"><img src="assets/banner.svg" alt="ungrok: your bots, your subscriptions" width="920" /></p>

# ungrok

**Bring your Claude or ChatGPT subscription to Grok Bot.**

Use the official Claude Code or Codex client on Grok Bot's shared computer. Sign-in stays in the native client. You keep the Grok Bot app and its host-managed tools.

> **0.2.0-alpha.1 is an implemented native-client alpha, not a stable release.** Codex **0.153.4** passed all five local subscription checks. Claude Code **2.1.263** passed four: text, tool proposal, two images, and image follow-up. A provider safeguard refused its tool-result follow-up; that check remains incomplete. Linux Grok host end-to-end testing is still pending. Other client versions are refused. [Current evidence](docs/compatibility.md)

[Get started](docs/getting-started.md) · [Subscription sign-in](docs/providers.md) · [Ask an assistant to help](docs/agent-setup.md) · [Recovery](docs/updates.md)

## Subscription-only

No API key, token proxy, or API fallback. The official client owns login and credential refresh on the remote computer. A login on your Mac does not automatically sign in Grok Bot's computer.

Your subscription's model access and usage limits still apply. Review extra-usage settings before enabling routines. ungrok is not a spending cap or a guarantee of zero Grok charges. [Provider instructions and policy sources](docs/providers.md)

## How it works

Grok Bot's host sends inference through the native client. The adapter translates the result back into Grok's existing session interface. **Grok remains the tool executor.** Native tools must be disabled by enforced runtime controls, not merely by a prompt. Unsupported runtimes remain blocked. [Architecture](docs/architecture.md)

This changes the shared remote host for all bots. The Mac app is untouched. Finish active work and pause routines before a restart.

## Start with the guide

Use the [v0.2.0-alpha.1 release](https://github.com/abhaysudhir/ungrok/releases/tag/v0.2.0-alpha.1). The older 0.1 release used a superseded design.

Run commands inside **Grok Bot → Computer → Terminal**, not your Mac terminal. Follow the [pinned native-client install](docs/providers.md#install-the-exact-native-clients) first. Use its explicit executable path for login and setup so an older PATH entry is not selected. The Claude flow is:

```sh
./ungrok doctor
./ungrok login claude --cli "$ungrok_clients/node_modules/.bin/claude"
./ungrok setup --provider claude --cli "$ungrok_clients/node_modules/.bin/claude"
./ungrok probe
```

Read each result and stop on failed checks. Setup does not restart the host. A probe tests the native client, not app routing, tools, or images. The [walkthrough](docs/getting-started.md) covers consent, restart, and real app verification.

For ChatGPT, use `./ungrok login chatgpt` and `./ungrok setup --provider chatgpt` with Codex **0.153.4**. Claude requires **2.1.263**. Do not weaken version checks or substitute another billing route if refused.

The optional [native verification script](docs/getting-started.md#optional-native-adapter-check) exercises synthetic text, tool proposals/results, and images. It uses subscription quota and does not patch or verify a Grok host.

## Updates and rollback

Computer updates can remove the hook or native client. Keep the exact checkout and private current-version backup. Repair only a compatible host, restart separately when idle, and verify the app again. Rollback refuses mismatched host versions and does not delete your provider login. [Recovery guide](docs/updates.md)

## Contribute

Use synthetic fixtures and fake native clients for tests. Live tests require the owner's permission. See [CONTRIBUTING.md](CONTRIBUTING.md), [release checks](docs/release-checklist.md), and [SECURITY.md](SECURITY.md).

Earlier work derives from BlockedPath's MIT-licensed adapter. [Provenance](vendor/UPSTREAM.md) separates that historical code from this overhaul.

Unofficial. Not affiliated with xAI, Cursor, Anthropic, or OpenAI.
