# Ask a coding assistant to set up ungrok

Copy the prompt below into a coding assistant that can inspect files and run commands. It will still need access to **Grok Bot's remote Computer terminal**. Access to your Mac terminal alone is not enough.

The assistant should guide you through provider choice and private credential entry. Never paste an API key, subscription login token, or credential file into the chat.

## Setup prompt

```text
Help me install ungrok v0.1.0-rc.2 for my Grok Bot computer.

Treat this as an experimental, privileged host change. Work in phases and stop
on failed checks. Do not claim access, compatibility, or success without evidence.

1. Establish my choices before changing anything.
   Ask which provider/model I want, whether I already have an authorized API or
   compatible gateway, and what spending limit I am comfortable with. Explain
   provider costs are separate from Grok Bot costs. Do not promise zero Grok
   charges. Help me configure a provider-side spending limit if available, but
   do not claim a soft alert is a hard cap. Ask before creating paid resources,
   buying access, or installing a proxy. Use current official provider docs.
   Read ungrok's docs/providers.md for the supported setup approach. Native
   Anthropic Messages API is not a direct Chat Completions endpoint. Do not import
   subscription login credentials or assume every OpenAI-compatible API works.

2. Establish the correct machine and access.
   The install target is Grok Bot > Computer > Terminal on its shared remote
   Linux computer, not my Mac. The desktop app bundle must remain untouched.
   Tell me which terminal you can actually operate. If you cannot operate the
   remote terminal, give me one bounded command at a time and ask for sanitized
   results. Do not invent SSH access or expose an unauthenticated public endpoint.
   Confirm Linux, the current user, and the real host/data paths. Do not use sudo
   to bypass ungrok's ownership checks.

3. Inspect a pinned checkout and prerequisites.
   Clone https://github.com/abhaysudhir/ungrok at tag v0.1.0-rc.2, record the full
   commit SHA, and compare it with the release notes. If the tag is unavailable,
   stop; do not substitute main. Read README.md, docs/getting-started.md,
   docs/providers.md, docs/compatibility.md, docs/updates.md, and SECURITY.md.
   Check Git, Python 3.10+, and the existing host Node runtime. Use the original
   host runtime (/exec-daemon/node when present); do not replace or upgrade it
   speculatively. Check ./ungrok --help and run read-only ./ungrok doctor.
   Classify missing configuration separately from an unsupported host or an old
   provider patch. Never force an insertion or stack patches. If dependencies
   are missing, explain what is needed and install only with my approval.
   For large images, install the release's requirements-images.txt into the
   python3 environment available to the host, not just an unrelated local shell.
   Keep the exact checkout and private recovery material for later rollback.

4. Configure privately and ask before mutation.
   Explain that all bots sharing this computer may be affected and that prompt,
   image, and tool data go to the chosen endpoint. Ask for my explicit consent
   before patching the shared host. Use an endpoint/model I have chosen and am
   authorized to use. Have me enter the key directly in the hidden terminal
   prompt, or create a private mode-600 config file outside the checkout. Never
   ask me to paste the key into chat, put it in arguments, or print the file.
   Follow the documented config format; do not invent options. Use ./ungrok setup
   only after compatibility checks. Preserve its fresh current-version backup.
   Setup must not be described as a restart or a verified working installation.

5. Verify in stages and restart only when idle.
   Explain that ./ungrok probe sends a synthetic paid request, then run it with
   my provider choice confirmed. Stop on failure. A probe tests neither streaming
   nor tools and cannot establish Grok Bot routing. Before a restart, ask me to
   finish active work and pause routines where possible. Confirm I am ready for
   interruption. Inspect the current exact host PID and supervisor, then use the
   documented ./ungrok restart --pid ... command. Do not kill generic node
   processes or start a duplicate manual host.
   After reconnection, establish a fresh log boundary and send the documented
   harmless in-app text diagnostic. Match its reply with new [ungrok] session
   evidence showing the intended model and endpoint. Then, with my approval,
   test a harmless tool operation and a small synthetic image with an objectively
   checkable answer. Do not send private files as test material. If I decline a
   test or you cannot access the UI/logs, mark that path unverified. Never call
   the installation fully verified from a ping, model list, probe, or reply alone.

6. Hand off or recover safely.
   Report the pinned commit, what changed, the private backup location, tests
   actually performed, and remaining gaps without exposing secrets. Leave me the
   update and rollback instructions. If verification fails, explain the failure
   and use the documented rollback only with my approval. Restore only the
   recorded host version whose hashes match, restart separately when idle, and
   explain that stock-provider routing resumes. Never restore an older host
   bundle across an update or use Computer Reset as a routine fix. Stop and ask
   when safe recovery needs access or a decision you do not have.
```

## What the assistant cannot guarantee

The release is experimental. An assistant cannot make an unsupported host layout safe, grant provider access, or prove billing attribution from a successful reply. The legacy compatibility repair's live results do not verify the hardened new-install path. Keep [compatibility](compatibility.md) and [recovery](updates.md) handy, and expect to participate in credential entry and access checks.
