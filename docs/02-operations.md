# Installation, daily use and rollback

## Foundation

This kit expects working native Windows Hermes and its PM-managed runtime. For the tested local model, GPU setup, download checksums and speech setup, follow the [local voice foundation guide](https://github.com/owaise-collab/hermes-local-voice-guide). Do not run pip into a Hermes environment. Use Hermes PM for runtime repair or speech extras.

The reference machine has an AMD Radeon RX 5700 with 8 GB VRAM, Vulkan llama.cpp, Agents-A1-4B Q8_0, a 65,536-token server context and one slot. A small local model has meaningful reasoning and source-verification limitations. A UI cannot remove them.

## Install

1. Clone/download this repository into a permanent folder. The generated launcher points to that folder; rerun the installer after moving it.
2. Run `scripts/Install-Jarvis.ps1 -DryRun`. Resolve runtime errors before proceeding.
3. Run `scripts/Install-Jarvis.ps1`. Record the printed backup directory.
4. Run `scripts/Start-Jarvis.ps1`. The default panel URL is `http://127.0.0.1:9120`.
5. Start a new Hermes conversation to load `/jarvis-workspace`.

The installer preserves unrelated config keys and existing SOUL text. It modifies main/local provider routes, model fallback chains, configured auxiliary text routes, delegation, external-login adoption, shared telemetry and speech provider choices. The changed files are `config.yaml`, `SOUL.md`, `skills/productivity/jarvis-workspace/SKILL.md`, `Jarvis-Local.cmd`, and `jarvis-data/settings.json`. It also initializes a vault map when absent. Existing secrets are not read, copied or removed by the installer.

`Invoke-HermesPython.ps1` discovers the Python runtime via `hermes pm env python` and `pm.environments`, temporarily applies its activation exports and restores the caller's environment afterward. It does not hardcode an install generation or mutate dependencies.

## Daily workflow

- Start Jarvis with `Jarvis-Local.cmd` or the PowerShell launcher. Keep the console open.
- Capture factual/source material in raw; put organized reference material in wiki.
- Select notes explicitly, pick a workflow and enter the audience and desired outcome.
- Wait for the job. First requests may take minutes on the reference machine.
- Review saved drafts. Use the note browser to open an output; select it as context for another format.
- Use Hermes Desktop for tasks requiring filesystem tools, commands or native integrations. Ask it to use the Jarvis vault skill.

The panel's local chat has no cross-message history. Every completed answer is saved as an output note, so you can explicitly select it for a following request. There is no hidden long-term prompt memory.

## Voice

Dictate uses browser microphone capture, encodes mono PCM16 WAV, and posts it to the loopback panel. The server loads cached Whisper `base` with `local_files_only=True`, CPU int8, English and VAD. Audio is held in memory, not saved by this panel. The browser microphone indicator is visible while recording. Click Stop or wait for the 59-second timer. Review the transcript before submitting.

Read aloud uses cached `en_US-lessac-medium` Piper, CPU, and returns an in-memory WAV played by the browser. The audio player has pause controls. At most the first 3,000 characters are spoken. Speech must not be treated as reliable Arabic or Quran recitation: this English voice is not appropriate for that purpose.

If there is no input device, reconnect/enable a microphone in Windows Sound settings and reload. For full native Hermes voice controls, use the foundation guide; the companion does not change the terminal hotkeys.

## Export

Open a saved output, select Print / PDF, and choose the browser's Save as PDF. The print stylesheet hides navigation, controls and the composer. It preserves the selected result as readable text and writing spaces, rather than generating a finished illustrated workbook. Copy exports plain text. No automatic publishing or DM automation is present.

## Stop and restart

Ctrl+C in the launcher console or **Stop panel** in the footer stops the panel. The UI refuses its Stop action while its current job is running. Completed notes persist. An interrupted in-flight model call may continue until its timeout/server completion; there is no cancellation claim. The separate llama.cpp process is not stopped with the panel. Use the existing local model stop script if you want to release VRAM. Closing a browser tab does not stop the server.

## Roll back

Stop Jarvis, then run:

```powershell
.\scripts\Restore-Jarvis.ps1 -Backup '<Hermes home>\backups\jarvis-<timestamp>'
```

Rollback restores the five installation files to their pre-install text, or removes them if absent before installation. It refuses to overwrite later edits; inspect the manifest and restore selectively if that happens. It deliberately keeps source notes, generated outputs and the vault map. Backups contain private original configuration and SOUL text; never publish them.

No service, login startup task, firewall change, shared drive or public listener is installed. To remove the companion entirely after rollback, remove the source checkout yourself; retain the vault wherever you want.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Model unavailable | Verify llama.cpp health, alias and port. The panel never substitutes a cloud provider. |
| Port already occupied | Stop the previous Jarvis console or select another `-Port`. Do not kill unrelated processes. |
| Whisper cache missing | Use the foundation guide to download the model once; restart. Runtime never downloads it silently. |
| Missing Piper voice | Install/download via the foundation guide; check the Hermes home cache directory. |
| PM discovery fails | Set the correct `-HermesHome`/`-HermesSource`; use `hermes pm repair` if the actual installation is broken. |
| API permission error after restart | Refresh the page to load the new per-process token. |
| Slow draft | One local GPU slot is shared. Avoid concurrent Hermes chat and panel jobs. |
| Source note seems ignored | Only selected notes are sent, capped at 6,000 characters each. Split large references and select the relevant sections. |
