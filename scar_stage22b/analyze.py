"""Complete public/agent audit and explicit, non-causal failure denominators."""
from collections import Counter
import copy
import csv
import json
import re
from .common import *
from .native import differences

FACTS={
 'tutorial_finished':r'Tutorial Finished\.',
 'guide_offer':r'Talk to me if you need a reminder',
 'oak_rod_objective':r'remy says: Craft an oak rod\.',
 'oak_rod_recipe_relation':r'oak_rod \((?:made of oak_log|0\.5 oak_log)\)',
 'oak_rod_exact_recipe':r'oak_rod \(0\.5 oak_log\)',
 'oak_rod_station_rejection':r'Cannot craft oak_rod\. Missing necessary workbench',
 'copper_sword_objective':r'remy says: Craft a copper sword',
 'librarian_objective':r'remy says: Enter the area where librarian_rowan',
 'kindness_disclosure':r'Write this exactly:\s+kindness',
 'stalls_objective':r'Head to Night Market, stalls',
 'torch_objective':r'Craft a torch using',
 'chapter_1_complete':r'=== Chapter 1 Complete ===',
 'chapter_2_intro':r'Chapter 2: The Forest Receipt',
}

def string_paths(x,needle,path=''):
    if isinstance(x,dict):
        for k,v in x.items():yield from string_paths(v,needle,path+'/'+str(k))
    elif isinstance(x,list):
        for k,v in enumerate(x):yield from string_paths(v,needle,path+'/'+str(k))
    elif isinstance(x,str) and needle in x:yield path

def public(obs,tracker):
    from scar_v3.state import PublicState
    from dataclasses import asdict
    p=PublicState.observe(obs)
    value={k:copy.deepcopy(getattr(p,k)) for k in ('location','hands','equipment','ground','npcs','neighbors')}
    value['inventory_id']=tracker.inventory
    value['last_observed_container_contents']=copy.deepcopy(tracker.containers)
    for field,pattern in [('health',r'My health is at ([\d.]+)'),('experience',r'My experience is at ([\d.]+)')]:
        m=re.search(pattern,obs['text']);value[field]=float(m[1]) if m else None
    value['scope']='Public observations plus last disclosed container accounting; null means not observed. This is an offline tracker, not a baseline memory.'
    return value

def spans(values):
    result=[]
    for step,value in enumerate(values,1):
        if not result or result[-1]['value']!=value:result.append(dict(start=step,end=step,length=1,value=value))
        else:result[-1]['end']=step;result[-1]['length']+=1
    return result

def periods(actions):
    # All exact minimal-period candidates, followed by maximal coverage filter.
    candidates=[]
    for start in range(len(actions)):
        for period in range(1,5):
            pattern=actions[start:start+period]
            if len(pattern)<period:continue
            if any(period%d==0 and pattern==pattern[:d]*(period//d) for d in range(1,period)):continue
            end=start+period
            while actions[end:end+period]==pattern and end+period<=len(actions):end+=period
            repeats=(end-start)//period
            if repeats>=2:candidates.append(dict(start=start+1,end=end,period=period,repetitions=repeats,pattern=pattern))
    return [r for r in candidates if not any(q['period']==r['period'] and q['start']<=r['start'] and q['end']>=r['end'] and q!=r for q in candidates)]

def actual_objective(progress,tutorial_done,definitions):
    if not tutorial_done:return dict(kind='tutorial',source='public Required action')
    if not progress:return None
    c,s=progress.get('chapter',0),progress.get('stage',0)
    if c>=len(definitions):return dict(complete=bool(progress.get('complete')))
    stages=definitions[c]['stages']
    return dict(chapter=c,stage=s,stage_id=stages[s]['id'] if s<len(stages) else None,
                objective_template=stages[s]['objective'] if s<len(stages) else None,
                source='Official quest definition used post hoc only; never agent input or witness action selection')

def main():
    forbid_network();integrity=check_freeze()
    from scar_stage16.knowledge import PublicTable
    from games.generated.mark.rules.step_rules.main_quest import MainQuestStepRule
    definitions=MainQuestStepRule.QUEST_CONFIG['chapters']
    metrics=[];information=[];knowledge_rows=[];all_gains=[]
    for method in METHODS:
        rr=rows(RESULTS/'agent_audit'/f'{method}.jsonl.gz')
        native_receipt=read(RESULTS/'native'/f'{method}.receipt.json')
        native={r['step']:r for r in rows(RESULTS/'native'/f'{method}.jsonl.gz')}
        tracker=PublicTable();initial=read(source(method)/'initial_public.json')['observation'];tracker.observe(initial)
        disclosures={k:[] for k in FACTS};disclosures.update(oak_log_visible_library=[],workbench_visible_hall=[])
        initial_goal=re.search(r'Required action:\s*`([^`]+)`',initial['text'])
        tutorial_end=None;public_goal=(dict(text=initial_goal[1],disclosed_at=0,kind='explicit_action') if initial_goal else None)
        last_progress=None;audits=[];info_timeline=[]
        for r in rr:
            n=r['step'];before=public(r['observation'],tracker)
            old_goal=public_goal
            tracker.observe(r['feedback'],r['selected_action']);after=public(r['feedback'],tracker)
            text=r['feedback']['text']
            m=re.search(r'Required action:\s*`([^`]+)`',text)
            if m:public_goal=dict(text=m[1],disclosed_at=n,kind='explicit_action')
            m=re.search(r'remy says: (.*?)(?:\n\n|\Z)',text,re.S)
            if m and not m[1].startswith('"You seem stuck'):
                public_goal=dict(text=m[1].strip(),disclosed_at=n,kind='NPC_natural_language_instruction')
            if 'Tutorial Finished.' in text:tutorial_end=n;public_goal=dict(text='Tutorial finished; main quest announced. Ask the public guide for its current stage.',disclosed_at=n,kind='quest_transition')
            for key,pattern in FACTS.items():
                if re.search(pattern,text):disclosures[key].append(n)
            if (after['location'] or '').endswith(', library') and (after['ground'] or {}).get('oak_log',0):disclosures['oak_log_visible_library'].append(n)
            if (after['location'] or '').endswith(', hall') and (after['ground'] or {}).get('workbench',0):disclosures['workbench_visible_hall'].append(n)
            messages='\n'.join(q['content'] for q in r['model_messages'])
            needle='remy says: Craft an oak rod.'
            internal_paths=list(string_paths(r['internal_before'],needle))
            observed_earlier=any(x<n for x in disclosures['oak_rod_objective'])
            missing_after_disclosure=observed_earlier and not internal_paths and needle not in r['observation']['text']
            if method=='Stage18-Fixed':
                c=r['internal_before']['controller'];d=r['decision'];goal=c['target']
                summary_records=d['fact_summary']['records'];in_summary=needle in json.dumps(summary_records,ensure_ascii=False)
                known_relation=bool(c['table']['recipes'].get('oak_rod',{}).get('ingredients'))
                goal_wrong=tutorial_end is not None and n>tutorial_end and goal=='enter hall'
                condition_misrepresented=goal_wrong and (before['location'] or '').endswith(', hall') and not d['execution_context']['goal']['complete']
                categories=[]
                if missing_after_disclosure:categories.append('A_explicit_goal_text_not_retained')
                if goal_wrong and observed_earlier and (internal_paths or needle in r['observation']['text']):categories.append('B_goal_evidence_retained_but_goal_channel_stale')
                knowledge_rows.append(dict(step=n,controller_target=goal,goal_completed_in_tutorial_but_still_target=goal_wrong,
                    current_location_meets_enter_target_but_possession_query_false=condition_misrepresented,
                    oak_rod_relation_structured=known_relation,oak_rod_goal_registered='oak_rod' in goal,
                    explicit_objective_disclosed_earlier=observed_earlier,internal_literal_evidence_paths=internal_paths,
                    objective_in_model_context=needle in messages,objective_in_structured_summary=in_summary,
                    selected_action=r['selected_action'],proposal=d['proposed_action'],classes=categories,
                    exploration_spent=c['exploration_spent'],fifo=list(c['queue']),
                    summary_available=len(d['fact_summary']['available_record_ids']),summary_selected=len(summary_records),
                    summary_characters=d['fact_summary']['characters']))
            else:goal=None;categories=[]
            if r['reward'].get('quest',0):
                all_gains.append(dict(method=method,step=n,action=r['selected_action'],increment=r['reward']['quest'],total=r['scores']['quest'],feedback=r['feedback']['text']))
            audits.append(dict(step=n,method=method,evidence_id=r['evidence_id'],observation=r['observation'],
                public_objective_before=old_goal,public_objective_after=public_goal,
                public_objective_scope='Latest explicit public instruction/transition, not an inferred baseline intention; may become stale after quest progress. See actual_quest fields for post-hoc stage annotation.',
                actual_quest_before=actual_objective(last_progress,tutorial_end is not None and n>tutorial_end,definitions),
                actual_quest_after=actual_objective(r['main_quest_progress'],tutorial_end is not None,definitions),
                agent_internal_goal=goal,agent_state_index=f'results/stage22b/agent_audit/{method}.jsonl.gz:{n}',
                history_actions=r['history_actions'],selected_action=r['selected_action'],feedback=r['feedback'],
                public_before=before,public_after=after,public_world_delta=differences(before,after),
                native_world_delta=native.get(n,{}).get('world_delta'),native_frame_index=f'results/stage22b/native/{method}.jsonl.gz:{n}' if n in native else None,
                hidden_world_available=n in native,hidden_world_note='Exact matched native frame' if n in native else 'Unavailable beyond first replay mismatch; do not infer full hidden state from observation',
                reward=r['reward'],scores=r['scores'],model_reasoning=(r.get('model_parsed') or {}).get('reasoning') if isinstance(r.get('model_parsed'),dict) else None,
                model_request_id=r['model_request_id'],model_usage=r['model_usage']))
            last_progress=r['main_quest_progress']
            info_timeline.append(dict(step=n,explicit_goal_literal_in_saved_state_paths=internal_paths,
                explicit_goal_literal_in_model_context=needle in messages,previously_disclosed=observed_earlier))
        gzwrite(RESULTS/'step_audit'/f'{method}.jsonl.gz',audits)
        actions=[r['selected_action'] for r in rr];aruns=spans(actions);loops=periods(actions)
        waits=[x for x in aruns if x['value']=='wait'];long_waits=[x for x in waits if x['length']>=5]
        areas=Counter(a['public_after']['location'] for a in audits);non_tutorial=[a for a in areas if not a.startswith('Tutorial,')]
        metric=dict(method=method,steps=300,main_quest=rr[-1]['scores']['quest'],tutorial_finished_step=tutorial_end,
            main_quest_complete=rr[-1]['main_quest_progress'].get('complete',False),
            wait_actions=actions.count('wait'),wait_blocks=len(waits),long_wait_blocks_5=len(long_waits),
            long_wait_actions_5=sum(w['length'] for w in long_waits),longest_wait=max((w['length'] for w in waits),default=0),
            same_action_blocks_2=sum(x['length']>=2 for x in aruns),same_action_repeat_steps=sum(x['length']-1 for x in aruns),
            exact_periodic_loops=loops,action_runs=aruns,wait_runs=waits,
            visited_non_tutorial_areas=non_tutorial,area_action_counts=dict(areas),native_replay=native_receipt,
            explicit_goal_field_exists=method=='Stage18-Fixed',input_max=max(r['model_usage']['prompt_tokens'] for r in rr),
            input_tokens=sum(r['model_usage']['prompt_tokens'] for r in rr),output_tokens=sum(r['model_usage']['completion_tokens'] for r in rr),
            successful_crafts=sum('successfully crafted' in r['feedback']['text'] for r in rr),
            hand_full_decision_steps=sum(sum((a['public_before']['hands'] or {}).values())>=2 for a in audits),
            quest_gains=[r for r in all_gains if r['method']==method])
        if method=='Stage18-Fixed':
            goal_runs=spans([r['internal_before']['controller']['target'] for r in rr])
            metric.update(goal_runs=goal_runs,longest_same_goal=max(x['length'] for x in goal_runs),
                stale_goal_decision_steps=sum(r['goal_completed_in_tutorial_but_still_target'] for r in knowledge_rows),
                completed_location_condition_reported_incomplete=sum(r['current_location_meets_enter_target_but_possession_query_false'] for r in knowledge_rows),
                raw_llm_wait=sum(r['decision']['proposed_action']=='wait' for r in rr),
                controller_created_wait=sum(r['selected_action']=='wait' and r['decision']['proposed_action']!='wait' for r in rr),
                overrides=sum(r['decision']['intercepted'] for r in rr),
                empty_fifo_steps=sum(not r['fifo'] for r in knowledge_rows),max_exploration_spent=max(r['exploration_spent'] for r in knowledge_rows),
                class_counts=dict(Counter(k for r in knowledge_rows for k in r['classes'])))
        metrics.append(metric)
        for key,seen in disclosures.items():
            pattern=FACTS.get(key)
            context=[r['step'] for r in rr if pattern and re.search(pattern,'\n'.join(m['content'] for m in r['model_messages']))]
            information.append(dict(method=method,fact=key,first_public_step=min(seen) if seen else None,
                public_steps=seen,model_context_steps=context,definition=pattern or 'Object visibly on the ground in named observed room',
                C_not_obtained=not bool(seen),context_note='Public statement literal/regex, not paraphrase inference; current observation enters the following decision'))
        gzwrite(RESULTS/'information_timeline'/f'{method}.jsonl.gz',info_timeline)
    write(RESULTS/'metrics.json',metrics);write(RESULTS/'information_matrix.json',information)
    write(RESULTS/'quest_gain_events.json',all_gains);gzwrite(RESULTS/'stage18_information_use.jsonl.gz',knowledge_rows)
    scalar=['method','steps','main_quest','tutorial_finished_step','wait_actions','wait_blocks','long_wait_blocks_5','long_wait_actions_5','longest_wait','same_action_repeat_steps','hand_full_decision_steps','input_max']
    with (RESULTS/'metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=scalar,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(metrics)
    write(RESULTS/'audit_receipt.json',dict(passed=True,agent_decisions=900,public_step_audits=900,
        native_steps=sum(m['native_replay']['verified_actions'] for m in metrics),api_calls=0,**integrity,
        classification='A/B are operational explicit-instruction retention/update measurements; C is fact-level; not causal shares'))
    print(json.dumps([{k:m.get(k) for k in scalar+['stale_goal_decision_steps','completed_location_condition_reported_incomplete','class_counts','overrides','controller_created_wait','empty_fifo_steps','max_exploration_spent']} for m in metrics]),flush=True)


if __name__=='__main__':main()
