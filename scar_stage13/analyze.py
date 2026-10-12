"""Post-freeze diagnostics. Native labels here never flow back into policy.py."""
import collections
import gzip
import json
from pathlib import Path
from scar.io import atomic_json, digest
from scar_stage12.analyze import raw_entry
from scar_stage12.public import controller, confirmed, primitive_candidate
from scar_stage13.native import verify_freeze
from scar_stage13.policy import decide, intent
from scar_stage13.prepare import public_history
from scar_v3.state import parse_action

OUT=Path('results/stage13'); OLD=Path('results/stage12/diagnostic')

def load(p):return json.loads(Path(p).read_text())
def merged_counts(rows,key):
    total=collections.Counter()
    for r in rows:total.update(r[key])
    return dict(total)


def brief(s,b):
    ctrl=controller(s['public_controller'],s['observation']);initial_nodes=confirmed(ctrl)
    seen=set(ctrl.table.inspected);previous_public=set();repeated=0;empty_craft=0;execs=[]
    for row in b['trace']:
        p=parse_action(row['action']);fresh=set(row['new_public_recipes'])-previous_public
        repeated+=p.verb=='inspect' and p.target in seen and not fresh
        if p.verb=='inspect' and 'I inspected ' in row['feedback']:seen.add(p.target)
        empty_craft+=p.verb=='craft' and not row['action_production'] and not fresh
        if p.target in initial_nodes and not row['rejected'] and (row['action_production'] or p.verb in {'pick up','take out','store'}):execs.append(row['action'])
        previous_public=set(row['new_public_recipes'])
    first=next((r['index'] for r in b['trace'] if r['new_key_recipes']),None)
    return {k:b[k] for k in ['actions','new_key_recipes','useful','one_step_useful','rejections','unrelated_craft',
          'unrelated_key_input_consumption','environment_key_loss','goal','stop']} | {
        'candidate_id':b['candidate']['id'],'intent':list(intent(b['candidate'])),
        'actions_trace':[r['action'] for r in b['trace']], 'feedback_trace':[r['feedback'] for r in b['trace']],
        'native_new_necessary_rule_count':len(b['new_key_recipes']),
        'preparation_actions_until_first_necessary_recipe':first,
        'craft_actions':sum(parse_action(r['action']).verb=='craft' for r in b['trace']),
        'inspect_actions':sum(parse_action(r['action']).verb=='inspect' for r in b['trace']),
        'consumption':merged_counts(b['trace'],'action_consumption'),
        'production':merged_counts(b['trace'],'action_production'),
        'environment_loss_quantities':merged_counts(b['trace'],'environment_key_loss'),
        'unrelated_key_consumption_quantities':merged_counts(b['trace'],'unrelated_key_input_consumption'),
        'repeated_inspect_without_new_public_recipe':repeated,'craft_without_output_or_new_recipe':empty_craft,
        'public_known_necessary_executions':execs,'raw_entry_useful':bool(b['useful'] and raw_entry(s,b['candidate'])),
        'native_trace_digest':digest(b['trace'])}


def aggregate(rows,base):
    by={r['state_id']:r for r in base}; gains=[];losses=[]
    for r in rows:
        b=by[r['state_id']]
        if r['useful'] and not b['useful']:gains.append(r['state_id'])
        if b['useful'] and not r['useful']:losses.append(r['state_id'])
    families=sorted({r['family'] for r in rows})
    per={f:{'useful':sum(r['useful'] for r in rows if r['family']==f),
        'net':sum(int(r['useful'])-int(by[r['state_id']]['useful']) for r in rows if r['family']==f)} for f in families}
    keys=['useful','one_step_useful','actions','native_new_necessary_rule_count','rejections','unrelated_craft',
          'unrelated_key_input_consumption','environment_key_loss','raw_entry_useful','repeated_inspect_without_new_public_recipe',
          'craft_without_output_or_new_recipe','harmful_goal_override','known_necessary_execution_delayed','changed']
    result={k:sum(r[k] for r in rows) for k in keys}
    result.update(n=len(rows),gains=gains,losses=losses,retained_original=10-len(losses),net=len(gains)-len(losses),
        positive_net_families=sum(r['net']>0 for r in per.values()),by_family=per,
        actions_per_necessary_recipe=result['actions']/result['native_new_necessary_rule_count'] if result['native_new_necessary_rule_count'] else None,
        actions_per_useful=result['actions']/result['useful'] if result['useful'] else None,
        rejection_states=sum(r['rejections']>0 for r in rows),
        known_necessary_execution_actions=sum(len(r['public_known_necessary_executions']) for r in rows),
        actual_goal_reached_in_short_branch=sum(r['goal'] for r in rows),
        closed_loop_success=None)
    return result


def main():
    verify_freeze()
    ss=load(OLD/'states.json');states={s['state_id']:s for s in ss}
    original={r['state_id']:r['branches'] for r in map(json.loads,gzip.open(OLD/'native_branches.jsonl.gz','rt'))}
    supplement=list(map(json.loads,gzip.open(OUT/'native_supplements.jsonl.gz','rt')))
    extra={(r['state_id'],r['candidate']['id']):r['branch'] for r in supplement if r['kind']=='base_proposal'}
    decisions={r['state_id']:r for r in load(OUT/'decisions.json')}
    inputs={r['state_id']:r['public'] for r in load(OUT/'public_inputs.json')}
    judgments={(r['state_id'],r['method'],r['replicate']):r for r in load(OLD/'judgments.json')}
    methods=['C0','C1','C2','C3','L','J3']; rows=[];misses=[];llm=[];pairs=[]
    for s in ss:
        sid=s['state_id'];d=decisions[sid];pub=inputs[sid];bs=original[sid]
        assert {k:d[k] for k in decide(pub)}==decide(pub),sid
        j=judgments[sid,'J3',0]['parsed'];family=parse_action(s['public_view']['target_action']).target
        old=bs[d['choices']['C0']];ob=brief(s,old);ctrl=controller(s['public_controller'],s['observation'])
        base_c=primitive_candidate(s['frozen_base_proposal'])
        base_b=bs.get(base_c['id']) or extra[sid,base_c['id']]
        f0=s['rule_decisions']['J0']['stage10']['frozen_F0_candidate']
        assert s['rule_actions']['J0']==s['rule_decisions']['J0']['stage10']['selected_action']
        menu={c['id']:c for c in s['candidates']}
        good=[brief(s,bs[k]) for k in menu if bs[k]['useful']]
        base_action=parse_action(s['rule_actions']['J0']);goal=parse_action(ctrl.target).target
        old_first=old['trace'][0] if old['trace'] else None
        native_goal_opportunity=bool(old_first and not old_first['rejected'] and base_action.target==goal
             and base_action.verb in {'craft','pick up','store','take out'}
             and (old_first['action_production'] or old_first['goal']))
        for m in methods:
            cid=d['choices'][m] if m!='J3' else j['selected_candidate_id'];b=bs[cid];v=brief(s,b)
            changed=cid!=d['choices']['C0'];first_changed=bool(b['trace'] and old['trace'] and b['trace'][0]['action']!=old['trace'][0]['action'])
            v.update(state_id=sid,family=family,method=m,changed=changed,first_action_changed=first_changed,
                source='Stage12 frozen native branch',
                harmful_goal_override=bool(first_changed and native_goal_opportunity and not b['goal']),
                known_necessary_execution_delayed=bool(first_changed and ctrl.base_progress(s['rule_actions']['J0'])
                    and old_first and not old_first['rejected']),
                additional_actions_vs_C0=b['actions']-old['actions'],
                baseline_action_not_resumed_within_window=bool(first_changed and not any(r['action']==s['rule_actions']['J0'] for r in b['trace'])))
            rows.append(v)
            if m in {'C1','C2','C3','L'} and changed:
                pairs.append({'state_id':sid,'family':family,'method':m,'features':d['features'],
                    'original':ob,'alternative':v,'delta_useful':int(b['useful'])-int(old['useful']),
                    'delta_necessary_rules':len(b['new_key_recipes'])-len(old['new_key_recipes']),
                    'not_full_task_effect':True})
        if good and not old['useful']:
            raw=[b for b in good if raw_entry(s,menu[b['candidate_id']])]
            minprep=min(b['preparation_actions_until_first_necessary_recipe'] for b in good)
            constraints=[]
            for b in good:
                c=menu[b['candidate_id']];a=c['next_action'];p=parse_action(a)
                if p.verb in {'enter','store','pick up','take out'} or b['rejections']:
                    constraints.append({'candidate_id':c['id'],'initial_public_condition':ctrl.assess(a),
                        'preparatory_first_action':a,'native_rejections':b['rejections']})
            costly=[b['candidate_id'] for b in good if b['consumption'] or b['environment_key_loss'] or b['actions']>=3]
            overridden=s['frozen_base_proposal']!=s['rule_actions']['J0']
            tags={
                'A':{'supported':bool(raw),'level':'native_counterfactual','meaning':'unconnected public entry yields necessary new knowledge; actual raw/intermediate identity not inferred by policy','candidates':[b['candidate_id'] for b in raw]},
                'B':{'supported':any(b['actions']>1 for b in good),'level':'native_counterfactual','meaning':'multi-action useful alternatives exist; unavoidable only when minimum preparation >0','unavoidable_within_observed_menu':minprep>0,'minimum_preparation_actions':minprep},
                'C':{'supported':bool(constraints),'level':'public_observation_and_native_counterfactual','meaning':'some useful alternatives require transport/acquisition or encounter a rejection; this alone does not prove S1 could not choose another immediate candidate','evidence':constraints},
                'D':{'supported':bool(overridden and base_b['useful']),'level':'native_counterfactual' if overridden and base_b['useful'] else 'unproven',
                    'meaning':'only count when exact frozen base proposal branch is useful and S1 override is not', 'override_observed':overridden,'base_proposal_useful':base_b['useful']},
                'E':{'supported':bool(d['features']['same_known_component_last3'] and d['features']['public_necessary_knowledge_drought']>=3),
                    'level':'public_observation_proxy','meaning':'sustained same public recipe component without new publicly connected recipe; causal overexploitation is not established',
                    'weaker_known_branch_action_observed':bool(ctrl.table.recipes.get(base_action.target,{}).get('ingredients') or any(base_action.target in r.get('ingredients',[]) for r in ctrl.table.recipes.values()))},
                'F':{'supported':bool(costly),'level':'native_counterfactual_cost','meaning':'actual useful branch uses >=3 actions or consumes resources/exposes loss; scarcity and net full-task harm remain untested','candidates':costly}}
            misses.append({'state_id':sid,'family':family,'case_id':s['case_id'], 'source_stage':s['source_stage'],
                'source_method':s['source_method'],'source_index':s['source_index'], 'public_view':s['public_view'],
                'public_observation':s['observation'],'remaining_actions':s['remaining_actions'],
                'base_proposal':s['frozen_base_proposal'],'fifo_candidate':f0,'S1_action':s['rule_actions']['J0'],
                'S1_choice_details':s['rule_decisions']['J0'],'S1_branch':ob,'base_proposal_branch':brief(s,base_b),
                'all_public_candidates':s['candidates'],'entry_ledger':d['entry_ledger'],'public_features':d['features'],
                'useful_candidates':good,'minimum_useful_actions':min(b['actions'] for b in good),
                'minimum_preparation_actions':minprep,'tags':tags,
                'not_proven':['hidden relevance identifiable in advance','overrides caused global failure','more short-term knowledge improves full-task success']})
        # Deduplicate actual intents, keep the first original ranked descriptor.
        ranked=[];seen=set();aliases=[]
        for cid in j['ranked_candidate_ids']:
            key=intent(menu[cid])
            if key in seen:aliases.append(cid)
            else:ranked.append(cid);seen.add(key)
        groups=collections.defaultdict(list)
        for cid,c in menu.items():groups[intent(c)].append(cid)
        alias_effects=[{'intent':list(k),'ids':ids,'different_information_outcomes':len({bs[x]['useful'] for x in ids})>1}
                      for k,ids in groups.items() if len(ids)>1]
        jc=menu[j['selected_candidate_id']];jb=bs[jc['id']];jbrief=brief(s,jb)
        connected=confirmed(ctrl);reason=' '.join(str(j.get(k,'')) for k in ['reason','hypothesized_connection','expected_information'])
        mentioned=[]
        for product,recipe in ctrl.table.recipes.items():
            for dep in recipe.get('ingredients',[]):
                if product in reason and dep in reason:mentioned.append({'product':product,'ingredient':dep})
        station_evidence=[n for n in ctrl.table.recipes.get(goal,{}).get('stations',[]) if n in reason]
        unobserved=[n for n in ctrl.table.recipes if n in reason and n not in connected and n!=goal]
        target_unconnected=jc['target'] not in connected
        hasrecipe=bool(ctrl.table.recipes.get(jc['target'],{}).get('ingredients'))
        evidence_class=('disclosed_recipe_direction_plus_unverified_downstream_link' if hasrecipe and target_unconnected
            else 'disclosed_recipe_or_dependency_direction' if hasrecipe or mentioned
            else 'known_station_prerequisite_only' if station_evidence
            else 'public_object_or_production_only_no_disclosed_goal_edge')
        llm.append({'state_id':sid,'family':family,'pair_class':'gain' if jb['useful'] and not old['useful'] else 'loss' if old['useful'] and not jb['useful'] else 'both_useful' if jb['useful'] else 'both_no_necessary_information',
            'same_exploration_intent':intent(old['candidate'])==intent(jc),
            'J0':ob,'J3':jbrief,'J3_raw_judgment':j,'public_features':d['features'],
            'J3_top3_original_ids':j['ranked_candidate_ids'],'J3_distinct_ranked_ids':ranked,
            'removed_alias_ids':aliases,'alias_groups':alias_effects,
            'distinct_top3_useful':any(bs[k]['useful'] for k in ranked),
            'distinct_top2_useful':any(bs[k]['useful'] for k in ranked[:2]),
            'effective_lower_rank_ids':[k for k in ranked[1:] if bs[k]['useful']],
            'no_effective_direction_in_returned_distinct_ranks':bool(good and not any(bs[k]['useful'] for k in ranked)),
            'candidate_pool_has_opportunity':bool(good),
            'new_connection_direction_relative_to_S1':intent(old['candidate'])!=intent(jc) and target_unconnected,
            'new_connection_useful_native_supported':bool(jb['useful'] and not old['useful']),
            'public_evidence_class':evidence_class,'co_mentioned_public_recipe_edges':mentioned,
            'co_mention_is_not_entailment_or_proof_of_reasoning':True,
            'mentioned_public_goal_station_requirements':station_evidence,
            'unconnected_recipe_names_mentioned':unobserved,
            'name_association_causality':'not identifiable from generated explanation alone; hypothesized downstream links remain hypotheses',
            'raw_entry_selected':raw_entry(s,jc),'raw_entry_effective_top3':[k for k in ranked if raw_entry(s,menu[k]) and bs[k]['useful']],
            'actual_native_costs_diagnostic_only':{'J0':old['actions'],'J3':jb['actions'],'difference':jb['actions']-old['actions']}})
    base=[r for r in rows if r['method']=='C0'];summary={m:aggregate([r for r in rows if r['method']==m],base) for m in methods}
    assert len(misses)==17 and summary['C0']['useful']==10 and summary['J3']['useful']==6
    assert len(summary['J3']['gains'])==4 and len(summary['J3']['losses'])==8
    granularity=[{'state_id':r['state_id'], 'family':r['family'],
        'same_first_action_useful_candidates':[b['candidate_id'] for b in r['useful_candidates'] if b['actions_trace'] and b['actions_trace'][0]==r['S1_action']],
        'minimum_useful_actions':r['minimum_useful_actions'],
        'cannot_infer_wrong_first_action':any(b['actions_trace'] and b['actions_trace'][0]==r['S1_action'] for b in r['useful_candidates'])} for r in misses]
    atomic_json(OUT/'evaluation_granularity_audit.json',{'states':granularity,
        'same_first_action_states':sum(r['cannot_infer_wrong_first_action'] for r in granularity),
        'interpretation':'primitive transport stops after one action; craft intention can continue; shared first action does not prove wrong S1 first choice or failure of its future closed-loop continuation'})
    attr={'n':17,'tags':{k:sum(r['tags'][k]['supported'] for r in misses) for k in 'ABCDEF'},
        'unavoidable_multistep':sum(r['tags']['B']['unavoidable_within_observed_menu'] for r in misses),
        'minimum_useful_actions':dict(collections.Counter(r['minimum_useful_actions'] for r in misses)),
        'by_family':{f:{'misses':sum(r['family']==f for r in misses),'tags':{k:sum(r['tags'][k]['supported'] for r in misses if r['family']==f) for k in 'ABCDEF'}} for f in sorted({r['family'] for r in misses})},
        'by_public_conditions':{k:dict(collections.Counter(str(r['public_features'][k]) for r in misses)) for k in ['incomplete_public_dependencies','no_public_progress_streak','same_known_component_last3','uninspected_independent_entry_intents','fresh_uninspected_product']},
        'overrides':sum(r['tags']['D']['override_observed'] for r in misses),
        'hypothesis_not_counted_as_causal_fact':True}
    lsum={'all_states':50,'gains':summary['J3']['gains'],'losses':summary['J3']['losses'],
        'other38':[r['state_id'] for r in llm if r['pair_class'] not in {'gain','loss'}],
        'same_intent_states':sum(r['same_exploration_intent'] for r in llm),
        'returned_distinct_directions':sum(len(r['J3_distinct_ranked_ids']) for r in llm),
        'returned_original_ids':sum(len(r['J3_top3_original_ids']) for r in llm),
        'states_with_rank_alias':sum(bool(r['removed_alias_ids']) for r in llm),
        'alias_groups_with_outcome_disagreement':sum(a['different_information_outcomes'] for r in llm for a in r['alias_groups']),
        'distinct_top3_effective_states':sum(r['distinct_top3_useful'] for r in llm),
        'distinct_top2_effective_states':sum(r['distinct_top2_useful'] for r in llm),
        'top1_miss_with_lower_effective':sum(not r['J3']['useful'] and bool(r['effective_lower_rank_ids']) for r in llm),
        'opportunity_but_no_effective_direction_returned':sum(r['no_effective_direction_in_returned_distinct_ranks'] for r in llm),
        'evidence_classes':dict(collections.Counter(r['public_evidence_class'] for r in llm)),
        'raw_entry_top1_effective':sum(r['J3']['raw_entry_useful'] for r in llm),
        'raw_entry_top3_effective':sum(bool(r['raw_entry_effective_top3']) for r in llm),
        'Oracle Upper Bound':{'useful':sum(r['J0']['useful'] or r['J3']['useful'] for r in llm),
            'implementable':False,'uses_native_outcome_labels':True},
        'L_public_selector':summary['L'],
        'feature_distributions_by_pair_class':{cls:{k:dict(collections.Counter(str(r['public_features'][k]) for r in llm if r['pair_class']==cls)) for k in next(iter(decisions.values()))['features']} for cls in ['gain','loss','both_useful','both_no_necessary_information']}}
    sensitivity=[]
    for r in supplement:
        if r['kind']!='truncation_sensitivity':continue
        s=states[r['state_id']];old=original[r['state_id']][r['candidate']['id']];b=r['branch']
        assert old['trace']==b['trace'][:4]
        keys6=sorted({n for row in b['trace'][:6] for n in row['new_key_recipes']})
        sensitivity.append({'state_id':s['state_id'],'family':parse_action(s['public_view']['target_action']).target,
            'candidate_id':r['candidate']['id'],'at4':brief(s,old),'at8':brief(s,b),
            'at6_new_key_recipes':keys6,'gain_at6':bool(keys6) and not old['useful'],
            'gain_at8':b['useful'] and not old['useful'], 'first4_identical':True})
    ssens={'branches':len(sensitivity),'states':len({r['state_id'] for r in sensitivity}),
        'newly_useful_at6_branches':sum(r['gain_at6'] for r in sensitivity),
        'newly_useful_at8_branches':sum(r['gain_at8'] for r in sensitivity),
        'newly_useful_at8_states':sorted({r['state_id'] for r in sensitivity if r['gain_at8']}),
        'scope':'separate posthoc horizon sensitivity; Stage12 and C0-C3 main labels unchanged', 'rows':sensitivity}
    cfg=load(OUT/'protocol.json')['selection_gate'];gates={}
    for m in ['C1','C2','C3','L']:
        a=summary[m];z=summary['C0']
        checks={'net_gain':a['net']>=cfg['minimum_net_gain'],'multiple_families':a['positive_net_families']>=cfg['minimum_positive_families'],
            'baseline_retention':len(a['losses'])<=cfg['maximum_lost_original'],
            'environment_loss':a['environment_key_loss']<=z['environment_key_loss']+cfg['maximum_added_environment_loss_states'],
            'unrelated_consumption':a['unrelated_key_input_consumption']<=z['unrelated_key_input_consumption']+cfg['maximum_added_unrelated_consumption_states'],
            'goal_execution':a['harmful_goal_override']<=cfg['maximum_harmful_goal_overrides']}
        gates[m]={'checks':checks,'passed':all(checks.values())}
    decision={'decision':'LOCAL_CANDIDATE_ONLY' if any(v['passed'] for v in gates.values()) else 'NO-GO',
        'gates':gates,'independent_validation':False,'closed_loop_success':None,'api_calls':0,'new_cost_usd':0,
        'project_total_usd':36.888925758,'no_post_freeze_rule_changes':True,
        'stop':'do not tune these rules on these states or stack additional ranking/GPAR; retain S1 reference unless independently justified'}
    for name,obj in [('state_metrics',rows),('method_metrics',summary),('misses',misses),('attribution_summary',attr),('llm_pairs',llm),
                     ('llm_summary',lsum),('changed_pairs',pairs),('sensitivity',ssens),('research_judgment',decision)]:atomic_json(OUT/(name+'.json'),obj)
    print(json.dumps({'methods':{m:{k:summary[m][k] for k in ['useful','net','changed','retained_original']} for m in methods},'attribution':attr['tags'],'unavoidable_multistep':attr['unavoidable_multistep'],'base_useful_overrides':attr['tags']['D'],'sensitivity':{k:v for k,v in ssens.items() if k!='rows'},'decision':decision['decision']},ensure_ascii=False))

if __name__=='__main__':main()
