# Choose a provider and connect it

**Start with a direct OpenRouter API connection. You do not need a local proxy for that route.** Use the optional LiteLLM section only if you already want to pay Anthropic directly through its API.

Setup asks for a server address, the exact name of your chosen model, and a private API key. This guide shows you where to get each one. ungrok does not include a model account, API credits, or a Grok Bot subscription. Your Claude/ChatGPT chat subscription is not the credential used by these instructions. API usage has its own billing. See [OpenRouter billing](https://openrouter.ai/docs/faq) and [Claude API billing](https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage).

This is an unofficial alpha. The examples describe supported protocol shapes, not a certification of every model or provider. Never give ungrok a credential you are not authorized to use.

## Option 1: OpenRouter, no proxy

1. Create an [OpenRouter account](https://openrouter.ai/) and add a small amount of API credit. Set a spending limit appropriate for a bot that can make repeated calls.
2. Create a dedicated key in [API Keys](https://openrouter.ai/settings/keys). Keep it in your password manager. Do not paste it into a bot conversation, issue, screenshot, command argument, or GitHub file.
3. Open the [model catalog](https://openrouter.ai/models). Pick a specific model that supports **tools** and, if you use screenshots or attachments, **image input**. Copy its exact API ID, not its display name. Check the model page for price, context limits, and provider availability. There is no permanently recommended ID in this guide because those change. [Model properties](https://openrouter.ai/docs/guides/overview/models) and [tool-calling support](https://openrouter.ai/docs/guides/features/tool-calling) explain what to check.
4. Complete the remote-computer, download, and `doctor` checks in the [setup walkthrough](getting-started.md) first. Once those pass, return to your cloned `ungrok` directory in **Grok Bot → Computer → Terminal** and run:

   ```sh
   ./ungrok setup
   ```

   Enter these values when prompted:

   | Prompt | Value |
   | --- | --- |
   | Base URL | `https://openrouter.ai/api/v1` |
   | Model ID | The exact ID copied from your chosen model page |
   | API key | Your OpenRouter key, entered at the hidden prompt |

   That base URL is the OpenAI-compatible endpoint documented in the [OpenRouter quickstart](https://openrouter.ai/docs/quickstart). Do not add `/chat/completions`; ungrok adds it.

5. Run `./ungrok probe`. It sends a small synthetic request and may incur API cost. A pass proves endpoint access, **not** live Grok Bot routing, tool use, or image support.
6. Finish the host restart and in-app checks in the [setup walkthrough](getting-started.md). Test one text request, one harmless tool action, and an image if you need vision. Check both fresh route logs and your provider usage dashboard.

OpenRouter receives the request and routes it to a model provider. Review its account privacy/routing settings and that provider's terms before sending private material. Choosing a fixed model ID does not mean that its underlying serving provider is fixed.

## Option 2: Anthropic API through a local LiteLLM proxy

**This is an optional, hands-on setup, not an unattended deployment.** LiteLLM translates the adapter's Chat Completions requests into Anthropic API requests. It does not turn a Claude chat subscription into API credit. Obtain an API key from the [Claude Console API Keys settings](https://platform.claude.com/docs/en/manage-claude/authentication), enable API billing, and choose an exact available model ID using the [Claude API documentation](https://platform.claude.com/docs/en/api/overview).

Run everything below in the **remote Grok Bot computer**, not your laptop. `127.0.0.1` means the machine running the bot host. A proxy on your laptop is not reachable at the remote computer's loopback address.

### Check the version before installing

As checked on **2026-09-06**, [PyPI lists LiteLLM 1.100.0](https://pypi.org/project/litellm/1.100.0/) with Python `>=3.10,<3.15`. The commands below pin that version. This is a package-publication check, not a security audit or an end-to-end test of this recipe.

**Do not install LiteLLM 1.82.7 or 1.82.8.** They were compromised; see the [official PyPI incident report](https://blog.pypi.org/posts/2026-04-02-incident-report-litellm-telnyx-supply-chain-attack/) and [LiteLLM security advisories](https://github.com/BerriAI/litellm/security). If you previously ran an affected package, stop and follow incident-response guidance before entering any fresh keys. A newer version number or a virtual environment is not proof that a previously compromised computer is clean.

### Install into its own directory

These commands do not use `sudo` or change the system Python. If the directory already exists, inspect it rather than overwriting it.

```sh
python3 --version
mkdir -m 700 "$HOME/ungrok-proxy"
python3 -m venv "$HOME/ungrok-proxy/venv"
"$HOME/ungrok-proxy/venv/bin/python" -m pip install 'litellm[proxy]==1.100.0'
"$HOME/ungrok-proxy/venv/bin/python" -c 'from importlib.metadata import version; print(version("litellm"))'
```

Stop if Python is outside the supported range or installation fails. The top-level package is pinned; its transitive dependencies are not fully hash-locked by this example. See LiteLLM's [installation requirements](https://docs.litellm.ai/docs/proxy/quick_start).

Using your remote computer's text editor, create `~/ungrok-proxy/config.yaml` with exactly this non-secret configuration:

```yaml
model_list:
  - model_name: my-claude
    litellm_params:
      model: os.environ/UNGROK_ANTHROPIC_MODEL
      api_key: os.environ/ANTHROPIC_API_KEY
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

`my-claude` is a local alias you will give ungrok. The actual provider model will be entered at startup. LiteLLM documents the `anthropic/` provider prefix in its [Anthropic integration](https://docs.litellm.ai/docs/providers/anthropic), and `os.environ/…` references in its [configuration guide](https://docs.litellm.ai/docs/proxy/configs). Do not replace the environment references with real keys in the YAML.

### Start it in the foreground

Create a separate random password-manager secret for the local proxy: `sk-` followed by at least 32 random characters. This is **not** your Anthropic key. You will use it both here and in ungrok's hidden API-key prompt.

The command below asks for secrets through hidden terminal prompts. It supplies them to the child process environment, not shell history or command-line arguments. Other processes with sufficient access to this account can still inspect that environment; loopback does not isolate mutually untrusted bots sharing one computer.

```sh
"$HOME/ungrok-proxy/venv/bin/python" -c '
import getpass, os, pathlib, re
root = pathlib.Path.home() / "ungrok-proxy"
model = input("Exact Anthropic API model ID, without anthropic/ prefix: ").strip()
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", model):
    raise SystemExit("Invalid model ID")
key = getpass.getpass("Anthropic API key: ")
local_key = getpass.getpass("Local proxy key from password manager (sk-...): ")
if not key or not local_key.startswith("sk-") or len(local_key) < 35:
    raise SystemExit("Missing API key or insufficient local proxy key")
env = dict(os.environ, ANTHROPIC_API_KEY=key,
           LITELLM_MASTER_KEY=local_key,
           UNGROK_ANTHROPIC_MODEL="anthropic/" + model)
binary = str(root / "venv/bin/litellm")
os.execve(binary, [binary, "--config", str(root / "config.yaml"),
                  "--host", "127.0.0.1", "--port", "4000"], env)
'
```

Leave that terminal running. Do not add `--detailed_debug`, expose the service on `0.0.0.0`, or publish port 4000. This guide uses a single master key for local access, not LiteLLM's database-backed virtual-key management.

### Connect and verify in a second remote terminal

From the `ungrok` checkout in a **second remote terminal**, run `./ungrok setup` and enter:

| Prompt | Value |
| --- | --- |
| Base URL | `http://127.0.0.1:4000/v1` |
| Model ID | `my-claude` |
| API key | The local proxy key, **not** the Anthropic key |

Run `./ungrok probe` while the first terminal remains open. If it passes, continue the [walkthrough's host restart and routing checks](getting-started.md). LiteLLM's [proxy quickstart](https://docs.litellm.ai/docs/proxy/quick_start) explains its Chat Completions interface; a successful synthetic probe still does not prove tools or vision work in the bot.

### Stopping, restarts, and updates

- **Ctrl-C in the first terminal stops this proxy.** Closing that terminal, a reboot, or a computer update can also stop it. The configured bots then lose this endpoint.
- To restart it, rerun the foreground startup command and enter the same local proxy key. Changing that key requires updating ungrok's saved configuration too.
- This recipe deliberately installs **no** background service, auto-start job, or watchdog. It is suitable for a supervised first test, not bots expected to work while you are away. Use the direct OpenRouter route for the simpler setup, or arrange a separately reviewed supervised proxy deployment before relying on unattended work.
- A Grok Bot computer update may remove installed runtimes/packages even if user files remain. Recheck Python, the venv, the proxy process, `./ungrok doctor`, and `./ungrok probe`; follow [update recovery](updates.md). Do not assume an open terminal or saved config proves that the process survived.

## Common mistakes

| Symptom | Check |
| --- | --- |
| Connection refused | The proxy must be running on the remote computer, with the correct loopback port. Direct OpenRouter needs no local process. |
| HTTP 401/403 | Check which key is required: OpenRouter key for OpenRouter, local proxy key for LiteLLM. Also check account/key restrictions. |
| Unknown model | Use the exact OpenRouter model ID, or `my-claude` for the proxy alias. The proxy's Anthropic model ID is a separate setting. |
| HTTP 429 / credits exhausted | Check provider billing, key limits, and rate limits. Do not repeatedly retry a bot loop. |
| Text works, tools/images fail | Check the chosen model and serving provider support those features, then run small separate tests. |
| You updated the computer | Recheck both the host patch and any optional proxy. They are separate components. |

Do not post raw proxy logs publicly. Third-party logs may contain request details even though ungrok suppresses provider response bodies in its own errors.
