import sys, tempfile, subprocess, threading, os
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bridge
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
import numpy as np
import soundfile as sf
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder); sr=22050; y=np.zeros(sr*30)
 for beat in np.arange(.5,29.8,.5):
  i=int(beat*sr); n=1100
  y[i:i+n] += .8*np.sin(2*np.pi*1000*np.arange(n)/sr)*np.exp(-np.arange(n)/180)
 sf.write(p/'click.wav',y,sr)
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw): super().__init__(*a,directory=folder,**kw)
  def log_message(self,*a): pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 real=bridge.external
 def reroute(cmd,timeout=1200):
  cmd=[f'http://127.0.0.1:{server.server_port}/click.wav' if x=='https://www.youtube.com/watch?v=abcdefghijk' else x for x in cmd]
  return real(cmd,timeout)
 work=p/'stage';work.mkdir()
 with patch.object(bridge,'external',reroute):
  audio=bridge.download_track('abcdefghijk',work,{'browser':''})
 assert 29<MP3(audio).info.length<31
 bpm=bridge.detect_bpm(audio)
 assert bpm is not None and abs(bpm-120)<4,bpm
 assert ID3(audio).get('TBPM') is not None
 again=bridge.detect_bpm(audio)
 assert again == bpm, (bpm, again)
 print('PASS: actual yt-dlp extraction from local synthetic WAV, FFmpeg MP3 conversion, MP3 validation, BPM estimate:',bpm,'and TBPM metadata')
 server.shutdown()
