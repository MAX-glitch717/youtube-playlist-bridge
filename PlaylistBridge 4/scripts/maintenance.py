"""Local maintenance commands. No network calls except the local helper's stop API."""
import fcntl
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

LABEL = 'local.playlistbridge.sync'


def running(state):
    lock = state / 'instance.lock'
    if not lock.exists():
        return False
    with lock.open('r') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def runtime(app, expected_arch):
    import pyexpat
    import ssl
    from xmlrpc import client
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Python 3.12 is required.')
    if not Path(sys.base_prefix).resolve().is_relative_to((app / 'python-runtime').resolve()):
        raise RuntimeError('This environment uses a system Python. Repair will create an independent runtime.')
    if platform.machine() != expected_arch:
        raise RuntimeError('Runtime architecture does not match this Mac.')
    if not platform.mac_ver()[0]:
        raise RuntimeError('macOS version detection failed.')
    print(f'Runtime OK: Python {platform.python_version()}, {platform.machine()}, {pyexpat.EXPAT_VERSION}')


def stop(state):
    if not running(state):
        print('PlaylistBridge is already stopped.')
        return
    from urllib.parse import urlparse, parse_qs
    from urllib.request import Request, build_opener, ProxyHandler
    address = json.loads((state / 'address.json').read_text())['url']
    parsed = urlparse(address)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port:
        raise RuntimeError('Invalid local helper address; quit from the control window.')
    token = parse_qs(parsed.query)['token'][0]
    request = Request(f'http://127.0.0.1:{parsed.port}/api/quit', data=b'{}',
                      headers={'X-App-Token': token, 'Content-Type': 'application/json'})
    with build_opener(ProxyHandler({})).open(request, timeout=10) as response:
        response.read()
    for _ in range(50):
        if not running(state):
            print('PlaylistBridge stopped.')
            return
        time.sleep(0.1)
    raise RuntimeError('The helper is still stopping. Try again shortly.')


def refresh_login(app):
    import plistlib
    path = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    if not path.exists():
        return
    body = plistlib.loads(path.read_bytes())
    body['ProgramArguments'] = [str(app / '.runtime-v2/bin/python'), str(app / 'bridge.py')]
    body['EnvironmentVariables'] = {'PATH': os.environ['PATH']}
    temporary = path.with_suffix('.plist.tmp')
    temporary.write_bytes(plistlib.dumps(body))
    temporary.replace(path)
    print('Existing start-at-login setting updated for the next login.')


def diagnostics(app, state):
    lines = ['PlaylistBridge diagnostic report',
             'Version: ' + (app / 'VERSION').read_text().strip(),
             f'macOS: {platform.mac_ver()[0]}', f'Architecture: {platform.machine()}',
             f'Python: {platform.python_version()}', f'Helper running: {running(state)}']
    try:
        import pyexpat, ssl
        lines += [f'Expat: {pyexpat.EXPAT_VERSION}', f'TLS: {ssl.OPENSSL_VERSION}']
    except Exception as error:
        lines.append('Runtime check: ' + type(error).__name__)
    for tool in ['uv', 'ffmpeg', 'ffprobe', 'deno']:
        try:
            result = subprocess.run([tool, '-version' if tool.startswith('ff') else '--version'],
                                    capture_output=True, text=True, timeout=10)
            first = result.stdout.splitlines()
            lines.append(f'{tool}: ' + (first[0] if first else f'exit {result.returncode}'))
        except Exception as error:
            lines.append(f'{tool}: {type(error).__name__}')
    try:
        config = json.loads((state / 'config.json').read_text())
        lines += [f'Playlist count: {len(config.get("playlists", []))}',
                  f'Automatic checks: {bool(config.get("enabled"))}',
                  f'BPM enabled: {bool(config.get("bpm"))}']
    except (OSError, ValueError):
        lines.append('Configuration unavailable.')
    state.mkdir(parents=True, exist_ok=True)
    report = state / 'diagnostics.txt'
    report.write_text('\n'.join(lines) + '\n')
    report.chmod(0o600)
    print('\n'.join(lines))
    print(f'Report saved to {report}')


def uninstall(app, state):
    import shutil
    expected = Path.home() / 'Applications/PlaylistBridge'
    if app != expected or app.resolve() != expected.absolute():
        raise RuntimeError('Unexpected installation path; automatic uninstall cancelled.')
    config_path = state / 'config.json'
    if config_path.exists():
        config = json.loads(config_path.read_text())
        folder = Path(config.get('folder', '~/Music/djay Imports')).expanduser().resolve()
        if folder.is_relative_to(app.resolve()):
            raise RuntimeError('Your music folder is inside the program folder. Move the music and change the destination before uninstalling.')
    print('This removes PlaylistBridge and its private runtime. Settings, download history and music are retained.')
    if input('Type UNINSTALL to continue: ').strip() != 'UNINSTALL':
        print('Cancelled.')
        return
    stop(state)
    path = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    subprocess.run(['launchctl', 'bootout', f'gui/{os.getuid()}/{LABEL}'], capture_output=True)
    path.unlink(missing_ok=True)
    shutil.rmtree(app)
    print('Uninstalled. Your music and settings remain in place. Homebrew and shared tools were retained.')


def main():
    command, app, state = sys.argv[1:4]
    app, state = Path(app), Path(state)
    if command == 'runtime':
        runtime(app, sys.argv[4])
    elif command == 'check-stopped':
        if running(state):
            raise RuntimeError('Quit the helper or run Stop.command before installing, repairing or updating.')
    elif command == 'stop':
        stop(state)
    elif command == 'refresh-login':
        refresh_login(app)
    elif command == 'diagnostics':
        diagnostics(app, state)
    elif command == 'uninstall':
        uninstall(app, state)
    else:
        raise RuntimeError('Unknown maintenance command.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'PlaylistBridge: {error}', file=sys.stderr)
        if sys.argv[1:2] == ['stop']:
            print('If a sync is active, wait for it to finish and try again.', file=sys.stderr)
        sys.exit(1)

