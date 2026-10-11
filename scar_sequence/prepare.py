"""Preflight, historical cost estimate and immutable pre-experiment manifest."""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from scar.io import atomic_json,digest
from scar.environment import restore
from scar_sequence.run import episode
from scar_sequence.offline import execute_public_controller


METHODS=['ShortTermMemoryAgent','SimpleFailureRecovery','SCARV3Agent','ResourceFIFO','SRP']


class NoAPIProvider:
    """Infrastructure smoke test, deliberately supplies no successful plan."""
    def __init__(self,*args,**kwargs):self.tokens_in=self.tokens_out=0
    def generate(self,*args,**kwargs):
        return {'response':'{"action":"wait","reasoning":"zero API integration check"}',
                'parsed':{'action':'wait','reasoning':'zero API integration check'},
                'num_input_tokens':0,'num_output_tokens':0}


def prepare(runtime):
    root=Path(runtime);out=Path('results/sequence');out.mkdir(parents=True,exist_ok=True)
    if (out/'freeze.json').exists():raise RuntimeError('Already frozen; do not overwrite')
    tests=json.loads((root/'offline/offline_tests.json').read_text())
    if not tests['gate_passed']:raise ValueError('Offline gate not passed')
    config=json.loads(Path('configs/protocol_v3.json').read_text())
    config.update(protocol_cohort='sequence_v1',algorithms=METHODS,games=['saltglass','quarantine','robot_kingdom'],
        max_steps=40,diagnostic_max_steps=40,test_seeds=[],total_budget_usd=12.0,max_workers=12,
        budget_authorization='prior_user_authorized_required_experiments_no_20_usd_cap; incremental_guard_12_usd',
        initial_workers=4,episode_budget_usd=0.5)
    cases=json.loads((root/'dataset/cases.json').read_text())
    for case in cases:
        env=restore(case['initial_snapshot'])
        case['object_names']={oid:obj.name for oid,obj in env.world.objects.items()}
    atomic_json(root/'dataset/cases.json',cases)
    config['dataset_sha256']=digest(cases)
    config['predeclared_outcomes']={'method_format_abort':'failure_in_full_denominator; no rerun',
        'transport_error':'incomplete; resumable only under same frozen policy and checkpoint',
        'global_budget_stop':'incomplete; never treated as algorithm failure',
        'paired_seed':'one frozen physical state and common public history per family; no provider seed available',
        'primary':'35 family paired Recovery@40, craft-only and knowledge/game breakdowns also mandatory',
        'statistics':'family paired bootstrap 10000 seed20261012; mechanism/source cluster sensitivity; no causal knowledge-stratum claim',
        'long_games':0}
    history=json.loads(Path('results/v3/formal/all_summaries.json').read_text())
    rates={}
    for method in METHODS[:3]:
        rows=[r for r in history if r['algorithm']==method and r.get('stage')=='hard' and r.get('steps',0)>0]
        rates[method]=sum(r['conservative_cost_usd'] for r in rows)/sum(r['steps'] for r in rows)
    rates['SRP']=rates['ResourceFIFO']=rates['ShortTermMemoryAgent']
    estimate=sum(rates.values())*len(cases)*40
    atomic_json(out/'budget_estimate.json',{'families':len(cases),'episodes':len(cases)*5,'max_steps':40,
        'per_step_historical_usd':rates,'full_40_step_estimate_usd':estimate,
        'planning_with_50_percent_contingency_usd':estimate*1.5,'new_hard_guard_usd':12,
        'per_episode_guard_usd':0.5,'previous_project_conservative_usd':23.130083244,
        'pricing':config['pricing_usd_per_million'],'basis':'Frozen historical accounting prices, not a current tariff or invoice.',
        'authorization':'User already authorized required experiments beyond prior 20 USD cap; guard prevents accidental unlimited execution.'})
    # Full runner, checkpoint and serialization checks for all five methods.
    dev=json.loads(next((root/'offline/dev/candidates').glob('*/case.json')).read_text())
    if not dev['validated']:
        dev=next(json.loads(p.read_text()) for p in (root/'offline/dev/candidates').glob('*/case.json') if json.loads(p.read_text())['validated'])
    checks=[]
    for method in METHODS:
        task={k:v for k,v in dev.items() if k not in {'witness','witness_replay'}}
        task.update(task_id='smoke-'+method,algorithm=method,diagnostic=True,max_steps=2,stage='smoke',protocol_cohort='zero_api_infrastructure')
        result=episode(task,config,root/'integration',None,1,provider_factory=NoAPIProvider)
        checks.append({k:result[k] for k in ['algorithm','status','steps','api_calls','cost_usd','error']})
    atomic_json(out/'integration_checks.json',checks)
    if not all(r['status']=='completed' and r['api_calls']==0 for r in checks):raise ValueError('Integration gate failed')
    # Original 12 negative cases: regression evidence, not independent performance.
    groups=json.loads(Path('results/v3/attribution/case_classifications.json').read_text())
    old={c['id']:c for c in json.loads(Path('results/v3/dataset/cases.json').read_text())}
    regressions=[]
    with gzip.open(out/'old_regression_traces.jsonl.gz','wt') as f:
        for row in groups:
            if row['group']!='stm_only':continue
            for mode in ['srp','fifo']:
                result=execute_public_controller(old[row['case_id']],mode)
                f.write(json.dumps(result,ensure_ascii=False)+'\n')
                regressions.append({k:v for k,v in result.items() if k!='trace'})
    atomic_json(out/'old_regression_summary.json',regressions)
    atomic_json(out/'offline_tests.json',tests)
    Path('configs').mkdir(exist_ok=True)
    atomic_json('configs/protocol_sequence.json',config)
    # Publish generated observations, edits, witness paths and hashes, not the
    # downloaded engine. Trustworthy snapshots stay on the experiment server.
    for name in ['cases.json','construction.json','selection_plan.json','supplement_manifest.json']:
        (out/'dataset').mkdir(exist_ok=True)
        (out/'dataset'/name).write_bytes((root/'dataset'/name).read_bytes())
    names=sorted(str(p) for base in ['scar','scar_v2','scar_v3','scar_sequence'] for p in Path(base).rglob('*.py'))
    names+=['configs/protocol_sequence.json']
    hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}
    protected=json.loads((out/'prior_manifest.json').read_text())
    if any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha for name,sha in protected.items()):
        raise ValueError('Previously frozen artifact changed')
    atomic_json(out/'freeze.json',{'dataset_digest':digest(cases),'families':len(cases),'episodes':len(cases)*5,
        'code_hashes':hashes,'protected_prior_files':protected,'base_commit':'a32a1c635700686ff9d09957dc8dda52ff25886b',
        'selection_before_paid_calls':True,'no_test_policy_scores_inspected':True,
        'new_api_calls_so_far':0,'protocol':config['predeclared_outcomes']})
    print(json.dumps({'frozen':True,'families':len(cases),'episodes':len(cases)*5,'estimated_usd':estimate,'cap':12,'integration':checks}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args()
    with open(Path(a.runtime)/'preflight.log','w') as log,contextlib.redirect_stderr(log):prepare(a.runtime)
