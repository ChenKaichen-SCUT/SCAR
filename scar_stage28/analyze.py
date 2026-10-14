"""Recomputable descriptive metrics. No mechanism is fed back into the Agent."""
import csv
import re
from collections import Counter
from agents.agc.state import extract
from .common import *
from .chain import analyze_event,intent

def accepted(r):return not extract(r['feedback'])['failed'] and not r['info'].get('step_invalid_action',{}).get(AGENT_ID,False)

def chapter1(r):return int((r.get('main_quest_progress') or {}).get('chapter',0))>=1

def metrics(s,rr,prefix,window):
    observed=rr[:window];chain=analyze_event(s,rr,window)
    states=[extract(p['observation']) for p in prefix]+[extract(p['feedback']) for p in prefix]
    seen={x['signature'] for x in states};locations={x['location'] for x in states};events={x['event'] for x in states}
    novel=[];new_locations=[];new_events=[];gains=[]
    for r in observed:
        before=extract(r['observation']);after=extract(r['feedback'])
        if after['signature'] not in seen:novel.append(r['step'])
        if after['location'] not in locations:new_locations.append(dict(step=r['step'],location=after['location']))
        if accepted(r) and after['event'] not in events:new_events.append(r['step'])
        seen.add(after['signature']);locations.add(after['location']);events.add(after['event'])
        # Hands + equipment only; unknown container contents never treated as zero.
        b=Counter(before['hands'] or {})+Counter(before['equipment'] or {})
        a=Counter(after['hands'] or {})+Counter(after['equipment'] or {})
        inc=a-b
        if inc:gains.append(dict(step=r['step'],items=dict(inc),caveat='Observed holding increase, may be retrieving an already owned item.'))
    return dict(window=window,actions=len(observed),window_complete=len(observed)==window,
        rejected=sum(not accepted(r) for r in observed),wait=sum(r['action']=='wait' for r in observed),
        supplemental_failure_steps=[r['step'] for r in observed if accepted(r) and re.search(r'^Failed to\b',extract(r['feedback'])['feedback'],re.I)],
        repeated_original_rejection=chain['repeated_rejection_count'],successful_original_retry=bool(chain['original_action_success_steps']),
        successful_original_retry_steps=chain['original_action_success_steps'],closed_loop=bool(chain['local_closed_loop_steps']),
        recovery_execution_steps=chain['execution_steps'],consecutive_execution=bool(chain['consecutive_execution_pairs']),
        goal_string_return_steps=chain['original_goal_string_return_steps'],new_public_state_steps=novel,new_location_events=new_locations,
        new_accepted_event_steps=new_events,holding_increases=gains,main_gain=sum(r['reward']['quest'] for r in observed),
        chapter1=chapter1(observed[-1]) if observed else False,
        main_final=observed[-1]['scores']['quest'] if observed else None)

def pair_counts(pairs,metric,window):
    out=Counter({'both':0,'Original_only':0,'Oracle_only':0,'neither':0})
    for p in pairs:
        a=bool(p['variants']['Original']['windows'][window][metric]);b=bool(p['variants']['OracleRecovery']['windows'][window][metric])
        out['both' if a and b else 'Original_only' if a else 'Oracle_only' if b else 'neither']+=1
    return dict(out)

def main():
    offline();ss=samples();sources={p:rows(ROOT/p) for p in {s['source_trajectory'] for s in ss}}
    chains={r['id']:r for r in rows(RESULTS/'failure_recovery_chains.jsonl.gz')};database=[]
    for s in ss:
        rr=[r for r in sources[s['source_trajectory']] if r['step']>s['step']];last=sources[s['source_trajectory']][-1]
        final=analyze_event(s,rr,max(1,len(rr)))
        database.append(dict(**s,chain20=chains[s['id']],chain5=analyze_event(s,rr,5),eventual_result=dict(
            suffix_actions=len(rr),final_absolute_step=last['step'],scores=last['scores'],main_quest_progress=last['main_quest_progress'],
            successful_original_retry_steps=final['original_action_success_steps'],local_closed_loop_steps=final['local_closed_loop_steps'],
            original_goal_return_steps=final['original_goal_string_return_steps'],main_gain=final['main_gain'],
            completed_chapter1=chapter1(last))))
    gzwrite(RESULTS/'failure_recovery_database.jsonl.gz',database)
    probes=rows(RESULTS/'native_feasibility_probes.jsonl.gz');pairs=[];cost=read(RESULTS/'cost_reconciliation.json');requests=[];exceptions=[]
    for ident,s in selected().items():
        prefix=json.loads(gzip.decompress((ROOT/'results/stage27/checkpoints'/ident/'public_prefix.json.gz').read_bytes()))
        pair=dict(id=ident,failure_step=s['step'],type=s['failure_type'],action=s['candidate_action'],goal=s['current_goal'],objective=CASES[ident],variants={})
        for variant in ['Original','OracleRecovery']:
            out=RESULTS/'runs'/ident/variant;rr=suffix(s) if variant=='Original' else rows(out/'trajectory.jsonl.gz');summary=read(out/'summary.json')
            pair['variants'][variant]=dict(summary=summary,first_decision=intent(s,rr[0]['decision']['attempts'][-1]['proposal']),first_action=rr[0]['action'],
                windows={str(w):metrics(s,rr,prefix,w) for w in [5,20,len(rr)]},
                probes=[p for p in probes if p['id']==ident and p['variant']==variant],
                final_main=rr[-1]['scores']['quest'],chapter1=chapter1(rr[-1]),
                final_goal=rr[-1]['decision']['attempts'][-1]['proposal'].get('goal_description'))
            if variant=='OracleRecovery':
                for q in rows(out/'requests.jsonl.gz'):
                    requests.append(dict(id=ident,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],status=q['status'],
                        input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0),cost_usd=q.get('cost_usd',0),
                        finish_reason=q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason'),injected=q['step']==s['step']+1))
                    if q.get('parse_exception') or q['status']!='ok':exceptions.append(dict(id=ident,kind='provider_or_json',request_id=q['request_id'],step=q['step'],details=q))
                for r in rr:
                    for index,a in enumerate(r['decision']['attempts'],1):
                        if not a.get('executed'):exceptions.append(dict(id=ident,step=r['step'],kind='native_hard_retry' if a.get('hard') else 'native_confidence_review',attempt=index,details=a))
                if summary['status']=='agent_decision_exhausted':exceptions.append(dict(id=ident,kind='terminal_decision_exhausted',details=read(out/'decision_exhausted.json')))
        pairs.append(pair)
    write(RESULTS/'paired_comparison.json',pairs);gzwrite(RESULTS/'exceptions.jsonl.gz',exceptions)
    with (RESULTS/'request_accounting.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(requests[0]),lineterminator='\n');w.writeheader();w.writerows(requests)
    improvement=sum(p['variants']['OracleRecovery']['final_main']>p['variants']['Original']['final_main'] for p in pairs)
    worsened=sum(p['variants']['OracleRecovery']['final_main']<p['variants']['Original']['final_main'] for p in pairs)
    chapter_delta=sum(p['variants']['OracleRecovery']['chapter1']-p['variants']['Original']['chapter1'] for p in pairs)
    local=pair_counts(pairs,'successful_original_retry','20');local_delta=local['Oracle_only']-local['Original_only']
    write(RESULTS/'summary.json',dict(pairs=len(pairs),independent_parent_episodes=1,freeze_commit='07c8284',
        local_actual_retry_pair_counts=local,local_net_improvement=local_delta,clear_local_improvement=local_delta>=3,
        main_improved=improvement,main_worsened=worsened,chapter1_net_improvement=chapter_delta,clear_long_improvement=improvement>=3 or chapter_delta>=3,
        variants={v:dict(actions=sum(p['variants'][v]['summary']['steps'] for p in pairs),
            short_rejections=sum(p['variants'][v]['windows']['5']['rejected'] for p in pairs),
            short_repeated_original_rejections=sum(p['variants'][v]['windows']['5']['repeated_original_rejection'] for p in pairs),
            medium_actual_retry_success=sum(p['variants'][v]['windows']['20']['successful_original_retry'] for p in pairs),
            medium_closed_loop=sum(p['variants'][v]['windows']['20']['closed_loop'] for p in pairs),
            main_final=[p['variants'][v]['final_main'] for p in pairs],chapter1=sum(p['variants'][v]['chapter1'] for p in pairs)) for v in ['Original','OracleRecovery']},
        **{k:cost[k] for k in ['new_requests','input_tokens','output_tokens','cost_usd']},
        total_model_cost_is_usage_priced_not_provider_invoice=True,analysis_model_calls=0,production_agent_changes=0))
    print(json.dumps(read(RESULTS/'summary.json')),flush=True)

if __name__=='__main__':main()
