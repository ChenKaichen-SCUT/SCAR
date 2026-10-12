import copy
import gzip
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json,digest

ROOT=Path('results/stage14')
OLD=Path('results/stage12/diagnostic')
BASE='80d800968c33c61a492227e72a332999c40bc022'
METHODS={10:['S0','S1','S2','S3'],11:['E0','E1','E2','E3','E4']}

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(p):
    with gzip.open(p,'rt') as f:yield from map(json.loads,f)
def save_records(p,rows):
    # Stable gzip bytes make cross-machine artifact reconciliation possible.
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:
        for row in rows:f.write((json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n').encode())
def episodes():
    for stage,methods in METHODS.items():
        cases={c['id']:c for c in load(f'results/stage{stage}/cases.json')}
        for method in methods:
            path=f'results/stage{stage}/trajectories_{method}.jsonl.gz'
            for ep in records(path):yield stage,method,ep,cases[ep['case_id']],path

def replay_old_controller(stage,row):
    from scar_stage10.controller import restore_controller as r10
    from scar_stage11.controller import restore_controller as r11
    c=(r10 if stage==10 else r11)(copy.deepcopy(row['stage7_state_before']))
    # Restore the actual controller; choose with the already saved proposal.
    action=c.choose(row['observation'],row['proposed_action'])
    assert action==row['executed_action'],(stage,row['index'],action,row['executed_action'])
    c.observe(row['observation'],action,row['next_observation'])
    return c
