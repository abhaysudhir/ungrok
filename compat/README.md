# Existing upstream installs

`upstream-image-stream.patch` is a compatibility repair for the original adapter at BlockedPath/grok-bot-setup commit `d9119f9632c635473213c57ace336028f7278abd` only. It preserves that adapter's existing configuration and authentication behavior; it is not the hardened ungrok adapter or a new-install guide.

Expected original SHA-256: `706758a5d95601b7aed989f582ce6abf2b672842f02d85a0e4a4590011cc07a5`.

Expected patched SHA-256: `5f9d78357cd55cd5e74312280319882cd68f5a30e69900a7dfd7ae047c8a0e94`.

The follow-up repair excludes image bytes from the text budget and prevents trimming the latest real user request after assistant/tool messages. It retains at most 20 recent images, supports ten images across adjacent upload batches, and caps the actual post-resize request separately at 16 MiB. This fixes a live failure where the bot acknowledged images and then lost the request on its next call. The new sequence is covered by regression tests. After installing the matching hash and restarting the live host on September 5, a six-image app upload completed and the bot returned specific content from each page while recognizing four earlier pages. A sample was independently checked against the original image. A separate post-reply follow-up was not run because the user resumed editing the chat.

The patch fixes binary image expansion, adjacent-message image loss, buffered streaming, and cancellation. Large inline images require Python 3 and Pillow plus `scripts/resize_image.py` installed next to the adapter as `ungrok-resize-image.py`. Originals are unchanged. Back up the exact adapter before applying; validate the staged file with the host's Node runtime before replacement. Do not apply to a different hash. A supervised host restart is required and interrupts active work.

This compatibility path passes local regression tests. On September 5, 2026, a supervised live host restart loaded the matching patched hash. Two consecutive app diagnostics returned their expected markers. A second message sent one second after a counting request superseded it and returned `FOLLOWUP_OK` five seconds later. This verifies that narrow multi-message case, not every steering or image path. The hardened public adapter and installer still need their own live end-to-end verification. For new installations use the main onboarding guide and authorized API credentials.
