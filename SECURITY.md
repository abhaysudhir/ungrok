# Security

ungrok changes a host with access to conversations, files, browser sessions, and connected services. Read the code and run as its authorized owner, without sudo.

Use [GitHub private vulnerability reporting](https://github.com/abhaysudhir/ungrok/security/advisories/new). If unavailable, request a private channel without sensitive public details. No response-time guarantee is offered.

## Native boundaries

The official Claude Code or Codex client owns subscription sign-in and refresh. ungrok must not extract, store, intermediate, or publish its tokens. No API-key onboarding or fallback is supported.

Native inference must not become a second tool executor. Runtime controls must disable independent tools, MCP, and applicable hooks. A prompt or read-only sandbox alone is insufficient. Keep unverified runtimes blocked; Grok's host remains responsible for tools.

Conversation, tool, and image data reach the selected provider. Native clients and the host may store their own logs/state. Review their settings; native sign-in is not a privacy guarantee. Processes sharing the host user may access native credentials.

Configuration has provider/path/model rather than credentials, but private backups and logs can expose data. Keep them out of public archives. Do not collect other people's subscription logins or offer token-backed shared access. [Policy sources](docs/providers.md)

Auth/quota failure or invalid native output must stop without alternative billing. An update removing the hook can restore stock routing. This is not a billing guard.

The alpha has no independent security audit or stable-support commitment. Report exact commits and native-client versions with synthetic sanitized reproductions.
