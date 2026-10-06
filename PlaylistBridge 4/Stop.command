#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
pb_init "$0" "$@"
[[ -x "$PB_RUNTIME/bin/python" ]] || { pb_fail 'Run Repair.command to restore the runtime first.'; exit 1; }
"$PB_RUNTIME/bin/python" "$PB_SOURCE/scripts/maintenance.py" stop "$PB_APP_DIR" "$PB_STATE_DIR"
