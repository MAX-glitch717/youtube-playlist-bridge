"""Build a customer ZIP from an explicit file list; exclude all runtime/user data."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'bridge.py', 'bpm.py', 'index.html', 'requirements.txt', 'README.md',
    'VERSION', 'CHANGELOG.md', 'THIRD-PARTY.md', 'TEST-RESULTS.md',
    'GITHUB-SETUP.md', 'CONTRIBUTING.md', 'scripts/package_release.py',
    'Install.command', 'Repair.command', 'Update.command',
    'Open PlaylistBridge.command', 'Stop.command', 'Diagnostics.command',
    'Uninstall.command', 'scripts/common.sh', 'scripts/maintenance.py',
    'locks/macos-arm64.txt', 'locks/macos-x86_64.txt',
    'test_bridge.py', 'test_maintenance.py', 'test_http.py', 'test_audio_pipeline.py',
]

def main():
    output = ROOT / 'dist' / 'PlaylistBridge-Mac.zip'
    output.parent.mkdir(exist_ok=True)
    for name in FILES:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name in FILES:
            info = ZipInfo('PlaylistBridge/' + name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            mode = 0o100755 if name.endswith('.command') else 0o100644
            info.external_attr = mode << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, (ROOT / name).read_bytes())
    with ZipFile(output) as archive:
        assert archive.testzip() is None
    print(output)

if __name__ == '__main__':
    main()
