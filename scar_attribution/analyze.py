"""Reproducible statistics from offline audit/branch records, without an API."""
import argparse
from collections import Counter,defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np
from scar.io import atomic_json,digest
from scar_attribution.prepare import load_traces
from scripts.audit_v3_learning import metrics


def write_csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows(rows)


def archive(path,rows):
    # Fixed gzip header permits byte-identical reruns of the export.
    with Path(path).open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:
            for r in rows:f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())


def read_archive(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]


def mean(values):return statistics.mean(values) if values else None


def uncertainty(rows,pairs,field='delta'):
    """Equal-family estimand; source/mechanism bootstrap resamples family clusters."""
    by=defaultdict(list)
    for r in rows:by[r['family']].append(r[field])
    fam={f:mean(v) for f,v in by.items()};point=mean(list(fam.values()))
    if not fam:return {'families':0,'mean':None}
    out={'families':len(fam),'mean':point}
    for cluster in ['family','source_cluster','mechanism_cluster']:
        groups=defaultdict(list)
        for f,v in fam.items():groups[f if cluster=='family' else pairs[f][cluster]].append(v)
        nums=np.array([sum(v) for v in groups.values()]);dens=np.array([len(v) for v in groups.values()]);n=len(groups)
        rng=np.random.default_rng(20261012);indexes=rng.integers(0,n,size=(10000,n));stats=nums[indexes].sum(axis=1)/dens[indexes].sum(axis=1)
        out[cluster]={'clusters':n,'percentile_95':np.quantile(stats,[.025,.975]).tolist()}
    return out


def certified(branch,k):
    return bool(branch and branch['distance'] is not None and branch['distance']<=k)


def interval(branch,k):
    if certified(branch,k):return 1,1
    if branch and branch['terminal_without_goal']:return 0,0
    return 0,1


def classify_family(pair,audit,searches,traces):
    evidence=defaultdict(list);rows=audit['rows'];last=rows[-1]
    for r in rows:
        i=r['index'];truth=r['goal_conditions'];pred=r['learned_target_prediction'];chosen=r['outcomes'][r['C0']]
        if truth['rejected'] and pred['status']!='REJECT':
            evidence['A'].append({'index':i,'kind':'missed_target_rejection','oracle_blockers':truth['violated'],'prediction':pred['status'],'strength':'observed prediction error/abstention, not proof of downstream cause'})
        if truth['rejected'] and pred['status']=='REJECT' and not any(o['progress']['net_blocker_reduction']>0 for o in r['outcomes'].values()):
            evidence['B'].append({'index':i,'kind':'known_blocker_no_immediate_repair_candidate','strength':'one-step proxy; intermediate planning may still be possible'})
        alternatives=[a for a,o in r['outcomes'].items() if o['progress']['net_blocker_reduction']>max(0,chosen['progress']['net_blocker_reduction'])]
        if alternatives:
            evidence['C'].append({'index':i,'kind':'unselected_candidate_with_greater_direct_blocker_repair','actions':alternatives,'selected':r['C0'],'strength':'same-state executed counterfactual; local progress only'})
        for event in r['events']:
            if event['event']=='plan_invalidated':
                evidence['D'].append({'index':i,'kind':'plan_invalidated','plan_before':r['memory_plan'],'strength':'observed invalidation; harm to a valid future plan unproven'})
        if not chosen['truth']['rejected'] and chosen['physical_noop']:
            evidence['E'].append({'index':i,'kind':'accepted_physical_noop','action':r['C0'],'strength':'observed world/task-state no-op; information gain remains possible'})
        if r['revisit_count']:
            evidence['E'].append({'index':i,'kind':'exact_physical_revisit','strength':'observed physical/task-state repeat, not merely repeated action'})
    for s in searches:
        rs=s['state'];k=rs['max_depth'];branch=s['branches'];up=s['upper']
        any_current=any(certified(b,k) for b in branch.values())
        if up['distance'] is not None and up['distance']<=k and not up['first_action_in_original_candidates'] and not any_current:
            evidence['B'].append({'index':rs['index'],'kind':'upper_bound_first_action_absent','upper_first_action':up['path'][0],'strength':'upper path verified; current candidates UNKNOWN, so not proof they cannot recover'})
        actual=branch[rows[rs['index']]['C0']]
        shorter=[a for a,b in branch.items() if b['distance'] is not None and actual['distance'] is not None and b['distance']<actual['distance']]
        if shorter:
            evidence['C'].append({'index':rs['index'],'kind':'shorter_found_path_not_selected','actions':shorter,'strength':'both witnesses replayed; shortest-found distances not optimal distances'})
    if audit['summary']['status']=='failed':evidence['F'].append({'index':len(rows),'kind':'bounded_format_repair_abort','error':audit['summary']['error'],'strength':'observed original failure, no new attempts'})
    flattened=[dict(cause=k,**e) for k,es in evidence.items() for e in es]
    first=min(flattened,key=lambda e:(e['index'],e['cause'])) if flattened else None
    # Retain the real ordered trajectories for all requested paired methods.
    sequences={m:[{'index':r['index'],'proposed':r['proposed_action'],'actual':r['executed_action'],'rejected':r['semantic_rejection'],'goal':r.get('diagnostic_goal_reached',False),'target_released':r.get('target_condition_release',False),'candidate_actions':r['all_proposals']} for r in by.get(pair['family'],[])] for m,by in traces.items()}
    return {'case_id':pair['id'],'family':pair['family'],'group':pair['group'],'target_action':pair['target_action'],'public_goal':pair['public_goal'],'initial_blockers':rows[0]['goal_conditions'],'initial_public_predicates':rows[0]['public_target_facts'],'earliest_observed_warning':first,'causes':dict(evidence),'last_index':last['index'],'last_action':last['C0'],'last_goal_conditions':last['outcomes'][last['C0']]['goal_conditions_after'],'outcomes':pair['recovery_at_40'],'sequences':sequences,'classification_caveat':'A-F are explicitly graded evidence, not mutually exclusive causal proportions or claims that eventual failure alone identifies cause.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',default=None);p.add_argument('--output',default='results/v3/attribution');args=p.parse_args()
    out=Path(args.output);pairs_list=json.loads((out/'pairs.json').read_text());pairs={p['family']:p for p in pairs_list}
    states=json.loads((out/'state_manifest.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
    if args.runtime:
        root=Path(args.runtime)
        audits=[json.loads(p.read_text()) for p in sorted((root/'audits').glob('*.json'))]
        searches=[json.loads((root/'branches'/(s['state_id']+'.json')).read_text()) for s in states]
        archive(out/'audits.jsonl.gz',audits);archive(out/'branches.jsonl.gz',searches)
        atomic_json(out/'execution_status.json',json.loads((root/'search_status.json').read_text()))
    else:
        audits=read_archive(out/'audits.jsonl.gz');searches=read_archive(out/'branches.jsonl.gz')
    assert len(audits)==89 and len(searches)==len(states)==321
    rows=[dict(family=a['family'],case_id=a['case_id'],**r) for a in audits for r in a['rows']]
    assert len(rows)==2150 and sum(r['intercepted'] for r in rows)==141
    assert not any(a['condition_mismatches'] for a in audits)
    by_state={(r['family'],r['index']):r for r in rows}
    predictions=[];target_predictions=[];learning_errors=Counter();one_step=[];candidate_rows=[]
    for r in rows:
        truth=r['outcomes'][r['proposed_action']]['truth']['rejected'];pred=r['learned_base_prediction']
        predictions.append({'truth':truth,'prediction':pred});target_predictions.append({'truth':r['goal_conditions']['rejected'],'prediction':r['learned_target_prediction']})
        if truth and pred['status']!='REJECT':
            learning_errors['missed_rejection_'+pred['status']]+=1
            learning_errors['missed_with_no_hypotheses_or_feedback_rule']+=not pred['hypotheses'] and not pred['rules']
            learning_errors['missed_with_unknown_predicates']+=bool(pred['unknown'])
        if not truth and pred['status']=='REJECT':learning_errors['false_rejection']+=1
        chosen={c:r['outcomes'].get(r[c]) for c in ['C0','C1']}
        one_step.append({'family':r['family'],'index':r['index'],'changed':r['C0']!=r['C1'],'candidate_count':len(r['candidate_actions']),**{c+'_'+k:v for c,o in chosen.items() for k,v in {'legal':bool(o and not o['truth']['rejected']),'direct_progress':bool(o and o['progress']['net_blocker_reduction']>0),'goal':bool(o and o['physical_goal']),'physical_noop':bool(o and o['physical_noop'])}.items()}})
        candidate_rows.append({'family':r['family'],'index':r['index'],'n':len(r['candidate_actions']),'any_legal':any(not o['truth']['rejected'] for o in r['outcomes'].values()),'any_direct_progress':any(o['progress']['net_blocker_reduction']>0 for o in r['outcomes'].values()),'target_blocked':r['goal_conditions']['rejected']})
    singles={'decisions':len(rows),'candidate_size_histogram':dict(Counter(x['candidate_count'] for x in one_step)),'candidate_instances':sum(len(r['candidate_actions']) for r in rows),'C1_changed_actions':sum(x['changed'] for x in one_step),'by_condition':{c:{k:sum(r[c+'_'+k] for r in one_step) for k in ['legal','direct_progress','goal','physical_noop']} for c in ['C0','C1']},'any_direct_progress_candidate':sum(r['any_direct_progress'] for r in candidate_rows),'base_prediction_metrics':metrics(predictions),'target_prediction_metrics':metrics(target_predictions),'learning_errors':dict(learning_errors)}
    singles['paired_family_C1_minus_C0']={k:uncertainty([{'family':r['family'],'delta':int(r['C1_'+k])-int(r['C0_'+k])} for r in one_step],pairs) for k in ['legal','direct_progress','goal']}
    comparisons=[];condition_table=[];interventions=[];coverage=[];all_verified=0;expanded=generated=0;replay_paths=0
    for s in searches:
        st=s['state'];r=by_state[(st['family'],st['index'])];bs=s['branches'];up=s['upper']
        assert s['source_audit_digest']==digest({k:v for k,v in r.items() if k not in ['family','case_id']})
        assert r['record_digest']==st['record_digest']
        for b in bs.values():
            all_verified+=b['verified'];replay_paths+=bool(b['verification'])
            if not b['search_cache_reused']:expanded+=b['search']['expanded'];generated+=b['search']['generated']
        expanded+=up['expanded'];generated+=up['generated'];replay_paths+=up['distance'] is not None
        for ks,cs in s['conditions'].items():
            k=int(ks);base=bs[r['proposed_action']];actual=bs[r['executed_action']]
            for c,choice in cs.items():
                b=bs.get(choice['action']);lo,hi=interval(b,k)
                condition_table.append({'family':st['family'],'state_id':st['state_id'],'index':st['index'],'long_chain':st['long_chain'],'intercepted':r['intercepted'],'k':k,'condition':c,'action':choice['action'],'verified_path':lo,'upper_reachability_bound':hi,'distance_found':b['distance'] if b else None,'changed_from_C0':choice['action']!=r['C0']})
            current=any(certified(b,k) for b in bs.values());upper=up['distance'] is not None and up['distance']<=k
            coverage.append({'family':st['family'],'state_id':st['state_id'],'index':st['index'],'k':k,'current_candidates_verified':current,'augmented_verified':bool(current or upper),'upper_path_first_absent':bool(upper and not up['first_action_in_original_candidates']),'upper_adds_certificate':bool(upper and not current),'upper_adds_absent_first_certificate':bool(upper and not current and not up['first_action_in_original_candidates'])})
            if r['intercepted']:
                bl,bh=interval(base,k);al,ah=interval(actual,k);effect=r['outcomes'][r['executed_action']]
                interventions.append({'family':st['family'],'state_id':st['state_id'],'k':k,'base_action':r['proposed_action'],'intervention_action':r['executed_action'],'base_verified':bl,'intervention_verified':al,'delta':al-bl,'identification_lower':al-bh,'identification_upper':ah-bl,'base_distance_found':base['distance'],'intervention_distance_found':actual['distance'],'direct_progress':effect['progress']['net_blocker_reduction']>0,'physical_noop':effect['physical_noop'],'equal_physical_successors':effect['child_physical_key']==r['outcomes'][r['proposed_action']]['child_physical_key'],'no_direct_progress_and_no_certificate':effect['progress']['net_blocker_reduction']<=0 and not al})
    for scope in ['all_sampled','initial_only','interventions_only']:
        scoped=[r for r in condition_table if scope=='all_sampled' or scope=='initial_only' and r['index']==0 or scope=='interventions_only' and r['intercepted']]
        for k in [5,10,20]:
            subset=[r for r in scoped if r['k']==k];by=defaultdict(dict)
            for r in subset:by[r['state_id']][r['condition']]=r
            for c in ['C0','C1','C2','C3']:
                cr=[v[c] for v in by.values()];deltas=[{'family':v[c]['family'],'delta':v[c]['verified_path']-v['C0']['verified_path']} for v in by.values()]
                comparisons.append({'scope':scope,'k':k,'condition':c,'states':len(cr),'families':len({r['family'] for r in cr}),'verified_chosen_paths':sum(r['verified_path'] for r in cr),'unknown_or_censored':sum(r['upper_reachability_bound']-r['verified_path'] for r in cr),'changed_actions':sum(r['changed_from_C0'] for r in cr),'family_paired_delta_vs_C0':uncertainty(deltas,pairs)})
    intervention_summary={}
    for k in [5,10,20]:
        rs=[r for r in interventions if r['k']==k]
        intervention_summary[str(k)]={'states':len(rs),'families':len({r['family'] for r in rs}),'base_verified':sum(r['base_verified'] for r in rs),'intervention_verified':sum(r['intervention_verified'] for r in rs),'both_verified':sum(r['base_verified'] and r['intervention_verified'] for r in rs),'neither_verified':sum(not r['base_verified'] and not r['intervention_verified'] for r in rs),'direct_progress':sum(r['direct_progress'] for r in rs),'physical_noop':sum(r['physical_noop'] for r in rs),'equal_physical_successors':sum(r['equal_physical_successors'] for r in rs),'unverified_progress_count_not_proven_waste':sum(r['no_direct_progress_and_no_certificate'] for r in rs),'MSIB_verified_lower_bound_difference':uncertainty(rs,pairs),'identification_lower_mean':uncertainty(rs,pairs,'identification_lower')['mean'],'identification_upper_mean':uncertainty(rs,pairs,'identification_upper')['mean'],'caveat':'Equal physical successors refer to environment reachability, not agent beliefs. UNKNOWN search outcomes never prove wasted intervention.'}
    coverage_summary=[]
    for scope in ['all_sampled','initial_only']:
        for k in [5,10,20]:
            rs=[r for r in coverage if r['k']==k and (scope!='initial_only' or r['index']==0)]
            coverage_summary.append({'scope':scope,'k':k,'states':len(rs),'families':len({r['family'] for r in rs}),**{key:sum(r[key] for r in rs) for key in ['current_candidates_verified','augmented_verified','upper_path_first_absent','upper_adds_certificate','upper_adds_absent_first_certificate']}})
    methods=['ShortTermMemoryAgent','SimpleFailureRecovery','SCARV2Agent','SCARV3Agent']
    traces={m:load_traces('results/v3/formal',m) for m in methods}
    by_family=defaultdict(list)
    for s in searches:by_family[s['state']['family']].append(s)
    classifications=[classify_family(pairs[a['family']],a,by_family[a['family']],traces) for a in audits]
    cause_counts={group:{letter:sum(bool(c['causes'].get(letter)) for c in classifications if c['group']==group) for letter in 'ABCDEF'} for group in ['stm_only','v3_only','both_success','both_failure']}
    long_ids={p['family'] for p in pairs_list if 'long_recovery_chain' in p['types']}
    long_stats={m:{'families':len(long_ids),'recovered':sum(pairs[f]['recovery_at_40'][m] for f in long_ids),'steps':sum(len(traces[m][f]) for f in long_ids),'repeated_observation_states':sum(len(rs)-len({r['visible_state_hash'] for r in rs}) for f,rs in traces[m].items() if f in long_ids),'interventions':sum(r['intercepted'] for f,rs in traces[m].items() if f in long_ids for r in rs),'target_releases':sum(r.get('target_condition_release',False) for f,rs in traces[m].items() if f in long_ids for r in rs)} for m in methods}
    assert long_stats['ShortTermMemoryAgent']['interventions']==0
    assert long_stats['SCARV3Agent']['interventions']==sum(r['intercepted'] for r in rows if r['family'] in long_ids)==121
    long_stats['V3_events']={'plan_invalidations':sum(e['event']=='plan_invalidated' for r in rows if r['family'] in long_ids for e in r['events']),'states_with_alternative_direct_progress_but_no_selection':sum(any(o['progress']['net_blocker_reduction']>max(0,r['outcomes'][r['C0']]['progress']['net_blocker_reduction']) for o in r['outcomes'].values()) for r in rows if r['family'] in long_ids),'single_candidate_decisions':sum(len(r['candidate_actions'])==1 for r in rows if r['family'] in long_ids)}
    false_predicates=Counter();false_cases=Counter();visibility=Counter();gain_examples=[];future_generation=[]
    for r in rows:
        pred=r['learned_base_prediction'];truth=r['outcomes'][r['proposed_action']]['truth']
        if pred['status']=='REJECT' and not truth['rejected']:
            false_predicates.update(pred['violated']);false_cases[r['case_id']]+=1
        for k in r['goal_conditions']['violated']:
            visibility[(k.split(':')[0],r['public_target_facts'][k].get('truth'))]+=1
    for s in searches:
        c=s['conditions']['10'];a=s['branches'][c['C0']['action']];b=s['branches'][c['C2']['action']]
        if certified(b,10) and not certified(a,10):
            gain_examples.append({'state_id':s['state']['state_id'],'group':pairs[s['state']['family']]['group'],'C0':a['path'],'C0_distance':a['distance'],'C2':b['path'],'C2_distance':b['distance']})
        if s['upper']['path'] and not s['upper']['first_action_in_original_candidates']:
            future=[r for r in by_state.values() if r['family']==s['state']['family'] and r['index']>s['state']['index']]
            action=s['upper']['path'][0]
            future_generation.append({'state_id':s['state']['state_id'],'missing_upper_first_action':action,'generated_later_on_actual_trajectory':any(action in r['candidate_actions'] for r in future),'executed_later_on_actual_trajectory':any(action==r['C0'] for r in future),'caveat':'Later actual states differ; this is not a same-state re-planning experiment.'})
    details={'initial_candidate_size_histogram':dict(Counter(len(a['rows'][0]['candidate_actions']) for a in audits)),'false_reject_predicates':dict(false_predicates),'false_reject_cases':dict(false_cases),'blocked_condition_visibility':[{'condition_type':k,'public_truth':v,'occurrences':n} for (k,v),n in visibility.items()],'repair_candidate_states':singles['any_direct_progress_candidate'],'repair_choice_accuracy':{c:singles['by_condition'][c]['direct_progress']/singles['any_direct_progress_candidate'] for c in ['C0','C1']},'K10_certificate_gain_examples':gain_examples,'later_candidate_generation':future_generation}
    distance_details={}
    for c in ['C1','C2','C3']:
        counts=Counter();deltas=[]
        for s in searches:
            a=s['branches'][s['conditions']['10']['C0']['action']];b=s['branches'][s['conditions']['10'][c]['action']]
            if a['first_action']==b['first_action']:continue
            counts['changed']+=1
            if a['distance'] is None or b['distance'] is None:counts['unknown']+=1;continue
            delta=b['distance']-a['distance'];deltas.append(delta);counts['shorter' if delta<0 else 'longer' if delta>0 else 'equal']+=1
        distance_details[c]=dict(counts,mean_distance_delta_among_changed_both_found=mean(deltas))
    details['K10_choice_shortest_found_distance_comparison']=distance_details
    resource={'api_calls':0,'api_cost_usd':0,'previous_project_cost_usd':23.130083244,'audited_families':89,'audited_decisions':2150,'sampled_states':321,'sampled_families':89,'source_clusters':len({p['source_cluster'] for p in pairs_list}),'mechanism_clusters':len({p['mechanism_cluster'] for p in pairs_list}),'distinct_first_action_branches':sum(len(s['branches']) for s in searches),'verified_first_action_branches':all_verified,'reported_positive_paths_each_replayed_twice':replay_paths,'expanded_search_nodes':expanded,'generated_search_transitions':generated,'search_worker_seconds_sum':sum(s['seconds'] for s in searches),'audit_worker_seconds_sum':sum(a['seconds'] for a in audits),'condition_mismatches':0,'C0_decisions_exactly_reproduced':2150,'actual_steps_exactly_replayed':2150,'protocol_digest':digest(protocol),'inputs_digest':digest({'audits':[digest(a) for a in audits],'searches':[digest(s) for s in searches]})}
    resource['search_wall_seconds']=json.loads((out/'execution_status.json').read_text())['wall_seconds']
    tables=out/'tables';tables.mkdir(exist_ok=True)
    write_csv(tables/'single_step.csv',one_step);write_csv(tables/'four_conditions.csv',condition_table);write_csv(tables/'interventions.csv',interventions);write_csv(tables/'candidate_coverage.csv',coverage)
    write_csv(tables/'paired_families.csv',[{k:p[k] for k in ['id','family','game','group','source_cluster','mechanism_cluster']}|p['recovery_at_40'] for p in pairs_list])
    atomic_json(out/'single_step_summary.json',singles);atomic_json(out/'condition_comparisons.json',comparisons);atomic_json(out/'intervention_summary.json',intervention_summary);atomic_json(out/'candidate_coverage_summary.json',coverage_summary);atomic_json(out/'case_classifications.json',classifications);atomic_json(out/'cause_counts.json',cause_counts);atomic_json(out/'long_chain_summary.json',long_stats);atomic_json(out/'resource_accounting.json',resource)
    atomic_json(out/'mechanism_evidence.json',details)
    print(json.dumps({'resources':resource,'single_step':singles['by_condition'],'candidate_histogram':singles['candidate_size_histogram'],'initial_comparisons':[r for r in comparisons if r['scope']=='initial_only' and r['k']==10]}))


if __name__=='__main__':main()
