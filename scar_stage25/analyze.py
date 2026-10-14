"""Public-only shared metrics; native score fields used only offline."""
import csv
import math
import statistics
import subprocess
import sys
from collections import Counter
from agents.agc.control import Control as PublicMonitor
from agents.agc.state import extract,satisfied_literal
from .common import *

def formal_cases():return [(g,42) for g in GAMES]
def csvwrite(path,records):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
def old_folder(game,method):
    if method=='Stage18-Fixed':return ROOT/'results/stage22/runs'/f'{game}__Stage18-Fixed'
    return ROOT/'results/stage24'/('runs' if game=='metropolis' else 'resumed/runs')/f'{game}__AGC'

def stats(game,method):
    folder=RESULTS/'runs'/case_id(game,42) if method=='AGC-v2' else old_folder(game,method)
    rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json')
    assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
    assert s['steps']==len(rr) and (s['status']!='step_limit' or len(rr)==300)
    common=PublicMonitor();initial=read(folder/'initial_public.json')['observation'];common.initialize(initial)
    counts=Counter();reason_counts=Counter();areas={extract(initial)['location']};steps=[];segments=[];events=[];milestones=[]
    last_goal=None;age=0;stale_prev=False;run_failure=0;max_failure=0;run_noquest=0;noquest_runs=[];chapter=None;first_new=None
    for i,r in enumerate(rr):
        n=r['step'];d=r['decision'];action=r['action'];after=extract(r['feedback']);progress=common.progress(r['observation'],action,r['feedback'],n)
        goal=d['controller_before']['target'] if method=='Stage18-Fixed' else d['attempts'][-1]['proposal']['goal_description'].strip()
        if goal!=last_goal or not segments:
            last_goal=goal;age=1;segments.append(dict(start=n,end=n,goal=goal,actions=Counter(),quest_gain=0))
        else:age+=1
        seg=segments[-1];seg['end']=n;seg['actions'][action]+=1;seg['quest_gain']+=r['reward']['quest']
        stale=bool(goal and age>=12 and progress['stagnant']);counts['stale_goal_steps']+=stale;counts['stale_goal_episodes']+=stale and not stale_prev;stale_prev=stale
        counts['stagnation_steps']+=progress['stagnant'];counts['informative_steps']+=progress['informative'];counts['new_states']+=progress['observation_new']
        counts['zero_information_window8']+=len(common.history)==8 and sum(x['progress'] for x in common.history)==0
        counts['new_areas']+=after['location'] not in areas;areas.add(after['location'])
        counts['waits']+=action=='wait';counts['adjacent_repeats']+=bool(i and action==rr[i-1]['action']);counts['public_failures']+=after['failed'];counts['native_invalid']+=r['invalid_action']
        counts['literal_completed_goal_held']+=bool(goal and satisfied_literal(goal,extract(r['observation'])))
        same_failure=bool(after['failed'] and i and action==rr[i-1]['action'] and extract(rr[i-1]['feedback'])['failed'])
        run_failure=run_failure+1 if same_failure else 1 if after['failed'] else 0;max_failure=max(max_failure,run_failure);counts['consecutive_failed_pairs']+=same_failure
        if first_new is None and progress['observation_new']:first_new=n
        if chapter is None and (r.get('main_quest_progress') or {}).get('chapter',0)>=1:chapter=n
        if r['reward']['quest']:
            if run_noquest:noquest_runs.append(dict(start=n-run_noquest,end=n-1,length=run_noquest))
            run_noquest=0;milestones.append(dict(step=n,action=action,increment=r['reward']['quest'],total=r['scores']['quest'],feedback=after['feedback']))
        else:run_noquest+=1
        confidence=None
        if method!='Stage18-Fixed':
            confidence=r['control_after']['goal'].get('confidence') if r['control_after']['goal'] else None
            counts['reconsider_calls_executed']+=d['reconsider_calls'];counts['bounded_soft_releases']+=d['bounded_soft_release']
            counts['action_retry_calls_executed']+=d.get('action_retry_calls',0);counts['confidence_review_calls_executed']+=d.get('confidence_review_calls',0)
            for event in r['control_after']['events']:
                e=dict(event);e['action']=action;e['quest_before']=rr[i-1]['scores']['quest'] if i else 0;e['quest_after']=r['scores']['quest'];events.append(e)
                counts['goal_resets']+=e['kind']=='goal_reset'
                if e['kind']=='goal_status':counts['status_'+e['after']]+=1
            for attempt in d['attempts']:
                if attempt['decision']=='RECONSIDER':reason_counts.update(attempt['reasons'])
                if method=='AGC-v2':
                    counts['unverified_proposals']+=not attempt['evidence_verified']
                    counts['unverified_syntax_valid_proposals']+=not attempt['evidence_verified'] and not attempt['hard']
            if method=='AGC-v2':counts['goal_related_progress']+=r['transition']['goal_related_progress']
        counts['controller_action_substitutions']+=d['intercepted'] if method=='Stage18-Fixed' else d['controller_generated_action']
        steps.append(dict(game=game,method=method,step=n,action=action,goal=goal,goal_age=age,confidence=confidence,stale=stale,
            public_progress=progress,quest=r['scores']['quest'],public_failed=after['failed'],reference=str(folder.relative_to(ROOT)/'trajectory.jsonl.gz')+f':{i+1}'))
    if run_noquest:noquest_runs.append(dict(start=len(rr)-run_noquest+1,end=len(rr),length=run_noquest))
    for seg in segments:seg['length']=seg['end']-seg['start']+1;seg['action_counts']=seg.pop('actions').most_common()
    resets=[e for e in events if e['kind']=='goal_reset'];reset_windows=[]
    for i,e in enumerate(resets):
        source=e['new']['source'];t=e['step']+(.5 if source=='public' else -.5);start=math.ceil(t)
        following=resets[i+1] if i+1<len(resets) else None
        next_t=following['step']+(.5 if following['new']['source']=='public' else -.5) if following else math.inf
        end=min(len(rr),start+19,math.floor(next_t) if following else len(rr));window=[r for r in rr if start<=r['step']<=end]
        related=sum(r.get('transition',{}).get('goal_related_progress',False) for r in window)
        complete=sum(any(x['kind']=='goal_status' and x['after']=='COMPLETED' for x in r['control_after']['events']) for r in window)
        gain=sum(r['reward']['quest'] for r in window);censored=not following and len(rr)<start+19
        reset_windows.append(dict(index=i,step=e['step'],source=source,previous=e['previous'],new=e['new'],start=start,end=end,
            actual_actions=len(window),main_gain=gain,main_success=gain>0,goal_related_steps=related,literal_subgoal_completions=complete,
            right_censored=censored,twenty_actions_remain=len(rr)>=start+19,low_confidence=e['previous'].get('confidence',1)<.4,
            quest_before=e['quest_after'] if source=='public' else e['quest_before'],quest_at_window_end=rr[end-1]['scores']['quest'] if 1<=end<=len(rr) else e['quest_after']))
    terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
    if terminal:
        for attempt in terminal['decision']['attempts']:reason_counts.update(attempt['reasons'])
    anomalies=[]
    for q in qq:
        issues=[];raw=q.get('raw_response',{});parsed=q.get('parsed_json')
        if q['status']!='ok':issues.append(q['status'])
        if q.get('parse_exception'):issues.append(q['parse_exception'])
        if raw and raw['choices'][0]['finish_reason']!='stop':issues.append('finish_reason:'+raw['choices'][0]['finish_reason'])
        required=['action','reasoning']+(['goal_description','goal_evidence'] if method!='Stage18-Fixed' else [])
        if q['status']=='ok' and not q.get('parse_exception'):
            issues += ['missing_'+k for k in required if not isinstance(parsed,dict) or not isinstance(parsed.get(k),str)]
        if issues:anomalies.append(dict(step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],issues=issues))
    n=len(rr);score=s['scores'];counts['action_retry_calls_terminal']=(terminal or {}).get('decision',{}).get('action_retry_calls',0)
    good=[x for x in reset_windows if not x['right_censored']];low=[x for x in reset_windows if x['low_confidence']]
    result=dict(game=game,method=method,seed=42,status=s['status'],actual_actions=n,unused_budget=300-n,main=score['quest'],
        supplementary=sum(score[k] for k in ['side_quest','exploration','craft','unique_kill']),scores=score,first_chapter_step=chapter,first_chapter_complete=chapter is not None,
        full_quest_complete=bool((rr[-1].get('main_quest_progress') or {}).get('complete')) if rr else False,
        final_quest_state=rr[-1].get('main_quest_progress') if rr else s.get('main_quest_progress'),
        counters=dict(counts),wait_ratio=counts['waits']/n if n else None,repeated_action_ratio=counts['adjacent_repeats']/max(n-1,1),
        first_new_state_step=first_new,mean_goal_duration=statistics.mean(x['length'] for x in segments) if segments else None,
        goal_segments=segments,goal_events=events,reset_windows=reset_windows,reset_main_success_rate=sum(x['main_success'] for x in reset_windows)/len(reset_windows) if reset_windows else None,
        reset_main_success_rate_uncensored=sum(x['main_success'] for x in good)/len(good) if good else None,
        low_confidence_reset_success_rate=sum(x['main_success'] for x in low)/len(low) if low else None,
        longest_consecutive_failed_actions=max_failure,no_quest_runs=noquest_runs,
        long_no_quest_ratio=sum(x['length'] for x in noquest_runs if x['length']>=8)/max(n,1),long_no_information_ratio=counts['zero_information_window8']/max(n,1),
        quest_milestones=milestones,rejection_reasons=dict(reason_counts),terminal_rejection=terminal,anomalies=anomalies,
        requests=len(qq),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),
        max_input_tokens=max((q.get('usage',{}).get('prompt_tokens',0) for q in qq),default=0),cost_usd=sum(q.get('cost_usd',0) for q in qq),
        initial_state_hash=s['initial_state_hash'],source_folder=str(folder.relative_to(ROOT)))
    gzwrite(RESULTS/'step_metrics'/f'{game}__{method}.jsonl.gz',steps)
    return result,qq

def main():
    offline();check_freeze();records=[];requests=[]
    for game in GAMES:
        for method in ['Stage18-Fixed','AGC','AGC-v2']:
            r,q=stats(game,method);records.append(r)
            for x in q:requests.append(dict(game=game,method=method,step=x['step'],ordinal=x['ordinal'],request_id=x['request_id'],status=x['status'],cost_usd=x.get('cost_usd',0),input_tokens=x.get('usage',{}).get('prompt_tokens',0),output_tokens=x.get('usage',{}).get('completion_tokens',0)))
    agc=[r for r in records if r['method']=='AGC-v2'];old=[r for r in records if r['method']=='AGC'];v={r['game']:r for r in agc}
    reliability=lambda r:not (r['terminal_rejection'] and any('action' in reason or 'consecutive_identical' in reason for a in r['terminal_rejection']['decision']['attempts'] for reason in a['reasons']))
    checks=dict(mark_preserved=v['mark']['main']>=11 and v['mark']['first_chapter_complete'],
        remnant_recovered=v['remnant']['main']>1 and reliability(v['remnant']),
        metropolis_recovered=v['metropolis']['main']>=7 and v['metropolis']['first_chapter_complete'])
    partial=any(v[r['game']]['main']>=r['main']+1 for r in old) or (reliability(v['remnant']) and v['remnant']['main']>=1)
    classification='SUCCESSFUL_WORKFLOW_IMPROVEMENT' if all(checks.values()) else 'PARTIAL_IMPROVEMENT' if partial else 'NO_FURTHER_GAIN'
    write(RESULTS/'metrics.json',records);write(RESULTS/'conclusion.json',dict(classification=classification,checks=checks,remnant_action_reliability_no_termination=reliability(v['remnant']),
        one_sample_per_game=True,user_scope_reduction_applied=True,causal_module_attribution=False))
    flat=[dict(game=r['game'],method=r['method'],main=r['main'],supplementary=r['supplementary'],actions=r['actual_actions'],status=r['status'],chapter1=r['first_chapter_complete'],
        resets=r['counters'].get('goal_resets') if r['method']!='Stage18-Fixed' else None,wait_ratio=r['wait_ratio'],repeat_ratio=r['repeated_action_ratio'],
        native_invalid=r['counters']['native_invalid'],requests=r['requests'],cost_usd=r['cost_usd']) for r in records]
    csvwrite(RESULTS/'comparison.csv',flat);csvwrite(RESULTS/'request_index.csv',requests)
    args=[sys.executable,str(ENGINE/'challenge_eval.py')]
    for game in GAMES:args+=['--'+game,str(RESULTS/'runs'/case_id(game,42))]
    result=subprocess.run(args+['--json'],text=True,capture_output=True,check=True);official=json.loads(result.stdout)
    for game in GAMES:assert official['games'][game]['main_quest']==v[game]['main'] and official['games'][game]['supplementary_total']==v[game]['supplementary']
    write(RESULTS/'official_scores.json',official);write(RESULTS/'official_scoring_command.json',dict(args=args,script_sha256=sha(ENGINE/'challenge_eval.py'),engine_commit=ENGINE_COMMIT))
    print(json.dumps(dict(classification=classification,checks=checks,formal=[(r['game'],r['main'],r['actual_actions']) for r in agc])))

if __name__=='__main__':main()
