"""Post-hoc request integrity and behavior summaries; does not alter the gate."""
import collections
import datetime
import gzip
import json
from pathlib import Path

from scar.io import atomic_json
from scar_v3.state import parse_action

OUT=Path('results/stage12/diagnostic')


def main():
    requests=[json.loads(line) for line in (OUT/'requests.jsonl').read_text().splitlines()]
    frozen={(r['state_id'],r['method'],r['replicate']):r for r in json.loads((OUT/'frozen_queries.json').read_text())}
    freeze=json.loads((OUT/'freeze.json').read_text());earliest=datetime.datetime.fromisoformat(freeze['time_utc']).timestamp()
    cfg=json.loads(Path('configs/protocol_stage12_diagnostic.json').read_text());models={};errors=[]
    for wrapper in requests:
        r=wrapper['request'];key=tuple(wrapper[k] for k in ['state_id','method','replicate']);q=frozen[key]
        if r['messages']!=[{'role':'system','content':q['system']},{'role':'user','content':q['user']}]:errors.append({'query':key,'kind':'prompt_mismatch'})
        if r['start']<earliest:errors.append({'query':key,'kind':'request_before_freeze'})
    for method in ['J2','J3']:
        rs=[r['request'] for r in requests if r['method']==method]
        models[method]={'requests':len(rs),'served_models':dict(collections.Counter(r.get('raw_response',{}).get('model') for r in rs)),
            'statuses':dict(collections.Counter(r['status'] for r in rs)),
            'thinking':dict(collections.Counter(r['thinking'] for r in rs)),
            'input_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in rs),
            'output_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in rs),
            'cache_hit_tokens':sum(r.get('usage',{}).get('prompt_cache_hit_tokens',0) for r in rs),
            'cache_miss_tokens':sum(r.get('usage',{}).get('prompt_cache_miss_tokens',0) for r in rs),
            'cost_usd':sum(r.get('cost_usd',0) for r in rs),
            'charged_or_reserved_usd':sum(r.get('charged_or_reserved_usd',0) for r in rs)}
    states={s['state_id']:s for s in json.loads((OUT/'states.json').read_text())}
    judgments={(r['state_id'],r['method'],r['replicate']):r for r in json.loads((OUT/'judgments.json').read_text())}
    aliases=[]
    for state in states.values():
        groups=collections.defaultdict(list)
        for c in state['candidates']:
            groups[(c['kind'],c['target'],c.get('location'),c['next_action'])].append(c['id'])
        duplicate=[v for v in groups.values() if len(v)>1]
        if duplicate:
            ranked=judgments[state['state_id'],'J3',0].get('parsed',{}).get('ranked_candidate_ids',[])
            aliases.append({'state_id':state['state_id'],'duplicate_groups':duplicate,
                            'ranked_duplicate':any(len(set(v)&set(ranked))>1 for v in duplicate)})
    atomic_json(OUT/'candidate_alias_audit.json',{'post_hoc_descriptive':True,'records':aliases,
        'states_with_duplicate_public_intents':len(aliases),
        'redundant_entries':sum(len(v)-1 for r in aliases for v in r['duplicate_groups']),
        'top3_repeated_intent_states':sum(r['ranked_duplicate'] for r in aliases),
        'interpretation':'exact rule-action anchors can duplicate an existing public inspection/craft intent; frozen menu was not changed after results; Top3 counts distinct IDs, not necessarily distinct semantic directions'})
    raw_top3=[]
    for c in json.loads((OUT/'candidate_coverage.json').read_text())['states']:
        ranked=judgments[c['state_id'],'J3',0].get('parsed',{}).get('ranked_candidate_ids',[])
        match=sorted(set(c['raw_entry_useful_ids'])&set(ranked))
        if match:raw_top3.append({'state_id':c['state_id'],'candidate_ids':match})
    branches={r['state_id']:r for r in map(json.loads,gzip.open(OUT/'native_branches.jsonl.gz','rt'))}
    rows=json.loads((OUT/'state_metrics.json').read_text());behavior={}
    for method in ['J0','J1','J2','J3']:
        counts=collections.Counter();rejections=collections.Counter()
        for r in rows:
            if r['method']!=method or not r['valid']:continue
            s=states[r['state_id']];b=branches[r['state_id']]['branches'][r['selected_id']];c=b['candidate']
            goal=parse_action(s['public_view']['target_action']).target
            stations={x for recipe in s['public_view']['confirmed_recipe_relations'].values()
                      for x in (recipe['stations'] if isinstance(recipe['stations'],list) else [])}
            if c['kind']=='visit' and c['target'] in stations:counts['visit_known_station']+=1
            if c['kind']=='inspect' and c['target']==goal:counts['inspect_final_target']+=1
            if c['kind']=='inspect' and c['target'] in s['public_view']['inspected']:counts['repeat_previously_inspected']+=1
            counts['native_goal_achieved_in_diagnostic_branch']+=b['goal']
            counts['branch_hit_4_action_limit']+=b['stop']=='action_limit'
            for step in b['trace']:
                if step['rejected']:rejections[step['feedback'].split('\n')[0]]+=1
        behavior[method]={'counts':dict(counts),'rejection_feedback_counts':dict(rejections)}
    atomic_json(OUT/'model_audit.json',{'methods':models,'frozen_query_count':len(frozen),
        'prompt_or_timing_errors':errors,'passed':not errors and all(m['served_models']=={'deepseek-flash':m['requests']} for m in models.values()),
        'protocol_parameters':{k:cfg[k] for k in ['model','temperature','thinking','max_tokens','short_term_memory_size']},
        'primary_vs_replicate':'one primary and prespecified repeat; none selected by outcome',
        'cost_basis':cfg['pricing_basis']})
    atomic_json(OUT/'behavior_audit.json',{'methods':behavior,'post_hoc_descriptive':True,
        'J3_raw_entry_top3_states':raw_top3,
        'raw_entry_definition':'predeclared proxy: publicly unconnected, no publicly known recipe or recorded production; can include an actually craftable intermediate',
        'interpretation':'no new necessary relation within4 actions is not proof an action has no station, material or long-horizon value'})
    gate=json.loads((OUT/'gate.json').read_text())
    if not gate['passed']:
        atomic_json('results/stage12/closed_loop/status.json',{'status':'not_run','reason':'Stage A failed frozen gate',
            'planned_episodes_if_passed':40,'actual_episodes':0,'api_calls':0,
            'methods':{m:{'status':'not_run','recovery_at_40':None} for m in ['B0','B1','B2','B3']},
            'not_a_failure_score':True,'online_plan_module_developed':False})
    print(json.dumps({'requests':len(requests),'cost_usd':sum(m['cost_usd'] for m in models.values()),'audit_passed':not errors,'gate':gate['decision']}))


if __name__=='__main__':main()
