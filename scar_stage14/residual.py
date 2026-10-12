"""Attribution from complete recorded trajectories, not new model answers."""
import re
from collections import Counter,defaultdict
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,OLD,load,records,episodes,save_records
from scar_stage14.intents import recorded_goal
from scar_v3.state import parse_action


def actual_closure(rows,start,target,operation):
    made=False;production=None
    for r in rows[start:]:
        p=parse_action(r['executed_action']);feedback=r['feedback']
        if p.verb=='craft' and p.target==target and 'I successfully crafted ' in feedback:
            made=True;production=r['index']
        inspect=p.verb=='inspect' and p.target==target and feedback.startswith('I inspected '+target+':')
        acquired=('I have acquired a new item: '+target+'. It can be used to craft:') in feedback
        if (operation in {'inspect','visit_inspect'} and inspect) or (operation=='craft_inspect' and made and (inspect or acquired)):
            return {'complete':True,'index':r['index'],'actions_inclusive':r['index']-start+1,
                'production_index':production,'closure':'inspect' if inspect else 'acquisition_disclosure',
                'evidence_action':r['executed_action'],'evidence_feedback':feedback}
    return {'complete':False,'index':None,'production_index':production}


def public_commitment(row):
    d=row.get('structured',{});e=d.get('mechanisms',{}).get('exploration') or {};s=e.get('source') or {}
    if e.get('reason') in {'acquire publicly named trial ingredient','reach publicly disclosed required station'} and s.get('product'):
        return s['product'],e
    if e.get('reason')=='bounded forward recipe trial' and s.get('recipe'):return s['recipe'],e
    x=d.get('stage11',{}).get('selected') or {}
    if x.get('kind')=='known_forward_bridge' and x.get('target'):return x['target'],x
    return None,None


def main():
    ss={s['state_id']:s for s in load(OLD/'states.json')};refs=load(ROOT/'intent_references.json')
    intents={(r['state_id'],r['intent']['id']):r['intent'] for r in load(ROOT/'candidate_intents.json')}
    bs={(r['state_id'],r['intent_id']):r['branch'] for f in ['reused_intent_branches.jsonl.gz','native_intent_branches.jsonl.gz'] for r in records(ROOT/f)}
    metrics=load(ROOT/'calibrated_state_metrics.json');by={(r['state_id'],r['panel'],r['window'],r['method']):r for r in metrics}
    timelines=defaultdict(list)
    for r in records(ROOT/'episode_timeline.jsonl.gz'):timelines[r['task_id']].append(r)
    knowledge={r['task_id']:r for r in load(ROOT/'episode_knowledge_summary.json')}
    eps={ep['task_id']:(stage,m,ep,c,path) for stage,m,ep,c,path in episodes()}
    frozen={(s['source_task'],s['source_index']):s for s in ss.values()}
    oldmiss={r['state_id'] for r in load('results/stage13/misses.json')}
    state_rows=[];continuity=[]
    for sid,s in ss.items():
        stage,m,ep,c,path=eps[s['source_task']];start=s['source_index'];timeline=timelines[ep['task_id']]
        ref=next(r for r in refs if r['state_id']==sid and r['role']=='J0');intent=intents[sid,ref['intent_id']];branch=bs[sid,ref['intent_id']]
        original=by[sid,'original',4,'J0'];parser=by[sid,'parser_only',4,'J0'];both=by[sid,'both',4,'J0']
        closure=actual_closure(ep['rows'],start,intent['target'],intent['operation'])
        g=recorded_goal(s['rule_decisions']['J0'],s['rule_actions']['J0'])
        explicit=g is not None
        common=0
        for a,b in zip(branch['trace'],ep['rows'][start:]):
            if a['action']!=b['executed_action']:break
            assert a['after']==b['next_observation'];common+=1
        divergence=start+common if common<len(branch['trace']) and start+common<len(ep['rows']) else None
        before_switch=timeline[start:divergence] if divergence is not None else []
        newinfo=[{'index':r['index'],'delta':{k:r['K1_delta'][k] for k in ['new_relations','quantity_updates','station_updates']}}
                 for r in before_switch if any(r['K1_delta'][k] for k in ['new_relations','quantity_updates','station_updates'])]
        resources=[r for r in ep['summary'].get('resource_destruction',[]) if start<=r['index']<(divergence if divergence is not None else start)]
        risks=[{'index':r['index'],'feedback':r['feedback']} for r in ep['rows'][start:divergence] if re.search(r'attacked|lost \d+ HP|Missing necessary|sufficient amount',r['feedback'])] if divergence is not None else []
        # Negative evidence must be available, not assumed from absent labels.
        gates={'explicit_recorded_exploration':explicit,'accepted_first_action':True,
            'native_fixed_continuation_completes':branch['intent_complete'],
            'actual_full_trajectory_unfinished':not closure['complete'],
            'different_actual_next_action':divergence is not None,
            'no_intervening_information_resource_or_risk':not (newinfo or resources or risks),
            'no_direct_goal_switch':divergence is not None and parse_action(ep['rows'][divergence]['executed_action']).target!=parse_action(c['target_action']).target}
        # Current candidate continuation proves only its own legality, not an
        # arbitrary suffix after a diverged actual trajectory.
        gates['next_action_native_supported']=common<len(branch['trace']) and not branch['trace'][common]['rejected']
        confirmed=all(gates.values())
        status='confirmed' if confirmed else 'completed_in_actual_trajectory' if closure['complete'] and explicit else 'possible_or_insufficient' if explicit and not closure['complete'] else 'no_explicit_multistep_commitment'
        ct={'state_id':sid,'task_id':ep['task_id'],'source_index':start,'intent':intent,'recorded_goal':g,
            'actual_closure':closure,'common_action_prefix':common,'divergence_index':divergence,
            'actual_at_divergence':ep['rows'][divergence]['executed_action'] if divergence is not None else None,
            'fixed_at_divergence':branch['trace'][common]['action'] if common<len(branch['trace']) else None,
            'new_public_information_before_switch':newinfo,'resource_changes_before_switch':resources,'public_risk_or_precondition_feedback':risks,
            'gates':gates,'status':status,'confirmed_F4':confirmed,'native_branch_intent_id':intent['id']}
        continuity.append(ct)
        tags=[];evidence={}
        if parser['useful'] and not original['useful']:
            tags.append('F1');evidence['F1']={'kind':'new acquisition feedback missed by old scoring','original_action':s['rule_actions']['J0'],'new_keys':parser['new_necessary']}
        if both['useful'] and not parser['useful']:
            tags.append('F2');evidence['F2']={'kind':'explicit preparatory prefix gains under shared continuation','goal':g,'actions':[r['action'] for r in branch['trace'][:4]]}
        gain6=by[sid,'both',6,'J0']['useful'];gain8=by[sid,'both',8,'J0']['useful']
        if both['any_opportunity'] and not both['useful']:
            if gain8:
                tags.extend(['F5','F6']);evidence['F5']={'kind':'four-action window truncation','useful_by6':gain6,'useful_by8':gain8}
                evidence['F6']='a longer productive intention is not established as a wrong direction by the four-action score alone'
            else:
                tags.append('F3');evidence['F3']={'kind':'conditional local knowledge opportunity missed','scope':'fixed observed pool and window, not full-task optimality',
                    'selected_action':s['rule_actions']['J0'],'selected_new_keys':both['new_necessary']}
        if not both['intent_complete'] and branch['stop'] not in {'atomic_intent_incomplete','action_budget'}:
            if 'F5' not in tags:tags.append('F5')
            evidence['F5']={'stop':branch['stop'],'feedback':[r['feedback'] for r in branch['trace'] if r['rejected']], 'scope':'selected bounded intent limitation, not global task impossibility'}
        if confirmed:tags.append('F4');evidence['F4']=gates
        elif explicit and not closure['complete']:
            if 'F6' not in tags:tags.append('F6')
            evidence['F6']={'strict_continuity_gates':gates,'status':status}
        state_rows.append({'state_id':sid,'family':both['family'],'source_stage':stage,'source_method':m,'source_index':start,
            'was_original17_miss':sid in oldmiss,'necessary_K1_not_K2_before':timeline[start]['needed_public_but_unregistered_before'],
            'original_useful':original['useful'],'parser_only_useful':parser['useful'],'both_useful4':both['useful'],
            'both_useful6':gain6,'both_useful8':gain8,'opportunity4':both['any_opportunity'],
            'same_first_as_old_useful_branch':any(b['trace'] and b['trace'][0]['action']==s['rule_actions']['J0'] and b['useful'] for rr in records(OLD/'native_branches.jsonl.gz') if rr['state_id']==sid for b in rr['branches'].values()),
            'tags':tags,'evidence':evidence,'continuity_status':status,'confirmed_F4':confirmed})
    # Full formal corpus, including successes, all methods. The S1/E0/E1
    # reference grouping is explicit; other algorithms are not S1 replications.
    complete=[];commitments=[]
    for task,(stage,m,ep,c,path) in eps.items():
        k=knowledge[task];tl=timelines[task];keys={c['object_names'][oid] for oid in c['recipe_graph']}
        last=k['last_public_knowledge'];first={n:f['first_relation_step'] for n,f in last.items() if f.get('ingredients') and n in keys}
        made=defaultdict(list);attempts=defaultdict(list)
        for r in ep['rows']:
            p=parse_action(r['executed_action'])
            if p.verb=='craft':
                attempts[p.target].append({'index':r['index'],'feedback':r['feedback']})
                if 'I successfully crafted ' in r['feedback']:made[p.target].append(r['index'])
        conversions=[]
        for name,step in sorted(first.items()):
            after=[j for j in made[name] if ep['rows'][j]['observation']['step']>=step]
            conversions.append({'recipe':name,'first_public_step':step,'successful_craft_indices':made[name],
                'executed_after_disclosure':bool(after),'not_successfully_crafted':not bool(made[name]),
                'known_before_first_failed_or_successful_attempt':bool(attempts[name]),'attempts':attempts[name]})
        all_known=next((r['index']+1 for r in tl if not (keys-(set(n for n,f in r['K1_before'].items() if f.get('ingredients'))|set(r['K1_delta']['new_relations'])))),None)
        losses=[]
        for x in ep['summary'].get('resource_destruction',[]):
            losses.append({**x,'named_items':{c['object_names'].get(n,n):v for n,v in x['items'].items()}})
        native_rejections=[{'index':r['index'],'action':r['executed_action'],'feedback':r['feedback']} for r in ep['rows'] if re.search(r'Cannot |Invalid ',r['feedback'])]
        row={'stage':stage,'method':m,'task_id':task,'family':k['family'],'success':k['historical_success_unchanged'],
            'source_file':path,'source_sha256':None,'steps':len(ep['rows']),
            'necessary_still_undisclosed':k['native_necessary_still_undisclosed'],
            'historical_missing_reclassified':k['historical_missing_but_actually_disclosed'],
            'necessary_public_unregistered':k['native_necessary_public_but_unregistered'],
            'all_necessary_public_after_action':all_known,'actions_remaining_when_all_known':len(ep['rows'])-all_known if all_known is not None else None,
            'knowledge_to_production':conversions,'known_but_never_successfully_crafted':[r['recipe'] for r in conversions if r['not_successfully_crafted']],
            'actual_environment_resource_losses':losses,'actual_rejections':native_rejections,
            'registration_only_reinspection_indices':[r['index'] for r in tl if r['registration_only_reinspection']],
            'reference_group':(stage,m) in {(10,'S1'),(11,'E0'),(11,'E1')},
            'interpretation':'observed knowledge/production/resource gaps; no counterfactual full-task feasibility guarantee'}
        complete.append(row)
        if not row['reference_group']:continue
        seen=set()
        for r in ep['rows']:
            target,e=public_commitment(r)
            if not target or target in seen:continue
            seen.add(target);closure=actual_closure(ep['rows'],r['index'],target,'craft_inspect')
            state=frozen.get((task,r['index']));ct=next((x for x in continuity if state and x['state_id']==state['state_id']),None)
            commitments.append({'task_id':task,'family':k['family'],'stage':stage,'method':m,'start_index':r['index'],
                'target':target,'action':r['executed_action'],'public_evidence':e,'actual_closure':closure,
                'matched_frozen_state':state['state_id'] if state else None,
                'strict_native_counterfactual_available':bool(ct),'confirmed_F4':bool(ct and ct['confirmed_F4']),
                'classification':'actual_chain_completed' if closure['complete'] else 'physical_or_information_change_at_checkpoint' if ct and not ct['gates']['no_intervening_information_resource_or_risk'] else 'insufficient_counterfactual_evidence'})
    oldrows=[r for r in state_rows if r['was_original17_miss']]
    summary={'states':50,'original_misses':len(oldrows),'initial_necessary_K1_K2_gap_states':sum(bool(r['necessary_K1_not_K2_before']) for r in state_rows),
        'original17_parser_only_recovered':sum(r['parser_only_useful'] for r in oldrows),
        'original17_shared_first_with_effective_old_branch':sum(r['same_first_as_old_useful_branch'] for r in oldrows),
        'original17_executor_additional_recovered4':sum(r['both_useful4'] and not r['parser_only_useful'] for r in oldrows),
        'original17_total_recovered4':sum(r['both_useful4'] for r in oldrows),
        'original17_remaining4':sum(not r['both_useful4'] for r in oldrows),
        'original17_remaining_tags':dict(Counter(t for r in oldrows if not r['both_useful4'] for t in r['tags'])),
        'calibrated_residual4':sum(r['opportunity4'] and not r['both_useful4'] for r in state_rows),
        'confirmed_F4_frozen_states':sum(r['confirmed_F4'] for r in continuity),
        'continuity_status':dict(Counter(r['status'] for r in continuity)),
        'full_reference_unique_task_target_commitments':len(commitments),
        'full_reference_commitment_status':dict(Counter(r['classification'] for r in commitments)),
        'full_episodes':len(complete),'full_successes':sum(r['success'] for r in complete),
        'decision':'NO-GO','RQ3_causal_generalization':'INCONCLUSIVE',
        'reason':'no replicated strict continuity failure established beyond fixed deterministic continuation; do not start a new mechanism or paid loop',
        'new_api_calls':0,'new_model_cost_usd':0}
    atomic_json(ROOT/'residual_states.json',state_rows);atomic_json(ROOT/'continuity_audit.json',continuity)
    atomic_json(ROOT/'full_episode_failure_audit.json',complete);atomic_json(ROOT/'full_reference_commitments.json',commitments)
    atomic_json(ROOT/'residual_summary.json',summary);print(summary)

if __name__=='__main__':main()
