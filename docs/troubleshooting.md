# Troubleshooting

Start with `./ungrok doctor`. It does not change the host. Fix the reported prerequisite before repeating setup, repair, or restart.

| Symptom | Check and next action |
| --- | --- |
| Host file missing | Confirm you are in Grok Bot's remote Linux terminal, not your Mac terminal. Check the actual host path. Stop if the layout has changed. |
| Unsupported or ambiguous insertion point | Preserve the current host. Open a sanitized compatibility report; do not force a patch or replace it with an older bundle. |
| Host already has a provider patch | Follow [migration](updates.md#migrating-an-existing-provider-patch). ungrok refuses to stack an upstream `xai` patch with its own. Establish a stock host for the current version first. |
| Node or Python is unavailable | Use Python 3.10 or newer and the host's Node runtime. Supply an absolute `--node` path before the command if needed. A computer update may have removed packages. |
| Configuration missing | Run interactive `setup` or pass a private configuration file. `repair` cannot recreate lost credentials. |
| Credential file rejected | It must belong to the current user, be a regular file rather than a symlink, and be private with mode `600`. Use only supported, unique `KEY=value` entries without quotes, `export`, or extra whitespace. |
| Private state directory rejected | Use a real directory you own with mode `700`. Run as the host owner, without `sudo`; do not loosen the checks. |
| Probe cannot connect | Check that your authorized endpoint is running and reachable from the remote computer. `127.0.0.1` means that computer, not your Mac. |
| Probe returns HTTP 3xx | Supply the final endpoint URL. The probe refuses redirects and ignores machine-wide HTTP proxy settings. |
| Probe returns HTTP 404 | Verify the base URL. ungrok appends `/chat/completions`; include `/v1` only where your endpoint requires it. |
| Provider returns HTTP 413 | Reduce the number of images or conversation size. Install the optional image dependency and verify the helper; per-image resizing cannot guarantee the whole request fits every provider. |
| Large image requires resize helper or resize fails | Check the recorded helper and install `requirements-images.txt` into the host's `python3` environment. Check [image limits](compatibility.md#inline-images). The error intentionally omits image contents. |
| Authentication rejected | Verify the key's permissions and provider account status privately. File presence alone does not prove valid authentication. |
| Model rejected | Check the provider's current catalog and exact model identifier. Never infer availability from a name in a screenshot or old guide. |
| Streaming or tool errors | Confirm OpenAI-compatible Chat Completions, SSE streaming, and tool-call support. Native Anthropic Messages API is a different protocol. |
| Setup succeeds, bot still uses stock route | Setup does not restart. Verify the host restarted, then correlate a fresh app test with new custom-provider log evidence. |
| Restart refused | Verify the PID is current, is the exact host, and has the supported same-user supervisor. Do not kill unrelated processes. |
| App does not reconnect | Inspect the host and supervisor logs. Do not start a second manual host. Roll back only if the recorded current-version backup passes checks. |
| Worked before computer update | Run `doctor`, restore missing prerequisites, then follow [update recovery](updates.md). |
| Rollback refuses a hash mismatch | The host or backup changed. Preserve both and investigate. Do not force an older host over the current one. |
| Checkout has a different adapter | Keep the installed checkout and follow [upgrading ungrok](updates.md#updating-ungrok-itself). Roll back with that version before installing a changed adapter. |
| Installed adapter was modified | Repair will not overwrite a changed adapter. Preserve the file and investigate the change; a missing recorded adapter can be restored, but an unexpected one needs review. |

## A successful reply is not routing proof

Check three different things:

- `doctor`: local configuration and host readiness.
- `probe`: the endpoint can answer a synthetic, non-streaming request. This can incur usage and does not check tool support.
- A fresh in-app request with matching new `[ungrok] session model=... endpoint=...` logs: evidence that the app used the intended route for that request.

None of these alone proves every background, voice, browser, or tool path uses that provider. Billing dashboards can lag or combine unrelated activity; they are not a substitute for route evidence.

## Report a bug without leaking data

Include the ungrok commit, Python and Node versions, the failed command with secrets removed, the exact sanitized error, and whether the problem followed a computer update. Say whether a standalone probe works and whether the app reconnects. Include the client version as context, not as proof of the host version.

Review diagnostic output before posting it. Replace personal paths, endpoint hostnames if private, account names, bot names, conversation text, and connected-service content. Share only the shortest log excerpt needed to show the failure.

Do not upload `ungrok.env`, API keys, cookies, OAuth files, raw host logs, host backups, or credential archives. Do not paste a full environment dump. If a key was exposed, revoke it through the provider before removing the public copy.

Use the repository's security reporting instructions for vulnerabilities or accidental secret exposure, rather than opening a public issue containing sensitive details.
