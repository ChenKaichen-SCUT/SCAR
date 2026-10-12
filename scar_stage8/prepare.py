"""Two freezes: policy before new task generation, then data before any API call."""
import argparse,contextlib,gzip,hashlib,json,subprocess,tempfile,datetime
from pathlib import Path
from scar.io import atomic_json,digest
from scar_unknown17.audit import initial
from scar_stage8.controller import METHODS,HISTORICAL
from scar_unknown17_stage7.controller import CONFIGS
OUT=Path('results/stage8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def configure():
    if (OUT/'policy_freeze.json').exists():raise ValueError('Policy already frozen')
    OUT.mkdir(exist_ok=True)
    prior={p:sha(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p}
    atomic_json(OUT/'prior_manifest.json',prior)
    c=json.loads(Path('configs/protocol_stage7.json').read_text())
    c.update(protocol_cohort='stage8_v1',algorithms=METHODS,games=['robot_kingdom','remnant','metropolis'],
        max_steps=40,total_budget_usd=5,episode_budget_usd=.25,
        switches={m:CONFIGS[HISTORICAL[m]] for m in METHODS},
        budget_authorization='User waives historical20USD cap; finite batch, incremental5USD hard guard; latest steering expands ONLY new families to2-3games')
    c.pop('dataset_sha256',None)
    c['predeclared_outcomes']={'primary':'historical Robot10 and novel cohorts separately; new per-game strata; paired family R10/20/40',
        'seed':'one frozen physical seed per family; APItemperature0.7 not paired model randomness',
        'abort':'policy exceptions failure, no paid rerun; infra/budget incomplete',
        'formal_internal_methods':METHODS,'maximum_new_families':18,'target_new_families_per_game':6,
        'selection':'ascending official target ID, no historical target, unique nameless weighted dependency graph within new set; then true engine witness<=35; no policy filtering',
        'scope':'all source games previously used somewhere in project; unseen tasks, NOT unseen-game generalization',
        'safety':'shared P3/P4 constraints; P0/P1/P2 exact frozen implementations',
        'local_audit':'all decisions with safety toggled for P3/P4; B/C/D toggles inP4; same recorded proposal and pre-state',
        'stop_after_formal_results':'no policy edits, steps extension, seed replacement or rerun'}
    c['mechanisms'].update(safety_versions=['P3','P4'],max_search_depth=12,max_search_nodes=64,max_candidates=48)
    atomic_json('configs/protocol_stage8.json',c)

def integration(root):
    from scar_stage8.run import episode
    from scar_stage8.agent import make_agent
    from scar_unknown17_stage7.agent import make_agent as old_agent
    from scar_sequence.prepare import NoAPIProvider
    from scar.environment import restore,AGENT_ID
    import copy
    c=next(c for c in json.loads(Path('results/stage7/cases.json').read_text()) if c['game']=='robot_kingdom')
    cfg=json.loads(Path('configs/protocol_stage8.json').read_text());records=[];prompts=[]
    root=Path(root);root.mkdir(parents=True,exist_ok=True);ip=root/'initial.pkl';ip.write_bytes(initial(c))
    class Capture(NoAPIProvider):
        def generate(self,*args,**kwargs):self.last=copy.deepcopy([args,kwargs]);return super().generate(*args,**kwargs)
    with (root/'integration.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for method in METHODS:
            task=dict(c,task_id='smoke-'+method,algorithm=method,diagnostic=True,max_steps=2,stage='smoke',initial_snapshot=str(ip))
            result=episode(task,cfg,root/'integration',None,1,provider_factory=NoAPIProvider)
            records.append({k:result[k] for k in ['algorithm','status','steps','api_calls','cost_usd','error']})
            with tempfile.TemporaryDirectory() as tmp:
                provider=Capture();ag=make_agent(method,c['game'],provider,cfg,Path(tmp)/'a')
                for h in c['history']:
                    ag.memorize(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}");ag.observe_transition(h['before'],h['action'],h['after'])
                ag.set_recovery_objective(c['target_action'],c['public_goal']);obs=restore(initial(c),tmp).obs[AGENT_ID]
                ag.act(obs);prompts.append(provider.last)
                ag.save_memory(Path(tmp)/'saved');clone=make_agent(method,c['game'],Capture(),cfg,Path(tmp)/'b');clone.load_memory(Path(tmp)/'saved')
                records[-1]['complete_agent_roundtrip']=ag.controller.to_dict()==clone.controller.to_dict() and ag.short_term_memory==clone.short_term_memory and ag.facts.to_dict()==clone.facts.to_dict()
    result={'records':records,'same_first_model_request_all5':all(x==prompts[0] for x in prompts),
        'passed':all(x['status']=='completed' and x['api_calls']==0 and x['complete_agent_roundtrip'] for x in records) and all(x==prompts[0] for x in prompts)}
    atomic_json(OUT/'integration_checks.json',result);print(json.dumps(result));assert result['passed']

def policy_freeze():
    if (OUT/'policy_freeze.json').exists():raise ValueError('Refuse overwrite policy freeze')
    assert json.loads((OUT/'offline_checks.json').read_text())['passed']
    assert json.loads((OUT/'integration_checks.json').read_text())['passed']
    paths=[str(p) for base in ['scar','scar_v2','scar_v3','scar_sequence','scar_unknown17','scar_unknown17_stage7'] for p in Path(base).rglob('*.py')]
    paths += ['scar_stage8/'+n+'.py' for n in ['__init__','controller','agent','run','offline','prepare']]+['tests/test_stage8.py','configs/protocol_stage8.json']
    atomic_json(OUT/'policy_freeze.json',{'base_commit':'adef04d812810cf0eb430e117562c257b21b5836','time_utc':now(),
        'code_hashes':{p:sha(p) for p in paths},'prior_file_hashes':json.loads((OUT/'prior_manifest.json').read_text()),
        'new_test_set_generated':False,'API_calls':0,'scope':'newtest builder/evaluator independent; no further policy change allowed'})
    print('policy frozen before new dataset generation')

def data_freeze(runtime):
    root=Path(runtime);f=json.loads((OUT/'policy_freeze.json').read_text());cs=json.loads((OUT/'cases.json').read_text());cfg=json.loads(Path('configs/protocol_stage8.json').read_text())
    assert all(sha(p)==h for p,h in f['code_hashes'].items())
    assert all(sha(p)==h for p,h in f['prior_file_hashes'].items())
    (root/'initials').mkdir(parents=True,exist_ok=True)
    for c in cs:
        raw=gzip.decompress((OUT/'initial_states'/f'{c["id"]}.pkl.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==c['snapshot_sha256'];(root/'initials'/f'{c["id"]}.pkl').write_bytes(raw)
    paths=[str(p) for p in (OUT/'initial_states').glob('*.gz')]+['results/stage8/cases.json','results/stage8/selection_plan.json','results/stage8/novelty.json','scar_stage8/build.py']
    f.update(dataset_digest=digest(cs),data_hashes={p:sha(p) for p in paths},data_freeze_time_utc=now(),families=len(cs),episodes=5*len(cs),methods=5,API_calls=0)
    atomic_json(OUT/'freeze.json',f)
    old=json.loads(Path('results/stage7/episode_metrics.json').read_text());cost=sum(x['cost_usd'] for x in old);steps=sum(x['steps'] for x in old)
    estimate=cost/steps*40*len(cs)*5
    atomic_json(OUT/'budget_estimate.json',{'families':len(cs),'episodes':5*len(cs),'max_actions':200*len(cs),
        'stage7_cost_per_action':cost/steps,'full40_estimate_usd':estimate,'increment_hard_cap_usd':5,
        'previous_cumulative_usd':31.214693910,'price_scope':'historical comparable token accounting, not current tariff/invoice','API_calls_before_freeze':0})
    print(json.dumps({'frozen':True,'episodes':5*len(cs),'full40_estimate_usd':estimate}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','integration','policy','data']);p.add_argument('--runtime');a=p.parse_args()
    if a.action=='configure':configure()
    elif a.action=='integration':integration(a.runtime)
    elif a.action=='policy':policy_freeze()
    else:data_freeze(a.runtime)
