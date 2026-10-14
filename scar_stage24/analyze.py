"""Common public-only diagnostics and unchanged official scoring, all runs."""
from collections import Counter
import csv
import statistics
import subprocess
import sys
from .common import *
from agents.agc.control import Control
from agents.agc.state import extract,satisfied_literal


def csvwrite(path,records):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)


def final_folder(game):
    repaired=(RESULTS/'repair_launch'/f'{game}.json').exists()
    folder=(RESULTS/'resumed' if repaired else RESULTS)/'runs'/f'{game}__AGC'
    assert (folder/'summary.json').exists(),('Still pending',game)
    return folder


def stats(game,method,phase='final'):
    folder=(final_folder(game) if phase=='final' else RESULTS/'runs'/f'{game}__AGC') if method=='AGC' else source(game)
    rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');summary=read(folder/'summary.json')
    assert summary['status'] in ['step_limit','native_done','agent_decision_exhausted']
    assert summary['status']!='step_limit' or len(rr)==300
    public=Control();initial=read(folder/'initial_public.json')['observation'];public.initialize(initial)
    seen_areas={extract(initial)['location']};last_goal=None;age=0;lengths=[];stale_before=False;counts=Counter();reason_counts=Counter()
    steps=[];events=[];milestones=[];episodes=[];run_wait=0;max_wait=0;chapter1=None;goals=[];requests=[];invalids=[]
    for i,r in enumerate(rr):
        n=r['step'];d=r['decision'];action=r['action']
        goal=d['attempts'][-1]['proposal']['goal_description'].strip() if method=='AGC' else d['controller_before']['target']
        if goal==last_goal:age+=1
        else:
            if age:lengths.append(age)
            age=1;last_goal=goal;goals.append(dict(step=n,goal=goal))
        a=extract(r['feedback']);p=public.progress(r['observation'],action,r['feedback'],n)
        stale=bool(goal and age>=12 and p['stagnant'])
        if stale and not stale_before:counts['stale_goal_episodes']+=1;episodes.append(dict(start=n,end=n,goal=goal))
        elif stale:episodes[-1]['end']=n
        stale_before=stale;counts['stale_goal_steps']+=stale
        literal=bool(goal and satisfied_literal(goal,extract(r['observation'])))
        counts['literal_completed_goal_retained_steps']+=literal
        counts['stagnation_steps']+=p['stagnant'];counts['new_state_discoveries']+=p['observation_new'];counts['informative_steps']+=p['informative']
        counts['new_area_count']+=a['location'] not in seen_areas;seen_areas.add(a['location'])
        counts['waits']+=action=='wait';run_wait=run_wait+1 if action=='wait' else 0;max_wait=max(max_wait,run_wait)
        counts['adjacent_repeats']+=bool(i and action==rr[i-1]['action'])
        counts['period2_return_actions']+=bool(i>=2 and action==rr[i-2]['action'])
        counts['public_failed_actions']+=a['failed'];counts['native_invalid']+=r['invalid_action']
        if (r.get('main_quest_progress') or {}).get('chapter',0)>=1 and chapter1 is None:chapter1=n
        if r['reward'].get('quest',0):milestones.append(dict(step=n,action=action,increment=r['reward']['quest'],score=r['scores']['quest'],feedback=r['feedback']))
        if method=='AGC':
            counts['reconsider_calls']+=d['reconsider_calls'];counts['bounded_soft_releases']+=d['bounded_soft_release']
            counts['reconsider_changed_action']+=bool(d['reconsider_calls'] and d['attempts'][0]['proposal'] and d['attempts'][0]['proposal'].get('action')!=action)
            for e in r['control_after']['events']:
                events.append(e)
                counts['goal_resets']+=e['kind']=='goal_reset'
                if e['kind']=='goal_status':
                    counts['invalid_triggers']+=e['after']=='INVALID';counts['suspicious_triggers']+=e['after']=='SUSPICIOUS'
                    if e['after']=='INVALID':invalids.append(e)
            for attempt in d['attempts']:
                if attempt['decision']=='RECONSIDER':reason_counts.update(attempt['reasons'])
        counts['controller_action_substitutions']+=d.get('intercepted',False) if method!='AGC' else d['controller_generated_action']
        steps.append(dict(game=game,method=method,step=n,action=action,goal=goal,goal_age=age,stale=stale,
            literal_completed_goal=literal,progress=p,quest_score=r['scores']['quest'],
            reference=str(folder.relative_to(ROOT)/'trajectory.jsonl.gz')+f':{i+1}'))
    if age:lengths.append(age)
    anomalies=[]
    for q in qq:
        issues=[]
        if q['status']!='ok':issues.append(q['status'])
        if q.get('parse_exception'):issues.append(q['parse_exception'])
        if q.get('raw_response'):
            ch=q['raw_response']['choices'][0]
            if ch['finish_reason']!='stop':issues.append('finish_reason:'+str(ch['finish_reason']))
        if issues:anomalies.append(dict(step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],issues=issues))
        requests.append(dict(game=game,method=method,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],status=q['status'],
            input_tokens=q.get('usage',{}).get('prompt_tokens'),output_tokens=q.get('usage',{}).get('completion_tokens'),cost_usd=q.get('cost_usd',0)))
    n=len(rr);score=summary['scores']
    record=dict(game=game,method=method,phase=phase,source_folder=str(folder.relative_to(ROOT)),status=summary['status'],actual_actions=n,unused_action_budget=300-n,
        main_quest=score['quest'],supplementary=sum(score.get(k,0) for k in ('side_quest','exploration','craft','unique_kill')),
        scores=score,first_chapter_complete=chapter1 is not None,first_chapter_step=chapter1,
        full_quest_complete=bool(((rr[-1].get('main_quest_progress') if rr else summary.get('main_quest_progress')) or {}).get('complete')),
        final_quest_state=rr[-1].get('main_quest_progress') if rr else summary.get('main_quest_progress'),
        counters=dict(counts),wait_ratio=counts['waits']/n if n else None,repeated_action_ratio=counts['adjacent_repeats']/max(n-1,1),
        mean_goal_duration=statistics.mean(lengths) if lengths else None,median_goal_duration=statistics.median(lengths) if lengths else None,
        goal_segment_count=len(lengths),short_goal_segments_le3=sum(x<=3 for x in lengths),longest_wait=max_wait,
        requests=len(qq),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),
        cost_usd=sum(q.get('cost_usd',0) for q in qq),max_input_tokens=max((q.get('usage',{}).get('prompt_tokens',0) for q in qq),default=0),
        anomalies=anomalies,stale_episodes=episodes,goal_changes=goals,goal_events=events,reconsider_reasons=dict(reason_counts),
        invalid_events=invalids,quest_milestones=milestones,initial_state_hash=summary['initial_state_hash'])
    if method=='AGC' and (folder/'decision_exhausted.json').exists():
        record['terminal_rejection']=read(folder/'decision_exhausted.json')
    if method=='AGC':
        record['repaired_continuation']=phase=='final' and (RESULTS/'repair_launch'/f'{game}.json').exists()
        if record['repaired_continuation']:record['repair_provenance']=read(RESULTS/'repair_launch'/f'{game}.json')
    gzwrite(RESULTS/'step_metrics'/f'{game}__{method}__{phase}.jsonl.gz',steps)
    return record,requests


def main():
    offline();check_freeze();assert read(RESULTS/'batch_completion.json')['complete']
    records=[];requests=[];first_pass=[]
    for game in GAMES:
        for method in ['Stage18-Fixed','AGC']:
            r,q=stats(game,method);records.append(r);requests+=q
        r,_=stats(game,'AGC','first_pass');first_pass.append(r)
    out=RESULTS/'official_scores';out.mkdir(exist_ok=True)
    args=[sys.executable,str(ENGINE/'challenge_eval.py')]
    for game in GAMES:args+=['--'+game,str(final_folder(game))]
    result=subprocess.run(args+['--json'],text=True,capture_output=True,check=True)
    official=json.loads(result.stdout);write(out/'AGC.json',official);(out/'AGC.stderr.txt').write_text(result.stderr)
    plain=subprocess.run(args,text=True,capture_output=True,check=True);(out/'AGC.txt').write_text(plain.stdout.rstrip()+'\n')
    write(out/'command.json',dict(command=args,script_sha256=sha(ENGINE/'challenge_eval.py'),engine_commit=ENGINE_COMMIT,unchanged=True))
    totals=[]
    for method in ['Stage18-Fixed','AGC']:
        rr=[r for r in records if r['method']==method]
        totals.append(dict(method=method,main_mean=statistics.mean(r['main_quest'] for r in rr),supplementary_mean=statistics.mean(r['supplementary'] for r in rr),
            chapters=sum(r['first_chapter_complete'] for r in rr),actions=sum(r['actual_actions'] for r in rr),requests=sum(r['requests'] for r in rr),
            cost_usd=sum(r['cost_usd'] for r in rr),input_tokens=sum(r['input_tokens'] for r in rr),output_tokens=sum(r['output_tokens'] for r in rr)))
    assert official['aggregate']['main_quest_mean']==totals[1]['main_mean'] and official['aggregate']['supplementary_total_mean']==totals[1]['supplementary_mean']
    for r in records:
        if r['method']=='AGC':assert official['games'][r['game']]['main_quest']==r['main_quest'] and official['games'][r['game']]['supplementary_total']==r['supplementary']
    a=next(r for r in records if r['game']=='mark' and r['method']=='AGC');b=next(r for r in records if r['game']=='mark' and r['method']=='Stage18-Fixed')
    checks=dict(mark_recovery=a['main_quest']>=3 and a['main_quest']>b['main_quest'],three_game_mean_improves=totals[1]['main_mean']>totals[0]['main_mean'],
        mark_wait_drop_at_least20pct=a['wait_ratio'] is not None and a['wait_ratio']<=b['wait_ratio']*.8,
        mark_stale_steps_drop=a['counters'].get('stale_goal_steps',0)<b['counters'].get('stale_goal_steps',0),
        mark_stagnation_steps_drop=a['counters'].get('stagnation_steps',0)<b['counters'].get('stagnation_steps',0))
    conclusion=dict(preregistered_checks=checks,all_checks_pass=all(checks.values()),single_sample_per_game=True,no_significance_claim=True,
        repaired_continuations=['remnant','mark'],first_pass_preserved=True,
        interpretation='One workflow comparison with two user-authorized parser-repaired continuations, not three homogeneous fresh v1.1 trials. Goal schema, controller, bounded failure memory and extra calls change together.')
    write(RESULTS/'metrics.json',records);write(RESULTS/'totals.json',totals);write(RESULTS/'conclusion.json',conclusion)
    write(RESULTS/'metrics_first_pass.json',first_pass)
    unique={q['request_id']:q for q in requests if q['method']=='AGC'}
    assert len(unique)==sum(r['requests'] for r in records if r['method']=='AGC')
    for game in GAMES:
        original=rows(RESULTS/'runs'/f'{game}__AGC'/'requests.jsonl.gz')
        final=rows(final_folder(game)/'requests.jsonl.gz')
        assert original==final[:len(original)],('Original requests changed',game)
    write(RESULTS/'cost_accounting.json',dict(unique_new_model_requests=len(unique),cost_usd=sum(q['cost_usd'] for q in unique.values()),
        first_pass_requests=sum(r['requests'] for r in first_pass),first_pass_cost_usd=sum(r['cost_usd'] for r in first_pass),
        new_requests_after_repair=len(unique)-sum(r['requests'] for r in first_pass),
        new_cost_after_repair_usd=sum(q['cost_usd'] for q in unique.values())-sum(r['cost_usd'] for r in first_pass),
        unused_paid_reconsider_responses=[dict(game=g,step=read(RESULTS/'repair_launch'/f'{g}.json')['resume_before_action'],ordinal=2) for g in ['remnant','mark']],
        baseline_reruns=0,offline_replay_model_calls=0,first_pass_and_continuation_not_double_counted=True))
    flat=[dict(game=r['game'],method=r['method'],status=r['status'],actions=r['actual_actions'],main_quest=r['main_quest'],supplementary=r['supplementary'],chapter1=r['first_chapter_complete'],
        wait_ratio=r['wait_ratio'],repeated_action_ratio=r['repeated_action_ratio'],stale_episodes=r['counters'].get('stale_goal_episodes',0),stale_steps=r['counters'].get('stale_goal_steps',0),
        goal_resets=r['counters'].get('goal_resets') if r['method']=='AGC' else None,invalid_triggers=r['counters'].get('invalid_triggers') if r['method']=='AGC' else None,
        new_states=r['counters'].get('new_state_discoveries',0),mean_goal_duration=r['mean_goal_duration'],requests=r['requests'],input_tokens=r['input_tokens'],output_tokens=r['output_tokens'],cost_usd=r['cost_usd']) for r in records]
    csvwrite(RESULTS/'three_game_results.csv',flat);csvwrite(RESULTS/'request_index.csv',requests)
    print(json.dumps(dict(totals=totals,checks=checks),ensure_ascii=False))

if __name__=='__main__':main()
