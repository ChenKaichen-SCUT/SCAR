"""Recompute all outcomes/paired changes from the complete frozen batch."""
from collections import Counter,defaultdict
import copy
import json
from pathlib import Path
import random
import statistics
from scar.io import atomic_json
from scar_stage14.common import load,records,save_records
from scar_stage14.knowledge import Knowledge
from scar_stage10.controller import ResourceController
from scar_stage15.controller import Controller15
from scar_v3.state import parse_action
ROOT=Path('results/stage15');METHODS=[f'P{i}' for i in range(7)]
PAIRS=[('P1','P0'),('P2','P1'),('P3','P1'),('P4','P1'),('P5','P1'),('P6','P1'),('P6','P0')]


def needed_public(table,target):
    seen=set();queue=[target]
    while queue:
        n=queue.pop()
        if n in seen:continue
        seen.add(n);queue.extend(table.get(n,{}).get('ingredients',[]))
    return seen


def bootstrap(diffs):
    rng=random.Random(314159);n=len(diffs)
    values=sorted(sum(diffs[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [values[249],values[9749]]


def main():
    cases={c['id']:c for c in load('results/stage11/cases.json')}
    audits={x['task_id']:x for x in records(ROOT/'native_audit.jsonl.gz')}
    metrics=[];detail=[];trajectories={};request_summary={};decision_checks=0;allrequests=set()
    for method in METHODS:
        request_rows=list(records(ROOT/f'requests_{method}.jsonl.gz'));bytask=defaultdict(list)
        for r in request_rows:
            request=r['request'];assert request['request_id'] not in allrequests;allrequests.add(request['request_id']);bytask[r['task_id']].append(request)
        request_summary[method]={'requests':len(request_rows),'statuses':dict(Counter(r['request']['status'] for r in request_rows)),
            'served_models':dict(Counter((r['request'].get('raw_response') or {}).get('model','NO_RESPONSE') for r in request_rows))}
        for ep in records(ROOT/f'trajectories_{method}.jsonl.gz'):
            case=cases[ep['case_id']];goal=case['goal']['name'];keys={case['object_names'][oid] for oid in case['recipe_graph']}
            k=Knowledge()
            for h in case['history']:
                k.observe(h['after'],h['action'],cutoff=h['after']['step'],source={'action':h['action'],'step':h['after']['step']})
            all_known=0 if keys<=set(k.relations()) else None
            known_at_start=all_known is not None;repeats=0;inspected=set();timeline=[];first_goal=None;final_craft=None;last=None
            qty_correct=qty_known=reg_known=reg_total=0
            ctr=Counter();public_losses=Counter();consumed=Counter();useful_consumed=Counter();lossall=Counter();health=0
            pending_cont=None;continuations=[];cursor=0
            assert len(audits[ep['task_id']]['rows'])==len(ep['rows'])
            for row,au in zip(ep['rows'],audits[ep['task_id']]['rows'],strict=True):
                i=row['index'];p=parse_action(row['executed_action']);state=row['stage7_state_before'];table=state['table']['recipes']
                assert all(e['observed_step']<=row['observation']['step'] for e in k.events)
                c=(ResourceController if method=='P0' else Controller15).from_dict(copy.deepcopy(state))
                got=c.choose(row['observation'],row['proposed_action'])
                if got!=row['executed_action']:
                    assert any(e.get('event')=='format_fallback' for e in row['events']),(ep['task_id'],i,got,row['executed_action'])
                c.observe(row['observation'],row['executed_action'],row['next_observation']);last=c;decision_checks+=1
                if method!='P0':
                    assert c.modules15==list({'P1':(),'P2':('quantity',),'P3':('finish',),'P4':('protect',),'P5':('continue',),'P6':('quantity','finish','protect','continue')}[method])
                    assert not c.opportunistic and not c.storage and c.continuation_used15<=7 and c.step15<=40
                # Match each executed model result to its actual request. Failed
                # provider attempts remain in separate cost/abort accounting.
                matched=None
                while cursor<len(bytask[ep['task_id']]):
                    rr=bytask[ep['task_id']][cursor];cursor+=1
                    choices=(rr.get('raw_response') or {}).get('choices') or []
                    if rr['status']=='ok' and choices and choices[0]['message']['content']==row['response']:
                        matched=rr;break
                assert matched is not None,(ep['task_id'],i,'request_alignment')
                for fact in row.get('fact_summary',{}).get('records',[]):
                    if fact['kind']=='recipe' and fact['key'] in k.relations():
                        truth=k.facts[fact['key']]
                        if truth['quantities'] is not None:
                            ctr['model_quantity_exposures']+=1
                            ctr['model_correct_quantity_exposures']+=int(fact['value'].get('quantities')==truth['quantities'])
                audit=row.get('structured',{}).get('stage15',{})
                delta=k.observe(row['next_observation'],row['executed_action'],cutoff=row['next_observation']['step'],source={'action':row['executed_action'],'step':row['next_observation']['step']})
                novelty=bool(delta['new_relations'] or delta['quantity_updates'] or delta['station_updates'])
                if p.verb=='inspect':
                    ctr['inspect']+=1
                    if p.target in inspected and p.target!='inventory' and p.target not in state['table']['containers'] and not novelty:repeats+=1
                    inspected.add(p.target)
                if all_known is None and keys<=set(k.relations()):all_known=i+1
                if p.verb=='craft':
                    ctr['craft']+=1;ctr['craft_success']+=int(au['actual_output']>0)
                    ctr['insufficient_material_rejection']+=int('Cannot craft a single' in row['feedback'])
                    ctr['batch_dominated']+=bool(au['locally_dominated_by'])
                    expected=audit.get('checks',[])
                    if p.target==goal and au['actual_output']>0:final_craft=i+1
                    # Public current deficit is a lower bound, not total future
                    # need: report excess as an exposure, not proven waste.
                    target_need=case['goal']['amount'] if p.target==goal else state.get('queue_needs',{}).get(p.target,1)
                    owned=c.quantity_facts.table.count(p.target) or 0
                    pre_owned=row['physical_before']['accessible'].get(p.target,0)
                    ctr['output_above_current_deficit_proxy']+=max(0,au['actual_output']-max(0,target_need-pre_owned))
                public_nodes=needed_public(table,goal)
                for n,v in au['environment_loss'].items():
                    lossall[n]+=v
                    if n in public_nodes:public_losses[n]+=v
                consumed.update(au['consumed'])
                if p.target in keys and au['actual_output']>0:useful_consumed.update(au['consumed'])
                health+=max(0,au['health_loss'])
                selected=audit.get('selected_module')
                for check in audit.get('checks',[]):
                    name=check['module']
                    if check.get('candidate') and check['candidate']!=audit.get('P1_action'):ctr[name+'_candidate_change']+=1
                if row['executed_action']!=audit.get('P1_action',row['executed_action']):ctr['changed_from_P1']+=1
                if selected=='protect':ctr['protection_actions']+=1;ctr['protection_health_loss']+=max(0,au['health_loss'])
                if selected=='finish':ctr['finish_selected']+=1
                if selected=='continue':
                    ctr['continuation_actions']+=1
                    if pending_cont is None:
                        pending_cont={'start':i,'product':(audit.get('intent') or {}).get('product'),'actions':0,'new_relations':[],'quantity_updates':[],'produced':0,'completed':False}
                        continuations.append(pending_cont)
                    pending_cont['actions']+=1;pending_cont['new_relations']+=delta['new_relations'];pending_cont['quantity_updates']+=delta['quantity_updates'];pending_cont['produced']+=au['actual_output']
                    reason=(c.intent15 or {}).get('stopped');pending_cont['stop']=reason
                    pending_cont['completed']=bool(p.verb=='inspect' and p.target==pending_cont['product'] and 'I inspected ' in row['feedback'])
                    if reason:pending_cont=None
                elif pending_cont is not None:
                    pending_cont['stop']=(c.intent15 or {}).get('stopped') or 'returned_to_S1';pending_cont=None
                if row['diagnostic_goal_reached'] and first_goal is None:first_goal=i+1
                timeline.append({'index':i,'base_proposal':row['proposed_action'],'old_controller_action':audit.get('shadow_S1_action',row['executed_action']),
                    'P1_action':audit.get('P1_action',row['executed_action']),'executed_action':row['executed_action'],
                    'conditions':audit,'public_feedback':row['feedback'],'new_knowledge':delta,
                    'known_necessary_names':sorted(keys&set(k.relations())),'all_necessary_names_known':keys<=set(k.relations()),
                    'native':au,'full_goal':row['diagnostic_goal_reached'],'semantic_rejection':row['semantic_rejection']})
            if pending_cont is not None:
                pending_cont['stop']='total40_environment_action_budget_exhausted' if len(ep['rows'])==40 else 'episode_terminated'
                pending_cont['stop_inferred_from_episode_termination']=True
            final_recipes=last.table.recipes if last else {}
            relations=k.relations();registered={n for n,r in final_recipes.items() if r.get('ingredients')}
            reg_total=len(relations);reg_known=sum(n in registered and set(final_recipes[n]['ingredients'])==set(f['ingredients']) for n,f in relations.items())
            qty_known=sum(f['quantities'] is not None for f in relations.values())
            qty_correct=sum(f['quantities'] is not None and final_recipes.get(n,{}).get('quantities')==f['quantities'] for n,f in relations.items())
            rq=bytask[ep['task_id']]
            m={'task_id':ep['task_id'],'case_id':ep['case_id'],'family':goal,'algorithm':method,'status':ep['summary']['status'],
               'R10':first_goal is not None and first_goal<=10,'R20':first_goal is not None and first_goal<=20,'R40':first_goal is not None and first_goal<=40,
               'success_step':first_goal,'steps':len(ep['rows']),'final_craft_step':final_craft,'final_acquisition_step':first_goal,
               'all_necessary_names_known_after':all_known,'actions_after_all_names_known':len(ep['rows'])-all_known if all_known is not None else None,
               'goal_actions_delayed':sum(1 for r in ep['rows'] if r.get('proposed_effect',{} ) and r['proposed_effect'].get('physical_goal') and not r['diagnostic_goal_reached']),
               'registered_relations':reg_known,'public_relations':reg_total,'correct_quantity_records':qty_correct,'public_quantity_records':qty_known,
               'repeat_information_inspections':repeats,'missing_necessary_names_final':sorted(keys-set(relations)),
               'input_tokens':sum((r.get('usage') or {}).get('prompt_tokens',0) for r in rq),'output_tokens':sum((r.get('usage') or {}).get('completion_tokens',0) for r in rq),
               'cost_usd':sum(r.get('cost_usd',0) for r in rq),'conservative_cost_usd':sum(r.get('charged_or_reserved_usd',0) for r in rq),'api_calls':len(rq),
               'semantic_rejections':sum(r['semantic_rejection'] for r in ep['rows']),
               'public_critical_loss':dict(public_losses),'all_environment_loss':dict(lossall),'actual_material_consumption':dict(consumed),
               'necessary_production_consumption':dict(useful_consumed),'health_loss':health,'continuations':continuations,**ctr}
            metrics.append(m);detail.append({'task_id':ep['task_id'],'case_id':ep['case_id'],'algorithm':method,'rows':timeline});trajectories[method,ep['case_id']]=ep
    aggregate={}
    sumfields=['R10','R20','R40','steps','input_tokens','output_tokens','cost_usd','conservative_cost_usd','api_calls','semantic_rejections',
       'registered_relations','public_relations','correct_quantity_records','public_quantity_records','repeat_information_inspections',
       'craft','craft_success','insufficient_material_rejection','batch_dominated','output_above_current_deficit_proxy',
       'model_quantity_exposures','model_correct_quantity_exposures','finish_selected','goal_actions_delayed','protection_actions','protection_health_loss','continuation_actions','health_loss','changed_from_P1']
    for method in METHODS:
        rows=[m for m in metrics if m['algorithm']==method]
        a={k:sum(m.get(k,0) for m in rows) for k in sumfields}
        a.update(episodes=len(rows),success_steps=[m['success_step'] for m in rows if m['R40']],statuses=dict(Counter(m['status'] for m in rows)),
          critical_loss_units=sum(sum(m['public_critical_loss'].values()) for m in rows),
          continuation_plans=sum(len(m['continuations']) for m in rows),continuation_completed=sum(c['completed'] for m in rows for c in m['continuations']))
        aggregate[method]=a
    paired=[];changed=[]
    metric_index={(m['algorithm'],m['case_id']):m for m in metrics}
    detail_index={d['task_id']:d for d in detail}
    for new,base in PAIRS:
        diffs=[];wins=[];losses=[]
        for caseid,case in cases.items():
            a,b=metric_index[new,caseid],metric_index[base,caseid];diff=int(a['R40'])-int(b['R40']);diffs.append(diff)
            if diff:
                (wins if diff>0 else losses).append(case['goal']['name'])
                changed.append({'comparison':new+'-'+base,'family':case['goal']['name'],'case_id':caseid,'change':diff,
                  'new_metrics':a,'base_metrics':b,'new_decisions':detail_index[a['task_id']]['rows'],'base_decisions':detail_index[b['task_id']]['rows'],
                  'scope':'different sampled prompts/proposals and trajectories; local shadow action evidence is conditional, not full causal mediation'})
        paired.append({'comparison':new+'-'+base,'delta_R40':sum(diffs)/10,'wins':wins,'losses':losses,'family_differences':diffs,
           'paired_family_bootstrap_95_descriptive':bootstrap(diffs),'sampling':'same physical seeds; API LLM samples not paired; ten repeatedly developed families'})
    atomic_json(ROOT/'episode_metrics.json',metrics);atomic_json(ROOT/'aggregate_metrics.json',aggregate);atomic_json(ROOT/'paired_comparisons.json',paired)
    atomic_json(ROOT/'request_model_audit.json',request_summary)
    save_records(ROOT/'decision_analysis.jsonl.gz',detail);save_records(ROOT/'all_success_changes.jsonl.gz',changed)
    atomic_json(ROOT/'analysis_checks.json',{'policy_decisions_reproduced':decision_checks,'requests_accounted':len(allrequests),
       'families':10,'episodes':len(metrics),'all_comparisons':len(paired),'success_changes':len(changed),'no_hidden_policy_input':True,
       'epistemic_limits':['nominal weights not batch ratios','excess output not proven waste','necessary production consumption not final causal utility','family intervals descriptive only','short checkpoint outcomes not full-task evidence']})
    print(json.dumps({m:{k:a[k] for k in ['R40','steps','cost_usd']} for m,a in aggregate.items()}))

if __name__=='__main__':main()
