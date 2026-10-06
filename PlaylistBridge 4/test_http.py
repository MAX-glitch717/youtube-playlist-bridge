"""Local HTTP integration test. Starts and stops an isolated helper process."""
import json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse, parse_qs
root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as state:
 env=dict(os.environ,PLAYLIST_BRIDGE_STATE=state)
 process=subprocess.Popen([sys.executable,str(root/'bridge.py')],env=env)
 try:
  address_file=Path(state)/'address.json'
  for _ in range(100):
   if address_file.exists():break
   time.sleep(.05)
  address=json.loads(address_file.read_text())['url']
  u=urlparse(address);base=f'http://{u.netloc}';token=parse_qs(u.query)['token'][0]
  def call(path,data=None,headers=None):
   req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
   try:
    with urllib.request.urlopen(req,timeout=10) as r:return r.status,r.read().decode()
   except urllib.error.HTTPError as e:return e.code,e.read().decode()
  assert call('/api/status')[0]==403
  assert call('/api/status',headers={'X-App-Token':token,'Host':'evil.example'})[0]==403
  assert call('/api/config',{}, {'X-App-Token':token,'Origin':'https://evil.example'})[0]==403
  assert call('/api/config',{'playlists':['file:///tmp/audio']},{'X-App-Token':token})[0]==400
  cfg={'playlists':['https://music.youtube.com/playlist?list=PL123456'],'folder':str(Path(state)/'MP3s'),'minutes':5,'browser':'','enabled':False,'bpm':True}
  assert call('/api/config',cfg,{'X-App-Token':token})[0]==200
  status,raw=call('/api/status',headers={'X-App-Token':token});assert status==200 and json.loads(raw)['config']==cfg
  assert call('/?token='+token)[0]==200
  assert call('/api/quit',{}, {'X-App-Token':token})[0]==200
  process.wait(timeout=5)
  print('PASS: authenticated page, config roundtrip, invalid config rejection, missing-token rejection, hostile Host and Origin rejection, graceful shutdown')
 finally:
  if process.poll() is None:process.terminate();process.wait(timeout=5)
