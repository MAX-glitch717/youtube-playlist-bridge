# Third-party components

This archive contains PlaylistBridge source and dependency lists. Its installer downloads third-party tools separately. Those components retain their upstream licenses; this document does not relicense them or define the seller's customer license for PlaylistBridge.

Primary projects:

- Python: https://www.python.org/psf/license/
- uv: https://github.com/astral-sh/uv
- yt-dlp and its JavaScript support: https://github.com/yt-dlp/yt-dlp
- FFmpeg: https://ffmpeg.org/legal.html (licensing depends on the installed build)
- Deno: https://github.com/denoland/deno
- Mutagen: https://github.com/quodlibet/mutagen
- librosa: https://github.com/librosa/librosa
- NumPy: https://github.com/numpy/numpy
- SciPy: https://github.com/scipy/scipy
- Numba: https://github.com/numba/numba

The complete resolved Python package list is in `locks/macos-arm64.txt` and `locks/macos-x86_64.txt`. Installed package metadata includes upstream license information. Homebrew installs its own tools and their dependencies separately.

YouTube Music and djay are product names of their respective owners. PlaylistBridge is an independent helper; this package does not establish endorsement or affiliation.
