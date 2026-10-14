"""Paired descriptive metrics, initialized from the shared public prefix."""
import csv
import re
from collections import Counter
from agents.agc.state import extract
from agents.agc.control import Control as Monitor
from .common import *
from .source_audit import subtype

def hp(obs):
    m=re.search(r'My health is at (-?\d+(?:\.\d+)?)',obs['text']);return float(m[1]) if m else None
def stage_key(progress):
    p=progress or {};return f"{p.get('chapter',0)}:{p.get('stage',0)}:{int(bool(p.get('complete')))}"
def csvwrite(path,records):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)

def metric(start,variant,prefix,rr,summary):
    monitor=Monitor();monitor.initialize(read(SOURCE/'initial_public.json')['observation'])
    areas={extract(read(SOURCE/'initial_public.json')['observation'])['location']}
    known_stages={stage_key(r['main_quest_progress']) for r in prefix};records=[];all_rows={r['step']:r for r in prefix+rr};before_states=[]
    for r in prefix:
        monitor.progress(r['observation'],r['action'],r['feedback'],r['step']);areas.add(extract(r['feedback'])['location'])
    counts=Counter();seen_stages=set(known_stages);new_stages=[];milestones=[];goals=[]
    for i,r in enumerate(rr):
        n=r['step'];a=extract(r['feedback']);b=extract(r['observation']);p=monitor.progress(r['observation'],r['action'],r['feedback'],n)
        counts['public_failed']+=a['failed'];counts['informative']+=p['informative'];counts['new_states']+=p['observation_new']
        counts['new_areas']+=a['location'] not in areas;areas.add(a['location'])
        counts['wait']+=r['action']=='wait';counts['native_invalid']+=r['invalid_action'];counts['adjacent_repeats']+=bool(i and r['action']==rr[i-1]['action'])
        counts['no_information_window8']+=len(monitor.history)==8 and not any(x['progress'] for x in monitor.history)
        cycle=None
        for previous in reversed(before_states[-8:]):
            segment=[all_rows[k] for k in range(previous['step'],n+1)]
            if a['context']==previous['context'] and len(segment)>=2 and len({s['action'] for s in segment})>=2 and not any(s['reward']['quest'] or extract(s['feedback'])['failed'] for s in segment):
                cycle=dict(start=previous['step'],end=n,actions=[s['action'] for s in segment]);counts['public_cycle_ends']+=1;break
        before_states.append(dict(step=n,context=b['context']))
        key=stage_key(r['main_quest_progress'])
        if key not in seen_stages:
            new_stages.append(dict(step=n,key=key,main=r['scores']['quest']));seen_stages.add(key)
        if r['reward']['quest']:
            milestones.append(dict(step=n,action=r['action'],delta=r['reward']['quest'],total=r['scores']['quest'],feedback=a['feedback']))
        goal=r['decision']['attempts'][-1]['proposal']['goal_description']
        if goals and goals[-1]['goal']==goal:goals[-1]['end']=n
        else:goals.append(dict(start=n,end=n,goal=goal))
        counts['hard_rejected_proposals']+=sum(p['hard'] for p in r['decision']['attempts'])
        counts['goal_review_calls']+=r['decision']['confidence_review_calls'];counts['action_retry_calls']+=r['decision']['action_retry_calls']
        record=dict(case=case_id(start),variant=variant,step=n,relative_step=n-start+1,action=r['action'],goal=goal,
            confidence=r['control_after']['goal']['confidence'],main=r['scores']['quest'],main_delta=r['reward']['quest'],public_failed=a['failed'],
            failure_subtype=subtype(a['feedback']) if a['failed'] else None,public_progress=p,cycle=cycle,
            hp_before=hp(r['observation']),hp_after=hp(r['feedback']),deaths_delta=r['reward']['death'],
            main_state=key,chapter1=(r['main_quest_progress'] or {}).get('chapter',0)>=1,
            reference=f'results/stage25/runs/remnant__s42__AGC-v2/trajectory.jsonl.gz:{n}' if variant=='Original' else f'results/stage26/runs/{case_id(start)}/Oracle/trajectory.jsonl.gz:{i+1}')
        records.append(record)
    def window(lo,hi):
        data=[x for x in records if lo<=x['relative_step']<=hi]
        return dict(relative_actions=[lo,hi],actual_actions=len(data),censored=len(data)<hi-lo+1,
            main_gain=sum(x['main_delta'] for x in data),new_states=sum(x['public_progress']['observation_new'] for x in data),
            informative=sum(x['public_progress']['informative'] for x in data),failures=sum(x['public_failed'] for x in data),
            cycle_ends=sum(x['cycle'] is not None for x in data),waits=sum(x['action']=='wait' for x in data))
    before_main=prefix[-1]['scores']['quest'] if prefix else 0
    first_chapter=next((r['step'] for r in records if r['chapter1']),None)
    data=dict(case=case_id(start),variant=variant,start=start,actual_actions=len(rr),remaining_budget=301-start,
        last_step=rr[-1]['step'] if rr else start-1,status=summary['status'],scores=summary['scores'],
        main=summary['scores']['quest'],main_before=before_main,main_gain=summary['scores']['quest']-before_main,
        supplementary=sum(summary['scores'][k] for k in ['unique_kill','craft','exploration','side_quest']),
        chapter1=first_chapter is not None,first_chapter_step=first_chapter,full_quest=bool(summary['main_quest_progress'].get('complete')),
        final_quest_state=summary['main_quest_progress'],new_main_state_count=len(new_stages),new_main_states=new_stages,
        counters=dict(counts),first_action=records[0],windows=dict(first5=window(1,5),first20=window(1,20),following5=window(2,6),following20=window(2,21)),
        quest_milestones=milestones,goal_segments=goals,
        last_main_progress=milestones[-1]['step'] if milestones else None,
        tail_without_main_progress=(rr[-1]['step']-(milestones[-1]['step'] if milestones else start-1)) if rr else 0,
        public_failure_types=dict(Counter(r['failure_subtype'] for r in records if r['public_failed'])),
        new_requests=summary.get('new_requests',0),cost_usd=summary.get('cost_usd',0),input_tokens=summary.get('input_tokens',0),output_tokens=summary.get('output_tokens',0))
    gzwrite(RESULTS/'step_metrics'/f'{case_id(start)}__{variant}.jsonl.gz',records)
    return data,records

def main():
    offline();check_freeze();source=rows(SOURCE/'trajectory.jsonl.gz');metrics=[];pairs=[];evidence=[]
    for n in CASES:
        pair={};prefix=source[:n-1]
        for variant in ['Original','Oracle']:
            folder=RESULTS/'runs'/case_id(n)/variant;s=read(folder/'summary.json')
            assert s['status'] in ['reused_original_suffix','step_limit','native_done','agent_decision_exhausted']
            rr=source[n-1:] if variant=='Original' else rows(folder/'trajectory.jsonl.gz')
            m,steps=metric(n,variant,prefix,rr,s);metrics.append(m);pair[variant]=m
            if variant=='Oracle':
                qq=rows(folder/'requests.jsonl.gz');qindex={}
                for i,q in enumerate(qq):qindex.setdefault(q['step'],[]).append(dict(line=i+1,ordinal=q['ordinal'],request_id=q['request_id'],status=q['status'],parse_exception=q.get('parse_exception')))
                for i,r in enumerate(rr):evidence.append(dict(case=case_id(n),step=r['step'],trajectory_line=i+1,trajectory=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),
                    requests=str((folder/'requests.jsonl.gz').relative_to(ROOT)),request_index=qindex.get(r['step'],[]),reused_source_step=r['step'] if i==0 else None,
                    action=r['action'],proposed_action=r['proposed_action'],oracle_replacement=r['oracle_replacement'],main_delta=r['reward']['quest'],state_hash=r['state_hash']))
                selected=set([n]+list(range(n+1,min(n+5,300)+1)))|{r['step'] for r in rr if r['reward']['quest']}
                selected.update(r['step'] for r in rr if any(p['hard'] for p in r['decision']['attempts']))
                write(RESULTS/'case_evidence'/f'{case_id(n)}.json',[dict(step=r['step'],action=r['action'],proposal=r['proposed_action'],observation=r['observation'],feedback=r['feedback'],
                    reward=r['reward'],goal=r['control_after']['goal'],attempts=[dict(proposal=a['proposal'],reasons=a['reasons'],executed=a['executed']) for a in r['decision']['attempts']]) for r in rr if r['step'] in selected])
        o,v=pair['Original'],pair['Oracle']
        pairs.append(dict(case=case_id(n),start=n,subtype=CASES[n]['subtype'],original_action=o['first_action']['action'],oracle_action=v['first_action']['action'],
            original_main=o['main'],oracle_main=v['main'],main_difference=v['main']-o['main'],original_chapter1=o['chapter1'],oracle_chapter1=v['chapter1'],
            original_actions=o['actual_actions'],oracle_actions=v['actual_actions'],oracle_status=v['status'],original_new_main_states=o['new_main_state_count'],oracle_new_main_states=v['new_main_state_count'],
            original_first5_information=o['windows']['first5']['informative'],oracle_first5_information=v['windows']['first5']['informative'],
            original_first20_gain=o['windows']['first20']['main_gain'],oracle_first20_gain=v['windows']['first20']['main_gain'],
            original_following20_failures=o['windows']['following20']['failures'],oracle_following20_failures=v['windows']['following20']['failures'],
            original_cycles=o['counters'].get('public_cycle_ends',0),oracle_cycles=v['counters'].get('public_cycle_ends',0),new_requests=v['new_requests'],cost_usd=v['cost_usd']))
    improved=sum(p['main_difference']>0 for p in pairs);chapters=sum(p['oracle_chapter1'] for p in pairs)
    classification='ACTION_RELIABILITY_SUPPORTED' if improved>=5 and chapters>=3 else 'MIXED_OR_LOCAL_RECOVERY' if improved or chapters else 'NO_CLEAR_LONG_TERM_RECOVERY'
    write(RESULTS/'paired_metrics.json',metrics);write(RESULTS/'paired_comparison.json',pairs);csvwrite(RESULTS/'paired_comparison.csv',pairs)
    gzwrite(RESULTS/'evidence_index.jsonl.gz',evidence)
    write(RESULTS/'conclusion.json',dict(classification=classification,paired_checkpoints=10,independent_parent_episodes=1,main_improved=improved,
        main_tied=sum(p['main_difference']==0 for p in pairs),main_worse=sum(p['main_difference']<0 for p in pairs),oracle_chapter1=chapters,original_chapter1=0,
        oracle_full_quest=sum(m['full_quest'] for m in metrics if m['variant']=='Oracle'),new_analysis_model_calls=0,significance_claim=False))
    by={(m['start'],m['variant']):m for m in metrics};short_aggregate={}
    for field in ['new_states','informative','failures','cycle_ends','main_gain']:
        delta=[by[n,'Oracle']['windows']['following20'][field]-by[n,'Original']['windows']['following20'][field] for n in CASES]
        short_aggregate[field]=dict(oracle_minus_original=delta,positive=sum(x>0 for x in delta),zero=sum(x==0 for x in delta),negative=sum(x<0 for x in delta))
    write(RESULTS/'short_term_summary.json',dict(following20_excludes_intervention=short_aggregate,
        immediate_new_information_only_oracle=sum(by[n,'Oracle']['first_action']['public_progress']['informative'] and not by[n,'Original']['first_action']['public_progress']['informative'] for n in CASES),
        warning='Ten dependent checkpoints; the guaranteed accepted correction itself is excluded from following20 metrics.'))
    # Exact post-failure behavior of all original failures, including unselected ones.
    recovery=[]
    for r in source:
        if not extract(r['feedback'])['failed']:continue
        n=r['step'];after=source[n:min(n+20,300)]
        accepted=next((x for x in after if not extract(x['feedback'])['failed']),None)
        same_success=next((x for x in after if x['action']==r['action'] and not extract(x['feedback'])['failed']),None)
        recovery.append(dict(step=n,action=r['action'],next_action=after[0]['action'] if after else None,
            first_accepted_after=accepted['step'] if accepted else None,first_accepted_delay=accepted['step']-n if accepted else None,
            same_action_success_within20=same_success['step'] if same_success else None,main_gain_next20=sum(x['reward']['quest'] for x in after),
            prior_same_context_failures=next(x['previous_same_context'] for x in read(RESULTS/'source_failure_statistics.json')['failed_actions'] if x['step']==n)))
    write(RESULTS/'original_failure_recovery.json',recovery)
    print(json.dumps(dict(classification=classification,improved=improved,chapters=chapters,oracle_actions=len(evidence))))

if __name__=='__main__':main()
