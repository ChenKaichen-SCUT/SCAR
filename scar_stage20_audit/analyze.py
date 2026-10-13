"""Retrospective attribution with public evidence and explicitly limited claims."""
from .common import *
deny_network()
from collections import Counter,defaultdict
from scar_v3.state import parse_action
from scar.io import digest


def main():
    plans=read_gzip(RESULTS/'planning_states.jsonl.gz');stalled=read_gzip(RESULTS/'terminal_states.jsonl.gz')
    branches=read_gzip(RESULTS/'counterfactual_results.jsonl.gz');branch_plan=load(RESULTS/'counterfactual_plan.json')
    tasks={t['task_id']:t for t in load(SOURCE/'tasks.json')}
    traces={tid:read_gzip(folder(tid)/'trajectory.jsonl.gz') for tid in tasks}
    terms={tid:load(folder(tid)/'terminal_decision.json')['decision']['controller'] for tid in tasks}
    def after_state(tid,step):
        rows=traces[tid]
        return rows[step]['decision']['decision']['controller_before'] if step<len(rows) else terms[tid]
    def ref(tid,step):return dict(file=str((folder(tid)/'trajectory.jsonl.gz').relative_to(ROOT)),line=step)
    rejections=[]
    for r in plans:
        if r['old_evidence_reason']!='evidence_unrelated_to_execution_entry':continue
        rejections.append(dict(id=r['id'],task_id=r['task_id'],decision_step=r['decision_step'],ordinal=r['ordinal'],
            proposal=r['plan']['proposal'],trigger=r['plan']['trigger'],original_acceptance=r['plan']['acceptance'],
            original_evidence_ids=r['plan']['proposal']['evidence_ids'],original_records=r['plan']['acceptance']['evidence_refs'],
            shadow=r['shadow'],state_index=r['id'],request_id=r['request_id'],source=r['source'],source_line=r['source_line'],
            conclusion_scope='citation/type/public access gate only, not certification that full original intent should execute'))
    branch_analysis=[]
    for b in branches:
        spec=next(p for p in branch_plan if p['id']==b['id'])
        state=spec.get('public_controller') or next(s['controller'] for s in stalled if s['task_id']==b['task_id'])
        c=controller(state);item=c.blocker20.get('item');known_before=c._known_path(item) if item else None
        relevant=c.needed();new_related=sorted(set(b['knowledge_delta']['new_relations'])&relevant)
        clone=copy.deepcopy(c);clone.observe(b['before_observation'],b['action'],b['after_observation'])
        known_after=clone._known_path(item) if item else None
        kstep=copy.deepcopy(clone).known_step(parse_action(clone.target).target,clone.amount)
        actual=traces[b['task_id']][b['at_completed_step']] if b['at_completed_step']<len(traces[b['task_id']]) else None
        branch_analysis.append(dict(id=b['id'],task_id=b['task_id'],at_completed_step=b['at_completed_step'],action=b['action'],
            native_action_accepted=b['native_action_accepted'],player_hp_loss=b['player_hp_loss'],new_relations=b['knowledge_delta']['new_relations'],
            prior_public_dependency_related_new_relations=new_related,blocker_item=item,public_path_before=known_before,public_path_after=known_after,
            subsequent_frozen_known_step=kstep,subsequent_step_not_executed=True,
            factual_next_action=actual['action'] if actual else 'method_stalled/no_action',
            factual_next_new_relations=actual['knowledge_delta']['new_relations'] if actual else [],
            factual_same_before_hash=actual['physical_before']['state_hash']==b['initial_state_hash'] if actual else b['initial_state_hash']==next(s['physical_state_hash'] for s in stalled if s['task_id']==b['task_id']),
            result_source='results/stage20_audit/counterfactual_results.jsonl.gz#'+b['id']))
    stall_audit=[]
    for s in stalled:
        tid=s['task_id'];c=controller(s['controller']);needed=c.needed();rows=traces[tid]
        meaningful=[r for r in s['candidates'] if r['eligible_public_trial'] and r['possible_new_knowledge'] and r['action'].startswith(('inspect ','enter '))]
        nonquota=[r for r in meaningful if not r['fallback_candidate_generated'] or r['entry_attempts_same_context']>0 or r['same_context_actual_visits']>=2]
        relevant=[]
        for row in rows:
            names=sorted(set(row['knowledge_delta']['new_relations'])&needed)
            stations=[v for v in row['mechanism_outcome']['new_preconditions'] if v.split(':')[0] in needed]
            if names or stations:relevant.append(dict(step=row['step'],action=row['action'],new_related_relations=names,new_related_area_requirements=stations,
                feedback=row['mechanism_outcome']['feedback'],exploration_spent_after=row['mechanism_outcome']['exploration_spent'],source=ref(tid,row['step'])))
        direct_D=[p['id'] for p in plans if p['task_id']==tid and p['plan']['acceptance']['reason']=='not_a_current_dependency_or_blocker' and p['shadow']['category']=='II']
        eligible_rejections=[r['id'] for r in rejections if r['task_id']==tid and r['shadow']['category'] in ('I','II')]
        native=[b for b in branch_analysis if b['task_id']==tid and b['at_completed_step']==len(rows) and b['native_action_accepted']]
        # B includes all hard controller filtering, with quota-only witnesses
        # explicitly separated. C is the narrower evidence+quota intersection.
        labels=dict(A=False if meaningful else 'UNKNOWN',B=bool(meaningful and native),
            C=bool(c.exploration_spent>=18 and relevant and meaningful and native),D=bool(direct_D))
        stall_audit.append(dict(task_id=tid,target=s['task']['target_item'],steps=len(rows),remaining_actions=100-len(rows),
            categories=labels,category_scope='B includes fixed-quota filtering; nonquota candidate omissions reported separately. C requires prior publicly relevant new evidence. D requires actual dependency-membership rejection, not ID matching alone.',
            nonquota_omission_witnesses=[r['action'] for r in nonquota],exploration_spent=c.exploration_spent,planning_calls=c.plan_calls20,
            max_same_context_requests=max(c.context_counts20.values(),default=0),can_request_at_terminal=c.can_request(),
            current_blocker=c.blocker20,final_goal=c.target,public_dependencies=sorted(needed),
            public_recipe_gaps=sorted(n for n in needed if not c.table.recipes.get(n,{}).get('ingredients') and c.ownership(n)['lower_bound']<1),
            quantity_unknown=sorted(n for n in needed if c.table.recipes.get(n,{}).get('ingredients') and c.table.recipes[n].get('quantities') is None),
            public_materials={n:c.ownership(n) for n in sorted(needed)},public_area_requirements=c.preconditions20,
            public_map=dict(location=c.table.state['location'],places=c.table.places,links=c.table.links,guards=c.table.guards),
            FIFO=dict(queue=c.queue,queue_needs=c.queue_needs,visits=c.visits,actual_visits=c.actual_visits),
            planning_history=[dict(id=p['id'],step=p['decision_step'],proposal=p['plan']['proposal'],acceptance=p['plan']['acceptance']) for p in plans if p['task_id']==tid],
            last_15_actions=[dict(step=r['step'],action=r['action'],feedback=r['mechanism_outcome']['feedback'],
                source=r['decision']['decision']['stage20']['source'],exploration_spent=r['mechanism_outcome']['exploration_spent'],raw=ref(tid,r['step'])) for r in rows[-15:]],
            relevant_evidence=relevant,public_candidate_count=len(meaningful),candidates=s['candidates'],
            positive_native_witnesses=[r['id'] for r in native],native_goal_related_knowledge_witnesses=[r['id'] for r in native if r['prior_public_dependency_related_new_relations']],
            direct_D_witnesses=direct_D,ID_gate_hypothesis_witnesses=eligible_rejections,
            absence_of_remaining_entry=False if meaningful else 'UNKNOWN',final_task_recoverable='UNKNOWN',
            terminal_state_source='results/stage20_audit/terminal_states.jsonl.gz#'+tid))
    accepted=load(SOURCE/'subgoal_outcomes.json');intent_rows=[]
    for end in accepted:
        if end['type'] not in ('LOCATE_PRECONDITION','ACQUIRE_MATERIAL'):continue
        tid=end['task_id'];rows=traces[tid];id=end['id'];plan=next(p for p in plans if p['task_id']==tid and p['plan']['acceptance'].get('intent_id')==id)
        lifecycle=[e for e in terms[tid]['lifecycle20'] if e['id']==id]
        interruption=next((e for e in lifecycle if e['event'] in ('blocked','execution_blocked','expired','cancelled')),None)
        parent=plan['plan']['trigger'].get('parent') or tasks[tid]['target_item']
        timeline=[]
        for action in end['actions']:
            step=action['step'];row=rows[step-1];before=controller(row['decision']['decision']['controller_before']);after=controller(after_state(tid,step))
            p=parse_action(row['action']);path=after._known_path(end['target']);owned=after.ownership(end['target'])
            target_gain=p.target==end['target'] and p.verb in ('store','pick up','take out') and owned['lower_bound']>before.ownership(end['target'])['lower_bound']
            req=plan['plan']['trigger'].get('requires_ground',False)
            satisfied=((after.table.state.get('ground') or {}).get(end['target'],0)>0) if req else owned['lower_bound']>=end.get('amount',1)
            timeline.append(dict(step=step,action=row['action'],feedback=row['mechanism_outcome']['feedback'],
                source=ref(tid,step),new_relations=row['knowledge_delta']['new_relations'],public_path=path,
                target_owned=owned,actual_target_transfer=target_gain,required_possession_or_area_satisfied=satisfied,
                exploration_after=after.exploration_spent,risk16_after=after.risk16,
                health_before=row['physical_before']['health'],health_after=row['physical_after']['health'],
                actual_production=row['metrics']['actual_production']))
        end_step=end.get('end_step',rows[-1]['step'])
        parent_attempts=[dict(step=r['step'],action=r['action'],success=bool(r['metrics']['actual_production']),source=ref(tid,r['step']))
            for r in rows if r['step']>end['start_step'] and parse_action(r['action']).verb=='craft' and parse_action(r['action']).target==parent]
        resume=next((r for r in rows if r['step']>end_step and r['decision']['decision']['stage20']['source'] in ('known_FIFO_execution','public_dependency_execution','P3_finish')),None)
        failing=None
        if end['status']!='completed':
            event=interruption or next((e for e in reversed(lifecycle) if e['event'] in ('blocked','expired','cancelled')),None)
            when=event['step'] if event else end_step;state=controller(after_state(tid,when));reason=event.get('reason') if event else end['termination_reason']
            has_path=state._known_path(end['target'])
            category=('budget_limit' if reason in ('fixed_intent_action_limit','inherited_exploration_budget_exhausted') else
                      'public_risk_interrupt' if reason=='immediate_public_health_or_combat_risk' else
                      'native_locked_route_feedback' if event and event['event']=='execution_blocked' and 'door is locked' in event.get('feedback','') else
                      'public_path_missing_and_bounded_entry_exhausted' if not has_path and reason in ('no_current_admissible_entry_or_dependency','replaced_by_new_verified_subgoal') else
                      'UNKNOWN_or_executor_boundary')
            event_after_action=bool(event and when>0 and event in rows[when-1]['mechanism_outcome']['lifecycle'])
            active=next((i for i in (state.intent20,state.suspended20) if i and i['id']==id),None)
            failing=dict(first_observable_node=when,event=event,reason=reason,category=category,target_public_path=has_path,
                timing='after_native_action' if event_after_action else 'choosing_next_action',
                action_selection_step=when if event_after_action else when+1,
                blocker_snapshot=state.blocker20,exploration_spent=state.exploration_spent,remaining_intent_actions=end['remaining_actions'],
                remaining_actions_at_first_node=active['remaining_actions'] if active else None,
                public_path_alone_does_not_prove_quantity_or_all_station_conditions=True,
                endpoint_failures_not_backdated_before_first_observable_interruption=True)
        intent_rows.append(dict(id=f'{tid}:{id}',task_id=tid,intent_id=id,type=end['type'],target=end['target'],entry=end['entry'],
            planning_state_id=plan['id'],proposal=plan['plan']['proposal'],trigger=plan['plan']['trigger'],parent=parent,
            start_step=end['start_step'],end_step=end_step,status=end['status'],termination_reason=end['termination_reason'],steps=end['steps'],
            lifecycle=lifecycle,timeline=timeline,first_failure_node=failing,
            stages=dict(first_inspect=next((r['step'] for r in timeline if r['action'].startswith('inspect ')),None),
                first_public_path=next((r['step'] for r in timeline if r['public_path']),None),
                first_actual_target_transfer=next((r['step'] for r in timeline if r['actual_target_transfer']),None),
                first_requirement_satisfied=next((r['step'] for r in timeline if r['required_possession_or_area_satisfied']),None),
                first_parent_craft_success=next((r['step'] for r in parent_attempts if r['success']),None)),
            parent_attempts=parent_attempts,original_goal_execution_resumed=resume['step'] if resume else None,
            first_resumed_action=resume['action'] if resume else None,attribution='temporal association; not a causal benefit estimate'))
    crafts=[dict(id=p['id'],task_id=p['task_id'],proposal=p['plan']['proposal'],trigger=p['plan']['trigger'],
        acceptance=p['plan']['acceptance'],shadow=p['shadow'],state_index=p['id']) for p in plans if p['plan']['proposal']['type']=='CRAFT_PRECONDITION']
    summary=dict(stall_counts={k:sum(s['categories'][k] is True for s in stall_audit) for k in ('A','B','C','D')},
        stalled_tasks=11,nonquota_omission_tasks=sum(bool(s['nonquota_omission_witnesses']) for s in stall_audit),
        quota_exhausted_tasks=sum(s['exploration_spent']==18 for s in stall_audit),
        rejection_counts={k:sum(r['shadow']['category']==k for r in rejections) for k in ('I','II','III','IV')},
        intents={kind:dict(accepted=sum(i['type']==kind for i in intent_rows),
            completed=sum(i['type']==kind and i['status']=='completed' for i in intent_rows),
            terminal_reasons=dict(Counter(i['termination_reason'] for i in intent_rows if i['type']==kind)),
            first_failure_categories=dict(Counter(i['first_failure_node']['category'] for i in intent_rows if i['type']==kind and i['first_failure_node'])),
            stages={stage:sum(i['type']==kind and i['stages'][stage] is not None for i in intent_rows) for stage in ('first_inspect','first_public_path','first_actual_target_transfer','first_requirement_satisfied','first_parent_craft_success')})
            for kind in ('LOCATE_PRECONDITION','ACQUIRE_MATERIAL')},
        craft_proposals=len(crafts),craft_accepted=sum(c['acceptance']['accepted'] for c in crafts),
        resumed_intents=sum(any(e['event']=='resumed' for e in r['lifecycle']) for r in intent_rows),
        resume_events=sum(e['event']=='resumed' for r in intent_rows for e in r['lifecycle']),
        P3_interruptions=sum(r['termination_reason']=='P3_public_final_task_progress' for r in intent_rows),
        completed_LOCATE_with_later_parent_production=sum(r['type']=='LOCATE_PRECONDITION' and r['status']=='completed' and r['stages']['first_parent_craft_success'] is not None for r in intent_rows),
        native_branches=len(branches),native_accepted=sum(r['native_action_accepted'] for r in branches),
        branches_with_recipe_gain=sum(bool(r['knowledge_delta']['new_relations']) for r in branches),
        branches_with_player_hp_loss=sum(r['player_hp_loss']>0 for r in branches),
        actual_model_calls=0,tokens=0,cost_usd=0,research_decision='PARTIAL',
        scope='offline local mechanism diagnosis; no completed task outcome inferred from one-step branches')
    for name,data in (('rejection_audit',rejections),('stall_audit',stall_audit),('intent_audit',intent_rows),('craft_proposal_audit',crafts),('branch_analysis',branch_analysis),('summary',summary)):
        write(RESULTS/(name+'.json'),data)
    assert not NETWORK_ATTEMPTS
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
