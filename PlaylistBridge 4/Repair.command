#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
pb_init "$0" "$@"
[[ -f "$PB_APP_DIR/bridge.py" ]] || { pb_fail 'Run Install.command first.'; exit 1; }
pb_stopped
pb_tools
pb_copy
pb_runtime
echo 'Repair complete. Settings and downloaded music were preserved.'
bash "$PB_APP_DIR/Open PlaylistBridge.command"
