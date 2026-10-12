"""Chronological K1/K2/K3 audit of all saved formal episodes and branches."""
import collections
import copy
import json
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,OLD,episodes,load,records,save_records,replay_old_controller,sha
from scar_stage14.knowledge import Knowledge,extract
from scar_stage12.public import controller
from scar_v3.state import parse_action


def names(recipes):return {n for n,r in recipes.items() if r.get('ingredients')}
def compact(k):
    return {n:{x:v for x,v in f.items() if x not in {'raw_evidence','evidence_ids'}} for n,f in k.facts.items()}
def absent(k,recipes):return sorted(set(k.relations())-names(recipes))
def quantity_gaps(k,recipes):
    return sorted(n for n,f in k.relations().items() if f['quantities'] is not None and n in names(recipes)
        and recipes[n].get('quantities')!=f['quantities'])

def initialize(case,cutoff):
    k=Knowledge();checks=[]
    for index,h in enumerate(case['history']):
        checks.append({'history_index':index,'before_step':h['before']['step'],'after_step':h['after']['step'],
            'within_cutoff':h['after']['step']<=cutoff,'forward':h['before']['step']<h['after']['step']})
        # A rejected future row is recorded, never silently fed to the parser.
        if h['after']['step']>cutoff:continue
        k.observe(h['before'],None,cutoff=cutoff,source={'kind':'initial_before','index':index})
        k.observe(h['after'],h['action'],cutoff=cutoff,source={'kind':'initial_after','index':index})
    return k,checks

def snapshot_registration(row):return copy.deepcopy(row['stage7_state_before']['table']['recipes'])

def prompt_access(k,row,request):
    summary={r['key']:r['value']['ingredients'] for r in row.get('fact_summary',{}).get('records',[]) if r['kind']=='recipe' and isinstance(r['value'].get('ingredients'),list)}
    text='\n'.join(m['content'] for m in request['messages']) if request else ''
    raw=set()
    for e in k.events:
        if e['ingredients'] and (e['raw_evidence'] in text or json.dumps(e['raw_evidence'],ensure_ascii=False)[1:-1] in text):raw.add(e['product'])
    summarized={n for n,v in summary.items() if n in k.relations() and set(v)==set(k.facts[n]['ingredients'])}
    return {'request_id':request.get('request_id') if request else None,
        'actual_request_found':request is not None,'exact_native_recipe_text_in_prompt':sorted(raw),
        'recipe_names_in_saved_fact_summary':sorted(summarized),'available_in_prompt_or_summary':sorted(raw|summarized),
        'presence_does_not_prove_reasoning_or_use':True}

def align_request(row,requests,cursor):
    for i in range(cursor,len(requests)):
        q=requests[i];choices=q.get('raw_response',{}).get('choices',[])
        response=choices[0].get('message',{}).get('content') if choices else None
        if response==row['response'] and any(row['observation']['text'] in m['content'] for m in q['messages']):return q,i+1
    return None,cursor

def summarize_run(stage,method,task_id,family,k,old,last_step,first_registered,keys,rows,success=None):
    relations=k.relations();registered=names(old);missing=set(relations)-registered
    delays=[]
    for n,f in relations.items():
        first=f['first_relation_step'];reg=first_registered.get(n)
        delays.append({'recipe':n,'first_disclosed_step':first,'first_registered_step':reg,
            'delay_environment_steps':max(0,reg-first) if reg is not None else None,
            'right_censored':reg is None,'censor_step':last_step})
    return {'stage':stage,'method':method,'task_id':task_id,'family':family,'public_relations':len(relations),
        'registered_relations':len(registered),'registered_disclosed_relations':len(set(relations)&registered),
        'never_registered':sorted(missing),'never_registered_fraction':len(missing)/len(relations) if relations else 0,
        'explicit_quantity_recipes':sum(f['quantities'] is not None for f in relations.values()),
        'quantity_missing_or_different':quantity_gaps(k,old),
        'registered_without_explicit_disclosure':sorted(registered-set(relations)),
        'native_necessary_publicly_known':sorted(set(relations)&keys),'native_necessary_registered':sorted(registered&keys),
        'native_necessary_public_but_unregistered':sorted(missing&keys),
        'native_necessary_still_undisclosed':sorted(keys-set(relations)),
        'delays':delays,'registration_only_reinspection_count':sum(bool(r.get('registration_only_reinspection')) for r in rows),
        'ambiguous_evidence':copy.deepcopy(k.ambiguous),'explicit_conflicts':[n for n,f in k.facts.items() if f['certainty']=='AMBIGUOUS_CONFLICT'],
        'historical_success_unchanged':success,'closed_loop_rerun':False}

def aggregate_runs(runs):
    groups={}
    for dim in ['stage','family','stage_method']:
        parts=collections.defaultdict(list)
        for r in runs:parts[str(r['stage']) if dim=='stage' else r['family'] if dim=='family' else str(r['stage'])+'/'+r['method']].append(r)
        groups[dim]={}
        for label,rr in parts.items():
            delays=[d['delay_environment_steps'] for r in rr for d in r['delays'] if d['delay_environment_steps'] is not None]
            total=sum(r['public_relations'] for r in rr);never=sum(len(r['never_registered']) for r in rr)
            groups[dim][label]={'runs':len(rr),'public_relations_sum_per_run':total,
                'registered_disclosed_relations_sum_per_run':sum(r['registered_disclosed_relations'] for r in rr),
                'never_registered_sum_per_run':never,'never_registered_fraction':never/total if total else 0,
                'quantity_missing_or_different_sum_per_run':sum(len(r['quantity_missing_or_different']) for r in rr),
                'registered_without_explicit_disclosure':sum(len(r['registered_without_explicit_disclosure']) for r in rr),
                'mean_registration_delay_when_registered':sum(delays)/len(delays) if delays else None,
                'registered_delay_samples':len(delays),'censored':never,
                'registration_only_reinspections':sum(r['registration_only_reinspection_count'] for r in rr),
                'native_necessary_public_but_unregistered_sum_per_run':sum(len(r['native_necessary_public_but_unregistered']) for r in rr)}
    return groups


def main():
    for p,h in load(ROOT/'parser_freeze.json')['hashes'].items():assert sha(p)==h,p
    wanted=load(OLD/'states.json');want={(s['source_task'],s['source_index']):s for s in wanted}
    snapshots={};timeline=[];runs=[];all_events=[];request_audit=[];history_audit=[];original_episodes={}
    for stage,method,ep,case,path in episodes():
        original_episodes[ep['task_id']]=(stage,method,ep,case,path)
        first_obs=ep['rows'][0]['observation'];k,hc=initialize(case,first_obs['step'])
        history_audit.append({'task_id':ep['task_id'],'initial_cutoff':first_obs['step'],'initial_history':hc})
        family=parse_action(case['target_action']).target;keys={case['object_names'][oid] for oid in case['recipe_graph']}
        requests=[r['request'] for r in records(f'results/stage{stage}/requests_{method}.jsonl.gz') if r['task_id']==ep['task_id']]
        cursor=0;first_registered={};episode_rows=[]
        for i,row in enumerate(ep['rows']):
            assert row['index']==i and row['next_observation']['step']>row['observation']['step']
            if i:assert ep['rows'][i-1]['next_observation']==row['observation']
            cutoff=row['observation']['step'];k.observe(row['observation'],ep['rows'][i-1]['executed_action'] if i else case['history'][-1]['action'],cutoff=cutoff,source={'file':path,'task_id':ep['task_id'],'index':i,'kind':'current'})
            assert all(e['observed_step']<=cutoff for e in k.events)
            old=snapshot_registration(row);kb=compact(k);known_before=set(k.relations());old_before=names(old)
            for n in old_before:first_registered.setdefault(n,cutoff)
            request,cursor=align_request(row,requests,cursor)
            k3=prompt_access(k,row,request)
            if (ep['task_id'],i) in want:
                s=want[ep['task_id'],i];assert s['observation']==row['observation']
                snapshots[s['state_id']]={'state_id':s['state_id'],'source_stage':stage,'source_task':ep['task_id'],'source_index':i,
                    'cutoff':cutoff,'knowledge':k.to_dict(),'K2_original':copy.deepcopy(s['public_controller']['table']['recipes']),
                    'native_necessary_keys_offline_only':sorted(keys),'K3_source_request':k3,
                    'initial_history_max_step':max(h['after']['step'] for h in case['history']),
                    'prefix_max_step':max((x['next_observation']['step'] for x in ep['rows'][:i]),default=first_obs['step']),
                    'latest_included_event_step':max((e['observed_step'] for e in k.events),default=0),
                    'future_events_excluded':True}
            delta=k.observe(row['next_observation'],row['executed_action'],cutoff=row['next_observation']['step'],
                source={'file':path,'task_id':ep['task_id'],'index':i,'kind':'after'})
            reconstructed=replay_old_controller(stage,row)
            after=reconstructed.table.recipes
            if i+1<len(ep['rows']):
                actual=ep['rows'][i+1]['stage7_state_before']['table']['recipes']
                assert after==actual,(stage,method,ep['task_id'],i,'controller recipe roundtrip')
                after=actual
            for n in names(after):first_registered.setdefault(n,row['next_observation']['step'])
            registered_new=names(after)-old_before
            gap_before=known_before-old_before
            repeated_gap=sorted(registered_new&gap_before) if parse_action(row['executed_action']).verb=='inspect' and not delta['new_relations'] and not delta['quantity_updates'] and not delta['station_updates'] else []
            reported_missing={n for r in row.get('fact_summary',{}).get('records',[]) if r['kind']=='uncertainty' for n in r['value'].get('missing_recipe_names',[])}
            tr={'stage':stage,'method':method,'task_id':ep['task_id'],'family':family,'index':i,'before_step':cutoff,
                'after_step':row['next_observation']['step'],'action':row['executed_action'],'source_file':path,
                'raw_feedback':row['feedback'],'source_observation_digest':digest(row['next_observation']),
                'K1_before':kb,'K2_before':old,'K2_after':copy.deepcopy(after),'K1_delta':delta,
                'K2_new_registered_relations':sorted(registered_new),'public_but_unregistered_before':sorted(gap_before),
                'public_but_unregistered_after':absent(k,after),'explicit_quantities_not_registered':quantity_gaps(k,after),
                'needed_public_but_unregistered_before':sorted(gap_before&keys),
                'needed_public_but_reported_UNKNOWN':sorted(gap_before&keys&reported_missing),
                'registration_only_reinspection':repeated_gap,'K3':k3,
                'K3_workflow_accessible_K2':sorted(old_before),'K3_actual_utilization_proven':False,
                'last_K2_reconstructed_only':i==len(ep['rows'])-1}
            timeline.append(tr);episode_rows.append(tr)
        result=summarize_run(stage,method,ep['task_id'],family,k,after,row['next_observation']['step'],first_registered,keys,episode_rows,ep['summary']['recovery_at_40'])
        result['historically_reported_missing_key_recipes']=ep['summary']['missing_key_recipes']
        result['historical_missing_but_actually_disclosed']=sorted(set(ep['summary']['missing_key_recipes'])&set(k.relations()))
        result['last_public_knowledge']=k.view();result['last_registered_knowledge']=copy.deepcopy(after)
        runs.append(result);all_events.extend(dict(e,stage=stage,method=method,task_id=ep['task_id'],family=family) for e in k.events)
        request_audit.append({'task_id':ep['task_id'],'rows':len(episode_rows),'requests':len(requests),
            'matched_primary':sum(r['K3']['actual_request_found'] for r in episode_rows),
            'unmatched_request_count':len(requests)-sum(r['K3']['actual_request_found'] for r in episode_rows)})
    assert len(snapshots)==50 and len(timeline)==2837 and len(runs)==90
    save_records(ROOT/'episode_timeline.jsonl.gz',timeline);atomic_json(ROOT/'episode_knowledge_summary.json',runs)
    atomic_json(ROOT/'frozen_state_knowledge.json',[snapshots[s['state_id']] for s in wanted])
    atomic_json(ROOT/'history_time_audit.json',{'episodes':history_audit,'states':[{k:v for k,v in snapshots[s['state_id']].items() if k not in {'knowledge','K2_original','K3_source_request','native_necessary_keys_offline_only'}} for s in wanted],
        'stage13_case_history_future_rows':sum(not h['within_cutoff'] for e in history_audit for h in e['initial_history']),
        'stage13_prefix_check':all(snapshots[s['state_id']]['prefix_max_step']<=s['observation']['step'] for s in wanted),
        'passed':all(h['within_cutoff'] and h['forward'] for e in history_audit for h in e['initial_history'])})
    atomic_json(ROOT/'request_context_audit.json',request_audit)
    # Branch knowledge calibration uses separate causal copies of the same prefix.
    states={s['state_id']:s for s in wanted};branch_records=[];branch_runs=[]
    original_registration={r['task_id']:{d['recipe']:d['first_registered_step'] for d in r['delays']} for r in runs}
    old12=list(records(OLD/'native_branches.jsonl.gz'));old13=list(records('results/stage13/native_supplements.jsonl.gz'))
    branches=[(12,r['state_id'],cid,b,'original4') for r in old12 for cid,b in r['branches'].items()]
    branches += [(13,r['state_id'],r['candidate']['id'],r['branch'],r['kind']) for r in old13]
    for stage,sid,cid,b,kind in branches:
        s=states[sid];k=Knowledge.from_dict(snapshots[sid]['knowledge']);ctrl=controller(s['public_controller'],s['observation'])
        keys=set(snapshots[sid]['native_necessary_keys_offline_only']);initial_k1=set(k.relations());initial_k2=names(ctrl.table.recipes)
        # Carry actual historical registration timestamps into each branch;
        # assigning every initial recipe the checkpoint time inflates delays.
        first_registered={n:original_registration[s['source_task']][n] for n in initial_k2}
        assert all(v is not None and v<=s['observation']['step'] for v in first_registered.values())
        rr=[]
        for tr in b['trace']:
            kb=compact(k);old=copy.deepcopy(ctrl.table.recipes);old_names=names(old);delta=k.observe(tr['after'],tr['action'],cutoff=tr['after']['step'],
                source={'stage':stage,'state_id':sid,'candidate_id':cid,'index':tr['index'],'kind':kind})
            ctrl.observe(tr['before'],tr['action'],tr['after']);after=copy.deepcopy(ctrl.table.recipes)
            new_keys=sorted((names(after)-initial_k2)&keys)
            assert new_keys==tr['new_key_recipes'],(stage,sid,cid,tr['index'])
            for n in names(after):first_registered.setdefault(n,tr['after']['step'])
            known_before=set(n for n,f in kb.items() if f['ingredients']);registered_new=names(after)-old_names
            repeated=sorted(registered_new&(known_before-old_names)) if parse_action(tr['action']).verb=='inspect' and not delta['new_relations'] and not delta['quantity_updates'] and not delta['station_updates'] else []
            rr.append({'index':tr['index'],'action':tr['action'],'step':tr['after']['step'],'raw_feedback':tr['feedback'],
                'K1_before':kb,'K2_before':old,'K2_after':after,'K1_delta':delta,'K2_new_registered_relations':sorted(registered_new),
                'public_but_unregistered_after':absent(k,after),'quantity_missing_or_different':quantity_gaps(k,after),
                'new_K1_necessary_cumulative':sorted((set(k.relations())-initial_k1)&keys),
                'new_K2_necessary_cumulative':new_keys,'registration_only_reinspection':repeated,
                'state_hash':tr['state_hash'],'source_before_digest':digest(tr['before']),'source_after_digest':digest(tr['after'])})
        row={'stage':stage,'state_id':sid,'candidate_id':cid,'kind':kind,'source_trace_digest':digest(b['trace']),
            'rows':rr,'new_K1_necessary':sorted((set(k.relations())-initial_k1)&keys),
            'new_K2_necessary':b['new_key_recipes'],'api_calls':0}
        branch_records.append(row)
        run=summarize_run(stage,'saved_branch',sid+'/'+cid+'/'+kind,parse_action(s['public_view']['target_action']).target,k,
            ctrl.table.recipes,b['trace'][-1]['after']['step'] if b['trace'] else s['observation']['step'],first_registered,keys,rr)
        branch_runs.append(run)
    save_records(ROOT/'branch_knowledge_timeline.jsonl.gz',branch_records);atomic_json(ROOT/'branch_knowledge_summary.json',branch_runs)
    save_records(ROOT/'episode_knowledge_events.jsonl.gz',all_events)
    groups=collections.defaultdict(lambda:collections.Counter())
    for e in all_events:
        for label in ['stage:'+str(e['stage']), 'family:'+e['family'],'verb:'+parse_action(e['source_action'] or '').verb,'format:'+e['format']]:
            groups[label]['disclosure_events']+=1;groups[label]['new_relations']+='new_relation' in e['changes'];groups[label]['quantity_updates']+='explicit_quantities_added' in e['changes'];groups[label]['station_updates']+='required_station_added' in e['changes'];groups[label]['repeat_only_events']+=e['changes']==['repeated_disclosure']
    # Terminal gaps attributed to the first disclosure of each recipe per run;
    # quantitative gaps separately attributed to the first numeric disclosure.
    runmap={r['task_id']:r for r in runs};attribution=collections.defaultdict(lambda:collections.Counter())
    for e in all_events:
        run=runmap[e['task_id']];name=e['product']
        for label in ['verb:'+parse_action(e['source_action'] or '').verb,'format:'+e['format']]:
            g=attribution[label]
            if 'new_relation' in e['changes']:
                g['public_relations']+=1
                g['finally_registered']+=name not in run['never_registered']
                g['never_registered']+=name in run['never_registered']
                delay=next(d for d in run['delays'] if d['recipe']==name)
                if delay['delay_environment_steps'] is not None:
                    g['registered_delay_sum']+=delay['delay_environment_steps'];g['registered_delay_samples']+=1
                else:g['right_censored']+=1
            if 'explicit_quantities_added' in e['changes']:
                g['explicit_quantity_first_disclosures']+=1
                g['quantity_missing_or_different_final']+=name in run['quantity_missing_or_different']
    atomic_json(ROOT/'disclosure_registration_by_format_action.json',dict(attribution))
    summary={'formal':aggregate_runs(runs),'branch_repetitions_separate':aggregate_runs(branch_runs),
        'formal_disclosure_events_by_group':dict(groups),'formal_episodes':90,'formal_actions':2837,
        'stage12_branches':len(old12) and sum(len(r['branches']) for r in old12),'stage13_branches':len(old13),
        'matched_primary_requests':sum(r['matched_primary'] for r in request_audit),
        'historical_missing_reclassified_episodes':sum(bool(r['historical_missing_but_actually_disclosed']) for r in runs),
        'historical_missing_reclassified_relations':sum(len(r['historical_missing_but_actually_disclosed']) for r in runs),
        'public_but_reported_unknown_decisions':sum(bool(r['needed_public_but_reported_UNKNOWN']) for r in timeline),
        'K1_missing_from_K2_but_available_to_model_decisions':sum(bool(set(r['public_but_unregistered_before'])&set(r['K3']['available_in_prompt_or_summary'])) for r in timeline),
        'not_independent_samples':'same families, repeated timepoints and counterfactual branches; no iid significance or corrected R@40 claims'}
    atomic_json(ROOT/'knowledge_statistics.json',summary)
    # Independent annotation accuracy: sets of exact relation/quantity/station facts.
    gold=load(ROOT/'parser_gold.json');checks=[];tp=fp=fn=0
    for row in gold['rows']:
        fs,amb=extract(row['observation'],row['action']);expected=row['expected']
        got={(f['product'],tuple(sorted(f['ingredients']))) for f in fs if f['ingredients']}
        wanted={(n,tuple(sorted(v))) for n,v in expected['recipes'].items()}
        tp+=len(got&wanted);fp+=len(got-wanted);fn+=len(wanted-got)
        checks.append({'id':row['id'],'relations_exact':got==wanted,
            'quantities_exact':{f['product']:f['quantities'] for f in fs if f['quantities']}==expected['quantities'],
            'stations_exact':{f['product']:f['stations'] for f in fs if f['stations']}==expected['stations'],'ambiguous':amb})
    atomic_json(ROOT/'parser_validation.json',{'native_feedbacks':len(checks),'checks':checks,'true_positive_relations':tp,
        'false_positive_relations':fp,'false_negative_relations':fn,'precision':tp/(tp+fp),'recall':tp/(tp+fn),
        'passed':all(r['relations_exact'] and r['quantities_exact'] and r['stations_exact'] and not r['ambiguous'] for r in checks),
        'single_analyst_manual_labels_not_external_blind_validation':True})
    print(json.dumps({k:v for k,v in summary.items() if k not in ['formal','branch_repetitions_separate','formal_disclosure_events_by_group']},ensure_ascii=False))

if __name__=='__main__':main()
