import gzip
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json
from scar_stage22.config import ENGINE,ENGINE_COMMIT,MODEL,GAMES,SEED,MAX_STEPS,AGENT_ID

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/stage24'
REPORTS=ROOT/'reports/stage24'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage24_runtime')
def read(p):return json.loads(Path(p).read_text())
def write(p,d):atomic_json(Path(p),d)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(x) for x in f]
def gzwrite(p,data):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt') as f:
        for d in data:f.write(json.dumps(d,ensure_ascii=False)+'\n')
def source(game):return ROOT/'results/stage22/runs'/f'{game}__Stage18-Fixed'
def check_freeze():
    d=read(RESULTS/'freeze.json')
    for n,h in d['files'].items():assert sha(ROOT/n)==h,n
    for n,h in d['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(d['files']),engine_files=len(d['engine_files']))
def offline():
    import socket
    def deny(*a,**k):raise RuntimeError('Offline verification: network prohibited')
    socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
