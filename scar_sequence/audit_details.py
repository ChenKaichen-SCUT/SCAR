"""Detailed old-family failure modes from frozen records, separate from policy."""
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
from scar.io import atomic_json
from scar_v3.state import PublicState,parse_action


def main():
    root=Path('results/v3/attribution')
    with gzip.open(root/'audits.jsonl.gz','rt') as f:audits={r['case_id']:r for r in map(json.loads,f)}
    with gzip.open(root/'branches.jsonl.gz','rt') as f:
        witnesses={r['state']['case_id']:r['upper'] for r in map(json.loads,f) if r['state']['index']==0}
    cases={c['id']:c for c in json.loads(Path('results/v3/dataset/cases.json').read_text())}
    groups={r['case_id']:r for r in json.loads((root/'case_classifications.json').read_text())}
    traces=defaultdict(dict)
    with gzip.open('results/v3/formal/trajectories_SCARV3Agent.jsonl.gz','rt') as f:
        for item in map(json.loads,f):
            if item['task']['stage']=='hard':traces[item['task']['family']][item['transition']['index']]=item['transition']
    result=[]
    for ident,audit in audits.items():
        case=cases[ident];events=defaultdict(list);local=traces[case['family']]
        graph=case.get('recipe_graph',{});resources={k for r in graph.values() for k in r['ingredients']}
        def add(kind,row,detail,strength='direct_record'):
            events[kind].append({'index':row['index'],'action':row['executed_action'],
                'state_hash':row['state_digest'],'detail':detail,'strength':strength})
        stored_in_ground={};seen={}
        for r in audit['rows']:
            actual=r['outcomes'][r['executed_action']];base=r['outcomes'].get(r['proposed_action'])
            if base and r['learned_base_prediction']['status']=='REJECT' and not base['truth']['rejected']:
                add('false_precondition_rejection',r,{'predicted':r['learned_base_prediction'],'oracle_feedback':base['truth']['feedback']})
            if base and base['truth']['rejected'] and r['learned_base_prediction']['status']!='REJECT':
                add('unidentified_rejection',r,{'predicted':r['learned_base_prediction']['status'],'oracle':base['truth']})
            p=parse_action(r['executed_action'])
            if p.verb=='craft' and actual['truth']['rejected']:
                needed=[(key,value) for key,value in r['goal_conditions']['facts'].items()
                        if not value.get('met') and value.get('object_id') in graph]
                if needed:add('unsatisfied_intermediate_at_target_attempt',r,needed,
                              'direct_missing_resource; omitted_subgoal_is_a_causal_hypothesis')
            if p.verb=='drop' and 'obj_'+p.target in resources:
                add('future_material_dropped',r,{'goal_regression':actual['progress']['regressed'],
                    'child_state':actual['child_state_digest'],'permanent_loss':None},
                    'direct_drop; resource remains on ground and may be recoverable')
            if r['memory_plan'].get('actions') and any(e.get('event')=='plan_invalidated' for e in r['events']):
                add('plan_discarded',r,r['memory_plan'],'direct_clear; plan_validity_and_causality_unverified')
            if r['memory_plan'].get('actions') and r['executed_action'] not in r['memory_plan']['actions']:
                add('action_deviates_from_cached_plan',r,r['memory_plan'],
                    'direct_deviation; repair_may_be_necessary')
            trace=local.get(r['index'])
            if trace:
                before=PublicState.observe(trace['observation']);after=PublicState.observe(trace['next_observation'])
                if p.verb=='store' and not actual['truth']['rejected']:
                    name=p.args[-1]
                    if name!='inventory' and name in (before.ground or {}) and name not in (before.hands or {}):
                        stored_in_ground[name]={'location':before.location,'item':p.target,'index':r['index']}
                if before.location!=after.location:
                    for name,detail in stored_in_ground.items():
                        if detail['location']==before.location and name not in (before.hands or {}) and name not in (before.equipment or {}):
                            add('left_loaded_ground_container',r,{'container':name,'stored':detail,'after_location':after.location},
                                'publicly_observed_access_loss; future_return_possible')
                if 'not enough space in hand' in actual['truth']['feedback']:
                    add('hand_capacity_rejection',r,{'hands':before.hands,'feedback':actual['truth']['feedback']})
            child=actual['child_physical_key']
            if p.verb in {'store','take out','drop','pick up'} and child in seen:
                add('physical_resource_revisit',r,{'previous_index':seen[child],'child_physical_key':child},
                    'physical_revisit; no_information_gain_or_pointlessness_claim')
            seen[r['physical_key']]=r['index']
            for e in r['events']:
                if e.get('event')=='goal_superseded':add('explicit_goal_switch',r,e)
        result.append({'case_id':ident,'family':case['family'],'group':groups[ident]['group'],
            'target':case['target_action'],'physical_goal':case['goal'],'failure_modes':dict(events),
            'recovery_witness':{'actions':case['witness'],'verified':case['validated'],'initial_hash':case['state_hash'],
                                'source':'results/v3/dataset/cases.json'},
            'additional_counterfactual_witness':witnesses.get(ident),
            'method_outcomes':groups[ident]['outcomes'],
            'sources':['results/v3/attribution/audits.jsonl.gz','results/v3/formal/trajectories_SCARV3Agent.jsonl.gz',
                       'results/v3/attribution/case_classifications.json'],
            'causal_status':'All categories are trace evidence or explicitly qualified hypotheses; STM success alone proves no planning mechanism.'})
    atomic_json('results/sequence/old_failure_modes.json',result)
    atomic_json('results/sequence/old_failure_mode_counts.json',{'families':len(result),
        'families_per_mode':dict(Counter(k for r in result for k,v in r['failure_modes'].items() if v)),
        'stm_only_families':sum(r['group']=='stm_only' for r in result),'api_calls':0})

if __name__=='__main__':main()
