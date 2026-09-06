# Contributing

Start with a small, reproducible failure or a sanitized compatibility report. Check existing issues first.

## Local development

Python 3.10+ and Node 20+ are used in CI. The core CLI and adapter use standard libraries; large-image resizing uses optional Pillow.

```sh
python3 -m pip install -r requirements-images.txt
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.cjs
python3 -m py_compile ungrok.py
node --check vendor/xai-prompt-session.cjs
git diff --check
```

The CLI deliberately refuses live installation on macOS. Tests create temporary synthetic Linux-host fixtures and mock the platform check. Do not point tests at a real host or use real credentials.

## Changes worth making

- A new host insertion point needs a sanitized fixture and refusal tests. Do not distribute an entire proprietary host bundle.
- A new endpoint needs tests for text, SSE, tool deltas, error handling, and credential boundaries. A model-list response is not sufficient.
- Installer changes need idempotence, interrupted-write, update, and rollback tests.
- Keep API keys out of arguments, logs, test output, and examples. Do not add automatic credential imports.
- Preserve the upstream MIT notice when changing the adapter, and record differences in `vendor/UPSTREAM.md`.

Keep PRs focused. Explain what changed, how you tested it, and any remaining uncertainty. Use conventional commit subjects such as `fix(recovery): reject modified backups`.

## Release checks

1. Run all tests from a clean checkout and check CI.
2. Check public files and git history for secrets and personal data.
3. Review README commands against the actual CLI.
4. Record whether live end-to-end verification was performed. Do not relabel fixture tests as a live test.
5. Tag only the reviewed, passing commit. Publish the candidate as a GitHub **prerelease**, with the exact commit and unresolved live-test gaps in its notes. Attach a source archive and its SHA-256 checksum; verify both after upload.
6. For a stable release, record a clean current-version host installation, real app text/tool/image requests, cancellation/follow-up, repeated setup, supervised restart, post-update repair, and rollback using the hardened path. The legacy compatibility patch's live results do not replace these checks.

Keep release tags immutable. Publish a new candidate for changed code rather than moving a tag. Review dependency-update PRs separately, including their runtime requirements; a green test run is evidence, not automatic merge approval.

A release must not change users' live Grok computers automatically.

Build the source archive from a clean, committed checkout:

```sh
python3 scripts/build_release.py --output-dir /path/to/new-release-output
```

The output directory must not already contain the archive or `SHA256SUMS`. The script packages only committed files at `HEAD`, uses the committed CLI version, and fixes gzip timestamps. Build twice in different directories and compare hashes before uploading. Checksums detect changed downloads; they are not a cryptographic signature or proof of maintainer identity.
