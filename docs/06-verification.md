# Verification and limitations

Foundation verification date: November 1, 2026. HUD redesign date: November 2, 2026. This is a Windows reference installation, not certification of every machine, voice, GPU or model.

## Automated behavior suite

The November 1 reference run passed 16 temporary-home/loopback tests on Windows. They cover:

- note capture, Unicode text, all-word search and selected-note context;
- path traversal rejection and local model endpoint validation;
- deterministic brief without inference and escaped print text;
- one active model job, saved draft provenance and explicit model failure;
- preservation of unrelated configuration, route/fallback changes;
- installer dry run, repeated installation, rollback and retained user notes;
- refusal to overwrite later user edits during rollback;
- API token requirement, Host validation, cross-origin write rejection;
- real HTTP note roundtrip and invalid job input rejection.
- fixed native Desktop launcher selection, ignoring arbitrary command text supplied to that endpoint.

The first test pass found a Windows launcher line-ending rollback mismatch. The implementation was corrected and the full suite rerun successfully. Tests use no cloud model, real microphone or user notes.

## Foundation live checks — November 1

The installed panel opened at `127.0.0.1:9120` and reported the actual local model ready. The UI was visually inspected in the browser. Full synthetic model and speech test results are recorded separately after execution in `runtime/jarvis-verification.json` under the Hermes home; that file is deliberately excluded from the repository.

| Actual local check | Result |
| --- | --- |
| Model health and expected alias | Passed |
| No-model vault brief | Passed |
| Panel job through the actual local model | Passed; exact `JARVIS_LOCAL_OK` response saved |
| Piper synthetic WAV generation | Passed |
| Cached Whisper transcription of that WAV | Passed; sentence preserved |
| Browser note capture, selection and carousel creation | Passed; eight-slide draft saved with input-note provenance |

The carousel sample still needed editorial review: its final suggested practice sentence did not align perfectly with inviting another child. This is why outputs remain drafts; successful generation does not certify teaching quality.

Run the repeatable live check explicitly:

```powershell
.\scripts\Invoke-HermesPython.ps1 -Script .\tests\live_check.py -ScriptArgs @('--hermes-home', '<your Hermes home>')
```

This sends a synthetic marker request to the panel, checks the saved output, synthesizes a short English sentence with local Piper and transcribes synthetic audio using cached Whisper. It does not record the microphone or play speakers. It adds a clearly synthetic marker output to the real vault.

## HUD redesign checks — November 2

The redesigned desktop HUD was visually inspected in the running browser. An actual local request returned `JARVIS_HUD_OK`, saved its output, and moved the core from processing to standby. Workflow buttons selected the matching route, a saved source note attached correctly, and the system view displayed the real endpoint and installed speech dependencies. The desktop page had no horizontal overflow. Motion controls were checked through computed styles: enabled rings use `hud-spin`; reduced motion uses no animation.

JavaScript syntax and the repository publication checks passed. Mobile breakpoints and the white result-only print stylesheet remain implemented, but this pass does not certify a phone screenshot or a newly exported PDF: the requested mobile viewport override did not take effect in the browser. Microphone capture and speech playback were not repeated for a visual redesign; the original hardware limitation below still applies.

The cyan rings and schematic lines are interface artwork. Model status comes from the local endpoint, note counts from the vault, and listening/speaking states from actual app events. Speech dependency availability must not be presented as a successful microphone test. The existing local-processing and native-tool network boundaries still apply.

## Hardware limitations observed

Windows audio device enumeration currently reports no input device. Browser live microphone dictation is therefore not certified in this installation. Connect a microphone and perform an explicit Dictate test; review the transcript before submitting. Existing foundation-guide microphone results are historical and are not substituted for a current hardware check.

English Piper output and Whisper base do not establish Arabic pronunciation quality, tajwid, quotation authenticity or educational suitability. Those need suitable models and qualified review.

## Product limits

- The panel does not execute arbitrary tools; full agent work stays in Hermes Desktop/CLI.
- Chat requests are independent, with explicit selected-note context.
- Completed drafts persist; job status and in-flight work are not durable across server restarts.
- No scheduler, wake word, background listener, cancellation, automatic publishing, image generator or video renderer is included.
- Print / PDF uses the browser dialog; verify pagination and the actual saved PDF.
- Native Hermes may use network-enabled tools; local model routing is not OS egress isolation.
- A small local model can hallucinate and can be slow. Sources and important conclusions require review.
