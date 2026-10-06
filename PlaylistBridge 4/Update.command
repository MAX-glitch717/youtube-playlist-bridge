#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
pb_init "$0" "$@"
[[ -x "$PB_RUNTIME/bin/python" ]] || { pb_fail 'Run Install.command first.'; exit 1; }
pb_stopped
pb_check_binary uv
uv pip install --python "$PB_RUNTIME/bin/python" --only-binary=:all: --upgrade 'yt-dlp[default]'
"$PB_RUNTIME/bin/python" -m yt_dlp --version
echo 'Downloader updated. Reopen Open PlaylistBridge.command. Core audio packages are unchanged.'
