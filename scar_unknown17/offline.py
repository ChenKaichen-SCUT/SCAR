"""Zero-API mechanism gates; never counted as closed-loop recovery scores."""
import argparse
import contextlib
import copy
import gzip
import json
from pathlib import Path
import tempfile
from scar.environment import restore,AGENT_ID,snapshot
from scar.diagnostics.build import transition
from scar.io import atomic_json
from scar_unknown17.audit import cases,initial,branch,save_state,known_recipes
from scar_unknown17.controller import SimpleController
from scar_unknown17.facts import PublicFacts
from scar_unknown17.agent import METHODS
from scar_unknown17.run import episode
from scar_sequence.prepare import NoAPIProvider


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();runtime=Path(a.runtime)
    out=Path('results/unknown17');cs=cases();checks=[];traces=[];summary_checks=[]
    config=json.loads(Path('configs/protocol_unknown17.json').read_text())
    with open(runtime/'offline_engine.log','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        # The exact two earlier illustrative states, now independently reconstructed.
        for cid,method,index,actions,label in [
            ('sequence-48401b39ba565b57','SRP',6,None,'bandage_batch'),
            ('sequence-7ef74a089f1ce41d','SRP',40,['store 1 machete inventory'],'machete_after_cap')]:
            all_cases=json.loads(Path('results/sequence/dataset/cases.json').read_text());case=next(c for c in all_cases if c['id']==cid)
            ep=next(e for e in map(json.loads,gzip.open(f'results/sequence/trajectories_{method}.jsonl.gz','rt')) if e['case_id']==cid)
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(initial(case),tmp)
                for r in ep['rows'][:index]:transition(env,r['executed_action'])
                raw=snapshot(env);state=save_state(raw,cid,label)
                variants=([branch(raw,[f'craft {n} sinew_cord','inspect inventory','store 2 sinew_cord inventory','craft 1 bandage_roll','pick up bandage_roll'],case) for n in [1,2]]
                          if actions is None else [branch(raw,actions,case)])
                checks.append({'name':label,'state':state,'variants':variants,'api_calls':0,
                    'passed':[v['goal'] for v in variants]==([False,True] if actions is None else [True]),
                    'scope':'local counterfactual only; does not alter Stage 5 or grant any formal extra steps'})
        # Read-only factual memory validation against every actual unknown trace.
        ids={c['id']:c for c in cs}
        for path in Path('results/sequence').glob('trajectories_*.jsonl.gz'):
            for ep in map(json.loads,gzip.open(path,'rt')):
                if ep['case_id'] not in ids:continue
                case=ids[ep['case_id']];f=PublicFacts()
                for h in case['history']:f.observe(h['before'],h['action'],h['after'])
                f.set_goal(case['target_action'],case['public_goal']);steps=0;maxchars=0;unknown_ok=True;retained=[]
                for r in ep['rows']:
                    text,meta=f.render(r['observation']);maxchars=max(maxchars,len(text))
                    rendered={x['key'] for x in meta['records'] if x['kind']=='recipe' and x['value']['ingredients']!='UNKNOWN'}
                    seen=known_recipes(f.table)
                    retained.append({'index':r['index'],'known':len(seen),'rendered':len(seen&rendered)})
                    unknown_ok &= all(x['value']['quantities'].startswith('UNKNOWN') for x in meta['records'] if x['kind']=='recipe')
                    f.observe(r['observation'],r['executed_action'],r['next_observation']);steps+=1
                summary_checks.append({'case_id':case['id'],'method':ep['summary']['algorithm'],'steps':steps,
                    'max_characters':maxchars,'unknown_quantities_preserved':unknown_ok,'retention_by_step':retained,
                    'passed':unknown_ok and maxchars<=6000})
        # Public-only deterministic trajectories are mechanism development probes,
        # not model results. No test score is used as a gate or selection criterion.
        for case in cs:
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(initial(case),tmp);c=SimpleController(True,'learned');rows=[]
                for h in case['history']:c.observe(h['before'],h['action'],h['after'])
                c.set_goal(case['target_action'],case['public_goal'])
                for i in range(12):
                    before=copy.deepcopy(env.obs[AGENT_ID]);a1=c.choose(before,'wait')
                    h=transition(env,a1);decision=copy.deepcopy(c.last_choice)
                    c.observe(h['before'],a1,h['after'])
                    rows.append(dict(h,index=i,decision=decision,events=copy.deepcopy(c.events)))
                    c.events.clear()
                traces.append({'case_id':case['id'],'scope':'12-step zero-API mechanism probe, not recovery evaluation','rows':rows})
        # Check the complete runner and checkpoint serialization for every method.
        c=cs[0];(runtime/'initials').mkdir(parents=True,exist_ok=True)
        path=runtime/'initials'/f'{c["id"]}.pkl';path.write_bytes(initial(c))
        integration=[]
        for method in METHODS:
            task=dict(c,task_id='smoke-'+method,algorithm=method,diagnostic=True,max_steps=2,stage='smoke',
                protocol_cohort='zero_api_infrastructure',initial_snapshot=str(path))
            r=episode(task,config,runtime/'integration_final',None,1,provider_factory=NoAPIProvider)
            integration.append({k:r[k] for k in ['algorithm','status','steps','api_calls','cost_usd','error']})
    atomic_json(out/'offline_counterfactuals.json',checks)
    atomic_json(out/'summary_history_checks.json',summary_checks)
    atomic_json(out/'integration_checks.json',integration)
    with gzip.open(out/'offline_public_probes.jsonl.gz','wt') as f:
        for r in traces:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    result={'local_counterfactuals_passed':all(x['passed'] for x in checks),'history_checks':len(summary_checks),
        'summary_checks_passed':all(x['passed'] for x in summary_checks),
        'integration_passed':all(x['status']=='completed' and x['api_calls']==0 for x in integration),
        'public_only_probes':len(traces),'api_calls':0,'formal_scores_used_for_tuning':False}
    result['passed']=all(result[x] for x in ['local_counterfactuals_passed','summary_checks_passed','integration_passed'])
    atomic_json(out/'offline_checks.json',result);print(json.dumps(result))

if __name__=='__main__':main()
