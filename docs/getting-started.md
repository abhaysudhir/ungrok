# Set up ungrok

ungrok is an alpha host patch for people comfortable recovering a remote Linux process. Read the [compatibility limits](compatibility.md) before changing a computer you rely on.

## What you need

- A working Grok Bot account with access to **Computer → Terminal**.
- Permission to change the shared remote host. Every bot on that computer can be affected.
- Git and Python 3.10 or newer to download and run ungrok, plus the host's Node.js runtime.
- An authorized OpenAI-compatible **Chat Completions** endpoint, its exact model ID, and a nonempty API or local proxy key. The endpoint must support streamed responses and tool calls.
- Time to pause bot work, apply the patch, and check a real request.

Large inline images also need Pillow in the host's `python3` environment. Text-only use does not need Pillow; install it after downloading and reviewing the source below.

Native Anthropic Messages API endpoints do not work directly with this adapter. A model appearing in an endpoint's catalog does not establish tool or streaming compatibility. Use an authorized compatible gateway if your provider needs translation. ungrok does not install a proxy or supply provider access.

Use API credentials or another arrangement your provider permits. This guide does not support repurposing Claude subscription login credentials for third-party integrations; see [Anthropic's legal and compliance documentation](https://code.claude.com/docs/en/legal-and-compliance).

## 1. Open the remote terminal

Open Grok Bot, select a bot, then open its **Computer** view and **Terminal**. Run the commands below there, not in Terminal on your Mac. The desktop app is left unchanged.

```sh
whoami
uname -s
test -f "$HOME/sand-host/host-main.cjs"
```

Expect Linux and an existing host file. Stop if you are on the wrong machine or the layout differs.

Run as the host file's owner, without `sudo`. Host, data, and state paths must be real paths without symlink components. If you already installed an upstream `xai` provider patch, follow [migration instructions](updates.md#migrating-an-existing-provider-patch) first; ungrok refuses to stack patches.

## 2. Download and inspect

```sh
git clone --branch v0.1.0-rc.1 --single-branch https://github.com/abhaysudhir/ungrok.git
cd ungrok
git rev-parse HEAD
```

These commands select `v0.1.0-rc.1`. Compare the printed commit with [the release notes](https://github.com/abhaysudhir/ungrok/releases/tag/v0.1.0-rc.1) and inspect the source before continuing. If the tag is not published yet, stop rather than substituting the moving `main` branch.

```sh
./ungrok --help
./ungrok doctor
```

`doctor` is read-only. Exit status 1 means the setup is not ready, which can be expected before first configuration. Read each finding. A missing ungrok configuration is different from an unsupported host layout; resolve compatibility failures before setup.

Keep the exact checked-out commit and a copy of the source outside the remote computer. The CLI's version string alone cannot distinguish development commits. If you download the source archive instead, verify its SHA-256 against the release checksum before extracting and running it.

If you will send large images, review and install the optional dependency:

```sh
python3 -m pip install -r requirements-images.txt
```

Use the `python3` environment available to the host process. If package installation is restricted, use an approved environment; do not bypass the system's package protections. An environment activated only in your terminal may not be inherited by an already-running host supervisor.

## 3. Configure and patch

Finish active work and pause routines through the app where possible. Setup changes the shared host, not just the selected bot.

```sh
./ungrok setup
```

Enter the base URL, exact model ID, and API or local proxy key when prompted. The key prompt is hidden. Do not put a key in a command argument, screenshot, or issue. Include `/v1` in the base URL if your endpoint requires it; ungrok appends `/chat/completions`. Use HTTPS for a remote endpoint; plain HTTP is allowed only for `localhost`, `127.0.0.1`, or `::1`. URLs cannot contain credentials, query parameters, or fragments.

Setup asks for confirmation before changing the host. It saves configuration in `~/sand-data/ungrok.env`, installs `~/sand-host/ungrok-session.cjs`, and patches the current host with a fresh backup. **Setup does not restart the host.**

Setup also installs the request-image helper as `~/sand-host/ungrok-resize-image.py`. Inline image data URLs longer than 200,000 characters are resized sequentially in memory before transmission. Request copies become JPEGs with a longest edge of at most 1,568 pixels; original files and conversation objects remain untouched. Remote image URLs are not fetched or resized by the helper. See [image limits](compatibility.md#inline-images) before sending image-heavy requests.

Successful setup prints `Installed. Host and adapter syntax checks passed. No host was restarted.` This confirms local installation only. Private state and backups live in `~/.local/state/ungrok`; an existing state directory must belong to you and have mode `700`.

The provider receives conversation content and tool output sent through the adapter. That can include files, browser content, and information from connected services. Choose an endpoint you trust with that data and review its retention policy.

For an unattended install, prepare a private configuration file with these fields:

```dotenv
SAND_XAI_BASE_URL=https://your-authorized-endpoint.example/v1
SAND_XAI_MODEL=your-exact-model-id
XAI_API_KEY=your-private-key
SAND_XAI_THINKING=disabled
```

The example URL and values are placeholders. The file must be UTF-8, owned by your current user, and private with mode `600`. Keep it outside the checkout. Use plain `KEY=value` lines with **no outer quotes, `export` prefixes, or surrounding whitespace**. Only the four keys shown above are accepted; duplicate keys are rejected. `SAND_XAI_THINKING` is optional, and `disabled` is its only supported value in v0.1.

Create the real file with a private editor, then substitute its actual path in these commands:

```sh
chmod 600 /private/path/provider.env
./ungrok setup --config /private/path/provider.env --yes
```

The legacy `XAI` field names are adapter names. The base URL determines the destination; these names do not mean a request goes to xAI.

## 4. Test the endpoint

```sh
./ungrok probe
```

This sends a synthetic, non-streaming prompt to the configured provider and expects `UNGROK_OK`. It can incur provider usage. It does not send an existing bot conversation, prove app routing, or test streaming or tool support. A successful result starts with `Provider probe passed: UNGROK_OK.`

The probe does not follow redirects or use machine-wide HTTP proxy environment settings. Supply the final endpoint URL and make sure it is directly reachable from the remote computer.

Stop if the probe fails. Check the URL, authentication, model, and endpoint compatibility before restarting.

## 5. Restart the verified host

Inspect the current host process:

```sh
pgrep -af 'host-main.cjs'
```

Identify the real host PID, then substitute that numeric value for `HOST_PID`:

```sh
./ungrok restart --pid HOST_PID --yes
```

This is a separate disruptive action. The command verifies the exact Node host process and a same-user parent running `sand-supervisor.mjs` before sending TERM, then waits up to 20 seconds for a replacement under that supervisor. If verification fails, stop and inspect the current supervisor arrangement. Do not kill all Node processes or launch a duplicate host.

## 6. Verify from Grok Bot

Wait for the app to reconnect. Record the current host log boundary before sending a test; the observed host layout uses `/tmp/sand-host.log`:

```sh
wc -l /tmp/sand-host.log
```

Send this to one idle bot:

> Diagnostic routing check: reply exactly UNGROK_OK. Do not use tools or message other bots.

Inspect only newly appended log lines for `[ungrok] session model=... endpoint=...` with the intended model and endpoint origin, plus any routing errors. The log intentionally omits the endpoint's path and credentials. If the log rotates, establish a new boundary and repeat. Keep other bots idle so unrelated sessions are less likely to confuse the check.

A reply by itself does not prove which provider answered. `doctor` and `probe` also cannot establish end-to-end routing. Do not resume important work until the app reply and fresh route evidence agree. Test harmless tool and browser workflows separately before relying on them.

## Custom paths

Global options go **before** the command:

```sh
./ungrok --host-dir /path/to/sand-host --data-dir /path/to/sand-data --state-dir /private/path/ungrok-state --node /path/to/node doctor
```

Defaults are `~/sand-host`, `~/sand-data`, and `~/.local/state/ungrok`. The default runtime is `/exec-daemon/node` when available, otherwise `node`. Use the same overrides for later setup, repair, restart, and rollback commands. Overrides do not make an incompatible host supported.

Keep [update recovery](updates.md) and [troubleshooting](troubleshooting.md) available outside the remote computer.
