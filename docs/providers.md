# Sign in with your subscription

Choose Claude or ChatGPT. The official client and its login must exist on the **same remote computer and user account** as the Grok host. This version has no API-key onboarding or subscription-token proxy.

## Install the exact native clients

Run this in Grok Bot's remote Linux terminal. First check:

```sh
node --version
npm --version
```

If either is missing, stop and ask your setup assistant to help install a compatible user-local Node/npm environment from official instructions. Leave Grok's existing host runtime unchanged. Do not blindly install a system-wide replacement.

The following installs both official packages into a **new, versioned user-local directory**, without sudo, global installation, or package lifecycle scripts. Review the pinned packages first: [Claude Code 2.1.263](https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.263) and [Codex 0.153.4](https://www.npmjs.com/package/@openai/codex/v/0.153.4).

```sh
ungrok_clients="$HOME/.local/share/ungrok/clients-0.2.0-alpha.1"
mkdir -p "$HOME/.local/share/ungrok"
mkdir -m 700 "$ungrok_clients" && npm install --prefix "$ungrok_clients" --ignore-scripts --no-audit --no-fund '@anthropic-ai/claude-code@2.1.263' '@openai/codex@0.153.4'
```

If the versioned directory already exists, the command stops before npm runs. Inspect it instead of deleting or overwriting it. If installation fails, stop and preserve the output privately; do not remove your native login directories.

Verify the exact installed executables, not whichever older client happens to be on PATH:

```sh
"$ungrok_clients/node_modules/.bin/claude" --version
"$ungrok_clients/node_modules/.bin/codex" --version
```

Expect **2.1.263** and **0.153.4** respectively. The official npm wrappers worked without lifecycle scripts in local verification. That does not guarantee support on every Linux architecture or Node version; if these checks fail, stop. The top-level packages are pinned, not a claim that all platform dependencies are hash-locked.

Use the same explicit paths for login and setup below. If you open another shell, set `ungrok_clients` again to this same directory. Installing these clients does not sign you in or patch the Grok host.

## Claude through Claude Code

This alpha requires official Claude Code **2.1.263** and a **Pro or Max** subscription login. Use the pinned installation above. [Anthropic's installation guide](https://code.claude.com/docs/en/setup) provides platform guidance, but a latest-version install may not match this alpha's exact requirement. Other versions, unsupported auth types, and detected managed-policy configurations are refused.

From the reviewed ungrok checkout:

```sh
./ungrok login claude --cli "$ungrok_clients/node_modules/.bin/claude"
```

Complete the official sign-in yourself. Use your eligible Claude subscription, not a Console/API-billed account. Check auth status privately through the official client; do not publish account details.

After the shared-host checks and consent in [setup](getting-started.md):

```sh
./ungrok setup --provider claude --cli "$ungrok_clients/node_modules/.bin/claude"
```

Anthropic's June 15 update paused its proposed billing change: Agent SDK, `claude -p`, and third-party app usage still draw from subscription limits. The old credit-plan text lower on that page is preserved history. [Current subscription usage update](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)

Use the unmodified official binary with your own sign-in. This does not authorize collecting or intermediating other users' credentials. [Anthropic credential rules](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use)

## ChatGPT through Codex

The native ChatGPT integration is implemented for official Codex **0.153.4**. All five local native adapter verification cases passed using a real subscription. Linux Grok host end-to-end verification remains pending. Other versions are refused. Check [compatibility](compatibility.md).

Use the pinned installation above, then run from the reviewed ungrok checkout:

```sh
./ungrok login chatgpt --cli "$ungrok_clients/node_modules/.bin/codex"
```

Complete the ChatGPT flow yourself. [Official Codex documentation](https://developers.openai.com/codex/cli) and [authentication](https://developers.openai.com/codex/auth) explain the native client.

After shared-host checks and consent:

```sh
./ungrok setup --provider chatgpt --cli "$ungrok_clients/node_modules/.bin/codex"
```

If refused, stop. Do not bypass runtime restrictions with unrestricted tools or an alternative billing route.

## Models and usage

Optional `--model MODEL` selects an alias supported by the native client and your account. A model name in a guide grants no access. Check the current client's defaults if omitting it.

Review subscription usage and extra-usage settings before enabling routines. Provider limits and terms can change. Native sign-in is neither unlimited compute nor a guarantee that every Grok path uses the subscription.
