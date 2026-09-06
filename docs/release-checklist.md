# Release gates

## v0.1.0-rc.2

- [x] Installer, adapter, and onboarding reviewed separately.
- [x] Confirmation races and backup/manifest validation covered by regression tests.
- [x] Image retention, invalid input, cancellation, malformed streams, and tool arguments covered by regression tests.
- [x] Credentials and personal content excluded from the source tree.
- [x] MIT notices retained; security reporting enabled on GitHub.
- [x] Source packaging uses a committed version and repeatable archive/checksum output.
- [x] Banner inspected in a browser after correcting the plug mark.

Publication requires green CI for the exact release commit, two identical archive builds, an extracted-archive smoke test, and a downloaded release checksum check. The GitHub release records the final commit and verification results. Do not move a published tag.

## Before stable support

These checks must use the published hardened installer and adapter on a recoverable, clean Grok computer. The legacy compatibility repair is a different path.

- [ ] Record the client and host version and confirm a known stock insertion point.
- [ ] Install with an authorized endpoint, run `doctor` and `probe`, and restart the verified supervised PID.
- [ ] Verify real app text, tool, image, and in-flight follow-up requests against fresh route evidence.
- [ ] Repeat setup and test failed-install recovery without losing configuration or original files.
- [ ] Test repair after a supported host update and verify a new app request.
- [ ] Roll back, restart, and verify that original routing resumes.

Stop or roll back on missing image content, lost user turns, stuck requests, invalid tool calls, changed host layout, missing recovery backups, or routing that cannot be verified. Never reset a user's computer to manufacture a clean test environment.

The Mac upload path is separate. This release does not add automatic pre-upload image resizing or change Grok Bot's desktop client.
