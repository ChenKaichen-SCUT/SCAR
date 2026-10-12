"""Preflight inputs and historical cost/batch audit, never imported by policy."""
import copy
import datetime
import subprocess
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import sha,records,load,save_records
from scar_stage10.controller import ResourceController
from scar_stage15.controller import Controller15,SWITCHES
from scar_stage15.knowledge import PublicTable
ROOT=Path('results/stage15')
BASE='568a16712255e014da554276d999680c8531ea8e'


def adapted(old,tracker,method,index):
    data=Controller15(method).to_dict()
    data.update(copy.deepcopy(old))
    for key,value in tracker.to_dict().items():
        if key.endswith('15'):data[key]=copy.deepcopy(value)
    data['method15']=method;data['modules15']=list(SWITCHES[method]);data['step15']=index
    data['table']['knowledge15']=tracker.table.knowledge15.to_dict()
    c=Controller15.from_dict(data);c.table.sync();return c


def main():
    ROOT.mkdir(exist_ok=True)
    if not (ROOT/'prior_manifest.json').exists():
        assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
        atomic_json(ROOT/'prior_manifest.json',{p:sha(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p})
    requests=[r['request'] for m in ['E0','E1','E2','E3','E4'] for r in records(f'results/stage11/requests_{m}.jsonl.gz')]
    observed={'episodes':50,'calls':len(requests),'cost_usd':sum(r.get('cost_usd',0) for r in requests),
       'input_tokens':sum((r.get('usage') or {}).get('prompt_tokens',0) for r in requests),
       'output_tokens':sum((r.get('usage') or {}).get('completion_tokens',0) for r in requests)}
    atomic_json(ROOT/'cost_estimate.json',{'history':observed,'estimate70':{k:v*1.4 for k,v in observed.items()},
        'guard_global':5,'guard_episode':.2,'basis':'same frozen peak price accounting; actual prompt length/cache can change','authorization':'Guide15 plus prior explicit waiver; cap is protective not extra authorization'})
    batches=list(records('results/stage10/batch_audit.jsonl.gz'));comparisons=[]
    for r in batches:
        v={int(x['action'].split()[1]):x for x in r['variants']}
        if 1 in v and 2 in v:
            a,b=v[1],v[2]
            comparisons.append({'task':r['task_id'],'index':r['index'],'target':r['target'],
               'one':{k:a[k] for k in ['actual_output','consumed']},'two':{k:b[k] for k in ['actual_output','consumed']},
               'both_requested_fulfilled':a['actual_output']==1 and b['actual_output']==2,
               'linear':b['consumed']=={k:2*x for k,x in a['consumed'].items()}})
    atomic_json(ROOT/'historical_batch_semantics.json',{'rows':comparisons,'policy_receives_this_file':False,
        'interpretation':'actual output may be capped; both output and consumption required to test linearity; no historical oracle samples seeded online'})
    cases={c['id']:c for c in load('results/stage11/cases.json')};decisions=[];jobs=[];selected=set();regression=[]
    for ep in records('results/stage10/trajectories_S1.jsonl.gz'):
        case=cases[ep['case_id']];tracker=Controller15('P1')
        for h in case['history']:tracker.observe(h['before'],h['action'],h['after'])
        tracker.set_goal(case['target_action'],case['public_goal'])
        regression.append({'case_id':case['id'],'task_id':ep['task_id'],'historical_success':ep['summary']['diagnostic_goal_reached'] if 'diagnostic_goal_reached' in ep['summary'] else any(r['diagnostic_goal_reached'] for r in ep['rows']),
                           'actions':[r['executed_action'] for r in ep['rows']],'proposals':[r['proposed_action'] for r in ep['rows']]})
        seen_kinds=set()
        for row in ep['rows']:
            i=row['index'];old=ResourceController.from_dict(copy.deepcopy(row['stage7_state_before']))
            assert old.choose(row['observation'],row['proposed_action'])==row['executed_action']
            adapted_cs={m:adapted(row['stage7_state_before'],tracker,m,i) for m in SWITCHES}
            variants={m:{'state':copy.deepcopy(c.to_dict()),'action':c.choose(row['observation'],row['proposed_action']),'decision':c.audit15} for m,c in adapted_cs.items()}
            knowledge=tracker.table.knowledge15
            assert all(e['observed_step']<=row['observation']['step'] for e in knowledge.events)
            assert all(f['quantities']==variants['P1']['state']['table']['recipes'][n]['quantities'] for n,f in knowledge.relations().items())
            decisions.append({'case_id':case['id'],'index':i,'old':row['executed_action'],'proposal':row['proposed_action'],
                'actions':{m:v['action'] for m,v in variants.items()},'audits':{m:v['decision'] for m,v in variants.items()}})
            kinds=[]
            for m in ['P2','P3','P4','P5','P6']:
                if variants[m]['action']!=variants['P1']['action'] and m not in seen_kinds:kinds.append('first_'+m);seen_kinds.add(m)
            if i in {0,len(ep['rows'])-1}:kinds.append('boundary')
            if row['objective_metrics'].get('unaccounted_resource_destruction'):kinds.append('historical_loss')
            if row.get('structured',{}).get('mechanisms',{}).get('exploration',{}).get('spent')==18:kinds.append('quota_edge')
            if kinds:
                jobs.append({'id':case['id']+'-'+str(i),'case_id':case['id'],'index':i,'kinds':kinds,
                    'historical_task':ep['task_id'],'observation':row['observation'],'original_action':row['executed_action'],
                    'variants':variants,'proposals':[r['proposed_action'] for r in ep['rows'][i:i+7]],
                    'original_actions':[r['executed_action'] for r in ep['rows'][i:i+7]]})
            tracker=adapted(row['stage7_state_before'],tracker,'P1',i)
            tracker.pending_probe=copy.deepcopy(old.pending_probe);tracker.explore_pending=copy.deepcopy(old.explore_pending)
            tracker.exploration_spent=old.exploration_spent
            tracker.observe(row['observation'],row['executed_action'],row['next_observation'])
    save_records(ROOT/'historical_public_decisions.jsonl.gz',decisions)
    save_records(ROOT/'preflight_jobs.jsonl.gz',jobs);atomic_json(ROOT/'regression_inputs.json',regression)
    atomic_json(ROOT/'preflight_plan.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'selection':'each family first intervention per module, initial/final boundary, every historical objective-resource-loss, quota18; chosen without native outcome filtering',
        'states':len(jobs),'restored_S1_decisions':len(decisions),'branch_limit':7,'methods':['P0',*SWITCHES],
        'P0':'recorded native actions','P1_to_P6':'public policy with frozen historical proposals; diagnostic not new LLM closed loop',
        'regression':'all10 original S1 action trajectories; no API calls; branch actions are actual engine transitions'})
    print({'states':len(jobs),'restored':len(decisions),'cost70':observed['cost_usd']*1.4})

if __name__=='__main__':main()
