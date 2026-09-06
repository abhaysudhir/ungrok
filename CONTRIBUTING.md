# Contributing

Work on native subscription sign-in through official Claude Code/Codex clients and Grok-host tool execution. Do not add key onboarding, token extraction, generic endpoint proxies, or fallback billing.

Use Python 3.10+ and the Node versions in CI. Run the current suite against fake clients and synthetic fixtures:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.cjs
python3 -m py_compile ungrok.py
git diff --check
```

Install only declared test dependencies. Never use personal auth files or conversations as fixtures.

Native flags need evidence from the exact binary, official docs, and behavioral tests. Prove tools are disabled; do not rely on a prompt, sandbox label, or text answer. Test host-tool translation, cancellation, and bounded subprocess output.

Installer work needs refusal, idempotence, interrupted writes, update, and rollback tests. Preserve applicable MIT notices and [provenance](vendor/UPSTREAM.md).

Ask before live subscription usage, shared-host mutation, or restart. Use harmless text/tool/image/follow-up tests and fresh route evidence. Follow [release checks](docs/release-checklist.md); old compatibility results do not transfer. Keep tags immutable and review final-commit CI/artifacts.
