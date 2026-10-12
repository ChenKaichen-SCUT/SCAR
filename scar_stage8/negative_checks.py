"""Post-hoc fixed-suffix diagnosis, never a policy edit or extra model episode."""
import argparse,contextlib,gzip,json
from pathlib import Path
from scar_unknown17.audit import branch
from scar_stage8.offline import save_state
from scar.io import atomic_json


def main(runtime):
    root=Path(runtime);out=Path('results/stage8');cases={c['id']:c for c in json.loads((out/'cases.json').read_text())};records=[]
    targets={
        'sequence-48401b39ba565b57':{'P3':14,'P4':13,'alternative':'store 2 sinew_cord inventory','suffix':['craft 1 bandage_roll','pick up bandage_roll'],'cause':'capacity dead end: hold existing cord and collect remaining grounded cord in one store'},
        'sequence-583fbd031e489fe8':{'P3':10,'P4':8,'alternative':'craft 2 fiend_alloy','suffix':['store 2 fiend_alloy inventory','craft 1 fiend_alloy_sheet','store 1 fiend_alloy_sheet inventory','craft 1 fiend_alloy_scale','pick up fiend_alloy_scale'],'cause':'default demand1 becomes hard batch upper bound before downstream need discovered'},
        'stage8-b1691776b6c8220e':{'P3':14,'P4':12,'alternative':'craft 2 knapped_edge','suffix':['store 2 knapped_edge inventory','craft 2 stone_slab','store 2 stone_slab inventory','craft 1 stone_blade','pick up stone_blade'],'cause':'minimum trial repeated separately can waste fractional input rounding; larger efficient batch needed'},
    }
    with (root/'negative-checks.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for m in ['P3','P4']:
            for ep in map(json.loads,gzip.open(out/f'trajectories_{m}.jsonl.gz','rt')):
                cid=ep['case_id']
                if cid not in targets:continue
                spec=targets[cid];i=spec[m];row=ep['rows'][i];folder=root/'runs'/ep['task_id'];raw=(folder/'initial.pkl' if i==0 else folder/'steps'/f'{i:04}'/'environment.pkl').read_bytes()
                actions=[spec['alternative']]+spec['suffix'];assert i+len(actions)<=40
                old=branch(raw,[row['executed_action']]+spec['suffix'],cases[cid]);new=branch(raw,actions,cases[cid])
                records.append({'case_id':cid,'method':m,'index':i,'task_id':ep['task_id'],'state':save_state(raw,ep['task_id']+'-negative-'+str(i)),
                    'original_action':row['executed_action'],'base_action':row['proposed_action'],'public_observation':row['observation'],
                    'controller_state':row['stage7_state_before'],'alternative_action':spec['alternative'],'suffix':spec['suffix'],
                    'actual_safety':row['structured'].get('safety'),'original_fixed_suffix':old,'alternative_fixed_suffix':new,
                    'diagnostic_hypothesis':spec['cause'],'within40':True,'strict_local_improvement':new['goal'] and not old['goal'],
                    'scope':'post-hoc evaluator-supplied common continuation from same real state, independently replayed twice; NOT autonomous model recovery'})
    # Follow-up diagnostics retain the unsuccessful batch-only hypotheses above.
    late=[('sequence-583fbd031e489fe8','P3',16,'enter cellar',['pick up hellcoal_concentrate','enter courtyard','craft 1 fiend_alloy','store 1 fiend_alloy inventory','craft 1 fiend_alloy_sheet','store 1 fiend_alloy_sheet inventory','craft 1 fiend_alloy_scale','pick up fiend_alloy_scale']),
        ('sequence-583fbd031e489fe8','P4',18,'craft 1 fiend_alloy',['store 1 fiend_alloy inventory','craft 1 fiend_alloy_sheet','store 1 fiend_alloy_sheet inventory','craft 1 fiend_alloy_scale','pick up fiend_alloy_scale']),
        ('stage8-b1691776b6c8220e','P3',29,'craft 1 stone_blade',['pick up stone_blade']),
        ('stage8-b1691776b6c8220e','P4',26,'store 1 knapped_edge inventory',['craft 1 knapped_edge','store 1 knapped_edge inventory','craft 1 stone_blade','pick up stone_blade'])]
    with (root/'negative-checks-late.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for cid,m,i,alternate,suffix in late:
            ep=next(e for e in map(json.loads,gzip.open(out/f'trajectories_{m}.jsonl.gz','rt')) if e['case_id']==cid);row=ep['rows'][i]
            raw=(root/'runs'/ep['task_id']/'steps'/f'{i:04}'/'environment.pkl').read_bytes();assert i+1+len(suffix)<=40
            old=branch(raw,[row['executed_action']]+suffix,cases[cid]);new=branch(raw,[alternate]+suffix,cases[cid])
            records.append({'case_id':cid,'method':m,'index':i,'task_id':ep['task_id'],'state':save_state(raw,ep['task_id']+'-late-negative-'+str(i)),
                'original_action':row['executed_action'],'base_action':row['proposed_action'],'public_observation':row['observation'],'controller_state':row['stage7_state_before'],
                'alternative_action':alternate,'suffix':suffix,'actual_safety':row['structured'].get('safety'),'original_fixed_suffix':old,'alternative_fixed_suffix':new,
                'diagnostic_hypothesis':'late no-progress: transport, forward demand lower-bound, or known final execution missing from candidate set',
                'within40':True,'strict_local_improvement':new['goal'] and not old['goal'],
                'scope':'post-hoc evaluator continuation after failed batch-only hypothesis; no policy modification or API calls'})
    atomic_json(out/'negative_counterfactuals.json',{'API_calls':0,'policy_changed':False,'records':records,
        'selection':'post-hoc diagnosis of lost bandage/fiend_scale regressions and new stone_blade reference successes; not all failures explained',
        'improved_fixed_suffixes':sum(x['strict_local_improvement'] for x in records)})
    print(json.dumps([{'method':r['method'],'case':r['case_id'],'old':r['original_fixed_suffix']['goal'],'alternative':r['alternative_fixed_suffix']['goal'],'first_feedback':r['alternative_fixed_suffix']['trace'][0]['feedback']} for r in records]))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();main(a.runtime)
