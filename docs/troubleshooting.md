# Troubleshooting

Start with read-only `./ungrok doctor`. Fix the prerequisite before repeating setup.

| Symptom | Next check |
| --- | --- |
| Wrong platform or missing host | Use Grok Bot's remote Linux terminal, not your Mac. |
| Unknown layout or old hook | Stop and follow [migration](updates.md). |
| Native client missing | Check its absolute path; install the official client with approval. |
| Mac logged in, remote fails | Sign in as the remote host user through the official client. |
| Wrong auth type | Use subscription sign-in. Do not supply credentials, proxy overrides, or another billing route. |
| Native execution refused | Check exact Claude Code 2.1.263 or Codex 0.153.4, supported subscription auth, and runtime policy restrictions. Do not weaken checks. |
| Model/usage unavailable | Check the account's current access and quota. |
| Probe passes, app fails | Verify restart and fresh native-route logs; probe is not end-to-end. |
| Tools/images fail | Mark that workflow unverified; text success does not prove it. |
| Attachments stay staged locally | Upload precedes inference. Check desktop connectivity and avoid duplicate sends. |
| Restart refused | Refresh the exact host PID and supervisor; do not kill generic processes. |
| Rollback hash mismatch | Preserve files; never restore an old host across an update. |

Report the exact commit, native-client version, sanitized error, and separate login/probe/app outcomes. Never upload auth stores, login codes, keys, tokens, raw conversations, or private backups. [Private security reports](../SECURITY.md)
