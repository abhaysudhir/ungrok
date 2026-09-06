# OpenManus comparison

This describes built-in support in the reviewed OpenManus commit `3309bf4e416fb1c74b008f3e86494439a31bad53`, not forks or integrations someone could build.

| Built-in capability | OpenManus |
| --- | --- |
| Integration with the existing Grok Bot app | No |
| Integration with the existing Grok Bot computer | No |
| Guided ChatGPT subscription sign-in | No |
| Guided Claude subscription sign-in | No |
| Open source | Yes |

The reviewed setup and client implementation use model API configuration; they do not contain the native subscription or Grok integration paths listed above. Sources: [README at the reviewed commit](https://github.com/FoundationAgents/OpenManus/blob/3309bf4e416fb1c74b008f3e86494439a31bad53/README.md), [LLM clients](https://github.com/FoundationAgents/OpenManus/blob/3309bf4e416fb1c74b008f3e86494439a31bad53/app/llm.py), [configuration](https://github.com/FoundationAgents/OpenManus/blob/3309bf4e416fb1c74b008f3e86494439a31bad53/app/config.py), [license](https://github.com/FoundationAgents/OpenManus/blob/3309bf4e416fb1c74b008f3e86494439a31bad53/LICENSE).

ungrok's native subscription integration is being implemented. This table is not a claim that both ungrok paths are live-verified. See [current evidence](compatibility.md). OpenClaw is a different project and already documents native subscription integrations; do not apply this table to it.
