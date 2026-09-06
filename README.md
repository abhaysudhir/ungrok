<p align="center"><img src="assets/banner.svg" alt="ungrok: your bots, your subscriptions" width="920" /></p>

# ungrok

**Bring your Claude or ChatGPT subscription to Grok Bot.**

Use the official Claude Code or Codex client on Grok Bot's shared computer. Sign-in stays in the native client. You keep the Grok Bot app and its host-managed tools.

> **Early access:** Claude and ChatGPT support is implemented. Fresh-install testing is still underway, and Claude tool-result follow-up remains unverified. [Current evidence and supported versions](docs/compatibility.md)

[Guided setup](docs/easy-setup.md) · [Manual setup](docs/getting-started.md) · [Subscription sign-in](docs/providers.md) · [Ask an assistant to help](docs/agent-setup.md) · [Recovery](docs/updates.md)

## Guided setup in development

The working source adds `./ungrok start`: choose a subscription, follow official sign-in, and approve installation and restart in one guided flow. It handles client paths and host process discovery. Existing safety checks remain in place.

**This command is not in the published alpha archive yet.** See [guided setup](docs/easy-setup.md) for prerequisites and the final app checks that still need a person or setup assistant. This is not a claim that every Grok computer is supported.

## Subscription-only

No API key, token proxy, or API fallback. The official client owns login and credential refresh on the remote computer. A login on your Mac does not automatically sign in Grok Bot's computer.

Your subscription's model access and usage limits still apply. Review extra-usage settings before enabling routines. ungrok is not a spending cap or a guarantee of zero Grok charges. [Provider instructions and policy sources](docs/providers.md)

## How it works

Grok Bot's host sends inference through the native client. The adapter translates the result back into Grok's existing session interface. **Grok remains the tool executor.** Native tools must be disabled by enforced runtime controls, not merely by a prompt. Unsupported runtimes remain blocked. [Architecture](docs/architecture.md)

This changes the shared remote host for all bots. The Mac app is untouched. Finish active work and pause routines before setup or configuration changes, not just before restart. Existing installations can use changed settings for new sessions immediately.

## Getting Started

### Prerequisites

Before you begin, make sure you have:

- **Grok Bot installed and signed in.** ungrok modifies an existing Grok Bot computer; it does not install or replace the app.
- **Active Grok Bot access**, through an eligible Cursor plan or linked subscription. You do not necessarily need a separate Cursor subscription. See [Grok Bot plans and access](https://cursor.com/help/grok-bot/plans).
- **Your own Claude or ChatGPT subscription** for the provider you want to use. Claude requires Pro or Max; ChatGPT requires subscription access supported by the pinned Codex client. Complete sign-in through the official client, never by pasting credentials into chat.
- **Access to Grok Bot → Computer → Terminal** on a compatible remote Linux computer you own or are authorized to modify. Installing the client on your Mac alone is not enough.
- **An idle computer with bot work finished and routines paused before setup.** The change affects all bots sharing that computer, not just one bot.

The remote computer also needs **Python 3.10+, Git, and compatible Node/npm**. Large-image resizing requires **Pillow**. The [setup guide](docs/getting-started.md) covers these requirements; do not replace Grok's runtime or use sudo to bypass a failed check.

### Let your AI install it

Paste this into your coding assistant. It needs access to **Grok Bot's remote Computer terminal**, not just your Mac. If it cannot access that computer, it can walk you through the commands instead. You'll complete sign-in yourself.

```text
Help me install ungrok from https://github.com/abhaysudhir/ungrok
using my Claude or ChatGPT subscription.

Read the repo's README and docs/agent-setup.md first. Use the documented
release and its instructions, not commands from an unreleased version.
Ask which provider I want, check the prerequisites, and confirm access to
my Grok Bot remote computer. If you cannot access it, guide me one step
at a time. Do not install this on my Mac instead.

Ask before installing dependencies or changing the shared host. Have me
finish bot work and pause routines before changing any configuration.
Let me complete official sign-in myself; never ask for passwords or tokens.
Ask separately before restarting. Verify actual app routing, a harmless
tool, and a test image, and tell me exactly what passed or remains unchecked.
Stop on unsupported configurations; do not bypass safety checks.
```

See the [full assistant setup guide](docs/agent-setup.md) for verification and recovery details. An assistant can help with setup, but it cannot make an unsupported computer compatible or guarantee that every workflow works.

### Install manually

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
