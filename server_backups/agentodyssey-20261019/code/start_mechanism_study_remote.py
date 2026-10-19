"""Freeze protocol, implementation and reference windows before the first paid call."""
import hashlib,json,socket,subprocess,time,urllib.request,zipfile
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
pre=json.loads((R/'mechanism_study_preflight.json').read_text());assert pre['all_passed'] and pre['api_calls']==0
assert not (R/'mechanism_study_status.json').exists() and not (R/'runner_mechanism_study.pid').exists()
for rel,h in pre['protected_files_unchanged'].items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
for n in ['mechanism_study_core.py','mechanism_study_agent.py','feedback_v4_core.py']:assert (R/n).read_bytes()==(repo/'agents'/n).read_bytes()
commit='248430692a9d4a61d38c6c03ab2126287faaf450'
archive=R/'agentodyssey-source.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e685c65046d3c53bd6954906ab7649e74aba86cb9eb2acb4adb929886192ae96'
with zipfile.ZipFile(archive) as z:
    prefix=z.namelist()[0].split('/')[0]+'/'
    engine_files=['games/base/env.py','challenge_eval.py']+[f'games/generated/{g}/{f}' for g in ['remnant','mark','metropolis'] for f in ['env.py','rules/action_rules.py']]
    for n in engine_files:assert (repo/n).read_bytes()==z.read(prefix+n),n
variants=['no_checks','no_execution','no_repeat','no_hypothesis']
runs=[{'id':g+'__ab_'+v,'game':g,'variant':v,'phase':'ablation','max_steps':300} for v in variants for g in ['remnant','metropolis']]
runs += [{'id':g+'__study_v4','game':g,'variant':'v4_selected','phase':'v4_validation','max_steps':500} for g in ['remnant','mark','metropolis']]
for spec in runs:
    for p in [R/'runs'/spec['id'],R/'telemetry'/spec['id'],R/'control_audit'/(spec['id']+'.jsonl')]:assert not p.exists()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8093))!=0
key=(R/'.deepseek-key').read_text().strip()
with urllib.request.urlopen(urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key}),timeout=30) as response:b=json.load(response)
assert b.get('is_available'),'No available balance; do not start'
(R/'mechanism_study_balance_at_start.json').write_text(json.dumps(b,indent=2))
reference={};historical_hashes={};oldstate=json.loads((R/'feedback_v3_status.json').read_text())
for g in ['remnant','metropolis']:
    rid=g+'__feedback_v3';p=R/'runs'/rid/'agent_adam_davis/agent_log.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()][:300]
    reference[g]={'main':sum(r['reward'].get('quest',0) for r in rows),'steps_observed':len(rows),'budget':300,
        'remaining_steps_after_method_failure':'no further reward credited; early algorithm failure retained' if len(rows)<300 else None,
        'original_completion_reason':oldstate['runs'][rid]['completion_reason']}
    historical_hashes[str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest()
names=['mechanism_study_core.py','mechanism_study_agent.py','feedback_v4_core.py','study_selection.py','eval_mechanism_study.py','api_proxy_mechanism_study.py','run_mechanism_study.py','analyze_mechanism_study.py','study_adapter_smoke.py','test_mechanism_study.py','test_study_selection.py','preflight_mechanism_study_remote.py','start_mechanism_study_remote.py','study_validation_cases.json','feedback_v3_core.py','feedback_v3_agent.py','feedback_v2_core.py','api_proxy.py','deepseek_adapter.py']
proto={'purpose':'Controlled component screening and separate reliability revision validation; no baseline reruns','runs':runs,'runs_per_condition':1,
    'api_model':'deepseek-flash','thinking':'disabled','actor_temperature':0.7,'actor_presence_penalty':1.5,'max_output_tokens':4096,'controller_temperature':0.,'controller_presence_penalty':0.,
    'controller_release':'min(60, 1 + step*60//500), same as frozen v3; at most 37 in 300 steps and 60 in 500 steps','max_repair_calls_per_run':32,
    'max_successful_llm_calls_total':4728,'transport_retries_max':2,'environment_seed':42,'source_commit':commit,'cpu_threads_per_process':2,
    'parallel_trajectories_ablation':4,'parallel_trajectories_v4':3,'api_concurrency_ceiling':128,'dependent_actions':'sequential within each game; no speculative paid branches',
    'reference_at_300':reference,'historical_reference_sha256':historical_hashes,
    'ablations':{'no_checks':'v3 joint quantity, task parameter, station, capacity and surplus vetoes become advisory; factual ledger retained',
        'no_execution':'v3 automatic dependency preparation and committed short-plan execution disabled; fresh actor proposals still checked',
        'no_repeat':'v3 repeated-context action and unchanged-inspection hard vetoes become advisory',
        'no_hypothesis':'v3 separate typed hypothesis proposal, trial marking and prompt feedback removed; review and actor budgets unchanged'},
    'v4_frozen_reliability_changes':['unreported inventory remains uncertain; capacity failure only constrains same observed load, attempted action, location, epoch and life',
        'death invalidates operational constraints; law rewrite also invalidates object-capability and inspection caches',
        'explicit not-equippable feedback persists as object capability until rule rewrite',
        'unsupported or contradicted objectives cannot remain locked; old objective may be revalidated after death',
        'successful navigation recurrence becomes advisory; unchanged failed actions and repeated inspections remain checked unless their group is removed',
        'fresh actor proposal precedes old plan/preparation after hazard, task, visibility or reset changes'],
    'selection':'At most one component group removed. Both 300-step screening runs must finish with valid scores, Remnant must strictly beat its frozen v3 reference and Metropolis must not regress. Rank qualifying groups by normalized total main gain (24/31 denominators), ties: no_hypothesis, no_execution, no_repeat, no_checks. If none qualify, retain all groups and apply only reliability revisions. No post-hoc threshold tuning.',
    'phase_transition':'after all 8 ablations stop, save selection, check provider balance once, then run selected v4 on all 3 games; no top-up, no automatic reruns',
    'measurements':['main/supplementary score, main score at step 300, early method versus API failures','zero-capacity vetoes, deaths, unchanged inspections, rejection types, main gain steps','observable objective effects, net dependency changes, typed tests','API call counts and prompt/completion tokens; no aggregate wall-time metric'],
    'data_access':['current public observations','own full history','declared action schema'],
    'prohibited_actor_inputs':['reward or hidden state','game-specific hardcoded objects, recipes, maps or answers','frozen historical traces, baseline scores or offline validation fixtures'],
    'limitations':['one stochastic trajectory per condition: screen, not significance or universal utility proof','same games used for development: no held-out generalization claim','v4 has several frozen reliability changes; its outcome cannot identify an individual repair effect','no factorial interaction estimates; at most one group removed to avoid combining untested deletions','method early exits remain failures with achieved score; infrastructure failures disqualify selection'],
    'implementation_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}}
(R/'protocol_mechanism_study.json').write_text(json.dumps(proto,indent=2))
for script,stem in [('api_proxy_mechanism_study.py','proxy_mechanism_study'),('run_mechanism_study.py','runner_mechanism_study')]:
    with (R/(stem+'.log')).open('w') as out:p=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(R/script)],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (R/(stem+'.pid')).write_text(str(p.pid));print(json.dumps({'script':script,'pid':p.pid}),flush=True)
    if stem=='proxy_mechanism_study':
        for _ in range(50):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',8093))==0:break
            if p.poll() is not None:raise RuntimeError('Proxy failed before games started')
            time.sleep(.1)
        else:raise RuntimeError('Proxy did not become ready')
print(json.dumps({'reference_at_300':reference,'planned_runs':len(runs),'balance':b}))
