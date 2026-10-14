import json
import gzip
from pathlib import Path
from scar_stage24.common import ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID,MAX_STEPS,read,write,sha,rows,gzwrite,offline

BASE='08fd73bc4c728c8e02943c8e421cf47a464a8714'
RESULTS=ROOT/'results/stage31';REPORTS=ROOT/'reports/stage31'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage31_runtime')
SEEDS=[42,43,44]
CASES=[(seed,method) for seed in SEEDS for method in ['AGC-v2','REC']]
def case_id(seed,method):return f'remnant__s{seed}__{method}'
def initial(seed):return ROOT/f'results/stage25/initial/remnant__s{seed}__AGC-v2'
def baseline(seed):return ROOT/f'results/stage25/runs/remnant__s{seed}__AGC-v2'
def check_freeze(light=False):
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():
        if not light or n.startswith(('agents/rec_v1/','scar_stage31/','results/stage31/checkpoints/')):assert sha(ROOT/n)==h,n
    if not light:
        for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))
