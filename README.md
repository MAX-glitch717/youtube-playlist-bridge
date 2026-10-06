# PlaylistBridge for Mac

Version 1.1.0 • A downloadable script package with a local browser control window.

**Repository setup:** [GITHUB-SETUP.md](GITHUB-SETUP.md) · **Development:** [CONTRIBUTING.md](CONTRIBUTING.md)

If you received a customer download without these repository documents, continue with Install below.

Add tracks to a YouTube Music playlist. PlaylistBridge checks for additions, converts available audio to MP3, optionally estimates BPM, and saves finished files in your chosen folder. Configure that folder in djay to bring tracks into your collection.

## Compatibility

| Mac | Package target | Notes |
| --- | --- | --- |
| Apple Silicon (M-series) | macOS 14 or newer | Uses native ARM64 tools and Python. A Terminal running under Rosetta is restarted in native mode. |
| Intel, 64-bit | macOS 14 or newer | Uses x86_64 tools and Python. Current dependency availability can limit installation on older Intel systems. |
| macOS 13 or earlier; PowerPC; 32-bit Intel | Unsupported | Installer stops with an explanation. |

This range is a compatibility target, not a guarantee for every Mac or future macOS release. Architecture-specific Python dependencies resolve for both architectures. This release has automated tests on Linux but has not been tested on physical Macs across this matrix. See **TEST-RESULTS.md** before distributing it to customers. The earlier runtime repair was reported working on an Apple Silicon Mac running macOS 26.2.

You need an internet connection, permission to write your destination folder, and room for the runtime plus your music. Allow a few GB for tools and dependencies in addition to MP3 storage. Your Mac must be awake for scheduled checks.

## Install

1. Unzip the package. Keep its files together.
2. Install native [Homebrew](https://brew.sh) if needed. The installer expects `/opt/homebrew/bin/brew` on Apple Silicon or `/usr/local/bin/brew` on Intel.
3. Open Terminal. Type `bash ` with a trailing space, drag **Install.command** into Terminal, and press Return. This also works when the extracted folder has spaces in its name.
4. Wait while dependencies install. The installer copies the program to `~/Applications/PlaylistBridge`, creates an independent Python 3.12 runtime, checks audio imports, and opens the control window. First installation can take several minutes.
5. Paste a normal playlist link. Start with a small dedicated playlist: the first sync processes **all available entries**, not just future additions.
6. Choose a destination, for example `~/Music/djay Imports`. Use a dedicated music folder outside the program folder. External drives must be mounted.
7. Choose the checking interval and BPM option, enable automatic checks, then save. Use **Sync now** for an immediate check.
8. In djay, add the destination under **Settings → Library → Import → +** (Dynamic Watch Folders). Check **My Collection** for imported tracks; interface wording can vary by djay version. If your djay version has no watch folders, add the folder manually in its library browser.
9. Optionally enable **start at login** in the control window. It takes effect on the next login.

After setup, add tracks to your configured YouTube Music playlist as usual. They become available after the next successful check, download, and djay import.

### Dependencies and manual installation

The installer installs missing `uv`, `ffmpeg` (including `ffprobe`) and `deno` through Homebrew. Homebrew's supported systems and binary availability can change independently of this package; consult its [support tiers](https://docs.brew.sh/Support-Tiers).

If those tools are already available, Homebrew is not needed. Advanced users can put native executable copies, with their required libraries, in `~/Applications/PlaylistBridge/tools`. The installer checks that tools run and rejects the wrong Mach-O architecture. Python is downloaded separately using [uv managed Python](https://docs.astral.sh/uv/concepts/python-versions/); Homebrew Python and `ensurepip` are not used.

## Control window

- Configure 1–20 playlists and a checking interval of 2–1440 minutes. The default is five minutes after the previous check finishes.
- Search downloaded tracks by text and filter or sort by estimated BPM. This window searches your prepared local collection, not the entire YouTube catalog. Search and add songs in YouTube Music itself.
- Choose a browser for sign-in only if required. The default profile of a locally signed-in browser is used. PlaylistBridge does not ask for your password or export a cookie file. Browser access or Keychain prompts may appear.
- Closing the browser window leaves the helper running. Use **Quit helper** or **Stop.command** to stop it.
- Wait for active syncing to finish before changing settings, quitting, repairing or updating. This prevents interrupting conversion and file publication.

The interface runs on `127.0.0.1` with a local access token. No hosted account or cloud server is required. Do not share the control-window URL: it contains your local token.

## Download and BPM behavior

Downloads use the available source audio and produce variable-bitrate MP3. Conversion cannot improve the source recording's quality. Distinct uploads retain their video IDs in filenames.

Completed tracks are remembered across restarts and deduplicated across configured playlists. Failed tracks are retried on later checks. A failed playlist does not block the other playlists. Temporary files are kept in a hidden sibling staging folder; only validated, finished MP3s appear in your destination.

This is an additive collection. Removing a song from YouTube Music does not delete its MP3. Playlist order and separate playlist folders are not mirrored. Moving, renaming or deleting an MP3 can cause it to download again. Choosing another destination builds a collection there without moving the previous files.

BPM is estimated from up to the first 180 seconds and written to the MP3's ID3 TBPM tag. Half/double-tempo errors and variable tempos are possible. djay may calculate its own tempo; adjust beatgrids there when needed. If BPM analysis fails, the MP3 is still saved with a warning. Enabling BPM later does not reanalyse existing downloads. This release does not separate stems or create BPM subfolders.

Unavailable entries and personal files uploaded to YouTube Music may not be downloadable through this workflow. Sleep, offline operation, or an unmounted destination postpones useful syncing until the required resources are available again.

## Included commands

Run commands from `~/Applications/PlaylistBridge`. You can use the same Terminal drag-and-drop method as installation.

| Command | Purpose |
| --- | --- |
| `Install.command` | Install this release or copy a newer release over an existing installation. Quit the helper first. |
| `Open PlaylistBridge.command` | Start the helper and open its control window, or reopen the existing helper's window. |
| `Stop.command` | Stop the helper when idle. Does not disable start at login. |
| `Update.command` | Update the downloader and its dependencies. Does not update the program source or pinned BPM stack. Reopen afterward. |
| `Repair.command` | Check tools, replace an invalid Python environment, and reinstall the release's pinned dependencies. Preserves settings and download history. Reopens afterward. |
| `Diagnostics.command` | Save a basic version and dependency report, without playlist URLs, track names, cookies or access tokens. |
| `Uninstall.command` | Ask for the word `UNINSTALL`, stop the idle helper, remove its login item and program folder. Keep music, settings and download history. |

To upgrade the program itself, download the newer package, stop the current helper, and run **Install.command from the new package**. Keep the old download until the upgrade succeeds. Repair restores the bundled dependency versions, so run Update afterward if you need a newer downloader.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| macOS will not open a command by double-clicking | Run the trusted package through Terminal using `bash ` and drag the command into the window. |
| Missing Homebrew or incorrect architecture | Install the native Homebrew for your Mac, or supply native tools as described above. Rerun Install. |
| Old `ensurepip`, `pyexpat`, or macOS version detection error | Run this release's Repair command. It uses a private managed Python instead of Homebrew Python. No `sudo` or global Python edits are needed. |
| Repair cannot start Python at all | Quit the helper. In Finder press Command-Shift-G, enter `~/Applications/PlaylistBridge`, show hidden files with Command-Shift-period, and rename `.runtime-v2` to `.runtime-v2.old`. Run Repair to create a fresh runtime. Keep the old folder until repaired. |
| Downloads recently stopped working | Stop the helper, run Update, reopen, and retry. Check the displayed track error and your connection/sign-in. |
| No MP3 appears in djay | Check the chosen folder in Finder and the helper's status. Verify djay watches that exact folder and view My Collection. |
| External disk or folder permission error | Mount the disk and confirm you can create files in the destination and its parent, which holds staging files. |
| Stop or Update says a sync is busy | Wait for the current sync to finish, then retry. |
| Start at login does not run | Reopen the helper, disable and re-enable its login option, and check macOS Login Items / background permissions. |
| BPM looks wrong | Adjust the beatgrid in djay; estimated BPM is not authoritative. |

Run Diagnostics before asking for help. Review any report before sharing. Detailed logs may contain personal paths, track titles and source information, so do not publish them unreviewed.

## Files and uninstall

- Program and private Python: `~/Applications/PlaylistBridge`
- Settings, history, local address and logs: `~/Library/Application Support/PlaylistBridge`
- Optional login item: `~/Library/LaunchAgents/local.playlistbridge.sync.plist`
- Music: the destination you selected; default `~/Music/djay Imports`
- Diagnostics report: `~/Library/Application Support/PlaylistBridge/diagnostics.txt`

Uninstall leaves music and state intact so reinstalling can reuse download history. It retains Homebrew and shared dependencies. If you intentionally want a complete settings reset after uninstalling, separately remove the Application Support folder. Do not remove your MP3 folder unless you intend to erase your music.

Uninstall refuses to remove a program folder containing your configured music destination. Move that music elsewhere and update the destination first.

## Release contents

The package includes readable Python, HTML and shell source, architecture-specific dependency locks, automated checks, a changelog and third-party acknowledgments. It does not include downloaded music, browser credentials, Python runtimes or third-party binaries. See **THIRD-PARTY.md** and **TEST-RESULTS.md**.
