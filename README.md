<p align="center">
  <img src="assets/banner.svg" alt="ungrok — Your bots. Your model." width="920" />
</p>

<p align="center">
  <a href="https://github.com/abhaysudhir/ungrok/actions/workflows/ci.yml"><img src="https://github.com/abhaysudhir/ungrok/actions/workflows/ci.yml/badge.svg" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license" /></a>
  <img src="https://img.shields.io/badge/status-experimental-orange" alt="Experimental" />
</p>

**Bring your own model to Grok Bot.** Keep its app and shared computer. Choose the endpoint that answers your bots.

ungrok is an unofficial, reversible host mod. It adds a custom inference adapter, checks the host before touching it, and gives you a way back when an update changes things.

[Get started](docs/getting-started.md) · [After an update](docs/updates.md) · [Compatibility](docs/compatibility.md) · [Troubleshooting](docs/troubleshooting.md)

> **v0.1.0-rc.2 prerelease.** The legacy compatibility repair has narrow live text, follow-up, and image results. The new installer and hardened adapter have automated tests, but their complete live setup/restart/repair/rollback path remains unverified. This relies on private host internals. Use a computer you can afford to recover, and read the [evidence boundary](docs/compatibility.md).

## Why ungrok?

You want Grok Bot's app and computer, but you want to choose the model behind them. A changed model label or a successful proxy request doesn't prove the bot actually uses that provider. And when a computer update replaces the host, a patch can disappear while the bots keep working through the default route.

ungrok makes the change explicit:

- **Inspect first.** `doctor` checks the host layout, installed hashes, and private configuration without sending a request.
- **Keep keys private.** Setup prompts for the key without putting it in shell history. It never borrows a Grok login token.
- **Stop on adapter failure.** The injected hook does not catch a failure and silently call the default provider.
- **Recover deliberately.** A fresh host backup, an explicit restart, and a rollback that refuses a mismatched host version.

This is a provider mod, not a replacement for Grok Bot or a way to remove its charges. A computer update can remove the hook entirely, at which point ungrok cannot stop the stock host from using its default route.

## How it works

```text
Grok Bot app
    │
    ▼
Shared Grok computer ── ungrok adapter ── your Chat Completions endpoint
    │
    └── existing tools, files, routines, and conversation infrastructure
```

The change is on the **remote computer shared by your bots**. The Mac app is untouched. Prompts and tool results handled by the adapter go to the endpoint you configure. Choose one you trust with that data.

## Quick start

Start with the **Grok Bot app** and an account with a service that provides the model you want. You don't need to know what an endpoint, SSE, or tool calling means.

### Let your AI assistant help

Paste this into a coding assistant that can use a terminal or help you operate the app:

```text
Help me set up ungrok: https://github.com/abhaysudhir/ungrok
Read its README and docs/agent-setup.md first. Start from my Grok Bot app.
Ask which model I want and help me choose the simplest supported provider.
Explain any separate API charges before I sign up or pay. Don't ask me to
paste API keys into this chat. Check the correct computer, back up before
changes, and verify a real bot reply before calling setup complete.
```

The assistant can guide setup and run checks where it has access. You'll still handle account sign-in, private keys, any payments, and approvals. A chat-only assistant can walk you through the steps but cannot control your computer. [Full copy-paste setup prompt →](docs/agent-setup.md)

### Do it yourself

1. **Open Grok Bot and sign in.** Finish the app's normal onboarding. Select or create a bot and open its **Computer** view. If it is starting or reconnecting, wait for it to become available. ungrok cannot create a Grok computer for you or fix an unavailable account.
2. **Choose your model service.** The simplest documented route is OpenRouter: create an account, get an API key, and pick a model that can use tools and read images if you need them. **No proxy installation is needed for this route.** API usage is billed separately from a ChatGPT or Claude chat subscription. [Choose a provider and get the three setup values →](docs/providers.md)
3. **Open Terminal inside Grok Bot's Computer view.** Grok Bot runs its bots on a remote Linux computer. That's where ungrok belongs, not in your Mac's Terminal. [The walkthrough checks this before changing anything →](docs/getting-started.md)
4. **Install, test, and restart using the walkthrough.** It explains each command, saves a backup, and checks a real bot request. Setup affects all bots sharing that computer.

[Start the step-by-step walkthrough →](docs/getting-started.md)

Already paying for API access directly from a provider? You may be able to use it directly, or need a small translator called a **proxy**. The [provider guide](docs/providers.md) explains both and includes installation steps for the optional proxy.

## Technical compatibility, if you need it

An **endpoint** is the web address where ungrok sends requests. **Streaming** means replies arrive as they are written. **Tool calls** let the model ask Grok Bot to do things such as read a file. Your provider needs to support those features; the setup guide helps you choose and test it.

The adapter uses the OpenAI Chat Completions format. It does not directly accept native Anthropic Messages or OpenAI Responses endpoints. Native providers may need a translating proxy. A model catalog listing does not prove tools, images, or streaming work in Grok Bot; test them during setup. [Technical limits and evidence →](docs/compatibility.md)

For large images, the walkthrough includes the optional Pillow dependency. It shrinks copies sent to the model after upload, not the original photos or the Mac-to-Grok upload.

## After a computer update

```sh
./ungrok doctor
./ungrok repair --yes
./ungrok probe
pgrep -af 'host-main.cjs'
./ungrok restart --pid HOST_PID --yes
```

Use these only after reading `doctor`'s findings. `repair` reuses your saved ungrok configuration and refuses an unknown or foreign-patched host. If the update removed the repo or your provider's proxy, restore those first. Verify a new app request before resuming important work. [Update playbook →](docs/updates.md)

To undo the recorded patch:

```sh
./ungrok rollback --yes
```

Then restart the verified host. Stock routing resumes after restart. Your private configuration and backups remain; rollback does not delete credentials.

## What this does not promise

- No guarantee of lower bills, zero Grok usage, or provider-policy approval.
- No automatic protection after an update removes the patch.
- No verified coverage of every voice, background, browser, or tool path.
- Live delta delivery and cancellation pass mock-server tests; follow-up/steering behavior on the actual host still needs end-to-end verification.
- No transparent full-context preservation. The adapter bounds long inputs by character count, which can discard older context.

These are release limits, not fine print. [Technical details and evidence →](docs/compatibility.md)

## Contribute a reproducible result

The most useful contribution is a **sanitized compatibility report**: host/client version, endpoint type, model ID, whether text and a harmless tool call worked, and what happened after an update. Never include a key, raw conversation, credential file, or full host log.

Run the credential-free tests:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.cjs
```

The full test suite requires Pillow; install `requirements-images.txt` first as described in [CONTRIBUTING.md](CONTRIBUTING.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and [SECURITY.md](SECURITY.md) for private reports. If this is useful, star the repo so you can find it after the next computer update.

## Credit

The inference adapter is derived from [BlockedPath/grok-bot-setup](https://github.com/BlockedPath/grok-bot-setup), under MIT. ungrok adds its own installer, recovery workflow, tests, and adapter hardening. Exact provenance and changes are in [vendor/UPSTREAM.md](vendor/UPSTREAM.md).

MIT licensed. Unofficial and not affiliated with xAI, Cursor, Anthropic, or OpenAI.
