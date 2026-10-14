"""All preregistered checkpoints, explicit reuse/correlation, no tuning."""
import csv
import re
from collections import Counter
from .common import *
from scar_stage22b.analyze import FACTS,spans


def csvwrite(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)


def public(obs):
    from scar_v3.state import PublicState
    s=PublicState.observe(obs)
    return dict(location=s.location,hands=s.hands,equipment=s.equipment,ground=s.ground,npcs=s.npcs)


def novelty(p):
    from scar.io import digest
    return digest(dict(location=p['location'],hands=p['hands'],equipment=p['equipment'],
        ground_names=sorted(p['ground'] or {}),npc_names=sorted(p['npcs'] or [])))


def disclosed(obs):
    # Evaluation-only mark facts; never imported by reset.py or a live agent.
    return {k for k,regex in FACTS.items() if re.search(regex,obs['text'])}


def metrics(start,variant,original):
    path=RESULTS/'runs'/case_id(start)/variant
    summary=read(path/'summary.json');rr=rows(path/'trajectory.jsonl.gz')
    assert summary['status'] in ('step_limit','native_done','reused_original_suffix'),summary
    assert rr and (rr[-1]['step']==300 or rr[-1]['done'])
    before_score=original[start-2]['scores']['quest']
    prior=[read(SOURCE/'initial_public.json')['observation']]+[r['feedback'] for r in original[:start-1]]
    visited={public(o)['location'] for o in prior};seen={novelty(public(o)) for o in prior}
    known=set().union(*(disclosed(o) for o in prior))
    owned=set().union(*[set(public(o)['hands'] or {})|set(public(o)['equipment'] or {}) for o in prior])
    events=[];changes=[];new_areas=[];new_states=0;effective=0;progress_proxy=0;reasons=Counter();blockers=Counter()
    active_steps=0;authority_stale=0;first_info=None;first_refresh=None;first_progress=None;chapter1=None
    actual_resets=summary.get('reset_events',[]);reset_time=actual_resets[0]['step'] if actual_resets else None
    for row in rr:
        n=row['step'];d=row.get('decision') or original[n-1]['decision'];p=public(row['feedback'])
        current_state=novelty(p);state_new=current_state not in seen;seen.add(current_state);new_states+=state_new
        area_new=p['location'] not in visited;visited.add(p['location'])
        if area_new:new_areas.append(dict(step=n,location=p['location']))
        obs_facts=disclosed(row['feedback']);new_facts=obs_facts-known;known|=obs_facts
        holding=set(p['hands'] or {})|set(p['equipment'] or {});new_owned=holding-owned;owned|=holding
        text=row['feedback']['text'];rejected=bool(row['invalid_action'] or re.search(r'\b(?:Cannot|Invalid action)\b|not following the tutorial',text))
        accepted=not rejected and row['action']!='wait';effective+=accepted
        gain=row['reward'].get('quest',0)
        craft=row['reward'].get('craft',0)>0
        progress=bool(accepted and (gain or craft or new_facts or area_new or new_owned or row['reward'].get('unique_kill',0)))
        progress_proxy+=progress
        active=bool(row.get('reset',{}).get('active'));active_steps+=active
        stale=(n>=32 and row.get('goal',d['controller_before']['target'])=='enter hall')
        authority_stale+=bool(stale and not active)
        reason=d.get('stage18',{}).get('reason','syntax_fallback');reasons[reason]+=1
        checks=d.get('stage18',{}).get('assessments',{}).get('llm',{})
        if active:
            for c in checks.get('conditions',[]):
                if c['status']=='REJECT':blockers[c['kind']]+=1
        if gain:
            events.append(dict(step=n,action=row['action'],gain=gain,score=row['scores']['quest'],feedback=row['feedback']))
            if first_progress is None:first_progress=n
        if (row.get('main_quest_progress') or {}).get('chapter',0)>=1 and chapter1 is None:chapter1=n
        if reset_time is not None and n>=reset_time:
            if first_info is None and new_facts:first_info=n
            if first_refresh is None and 'remy says: Craft an oak rod.' in text:first_refresh=n
        changes.append(dict(case=case_id(start),variant=variant,step=n,action=row['action'],proposal=d['proposed_action'],
            reset_active=active,reset_triggered=bool(row.get('reset',{}).get('triggered')),
            registered_goal=d['controller_before']['target'],stale_goal_authority=bool(stale and not active),
            accepted_nonwait=accepted,observable_progress_proxy=progress,new_state_signature=state_new,
            newly_visited_area=p['location'] if area_new else None,new_public_fact_ids=sorted(new_facts),
            new_owned_object_names=sorted(new_owned),quest_gain=gain,quest_score=row['scores']['quest'],
            llm_assessment=checks.get('status'),arbitration_reason=reason,
            rejected_condition_kinds=[c['kind'] for c in checks.get('conditions',[]) if c['status']=='REJECT'],
            raw_trace=f'results/stage23/runs/{case_id(start)}/{variant}/trajectory.jsonl.gz:{n-start+1}'))
    actions=[r['action'] for r in rr];waits=[x for x in spans(actions) if x['value']=='wait']
    for x in waits:x['start']+=start-1;x['end']+=start-1
    all_goals=[r['decision']['controller_before']['target'] for r in original[:start-1]]+[r.get('goal',r.get('decision',{}).get('controller_before',{}).get('target')) for r in rr]
    old_goals=[s['length'] for s in spans(all_goals) if s['value']=='enter hall']
    release_changes=[r['step'] for r in changes if r['arbitration_reason']=='stage23_released_stale_goal_default']
    prior_wait=0
    if reset_time is not None:
        combined=[(r['step'],r['action']) for r in original[:start-1]]+[(r['step'],r['action']) for r in rr if r['step']<reset_time]
        for n,action in combined[::-1]:
            if action!='wait':break
            prior_wait+=1
    requests=rows(path/'requests.jsonl.gz') if variant!='Stage18-Origin' else []
    anomalies=[dict(step=r['step'],source=r['sample_origin'],request_id=r['request_id']) for r in requests
        if not isinstance(r.get('parsed_json'),dict) or not all(k in r['parsed_json'] for k in ('action','reasoning'))]
    record=dict(case=case_id(start),variant=variant,start=start,remaining_budget=301-start,actual_actions=len(rr),
        final_main_reward=rr[-1]['scores']['quest'],main_reward_gain=rr[-1]['scores']['quest']-before_score,
        chapter1_completed=chapter1 is not None,chapter1_step=chapter1,full_main_quest_complete=bool((rr[-1].get('main_quest_progress') or {}).get('complete')),
        final_quest_state=rr[-1]['main_quest_progress'],first_stale_goal_in_parent=32,
        first_reset=reset_time,reset_events=actual_resets,first_effective_release=release_changes[0] if release_changes else None,
        reset_first_action=next((r['action'] for r in rr if r['step']==reset_time),None),
        reset_first_proposal=next((r['proposal'] for r in changes if r['step']==reset_time),None),
        waits_immediately_before_reset=prior_wait,first_new_fact_after_reset=first_info,first_oak_goal_refresh_after_reset=first_refresh,
        first_quest_gain=first_progress,new_state_discoveries=new_states,new_areas=new_areas,
        new_area_count=len(new_areas),accepted_nonwait=effective,accepted_nonwait_ratio=effective/len(rr),
        observable_progress_actions=progress_proxy,observable_progress_ratio=progress_proxy/len(rr),
        wait_count=actions.count('wait'),wait_ratio=actions.count('wait')/len(rr),longest_wait=max((x['length'] for x in waits),default=0),
        wait_runs=waits,reset_active_decisions=active_steps,stale_authority_decisions=authority_stale,
        longest_old_goal_text_run_including_shared_prefix=max(old_goals,default=0),
        arbitration_releases=len(release_changes),remaining_overrides=sum(r['proposal']!=r['action'] for r in changes),
        post_reset_rejected_conditions=dict(blockers),arbitration_reasons=dict(reasons),quest_events=events,
        new_model_requests=summary['new_model_requests'],new_model_cost_usd=summary['new_model_cost_usd'],
        source_reuses=summary.get('source_reuses',len(rr) if variant=='Stage18-Origin' else 0),
        paired_reuses=summary.get('paired_reuses',0),input_tokens_new=summary.get('input_tokens_new',0),
        output_tokens_new=summary.get('output_tokens_new',0),response_anomalies=anomalies,
        earliest_irrecoverable_step=None,irrecoverable_scope='No proof of full-task irrecoverability; final failure alone is insufficient.')
    gzwrite(RESULTS/'step_metrics'/f'{case_id(start)}__{variant}.jsonl.gz',changes)
    return record


def main():
    from scar_stage22b.common import forbid_network
    forbid_network();check_freeze()
    assert read(RESULTS/'batch_completion.json')['complete'],'Do not classify unfinished runs'
    original=rows(SOURCE/'trajectory.jsonl.gz')
    records=[metrics(n,v,original) for n in CASES for v in VARIANTS]
    aggregated=[]
    for v in VARIANTS:
        rr=[r for r in records if r['variant']==v]
        chapter=sum(r['chapter1_completed'] for r in rr);progressed=sum(r['main_reward_gain']>=1 for r in rr)
        aggregated.append(dict(variant=v,checkpoint_count=10,independent_parent_episodes=1,
            chapter1_completed=chapter,main_progress_checkpoints=progressed,
            gain_at_least_3=sum(r['main_reward_gain']>=3 for r in rr),
            total_main_reward=sum(r['final_main_reward'] for r in rr),mean_main_reward=sum(r['final_main_reward'] for r in rr)/10,
            meaningful_recovery=progressed>=5 or chapter>=1,
            total_actions=sum(r['actual_actions'] for r in rr),wait_count=sum(r['wait_count'] for r in rr),
            accepted_nonwait=sum(r['accepted_nonwait'] for r in rr),observable_progress_actions=sum(r['observable_progress_actions'] for r in rr),
            new_area_count_sum=sum(r['new_area_count'] for r in rr),new_state_count_sum=sum(r['new_state_discoveries'] for r in rr),
            stale_authority_decisions=sum(r['stale_authority_decisions'] for r in rr),
            new_model_requests=sum(r['new_model_requests'] for r in rr),new_model_cost_usd=sum(r['new_model_cost_usd'] for r in rr),
            input_tokens_new=sum(r['input_tokens_new'] for r in rr),output_tokens_new=sum(r['output_tokens_new'] for r in rr),
            source_reuses=sum(r['source_reuses'] for r in rr),paired_reuses=sum(r['paired_reuses'] for r in rr)))
    b,c=aggregated[1:]
    verdict='ENGINEERING_FIX_SUPPORTED' if b['meaningful_recovery'] else 'CONTROLLER_LIMIT_CONFIRMED' if c['meaningful_recovery'] else 'DESIGN_LIMIT_CONFIRMED'
    write(RESULTS/'metrics.json',records);write(RESULTS/'aggregate.json',aggregated)
    write(RESULTS/'conclusion.json',dict(verdict=verdict,rule=read(RESULTS/'protocol.json')['meaningful_recovery_rule'],
        independent_parent_episodes=1,no_statistical_significance_claim=True,
        scope='Arbitration-only reset with original stale prompt state and all original rejection guards retained.',
        earliest_irrecoverable_proven=False,all_30_slots_accounted=True))
    fields=['case','variant','start','remaining_budget','actual_actions','chapter1_completed','chapter1_step','final_main_reward','main_reward_gain','first_reset','first_effective_release','reset_first_action','waits_immediately_before_reset','first_new_fact_after_reset','first_oak_goal_refresh_after_reset','first_quest_gain','new_state_discoveries','new_area_count','accepted_nonwait_ratio','observable_progress_ratio','wait_count','wait_ratio','longest_wait','stale_authority_decisions','new_model_requests','input_tokens_new','output_tokens_new','new_model_cost_usd']
    csvwrite(RESULTS/'paired30.csv',[{k:r[k] for k in fields} for r in records])
    write(RESULTS/'costs.json',dict(new_model_requests=sum(a['new_model_requests'] for a in aggregated),
        input_tokens=sum(a['input_tokens_new'] for a in aggregated),output_tokens=sum(a['output_tokens_new'] for a in aggregated),
        usage_priced_usd=sum(a['new_model_cost_usd'] for a in aggregated),price_source=read(RESULTS/'protocol.json')['price_verification'],
        source_reuses=sum(a['source_reuses'] for a in aggregated),paired_reuses=sum(a['paired_reuses'] for a in aggregated),
        note='Original and matched paired responses do not incur new charges; logical token totals must not be billed twice.'))
    print(json.dumps(dict(verdict=verdict,aggregate=aggregated),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
