"""Offline regression tests using generated audio, never copyrighted downloads."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from bridge import Bridge, playlist_url, safe_name, validate_config


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio_tmp = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.audio_tmp.name) / 'tone.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=1', '-y', str(cls.fixture)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.audio_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.entries = [{'id': 'abcdefghijk', 'title': 'Remix / first'}]
        self.downloads = []
        def download(ident, work, config):
            self.downloads.append(ident)
            self.assertFalse(any(Path(config['folder']).glob('*.mp3')) if len(self.downloads) == 1 else False)
            target = work / 'audio.mp3'
            shutil.copyfile(self.fixture, target)
            return target
        self.bridge = Bridge(self.root / 'state', fetch=lambda *_: self.entries,
                             download=download, analyzer=lambda _: 128.0)
        self.config = dict(playlists=['https://music.youtube.com/playlist?list=PL123456'],
                           folder=str(self.root / 'imports'), minutes=5, bpm=True, browser='', enabled=False)
        self.bridge.save(self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def test_duplicate_and_restart(self):
        self.entries *= 2
        self.bridge.sync()
        self.bridge.sync()
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(len(list((self.root / 'imports').glob('*.mp3'))), 1)
        other = Bridge(self.root / 'state', fetch=lambda *_: self.entries,
                       download=lambda *_: self.fail('Restart redownloaded a completed track'))
        other.sync()
        self.assertEqual(len(other.tracks), 1)
        self.assertEqual(other.errors, [])

    def test_failed_download_is_not_published_then_retried(self):
        good = self.bridge.download
        def broken(_, work, config):
            (work / 'audio.part').write_text('incomplete')
            raise RuntimeError('Network disconnected')
        self.bridge.download = broken
        self.bridge.sync()
        self.assertEqual(len(self.bridge.tracks), 0)
        self.assertEqual(list((self.root / 'imports').iterdir()), [])
        self.assertTrue(self.bridge.errors)
        self.bridge.download = good
        self.bridge.sync()
        self.assertEqual(len(self.bridge.tracks), 1)

    def test_new_addition_and_removal_never_deletes(self):
        self.bridge.sync()
        self.entries.append({'id': 'lmnopqrstuv', 'title': 'Second'})
        self.bridge.sync()
        self.entries.clear()
        self.bridge.sync()
        self.assertEqual(len(list((self.root / 'imports').glob('*.mp3'))), 2)

    def test_missing_file_is_repaired(self):
        self.bridge.sync()
        Path(next(iter(self.bridge.tracks.values()))['path']).unlink()
        self.bridge.sync()
        self.assertEqual(len(self.downloads), 2)
        self.assertTrue(Path(next(iter(self.bridge.tracks.values()))['path']).exists())

    def test_analysis_failure_still_publishes(self):
        def fail(_):
            raise RuntimeError('BPM timed out')
        self.bridge.analyzer = fail
        self.bridge.sync()
        track = next(iter(self.bridge.tracks.values()))
        self.assertIsNone(track['bpm'])
        self.assertIn('timed out', track['warning'])
        self.assertTrue(Path(track['path']).exists())

    def test_bad_audio_never_published(self):
        def bad(_, work, config):
            path = work / 'audio.mp3'
            path.write_text('not audio')
            return path
        self.bridge.download = bad
        self.bridge.sync()
        self.assertEqual(self.bridge.tracks, {})
        self.assertTrue(self.bridge.errors)

    def test_concurrent_sync_does_not_download_twice(self):
        entered, release = threading.Event(), threading.Event()
        original = self.bridge.fetch
        def slow(*args):
            entered.set()
            release.wait(3)
            return original(*args)
        self.bridge.fetch = slow
        thread = threading.Thread(target=self.bridge.sync)
        thread.start()
        self.assertTrue(entered.wait(2))
        self.bridge.sync()
        with self.assertRaises(ValueError):
            self.bridge.save(self.config)
        release.set()
        thread.join(5)
        self.assertEqual(len(self.downloads), 1)

    def test_one_failed_playlist_does_not_block_other(self):
        self.config['playlists'].append('https://music.youtube.com/playlist?list=PL654321')
        self.bridge.save(self.config)
        def fetch(url, config):
            if 'PL123456' in url:
                raise RuntimeError('Playlist unavailable')
            return self.entries
        self.bridge.fetch = fetch
        self.bridge.sync()
        self.assertEqual(len(self.bridge.tracks), 1)
        self.assertEqual(len(self.bridge.errors), 1)

    def test_destination_change_downloads_to_new_folder(self):
        self.bridge.sync()
        self.config['folder'] = str(self.root / 'another drive')
        self.bridge.save(self.config)
        self.bridge.sync()
        self.assertEqual(len(list((self.root / 'another drive').glob('*.mp3'))), 1)
        self.assertEqual(len(self.downloads), 2)

    def test_validation(self):
        for bad in ['file:///etc/passwd', 'https://youtube.com.evil.test/playlist?list=PL123456',
                    'https://music.youtube.com/watch?v=abcdefghijk', 'https://music.youtube.com/playlist?list=RD123456']:
            with self.assertRaises(ValueError):
                playlist_url(bad)
        self.assertEqual(playlist_url('https://www.youtube.com/watch?v=abcdefghijk&list=PL123456'), self.config['playlists'][0])
        for minutes in [0, -1, 1441]:
            with self.assertRaises(ValueError):
                validate_config(dict(self.config, minutes=minutes))
        filename = safe_name('../bad/name:曲' * 80, 'abcdefghijk')
        self.assertNotIn('/', filename)
        self.assertLess(len(filename.encode()), 255)


if __name__ == '__main__':
    unittest.main(verbosity=2)
