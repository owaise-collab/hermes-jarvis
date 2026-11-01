# How we built Hermes Jarvis

## Starting point — November 1, 2026

The machine already had native Hermes, a local llama.cpp model, Whisper, Piper, Desktop launchers and a separate local voice guide. We inspected the installation and source documentation rather than installing a duplicate stack. The reference environment uses Agents-A1-4B Q8_0 on a Vulkan GPU and CPU speech engines.

The user requested a Jarvis-style local setup inspired by two Instagram carousels, and then selected a **separate repository**. Both reference carousels were navigated slide by slide: one explained components, the other put skills and organized knowledge before voice, routing and interface. Their offered setup/code was not obtained or assumed.

## Decisions

1. **Keep Hermes intact.** Extend it with a skill, additive instructions, an ordinary file vault and a sidecar. Do not patch upstream agent or desktop internals for branding.
2. **Reuse the existing local engines.** Use the same llama.cpp server, cached Whisper and cached Piper. Do not install a classifier or second speech system merely to match a diagram.
3. **Make routing explicit.** Note capture/search/brief are deterministic. Model workflows are selected by the user and have no arbitrary tools. Full tool-enabled requests stay in native Hermes with its existing permissions.
4. **Keep context inspectable.** The user selects the notes sent to each model request; each output records its request and input note paths.
5. **Keep publication separate from private state.** Source and documentation live under a standalone checkout; data stays under the Hermes home.

## Implementation sequence

First built `core.py`: loopback-only model access, Markdown capture/search, context selection, deterministic brief and a single-active-job manager. Then added the HTTP interface with session tokens, Host/Origin checks and bounded inputs. The frontend uses no framework/CDN and renders untrusted text safely. It includes responsive layout, explicit voice capture and a print stylesheet.

Speech adapters use the installed Python packages directly. Whisper receives in-memory PCM samples and must find its model locally. Piper receives an explicit cached voice file and returns a WAV in memory. The browser never invokes Web Speech Recognition or browser-selected TTS voices, whose processing location could be unclear.

The installer discovers the existing PM runtime, preserves unrelated YAML settings, backs up five installation files, pins supported local routes and appends a vault section to SOUL. The rollback manifest records both pre-install and installed text so later user edits are detected rather than overwritten.

## Problems encountered and resolved

- **Sandboxed process environment:** the execution environment redirected default app-data locations and blocked direct loopback networking. We supplied the actual Hermes home explicitly and ran host network checks through the permitted execution path. This was not a reason to replace a working runtime or call a cloud model.
- **Windows line endings:** the first rollback regression found a mismatch in a generated command launcher. Normalized generated text and reran the full behavior suite; the final 16 tests passed.
- **Runtime packaging:** system Python did not have the speech/YAML packages. Used the selected Hermes PM environment rather than installing dependencies into an unrelated interpreter.
- **Missing microphone:** device discovery showed no input endpoint. Live dictation cannot be certified until a microphone is connected. Synthetic local speech/transcription is tested separately.

## Design rationale

Deep teal, ivory and restrained terracotta distinguish the workspace from the references. A simple geometric emblem is decorative; actual readiness comes from the model health check. The interface exposes useful outcomes instead of artificial token charts or meaningless animated metrics. The footer and system view explain the panel's role and limits.

## Reproduce and extend

Start from the foundation guide, clone this kit, preview installation, install, launch, run the behavior suite, then perform the documented live checks. When adding a workflow, update `WORKFLOWS`, the selector and its acceptance examples together. Keep new integrations explicit about network access. A real scheduler, multi-user dashboard, semantic index or Arabic speech model should be added only with a concrete consumer and appropriate tests.

The detailed current verification results and limitations live in [verification](06-verification.md), rather than treating every implemented feature as automatically tested hardware behavior.
