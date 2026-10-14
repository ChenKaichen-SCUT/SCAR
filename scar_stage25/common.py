from scar_stage24.common import read,write,sha,rows,gzwrite,offline,ROOT,ENGINE,ENGINE_COMMIT,MODEL,GAMES,AGENT_ID,MAX_STEPS
from pathlib import Path
import gzip
import json
RESULTS=ROOT/'results/stage25'
REPORTS=ROOT/'reports/stage25'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage25_runtime')
SEEDS=(42,43,44)
CASES=[(game,seed) for game in GAMES for seed in SEEDS]
def case_id(game,seed):return f'{game}__s{seed}__AGC-v2'
def check_freeze():
    d=read(RESULTS/'freeze.json')
    for n,h in d['files'].items():assert sha(ROOT/n)==h,n
    for n,h in d['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(d['files']),engine_files=len(d['engine_files']))
