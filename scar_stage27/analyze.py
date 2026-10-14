"""Recomputable descriptive analysis. Human semantic adjudications are data."""
import csv
import gzip
import json
import re
from collections import Counter,defaultdict
from statistics import mean
from agents.agc.state import extract
from .common import *

def csvwrite(path,records):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)

def metrics(s,c):
    cp=RESULTS/'checkpoints'/s['id']
    prefix=json.loads(gzip.decompress((cp/'public_prefix.json.gz').read_bytes()))
    before_locations={extract(r['observation'])['location'] for r in prefix}|{extract(r['feedback'])['location'] for r in prefix}
    before_events={extract(r['feedback'])['event'] for r in prefix}
    b=extract(c['observation']);a=extract(c.get('feedback',c['observation']));action=c.get('action','')
    gain={k:v-(b['hands'] or {}).get(k,0) for k,v in (a['hands'] or {}).items() if v>(b['hands'] or {}).get(k,0)}
    facts=[line for line in a['event'].splitlines() if not re.search(r'attacked|attack |defend|damage|killed|loot|enters the area|leaves the area|friction|focus|intent|stamina|dawn',line,re.I)]
    novel_noncombat_event=bool(facts and any(line not in '\n'.join(before_events) for line in facts))
    quote=(c.get('proposal') or {}).get('goal_evidence','')
    accessible=s['original_messages'][1]['content']
    supported_quote=bool(isinstance(quote,str) and quote.strip() and ' '.join(quote.split()) in ' '.join(accessible.split()))
    grounded_quote=bool(isinstance(quote,str) and quote.strip() and any(' '.join(quote.split()) in ' '.join(r[k]['text'].split()) for r in prefix for k in ['observation','feedback']))
    return dict(id=s['id'],trajectory=s['trajectory'],failure_type=s['failure_type'],step=s['step'],
        action=action,syntax_valid=c['syntax_valid'],accepted=c['accepted'],
        native_rejection=c['status']=='executed' and not c['accepted'],
        trigger_repeat_rejected=c.get('same_as_trigger',False) and not c['accepted'],
        past_failed_action_rejected=c.get('repeats_prior_failed_action',False) and not c['accepted'],
        new_public_state=bool(c.get('public_progress',{}).get('observation_new')),
        new_information=bool(c.get('public_progress',{}).get('informative')),
        new_area=bool(c['status']=='executed' and a['location'] not in before_locations),
        held_gain=bool(gain),accepted_held_gain=bool(gain) and c['accepted'],
        accepted_noncombat_information=c['accepted'] and novel_noncombat_event,
        progress_proxy=c['accepted'] and (bool(gain) or a['location'] not in before_locations or novel_noncombat_event),
        main_reward=c.get('reward',{}).get('quest',0),death=c.get('reward',{}).get('death',0),
        original_goal=s['current_goal'],proposed_goal=(c.get('proposal') or {}).get('goal_description'),
        goal_quote_in_A_input=supported_quote,goal_quote_in_public_prefix=grounded_quote,
        reasoning=(c.get('proposal') or {}).get('reasoning'),feedback=a['feedback'] if c['status']=='executed' else 'No native execution: invalid proposal')

MEASURES=['syntax_valid','accepted','native_rejection','trigger_repeat_rejected','past_failed_action_rejected',
    'new_public_state','new_information','new_area','accepted_held_gain','accepted_noncombat_information','progress_proxy','main_reward','death',
    'goal_quote_in_A_input','goal_quote_in_public_prefix']

def aggregate(entries):
    return dict(n=len(entries),**{k:sum(r[k] for r in entries) for k in MEASURES})

def main():
    offline();assert read(RESULTS/'completion.json')['complete']
    ss=samples();pairs=[];details=[];recovery=[];understanding=[];requests=[];anomalies=[]
    judgments=read(RESULTS/'understanding_judgments.json') if (RESULTS/'understanding_judgments.json').exists() else {}
    for s in ss:
        base=RESULTS/'probes'/s['id'];u=read(base/'understanding/result.json')
        understanding.append(dict(id=s['id'],trajectory=s['trajectory'],failure_type=s['failure_type'],
            gold_public_reason=s['failure_reason'],answer=u['answer'],response=u['response'],judgment=judgments.get(s['id'])))
        for condition in ['understanding','A','B'] if s['action_test_eligible'] else ['understanding']:
            raw_queries=rows(base/condition/'requests.jsonl.gz')
            for line,q in enumerate(raw_queries,1):
                requests.append(dict(id=s['id'],condition=condition,turn=q['step'],request_id=q['request_id'],status=q['status'],
                    input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0),
                    cost_usd=q.get('cost_usd',0),finish_reason=q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason'),
                    invalid_json=bool(q.get('parse_exception')),reference=str((base/condition/'requests.jsonl.gz').relative_to(ROOT))+f':{line}'))
            if condition!='understanding':
                result=read(base/condition/'result.json')
                for c in result['chain']:
                    if not c['syntax_valid']:
                        q=next(q for q in raw_queries if q['status']=='ok' and q['step']==c['turn'])
                        kind='invalid_json' if c['proposal'] is None else 'missing_action' if not isinstance(c['proposal'].get('action'),str) else 'invalid_action_syntax'
                        anomalies.append(dict(id=s['id'],condition=condition,turn=c['turn'],step=c['step'],kind=kind,
                            request_id=q['request_id'],finish_reason=q['raw_response']['choices'][0]['finish_reason'],
                            response=c['response'],proposal=c['proposal'],handling='Count as unusable proposal; no native action or paid resampling.'))
        if not s['action_test_eligible']:continue
        pair=dict(id=s['id'],trajectory=s['trajectory'],failure_type=s['failure_type'],step=s['step'])
        for condition in ['A','B']:
            result=read(base/condition/'result.json');chain=result['chain'];m=metrics(s,chain[0]);m['condition']=condition;details.append(m);pair[condition]=m
            if s['trajectory']=='parent':
                recovery.append(dict(id=s['id'],condition=condition,turns=len(chain),executed=sum(x['status']=='executed' for x in chain),
                    accepted=sum(x['accepted'] for x in chain),rejections=sum(x['status']=='executed' and not x['accepted'] for x in chain),
                    invalid=sum(not x['syntax_valid'] for x in chain),any_main=any(x.get('reward',{}).get('quest',0)>0 for x in chain),
                    main_reward=sum(x.get('reward',{}).get('quest',0) for x in chain),any_rejection=any(not x['accepted'] for x in chain),
                    all_three_accepted=len(chain)==3 and all(x['accepted'] for x in chain),
                    original_action_retry_success=any(x.get('action')==s['candidate_action'] and x['accepted'] for x in chain),
                    actions=[x.get('action') for x in chain],feedbacks=[extract(x['feedback'])['feedback'] if x.get('feedback') else 'invalid proposal' for x in chain]))
        pairs.append(pair)
    groups={}
    for group in ['all','parent','branches']+sorted({s['failure_type'] for s in ss}):
        subset=[p for p in pairs if group=='all' or group=='parent' and p['trajectory']=='parent' or group=='branches' and p['trajectory']!='parent' or p['failure_type']==group]
        if not subset:continue
        counts=Counter(('both_accepted' if p['A']['accepted'] and p['B']['accepted'] else 'B_only' if p['B']['accepted'] else 'A_only' if p['A']['accepted'] else 'neither_accepted') for p in subset)
        groups[group]=dict(A=aggregate([p['A'] for p in subset]),B=aggregate([p['B'] for p in subset]),paired_acceptance=dict(counts),
            B_minus_A_acceptance_pp=100*sum(int(p['B']['accepted'])-int(p['A']['accepted']) for p in subset)/len(subset))
    ugroups={}
    for group in ['all','parent','branches']+sorted({s['failure_type'] for s in ss}):
        subset=[u for u in understanding if group=='all' or group=='parent' and u['trajectory']=='parent' or group=='branches' and u['trajectory']!='parent' or u['failure_type']==group]
        ugroups[group]=dict(n=len(subset),labels=dict(Counter((u['judgment'] or {}).get('label','ungraded') for u in subset)))
    rec={c:dict(n=sum(r['condition']==c for r in recovery),**{k:sum(r[k] for r in recovery if r['condition']==c) for k in ['turns','executed','accepted','rejections','invalid','any_main','main_reward','any_rejection','all_three_accepted','original_action_retry_success']}) for c in ['A','B']}
    summary=dict(action_groups=groups,understanding_groups=ugroups,recovery=rec,new_requests=len(requests),
        cost_usd=sum(q['cost_usd'] for q in requests),input_tokens=sum(q['input_tokens'] for q in requests),output_tokens=sum(q['output_tokens'] for q in requests),
        invalid_json=sum(q['invalid_json'] for q in requests),truncated=sum(q['finish_reason']=='length' for q in requests),
        costs_by_condition={c:dict(requests=sum(q['condition']==c for q in requests),cost_usd=sum(q['cost_usd'] for q in requests if q['condition']==c),
            mean_input_tokens=mean(q['input_tokens'] for q in requests if q['condition']==c)) for c in ['understanding','A','B']},
        independent_parent_episodes=1,no_significance_claim=True)
    summary['unusable_proposals']=dict(Counter(a['kind'] for a in anomalies))
    write(RESULTS/'response_anomalies.json',anomalies)
    write(RESULTS/'summary.json',summary);write(RESULTS/'paired_comparison.json',pairs);write(RESULTS/'recovery.json',recovery)
    gzwrite(RESULTS/'understanding_answers.jsonl.gz',understanding);csvwrite(RESULTS/'action_quality.csv',details);csvwrite(RESULTS/'request_index.csv',requests)
    csvwrite(RESULTS/'paired_comparison.csv',[dict(id=p['id'],trajectory=p['trajectory'],step=p['step'],failure_type=p['failure_type'],
        A_action=p['A']['action'],B_action=p['B']['action'],A_accepted=p['A']['accepted'],B_accepted=p['B']['accepted'],
        A_main=p['A']['main_reward'],B_main=p['B']['main_reward']) for p in pairs])
    print(json.dumps({k:summary[k] for k in ['new_requests','cost_usd','invalid_json','truncated','recovery']}),flush=True)

if __name__=='__main__':main()
