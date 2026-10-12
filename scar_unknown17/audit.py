"""Offline-only attribution. Hidden engine facts never enter a decision policy.

Read every prior trace; replay all 85 unknown-task episodes. Witness branches
establish local possibility, not an autonomous policy's success probability.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import gzip
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import tempfile

from scar.environment import AGENT_ID, restore, snapshot, state_digest
from scar.diagnostics.build import transition
from scar.io import atomic_json, digest
from scar_sequence.public import ResourceTable
from scar_sequence.evaluate import physical
from scar_sequence.supplement import goal_reached
from scar_sequence.resource_audit import census
from scar_v3.state import parse_action

SOURCE = Path('results/sequence')
OUT = Path('results/unknown17')

def known_recipes(table):
    return {name for name, r in table.recipes.items() if r.get('ingredients')}



def cases():
    return [c for c in json.loads((SOURCE/'dataset/cases.json').read_text())
            if c['kind']=='craft' and c['knowledge']=='interaction_discovery']


def initial(case):
    raw=gzip.decompress((SOURCE/'dataset/initial_states'/f'{case["id"]}.pkl.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==case['snapshot_sha256']
    return raw


def branch(raw, actions, case):
    endings=[]; trace=[]
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env=restore(raw,tmp); trace=[]
            for action in actions:
                before=physical(env,case)
                row=transition(env,action)
                trace.append(dict(row,physical_before=before,physical_after=physical(env,case),
                                  state_hash=state_digest(env),goal=goal_reached(env,case['goal'])))
            endings.append(state_digest(env))
    assert endings[0]==endings[1]
    return {'actions':actions,'trace':trace,'goal':goal_reached(env,case['goal']),
            'final_hash':endings[0],'independently_replayed_twice':True}


def save_state(raw, cid, label):
    path=OUT/'counterfactual_states'/f'{cid}-{label}.pkl.gz'
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(raw)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'serialized_sha256':hashlib.sha256(raw).hexdigest()}


def audit_family(job):
    case,episodes=job; cid=case['id']; names=case['object_names']
    needed={names[k] for k in case['recipe_graph']}
    truth={names[k]:{'ingredients':{names[x]:n for x,n in r['ingredients'].items()},
                    'stations':[names[x] for x in r['dependencies']]} for k,r in case['recipe_graph'].items()}
    raw=initial(case); initial_table=ResourceTable()
    for h in case['history']:initial_table.observe(h['before']);initial_table.observe(h['after'],h['action'])
    result={'case_id':cid,'game':case['game'],'goal':case['goal'],'hidden_truth_evaluation_only':truth,
        'initial_public_knowledge':initial_table.to_dict(),'history_length':len(case['history']),
        'methods':{},'public_discovery_probes':[],'batch_branches':[],
        'witness':case['witness'],'scope':'Exploratory known cases. Counterfactual witness suffix is evaluator-only, never a policy hint.'}
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        result['witness_check']=branch(raw,case['witness'],case)
        # Probe every public object on a successful real witness, once per object.
        env=restore(raw,tmp);seen=set();table=copy.deepcopy(initial_table)
        for wi in range(len(case['witness'])+1):
            s=table.state
            visible=set(s.get('ground') or {})|set(s.get('hands') or {})|set(s.get('equipment') or {})
            for c,v in table.containers.items():
                if table.carried(c):visible.update(v['counts'] or {})
            for item in sorted(visible-seen):
                seen.add(item); b=snapshot(env)
                probe=branch(b,['inspect '+item],case)
                pt=copy.deepcopy(table);pt.observe(probe['trace'][0]['after'],'inspect '+item)
                gains=sorted((known_recipes(pt)-known_recipes(table))&needed)
                if gains:
                    result['public_discovery_probes'].append({'witness_index':wi,'object':item,
                        'key_recipe_gain':gains,'state':save_state(b,cid,f'discovery-{wi}-{len(result["public_discovery_probes"])}'),
                        'inspect':probe,'wait_control':branch(b,['wait'],case),
                        'strength':'paired same-state information effect; witness access may require hidden evaluator guidance'})
            if wi==len(case['witness']):break
            action=case['witness'][wi];p=parse_action(action)
            if p.verb=='craft':
                b=snapshot(env)
                variants=[]
                for amount in [1,2,4]:
                    a=f'craft {amount} {p.target}'
                    res=branch(b,[a]+case['witness'][wi+1:],case)
                    variants.append(dict(amount=amount,**res))
                result['batch_branches'].append({'witness_index':wi,'target':p.target,
                    'state':save_state(b,cid,f'batch-{wi}'),'variants':variants,
                    'same_suffix':True,'strength':'local causal batch replacement under fixed evaluator witness suffix'})
            h=transition(env,action);table.observe(h['before']);table.observe(h['after'],action)
        # Fully read and independently execute all previous actual decisions.
        for ep in episodes:
            env=restore(raw,tmp);t=copy.deepcopy(initial_table);events=[]; discoveries=[];crafts=[];first={}
            known_used=set(); inspections=[]; missed=[]; repeats=[];signature={};deviations=[]
            for row in ep['rows']:
                i=row['index'];a=row['executed_action'];p=parse_action(a); before=snapshot(env)
                assert env.obs[AGENT_ID]['text']==row['observation']['text']
                old_rec=known_recipes(t); ready=row['physical_before']['conditions'].get(case['goal']['object_id'],{})
                if ready and all(v for g in ready.values() for v in g.values()) and p.target!=case['goal']['name']:
                    missed.append({'index':i,'actual':a,'kind':'ingredients/station ready; final pickup still required'})
                if p.verb=='inspect':inspections.append({'index':i,'action':a,'feedback':row['action_rule_feedback']})
                if p.verb=='craft':
                    known_used.add(p.target)
                    crafts.append({'index':i,'action':a,'feedback':row['action_rule_feedback'],
                        'public_recipe_before':copy.deepcopy(t.recipes.get(p.target)),
                        'conditions_before':row['physical_before']['conditions'],
                        'physical_before':row['physical_before'],'physical_after':row['physical_after']})
                h=transition(env,a)
                assert h['after']['text']==row['next_observation']['text']
                t.observe(h['before']);t.observe(h['after'],a)
                gains=sorted((known_recipes(t)-old_rec)&needed)
                for name in gains:first.setdefault(name,i)
                if gains:discoveries.append({'index':i,'action':a,'key_recipe_gain':gains,'feedback':row['action_rule_feedback']})
                key=(row['physical_before']['resource_hash'],a)
                if key in signature:repeats.append({'first_index':signature[key],'index':i,'action':a,'new_key_rules':gains})
                signature[key]=i
                if row['semantic_rejection']:events.append({'index':i,'action':a,'feedback':row['action_rule_feedback'],
                    'category':'F7' if row.get('engine_invalid') or 'Invalid ' in row['action_rule_feedback'] else 'F4' if 'space in hand' in row['action_rule_feedback'] else 'F3' if 'Cannot craft a single' in row['action_rule_feedback'] else 'F8',
                    'strength':'observed rejection; task-level causal necessity unproven'})
            known=known_recipes(t)&needed; missing=sorted(needed-known)
            discoverable={n for x in result['public_discovery_probes'] for n in x['key_recipe_gain']}
            cats=[]
            if set(missing)&discoverable:cats.append('F1')
            if known-known_used:cats.append('F2')
            if any(e['category']=='F3' for e in events):cats.append('F3')
            if any(e['category']=='F4' for e in events) or ep['summary'].get('resource_destruction_steps'):cats.append('F4')
            if repeats:cats.append('F5')
            if any(e['category']=='F7' for e in events):cats.append('F7')
            if not ep['summary']['recovery_at_40']:cats.append('F8')
            # F6 requires a concrete missing proposal, not mere final failure.
            absent=[n for n in known if not any(parse_action(a).target==n and parse_action(a).verb=='craft'
                    for r in ep['rows'] for a in r.get('all_proposals',[]))]
            if absent:cats.append('F6')
            primary='success' if ep['summary']['recovery_at_40'] else ('F1' if missing else 'F3' if 'F3' in cats else 'F8')
            result['methods'][ep['summary']['algorithm']]={'recovered':ep['summary']['recovery_at_40'],
                'steps':len(ep['rows']),'categories':cats,'primary_observable_bottleneck':primary,
                'strength':'descriptive trace evidence; local branch support is separately enumerated',
                'information_actions':inspections,'discoveries':discoveries,'first_discovery':first,
                'known_key_recipes':sorted(known),'missing_key_recipes':missing,'known_but_never_crafted':sorted(known-known_used),
                'candidate_absence':absent,'rejections':events,'crafts':crafts,'resource_repeats':repeats,
                'missed_ready_goal_actions':missed,'earliest_observed_rejection':events[0] if events else None,
                'final_materials':ep['rows'][-1]['physical_after'],'final_public_table':t.to_dict(),
                'replay_exact':True,'repair_hypotheses':[
                    'Inspect public raw materials and produced intermediates; use bounded forward probes to bridge an unknown target recipe.',
                    'Compare batch 1/2/4 effects without assuming nominal fractions or linear consumption.',
                    'Expose observed facts to base STM; retain UNKNOWN and timestamped locations.',
                    'Do not equate missing proposals or repetitions with proven task-level cause.']}
    atomic_json(OUT/'families'/f'{cid}.json',result)
    return {k:result[k] for k in ['case_id','game','goal']}|{'methods':{m:{k:v[k] for k in ['recovered','primary_observable_bottleneck','categories','missing_key_recipes']} for m,v in result['methods'].items()},
        'public_discovery_probes':len(result['public_discovery_probes']),'batch_states':len(result['batch_branches']),
        'batch_suffix_outcome_changes':sum(len({v['goal'] for v in b['variants']})>1 for b in result['batch_branches'])}


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'families').mkdir(exist_ok=True)
    cs=cases();groups={c['id']:[] for c in cs};read=[]
    for path in sorted(SOURCE.glob('trajectories_*.jsonl.gz')):
        all_rows=[json.loads(l) for l in gzip.open(path,'rt')]
        read.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'episodes_fully_parsed':len(all_rows),'actions_fully_parsed':sum(len(e['rows']) for e in all_rows)})
        for e in all_rows:
            if e['case_id'] in groups:groups[e['case_id']].append(e)
    for name in ['dataset/cases.json','typical_cases.json','old_failure_modes.json']:
        data=json.loads((SOURCE/name).read_text());read.append({'path':str(SOURCE/name),'records_fully_parsed':len(data),
            'sha256':hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()})
    atomic_json(OUT/'source_read_manifest.json',read)
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        records=list(pool.map(audit_family,[(c,groups[c['id']]) for c in cs]))
    atomic_json(OUT/'attribution_summary.json',records)
    print(json.dumps({'families':len(records),'episodes_replayed':sum(len(x['methods']) for x in records),
                      'api_calls':0,'discovery_probes':sum(x['public_discovery_probes'] for x in records)}))

if __name__=='__main__':main()
