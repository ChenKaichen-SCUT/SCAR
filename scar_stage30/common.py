import json
import gzip
from pathlib import Path
from scar_stage24.common import ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID,MAX_STEPS,read,write,sha,rows,gzwrite,offline
from scar_stage28.common import CASES,selected,suffix

BASE='bca5bcef42ab71f8d6b743b62fa1a3c3fae88bfd'
RESULTS=ROOT/'results/stage30'
REPORTS=ROOT/'reports/stage30'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage30_runtime')
CHECKPOINTS=ROOT/'results/stage28/checkpoints'

def check_freeze(light=False):
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():
        if not light or n.startswith('scar_stage30/') or n.startswith('results/stage30/checkpoints/'):
            assert sha(ROOT/n)==h,n
    if not light:
        for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))
