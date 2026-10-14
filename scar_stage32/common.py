from scar_stage24.common import ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID,MAX_STEPS,read,write,sha,rows,gzwrite,offline
from pathlib import Path
import json,gzip
BASE='60311467be7245637abb7392e8c7b82686c9530a'
RESULTS=ROOT/'results/stage32';REPORTS=ROOT/'reports/stage32';RUNTIME=Path('/mnt/Space0/scar_dependencies/stage32_runtime')
SEEDS=[42,43,44]
def ident(seed):return f'remnant__s{seed}__SAER'
def parent(seed):return ROOT/f'results/stage31/runs/remnant__s{seed}__REC'
def initial(seed):return ROOT/f'results/stage25/initial/remnant__s{seed}__AGC-v2'
def baseline(seed):return ROOT/f'results/stage{25 if seed==42 else 31}/runs/remnant__s{seed}__AGC-v2'
def check_freeze(light=False):
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():
        if not light or n.startswith(('agents/saer/','scar_stage32/','results/stage32/checkpoints/')):assert sha(ROOT/n)==h,n
    if not light:
        for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))
