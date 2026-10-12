"""Separate historical regression / unseen task cohorts, with paired outcomes."""
import argparse,collections,csv,gzip,json,statistics,re
from pathlib import Path
from scar.io import atomic_json,digest
from scar_sequence.analyze import episode_metrics,aggregate,bootstrap,divide
from scar_unknown17.analyze import mechanism_metrics,grouped_extra
from scar_unknown17_stage7.analyze import stage7_metrics,group_stage7
from scar_stage8.controller import METHODS,ReliableController,restore_controller
from scar_v3.state import parse_action
OUT=Path('results/stage8')

def reliability(rows,case):
    repeats=[];seen={};redundant=[];capacity=[];limits=[];inspections=[];lost=[];states=[];active=[]
    last_queue=None;last_sig=None
    for r in rows:
        s=r['stage7_state_before'];ctrl=ReliableController.from_dict(s);ctrl.table.observe(r['observation']);t=ctrl.table
        p=parse_action(r['executed_action']);signature=digest([ctrl.failure_key(r['executed_action']),ctrl.action_context(r['executed_action'])])
        if p.verb=='pick up' and r['semantic_rejection']:
            if signature in seen:repeats.append({'index':r['index'],'previous':seen[signature],'action':r['executed_action']})
            seen[signature]=r['index']
        if p.verb=='craft' and 'successfully crafted' in r['action_rule_feedback']:
            post=restore_controller(s);post.choose(r['observation'],r['proposed_action'])
            need=post.public_demand(p.target);own=t.count(p.target) or 0;ground=(t.state.get('ground') or {}).get(p.target,0)
            if own>=need or own+ground>=need and ground>0:
                redundant.append({'index':r['index'],'action':r['executed_action'],'own':own,'ground':ground,'public_need':need,
                    'scope':'public sufficient-copy signal; possible mirage/container uncertainty, see engine opportunity audit for verified material loss'})
            after=next((x['index'] for x in rows[r['index']+1:] if parse_action(x['executed_action']).verb=='inspect' and parse_action(x['executed_action']).target==p.target and not x['semantic_rejection']),None)
            inspections.append({'index':r['index'],'product':p.target,'next_inspect':after,'within3':after is not None and after-r['index']<=3,'censored':after is None})
        if r['semantic_rejection'] and re.search(r'hand|space|capacity|inventory|container',r['action_rule_feedback'],re.I):capacity.append({'index':r['index'],'action':r['executed_action'],'feedback':r['action_rule_feedback']})
        safety=r.get('structured',{}).get('safety',{})
        if safety.get('search_limits') or safety.get('candidate_limit_reached'):limits.append({'index':r['index'],'safety':safety})
        resource=ctrl._signature()
        if last_queue and not s.get('queue') and resource==last_sig:lost.append(r['index'])
        last_queue=r.get('structured',{}).get('queue');last_sig=resource
        states.append(len(json.dumps(s,ensure_ascii=False).encode()))
        heavy={'events','attempt_log','gap_log','mode_log','batch_decisions','last_choice','stage7_decision','safety_decision','quantity_facts','table'}
        active.append(len(json.dumps({k:v for k,v in s.items() if k not in heavy and v},ensure_ascii=False).encode()))
    return {'repeated_rejected_pickups':len(repeats),'repeated_pickup_records':repeats,
        'public_sufficient_copy_crafts':len(redundant),'sufficient_copy_records':redundant,
        'capacity_errors':len(capacity),'capacity_error_records':capacity,'generation_limit_events':len(limits),'generation_limit_records':limits,
        'new_product_inspection_records':inspections,'new_products_inspected_within3':sum(x['within3'] for x in inspections),
        'new_products_total':len(inspections),'unrelated_queue_clear_count':len(lost),'unrelated_queue_clear_indices':lost,
        'mean_controller_checkpoint_bytes':statistics.mean(states) if states else 0,'mean_active_control_bytes':statistics.mean(active) if active else 0,
        'actual_wait_actions':sum(r['executed_action']=='wait' for r in rows),
        'safe_no_candidate_steps':sum(r.get('structured',{}).get('safety',{}).get('no_candidate',False) for r in rows)}

def rel_group(rs):
    fields=['repeated_rejected_pickups','public_sufficient_copy_crafts','capacity_errors','generation_limit_events','new_products_inspected_within3','new_products_total','unrelated_queue_clear_count','safe_no_candidate_steps','actual_wait_actions','method_abort','recursion_abort','format_abort']
    return {k:sum(r[k] for r in rs) for k in fields}|{'mean_controller_checkpoint_bytes':statistics.mean(r['mean_controller_checkpoint_bytes'] for r in rs) if rs else 0,
        'mean_active_control_bytes':statistics.mean(r['mean_active_control_bytes'] for r in rs) if rs else 0}

def main(runtime):
    root=Path(runtime);tasks=json.loads((root/'tasks.json').read_text());cases={c['id']:c for c in json.loads((OUT/'cases.json').read_text())}
    groups={k:collections.defaultdict(list) for k in ['resource_audit','batch_audit','opportunity_audit']}
    for name,g in groups.items():
        for r in map(json.loads,gzip.open(OUT/(name+'.jsonl.gz'),'rt')):g[r['task_id']].append(r)
    catalog=json.loads((OUT/'truth_catalog_evaluation_only.json').read_text());metrics=[];summaries=[];incomplete=[]
    handles={m:gzip.open(OUT/f'trajectories_{m}.jsonl.gz','wt') for m in METHODS}
    for task in tasks:
        folder=root/'runs'/task['task_id'];path=folder/'summary.json'
        if not path.exists():incomplete.append({'task_id':task['task_id'],'status':'missing'});continue
        s=json.loads(path.read_text())
        if s['status'] not in {'completed','method_abort'}:incomplete.append({'task_id':task['task_id'],'status':s['status']});continue
        c=cases[task['id']];rows=[json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))]
        rr=groups['resource_audit'][task['task_id']];bb=groups['batch_audit'][task['task_id']]
        m=episode_metrics(s,rows,c,rr);m.update(mechanism_metrics(c,rows,catalog[c['id']],bb))
        m.update(stage7_metrics(c,rows,groups['opportunity_audit'][task['task_id']],{r['index']:r for r in rr}));m.update(reliability(rows,c))
        m.update(cohort=c['cohort'],method_abort=s['status']=='method_abort',recursion_abort='RecursionError' in (s.get('error') or ''),format_abort='ModelResponseError' in (s.get('error') or ''),error=s.get('error'),observed_actions_before_stop=len(rows))
        final=rows[-1]['physical_after'] if rows else {};recipe=c['recipe_graph'][c['goal']['object_id']]
        m['failure_context']={'kind':'success' if m['recovery_at_40'] else 'method_abort' if m['method_abort'] else 'missing_knowledge' if m['missing_key_recipes'] else 'known_names_execution_or_resources',
            'goal_owned':final.get('accessible',{}).get(c['goal']['name']),
            'final_root_inputs_evaluator_only':{c['object_names'][o]:{'nominal_need':n,'owned':final.get('accessible',{}).get(c['object_names'][o],0)} for o,n in recipe['ingredients'].items()},
            'scope':'local terminal state, not proof of irreversible impossibility or hidden-rule necessity'}
        for record in m['recipe_conversion_records']:record.update(observed_followup_actions=max(0,len(rows)-record['discovered_after_action']),early_method_abort=m['method_abort'])
        metrics.append(m);summaries.append(s)
        handles[task['algorithm']].write(json.dumps({'task_id':task['task_id'],'case_id':c['id'],'summary':m,'rows':rows},ensure_ascii=False)+'\n')
    for f in handles.values():f.close()
    atomic_json(OUT/'completion.json',{'expected':len(tasks),'completed':len(metrics),'incomplete':incomplete,'fully_complete':len(metrics)==len(tasks) and not incomplete,'statuses':dict(collections.Counter(x['status'] for x in metrics))})
    atomic_json(OUT/'episode_metrics.json',metrics);atomic_json(OUT/'all_summaries.json',summaries)
    scopes={cohort:{cid for cid,c in cases.items() if c['cohort']==cohort} for cohort in ['regression','new']}
    overlap=json.loads((OUT/'extended_overlap_audit.json').read_text())['records']
    scopes['new_structure_novel_sensitivity']={r['case_id'] for r in overlap if not r['anonymous_shape_matches_prior_targets']}
    for g in sorted({c['game'] for c in cases.values()}):scopes['new_'+g]={cid for cid,c in cases.items() if c['cohort']=='new' and c['game']==g}
    grouped={scope:{method:aggregate(rs)|grouped_extra(rs)|group_stage7(rs)|rel_group(rs) for method in METHODS
        for rs in [[r for r in metrics if r['algorithm']==method and r['case_id'] in ids]]} for scope,ids in scopes.items() if ids}
    atomic_json(OUT/'method_metrics.json',grouped)
    by={m:{r['case_id']:r for r in metrics if r['algorithm']==m} for m in METHODS};pairs=[]
    for scope,ids0 in scopes.items():
        if not ids0:continue
        for a,b in [('P4','P2'),('P3','P1'),('P4','P3'),('P3','P0'),('P4','P0'),('P2','P1')]:
            ids=sorted(ids0&by[a].keys()&by[b].keys());d=[int(by[a][x]['recovery_at_40'])-int(by[b][x]['recovery_at_40']) for x in ids]
            pairs.append({'scope':scope,'a':a,'b':b,'family':bootstrap(d),'source_cluster':bootstrap(d,[cases[x]['game'] for x in ids]),
                'a_only':[x for x,v in zip(ids,d) if v==1],'b_only':[x for x,v in zip(ids,d) if v==-1],
                'cost_difference':bootstrap([by[a][x]['cost_usd']-by[b][x]['cost_usd'] for x in ids])})
    atomic_json(OUT/'paired_comparisons.json',pairs)
    families=[]
    for cid,c in cases.items():
        es={m:by[m].get(cid) for m in METHODS}
        families.append({'case_id':cid,'cohort':c['cohort'],'target':c['goal']['name'],'game':c['game'],
            'successes':{m:r['recovery_at_40'] if r else None for m,r in es.items()},'evidence':es})
    atomic_json(OUT/'family_comparison.json',families)
    fields=['scope','algorithm','n','successes','recovery_at_10','recovery_at_20','recovery_at_40','mean_success_steps','steps','cost_usd','cost_per_success_all_attempts','key_discovery_rate','intermediate_discovery_rate','harmful_goal_overrides','legal_to_rejected','avoidable_reserve_depletion','repeated_rejected_pickups','public_sufficient_copy_crafts','capacity_errors','generation_limit_events','method_abort']
    with (OUT/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader()
        for scope,group in grouped.items():
            for m,r in group.items():w.writerow({k:({'scope':scope,'algorithm':m}|r).get(k) for k in fields})
    atomic_json(OUT/'metric_definitions.json',{'cohorts':'regression Robot10; new distinct target+anonymous weighted graph per predeclared selection; never pooled as improvement over old scores',
        'randomness':'single physical seed; nonzero model temperature; differences not automatically mechanism causality',
        'repeated_pickup':'rejected same action on same relevant observable target/location/hand conditions, ignores clock',
        'sufficient_copy_craft':'public owned+ground>=public demand, actual productive craft; public signals may be deceptive, not an oracle claim of legality',
        'resource_loss':'exact native action consumption and complete step separately, compare smaller production and legal preexisting acquisition; inherited Stage7 criterion',
        'conversion':'per recipe discovery→first effective craft; never-discovered and censored at40 explicitly separated',
        'new_product_inspection':'first successful inspect of produced item in next3actions; may be unnecessary if already known',
        'plan_loss':'FIFOqueue becomes empty without public resource change between recorded decisions; narrow detectable proxy, not all plan-quality failures',
        'state_size':'JSONbytes full controller and active non-log subset; representation metric, not theoretical complexity or CPU proof',
        'scope':'synthetic task/state generalization within3previously used sourcegames; few clusters, no robust broad crossgame claim'})
    print(json.dumps({'complete':len(metrics),'successes':{scope:{m:r['successes'] for m,r in group.items()} for scope,group in grouped.items()},'new_cost_usd':sum(x['cost_usd'] for x in metrics)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();main(a.runtime)
