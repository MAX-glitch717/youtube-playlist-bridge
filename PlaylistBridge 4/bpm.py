"""Estimate tempo from a bounded audio excerpt; write ID3 TBPM before publishing."""
import json
import math
import subprocess
import sys
import numpy as np
import librosa
from mutagen.id3 import ID3, TBPM


def estimate(path):
    # Decode at most 180 seconds to mono PCM; avoids loading long mixes in memory.
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-t', '180',
                          '-f', 'f32le', '-ac', '1', '-ar', '22050', 'pipe:1'],
                         capture_output=True, check=True, timeout=90).stdout
    samples = np.frombuffer(pcm, dtype='<f4')
    if len(samples) < 22050 * 5 or np.max(np.abs(samples)) < 1e-5:
        return None
    tempo, beats = librosa.beat.beat_track(y=samples, sr=22050, hop_length=256)
    value = float(np.asarray(tempo).reshape(-1)[0])
    if not math.isfinite(value) or value <= 0 or len(beats) < 4:
        return None
    return round(value, 1)


if __name__ == '__main__':
    value = estimate(sys.argv[1])
    if value is not None:
        tags = ID3(sys.argv[1])
        tags.add(TBPM(encoding=3, text=str(round(value))))
        tags.save(sys.argv[1], v2_version=3)
    print(json.dumps({'bpm': value}))
