# Development

Use Python 3.12 and FFmpeg on PATH. Create a separate development environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest test_bridge test_maintenance -v
python test_http.py
python test_audio_pipeline.py
```

On Macs affected by Homebrew Python issues, use uv to create the development environment with managed Python instead: `uv venv --managed-python --python 3.12 .venv`, then activate it and use `uv pip install -r requirements.txt`.

Keep Mac command files compatible with Bash 3.2. Do not change the installer to depend on Homebrew Python. Installer dependency locks are architecture-specific; changes to requirements must also be reflected in those locks. Check the supported macOS range before changing binary dependencies.

Include the issue being fixed and the relevant check results in pull requests. Never attach cookies, access-token URLs, personal settings or downloaded songs. GitHub workflow checks do not replace native Mac installation, login and djay import testing.

Build the customer ZIP with `python scripts/package_release.py`.
