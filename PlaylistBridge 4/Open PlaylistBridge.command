#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
pb_init "$0" "$@"
[[ -x "$PB_RUNTIME/bin/python" ]] || { pb_fail 'Run Install.command first.'; exit 1; }
mkdir -p "$PB_STATE_DIR"
nohup "$PB_RUNTIME/bin/python" "$PB_APP_DIR/bridge.py" --open >> "$PB_STATE_DIR/service.log" 2>&1 < /dev/null &
echo 'Opening the control window. You may close Terminal; the helper keeps running.'
