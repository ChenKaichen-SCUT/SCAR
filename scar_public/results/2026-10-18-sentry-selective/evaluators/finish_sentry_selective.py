import json,os,subprocess
from pathlib import Path
root=Path('/root/scar_sentry_selective_20261018');base=Path('/root/scar_research_20261015');deps=Path('/root/scar_core_valid_20261017')
env=dict(os.environ,PYTHONPATH=f'{deps}/deps:{root}/frozen:{deps}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
    AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
jobs=[]
for game in ('remnant','mark','metropolis'):
    assert (root/'evaluation'/game/'selective/result.json').exists(),game
    receipt=json.loads((root/'evaluation'/game/'selective/manifest.json').read_text())['initial_receipt']
    with (root/f'{game}_audit.log').open('w') as log:
        p=subprocess.Popen([str(base/'venv/bin/python'),'/root/audit_sentry_selective.py','--game',game],env=dict(env,PYTHONHASHSEED=receipt['hash_seed']),
            cwd=root/'frozen',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    jobs.append(dict(game=game,pid=p.pid))
print(json.dumps(jobs))
