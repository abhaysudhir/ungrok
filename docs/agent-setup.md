# Install with Grok Bot

Start with the copy-paste prompt in the [README](../README.md#option-a-have-grok-bot-install-it). Paste it directly into a Grok Bot chat. The bot has access to its remote computer; you complete official sign-in and the restart handoff yourself. This flow is experimental and has not passed a clean-computer test. Usage has not been measured.

The detailed instructions below also work as a checklist for an external coding assistant with authorized remote terminal access. They do not authorize a bot to restart the host running its own conversation.

The unreleased working source has a [guided `./ungrok start` flow](easy-setup.md) for a person at the terminal. It is not an unattended bot installer and is not in the published alpha archive. For the bot-led flow, follow the published release's individual commands and the handoff below.

```text
Help me set up ungrok 0.2.0-alpha.1 with my Claude or ChatGPT subscription only.

Ask which subscription I want, whether its official client is installed on the
remote Grok computer, and whether I accept using subscription quota for bots.
Do not offer API keys, credit purchases, endpoint proxies, or token extraction.
Check current official docs and account limits. Do not promise unlimited usage
or zero Grok charges, and ask before changing paid settings.

Read README, providers, getting-started, compatibility, architecture, updates,
and SECURITY from the exact reviewed alpha checkout. Record the full commit.
Do not use the superseded 0.1 release. If the tag is unavailable, ask for a
reviewed commit; do not pretend it exists.

Verify real remote Linux terminal access as the host owner. Leave my Mac app
untouched. If you lack remote access, give one bounded command at a time and ask
for sanitized results. Never invent SSH/UI access or use sudo to bypass checks.

Check Git, Python, the original host Node runtime, and official Claude Code
2.1.263 or Codex 0.153.4 exactly. Ask before installing missing dependencies.
Run read-only doctor and
classify missing config separately from unsupported layout or old hooks. Doctor
does not verify auth or network access; native login/status checks are separate.

Have me complete login claude or login chatgpt through the official flow on the
remote computer. Do not request, expose, copy, or proxy its credentials. Verify
subscription auth through the client. A successful login does not authorize
bypassing exact-version, auth, managed-policy, or tool-isolation checks.

Explain shared-host scope and provider data exposure; obtain consent before
setup. Have me finish other bot work and pause routines before any configuration
write: on an existing installation, new sessions can pick up changed settings
before a restart. Configure only provider, executable path, optional model. Preserve the
fresh backup. Before applying changes, save a credential-free recovery note
with the exact release/commit, checkout path, completed steps, and backup
location. No alternative billing fallback is allowed.

Run the synthetic probe after confirming quota use. Stop on failure. Before
restart, have me finish work and pause routines; obtain interruption approval.
If you are the bot running on this host, DO NOT restart it yourself. Verify
the exact host PID/supervisor, then give me the documented restart command
with the real PID and checkout path. Tell me to click Computer at the top
right of Grok Bot, open Terminal inside that remote computer, and run it
there. Wait for me to return and say "continue setup." Reinspect the actual
state before continuing; a saved note is not proof of completion. If the
restart command refuses, stop and recheck rather than bypassing it.
Never kill generic Node processes or start a duplicate host.

Verify a real app text diagnostic with fresh native-route evidence. With
approval, test a harmless Grok-host tool, its result/follow-up, a synthetic
image, and an image follow-up. Ensure the native
client did not execute independent tools. Mark unavailable/failed paths
unverified. Login, ping, probe, or a reply alone is not setup proof.

End with an unmistakable result. Only after all five checks pass, say:
"Setup complete — ungrok is working with [verified provider]."
Show the configured model, or "client default" if none was selected, and
one PASS line for each check. Say these tested features are ready to use
and the setting affects all bots on this computer. Do not infer an actual
model identifier from an unspecified client default. Do not claim every
routine, voice feature, or billing path has been tested or resume routines
without approval.

If any check fails or cannot be verified, say "Setup incomplete." List
what passed, the exact remaining issue, and the next safe step. Never
print the success report as though it were a result before running checks.

Report commit, changes, private backup location, actual tests, and gaps without
secrets. Ask before exact-version hash-checked rollback, restart separately
when idle, and explain stock routing resumes. Never force an old backup over
an update or use Computer Reset as a routine fix.
```

The native overhaul is alpha. An assistant cannot make an unsupported runtime safe or transfer old test results to the new route.
