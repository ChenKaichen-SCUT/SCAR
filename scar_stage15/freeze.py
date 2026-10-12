"""One-time acceptance gate and immutable formal protocol; no paid API here."""
import datetime
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import load,sha,records
ROOT=Path('results/stage15')


def main():
    assert not (ROOT/'freeze.json').exists(),'Policy already frozen; no revisions after paid launch'
    prior=load(ROOT/'prior_manifest.json')
    for path,h in prior.items():assert sha(path)==h,path
    server=load(ROOT/'preflight_server/summary.json');local=load(ROOT/'preflight_local_summary.json')
    assert server['native_branches_digest']==local['native_branches_digest'] and server['repeats']==local['repeats']==2
    rows=list(records(ROOT/'preflight_server/native_branches.jsonl.gz'))
    retained={m:all(not r['branches']['P0']['goal'] or r['branches'][m]['goal'] for r in rows) for m in ['P1','P2','P3','P4','P5','P6']}
    assert all(retained.values())
    first_harm=[]
    for r in rows:
        old=r['branches']['P1']['trace']
        for method in ['P2','P3','P4','P6']:
            new=r['branches'][method]['trace']
            if old and new and old[0]['action']!=new[0]['action'] and not old[0]['rejected'] and new[0]['rejected']:
                first_harm.append([r['state_id'],method])
    assert not first_harm,first_harm
    for where in ['local','server']:
        smoke=load(ROOT/f'smoke_{where}.json');assert len(smoke['rows'])==7 and smoke['api_calls']==0
        assert all(r['status']=='completed' and r['restored_memory'] for r in smoke['rows'])
    acceptance={'passed':True,'API_calls':0,'protected_files':len(prior),'native_four_passes_equal':True,
      'native_states':len(rows),'branches_per_pass':len(rows)*7,'actions_per_pass':server['actions_per_pass'],
      'successful_baseline_branches_preserved':retained,'first_action_legal_to_rejected':first_harm,
      'scope':'short public-policy diagnostic branches with recorded proposals, NOT full-task LLM success evidence',
      'tests':load(ROOT/'tests.json'),'revision_record':'pre_freeze_revisions.json'}
    atomic_json(ROOT/'acceptance.json',acceptance)
    code={str(p):sha(p) for p in sorted(Path('scar_stage15').glob('*.py'))}
    code['configs/protocol_stage15.json']=sha('configs/protocol_stage15.json')
    # P0 and dependencies are also anchored by all historical hashes.
    code.update({p:h for p,h in prior.items() if p.endswith('.py')})
    data={'results/stage11/cases.json':sha('results/stage11/cases.json')}
    data.update({str(p):sha(p) for p in sorted(Path('results/stage11/initial_states').glob('*.gz'))})
    data.update({str(ROOT/n):sha(ROOT/n) for n in ['acceptance.json','cost_estimate.json','preflight_jobs.jsonl.gz','preflight_plan.json','historical_batch_semantics.json']})
    config=load('configs/protocol_stage15.json')
    assert config['algorithms']==[f'P{i}' for i in range(7)] and config['max_steps']==40
    atomic_json(ROOT/'freeze.json',{'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'base_commit':'568a16712255e014da554276d999680c8531ea8e','code_hashes':code,'data_hashes':data,
      'dataset_digest':digest(load('results/stage11/cases.json')),'episodes':70,'new_cost_cap_usd':5,
      'P0':'fresh frozen Stage10 S1 execution; no copied success scores','max_steps':40,
      'policy_changes_after_freeze':False,'selective_reruns':False,'acceptance':acceptance})
    print({'frozen':True,'episodes':70,'protected_files':len(prior)})

if __name__=='__main__':main()
