from pathlib import Path
from functools import lru_cache
from scar_stage24.common import ROOT,ENGINE,read,write,sha,rows,gzwrite,offline,AGENT_ID
from scar_stage28.common import CASES,selected,suffix
RESULTS=ROOT/'results/stage29'
REPORTS=ROOT/'reports/stage29'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage29_runtime')
BASE='14b16e0876bcf488cb33a037476ceeeee2d5b051'

@lru_cache(None)
def data(ident,variant):
    s=selected()[ident]
    source=ROOT/s['source_trajectory'] if variant=='Original' else ROOT/f'results/stage28/runs/{ident}/OracleRecovery/trajectory.jsonl.gz'
    allrows=rows(source);rr=[r for r in allrows if r['step']>s['step']]
    qq=[q for q in rows(source.parent/'requests.jsonl.gz') if q['step']>s['step']]
    return s,rr,qq,str(source.relative_to(ROOT)),{r['step']:i for i,r in enumerate(allrows,1)}

def check_freeze():
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():assert sha(ROOT/n)==h,n
    for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))
