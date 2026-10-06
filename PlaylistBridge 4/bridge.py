#!/usr/bin/env python3
"""Local playlist-to-MP3 bridge. No cloud server or credentials storage."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import signal
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import webbrowser

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get('PLAYLIST_BRIDGE_STATE', str(Path.home() / 'Library/Application Support/PlaylistBridge')))
LABEL = 'local.playlistbridge.sync'


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def read_json(path, default):
    if not path.exists():
        return default
    # Fail visibly on damaged state, rather than silently losing the archive.
    return json.loads(path.read_text(encoding='utf-8'))


def playlist_url(value):
    parsed = urlparse(value.strip())
    if parsed.scheme != 'https' or parsed.hostname not in {'music.youtube.com', 'www.youtube.com', 'youtube.com'}:
        raise ValueError('Use an https://music.youtube.com/playlist?list=… link.')
    ident = parse_qs(parsed.query).get('list', [''])[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,150}', ident):
        raise ValueError('The link needs a valid playlist list= ID. Use a saved playlist, not a radio mix.')
    if ident.startswith('RD'):
        raise ValueError('Radio mixes are changing queues. Create a normal saved playlist instead.')
    return 'https://music.youtube.com/playlist?list=' + ident


def validate_config(data):
    urls = data.get('playlists', [])
    if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
        raise ValueError('Enter between 1 and 20 playlist links, one per line.')
    urls = list(dict.fromkeys(playlist_url(x) for x in urls))
    folder = Path(str(data.get('folder', '')).strip()).expanduser()
    if not folder.is_absolute() or folder == Path('/'):
        raise ValueError('Choose an absolute destination folder, such as ~/Music/djay Imports.')
    # Never create a missing external volume mount point on the internal drive.
    if str(folder).startswith('/Volumes/') and not Path(*folder.parts[:3]).is_mount():
        raise ValueError('Mount the external drive before choosing this folder.')
    minutes = int(data.get('minutes', 5))
    if not 2 <= minutes <= 1440:
        raise ValueError('Check interval must be between 2 and 1440 minutes.')
    browser = data.get('browser', '')
    if browser not in {'', 'chrome', 'firefox', 'safari', 'edge', 'brave'}:
        raise ValueError('Unsupported browser.')
    return dict(playlists=urls, folder=str(folder), minutes=minutes,
                browser=browser, bpm=bool(data.get('bpm', True)), enabled=bool(data.get('enabled', True)))


def safe_name(title, video_id):
    name = re.sub(r'[\x00-\x1f/\\:]', '_', title).strip(' .') or 'Track'
    name = name.encode('utf-8')[:160].decode('utf-8', errors='ignore')
    return f'{name} [{video_id}].mp3'


def external(cmd, timeout=1200):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Kill the process group, including FFmpeg children, before retrying a file.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise RuntimeError(f'Operation timed out after {timeout} seconds; retry on the next check.')
    if process.returncode:
        error = stderr.strip() or stdout.strip() or f'Command exited with code {process.returncode}'
        raise RuntimeError(error[-1800:])
    return stdout


def ytdlp_args(config):
    args = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-colors',
            '--socket-timeout', '30', '--retries', '3', '--extractor-retries', '2']
    if config['browser']:
        args += ['--cookies-from-browser', config['browser']]
    return args


def fetch_playlist(url, config):
    raw = external(ytdlp_args(config) + ['--flat-playlist', '--dump-single-json', '--skip-download', '--', url], 300)
    result = json.loads(raw)
    if not isinstance(result.get('entries'), list):
        raise RuntimeError('The source did not return a playlist. Check its visibility and link.')
    return result['entries']


def download_track(video_id, work, config):
    # An interrupted FFmpeg run may leave a playable but incomplete MP3. Never
    # reuse that output. yt-dlp can still resume its original .part download.
    (work / 'audio.mp3').unlink(missing_ok=True)
    external(ytdlp_args(config) + [
        '--no-playlist', '--no-progress', '--no-overwrites', '-f', 'bestaudio/best',
        '-x', '--audio-format', 'mp3', '--audio-quality', '0', '--embed-metadata',
        '--write-info-json', '--match-filters', '!is_live & !is_upcoming',
        '-o', str(work / 'audio.%(ext)s'), '--', 'https://www.youtube.com/watch?v=' + video_id])
    path = work / 'audio.mp3'
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('No complete MP3 produced (track may be live, private, removed, or unavailable).')
    return path


def detect_bpm(path):
    # Separate process bounds analysis time and releases numerical-library memory.
    result = external([sys.executable, str(ROOT / 'bpm.py'), str(path)], 300)
    value = json.loads(result)['bpm']
    return value


class Bridge:
    def __init__(self, state=STATE, fetch=fetch_playlist, download=download_track, analyzer=detect_bpm):
        self.state = state
        state.mkdir(parents=True, exist_ok=True)
        self.config = read_json(state / 'config.json', dict(playlists=[], folder=str(Path.home() / 'Music/djay Imports'), minutes=5, browser='', bpm=True, enabled=False))
        self.tracks = read_json(state / 'tracks.json', {})
        self.fetch, self.download, self.analyzer = fetch, download, analyzer
        self.lock = threading.RLock()
        self.busy = False
        self.message = 'Add your playlist and destination folder to begin.'
        self.errors = []
        self.last_sync = None
        self.next_sync = time.time() if self.config['enabled'] else None
        self.wake = threading.Event()

    def snapshot(self):
        with self.lock:
            return dict(config=dict(self.config), busy=self.busy, message=self.message,
                        errors=list(self.errors), last_sync=self.last_sync, next_sync=self.next_sync,
                        tracks=list(self.tracks.values()), login=(Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')).exists())

    def save(self, data):
        config = validate_config(data)
        with self.lock:
            if self.busy:
                raise ValueError('Wait for this sync to finish before changing settings.')
            atomic_json(self.state / 'config.json', config)
            self.config = config
            self.next_sync = time.time() if config['enabled'] else None
        self.wake.set()

    def set_message(self, message):
        with self.lock:
            self.message = message

    def sync(self):
        with self.lock:
            if self.busy:
                return
            self.busy = True
            config = dict(self.config)
            self.errors = []
        added = 0
        try:
            config = validate_config(config)
            folder = Path(config['folder'])
            folder.mkdir(parents=True, exist_ok=True)
            # Same volume, outside watched folder: finished file is published atomically.
            stage = folder.parent / ('.' + folder.name + '-playlistbridge-work')
            stage.mkdir(mode=0o700, exist_ok=True)
            seen = set()
            for url in config['playlists']:
                self.set_message('Checking playlist…')
                try:
                    entries = self.fetch(url, config)
                except Exception as exc:
                    with self.lock:
                        self.errors.append(str(exc))
                    continue
                for entry in entries:
                    if not entry:
                        continue
                    ident = str(entry.get('id', ''))
                    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', ident):
                        with self.lock:
                            self.errors.append('Skipped an entry without a usable YouTube video ID.')
                        continue
                    if ident in seen:
                        continue
                    seen.add(ident)
                    key = hashlib.sha256((str(folder) + '\0' + ident).encode()).hexdigest()
                    previous = self.tracks.get(key)
                    if previous and Path(previous['path']).is_file():
                        continue
                    title = str(entry.get('title') or ident)
                    work = stage / ident
                    work.mkdir(exist_ok=True)
                    try:
                        self.set_message('Downloading: ' + title)
                        audio = self.download(ident, work, config)
                        from mutagen.mp3 import MP3
                        duration = MP3(audio).info.length  # Reject damaged/partial MP3s.
                        if duration <= 0:
                            raise RuntimeError('MP3 has no audio duration.')
                        bpm = None
                        warning = ''
                        if config['bpm']:
                            self.set_message('Analysing BPM: ' + title)
                            try:
                                bpm = self.analyzer(audio)
                            except Exception as exc:
                                warning = 'BPM unavailable: ' + str(exc)[-300:]
                        target = folder / safe_name(title, ident)
                        # Crash recovery: never overwrite a published file with a changed name.
                        if target.exists():
                            existing = MP3(target)
                            if existing.info.length <= 0:
                                raise RuntimeError('An invalid file already exists at the destination; move it aside and retry.')
                            audio.unlink()
                        else:
                            os.replace(audio, target)
                        record = dict(id=ident, title=title, path=str(target), bpm=bpm,
                                      duration=round(duration), added=time.time(), warning=warning)
                        with self.lock:
                            self.tracks[key] = record
                            atomic_json(self.state / 'tracks.json', self.tracks)
                        shutil.rmtree(work)
                        added += 1
                    except Exception as exc:
                        with self.lock:
                            self.errors.append(title + ': ' + str(exc))
                        # Failed files remain outside djay. Retry on next check.
            self.set_message(f'Finished: {added} new MP3(s). ' + (f'{len(self.errors)} issue(s); see below.' if self.errors else 'Ready for djay.'))
        except Exception as exc:
            with self.lock:
                self.errors.append(str(exc))
            self.set_message('Sync could not finish. See the issue below.')
        finally:
            with self.lock:
                self.last_sync = time.time()
                self.busy = False
                self.next_sync = time.time() + self.config['minutes'] * 60 if self.config['enabled'] else None

    def scheduler(self):
        while True:
            with self.lock:
                due = self.config['enabled'] and self.next_sync is not None and time.time() >= self.next_sync
            if due:
                self.sync()
            self.wake.wait(1)
            self.wake.clear()


def login_item(enable):
    if sys.platform != 'darwin':
        raise ValueError('Start at login is available on macOS only.')
    path = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    if enable:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = dict(Label=LABEL, ProgramArguments=[sys.executable, str(ROOT / 'bridge.py')],
                    RunAtLoad=True, ProcessType='Background',
                    EnvironmentVariables={'PATH': os.environ['PATH']},
                    StandardOutPath=str(STATE / 'service.log'), StandardErrorPath=str(STATE / 'service-error.log'))
        path.write_bytes(plistlib.dumps(body))
        # RunAtLoad activates at the next login; current running helper keeps working.
        return 'Enabled for your next login. This session is already running.'
    if path.exists():
        path.unlink()
    return 'Disabled for future logins. Quit the helper to stop this session.'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', action='store_true', help='Open the control window')
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_file = (STATE / 'instance.lock').open('w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        if args.open:
            address = read_json(STATE / 'address.json', {})
            if address.get('url'):
                webbrowser.open(address['url'])
        return
    bridge = Bridge()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not log the capability token or playlist data.

        def reply(self, status, data, kind='application/json'):
            body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            host = self.headers.get('Host', '')
            return host == f'127.0.0.1:{self.server.server_port}' and secrets.compare_digest(self.headers.get('X-App-Token', ''), token)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/' and self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}' and secrets.compare_digest(parse_qs(url.query).get('token', [''])[0], token):
                self.reply(200, (ROOT / 'index.html').read_text().replace('__TOKEN__', token), 'text/html')
            elif url.path == '/api/status' and self.authorized():
                self.reply(200, bridge.snapshot())
            else:
                self.reply(403, {'error': 'Open the helper using Open PlaylistBridge.command.'})

        def do_POST(self):
            if not self.authorized() or self.headers.get('Origin', '') not in {'', f'http://127.0.0.1:{self.server.server_port}'}:
                self.reply(403, {'error': 'Unauthorized'})
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 <= length <= 65536:
                    raise ValueError('Request too large')
                data = json.loads(self.rfile.read(length) or b'{}')
                route = urlparse(self.path).path
                message = 'Done'
                if route == '/api/config':
                    bridge.save(data)
                    message = 'Settings saved.'
                elif route == '/api/sync':
                    threading.Thread(target=bridge.sync, daemon=True).start()
                    message = 'Sync requested.'
                elif route == '/api/folder':
                    if sys.platform != 'darwin':
                        raise ValueError('Type the folder path on this platform.')
                    folder = external(['osascript', '-e', 'POSIX path of (choose folder with prompt "Choose your djay MP3 folder")'], 180).strip()
                    self.reply(200, {'folder': folder})
                    return
                elif route == '/api/reveal':
                    folder = Path(bridge.config['folder'])
                    if not folder.is_dir():
                        raise ValueError('The destination folder does not exist yet. Run a sync first.')
                    if sys.platform == 'darwin':
                        subprocess.Popen(['open', str(folder)])
                elif route == '/api/login':
                    message = login_item(bool(data.get('enabled')))
                elif route == '/api/quit':
                    if bridge.busy:
                        raise ValueError('Wait for the current sync to finish before quitting.')
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    message = 'Helper stopped. Reopen it with Open PlaylistBridge.command.'
                else:
                    self.reply(404, {'error': 'Not found'})
                    return
                self.reply(200, {'message': message})
            except Exception as exc:
                self.reply(400, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    address = f'http://127.0.0.1:{server.server_port}/?token={token}'
    atomic_json(STATE / 'address.json', {'url': address})
    threading.Thread(target=bridge.scheduler, daemon=True).start()
    if args.open:
        webbrowser.open(address)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
