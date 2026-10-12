"""Finite 102-episode configuration and pre-call immutable source freeze."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from scar.io import atomic_json,digest
from scar_unknown17.audit import initial
from scar_unknown17_stage7.controller import CONFIGS

OUT=Path('results/stage7')

def configure():
    OUT.mkdir(parents=True,exist_ok=True)
    cs=json.loads(Path('results/unknown17/cases.json').read_text())
    config=json.loads(Path('configs/protocol_unknown17.json').read_text())
    config.update(protocol_cohort='stage7_v1',algorithms=list(CONFIGS),switches=CONFIGS,
        total_budget_usd=5.0,episode_budget_usd=.25,
        budget_authorization='User waived 20 USD cap; guide7 finite 102 episodes with new 5 USD incremental guard')
    config['predeclared_outcomes'].pop('fixed_batch_extra_comparator',None)
    config['predeclared_outcomes'].update(formal_episodes=102,only_internal_combined_controls=True,
        same_checkpoint_one_switch_audit='all 4 toggles at every committed formal decision; fixed recorded base action; same starting physical checkpoint',
        conversion_censoring='remaining to 40 actions for any discovered but unexecuted recipe / all-known uncompleted goal',
        scoring_cannot_change_policy=True)
    config['mechanisms'].update(stage7_flags=CONFIGS,quantity_candidates=[1,2,3,4],
        quantity_numbers='D alone reads explicit public acquisition numeric recipes only for names already in shared FIFO table',
        same_prompt_and_summary_for_all=True,no_extra_model_calls=True)
    atomic_json('configs/protocol_stage7.json',config);atomic_json(OUT/'cases.json',cs)
    old=[r for r in json.loads(Path('results/unknown17/episode_metrics.json').read_text()) if r['algorithm']=='FIFOCombined']
    cost=sum(r['cost_usd'] for r in old);steps=sum(r['steps'] for r in old)
    atomic_json(OUT/'budget_estimate.json',{'historical_17_cost_usd':cost,'historical_steps':steps,
        'nominal_six_cohorts_usd':6*cost,'full_4080_actions_historical_rate_usd':cost/steps*4080,
        'prompt_change_tokens':0,'controller_extra_API_calls':0,'hard_incremental_cap_usd':5,
        'episode_guard_usd':.25,'previous_cumulative_usd':28.977867894,
        'price_scope':'historical comparable accounting, not current invoice',
        'authorization':config['budget_authorization'],'total_episodes':102})
    names=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
    atomic_json(OUT/'prior_manifest.json',{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in names if p})


def freeze(runtime):
    if (OUT/'freeze.json').exists():raise ValueError('Refuse to overwrite formal freeze')
    checks=json.loads((OUT/'offline_checks.json').read_text());assert checks['passed']
    cs=json.loads((OUT/'cases.json').read_text());root=Path(runtime);(root/'initials').mkdir(parents=True,exist_ok=True)
    for c in cs:(root/'initials'/f'{c["id"]}.pkl').write_bytes(initial(c))
    previous=json.loads((OUT/'prior_manifest.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in previous.items())
    paths=sorted(str(p) for base in ['scar','scar_v2','scar_v3','scar_sequence','scar_unknown17'] for p in Path(base).rglob('*.py'))
    paths+=['scar_unknown17_stage7/'+n+'.py' for n in ['__init__','controller','agent','run','prepare','offline']]
    paths+=['configs/protocol_stage7.json','tests/test_stage7.py']
    atomic_json(OUT/'freeze.json',{'base_commit':'44297e64351262a78a56953ee3f1dee0101d3bd7',
        'code_hashes':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        'dataset_digest':digest(cs),'prior_file_hashes':previous,'families':17,'methods':6,'episodes':102,
        'freeze_scope':'all prior sources plus new policy, agent, runner, preparation, offline gates and tests; postprocessing hash manifest published separately',
        'api_calls_before_freeze':0,'exploratory_seen_cases':True,'formal_results_used_for_tuning':False,
        'offline_checks':checks,'configurations':CONFIGS,'max_steps':40,'same_original_seed':True})
    print(json.dumps({'frozen':True,'episodes':102,'api_calls_before_freeze':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:freeze(a.runtime)
    else:configure()
