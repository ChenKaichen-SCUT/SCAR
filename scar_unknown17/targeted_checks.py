"""Additional predeclared-by-behavior local checks after inspecting raw evidence.

Retains the initial first-attempt checks. Test ALL productive quantity overrides
in successful episodes, so a rejected first attempt cannot obscure a later effect.
Inspection controls use wait to avoid introducing a different location as the
explanation for a purported information effect. Still no adaptive model reruns.
"""
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
    cases={c['id']:c for c in json.loads((out/'cases.json').read_text())};records=[]
    with open(root/'targeted_checks.log','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for path in sorted(out.glob('trajectories_*.jsonl.gz')):
            for ep in map(json.loads,gzip.open(path,'rt')):
                if not ep['summary']['recovery_at_40']:continue
                cid=ep['case_id'];method=ep['summary']['algorithm'];rows=ep['rows']
                discoveries={x['index'] for x in ep['summary']['discovery_events'] if x['directed']}
                for r in rows:
                    i=r['index'];p=parse_action(r['executed_action']);mechs=r.get('structured',{}).get('mechanisms',{})
                    batch=mechs.get('batch') or {};kind=None;alternative=None
                    if p.verb=='craft' and 'successfully crafted' in r['action_rule_feedback'] and batch.get('original_action')!=r['executed_action'] and batch:
                        kind='all_productive_batch_overrides';alternative=batch['original_action']
                    elif p.verb=='inspect' and i in discoveries:
                        kind='information_inspect_vs_wait';alternative='wait'
                    if not kind:continue
                    folder=root/'runs'/ep['task_id'];start=folder/'initial.pkl' if i==0 else folder/'steps'/f'{i:04}'/'environment.pkl'
                    raw=start.read_bytes();suffix=[v['executed_action'] for v in rows[i+1:]]
                    actual=branch(raw,[r['executed_action']]+suffix,cases[cid]);cf=branch(raw,[alternative]+suffix,cases[cid]);assert actual['goal']
                    records.append({'case_id':cid,'method':method,'index':i,'kind':kind,
                        'state':save_state(raw,cid,f'targeted-{method}-{i}'),'actual':actual,'replacement':cf,
                        'local_success_depends_on_actual':not cf['goal'],
                        'scope':'Same remaining action sequence, no extra steps. Inspection removal does not remove knowledge from the fixed continuation; not an autonomous information-value test.'})
    with gzip.open(out/'targeted_counterfactuals.jsonl.gz','wt') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    summary={'checks':len(records),'api_calls':0,'selection':'all successful quantity overrides and all directed key-recipe inspections in every successful episode; original first-attempt checks retained',
        'local_goal_changes':[{'case_id':r['case_id'],'method':r['method'],'index':r['index'],'kind':r['kind'],
            'actual':r['actual']['actions'][0],'alternative':r['replacement']['actions'][0]} for r in records if r['local_success_depends_on_actual']],
        'per_check':[{'case_id':r['case_id'],'method':r['method'],'index':r['index'],'kind':r['kind'],
            'changed_goal':r['local_success_depends_on_actual']} for r in records]}
    atomic_json(out/'targeted_checks_summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='per_check'}))

if __name__=='__main__':main()
