"""Recompute all Stage 5 results from committed trajectories, no model calls."""
import argparse
from collections import Counter,defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np
from scar.io import atomic_json,read_jsonl,digest


METHODS=['ShortTermMemoryAgent','SimpleFailureRecovery','SCARV3Agent','ResourceFIFO','SRP']


def divide(a,b):return a/b if b else None


def bootstrap(values,clusters=None):
    if not values:return {'difference':None,'ci95':None,'n':0}
    if clusters is not None:
        grouped=defaultdict(list)
        for c,x in zip(clusters,values):grouped[c].append(x)
        values=[float(np.mean(v)) for v in grouped.values()]
    a=np.asarray(values,dtype=float);rng=np.random.default_rng(20261012)
    means=a[rng.integers(len(a),size=(10000,len(a)))].mean(axis=1)
    return {'difference':float(a.mean()),'ci95':[float(x) for x in np.quantile(means,[.025,.975])],'n':len(a)}


def episode_metrics(summary,rows,case,resource_records=None):
    recovery=next((i+1 for i,r in enumerate(rows) if r['diagnostic_goal_reached']),None)
    first=rows[0]['physical_before'] if rows else None
    last=rows[-1]['physical_after'] if rows else None
    graph=case.get('recipe_graph',{})
    completed=set();conditions=set();accum=set();loops=[];seen={}
    initial_crafted=first['crafted'] if first else {}
    last_completed=0
    for i,row in enumerate(rows):
        before,after=row['physical_before'],row['physical_after'];m=row['objective_metrics']
        for oid in graph:
            if after['crafted'].get(oid,0)>initial_crafted.get(oid,0):completed.add(oid)
            if all(after['conditions'][oid]['ingredients'].values()):accum.add(oid)
        conditions.update(oid for oid,c in after['conditions'].items() if all(v for g in c.values() for v in g.values()))
        key=m['resource_hash_after']
        if m['transfer_action'] and key in seen and len(completed)==seen[key][1]:
            previous=seen[key][0]
            if not any(r['diagnostic_goal_reached'] for r in rows[previous:i+1]):
                loops.append({'from_index':previous,'to_index':i,'resource_hash':key,
                              'scope':'physical resource cycle, no new craft milestone; information gain not excluded'})
        seen[key]=(i,len(completed));last_completed=len(completed)
    labelled=[r for r in rows if r.get('proposed_truth') is not None]
    harmful_goal=[];harmful_delta=[];improved=[]
    for r in labelled:
        cf=r['proposed_effect']['physical_state'];actual=r['physical_after'];before=r['physical_before']
        if cf['goal'] and not actual['goal']:harmful_goal.append(r['index'])
        name=case['goal'].get('name')
        if case['goal']['kind']=='possess':
            if cf['accessible'].get(name,0)>actual['accessible'].get(name,0):harmful_delta.append(r['index'])
        elif cf['tutorial_stage']>actual['tutorial_stage']:harmful_delta.append(r['index'])
        if r['objective_metrics']['physical_goal_delta']>0 or r['objective_metrics']['conditions_released']>0:improved.append(r['index'])
    plan_clear=[{'index':r['index'],'event':e} for r in rows for e in r.get('events',[]) if e.get('event')=='plan_invalidated']
    raw_destroyed=[{'index':r['index'],'action':r['executed_action'],'items':r['objective_metrics']['unaccounted_resource_destruction']} for r in rows if r['objective_metrics']['unaccounted_resource_destruction']]
    destroyed=([{'index':r['index'],'action':r['action'],'items':r['environment_quantity_destruction']} for r in resource_records if r['environment_quantity_destruction']] if resource_records is not None else raw_destroyed)
    result={'case_id':case['id'],'family':case['family'],'game':case['game'],'kind':case['kind'],
        'source_cluster':case['source_cluster'],'mechanism_cluster':case['mechanism_cluster'],'knowledge':case['knowledge'],
        'algorithm':summary['algorithm'],'status':summary['status'],'error':summary.get('error'),
        'steps':len(rows),'recovery_steps':recovery,
        **{f'recovery_at_{k}':recovery is not None and recovery<=k for k in [10,20,40]},
        **{k:summary.get(k,0) for k in ['cost_usd','conservative_cost_usd','input_tokens','output_tokens','api_calls','failed_requests','http_429']},
        'semantic_rejections':sum(r['semantic_rejection'] for r in rows),
        'dependency_tests':sum(r['objective_metrics']['craft_condition_test'] for r in rows),
        'dependency_violations':sum(r['objective_metrics']['dependency_violation'] for r in rows),
        'subgoal_total':len(graph),'subgoal_completed':len(completed),'completed_recipe_nodes':sorted(completed),
        'material_accumulation_nodes':len(accum),'condition_released_nodes':len(conditions),
        'container_access_tests':sum(r['objective_metrics']['container_access_test'] for r in rows),
        'container_access_errors':sum(r['objective_metrics']['container_access_error'] for r in rows),
        'false_carried_claims':sum(len(r['objective_metrics']['false_carried_claims']) for r in rows),
        'resource_destruction_steps':len(destroyed),'resource_destruction':destroyed,
        'raw_nominal_loss_steps':len(raw_destroyed),'exact_resource_audit_applied':resource_records is not None,
        'temporary_access_loss_records':sum(len(r['temporary_access_loss']) for r in resource_records) if resource_records is not None else None,
        'resource_cycles':len(loops),'cycle_evidence':loops,
        'plan_clear_count':len(plan_clear),'plan_clear_evidence':plan_clear,
        'proven_premature_plan_invalidations':None,
        'interventions':len(labelled),
        'legal_to_rejected':sum(not r['proposed_truth']['semantic_rejection'] and r['semantic_rejection'] for r in labelled),
        'rejected_to_legal':sum(r['proposed_truth']['semantic_rejection'] and not r['semantic_rejection'] for r in labelled),
        'interventions_physical_progress':len(improved),'intervention_progress_indices':improved,
        'harmful_goal_overrides':len(harmful_goal),'harmful_goal_indices':harmful_goal,
        'harmful_target_quantity_overrides':len(harmful_delta),'harmful_quantity_indices':harmful_delta,
        'target_condition_releases':sum(r.get('target_condition_release',False) for r in rows),
        'goal_switches_observed':sum(r['physical_after']['tutorial_stage']>r['physical_before']['tutorial_stage'] for r in rows)}
    return result


def aggregate(rows):
    n=len(rows);success=sum(r['recovery_at_40'] for r in rows);steps=sum(r['steps'] for r in rows)
    sums={k:sum(r[k] for r in rows) for k in ['cost_usd','conservative_cost_usd','input_tokens','output_tokens','api_calls',
        'semantic_rejections','dependency_tests','dependency_violations','subgoal_total','subgoal_completed',
        'material_accumulation_nodes','container_access_tests','container_access_errors','false_carried_claims',
        'resource_destruction_steps','resource_cycles','plan_clear_count','interventions','legal_to_rejected','rejected_to_legal',
        'interventions_physical_progress','harmful_goal_overrides','harmful_target_quantity_overrides','target_condition_releases']}
    familymean=lambda numerator,denominator:float(np.mean([r[numerator]/r[denominator] for r in rows if r[denominator]])) if any(r[denominator] for r in rows) else None
    return {'n':n,'successes':success,'steps':steps,**{f'recovery_at_{k}':divide(sum(r[f'recovery_at_{k}'] for r in rows),n) for k in [10,20,40]},
        'mean_success_steps':statistics.mean([r['recovery_steps'] for r in rows if r['recovery_steps'] is not None]) if success else None,
        'cost_per_success_all_attempts':divide(sums['cost_usd'],success),
        'tokens_per_success_all_attempts':divide(sums['input_tokens']+sums['output_tokens'],success),
        'semantic_rejection_rate':divide(sums['semantic_rejections'],steps),
        'dependency_violation_rate':divide(sums['dependency_violations'],sums['dependency_tests']),
        'family_mean_subgoal_completion':familymean('subgoal_completed','subgoal_total'),
        'family_mean_material_accumulation':familymean('material_accumulation_nodes','subgoal_total'),
        'container_access_error_rate':divide(sums['container_access_errors'],sums['container_access_tests']),
        'harmful_goal_override_rate':divide(sums['harmful_goal_overrides'],sums['interventions']),
        'proven_premature_plan_invalidations':None,**sums}


def analyze(runtime,output):
    root=Path(runtime);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    tasks=json.loads((root/'tasks.json').read_text())
    cases={c['id']:c for c in json.loads((out/'dataset/cases.json').read_text())}
    complete=[];missing=[];summaries=[]
    gz={m:gzip.open(out/f'trajectories_{m}.jsonl.gz','wt') for m in METHODS}
    mechanisms=[]
    resource_audits=defaultdict(list)
    if (out/'resource_audit.jsonl.gz').exists():
        with gzip.open(out/'resource_audit.jsonl.gz','rt') as f:
            for r in map(json.loads,f):resource_audits[r['task_id']].append(r)
    for task in tasks:
        folder=root/'runs'/task['task_id'];path=folder/'summary.json'
        if not path.exists():missing.append({'task_id':task['task_id'],'reason':'no_summary'});continue
        s=json.loads(path.read_text())
        if s['status'] not in {'completed','method_abort'}:
            missing.append({'task_id':task['task_id'],'reason':s['status'],'error':s.get('error')});continue
        rows=[json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))]
        case=cases[task['id']];metrics=episode_metrics(s,rows,case,resource_audits.get(task['task_id']));complete.append(metrics);summaries.append(s)
        gz[task['algorithm']].write(json.dumps({'task_id':task['task_id'],'case_id':task['id'],'summary':metrics,'rows':rows},ensure_ascii=False)+'\n')
        # Complete family-level action sequences, not selectively reported anecdotes.
        mechanisms.append({'task_id':task['task_id'],'case_id':task['id'],'algorithm':task['algorithm'],
            'knowledge':case['knowledge'],'kind':case['kind'],'success':metrics['recovery_at_40'],
            'actions':[{'index':r['index'],'proposed':r['proposed_action'],'actual':r['executed_action'],
                'rejected':r['semantic_rejection'],'feedback':r.get('action_rule_feedback'),
                'public_environment_feedback':r['next_observation']['text'],
                'goal':r['diagnostic_goal_reached'],'metrics':r['objective_metrics']} for r in rows],
            'error':s.get('error')})
    for f in gz.values():f.close()
    atomic_json(out/'completion.json',{'expected':len(tasks),'completed':len(complete),'incomplete':missing,
         'fully_complete':not missing and len(complete)==len(tasks),'statuses':dict(Counter(r['status'] for r in complete))})
    atomic_json(out/'episode_metrics.json',complete)
    atomic_json(out/'all_summaries.json',summaries)
    with gzip.open(out/'mechanism_evidence.jsonl.gz','wt') as f:
        for r in mechanisms:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    grouped={}
    scopes={'all':lambda r:True,'craft':lambda r:r['kind']=='craft',
        'known_craft':lambda r:r['kind']=='craft' and r['knowledge']=='demonstrated_rules',
        'unknown_craft':lambda r:r['kind']=='craft' and r['knowledge']=='interaction_discovery',
        'locks':lambda r:r['kind']=='lock_release','goal_switch':lambda r:r['kind']=='goal_switch'}
    for game in ['saltglass','quarantine','robot_kingdom']:
        scopes[game]=lambda r,g=game:r['game']==g
    for scope,predicate in scopes.items():
        grouped[scope]={m:aggregate([r for r in complete if r['algorithm']==m and predicate(r)]) for m in METHODS}
    atomic_json(out/'method_metrics.json',grouped)
    comparisons=[]
    for scope,predicate in scopes.items():
        selected={m:{r['family']:r for r in complete if r['algorithm']==m and predicate(r)} for m in METHODS}
        for a,b in [('SRP','ResourceFIFO'),('SRP','ShortTermMemoryAgent'),('ResourceFIFO','ShortTermMemoryAgent'),('SRP','SCARV3Agent')]:
            families=sorted(set(selected[a])&set(selected[b]));deltas=[int(selected[a][f]['recovery_at_40'])-int(selected[b][f]['recovery_at_40']) for f in families]
            comparisons.append({'scope':scope,'a':a,'b':b,'paired_family':bootstrap(deltas),
                'source_cluster':bootstrap(deltas,[selected[a][f]['source_cluster'] for f in families]),
                'mechanism_cluster':bootstrap(deltas,[selected[a][f]['mechanism_cluster'] for f in families]),
                'a_only':sum(x==1 for x in deltas),'b_only':sum(x==-1 for x in deltas),
                'same':sum(x==0 for x in deltas)})
    atomic_json(out/'paired_comparisons.json',comparisons)
    atomic_json(out/'metric_definitions.json',{
        'primary':'Recovery@40, full frozen family denominator; method abort failures included. Incomplete infrastructure tasks block final conclusions.',
        'subgoal_completion':'Fraction of predeclared recipe nodes crafted at least once AFTER initial snapshot. Histories do not count as new completion; partial count per family.',
        'material_accumulation':'Fraction of recipe nodes whose one-copy ingredient conditions were simultaneously physically satisfied at least once.',
        'dependency_violation':'Executed craft attempts missing actual recipe inputs or workstation; includes deliberate discovery probes, not necessarily controller defects.',
        'container_access_error':'Store/take-out/discard references inaccessible known physical container. Unknown names and other semantic errors are separate; claiming inventory with another merely-held container can evade this conservative check.',
        'resource_destruction':'Post-hoc exact original action-only dispatch vs committed full step; world census includes NPC inventories. Nominal fractional-consumption raw flags retained separately. Actual destroyed units do not prove permanent task failure.',
        'resource_cycles':'Return after resource-transfer action to a previously seen evaluator resource configuration without newly crafted recipe milestone; information gain not excluded.',
        'plan_invalidations':'Raw V3 plan_invalidated events; correctness and continued relevance of discarded plan not established, so PROVEN premature invalidation is NA.',
        'harmful_override':'One-step same-state base counterfactual physically achieves goal and actual override does not. Also report a weaker target-quantity/stage difference; no long-term harm claim.',
        'temporary_loss':'Drop/store location and carried access retained in every physical_before/after record. Drops are not counted as permanent loss.',
        'statistical_unit':'One paired family; state/step totals descriptive only. Bootstrap by family plus source/mechanism sensitivity. Only three source-game clusters; low precision.',
        'knowledge_strata':'Demonstration availability not randomized among surviving valid scenarios; game, recipe and history lengths differ. Stratum gaps are descriptive, not a causal online-learning effect.'})
    # Deterministic next-stage decision; require task evidence, not complexity.
    judgments={'complete':not missing,'go_for_full_v4':False,'verdict':'PENDING' if missing else 'NO-GO',
        'h1':'Needs independent paired closed-loop evidence; pure condition and memory effects remain bundled.',
        'h2':'Assess FIFO and SRP paired task recovery against STM, together with costs.',
        'h3':'Unknown-stratum failures and native dynamic events identify hypotheses only; no new online-learning method has been compared.'}
    if not missing:
        srp=grouped['all']['SRP'];fifo=grouped['all']['ResourceFIFO'];stm=grouped['all']['ShortTermMemoryAgent']
        if fifo['successes']>=srp['successes']-1:
            judgments.update(verdict='NO-GO for added planner/learning complexity',situation='A',
                reason='FIFO is within one paired family of or exceeds SRP. This is descriptive proximity, not a powered equivalence test.')
        elif srp['successes']<stm['successes'] and fifo['successes']<stm['successes']:
            judgments.update(verdict='NO-GO for V4; inspect STM exploration and feedback use',situation='D',
                reason='Both structured methods remain below STM in task recovery.')
        else:
            diff=next(c for c in comparisons if c['scope']=='known_craft' and c['a']=='SRP' and c['b']=='ResourceFIFO')
            known=grouped['known_craft']['SRP']['recovery_at_40'];unknown=grouped['unknown_craft']['SRP']['recovery_at_40']
            judgments.update(verdict='PARTIAL; deterministic planning worth further isolation',situation='B/C not causally separated',
                reason='A task-level numerical gain exists, but components and knowledge strata are confounded.',
                known_minus_unknown=None if known is None or unknown is None else known-unknown,
                known_srp_minus_fifo=diff['paired_family'])
        judgments.update(h1='PARTIAL: structured persistent memory plus execution control improves this frozen cohort, but memory, planning, and exploration are not separately identified; source-cluster sensitivity remains important.',
            h2=f'Supported within this cohort: FIFO {fifo["successes"]}/{fifo["n"]}, SRP {srp["successes"]}/{srp["n"]}, STM {stm["successes"]}/{stm["n"]}. Not a cross-game universal claim.',
            h3='NOT IDENTIFIED: unknown-stratum degradation exists, but quantity/batch exploration, deterministic implementation limitations and game effects remain alternatives to needing new learning.',
            next_algorithm='NO-GO for full V4. At most a small isolated test of context/batch-dependent effect hypotheses against an equally informed deterministic batch-rule baseline, on newly frozen states.')
    atomic_json(out/'research_judgment.json',judgments)
    fields=['scope','algorithm','n','successes','recovery_at_10','recovery_at_20','recovery_at_40','mean_success_steps',
        'cost_usd','cost_per_success_all_attempts','semantic_rejection_rate','dependency_violation_rate',
        'family_mean_subgoal_completion','family_mean_material_accumulation','resource_cycles','resource_destruction_steps']
    with (out/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for scope,data in grouped.items():
            for method,r in data.items():w.writerow({k:({'scope':scope,'algorithm':method}|r).get(k) for k in fields})
    return {'complete':not missing,'episodes':len(complete),'expected':len(tasks),'judgment':judgments}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',default='results/sequence')
    a=p.parse_args();print(json.dumps(analyze(a.runtime,a.output),ensure_ascii=False))
