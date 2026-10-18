"""One full development evaluation after the declared branch gate passed."""
import json,os,subprocess,sys
from pathlib import Path
root=Path('/root/scar_effect_v4_20261018');code=root/'frozen';base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017')
read=lambda p:json.loads(p.read_text())
probes={name:read(root/'probes'/name/'result.json')['results'] for name in ('mark_r0','mark_r1','route_value','failed_source','positive_source')}
assert probes['positive_source']['effect']['fulfilled'] and probes['positive_source']['effect']['steps']==probes['positive_source']['plan']['steps']
assert any(v['effect']['fulfilled'] and not v['plan']['fulfilled'] or v['effect']['score_delta']>v['plan']['score_delta'] for v in probes.values())
assert all(v['effect']['score_delta']>=v['plan']['score_delta'] for v in probes.values())
(root/'full_game_gate.json').write_text(json.dumps(dict(status='passed',basis='Two actual craft-and-hold improvements; positive control preserved; no branch score loss. Mark-r0 incurred one informative missing-station craft failure; no implementation error.',qualification='Selected development branches, not independent validation'),indent=2))
jobs=read(root/'jobs.json') if (root/'jobs.json').exists() else []
for name in sys.argv[1:]:
    assert name in ('mark_r0','mark_r1','metropolis_r1','metropolis_7537')
    assert name not in [j['name'] for j in jobs]
    assert (Path('/root/scar_effect_v3_20261018/evaluation')/name/'result.json').exists()
    block=old/'evaluation'/name if name!='metropolis_7537' else Path('/root/scar_compact_independent_20261017/evaluation/metropolis/main')
    seed=read(block/'manifest.json')['hash_seed']
    env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),PYTHONHASHSEED=seed,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    historical=[Path('/root')/v/'evaluation'/name/'api' for v in ('scar_effect_v3_20261018','scar_effect_v2_20261018','scar_plan_v2_20261018','scar_plan_20261018','scar_objective_v3_20261018','scar_objective_v2_20261018','scar_objective_20261018','scar_hypothesis_v2_20261018','scar_hypothesis_20261018')]
    for v in ('scar_effect_v4_20261018','scar_effect_v3_20261018','scar_effect_v2_20261018','scar_effect_20261018'):
        for probe in ('mark_r0','mark_r1','route_value','failed_source','positive_source'):
            historical.append(Path('/root')/v/'probes'/probe/'effect/api')
    cmd=[str(base/'venv/bin/python'),'-m','scar_public.experiments.obstacle_trial','--agent','effect','--block',str(block),'--root',str(root/'evaluation'/name),'--key',str(base/'private/deepseek.key')]
    for path in historical:cmd.extend(['--reuse-api',str(path)])
    with (root/(name+'_game.log')).open('w') as log:
        proc=subprocess.Popen(cmd,cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    jobs.append(dict(name=name,block=str(block),pid=proc.pid))
(root/'jobs.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))
