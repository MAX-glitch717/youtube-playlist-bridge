# Verification — version 1.1.0

Checked September 15, 2026 in a Linux x86_64 development environment using uv-managed Python 3.12.14. These checks do not substitute for Mac hardware tests.

## Passed

- 10 sync tests: duplicate handling and restart persistence, additions/removals, missing-file recovery, destination changes, concurrency, download retry, invalid audio rejection, independent playlist failures, validation, and successful publication despite BPM failure.
- Local HTTP integration: control page, settings roundtrip, invalid settings, missing-token rejection, hostile Host/Origin rejection and graceful shutdown.
- Actual audio pipeline: yt-dlp downloads a synthetic WAV from a local test server using the production download options, FFmpeg converts to valid MP3, BPM analysis reports 120.2 for a 120 BPM reference, and ID3 TBPM metadata is present. Analysis also succeeds with a warm cache.
- Maintenance integration: running helper blocks installation/updates; Stop reaches the authenticated local API, stops the process, releases the instance lock, and succeeds when already stopped.
- Platform classification cases: native ARM64, native Intel, Rosetta ARM selection, and rejection of old macOS/unknown processors/missing version.
- Architecture-specific wheel-only dependency resolution for macOS ARM64 and x86_64 using uv, Python 3.12. No source compilation required by either resolved Python dependency set.
- Python compilation, shell syntax and embedded JavaScript syntax checks.
- Archive integrity and inclusion of nested scripts and dependency locks.

## Not verified here

- Installing or running version 1.1.0 on physical Intel or Apple Silicon Macs.
- Actual Rosetta re-execution, native Homebrew installations, macOS folder picker, Keychain/browser cookie access, launchd login behavior, or uninstall on macOS.
- Live YouTube Music downloading or djay automatic folder import in this development environment.
- Interactive browser visual rendering; only JavaScript syntax and HTTP behavior were checked.
- Every macOS version, external disk format or browser profile combination.

The user reported the earlier private-Python repair working on an Apple Silicon Mac running macOS 26.2. That report is not a hardware test of the new installer and maintenance commands.

Before claiming broad compatibility in a commercial listing, run a clean installation, small playlist sync, djay import, login restart, update, repair and uninstall on a native Intel Mac and an Apple Silicon Mac, including the oldest macOS version you advertise.

## Reproduce core checks

From the extracted source folder, with its dependencies installed in your test Python:

```bash
python -m unittest test_bridge test_maintenance -v
python test_http.py
python test_audio_pipeline.py
```

Audio tests use generated test audio; they do not need a YouTube account. Tests isolate their state in temporary folders. FFmpeg must be on PATH.

## GitHub packaging check — October 6, 2026

The repository edition adds git ignore/line-ending rules, development and publishing instructions, a Linux GitHub Actions workflow, and an allowlist-based customer ZIP builder. Application behavior was not changed.

Rechecked: all 12 sync/maintenance unit tests, local HTTP integration, Python and shell syntax, and archive integrity. The first local unit run lacked Mutagen; after installing it in an isolated test environment, all tests passed. Full BPM audio analysis was not repeated for this packaging-only change; its earlier result is recorded above. The GitHub Actions workflow is provided but has not yet run on GitHub.
