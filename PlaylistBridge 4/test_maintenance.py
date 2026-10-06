"""Maintenance integration and platform classification checks; no Mac emulation."""
import os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent

class MaintenanceTests(unittest.TestCase):
    def test_platform_targets(self):
        for version, arch, rosetta, expected in [
            ('14.0','arm64','0','arm64'), ('26.2','x86_64','0','x86_64'),
            ('15.1','x86_64','1','arm64'), ('13.6','arm64','0',None),
            ('26.2','ppc','0',None), ('','arm64','0',None)]:
            result = subprocess.run(['bash','-c','source "$1"; pb_platform "$2" "$3" "$4"',
                                     'test',str(ROOT/'scripts/common.sh'),version,arch,rosetta],
                                    capture_output=True,text=True)
            if expected:
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout.strip(),expected)
            else:
                self.assertNotEqual(result.returncode,0)

    def test_stop_and_install_guard(self):
        with tempfile.TemporaryDirectory(prefix='playlist bridge ') as directory:
            state=Path(directory)
            process=subprocess.Popen([sys.executable,str(ROOT/'bridge.py')],
                                     env=dict(os.environ,PLAYLIST_BRIDGE_STATE=directory))
            def maintenance(command):
                return subprocess.run([sys.executable,str(ROOT/'scripts/maintenance.py'),command,str(ROOT),directory],
                                      capture_output=True,text=True,timeout=15)
            try:
                for _ in range(100):
                    if (state/'address.json').exists(): break
                    time.sleep(.05)
                self.assertTrue((state/'address.json').exists())
                self.assertNotEqual(maintenance('check-stopped').returncode,0)
                result=maintenance('stop')
                self.assertEqual(result.returncode,0,result.stderr)
                process.wait(timeout=5)
                self.assertEqual(maintenance('check-stopped').returncode,0)
                self.assertEqual(maintenance('stop').returncode,0)
            finally:
                if process.poll() is None:
                    process.terminate();process.wait(timeout=5)

if __name__=='__main__': unittest.main()
