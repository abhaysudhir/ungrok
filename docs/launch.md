# Native-alpha launch draft

Do not post this as a stable or fully tested release.

## Description

Bring your Claude or ChatGPT subscription to Grok Bot through official native clients. Experimental shared-host integration.

## Draft

I'm rebuilding ungrok around subscriptions: Claude through Claude Code and ChatGPT through Codex.

You keep the Grok Bot app and computer. Sign-in stays inside the official client, and Grok remains responsible for tools.

Both native paths are implemented. Codex 0.153.4 passed all five local subscription checks. Claude Code 2.1.263 passed four, including actual images and image follow-up; its tool-result follow-up was refused by a provider safeguard. Linux Grok host end-to-end testing is still pending. This is alpha, with those limits stated up front.

https://github.com/abhaysudhir/ungrok

Before posting, verify the exact release, archive/checksum, CI, and current compatibility status. Use synthetic demo data. Do not advertise unlimited use, zero Grok charges, token proxies, or support proven only on the old adapter.
