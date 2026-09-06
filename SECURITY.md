# Security

ungrok modifies a remote host that can access your conversations, files, browser sessions, and connected services. Treat this as privileged software. Read the code before running it, and do not run it with sudo.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/abhaysudhir/ungrok/security/advisories/new). Do not open a public issue containing credentials, raw conversations, or an exploit that exposes another user's data.

If private reporting is unavailable, open a blank security-contact request without sensitive details so a private channel can be arranged. There is no promised response-time SLA for this experimental project.

## Credential handling

- Setup reads API keys through a hidden prompt or a private mode-600 file. Keys are not accepted as command-line arguments.
- Configuration lives on the Grok computer in `~/sand-data/ungrok.env`. It is plaintext with restricted permissions, not a vault. Processes running as the same user can read it.
- Backups can contain old provider configuration. Keep `~/.local/state/ungrok` private and out of uploaded archives.
- The adapter never reads your Grok or Claude login files. It uses the explicit key in its configuration.
- Remote endpoints require HTTPS. Loopback HTTP is allowed for a proxy on the same computer. Redirects are not followed.
- The adapter logs session model and endpoint origin, not prompts, credentials, or provider error bodies. The host or provider may log data independently.
- Image resizing runs the local Python/Pillow helper on untrusted image data. It uses bounded input, pixels, output, and execution time, but it is not an OS sandbox. Keep the pinned dependency reviewed and use a host account you are authorized to modify.

## Boundaries

Your endpoint receives prompt and tool-result data. ungrok cannot enforce the provider's retention or privacy policy. Bots sharing the host share its route. A new host bundle may replace the patch and restore default inference. The injected hook fails on adapter errors while present; this is not a billing guard for other paths or after updates.

No telemetry or remote update check is built into the CLI. `probe` is an explicit network call to your configured endpoint. GitHub, cloned source, and external provider software have their own security boundaries.

Security fixes target the current development line and newest prerelease. There is no stable-support commitment yet. No version is represented as independently security-audited.
