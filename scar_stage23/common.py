import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/stage23'
REPORTS=ROOT/'reports/stage23'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage23_runtime')
ENGINE=Path('/mnt/Space0/scar_dependencies/agentodyssey_stage22')
AGENT='agent_adam_davis'
SOURCE=ROOT/'results/stage22/runs/mark__Stage18-Fixed'
CASES=(33,35,52,64,70,100,179,193,244,271)
VARIANTS=('Stage18-Origin','Stage18-Reset','Oracle-Reset')
MAX_STEPS=300

def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(line) for line in f]
def gzwrite(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8') as f:
        for r in data:f.write(json.dumps(r,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):
    from scar.io import atomic_json
    atomic_json(Path(p),data)
def case_id(step):return f'mark-a{step:03d}'
def check_freeze():
    p=read(RESULTS/'freeze.json')
    for n,h in p['files'].items():assert sha(ROOT/n)==h,'Frozen source changed: '+n
    for n,h in p['engine_files'].items():assert sha(ENGINE/n)==h,'Engine changed: '+n
    return dict(project_files=len(p['files']),engine_files=len(p['engine_files']))
