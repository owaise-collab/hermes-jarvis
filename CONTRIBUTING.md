# Contributing

Keep the companion small, local and separate from Hermes core. Use native Hermes for full agent tools rather than implementing a second arbitrary-command API. New endpoints need bounded input, the same session/Host/Origin protection, and behavior checks using temporary data.

Run the two test commands in README, parse changed PowerShell scripts and inspect the actual browser UI. Voice changes need a synthetic roundtrip and, when hardware is available, a separately disclosed microphone/playback check. Do not pass historical hardware results off as current tests.

Never stage a Hermes home, backups, private configuration, credentials, vault content, raw logs, model files or audio. Keep examples synthetic. Before publication, review `git diff --cached` and the publication checker. Documentation must distinguish implemented behavior, tested behavior and remaining limitations.
