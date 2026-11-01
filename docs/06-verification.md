# Verification and limitations

Reference date: November 1, 2026. This is a Windows reference installation, not certification of every machine, voice, GPU or model.

## Automated behavior suite

The 16 temporary-home/loopback tests pass on the Windows reference machine. They cover:

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

## Live checks

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
