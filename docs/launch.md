# Launch copy

Drafts for the maintainer to review and post. Nothing in this file has been posted automatically. This is prerelease copy; publish it only after the candidate tag, source archive, checksum, and CI result are verified.

## Repository description

Bring your own model to Grok Bot. Unofficial host patch with compatibility checks, update recovery, and rollback.

## Short announcement

I made ungrok: an unofficial way to point Grok Bot at an authorized OpenAI-compatible provider.

It patches the shared remote host and leaves the desktop app alone. You get setup checks, backups, post-update repair, and rollback.

It's an alpha prerelease. The legacy compatibility repair has narrow live results; the hardened new-install path still needs live end-to-end testing. Computer updates can break it. I'd love help testing compatible endpoints and improving recovery.

https://github.com/abhaysudhir/ungrok

## Longer introduction

Grok Bot gives your assistants a shared computer. ungrok lets you configure the inference endpoint used by a custom host adapter.

The project grew out of a working custom-provider setup that needed repair after a computer update. I wanted the repair steps to be inspectable and repeatable: check the current host, back it up, patch it, restart deliberately, then verify a real bot request.

ungrok is an unofficial alpha. It requires an authorized OpenAI-compatible Chat Completions endpoint with streaming and tool support. It does not supply a model, replace Grok's infrastructure, guarantee future update compatibility, or promise zero Grok charges. The new hardened implementation still needs live end-to-end verification.

If you try it, start with the compatibility notes and keep the rollback instructions handy. Useful contributions include sanitized compatibility reports, endpoint tests, and fixes that make failure easier to understand.

https://github.com/abhaysudhir/ungrok

## Demo checklist

Record a short demo only after the published code has passed a live test. Show the configured model, a successful readiness check, a harmless in-app request, and matching fresh route evidence. Label endpoint smoke tests separately from app tests.

Use a clean demo account or synthetic data. Hide credentials, personal bot names, connected-service content, private endpoints, and browser profile details. Review every frame before posting.

Do not claim “any model,” “free Claude,” “zero Grok charges,” automatic update survival, or a working live demo before those claims have evidence. Change the testing-status sentence in these drafts only when the published implementation has actually been tested.
