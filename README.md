<p align="center"><img src="assets/banner.svg" alt="ungrok: your bots, your subscriptions" width="920" /></p>

# ungrok

**Connect your AI subscriptions to Grok Bot.**

Use Claude or ChatGPT inside Grok Bot through the official Claude Code or Codex client. Keep the Grok Bot app and its tools, and sign in with your own subscription. No API keys.

> **Early access:** Fresh-install testing is still pending, and Claude tool-result follow-up remains unverified. [Test results and supported versions](docs/compatibility.md)

## Getting Started

### 1. Check what you need

- **Grok Bot installed and signed in**, with active access through an eligible Cursor plan or linked subscription. [Access requirements](https://cursor.com/help/grok-bot/plans)
- **Your own Claude or ChatGPT subscription.** Claude requires Pro or Max; ChatGPT needs subscription access supported by the pinned Codex client. [Supported clients and sign-in](docs/providers.md)
- **Access to Grok Bot → Computer → Terminal** on a compatible remote Linux computer you own or are authorized to modify. Setup happens there, not in your Mac's terminal.

Your assistant will check Python 3.10+, Git, Node/npm, and Pillow for large-image resizing. Missing dependencies may need your approval and additional setup.

### 2. Let your AI install it

Paste this into your coding assistant:

```text
Help me install ungrok: https://github.com/abhaysudhir/ungrok

Read docs/agent-setup.md and follow the documented release instructions.
Ask whether I want Claude or ChatGPT, then check the prerequisites on
my Grok Bot remote computer. If you cannot access it, guide me one step
at a time. Ask before making changes, have me pause bots and routines,
and let me complete official sign-in myself. Verify the setup in the
app and report anything that remains untested. Never request my tokens
or bypass safety checks.
```

The assistant needs remote Computer terminal access to carry out the installation. Otherwise, it can walk you through it. You'll choose your provider, complete sign-in, and approve changes and restart.

### 3. Check it in Grok Bot

After setup, have your assistant verify a new message, a harmless tool task, and a test image in the app. It should confirm that the selected provider handled the request, not just that a reply appeared. Keep important routines paused until these checks pass.

Then use your bots in the same app. The provider and model setting applies to **all bots on that shared computer**.

## Before you use it

- Pause active work and routines **before setup or model/provider changes**. On an existing installation, new sessions can pick up changed settings before restart.
- Conversations, tool results, and images go to your chosen provider. Subscription limits still apply; ungrok does not guarantee unlimited use or zero Grok charges.
- Grok Bot updates can remove the integration. Keep your installation checkout and backup, and follow the [recovery guide](docs/updates.md) if routing changes or you want to undo setup.

## Help and documentation

[Setup questions](https://github.com/abhaysudhir/ungrok/discussions) · [Report a bug](https://github.com/abhaysudhir/ungrok/issues/new/choose) · [Troubleshooting](docs/troubleshooting.md)

Prefer to run the commands yourself? Use the [manual installation guide](docs/getting-started.md) for the published [v0.2.0-alpha.1 release](https://github.com/abhaysudhir/ungrok/releases/tag/v0.2.0-alpha.1).

[How it works](docs/architecture.md) · [Security and privacy](SECURITY.md) · [Compatibility](docs/compatibility.md) · [Updates and rollback](docs/updates.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and tests, and the [release checklist](docs/release-checklist.md) for verification requirements. The unreleased `./ungrok start` wizard is documented in the [development setup guide](docs/easy-setup.md); it is not in the published alpha archive.

## License

[MIT](LICENSE). Earlier work derives from BlockedPath's MIT-licensed adapter. See [provenance](vendor/UPSTREAM.md).

Unofficial. Not affiliated with xAI, Cursor, Anthropic, or OpenAI.
