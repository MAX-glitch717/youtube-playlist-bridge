#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
pb_init "$0" "$@"
pb_stopped
pb_tools
pb_copy
pb_runtime
echo 'Installation complete. Opening PlaylistBridge…'
bash "$PB_APP_DIR/Open PlaylistBridge.command"
