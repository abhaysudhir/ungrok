# Existing upstream installs

`upstream-image-stream.patch` is a compatibility repair for the original adapter at BlockedPath/grok-bot-setup commit `d9119f9632c635473213c57ace336028f7278abd` only. It preserves that adapter's existing configuration and authentication behavior; it is not the hardened ungrok adapter or a new-install guide.

Expected original SHA-256: `706758a5d95601b7aed989f582ce6abf2b672842f02d85a0e4a4590011cc07a5`.

Expected patched SHA-256: `48f430f98147d02e493963b3b3eef9b483ffaed48501bb1d05a5a9e3ecd4c526`.

The patch fixes binary image expansion, adjacent-message image loss, buffered streaming, and cancellation. Large inline images require Python 3 and Pillow plus `scripts/resize_image.py` installed next to the adapter as `ungrok-resize-image.py`. Originals are unchanged. Back up the exact adapter before applying; validate the staged file with the host's Node runtime before replacement. Do not apply to a different hash. A supervised host restart is required and interrupts active work.

This compatibility path passes local regression tests. On September 5, 2026, a supervised live host restart loaded the matching patched hash. Two consecutive app diagnostics returned their expected markers. A second message sent one second after a counting request superseded it and returned `FOLLOWUP_OK` five seconds later. This verifies that narrow multi-message case, not every steering or image path. The hardened public adapter and installer still need their own live end-to-end verification. For new installations use the main onboarding guide and authorized API credentials.
