# Set up the native alpha

This guide is for **0.2.0-alpha.1**, not the older API-based release. Both native paths are implemented and have passed real local marker probes. Linux Grok host verification is pending. Use exact Claude Code **2.1.263** or Codex **0.153.4**; read [compatibility](compatibility.md) first.

## 1. Confirm the machine

Open **Grok Bot → Computer → Terminal**:

```sh
whoami
uname -s
test -f "$HOME/sand-host/host-main.cjs"
```

Expect Linux and the current host file. Run as its owner without sudo. The default host/data directories are `~/sand-host` and `~/sand-data`. Stop on an unsupported layout. The Mac app is unchanged.

Check Git, Python 3.10+, the original host Node runtime, and the official client. Install missing dependencies only with approval; do not replace the host runtime to bypass a failed check.

## 2. Read the right source

Clone the exact alpha tag into a new directory. If the directory already exists, inspect it instead of overwriting it:

```sh
git clone --branch v0.2.0-alpha.1 --depth 1 https://github.com/abhaysudhir/ungrok.git ungrok-0.2.0-alpha.1
cd ungrok-0.2.0-alpha.1
git rev-parse HEAD
```

Record that commit and keep the checkout for recovery. Do not substitute an older 0.1 release.

```sh
./ungrok --version
./ungrok --help
./ungrok doctor
```

Doctor checks local files and configuration only; it does not verify native auth or make a network request. It may report not-ready before setup. Do not stack an old hook; read [migration](updates.md).

## 3. Sign in

Follow the [pinned client installation](providers.md#install-the-exact-native-clients), which sets `ungrok_clients` to the versioned prefix. From the ungrok checkout, for Claude:

```sh
./ungrok login claude --cli "$ungrok_clients/node_modules/.bin/claude"
```

Complete sign-in yourself through the official client on the remote computer. ChatGPT uses `./ungrok login chatgpt` with Codex 0.153.4; Claude requires version 2.1.263 and supported Pro/Max auth. Never paste login codes, keys, tokens, or credential files into chat.

## 4. Configure and patch

Finish active bot work and pause routines. Confirm consent to changing the shared host for all bots and sending conversation/tool data through the chosen provider.

```sh
./ungrok setup --provider claude --cli "$ungrok_clients/node_modules/.bin/claude"
```

Setup resolves the native executable or accepts `--cli /absolute/path/to/claude`. Optional `--model MODEL` selects an account-supported alias. Authentication must pass before installation. **Setup does not restart.**

For noninteractive configuration, use an owner-only file outside the checkout:

```dotenv
UNGROK_PROVIDER=claude
UNGROK_CLI=/absolute/path/to/claude
# UNGROK_MODEL=your-supported-model-alias
```

Replace the path with the real executable. The provider is `claude` or `chatgpt`; model is optional. Use plain `KEY=value` lines, no shell quotes or exported variables. No credential or endpoint belongs here. After consent, pass `./ungrok setup --config /private/path/provider.env --yes`; do not combine `--config` with provider/model/CLI flags. Existing native profile locators such as `CLAUDE_CONFIG_DIR` and `CODEX_HOME` must point to the same profile for login, setup, and execution.

## 5. Probe and restart separately

```sh
./ungrok probe
```

This consumes subscription quota for a synthetic prompt. Stop on failure. A pass does not verify app routing, tools, or images.

When the computer is idle and you approve interruption:

```sh
pgrep -af 'host-main.cjs'
./ungrok restart --pid HOST_PID --yes
```

Replace HOST_PID with the exact verified numeric PID. Restart must verify the host/supervisor. Do not kill generic Node processes or launch a duplicate manual host.

## 6. Verify in the app

Wait for reconnection, establish a fresh host-log boundary, and send an idle bot:

> Diagnostic routing check: reply exactly UNGROK_OK. Do not use tools or message other bots.

Match the reply with fresh `[ungrok] native session provider=... model=...` evidence for the selected provider. With approval, test a harmless Grok-host tool and a small synthetic image with an objectively checkable answer. Confirm the native client did not execute its own tools outside Grok's host.

Report each check separately. Mark inaccessible or failed workflows unverified. Do not resume important work based on login or probe alone.

Global `--host-dir`, `--data-dir`, `--state-dir`, and `--node` overrides belong before the command. Keep the same paths and original checkout for recovery.

## Optional native adapter check

After native sign-in, this opt-in script tests five synthetic cases without installing or restarting a Grok host. It consumes subscription quota. Replace the executable path with your exact supported official client:

```sh
node scripts/verify_subscription.cjs --provider claude --cli /absolute/path/to/claude --yes
```

For Codex use `--provider chatgpt --cli /absolute/path/to/codex`. Optional `--model MODEL` selects an account-supported alias.

The cases are text, a proposed synthetic host-tool call, its supplied result/follow-up, two binary images, and image follow-up. No real Grok tool is executed. A pass establishes that native adapter route on the machine where the script ran, not successful installation, Linux compatibility, or live Grok app routing. Record the printed outcomes separately from the real app checks above.
