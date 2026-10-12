"""Recompute family-level results and evidence, never update frozen policies."""
import argparse
from collections import Counter,defaultdict,deque
import csv
import gzip
import json
from pathlib import Path
import re
from scar.io import atomic_json,read_jsonl
from scar_sequence.analyze import episode_metrics,aggregate,bootstrap,divide
from scar_sequence.public import ResourceTable
from scar_unknown17.agent import METHODS as PRIMARY_METHODS
METHODS=PRIMARY_METHODS+["STMFormatControl"]
from scar_unknown17.audit import known_recipes
from scar_v3.state import parse_action,PublicState


def public_recipe_names(text):
    return {x[0] for x in re.findall(r'([\w-]+) \(made of ([^)]+)\)',text)}


def mechanism_metrics(case,rows,catalog,batches):
    table=ResourceTable();key={case['object_names'][x] for x in case['recipe_graph']}
    intermediate=key-{case['goal']['name']};history=deque(maxlen=5)
    for h in case['history']:
        table.observe(h['before']);table.observe(h['after'],h['action'])
        history.append(h['before']['text']+'\n'+h['after']['text'])
    history.append('Recovery objective: '+case['public_goal'])
    initial_known=known_recipes(table)&key;ever=set(initial_known);events=[];info=[];newsteps=[]
    retention_num=retention_den=fact_correct=fact_checked=stale=summary_chars=summary_token_proxy=0
    summary_recipe_num=summary_recipe_den=0;facts_detail=[];repeated_info=[];inspected=set();crafted=[]
    for r in rows:
        i=r['index'];p=parse_action(r['executed_action']);before_known=known_recipes(table)&key
        summary=r.get('fact_summary') or {};rendered=summary.get('records',[])
        summary_chars+=summary.get('characters',0);summary_token_proxy+=summary.get('token_proxy_char_div4',0)
        summary_names={x['key'] for x in rendered if x['kind']=='recipe' and x['value']['ingredients']!='UNKNOWN'}
        prompt_names=set().union(*(public_recipe_names(t) for t in history))|summary_names|public_recipe_names(r['observation']['text'])
        controller_table=r.get('structured',{}).get('resource_table',{})
        controller_names={x for x,v in controller_table.get('recipes',{}).items() if v.get('ingredients')}
        retained=prompt_names|controller_names
        retention_num+=len(before_known&retained);retention_den+=len(before_known)
        if summary:
            summary_recipe_num+=len(before_known&summary_names);summary_recipe_den+=len(before_known)
        for fact in rendered:
            correct=None
            if fact['kind']=='recipe' and fact['value']['ingredients']!='UNKNOWN':
                correct=set(fact['value']['ingredients'])==set(catalog.get(fact['key'],{}).get('ingredients',[]))
            elif fact['kind']=='current':correct=fact['value']==ResourceTable().observe(r['observation']).state.get(fact['key'])
            elif fact['kind']=='goal':
                actual_owned=r['physical_before']['accessible'].get(case['goal']['name'],0)
                claimed=fact['value']['observed_owned_lower_bound']
                correct=(claimed is None or claimed<=actual_owned) and fact['value']['complete']==r['physical_before']['goal']
                if claimed is not None and claimed>actual_owned:stale+=1
            elif fact['kind']=='container':
                c=r['physical_before']['containers'].get(fact['key']);v=fact['value']
                if c:correct=v['carried_now']==c['carried'] and v['transfer_access_now']==c['transfer_accessible']
            if correct is not None:
                fact_checked+=1;fact_correct+=bool(correct)
                if not correct:facts_detail.append({'index':i,'fact':fact,'kind':'disagrees with physical/current/recipe truth'})
            # Historical counts/locations are explicitly marked historical. Do
            # not pretend absence of a current assertion proves absence of misuse.
        action_key=(p.verb,p.target)
        if p.verb=='inspect':
            if action_key in inspected:repeated_info.append({'index':i,'action':r['executed_action'],'scope':'repeated object inspection; state-dependent justification possible'})
            inspected.add(action_key)
        table.observe(r['observation']);table.observe(r['next_observation'],r['executed_action'])
        new=(known_recipes(table)&key)-ever;ever|=new
        new_public_all=public_recipe_names(r['next_observation']['text'])-public_recipe_names('\n'.join(history))
        probe=r.get('structured',{}).get('mechanisms',{}).get('exploration')
        if probe or p.verb=='inspect':
            info.append({'index':i,'action':r['executed_action'],'directed':bool(probe),'key_gains':sorted(new),
                'public_recipe_names':sorted(public_recipe_names(r['next_observation']['text'])),'probe':probe})
        if new:
            newsteps.append(i+1);events.append({'index':i,'event':'key_recipe_discovered','recipes':sorted(new),
                'action':r['executed_action'],'feedback':r['action_rule_feedback'],'directed':bool(probe)})
        if p.verb=='craft':crafted.append({'index':i,'target':p.target,'success':'successfully crafted' in r['action_rule_feedback']})
        history.append(r['observation']['text'])
    directed_used=[]
    for e in events:
        if e['directed']:
            for name in e['recipes']:
                if any(c['target']==name and c['success'] and c['index']>e['index'] for c in crafted):directed_used.append({'recipe':name,'discovery_index':e['index']})
    directed=[x for x in info if x['directed']]
    predictions=[b['prediction_l1_error'] for b in batches if b['prediction_l1_error'] is not None]
    failures=[]
    missing=sorted(key-ever)
    if missing:failures.append('F1')
    if any(not b['quantity_choice_non_dominated'] for b in batches):failures.append('F3')
    if any('space in hand' in r['action_rule_feedback'] for r in rows):failures.append('F4')
    if not any(r['diagnostic_goal_reached'] for r in rows):failures.append('F8')
    return {'key_recipe_total':len(key),'key_recipe_discovered':len(ever),
        'intermediate_recipe_total':len(intermediate),'intermediate_recipe_discovered':len(ever&intermediate),
        'initially_unknown_key_rules':len(key-initial_known),'unknown_to_supported':len(ever-initial_known),
        'first_key_discovery_step':min(newsteps) if newsteps else None,'missing_key_recipes':missing,
        'discovery_events':events,'information_actions':info,'directed_information_actions':len(directed),
        'directed_actions_without_immediate_key_gain':sum(not x['key_gains'] for x in directed),
        'directed_discovered_then_crafted':directed_used,
        'all_craft_states_audited':len(batches),
        'quantity_choices_audited':sum(any(v['actual_output']>0 for v in b['variants']) for b in batches),
        'quantity_choices_nondominated':sum(b['quantity_choice_non_dominated'] for b in batches if any(v['actual_output']>0 for v in b['variants'])),
        'quantity_prediction_count':len(predictions),'quantity_prediction_l1_sum':sum(predictions),
        'unknown_quantity_choices':sum((r.get('structured',{}).get('mechanisms',{}).get('batch') or {}).get('rule')=='fixed_deficit_or_two' for r in rows),
        'forward_trial_actions':sum((x['probe'] or {}).get('reason')=='bounded forward recipe trial' for x in directed),
        'retained_key_facts_numerator':retention_num,'retained_key_facts_denominator':retention_den,
        'summary_key_facts_numerator':summary_recipe_num,'summary_key_facts_denominator':summary_recipe_den,
        'summary_stale_owned_claims':stale,'summary_facts_correct':fact_correct,'summary_facts_checked':fact_checked,'summary_incorrect_facts':facts_detail,
        'historical_fact_misuse_proven':None,'summary_characters_total':summary_chars,'summary_token_proxy_total':summary_token_proxy,
        'repeated_inspection_count':len(repeated_info),'repeated_inspections':repeated_info,
        'hand_capacity_rejections':sum('space in hand' in r['action_rule_feedback'] for r in rows),
        'residual_observable_categories':failures,'final_goal_owned':rows[-1]['physical_after']['accessible'].get(case['goal']['name'],0) if rows else None}


def grouped_extra(rows):
    sums={k:sum(r[k] for r in rows) for k in ['key_recipe_total','key_recipe_discovered','intermediate_recipe_total','intermediate_recipe_discovered',
        'initially_unknown_key_rules','unknown_to_supported','directed_information_actions','directed_actions_without_immediate_key_gain',
        'all_craft_states_audited','quantity_choices_audited','quantity_choices_nondominated','quantity_prediction_count','quantity_prediction_l1_sum','unknown_quantity_choices',
        'forward_trial_actions','retained_key_facts_numerator','retained_key_facts_denominator','summary_key_facts_numerator','summary_key_facts_denominator',
        'summary_stale_owned_claims','summary_facts_correct','summary_facts_checked','summary_characters_total','summary_token_proxy_total','repeated_inspection_count','hand_capacity_rejections']}
    return sums|{'key_discovery_rate':divide(sums['key_recipe_discovered'],sums['key_recipe_total']),
        'intermediate_discovery_rate':divide(sums['intermediate_recipe_discovered'],sums['intermediate_recipe_total']),
        'retention_recall':divide(sums['retained_key_facts_numerator'],sums['retained_key_facts_denominator']),
        'summary_retention_recall':divide(sums['summary_key_facts_numerator'],sums['summary_key_facts_denominator']),
        'summary_fact_precision':divide(sums['summary_facts_correct'],sums['summary_facts_checked']),
        'quantity_nondominated_rate':divide(sums['quantity_choices_nondominated'],sums['quantity_choices_audited']),
        'quantity_prediction_mae':divide(sums['quantity_prediction_l1_sum'],sums['quantity_prediction_count']),
        'no_immediate_key_gain_rate':divide(sums['directed_actions_without_immediate_key_gain'],sums['directed_information_actions'])}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/unknown17')
    tasks=json.loads((root/'all_tasks.json').read_text());cases={c['id']:c for c in json.loads((out/'cases.json').read_text())}
    catalog=json.loads((out/'truth_catalog_evaluation_only.json').read_text());resources=defaultdict(list);batch=defaultdict(list)
    for name,group in [('resource_audit',resources),('batch_audit',batch)]:
        for r in map(json.loads,gzip.open(out/f'{name}.jsonl.gz','rt')):group[r['task_id']].append(r)
    summaries=[];metrics=[];missing=[];gzipfiles={m:gzip.open(out/f'trajectories_{m}.jsonl.gz','wt') for m in METHODS}
    for t in tasks:
        folder=root/'runs'/t['task_id'];path=folder/'summary.json'
        if not path.exists():missing.append({'task_id':t['task_id'],'reason':'missing summary'});continue
        s=json.loads(path.read_text())
        if s['status'] not in {'completed','method_abort'}:missing.append({'task_id':t['task_id'],'reason':s['status']});continue
        rows=[json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))]
        c=cases[t['id']];m=episode_metrics(s,rows,c,resources[t['task_id']])
        m.update(mechanism_metrics(c,rows,catalog[t['id']],batch[t['task_id']]))
        summaries.append(s);metrics.append(m)
        gzipfiles[t['algorithm']].write(json.dumps({'task_id':t['task_id'],'case_id':t['id'],'summary':m,'rows':rows},ensure_ascii=False)+'\n')
    for f in gzipfiles.values():f.close()
    atomic_json(out/'completion.json',{'expected':153,'completed':len(metrics),'fully_complete':len(metrics)==153 and not missing,
        'incomplete':missing,'statuses':dict(Counter(x['status'] for x in metrics))})
    atomic_json(out/'episode_metrics.json',metrics);atomic_json(out/'all_summaries.json',summaries)
    groups={}
    for scope in ['all','saltglass','quarantine','robot_kingdom']:
        groups[scope]={m:aggregate(rs)|grouped_extra(rs) for m in METHODS for rs in [[r for r in metrics if r['algorithm']==m and (scope=='all' or r['game']==scope)]]}
    old=json.loads((out/'attribution_summary.json').read_text())
    for category in ['F1','F3','F8']:
        ids={c['case_id'] for c in old if c['methods']['ResourceFIFO']['primary_observable_bottleneck']==category}
        groups['old_FIFO_'+category]={m:aggregate(rs)|grouped_extra(rs) for m in METHODS for rs in [[r for r in metrics if r['algorithm']==m and r['case_id'] in ids]]}
    atomic_json(out/'method_metrics.json',groups)
    by={m:{r['case_id']:r for r in metrics if r['algorithm']==m} for m in METHODS};paired=[]
    comparisons=[(m,'ResourceFIFO') for m in METHODS if m not in ['ResourceFIFO','ShortTermMemoryAgent']]+[
        ('STMFacts','ShortTermMemoryAgent'),('STMFacts','STMFormatControl'),('STMFormatControl','ShortTermMemoryAgent'),('FIFOCombined','FIFOExplore'),('FIFOCombined','FIFOBatch'),('FIFOCombined','FIFOFacts'),('FIFOBatch','FIFOFixedBatch')]
    for x,y in comparisons:
        ids=sorted(set(by[x])&set(by[y]));d=[int(by[x][c]['recovery_at_40'])-int(by[y][c]['recovery_at_40']) for c in ids]
        paired.append({'a':x,'b':y,'family':bootstrap(d),'source_cluster':bootstrap(d,[cases[c]['game'] for c in ids]),
            'a_only':[c for c,z in zip(ids,d) if z==1],'b_only':[c for c,z in zip(ids,d) if z==-1]})
    atomic_json(out/'paired_comparisons.json',paired)
    evidence=[]
    for cid,c in cases.items():
        winners=[m for m in METHODS if cid in by[m] and by[m][cid]['recovery_at_40']]
        evidence.append({'case_id':cid,'game':c['game'],'target':c['goal']['name'],'winners':winners,
            'combined_only':winners==['FIFOCombined'],'all_fail':not winners,
            'method_evidence':{m:{k:by[m][cid][k] for k in ['recovery_at_40','recovery_steps','cost_usd','missing_key_recipes',
                'directed_discovered_then_crafted','discovery_events','quantity_choices_audited','quantity_choices_nondominated',
                'summary_key_facts_numerator','summary_key_facts_denominator','residual_observable_categories']} for m in METHODS if cid in by[m]},
            'causal_limit':'same initial state does not pair remote model sampling; task-level gain alone is not mechanism necessity'})
    atomic_json(out/'family_comparison.json',evidence)
    fields=['scope','algorithm','n','successes','recovery_at_10','recovery_at_20','recovery_at_40','mean_success_steps','cost_usd',
        'cost_per_success_all_attempts','tokens_per_success_all_attempts','key_discovery_rate','intermediate_discovery_rate','quantity_nondominated_rate','retention_recall','summary_fact_precision']
    with (out/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader()
        for scope,data in groups.items():
            for method,r in data.items():w.writerow({k:({'scope':scope,'algorithm':method}|r).get(k) for k in fields})
    atomic_json(out/'metric_definitions.json',{
        'recovery':'physical frozen possession goal, full 17-family denominator per method; format aborts fail, infrastructure/budget incomplete blocks conclusion',
        'recipe_discovery':'publicly observed nonempty ingredient-name list; station-only metadata is NOT a known recipe; no quantity implication',
        'no_info_gain':'no immediate new necessary recipe on this directed action; transport and material probes may have delayed value',
        'quantity_correctness_proxy':'among states with at least one productive candidate: local Pareto non-dominance among craft1/2/4 and actual amount under exact action rules; higher output and no higher input consumption dominates; not guaranteed task-optimal or future-resource-safe',
        'consumption_prediction_error':'L1 only where an exact-context empirical sample produced a prediction; UNKNOWN excluded, coverage mandatory',
        'retention':'publicly observed key recipe names available in last5 observation memory OR actual rendered summary OR FIFO table at decision; source evidence, not internal neural knowledge',
        'summary_precision':'checked explicit recipe ingredient names, current observation fields, current goal possession lower bounds and physical container access; excludes unidentifiable historical-fact misuse',
        'stale_misuse':'NA unless causal behavioral evidence; historical locations/counts explicitly marked historical are not false current assertions',
        'context_cost':'all actual input/output tokens billed; added summary chars and char/4 proxy reported separately; exact incremental provider-token segmentation unavailable',
        'resource_destruction':'exact action dispatch vs full environmental step, includes NPC storage; net decrease is not proof of permanent failure',
        'statistical_unit':'17 paired exploratory families, source-game counts4/3/10; 10000 bootstrap, 3 source clusters, no stable significance claims'})
    print(json.dumps({'completed':len(metrics),'missing':len(missing),'successes':{m:r['successes'] for m,r in groups['all'].items()},
        'cost_usd':sum(r['cost_usd'] for r in metrics)}))

if __name__=='__main__':main()
