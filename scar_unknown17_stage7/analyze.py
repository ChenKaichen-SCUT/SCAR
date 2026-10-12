"""Family-paired exploratory analysis, including censored conversion delays.

No policy or provider imports beyond public state parsing. All failures and
negative paired changes are kept. Local counterfactuals are a separate tier.
"""
import argparse
from collections import Counter,defaultdict
import csv
import gzip
import json
from pathlib import Path
import statistics
from scar.io import atomic_json,digest
from scar_sequence.analyze import episode_metrics,aggregate,bootstrap,divide
from scar_sequence.public import ResourceTable
from scar_unknown17.analyze import mechanism_metrics,grouped_extra
from scar_unknown17.audit import known_recipes
from scar_v3.state import parse_action

METHODS=['C0','C1','C2','C3','C4','C5']


def stage7_metrics(case,rows,opportunities,resources):
    t=ResourceTable();key={case['object_names'][x] for x in case['recipe_graph']};goal=case['goal']['name']
    for h in case['history']:t.observe(h['before']);t.observe(h['after'],h['action'])
    first={x:0 for x in known_recipes(t)&key};effective={};all_new=set(known_recipes(t));all_known_at=0 if key<=set(first) else None
    modes=Counter();triggers=Counter();attempts=[];gap_actions=[];no_gain=[];seen={};events=[];mode_events=[];retry_success=[]
    info_cost=0;info_tokens=0;info_steps=0;info_types=Counter();directed_key_gains=0
    kinds=Counter();public_gains=0;last_progress=-1;unproductive_toggles=[];transitions=[]
    for r in rows:
        i=r['index'];p=parse_action(r['executed_action']);d=r.get('structured',{}).get('stage7',{})
        for name,value in d.items():
            if value:triggers[name]+=len(value) if name=='A_suppressed' else 1
        modes[(d.get('C_mode') or {}).get('mode','UNMANAGED')]+=1
        known_before=known_recipes(t);t.observe(r['observation']);signature=digest([t.state.get(k) for k in ['location','hands','equipment','ground']]+[{k:v['counts'] for k,v in t.containers.items()}])
        t.observe(r['next_observation'],r['executed_action']);new=known_recipes(t)-all_new;all_new|=new;public_gains+=len(new)
        probe=r.get('structured',{}).get('mechanisms',{}).get('exploration')
        if probe or p.verb=='inspect':
            info_steps+=1;info_cost+=r['api_delta']['cost_usd'];info_tokens+=r['api_delta']['input_tokens']+r['api_delta']['output_tokens']
            info_types['inspect' if p.verb=='inspect' else 'forward_craft' if p.verb=='craft' else 'move' if p.verb=='enter' else 'preparation']+=1
            if probe:directed_key_gains+=len(new&key)
        for x in sorted((known_recipes(t)&key)-set(first)):first[x]=i+1
        if all_known_at is None and key<=set(first):all_known_at=i+1
        productive=p.verb=='craft' and 'successfully crafted' in r['action_rule_feedback']
        if productive and p.target in key:effective.setdefault(p.target,i+1)
        if new or productive or r['objective_metrics']['physical_goal_delta']>0 or r['objective_metrics']['conditions_released']>0:last_progress=i
        repeat_key=digest([signature,r['executed_action'],r['action_rule_feedback']])
        same_resources=r['physical_before']['resource_hash']==r['physical_after']['resource_hash']
        if repeat_key in seen and not new and not productive and same_resources:
            no_gain.append({'index':i,'previous':seen[repeat_key],'action':r['executed_action'],
                'scope':'repeated same public resources, same action and feedback, no recipe gain and no physical resource delta'})
        seen[repeat_key]=i
        for e in r.get('events',[]):
            if e.get('event')=='stage7_attempt_result':
                if e.get('was_forward_trial') and e.get('state')=='BLOCKED_BY_PRECONDITION':triggers['A_precondition_failure_quota_retained']+=1
                if e.get('retry_after_block'):triggers['A_condition_released_success']+=1
                if e.get('retry_after_block') and e.get('was_forward_trial'):triggers['A_forward_released_retry']+=1
                rr=resources.get(i,{})
                attempts.append(dict(e,index=i,engine_actual_consumption=rr.get('actual_action_consumption'),
                    engine_environment_loss=rr.get('environment_quantity_destruction'),resource_evidence='independent original engine action audit'))
                if e.get('retry_after_block'):retry_success.append({'index':i,'target':e['target'],'action':r['executed_action'],'feedback':e['feedback']})
            if e.get('event')=='stage7_gap_result':
                gain=sorted(new&key);event=dict(e,index=i,new_necessary_recipes=gain,
                    actual_consumption=resources.get(i,{}).get('actual_action_consumption'))
                gap_actions.append(event);kinds[e['classification']]+=1
            if e.get('event')=='stage7_mode_transition':
                event=dict(e,index=i,last_measured_progress=last_progress);mode_events.append(event)
                if transitions and e['new']==transitions[-1]['old'] and last_progress<transitions[-1]['index']:
                    unproductive_toggles.append({'from':transitions[-1]['index'],'to':i,'old':e['old'],'new':e['new'],
                        'scope':'no new recipe, productive craft, goal gain or condition release between opposite mode changes; not necessarily irrational'})
                transitions.append(event)
        if new or productive or d:
            events.append({'index':i,'action':r['executed_action'],'base':r['proposed_action'],
                'new_recipes':sorted(new),'new_key_recipes':sorted(new&key),'productive':productive,
                'feedback':r['action_rule_feedback'],'mechanism':d})
    recovery=next((i+1 for i,r in enumerate(rows) if r['diagnostic_goal_reached']),None)
    conversion=[]
    for name,discovered in sorted(first.items()):
        exec_time=effective.get(name)
        # Production before discovery is reported separately, not a negative delay.
        converted=exec_time is not None and exec_time>=discovered
        conversion.append({'recipe':name,'intermediate':name!=goal,'discovered_after_action':discovered,
            'first_effective_action':exec_time,'executed_before_discovery':exec_time is not None and exec_time<discovered,
            'converted':converted,'censored':exec_time is None,
            'lag_or_remaining40':exec_time-discovered if converted else 40-discovered if exec_time is None else None})
    last_delay=None if all_known_at is None else {'last_necessary_rule_after_action':all_known_at,
        'completion_action':recovery,'censored':recovery is None,'lag_or_remaining40':(recovery if recovery is not None else 40)-all_known_at}
    ready=[x for x in opportunities if x['known_engine_ready_nodes']]
    batches=[e for e in events if 'D_batch' in e['mechanism']]
    goal_crafted=goal in effective
    return {'information_action_steps':info_steps,'information_action_cost_usd':info_cost,'information_action_tokens':info_tokens,
        'information_action_types':dict(info_types),'directed_key_gains':directed_key_gains,
        'first_key_recipe_actions':first,'first_effective_recipe_actions':effective,'recipe_conversion_records':conversion,
        'last_rule_to_goal':last_delay,'all_necessary_known_at':all_known_at,'all_known_but_failed':all_known_at is not None and recovery is None,
        'known_ready_opportunities':len(ready),'known_ready_executed':sum(x['ready_executed'] for x in ready),
        'known_ready_missed':sum(not x['ready_executed'] for x in ready),
        'mode_actions':dict(modes),'mechanism_trigger_counts':dict(triggers),'mode_transitions':mode_events,
        'unproductive_mode_toggles':unproductive_toggles,'unsupported_same_signature_toggles':sum(a['public_signature']==b['public_signature'] for a,b in zip(mode_events,mode_events[1:])),
        'reasonable_recover_entries':sum(e['new']=='RECOVER' and 'public execution failure' in e['reason'] for e in mode_events),
        'actual_attempt_records':attempts,'condition_released_successes':retry_success,
        'gap_actions':gap_actions,'gap_action_types':dict(kinds),'public_new_recipes':public_gains,
        'gap_discovered_key_recipe_count':sum(len(x['new_necessary_recipes']) for x in gap_actions),
        'confirmed_same_state_no_gain_actions':no_gain,'expired_trial_missed_opportunities':sum(len(x['missed_retry_candidates']) for x in opportunities),
        'final_available_unrelated_actions':sum(x['final_available_unrelated_action'] for x in opportunities),
        'avoidable_reserve_depletion':sum(bool(x['avoidable_known_reserve_depletion']) for x in opportunities),
        'reserve_depletion_evidence_records':sum(len(x['avoidable_known_reserve_depletion']) for x in opportunities),
        'reserve_depletion_by_type':dict(Counter('redundant_ground_copy_production' if 'redundant craft' in e['scope'] else 'consumed_owned_goal' if 'already-owned final' in e['scope'] else 'smaller_productive_quantity' for x in opportunities for e in x['avoidable_known_reserve_depletion'])),
        'produced_goal_but_uncollected_at_end':bool(goal_crafted and recovery is None),
        'D_quantity_changed':sum(e['action']!=e['mechanism']['D_batch']['legacy'] for e in batches),
        'mechanism_timeline':events}


def group_stage7(rs):
    conv=[x for r in rs for x in r['recipe_conversion_records'] if x['intermediate'] and x['lag_or_remaining40'] is not None]
    last=[r['last_rule_to_goal'] for r in rs if r['last_rule_to_goal'] is not None]
    sums={k:sum(r[k] for r in rs) for k in ['known_ready_opportunities','known_ready_executed','known_ready_missed',
        'expired_trial_missed_opportunities','final_available_unrelated_actions','avoidable_reserve_depletion','reserve_depletion_evidence_records',
        'information_action_steps','information_action_cost_usd','information_action_tokens','directed_key_gains',
        'produced_goal_but_uncollected_at_end','all_known_but_failed','public_new_recipes','gap_discovered_key_recipe_count','D_quantity_changed','reasonable_recover_entries','unsupported_same_signature_toggles']}
    triggers=Counter();modes=Counter();kinds=Counter()
    for r in rs:triggers.update(r['mechanism_trigger_counts']);modes.update(r['mode_actions']);kinds.update(r['gap_action_types'])
    return sums|{'information_cost_per_discovered_key':divide(sums['information_action_cost_usd'],sum(r['unknown_to_supported'] for r in rs)),
        'directed_actions_per_directed_key_gain':divide(sum(r['directed_information_actions'] for r in rs),sums['directed_key_gains']),
        'ready_execution_rate':divide(sums['known_ready_executed'],sums['known_ready_opportunities']),
        'condition_released_successes':sum(len(r['condition_released_successes']) for r in rs),
        'same_state_confirmed_no_gain':sum(len(r['confirmed_same_state_no_gain_actions']) for r in rs),
        'unproductive_mode_toggles':sum(len(r['unproductive_mode_toggles']) for r in rs),
        'mode_actions':dict(modes),'trigger_counts':dict(triggers),'gap_action_types':dict(kinds),
        'intermediate_conversion_n':len(conv),'intermediate_conversion_censored':sum(x['censored'] for x in conv),
        'intermediate_conversion_lag_with_censor_mean':statistics.mean(x['lag_or_remaining40'] for x in conv) if conv else None,
        'last_rule_goal_n':len(last),'last_rule_goal_censored':sum(x['censored'] for x in last),
        'last_rule_goal_lag_with_censor_mean':statistics.mean(x['lag_or_remaining40'] for x in last) if last else None,
        'failed_subgoal_progress_sum':sum(r['subgoal_completed'] for r in rs if not r['recovery_at_40']),
        'lag_scope':'includes right-censored remaining40 durations; descriptive restricted observation, not uncensored time-to-event mean; name-defined necessary nodes may already have obtainable copies'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/stage7')
    from scar_unknown17_stage7.failure_audit import adjudicated_status
    tasks=json.loads((root/'tasks.json').read_text());cases={c['id']:c for c in json.loads((out/'cases.json').read_text())}
    groups={name:defaultdict(list) for name in ['resource_audit','batch_audit','opportunity_audit']}
    for name,group in groups.items():
        for r in map(json.loads,gzip.open(out/(name+'.jsonl.gz'),'rt')):group[r['task_id']].append(r)
    catalog=json.loads((out/'truth_catalog_evaluation_only.json').read_text());metrics=[];summaries=[];incomplete=[]
    files={m:gzip.open(out/f'trajectories_{m}.jsonl.gz','wt') for m in METHODS}
    for task in tasks:
        folder=root/'runs'/task['task_id'];path=folder/'summary.json'
        if not path.exists():incomplete.append({'task_id':task['task_id'],'status':'missing'});continue
        s=json.loads(path.read_text());s['raw_execution_status']=s['status'];s['status']=adjudicated_status(task['task_id'],s['status'])
        if s['status'] not in {'completed','method_abort'}:incomplete.append({'task_id':task['task_id'],'status':s['status']});continue
        rows=[json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))];c=cases[task['id']]
        rr=groups['resource_audit'][task['task_id']];bb=groups['batch_audit'][task['task_id']]
        m=episode_metrics(s,rows,c,rr);m.update(mechanism_metrics(c,rows,catalog[c['id']],bb))
        m.update(stage7_metrics(c,rows,groups['opportunity_audit'][task['task_id']],{r['index']:r for r in rr}))
        final=rows[-1]['physical_after'] if rows else {}
        root_recipe=c['recipe_graph'].get(c['goal']['object_id'],{})
        m['failure_context']={'kind':'method_abort' if s['status']=='method_abort' else 'unknown_necessary_rules' if m['missing_key_recipes'] else 'known_names_but_execution_or_resources' if not m['recovery_at_40'] else 'success',
            'goal_owned':final.get('accessible',{}).get(c['goal']['name']),
            'final_root_materials_evaluation_only':{c['object_names'][oid]:{'nominal_per_copy':amount,'owned_now':final.get('accessible',{}).get(c['object_names'][oid],0)} for oid,amount in root_recipe.get('ingredients',{}).items()},
            'missing_current_root_stations_evaluation_only':[c['object_names'][oid] for oid,yes in final.get('conditions',{}).get(c['goal']['object_id'],{}).get('stations',{}).items() if not yes],
            'scope':'final local conditions, not proof of global irreversibility or alternative-plan absence'}
        m['raw_execution_status']=s['raw_execution_status']
        m['observed_actions_before_stop']=len(rows)
        m['method_abort']=s['status']=='method_abort'
        for record in m['recipe_conversion_records']:
            record['observed_followup_actions']=max(0,len(rows)-record['discovered_after_action'])
            record['early_method_abort']=m['method_abort']
        if m['last_rule_to_goal'] is not None:m['last_rule_to_goal'].update(early_method_abort=m['method_abort'],observed_episode_actions=len(rows))
        m['switches']=json.loads(Path('configs/protocol_stage7.json').read_text())['switches'][task['algorithm']]
        metrics.append(m);summaries.append(s)
        files[task['algorithm']].write(json.dumps({'task_id':task['task_id'],'case_id':c['id'],'summary':m,'rows':rows},ensure_ascii=False)+'\n')
    for f in files.values():f.close()
    atomic_json(out/'completion.json',{'expected':102,'completed':len(metrics),'incomplete':incomplete,
        'fully_complete':len(metrics)==102 and not incomplete,'statuses':dict(Counter(r['status'] for r in metrics))})
    atomic_json(out/'episode_metrics.json',metrics);atomic_json(out/'all_summaries.json',summaries)
    oldfamilies=json.loads(Path('results/unknown17/family_comparison.json').read_text())
    common={r['case_id'] for r in oldfamilies if r['all_fail']}
    oldcombined={r['case_id']:r for r in json.loads(Path('results/unknown17/episode_metrics.json').read_text()) if r['algorithm']=='FIFOCombined'}
    scopes={'all':set(cases)}|{g:{c['id'] for c in cases.values() if c['game']==g} for g in ['saltglass','quarantine','robot_kingdom']}
    scopes.update(old_common11=common,old_missing7={x for x in common if oldcombined[x]['missing_key_recipes']},old_known4={x for x in common if not oldcombined[x]['missing_key_recipes']})
    grouped={scope:{method:aggregate(rs)|grouped_extra(rs)|group_stage7(rs) for method in METHODS
        for rs in [[r for r in metrics if r['algorithm']==method and r['case_id'] in ids]]} for scope,ids in scopes.items()}
    atomic_json(out/'method_metrics.json',grouped)
    by={m:{r['case_id']:r for r in metrics if r['algorithm']==m} for m in METHODS};paired=[]
    for a,b in [(m,'C0') for m in METHODS[1:]]+[("C5",m) for m in METHODS[1:5]]:
        ids=sorted(set(by[a])&set(by[b]));d=[int(by[a][x]['recovery_at_40'])-int(by[b][x]['recovery_at_40']) for x in ids]
        paired.append({'a':a,'b':b,'family':bootstrap(d),'source_cluster':bootstrap(d,[cases[x]['game'] for x in ids]),
            'a_only':[x for x,z in zip(ids,d) if z==1],'b_only':[x for x,z in zip(ids,d) if z==-1],
            'paired_key_rule_delta':bootstrap([by[a][x]['key_recipe_discovered']-by[b][x]['key_recipe_discovered'] for x in ids]),
            'paired_all_attempt_cost_delta':bootstrap([by[a][x]['cost_usd']-by[b][x]['cost_usd'] for x in ids])})
    atomic_json(out/'paired_comparisons.json',paired)
    families=[]
    for cid,c in cases.items():
        evidence={m:by[m].get(cid) for m in METHODS}
        families.append({'case_id':cid,'target':c['goal']['name'],'game':c['game'],
            'old_common_failure':cid in common,'old_failure_class':'old_success' if oldcombined[cid]['recovery_at_40'] else 'missing_knowledge' if oldcombined[cid]['missing_key_recipes'] else 'known_but_execution_failed',
            'old_combined_success':oldcombined[cid]['recovery_at_40'],'old_missing':oldcombined[cid]['missing_key_recipes'],
            'successes':{m:e['recovery_at_40'] if e else None for m,e in evidence.items()},
            'C0_failed_new_success':[m for m in METHODS[1:] if evidence[m] and evidence[m]['recovery_at_40'] and not evidence['C0']['recovery_at_40']],
            'C0_success_new_failure':[m for m in METHODS[1:] if evidence[m] and not evidence[m]['recovery_at_40'] and evidence['C0']['recovery_at_40']],
            'evidence':{m:{k:e[k] for k in ['recovery_steps','missing_key_recipes','first_key_recipe_actions','mechanism_trigger_counts','condition_released_successes',
                'known_ready_opportunities','known_ready_executed','recipe_conversion_records','last_rule_to_goal','mechanism_timeline','avoidable_reserve_depletion',
                'final_available_unrelated_actions','produced_goal_but_uncollected_at_end','subgoal_completed','failure_context']} for m,e in evidence.items() if e},
            'causal_limit':'paired families share initial state and seed but remote LLM samples differ; mechanism events need local counterfactual corroboration'})
    atomic_json(out/'family_comparison.json',families)
    fields=['scope','algorithm','n','successes','recovery_at_10','recovery_at_20','recovery_at_40','mean_success_steps','steps','cost_usd','cost_per_success_all_attempts',
        'key_discovery_rate','intermediate_discovery_rate','quantity_nondominated_rate','ready_execution_rate','all_known_but_failed','avoidable_reserve_depletion',
        'final_available_unrelated_actions','harmful_goal_overrides']
    with (out/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader()
        for scope,methods in grouped.items():
            for m,r in methods.items():w.writerow({k:({'scope':scope,'algorithm':m}|r).get(k) for k in fields})
    definitions={'evidence_levels':['unit correctness','same-state engine local counterfactual','real model closed-loop performance'],
        'success':'physical possession goal, 40 actions; all17 denominators, no removed failures or extra seeds',
        'names_known':'public nonempty ingredient names; station-only not known; numeric acquisition hints do not change common ResourceTable',
        'censored_delays':'for every discovered necessary recipe, record first actual productive craft and missing execution censored at remaining40; not only success averages; never-discovered rules separately missing',
        'ready':'publicly known necessary recipe, public count below explicit/inherited demand, and independent engine craft1 legal; step opportunities, not randomized timing effects',
        'reserve_loss':'exact consumption compared with smaller productive quantity OR legal acquisition of enough already-visible product copies, crossing public downstream reserve floor; also loss of required existing final copy. Count affected actions; publish evidence record count and type separately because multiple records may describe one action; not proof of irreversible global failure',
        'batch_Pareto':'1/2/3/4 same physical state, more output no higher consumption; ignores future utility of unnecessary copies',
        'no_gain':'confirmed same public resource state/action/feedback and no rule/resource change; ordinary no-immediate gain remains delayed/unknown',
        'expired_trial':'previously rejected forward trial still marked exhausted, relevant station now present, engine says craft legal, no product already known available, but not retried on this step; candidate opportunity, not guaranteed task-relevant',
        'mode_toggle':'opposite transitions without new rule, productive craft, goal gain or condition release; descriptive, not all harmful',
        'scope':'17 repeatedly analyzed families, 4/3/10 per game; family paired bootstrap10000; only3 source clusters; remote temperature.7 not strict matched sampling; six cells cannot identify all interactions'}
    atomic_json(out/'metric_definitions.json',definitions)
    print(json.dumps({'complete':len(metrics),'successes':{m:r['successes'] for m,r in grouped['all'].items()},'new_cost_usd':sum(r['cost_usd'] for r in metrics)}))

if __name__=='__main__':main()
