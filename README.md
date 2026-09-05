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

> **Experimental release.** The original adapter was tested on a Grok Bot computer, including recovery after an update. This hardened public version has automated fixture tests, but has not yet been verified end-to-end on a live Grok Bot host. It relies on private host internals. Read the limits before installing it on a computer you depend on.

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

You need a working Grok Bot computer, Git, Python 3.10+, the host's Node runtime, and an authorized **OpenAI-compatible Chat Completions endpoint with SSE streaming and tool calls**. ungrok does not provide model access or install a proxy.

**Run this inside Grok Bot → Computer → Terminal. Not in Terminal on your Mac.**

```sh
git clone https://github.com/abhaysudhir/ungrok.git
cd ungrok
./ungrok doctor
```

On a first install, `doctor` should report a known insertion point and missing configuration. If it reports an unknown host layout or an existing provider patch, stop and read [compatibility](docs/compatibility.md).

Read the code, finish active bot work, and pause routines where possible. Then:

```sh
./ungrok setup
```

Enter your endpoint's base URL, exact model ID, and key at the prompts. Setup saves a private config, checks JavaScript syntax, backs up the current host, and installs the hook. **It does not restart anything.**

```sh
./ungrok probe
pgrep -af 'host-main.cjs'
./ungrok restart --pid HOST_PID --yes
```

Replace `HOST_PID` with the numeric PID you just verified. `probe` sends one synthetic prompt and may incur provider usage. The restart command verifies the host and its supervisor before signaling it.

Finally, send this to an idle bot:

> Diagnostic routing check: reply exactly UNGROK_OK. Do not use tools or message other bots.

Check both the reply **and fresh `[ungrok] session` log lines** showing your intended model and endpoint. A reply alone is not proof of routing. [Full setup and verification →](docs/getting-started.md)

## Pick an endpoint, not a logo

| Endpoint type | v0.1 expectation |
| --- | --- |
| Authorized OpenAI-compatible API or gateway | Configurable. Must support Chat Completions, SSE, and tool calls; live compatibility depends on the endpoint and model. |
| Proxy already running on the Grok computer | Loopback HTTP is allowed. You manage its installation, authentication, and uptime. |
| Native Anthropic Messages API | Not directly compatible. Requires an authorized translating gateway. |
| Model running on your laptop | `localhost` on the Grok computer is **not your laptop**. You need a secure reachable endpoint. |
| Claude subscription login | Not offered by ungrok. Use provider-authorized API access; see [Anthropic's credential policy](https://code.claude.com/docs/en/legal-and-compliance). |

We don't list a provider as supported just because it accepts a text prompt. Tool handling, long conversations, images, and host behavior need separate tests. See the [compatibility record](docs/compatibility.md).

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and [SECURITY.md](SECURITY.md) for private reports. If this is useful, star the repo so you can find it after the next computer update.

## Credit

The inference adapter is derived from [BlockedPath/grok-bot-setup](https://github.com/BlockedPath/grok-bot-setup), under MIT. ungrok adds its own installer, recovery workflow, tests, and adapter hardening. Exact provenance and changes are in [vendor/UPSTREAM.md](vendor/UPSTREAM.md).

MIT licensed. Unofficial and not affiliated with xAI, Cursor, Anthropic, or OpenAI.
