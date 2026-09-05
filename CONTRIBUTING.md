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
5. Tag the reviewed commit and attach a source archive with its SHA-256 checksum.

A release must not change users' live Grok computers automatically.
