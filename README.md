<p align="center"><img src="assets/banner.svg" alt="ungrok: your bots, your subscriptions" width="920" /></p>

# ungrok

**Connect your AI subscriptions to Grok Bot.**

Use Claude or ChatGPT inside Grok Bot through the official Claude Code or Codex client. Keep the Grok Bot app and its tools, and sign in with your own subscription. No API keys.

> **Early access:** Fresh-install testing is still pending, and Claude tool-result follow-up remains unverified. [Test results and supported versions](docs/compatibility.md)

**Grok Bot version:** The previous integration passed an upgrade smoke test on desktop **0.44.0** on September 6, 2026. A September 9 check found its on-disk routing hook and installed adapter missing; a manual repair passed fresh text/tool checks after a host restart. These are legacy integration results, not verification of the current subscription-based installer. [Version details](docs/compatibility.md#grok-bot-version)

> **Usage and updates:** Custom-provider routing does not guarantee zero Grok usage. A working chat can outlive an on-disk hook that a host update removed. Verify the installed files and fresh routing after a controlled restart, not just an old success log. [September 9 findings](docs/compatibility.md#september-2026-legacy-host-incident)

## Getting Started

### 1. Check what you need

- **Grok Bot installed and signed in**, with active access through an eligible Cursor plan or linked subscription. [Access requirements](https://cursor.com/help/grok-bot/plans)
- **Your own Claude or ChatGPT subscription.** Claude requires Pro or Max; ChatGPT needs subscription access supported by the pinned Codex client. [Supported clients and sign-in](docs/providers.md)
- **Access to Grok Bot's remote computer**, which you own or are authorized to modify. Setup happens there, not in your Mac's terminal.

The remote computer needs Python 3.10+, Git, Node/npm, and Pillow for large-image resizing. Grok Bot can check these for you, or you can check them during manual installation.

### 2. Install ungrok

Start with Grok Bot below, or expand the manual instructions if you prefer to run the commands yourself.

#### Option A: Have Grok Bot Install It

Paste this into a **Grok Bot chat**. It will guide setup on its own computer, stopping for your sign-in and approval. This uses some Grok Bot allowance.

**Experimental:** this bot-led installation flow has not yet passed a clean-computer test.

```text
Help me install ungrok on this Grok Bot computer:
https://github.com/abhaysudhir/ungrok

Read the README, docs/agent-setup.md, and SECURITY.md first. Use the
documented release and its matching instructions.

1. Ask whether I want Claude or ChatGPT. Check prerequisites and any
   existing installation. Stop on unsupported layouts or conflicts.
2. Explain what needs installing and ask for approval. Use the pinned
   official clients. Never use sudo, overwrite an unknown installation,
   extract tokens, or bypass safety checks.
3. Guide official subscription sign-in. Let me enter credentials myself;
   never request passwords or tokens in chat.
4. Before changing the shared host, ask me to pause other bots and
   routines. Explain that all bots are affected. Preserve the backup
   and save a credential-free recovery note with the release,
   installation folder, and completed steps before applying changes.
5. Apply the configuration and run the documented checks with my
   approval. Stop on failure and explain what changed.
6. Do not restart your own host. Give me the exact restart command for
   the verified host process, tell me where to run it, and wait.

When I return and say "continue setup," inspect the current state.
Verify a fresh response uses my chosen provider, then test a harmless
tool task, its result/follow-up, a small image, and an image follow-up.
Only if all checks pass, end with:
"Setup complete — ungrok is working with [verified provider]."
Show the configured model, or "client default" if no model was selected,
and mark each verified check PASS. Tell me I can use the tested features
in Grok Bot and that the setting applies to all bots on this computer.
If any check fails or cannot be verified, say "Setup incomplete," list
what passed, and give the exact remaining issue and next step. Never
show the success message based only on login, a probe, or a restart.
```

You'll complete official sign-in yourself. For the restart handoff, click **Computer in Grok Bot's top-right corner**, open **Terminal inside that remote computer**, and run the command the bot gives you. After reconnection, return to the chat and say **continue setup**. Do not run the restart command in your Mac's terminal.

#### Option B: Install it yourself

<details>
<summary>Open the step-by-step terminal instructions</summary>

These commands use the published **v0.2.0-alpha.1** release. In Grok Bot, click **Computer in the top-right corner**, then open **Terminal inside the remote computer**. Run one block at a time there. Stop if a command fails. Do not run these commands in your Mac's terminal or use sudo.

To open the right terminal:

1. Open the Grok Bot app.
2. Click **Computer** in the **top-right corner**.
3. Once the remote computer opens, open **Terminal inside that computer**.
4. Run the commands below in that terminal, not your Mac's Terminal app.

**1. Check the computer.**

```sh
uname -s
python3 --version
git --version
node --version
npm --version
```

Expect Linux, Python 3.10 or newer, and working Git, Node, and npm commands. If a prerequisite is missing, see [setup help](https://github.com/abhaysudhir/ungrok/discussions) before continuing. Leave Grok's existing runtime unchanged.

**2. Download ungrok and check the host.**

```sh
git clone --branch v0.2.0-alpha.1 --depth 1 https://github.com/abhaysudhir/ungrok.git ungrok-0.2.0-alpha.1
```

After the clone succeeds:

```sh
cd ungrok-0.2.0-alpha.1
git rev-parse HEAD
./ungrok doctor
```

Keep this folder and the printed commit for recovery. On a fresh install, doctor may report that provider configuration is missing; that is expected. Stop on an unsupported host, existing foreign patch, or other error. If you already have an installation, follow [migration and recovery](docs/updates.md) instead of overwriting it.

**3. Install the supported clients.**

This installs the pinned Claude Code and Codex clients in a new user-local folder, without global installation or package scripts:

```sh
ungrok_clients="$HOME/.local/share/ungrok/clients-0.2.0-alpha.1"
mkdir -p "$HOME/.local/share/ungrok"
mkdir -m 700 "$ungrok_clients" && npm install --prefix "$ungrok_clients" --ignore-scripts --no-audit --no-fund '@anthropic-ai/claude-code@2.1.263' '@openai/codex@0.153.4'
```

If the folder already exists, stop and inspect it; do not delete it to retry. After installation succeeds, verify:

```sh
"$ungrok_clients/node_modules/.bin/claude" --version
"$ungrok_clients/node_modules/.bin/codex" --version
```

Expect Claude Code **2.1.263** and Codex **0.153.4**. Other versions are unsupported. Keep using this terminal so the `ungrok_clients` variable remains set. Doctor also reports Pillow availability; missing Pillow affects most photos and screenshots. See [large-image support](docs/getting-started.md#large-image-support).

**4. Choose your provider and sign in.**

Run **one** of these blocks to select your provider:

Claude:

```sh
ungrok_provider=claude
ungrok_cli="$ungrok_clients/node_modules/.bin/claude"
```

ChatGPT:

```sh
ungrok_provider=chatgpt
ungrok_cli="$ungrok_clients/node_modules/.bin/codex"
```

Then sign in:

```sh
./ungrok login "$ungrok_provider" --cli "$ungrok_cli"
```

Complete the official sign-in flow yourself. Never post login codes, tokens, or credential files. If you use a custom sign-in profile, check [profile requirements](docs/getting-started.md) before continuing.

**5. Apply the settings and test the connection.**

Finish all bot work and pause routines first. This changes the shared computer for every bot, and an existing installation can use new settings immediately.

```sh
./ungrok setup --provider "$ungrok_provider" --cli "$ungrok_cli"
```

Read and approve the setup prompt. To choose a specific supported model, add `--model MODEL` to that command; otherwise it uses the official client's default.

After setup succeeds:

```sh
./ungrok probe
```

The probe uses subscription allowance. Stop on failure. A passing probe checks the native client, not the app's tools or images.

**6. Restart the verified host.**

Keep bots idle and routines paused. Find the host process:

```sh
pgrep -af 'host-main.cjs'
```

Identify the process for this computer's `sand-host/host-main.cjs`. Replace `HOST_PID` below with its numeric process ID. If there are multiple candidates or you are unsure, ask for [setup help](https://github.com/abhaysudhir/ungrok/discussions); do not guess.

```sh
./ungrok restart --pid HOST_PID
```

The command checks the process and supervisor before asking for restart approval. Do not kill generic Node processes if it refuses. Wait for Grok Bot to reconnect, then continue with **Check your setup** below.

</details>

### 3. Check your setup

After either installation option, send an idle bot this message:

> Reply exactly UNGROK_OK. Do not use tools or message other bots.

Check the fresh host logs for `[ungrok] native session provider=... model=...` matching your selected provider. A reply alone does not prove the integration handled it. If you cannot locate that evidence, ask for [setup help](https://github.com/abhaysudhir/ungrok/discussions) rather than assuming success; never post full logs or credentials.

Next, try a harmless tool task, such as asking for the names in an empty test folder, and confirm the bot can explain the returned result in a follow-up. Attach a small test image with an obvious answer, then ask a follow-up about it. You can do these checks yourself or have Grok Bot help. Keep important routines paused until the checks pass. See [verification details](docs/getting-started.md#6-verify-in-the-app) if anything fails.

**How you know it worked:** all five checks below pass. For the bot-led installation, Grok Bot should finish with this report, filled in from actual results:

```text
Setup complete — ungrok is working with [verified provider].
Model: [configured model, or "client default"]

PASS — A new message used the selected provider.
PASS — A harmless Grok tool task returned the expected result.
PASS — The bot correctly handled the tool result in a follow-up.
PASS — The bot correctly read the test image.
PASS — The bot correctly answered an image follow-up.

You can now use these tested features in Grok Bot.
This provider/model setting applies to all bots on this computer.
```

For manual installation, use the same checklist. If any item fails or is unchecked, **setup is incomplete**. A successful sign-in, probe, or restart alone is not enough. Ask for help with the specific failed check instead of assuming it worked. These checks do not certify every routine, voice feature, or billing path.

## Before you use it

- Pause active work and routines **before setup or model/provider changes**. On an existing installation, new sessions can pick up changed settings before restart.
- Conversations, tool results, and images go to your chosen provider. Subscription limits still apply; ungrok does not guarantee unlimited use or zero Grok charges.
- Grok Bot updates can remove the integration. Keep your installation checkout and backup, and follow the [recovery guide](docs/updates.md) if routing changes or you want to undo setup.

## Help and documentation

[Setup questions](https://github.com/abhaysudhir/ungrok/discussions) · [Report a bug](https://github.com/abhaysudhir/ungrok/issues/new/choose) · [Troubleshooting](docs/troubleshooting.md)

For custom paths and configuration, see the [detailed installation guide](docs/getting-started.md).

[How it works](docs/architecture.md) · [Security and privacy](SECURITY.md) · [Compatibility](docs/compatibility.md) · [Updates and rollback](docs/updates.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and tests, and the [release checklist](docs/release-checklist.md) for verification requirements. The unreleased `./ungrok start` wizard is documented in the [development setup guide](docs/easy-setup.md); it is not in the published alpha archive.

## License

[MIT](LICENSE). Earlier work derives from BlockedPath's MIT-licensed adapter. See [provenance](vendor/UPSTREAM.md).

Unofficial. Not affiliated with xAI, Cursor, Anthropic, or OpenAI.
