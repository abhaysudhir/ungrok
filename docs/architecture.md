# Native-client architecture

The 0.2 alpha uses official Claude Code or Codex clients for subscription-backed inference. The client owns sign-in and refresh.

```text
Grok Bot app -> shared host -> ungrok adapter -> official native client
                               <- text or validated host-tool request
              Grok host tools <- adapter
```

## One tool executor

Each host step is a native inference call with conversation context and host-tool descriptions. The native client returns structured text/tool requests; the adapter validates and translates them into Grok's session interface. Grok remains the tool executor.

The native client must not run a second tool loop. Enforced runtime controls must disable its tools, MCP integrations, and applicable hooks. Prompt instructions alone are insufficient; a read-only sandbox is not proof all tools are disabled. A runtime remains blocked until its installed version's actual behavior establishes this boundary.

Both native controls are implemented for exact versions: Claude Code 2.1.263 and Codex 0.153.4. Other versions fail closed. Claude requires supported native subscription auth and rejects detected managed-policy configurations. These restrictions still need validation in the target Linux Grok environment.

Each host step starts a fresh, stateless native invocation and buffers its structured result. Text and host-tool requests are delivered after validation; this is not real-time token streaming. Startup overhead and repeated context can affect latency and quota. The installed adapter loads its adjacent native runtime modules rather than an HTTP token proxy.

## Authentication and failure

Configuration selects `UNGROK_PROVIDER`, absolute `UNGROK_CLI`, and optional `UNGROK_MODEL`. The official binary handles the owner's subscription login on the same remote computer. No token extraction, generic endpoint proxy, or API fallback is part of this architecture.

Auth failure, unsupported runtime, invalid structured output, quota exhaustion, or native tool activity must stop the request. An update that removes the hook can restore stock routing; ungrok cannot enforce rules when absent.

## Evidence

Test native auth, tool isolation, parsing, subprocess bounds, cancellation, and host-tool translation separately. Then test real app text, tools, images, and follow-ups. Earlier legacy-adapter results do not verify this architecture.
