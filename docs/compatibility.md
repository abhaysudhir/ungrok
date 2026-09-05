# Compatibility and evidence

ungrok is **alpha**. Its patch relies on private host internals, and the hardened ungrok implementation has not yet been verified end-to-end on a live Grok Bot computer. Do not treat the historical upstream result as a test of this code.

## Known image incident

An image-heavy request was reported to fail with HTTP 413, indicating that a request was too large for an upstream limit. Offline reproduction also confirmed that the earlier consecutive-user-message merge could discard structured images. That data-loss bug is a separate finding; it does not establish the cause of a computer crash or prove which component rejected the live request.

The image preprocessing path now has offline integration tests, including a real Pillow downsample and preservation of original message objects. Live recovery and end-to-end verification remain pending. Do not treat this change as a proven fix for every HTTP 413 or computer failure.

## Test status

| Component or workflow | Status |
| --- | --- |
| Historical upstream custom-provider route | Observed working for a plain-text bot reply and matching custom session logs. |
| Historical post-update repair | Observed working after a computer update in a client `0.43.0` context on September 5, 2026. This is not a universal host-version guarantee. |
| Hardened ungrok installer and adapter | New implementation; live end-to-end verification pending. See repository CI for automated test results. |
| Arbitrary OpenAI-compatible providers/models | Experimental. Compatibility depends on streaming, tools, model behavior, and gateway details. |
| Native Anthropic Messages API | Not directly compatible. Requires an authorized Chat Completions translation layer. |
| Voice, background paths, full browser/tool workflows | Not established by the historical text-reply check. Test each workflow separately. |
| Billing attribution or zero Grok usage | Not verified and not guaranteed. |

## Expected host layout

The default target is a Linux remote computer with `~/sand-host/host-main.cjs`, `~/sand-data`, Python 3.10 or newer, and a usable Node runtime. Run as the host owner, without `sudo`. Restart support requires a verified same-user parent running `sand-supervisor.mjs`. Global path overrides are available for inspection, but do not bypass compatibility requirements.

The patch checks the requested-model section containing `requestedModel` and `resolveSandRequestedModel`, together with a unique `createCursorInferencePromptSession` insertion point. If the expected pattern is absent or ambiguous, stop. Do not weaken the check to make a new bundle accept the patch.

Matching this pattern establishes where the patch can be inserted, not that a new host's session contract remains compatible. A syntax check, local fixture test, and real app test answer different questions.

Existing upstream `xai` hooks are refused. Migration requires a verified stock host of the current version; see [migration and backup cautions](updates.md#migrating-an-existing-provider-patch).

## Endpoint requirements

Provide an authorized base URL for an OpenAI-compatible Chat Completions endpoint, an exact model ID, and a nonempty API or local proxy key. The endpoint must handle SSE streaming and tool calls expected by the adapter. Remote endpoints require HTTPS; `localhost`, `127.0.0.1`, and `::1` may use HTTP. Credentials, query parameters, and fragments are forbidden in the URL. v0.1 supports `SAND_XAI_THINKING=disabled` only.

The standalone probe sends a non-streaming request and does not test SSE or tools. It ignores machine-wide HTTP proxy settings and refuses redirects. A successful probe is one prerequisite for live testing, not a provider compatibility certification.

ungrok does not bundle a proxy, create provider accounts, grant model access, or authorize subscription credential reuse. Provider support and terms can change. Confirm that your provider permits your integration and your intended data handling.

The adapter sends conversation and tool content to the configured endpoint. It does not replace Grok Bot's cloud computer, tools, routines, or orchestration. All bots sharing the modified host can be affected, and some paths may remain outside the adapter.

## Inline images

The adapter prepares request copies after message trimming. For inline `data:image/...;base64,...` URLs over 200,000 characters, it runs the installed `ungrok-resize-image.py` helper through `python3`, one image at a time. Development checkouts can use `scripts/resize_image.py` instead. The pinned optional Pillow dependency is listed in `requirements-images.txt`.

The helper reads and writes image data through pipes, without writing images to disk. It accepts JPEG, PNG, WebP, and GIF, uses the first frame of animated images, applies orientation, and emits a metadata-free JPEG with a longest edge of at most 1,568 pixels. Transparency becomes white. These changes can reduce fine detail; original files and original conversation objects are preserved.

Each image is limited to 20 MiB of decoded input and 40 megapixels, with a 4 MiB JPEG output limit before base64 encoding in the helper. The adapter limits helper stdout to 6 MiB and enforces a 20-second deadline per image. Cancellation stops the helper. Missing Pillow/helper, invalid data, or exceeded limits fail the request instead of forwarding the large original.

Smaller inline images pass through unchanged. Remote image URLs are never fetched by the helper. Reducing each image does not guarantee the combined request fits every provider's limit; a large batch or long conversation can still be rejected. Send fewer images when needed.

## Recording a new successful test

For a useful compatibility report, record:

1. The ungrok commit and relevant runtime versions.
2. Host layout and sanitized compatibility-check results, with client version listed separately.
3. The endpoint type and exact model ID, without credentials or private account details.
4. Whether setup, repeat setup, restart, repair, and rollback were actually tested.
5. A fresh app reply paired with matching new session logs.
6. Which harmless tool or browser workflows were tested, and which remain untested.

Do not publish a proprietary host bundle or personal logs as evidence. A report should state what ran and what was observed, without implying broader coverage.
