# Native-alpha release checks

0.2.0-alpha.1 replaces the earlier design. Old checks do not establish native support.

- Accept only native provider/client/model configuration; reject credentials, endpoints, and foreign hooks.
- Verify the owner's subscription login through official status interfaces.
- Prove native tools, MCP, and applicable hooks are disabled by enforced controls. Block unproven runtimes.
- Test structured output, host tools, images, auth/quota failure, cancellation/follow-ups, subprocess bounds, and secret-safe errors.
- Test clean-host setup, repeat setup, interrupted writes, restart, post-update repair, and same-version rollback.
- Run final-commit CI and explicitly list live checks not performed.
- Review docs/examples/history for obsolete onboarding, credentials, and unsupported claims.
- Publish as alpha with immutable tag, exact commit, source archive, and verified checksum.
- Verify the uploaded release and artifacts. Publishing must not change live user computers.

A native probe or old image demo does not replace live native-path testing.
