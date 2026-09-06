# Guided setup

**This guided flow is an unreleased change. It is not included in the published v0.2.0-alpha.1 archive.** It reduces the commands you need to run, but real Grok-host end-to-end verification is still pending. Do not treat this as a stable release.

You need a compatible Grok Bot computer and an eligible Claude or ChatGPT subscription. The change affects **every bot on that shared computer**. Your Mac app stays unchanged. Conversations and tool results go to the provider you choose, and its usage limits still apply.

## Start

Open **Grok Bot → Computer → Terminal**, not Terminal on your Mac. In the reviewed ungrok checkout containing this change, run:

```sh
./ungrok start
```

If you do not have that checkout, ask your setup assistant to help obtain and review it. Do not use the old alpha download and expect this command to exist. A pinned download command will be added when this change is released.

The guide walks you through choosing your subscription and model, installing the supported official client if needed, signing in, and enabling ungrok. It asks before downloads, changes to your shared host, subscription-consuming checks, and restart. You do not need to find executable paths or process IDs.

Choose the **default model** unless you already know a model your account supports. Advanced users can enter a model name. There is no account-specific model catalog yet.

Complete the official sign-in yourself. Never paste login codes or credentials into a chat. You can stop before any confirmation; earlier completed steps, such as client installation or sign-in, are not automatically undone.

Before agreeing to apply settings, finish active bot work and pause routines. On an existing ungrok installation, new sessions can use changed provider/model settings immediately, even if you decline restart. Keep work paused until verification is complete. The guide only restarts a host it can identify and verify safely. If it cannot, it stops instead of asking you to guess.

## Check it in Grok Bot

After the computer reconnects, send an idle bot:

> Reply exactly UNGROK_OK. Do not use tools or message other bots.

A reply alone does not prove ungrok handled it. Have your setup assistant check fresh `[ungrok] native session` evidence for your chosen provider, then test a harmless tool and a small test image with your approval. Keep important routines paused until those checks pass.

**The guide does not mark the app verified automatically.** A successful sign-in, test prompt, or restart is only that step's result.

## Change your choice later

Run `./ungrok start` again from the same checkout. Review the existing provider and model, choose the change, and follow the checks and restart prompt. The choice still applies to all bots on that host.

## If it stops

Read the message before retrying. An unsupported host or client, missing prerequisite, failed sign-in, or ambiguous host process needs attention; do not bypass the check. Ask your setup assistant for help and share only sanitized error text, never credential files or login output.

Python 3.10+, Git for obtaining the source, and suitable Node/npm must already be available. The guide does not use sudo, replace Grok's runtime, or reset the computer. Large-image resizing also needs [Pillow](getting-started.md); installing the native client alone does not provide it.

The terminal and running Grok host must both be able to use those dependencies. A dependency check in your terminal does not prove the host has the same environment; your setup assistant must check this during app verification.

For manual controls, use [the detailed guide](getting-started.md). To restore original routing, follow [recovery](updates.md) using the same checkout and retained backup. Do not delete login folders or use Computer Reset as a setup fix.
