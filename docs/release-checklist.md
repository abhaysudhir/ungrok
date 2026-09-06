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

## Guided setup release gate

- Run `./ungrok start` on a clean compatible Linux Grok computer for each advertised provider, with a person completing official sign-in.
- Check missing prerequisites, declined consent, failed download/login/probe, repeat setup, changed model, and ambiguous host detection. Preserve partial state and show the next safe step.
- Confirm that nobody needs to edit config files, find executable paths, or look up a process ID in the supported flow.
- Confirm supervised execution uses the same native account/profile as sign-in.
- Check fresh app routing, a harmless host tool, a small image, and recovery. Do not substitute mocked wizard tests.
- Before publishing, replace the unreleased source notice in `docs/easy-setup.md` with an exact immutable download and start command. Check it by copying the instructions into a clean terminal.
- Keep prerelease status until the live checks pass. The guided UI alone does not resolve the Claude follow-up verification gap.
