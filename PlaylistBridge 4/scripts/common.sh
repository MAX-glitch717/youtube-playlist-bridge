#!/bin/bash
# Compatible with macOS's bundled Bash 3.2. Sourced by command entrypoints.
pb_fail() { echo "PlaylistBridge: $*" >&2; return 1; }

pb_platform() {
  local version="$1" machine="$2" translated="$3" major
  major="${version%%.*}"
  case "$major" in ''|*[!0-9]*) pb_fail 'Cannot determine macOS version.'; return 1;; esac
  if (( major < 14 )); then
    pb_fail "macOS $version is outside this package's target range. macOS 14 or newer is required."
    return 1
  fi
  if [[ "$translated" == 1 ]]; then echo arm64; return; fi
  case "$machine" in arm64|x86_64) echo "$machine";; *) pb_fail "Unsupported processor: $machine"; return 1;; esac
}

pb_init() {
  local entry="$1" translated version
  shift
  if [[ "$(uname -s)" != Darwin ]]; then pb_fail 'This package runs on macOS only.'; return 1; fi
  translated="$(/usr/sbin/sysctl -in sysctl.proc_translated 2>/dev/null || true)"
  if [[ "$translated" == 1 ]]; then
    echo 'Reopening in native Apple Silicon mode…'
    exec /usr/bin/arch -arm64 /bin/bash "$entry" "$@"
  fi
  version="$(/usr/bin/sw_vers -productVersion)"
  PB_ARCH="$(pb_platform "$version" "$(uname -m)" "$translated")"
  PB_SOURCE="$(cd "$(dirname "$entry")" && pwd)"
  PB_APP_DIR="$HOME/Applications/PlaylistBridge"
  PB_STATE_DIR="$HOME/Library/Application Support/PlaylistBridge"
  PB_RUNTIME="$PB_APP_DIR/.runtime-v2"
  if [[ "$PB_ARCH" == arm64 ]]; then PB_PREFIX=/opt/homebrew; PB_UV_ARCH=aarch64;
  else PB_PREFIX=/usr/local; PB_UV_ARCH=x86_64; fi
  export PATH="$PB_APP_DIR/tools:$PB_PREFIX/bin:$PB_PREFIX/sbin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
  export UV_PYTHON_INSTALL_DIR="$PB_APP_DIR/python-runtime"
  echo "PlaylistBridge 1.1.0 · macOS $version · $PB_ARCH"
}

pb_check_binary() {
  local tool="$1" location description
  location="$(command -v "$tool")" || { pb_fail "Missing dependency: $tool"; return 1; }
  description="$(/usr/bin/file -Lb "$location" 2>/dev/null || true)"
  if [[ "$description" == *Mach-O* && "$description" != *"$PB_ARCH"* ]]; then
    pb_fail "$tool is not native $PB_ARCH. Install a matching copy in $PB_PREFIX/bin or $PB_APP_DIR/tools."
    return 1
  fi
  case "$tool" in ffmpeg|ffprobe) "$tool" -version >/dev/null;; *) "$tool" --version >/dev/null;; esac
}

pb_tools() {
  local tool formula formulas=''
  for tool in uv ffmpeg ffprobe deno; do
    if ! command -v "$tool" >/dev/null; then
      formula="$tool"; [[ "$tool" == ffprobe ]] && formula=ffmpeg
      case " $formulas " in *" $formula "*) ;; *) formulas="$formulas $formula";; esac
    fi
  done
  if [[ -n "$formulas" ]]; then
    if [[ ! -x "$PB_PREFIX/bin/brew" ]]; then
      pb_fail "Install native Homebrew from https://brew.sh, then rerun this command. Expected: $PB_PREFIX/bin/brew. Alternatively supply native uv, ffmpeg, ffprobe and deno in the tools folder."
      return 1
    fi
    echo "Installing missing dependencies:$formulas"
    # Formula names are selected solely from the fixed list above.
    HOMEBREW_NO_INSTALL_CLEANUP=1 "$PB_PREFIX/bin/brew" install $formulas
    hash -r
  fi
  for tool in uv ffmpeg ffprobe deno; do pb_check_binary "$tool"; done
}

pb_stopped() {
  if [[ -x "$PB_RUNTIME/bin/python" ]]; then
    "$PB_RUNTIME/bin/python" "$PB_SOURCE/scripts/maintenance.py" check-stopped "$PB_APP_DIR" "$PB_STATE_DIR"
  fi
}

pb_copy() {
  local item
  mkdir -p "$PB_APP_DIR/scripts" "$PB_APP_DIR/locks"
  if [[ "$PB_SOURCE" != "$PB_APP_DIR" ]]; then
    for item in bridge.py bpm.py index.html requirements.txt README.md VERSION CHANGELOG.md THIRD-PARTY.md \
      Install.command Repair.command Update.command 'Open PlaylistBridge.command' Stop.command Diagnostics.command Uninstall.command; do
      cp "$PB_SOURCE/$item" "$PB_APP_DIR/$item"
    done
    cp "$PB_SOURCE/scripts/common.sh" "$PB_APP_DIR/scripts/common.sh"
    cp "$PB_SOURCE/scripts/maintenance.py" "$PB_APP_DIR/scripts/maintenance.py"
    cp "$PB_SOURCE/locks/macos-arm64.txt" "$PB_APP_DIR/locks/macos-arm64.txt"
    cp "$PB_SOURCE/locks/macos-x86_64.txt" "$PB_APP_DIR/locks/macos-x86_64.txt"
  fi
  chmod +x "$PB_APP_DIR/"*.command
}

pb_runtime() {
  if [[ -e "$PB_RUNTIME" ]]; then
    if [[ ! -x "$PB_RUNTIME/bin/python" ]] || ! "$PB_RUNTIME/bin/python" "$PB_APP_DIR/scripts/maintenance.py" runtime "$PB_APP_DIR" "$PB_STATE_DIR" "$PB_ARCH"; then
      local backup="$PB_RUNTIME.backup-$(date +%Y%m%d-%H%M%S)-$$"
      mv "$PB_RUNTIME" "$backup"
      echo "Preserved the old runtime at: $backup"
    fi
  fi
  if [[ ! -x "$PB_RUNTIME/bin/python" ]]; then
    uv venv --no-project --managed-python --python "cpython-3.12-macos-$PB_UV_ARCH-none" "$PB_RUNTIME"
  fi
  "$PB_RUNTIME/bin/python" "$PB_APP_DIR/scripts/maintenance.py" runtime "$PB_APP_DIR" "$PB_STATE_DIR" "$PB_ARCH"
  uv pip install --python "$PB_RUNTIME/bin/python" --only-binary=:all: -r "$PB_APP_DIR/locks/macos-$PB_ARCH.txt"
  echo 'Checking audio dependencies; first load may take a minute…'
  "$PB_RUNTIME/bin/python" -c 'import yt_dlp, mutagen, numpy, scipy; from librosa.beat import beat_track; print("All audio dependencies loaded.")'
  "$PB_RUNTIME/bin/python" "$PB_APP_DIR/scripts/maintenance.py" refresh-login "$PB_APP_DIR" "$PB_STATE_DIR"
}
