"""Post-run local causal checks on actual successes; no policy reruns or API."""
import argparse
import contextlib
import gzip
import json
from pathlib import Path
from scar.io import atomic_json
from scar_unknown17.audit import branch,save_state
from scar_v3.state import parse_action


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/unknown17')
    cases={c['id']:c for c in json.loads((out/'cases.json').read_text())}
    metrics=json.loads((out/'episode_metrics.json').read_text());by={(r['case_id'],r['algorithm']):r for r in metrics}
    results=[]
    with open(root/'success_checks_engine.log','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for path in sorted(out.glob('trajectories_*.jsonl.gz')):
            for ep in map(json.loads,gzip.open(path,'rt')):
                s=ep['summary'];cid=ep['case_id'];method=s['algorithm']
                if not s['recovery_at_40']:continue
                rows=ep['rows'];case=cases[cid];checks=[]
                # First quantity override, plus first directed forward craft or
                # inspection producing a needed recipe, selected independently
                # of the counterfactual outcome. At most two local tests/episode.
                chosen={}
                for r in rows:
                    mechanisms=r.get('structured',{}).get('mechanisms',{});batch=mechanisms.get('batch') or {};explore=mechanisms.get('exploration') or {}
                    if batch and batch.get('original_action')!=r['executed_action'] and 'batch' not in chosen:
                        chosen['batch']=(r,batch['original_action'])
                    new_names={n for d in s['discovery_events'] if d['index']==r['index'] for n in d['recipes']}
                    if explore and (new_names or explore.get('reason')=='bounded forward recipe trial') and 'exploration' not in chosen:
                        alt=r['proposed_action'] if r['proposed_action']!=r['executed_action'] else 'wait'
                        chosen['exploration']=(r,alt)
                for kind,(r,alt) in chosen.items():
                    i=r['index'];folder=root/'runs'/ep['task_id']
                    state=folder/'initial.pkl' if i==0 else folder/'steps'/f'{i:04}'/'environment.pkl'
                    raw=state.read_bytes();suffix=[x['executed_action'] for x in rows[i+1:]]
                    actual=branch(raw,[r['executed_action']]+suffix,case)
                    cf=branch(raw,[alt]+suffix,case)
                    assert actual['goal']
                    checks.append({'kind':kind,'index':i,'state':save_state(raw,cid,f'new-{method}-{i}-{kind}'),
                        'actual':actual,'replacement':cf,'identical_continuation':True,
                        'actual_reaches_goal_alternative_does_not':not cf['goal'],
                        'scope':'local action replacement under fixed recorded continuation; does not emulate adaptive model or establish necessity of memory module'})
                results.append({'case_id':cid,'method':method,'steps':len(rows),'fresh_FIFO_success':by[(cid,'ResourceFIFO')]['recovery_at_40'],
                    'fresh_STM_success':by[(cid,'ShortTermMemoryAgent')]['recovery_at_40'],
                    'discovery_events':s['discovery_events'],'directed_discovered_then_crafted':s['directed_discovered_then_crafted'],
                    'summary_retained_key_facts':s['summary_key_facts_numerator'],'checks':checks,
                    'claim_boundary':'Same-state action effect may be causal locally. Whole-method outcome difference remains exposed to model sampling and changed histories.'})
    atomic_json(out/'success_evidence.json',results)
    print(json.dumps({'successful_episodes':len(results),'local_checks':sum(len(x['checks']) for x in results),'api_calls':0}))

if __name__=='__main__':main()
