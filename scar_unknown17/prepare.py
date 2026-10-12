"""Historical usage estimate and immutable pre-call freeze, no paid calls."""
import argparse
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json,digest
from scar_unknown17.audit import cases,initial
from scar_unknown17.agent import METHODS


def configure():
    out=Path('results/unknown17');out.mkdir(parents=True,exist_ok=True)
    config=json.loads(Path('configs/protocol_sequence.json').read_text())
    config.update(protocol_cohort='unknown17_v1',algorithms=METHODS,total_budget_usd=4.0,episode_budget_usd=.25,
        budget_authorization='prior_user_waived_project_cap; guide6 required finite cohort; new automatic guard 4 USD',
        predeclared_outcomes={'primary':'17 exploratory family-paired Recovery@40; game strata; no new generalization claim',
            'max_steps':40,'one_frozen_seed_per_family':True,'long_games':0,
            'format_abort':'failure in denominator, no retry','infrastructure_error':'incomplete, same checkpoint only',
            'batch_stop':'incomplete, never algorithm failure','fixed_batch_extra_comparator':True,
            'statistical_unit':'family, not step; paired bootstrap and per-game raw counts; no stable significance claim'},
        mechanisms={'directed_actions_max':18,'forward_trials_max':4,'batch_candidates':[1,2,4],
            'summary_max_records':48,'summary_max_characters':6000,'summary_extra_calls':0})
    cs=cases();config['dataset_sha256']=digest(cs)
    atomic_json('configs/protocol_unknown17.json',config);atomic_json(out/'cases.json',cs)
    old=json.loads(Path('results/sequence/episode_metrics.json').read_text())
    rates={}
    for m in ['ShortTermMemoryAgent','ResourceFIFO']:
        rows=[r for r in old if r['algorithm']==m and r['case_id'] in {c['id'] for c in cs}]
        rates[m]=sum(r['cost_usd'] for r in rows)/sum(r['steps'] for r in rows)
    steps=17*40
    base=steps*(rates['ShortTermMemoryAgent']*2+rates['ResourceFIFO']*6)
    # Three methods append at most 6000 characters. Plan using 2000 extra cache-
    # miss input tokens per call, explicitly a proxy, not the provider tokenizer.
    summary_extra=3*steps*2000*config['pricing_usd_per_million']['cache_miss']/1e6
    atomic_json(out/'budget_estimate.json',{'families':17,'methods':8,'episodes':136,'max_steps':40,
        'historical_unknown_only_cost_per_step':rates,'base_full_40_estimate_usd':base,
        'summary_additional_uncached_proxy_usd':summary_extra,'estimated_total_usd':base+summary_extra,
        'hard_stop_usd':4,'episode_stop_usd':.25,'previous_cumulative_usd':25.770981798,
        'prices':config['pricing_usd_per_million'],'pricing_scope':'historical comparable accounting, not current supplier invoice',
        'authorization':'User authorized required experiments with no 20 USD cap; finite new 4 USD automatic guard.',
        'no_srp_v3_rerun':True})
    print(json.dumps({'estimate_usd':base+summary_extra,'guard':4,'episodes':136}))


def freeze(runtime):
    root=Path(runtime);out=Path('results/unknown17')
    if (out/'freeze.json').exists():raise ValueError('Refuse to overwrite a formal freeze')
    checks=json.loads((out/'offline_checks.json').read_text());assert checks['passed']
    cs=cases();(root/'initials').mkdir(parents=True,exist_ok=True)
    for c in cs:(root/'initials'/f'{c["id"]}.pkl').write_bytes(initial(c))
    previous=json.loads((out/'prior_manifest.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in previous.items())
    paths=sorted(str(p) for base in ['scar','scar_v2','scar_v3','scar_sequence','scar_unknown17'] for p in Path(base).rglob('*.py'))
    paths+=['configs/protocol_unknown17.json','tests/test_unknown17.py']
    atomic_json(out/'freeze.json',{'base_commit':'2496b60d52767e3915a62fe60f874902fd68a489',
        'code_hashes':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        'dataset_digest':digest(cs),'prior_file_hashes':previous,'families':17,'methods':8,'episodes':136,
        'api_calls_before_freeze':0,'exploratory_seen_cases':True,'formal_results_used_for_tuning':False,
        'offline_checks':checks,'single_attempt_per_family_method':True,'no_new_long_games':True})
    print(json.dumps({'frozen':True,'episodes':136,'new_api_calls':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:freeze(a.runtime)
    else:configure()
