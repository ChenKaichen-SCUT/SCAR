"""Deterministic statistics and evidence indices from archived data; zero API."""
import collections as C
import copy
import csv
import json
import statistics as S
from .common import *
from scar_stage14.knowledge import Knowledge, extract
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text
from third_party_adapters.adaplanner_agentodyssey import validate_plan

def avg(v):return S.mean(v) if v else None

def context_facts(request,events):
    # Search only attested public disclosure strings or system fact records.
    # Model predictions/plan assertions never create knowledge here.
    text='\n'.join(m['content'] for m in request['messages'])
    flat=norm(text.replace('\\n','\n').replace('\\"','"'))
    facts={};ids=[]
    for e in events:
        if norm(e['raw_evidence']) not in flat:continue
        ids.append(e['evidence_id']);n=e['product']
        f=facts.setdefault(n,dict(ingredients=None,quantities=None,stations=None))
        for k in ('ingredients','quantities'):
            if e.get(k) is not None:f[k]=e[k]
        if e.get('stations'):f['stations']=sorted(set(f.get('stations') or [])|set(e['stations']))
    records=[]
    for msg in request['messages']:
        if msg['role']!='system':continue
        for line in msg['content'].splitlines():
            try:rec=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(rec,dict) or rec.get('kind')!='recipe':continue
            n=rec['key'];v=rec['value'];records.append(rec['id'])
            f=facts.setdefault(n,dict(ingredients=None,quantities=None,stations=None))
            # Every field must also have past native evidence for this product.
            for k in ('ingredients','quantities','stations'):
                x=v.get(k)
                if x is not None and x!='UNKNOWN' and any(e['product']==n and (set(e[k])==set(x) if k in ('ingredients','stations') and isinstance(e.get(k),list) and isinstance(x,list) else e.get(k)==x) for e in events):f[k]=x
    return facts,ids,records

def error_reason(q,requests):
    raw=q.get('raw_response',{});choices=raw.get('choices',[])
    if not choices:return 'no_saved_response:'+str(q.get('error_type'))
    content=choices[0].get('message',{}).get('content');finish=choices[0].get('finish_reason')
    try:d=json.loads(content)
    except (TypeError,ValueError) as e:return f'JSON_decode; finish={finish}; {str(e)}'
    phase=q['phase'];required={'plan':('steps','reasoning'),'revision':('steps','reasoning'),'plan_check':('steps','reasoning'),'resume':('start_from','reasoning'),'ask_LLM':('answer','reasoning')}.get(phase,('action','reasoning'))
    if not isinstance(d,dict) or not all(k in d for k in required):return 'missing_required_fields:'+','.join(required)
    try:
        if phase in ('plan','revision','plan_check'):validate_plan(d)
        elif phase=='resume':
            prev=[r for r in requests if r['step']==q['step'] and r['ordinal']<q['ordinal'] and r['phase']=='plan_check' and r['status']=='ok']
            ids=[x['id'] for x in prev[-1]['parsed']['steps']] if prev else []
            if d['start_from'] not in ids:raise ValueError(f"Resume must name a top-level step; selected={d['start_from']}; allowed={ids}")
        elif phase=='ask_LLM' and not isinstance(d['answer'],str):raise ValueError('string required')
        elif phase=='action' and (not isinstance(d['action'],str) or not d['action'].strip()):raise ValueError('Invalid action')
    except ValueError as e:
        detail=''
        if str(e)=='Invalid plan structure':
            def locate(steps,path='steps',depth=0):
                if not isinstance(steps,list):return path+':not_a_list'
                if not steps:return path+':empty_list'
                if depth>8:return path+':depth_exceeds_8'
                for i,node in enumerate(steps):
                    if not isinstance(node,dict):continue
                    keys=['body'] if node.get('op')=='repeat' else ['then']+(['else'] if node.get('else') else []) if node.get('op')=='if' else []
                    for key in keys:
                        found=locate(node.get(key),f'{path}[{i}].{key}',depth+1)
                        if found:return found
            detail='; '+str(locate(d.get('steps')))
        return 'validator:'+str(e)+detail
    return 'not_isolated_from_saved_response:'+str(q.get('error_type'))

def run():
    deny_network();baseline()
    tasks=load(RESULTS/'tasks.json');truth=load(RESULTS/'evaluator_truth.json')
    histories={r['task_id']:r for r in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    witnesses={r['task_id']:r for r in read_gzip(RESULTS/'native_feasibility_witnesses.jsonl.gz')}
    frozen_stats={(r['task_id'],r['method']):r for r in load(RESULTS/'per_task.json')}
    allstats=[];allknowledge=[];allcontexts=[];allactions=[];audits=[];errors=[];cf={}
    cfpath=OUT/'counterfactual_local.jsonl.gz'
    if not cfpath.exists():cfpath=OUT/'counterfactual_server.jsonl.gz'
    if cfpath.exists():cf={r['evidence_id']:r for r in read_gzip(cfpath)}
    for t in tasks:
        tid=t['task_id'];graph=truth[tid]['recipes'];names={r['name'] for r in graph.values()};target=t['target_item']
        witness_names=sorted({parse_action(r['action']).target for r in witnesses[tid]['trace'] if parse_action(r['action']).verb=='craft'}&names)
        for method in METHODS:
            folder=run_dir(t,method);rows=read_gzip(folder/'trajectory.jsonl.gz');requests=read_gzip(folder/'requests.jsonl.gz');summary=load(folder/'summary.json')
            assert len(rows)==summary['steps'] and summary['status'] in ('success','game_failure','step_limit','model_parse_exception')
            assert summary['initial_state_hash']==t['initial_state_hash'] and len(rows)<=100
            stat=copy.deepcopy(frozen_stats[tid,method]);stat.pop('knowledge',None)
            for key in ('input_tokens','output_tokens','cache_hit_tokens','craft_failed','invalid','material_rejection','station_rejection','identical_feedback_repeat_inspections'):stat.setdefault(key,0)
            craftrows=[r for r in rows if r['metrics']['craft']]
            stat.update(target=target,seed=t['initial_seed'],recipe_nodes=t['recipe_nodes'],craft_attempts=len(craftrows),
                productive_crafts=sum(bool(r['metrics']['actual_production']) for r in craftrows),
                closure_productive_crafts=sum(bool(set(r['metrics']['actual_production'])&set(graph)) for r in craftrows),
                wait_actions=sum(parse_action(r['action']).verb=='wait' for r in rows),
                health_loss_actions=sum(r['physical_after']['health']<r['physical_before']['health'] for r in rows),
                charged_known_usage=sum(r.get('cost_usd',0) for r in requests),
                unknown_billing_reserves=sum(r['charged_or_reserved_usd'] for r in requests if 'usage' not in r),
                failed_request_cost=sum(r['charged_or_reserved_usd'] for r in requests if r['status']!='ok'),
                context_first_tokens=next((r['usage']['prompt_tokens'] for r in requests if 'usage' in r),0),
                context_last_tokens=next((r['usage']['prompt_tokens'] for r in reversed(requests) if 'usage' in r),0),
                context_max_tokens=max([r.get('usage',{}).get('prompt_tokens',0) for r in requests]+[0]),
                context_truncated_flags=sum(bool(r['decision'].get('truncated')) for r in rows),
                response_length_finishes=sum(r.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason')=='length' for r in requests),
                successful_api_phases=dict(C.Counter(r['phase'] for r in requests if r['status']=='ok')))
            if method=='A3':stat['completed_plan_versions']=rows[-1]['decision']['version'] if rows else 0
            allstats.append(stat)
            kb=Knowledge();events=[]
            for i,h in enumerate(histories[tid]['history']):
                delta=kb.observe(h['after'],h['action'])
                events.extend(dict(e,evaluation_step=0,evidence_id=f'{tid}:prefix{i+1:03d}') for e in delta['events'])
            kb.observe(histories[tid]['observation'],'')
            initial=coverage(kb.facts,graph);timeline=[dict(step=0,coverage=initial)]
            first={k:{n:0 for n in initial[k]} for k in initial};used={};registered=[];runcontexts=[]
            inspections=C.Counter();no_change_queue=0;previous_queue=None;max_queue_streak=0
            for r in rows:
                step=r['step'];ident=eid(t,method,step);before=coverage(kb.facts,graph)
                # request.step is the action about to run: later feedback is excluded.
                for q in [q for q in requests if q['step']==step]:
                    facts,source_ids,records=context_facts(q,events)
                    c=dict(task_id=tid,method=method,step=step,request_id=q['request_id'],phase=q['phase'],status=q['status'],
                        coverage=coverage(facts,graph),public_before=before,evidence_ids=source_ids,system_record_ids=records,
                        prompt_tokens=q.get('usage',{}).get('prompt_tokens'),output_tokens=q.get('usage',{}).get('completion_tokens'),
                        cache_hit_tokens=q.get('usage',{}).get('prompt_cache_hit_tokens'),
                        source='Literal native evidence and attested system recipe records only; semantic paraphrases not classified.')
                    allcontexts.append(c);runcontexts.append(c)
                delta=kb.observe(r['feedback'],r['action'])
                # Reconstruct the offline public observer exactly; no inferred facts.
                assert coverage(kb.facts,graph)==coverage(r['public_knowledge_after'],graph)
                events.extend(dict(e,evaluation_step=step,evidence_id=ident) for e in delta['events'])
                cov=coverage(kb.facts,graph);timeline.append(dict(step=step,coverage=cov))
                for k,ns in cov.items():
                    for n in ns:first[k].setdefault(n,step)
                for oid,q in r['metrics']['actual_production'].items():
                    if oid in graph and q>0:used.setdefault(graph[oid]['name'],step)
                table=r['decision'].get('controller',{}).get('table',r['decision'].get('table'))
                if table is not None:
                    facts=table.get('knowledge',{}).get('facts',{})
                    rc=coverage(facts,graph)
                    registered.append(dict(step=step,coverage=rc,public_before=before,
                        missing_before_relation=sorted(set(before['relation'])-set(rc['relation'])),
                        missing_before_quantity=sorted(set(before['quantity'])-set(rc['quantity']))))
                p=parse_action(r['action']);repeated=bool(p.verb=='inspect' and inspections[p.target]);
                if p.verb=='inspect':inspections[p.target]+=1
                evidence=dict(evidence_id=ident,task_id=tid,method=method,step=step,action=r['action'],
                    raw_path=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),jsonl_line=step,
                    requests=[q['request_id'] for q in requests if q['step']==step],
                    feedback=feedback_text(r['feedback']['text']),before_hash=r['physical_before']['state_hash'],after_hash=r['state_hash'],
                    health_before=r['physical_before']['health'],health_after=r['physical_after']['health'],
                    death=r['death'],
                    metrics=r['metrics'],knowledge_delta=delta,public_coverage_before=before,public_coverage_after=cov,
                    target_owned=r['physical_after']['target_owned'],success=r['success'],repeated_inspect=repeated)
                allactions.append(evidence)
                if method!='A0':continue
                d=r['decision']['decision'];structured=d['structured'];s10=structured.get('stage10',{});s16=structured.get('stage16',{})
                controller=r['decision']['controller'];prop=d['proposed_action'];pp=parse_action(prop);over=prop!=r['action']
                layer=[]
                if s10.get('frozen_F0_candidate')!=prop:layer.append('S1_FIFO_exploration_or_batch')
                if s10.get('overlay_changed_F0'):layer.append('S1_condition_guard_or_public_alternative')
                bm=structured.get('mechanisms',{}).get('batch',{})
                if bm and bm.get('original_action') not in (None,s10.get('selected_action')):layer.append('batch')
                if s16.get('selected_module'):layer.append('P3_finish')
                conditions=[x for x in s10.get('conditions',[]) if x['action']==prop]
                public_support=[]
                state=structured.get('resource_table',{}).get('state',{})
                if pp.verb=='inspect' and pp.target in (state.get('ground') or {}):public_support.append('object_visible')
                if pp.verb=='enter' and pp.target in (state.get('neighbors') or []):public_support.append('adjacent_route')
                if pp.verb in ('pick up','store') and pp.target in (state.get('ground') or {}):public_support.append('ground_material_visible')
                if pp.verb=='craft' and pp.target in before['relation']:public_support.append('recipe_relation_public')
                if pp.verb=='craft' and pp.target in before['quantity']:public_support.append('recipe_quantity_public')
                queue=controller.get('queue');no_change_queue=no_change_queue+1 if queue==previous_queue else 1
                previous_queue=copy.deepcopy(queue);max_queue_streak=max(max_queue_streak,no_change_queue)
                gained={k:v for k,v in r['metrics']['actual_production'].items() if v>0}
                materials={k:v-r['physical_before']['possessed'].get(k,0) for k,v in r['physical_after']['possessed'].items() if v>r['physical_before']['possessed'].get(k,0)}
                phenomenon=[]
                if over and pp.verb=='inspect' and pp.target not in controller.get('table',{}).get('inspected',[]):phenomenon.append('proposal_inspects_not_registered_item')
                if over and pp.verb=='craft' and pp.target in names and p.verb in ('inspect','enter','wait'):phenomenon.append('necessary_craft_to_explore_or_wait')
                if len(before['relation'])==len(names) and not gained and not materials and not delta['new_relations'] and p.verb in ('inspect','wait'):phenomenon.append('closure_relations_complete_no_immediate_gain')
                if over and pp.target==target:phenomenon.append('target_action_overridden')
                if controller.get('exploration_spent',0)>=18:phenomenon.append('exploration_cap_reached')
                if p.verb=='wait':phenomenon.append('wait')
                audit=dict(evidence_id=ident,task_id=tid,step=step,proposal=prop,actual=r['action'],overridden=over,
                    S1_candidate=s10.get('frozen_F0_candidate'),P1_action=s16.get('P1_action'),P3_action=s16.get('selected'),
                    layers=layer,stage10_reason=s10.get('reason'),P3_module=s16.get('selected_module'),
                    batch=bm,proposal_public_support=public_support,proposal_condition_checks=conditions,
                    saved_S1_mechanisms=structured.get('mechanisms',{}),
                    public_support_limit='Partial evidential support is not full executability or optimality.',
                    actual_new_relations=delta['new_relations'],actual_quantity_updates=delta['quantity_updates'],actual_station_updates=delta['station_updates'],
                    actual_production=gained,actual_material_gains=materials,health_change=evidence['health_after']-evidence['health_before'],
                    queue=queue,queue_unchanged_streak=no_change_queue,exploration_spent=controller.get('exploration_spent'),
                    phenomena=phenomenon,local_counterfactual_dimensions=cf.get(ident,{}).get('local_dimensions',[]))
                audits.append(audit)
            # Terminal planning attempts can happen at N+1 without an environment action.
            for q in [q for q in requests if q['step']>len(rows)]:
                facts,source_ids,records=context_facts(q,events)
                c=dict(task_id=tid,method=method,step=q['step'],request_id=q['request_id'],phase=q['phase'],status=q['status'],coverage=coverage(facts,graph),public_before=coverage(kb.facts,graph),evidence_ids=source_ids,system_record_ids=records,terminal_no_action=True,prompt_tokens=q.get('usage',{}).get('prompt_tokens'))
                allcontexts.append(c);runcontexts.append(c)
            final=coverage(kb.facts,graph)
            complete=lambda scope,k: max([first[k].get(n,10**6) for n in scope],default=0) if all(n in first[k] for n in scope) else None
            kn=dict(task_id=tid,method=method,scope=sorted(names),witness_scope=witness_names,goal=target,initial=initial,final=final,
                initially_public_recipes=initial['relation'],newly_public_recipes=sorted(set(final['relation'])-set(initial['relation'])),
                first=first,first_all_relations=complete(names,'relation'),first_all_quantities=complete(names,'quantity'),
                first_all_witness_relations=complete(witness_names,'relation'),first_all_explicit_conditions=complete(names,'full_explicitly_confirmed'),
                snapshots={str(b):dict(coverage=timeline[min(b,len(rows))]['coverage'],observed_through=min(b,len(rows)),terminated=len(rows)<b,status=summary['status']) for b in (20,40,60,80,100)},
                first_successful_craft=used,
                latency_from_relation={n:used[n]-first['relation'][n] for n in used.keys()&first['relation'].keys()},
                latency_from_quantity={n:used[n]-first['quantity'][n] for n in used.keys()&first['quantity'].keys()},
                known_relation_not_crafted=sorted(set(final['relation'])-set(used)),known_quantity_not_crafted=sorted(set(final['quantity'])-set(used)),
                unknown_quantities=sorted(names-set(final['quantity'])),
                no_station_requirement_disclosed=sorted(n for n in names if not kb.facts.get(n,{}).get('stations')),
                partially_disclosed_stations={n:kb.facts[n]['stations'] for n in names if kb.facts.get(n,{}).get('stations')},
                complete_station_conditions_unconfirmed=sorted(n for n in names if kb.facts.get(n,{}).get('station_completeness')!='explicit_complete'),
                station_epistemic_status={n:kb.facts.get(n,{}).get('station_completeness','UNKNOWN') for n in names},
                registered=registered,events=[e for e in events if e['product'] in names],timeline=timeline,
                model_context_last=runcontexts[-1]['coverage'] if runcontexts else None,
                structured_note='A0/A4 explicit recipe table; A1/A2/A3 no equivalent explicit recipe registration; not scored as zero.')
            allknowledge.append(kn)
            for q in requests:
                if q['status']=='ok':continue
                errors.append(dict(task_id=tid,method=method,request_id=q['request_id'],step=q['step'],ordinal=q['ordinal'],attempt=q['attempt'],phase=q['phase'],
                    terminal=summary['status']=='model_parse_exception' and q['step']==len(rows)+1 and q['logical_id']==requests[-1]['logical_id'],
                    reason=error_reason(q,requests),error_type=q.get('error_type'),status=q['status'],
                    finish_reason=q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason'),
                    cost_usd=q['charged_or_reserved_usd'],subsequently_recovered=any(x['logical_id']==q['logical_id'] and x['status']=='ok' for x in requests),
                    request_path=str((folder/'requests.jsonl.gz').relative_to(ROOT)),jsonl_line=requests.index(q)+1,
                    response_text=q.get('raw_response',{}).get('choices',[{}])[0].get('message',{}).get('content')))
    write(OUT/'per_run.json',allstats);write(OUT/'knowledge.json',allknowledge)
    gzip_rows(OUT/'model_context_evidence.jsonl.gz',allcontexts);gzip_rows(OUT/'action_evidence.jsonl.gz',allactions)
    gzip_rows(OUT/'controller_audit.jsonl.gz',audits);write(OUT/'response_errors.json',errors)
    fields=['task_id','game','target','seed','depth','recipe_nodes','method','status','success','steps','craft_attempts','productive_crafts','closure_productive_crafts','craft_failed','invalid','repeated_inspections','material_rejection','station_rejection','api_calls','input_tokens','output_tokens','cache_hit_tokens','cost_usd','charged_known_usage','unknown_billing_reserves']
    with (OUT/'per_run.csv').open('w') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(allstats)
    wide=[]
    for t in tasks:
        out={k:t[k] for k in ('task_id','game_name','target_item','initial_seed','dependency_depth','recipe_nodes')}
        for r in [x for x in allstats if x['task_id']==t['task_id']]:
            out.update({r['method']+'_'+k:r[k] for k in fields if k not in ('task_id','game','target','seed','depth','recipe_nodes','method')})
        wide.append(out)
    with (OUT/'paired_24.csv').open('w') as f:
        w=csv.DictWriter(f,list(wide[0]));w.writeheader();w.writerows(wide)
    aggregates={};pairs={}
    for m in METHODS:
        rr=[r for r in allstats if r['method']==m];kk=[k for k in allknowledge if k['method']==m];cc=[c for c in allcontexts if c['method']==m]
        agg=copy.deepcopy(load(RESULTS/'analysis.json')['methods'][m]);agg.pop('nominal_wilson_R100',None)
        for key in ('craft_attempts','productive_crafts','closure_productive_crafts','wait_actions','health_loss_actions','failed_request_cost','unknown_billing_reserves','response_length_finishes','context_truncated_flags'):agg[key]=sum(r[key] for r in rr)
        agg['cache_hit_rate']=agg['cache_hit_tokens']/agg['input_tokens'] if agg['input_tokens'] else None
        agg['context_max_tokens']=max(r['context_max_tokens'] for r in rr)
        agg['phases']=dict(sum((C.Counter(r['api_phases']) for r in rr),C.Counter()))
        agg['successful_phases']=dict(sum((C.Counter(r['successful_api_phases']) for r in rr),C.Counter()))
        agg['knowledge']=dict(goal_relation_discovered=sum(k['goal'] in k['final']['relation'] for k in kk),goal_quantity_discovered=sum(k['goal'] in k['final']['quantity'] for k in kk),
            all_relations=sum(k['first_all_relations'] is not None for k in kk),all_witness_relations=sum(k['first_all_witness_relations'] is not None for k in kk),
            final_relation_macro=avg([len(k['final']['relation'])/len(k['scope']) for k in kk]),final_quantity_macro=avg([len(k['final']['quantity'])/len(k['scope']) for k in kk]),
            successful_after_goal_relation=sum(r['success'] and k['goal'] in k['final']['relation'] for r,k in zip(rr,kk)),
            successful_after_goal_quantity=sum(r['success'] and k['goal'] in k['final']['quantity'] for r,k in zip(rr,kk)),
            mean_relation_latency=avg([v for k in kk for v in k['latency_from_relation'].values() if v>=0]),
            checkpoints={str(b):{key:avg([len(k['snapshots'][str(b)]['coverage'][key])/len(k['scope']) for k in kk]) for key in ('relation','quantity')} for b in (20,40,60,80,100)},
            structured_missing_relation_actions=sum(bool(x['missing_before_relation']) for k in kk for x in k['registered']),
            structured_missing_quantity_actions=sum(bool(x['missing_before_quantity']) for k in kk for x in k['registered']),
            requests_with_public_relation_omissions=sum(bool(set(c['public_before']['relation'])-set(c['coverage']['relation'])) for c in cc),
            requests_with_public_quantity_omissions=sum(bool(set(c['public_before']['quantity'])-set(c['coverage']['quantity'])) for c in cc))
        aggregates[m]=agg
        if m=='A0':continue
        pp=[]
        for t in tasks:
            a=next(r for r in allstats if r['task_id']==t['task_id'] and r['method']=='A0');b=next(r for r in rr if r['task_id']==t['task_id'])
            ka=next(k for k in allknowledge if k['task_id']==t['task_id'] and k['method']=='A0');kb=next(k for k in kk if k['task_id']==t['task_id'])
            pp.append(dict(task_id=t['task_id'],category=('both_success' if a['success'] and b['success'] else 'scar_only' if a['success'] else 'other_only' if b['success'] else 'both_fail'),
                scar_steps=a['steps'],other_steps=b['steps'],action_delta=a['steps']-b['steps'],cost_delta=a['cost_usd']-b['cost_usd'],
                both_goal_relation_known=t['target_item'] in ka['final']['relation'] and t['target_item'] in kb['final']['relation'],
                both_goal_quantity_known=t['target_item'] in ka['final']['quantity'] and t['target_item'] in kb['final']['quantity']))
        paired=[p for p in pp if p['category']=='both_success']
        pairs[m]=dict(counts=dict(C.Counter(p['category'] for p in pp)),tasks=pp,
            both_success_action_delta_mean=avg([p['action_delta'] for p in paired]),both_success_cost_delta_mean=avg([p['cost_delta'] for p in paired]),
            both_success_scar_faster=sum(p['action_delta']<0 for p in paired),both_success_other_faster=sum(p['action_delta']>0 for p in paired),
            both_goal_relation_known_outcomes=dict(C.Counter(p['category'] for p in pp if p['both_goal_relation_known'])),
            both_goal_quantity_known_outcomes=dict(C.Counter(p['category'] for p in pp if p['both_goal_quantity_known'])))
    write(OUT/'statistics.json',dict(methods=aggregates,paired=pairs,
        audit=dict(actions=len(audits),overrides=sum(a['overridden'] for a in audits),layers=dict(C.Counter(l for a in audits if a['overridden'] for l in a['layers'])),
        phenomena=dict(C.Counter(p for a in audits for p in a['phenomena'])),local_dimensions=dict(C.Counter(l for a in audits for l in a['local_counterfactual_dimensions']))),
        errors=dict(attempts=len(errors),terminal_runs=len({(e['task_id'],e['method']) for e in errors if e['terminal']})),
        new_api_calls=0,network_guard=True,unchanged_input_files=baseline()))
    print('analyzed',len(allstats),'runs;',len(allactions),'actions;',len(errors),'abnormal responses')

if __name__=='__main__':run()
