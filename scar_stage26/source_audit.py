"""Exhaustive public-feedback failure labels; denominators remain explicit."""
from collections import Counter
from agents.agc.state import extract
from agents.agc.control import Control as Monitor
from .common import *

def subtype(text):
    low=text.lower()
    for phrase,label in [
        ('not enough space in hand','hand_capacity'),('not enough space in small','container_capacity'),
        ('door is locked','locked_exit'),('no lockpick tool','missing_lockpick_tool'),
        ('no writing tools','missing_writing_tool'),('missing necessary workbench','missing_workbench'),
        ('blocked the way out','combat_blocks_exit'),('not equippable','not_equippable'),
        ('not found in hand','object_not_held_or_visible'),('not have sufficient','insufficient_ingredients')]:
        if phrase in low:return label
    return 'other_public_failure'

def main():
    offline();rr=rows(SOURCE/'trajectory.jsonl.gz');qq=rows(SOURCE/'requests.jsonl.gz')
    requests={(q['step'],q['ordinal']):(i+1,q) for i,q in enumerate(qq)}
    monitor=Monitor();monitor.initialize(read(SOURCE/'initial_public.json')['observation'])
    records=[];rejected=[];failed=[];cycles=[];previous_failures={};counts=Counter();last_main=0;before_states=[];failure_runs=[];run=[]
    for i,r in enumerate(rr):
        n=r['step'];b,a=extract(r['observation']),extract(r['feedback']);progress=monitor.progress(r['observation'],r['action'],r['feedback'],n)
        proposals=[]
        for p in r['decision']['attempts']:
            line,q=requests[n,p['ordinal']]
            entry=dict(ordinal=p['ordinal'],proposal=p['proposal'],executed=p['executed'],hard=p['hard'],reasons=p['reasons'],
                request_line=line,request_id=q['request_id'],confidence_review=p['goal_review'])
            proposals.append(entry)
            if p['hard']:
                label='A' if any(reason in ['missing_action','action_not_in_public_action_syntax'] for reason in p['reasons']) else 'C' if any('consecutive_identical' in reason for reason in p['reasons']) else 'interface_metadata'
                rejected.append(dict(step=n,category=label,**entry));counts['rejected_'+label]+=1
        labels=[];same_context_previous=[];adjacent=False;sub=None
        if a['failed']:
            labels.append('B');counts['B_actual_failed']+=1;sub=subtype(a['feedback'])
            key=(r['action'],b['context']);same_context_previous=previous_failures.get(key,[]).copy()
            adjacent=bool(i and extract(rr[i-1]['feedback'])['failed'] and rr[i-1]['action']==r['action'] and extract(rr[i-1]['observation'])['context']==b['context'])
            if adjacent:labels.append('C');counts['C_consecutive_same_context']+=1
            if same_context_previous:counts['C_recurrent_same_context']+=1
            previous_failures.setdefault(key,[]).append(n)
            failed.append(dict(step=n,action=r['action'],subtype=sub,feedback=a['feedback'],previous_same_context=same_context_previous,adjacent_repeat=adjacent))
            run.append(n)
        else:
            if run:failure_runs.append(run);run=[]
        if r['reward']['quest']:last_main=n
        strict_d=not a['failed'] and len(monitor.history)==8 and not any(x['progress'] for x in monitor.history)
        if strict_d:labels.append('D');counts['D_zero_information_window8']+=1
        cycle=None
        for old in reversed(before_states[-8:]):
            segment=rr[old['step']-1:n]
            if a['context']==old['context'] and len(segment)>=2 and len({s['action'] for s in segment})>=2 and not any(s['reward']['quest'] or extract(s['feedback'])['failed'] for s in segment):
                cycle=dict(start=old['step'],end=n,actions=[s['action'] for s in segment],context=a['context']);cycles.append(cycle);break
        before_states.append(dict(step=n,context=b['context']))
        accepted_no_main=not a['failed'] and not r['reward']['quest']
        counts['accepted_without_main_reward']+=accepted_no_main
        record=dict(step=n,observation=r['observation'],current_goal_before=r['decision']['control_before']['goal'],
            selected_goal=r['decision']['attempts'][-1]['proposal']['goal_description'],action_proposal=proposals,
            executed_action=r['action'],environment_response=a['feedback'],next_observation=r['feedback'],
            progress_change=dict(main_delta=r['reward']['quest'],main_total=r['scores']['quest'],public=progress,goal_related=r['transition']['goal_related_progress']),
            categories=labels,failure_subtype=sub,previous_same_action_context_failures=same_context_previous,
            accepted_without_main_reward=accepted_no_main,short_public_state_cycle=cycle,
            source_trajectory=f'results/stage25/runs/remnant__s42__AGC-v2/trajectory.jsonl.gz:{n}')
        records.append(record)
    if run:failure_runs.append(run)
    tail=rr[last_main:]
    summary=dict(actions=len(rr),model_proposals=len(qq),counts=dict(counts),rejected_proposals=rejected,failed_actions=failed,
        subtype_counts=dict(Counter(x['subtype'] for x in failed)),failure_runs=failure_runs,
        long_no_information_steps=[r['step'] for r in records if 'D' in r['categories']],short_public_state_cycles=cycles,
        last_main_progress_step=last_main,tail_steps=len(tail),tail_failed_actions=sum(extract(r['feedback'])['failed'] for r in tail),
        tail_accepted_without_main=sum(not extract(r['feedback'])['failed'] and not r['reward']['quest'] for r in tail),
        tail_actions_by_verb=dict(Counter(r['action'].split()[0] for r in tail)),
        stage25_final_main=rr[-1]['scores']['quest'],new_model_calls=0,hidden_rules_used=False,
        caveat='A uses proposal denominator; B/C use 300 actual actions and C overlaps B. D is a strict no-information proxy, not all low-reward actions. Cycles use public state only, never strict complete-state equivalence.')
    gzwrite(RESULTS/'action_failure_replay.jsonl.gz',records);write(RESULTS/'source_failure_statistics.json',summary)
    print(json.dumps({k:summary[k] for k in ['actions','model_proposals','counts','subtype_counts','last_main_progress_step','tail_steps','tail_failed_actions','tail_accepted_without_main']}))

if __name__=='__main__':main()
