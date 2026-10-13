"""Server-only, zero-API analysis. Never imported by the frozen agent/runner.

Hidden closure names label necessity offline; hidden quantities/stations NEVER
complete a public knowledge state. Historical results are read, never rerun.
"""
import collections as C
import copy
import csv
import json
import re
import statistics as S
from .common import ROOT, RESULTS, load, write, read_gzip, gzip_rows, deny_network, sha
from .controller import Controller18
from .acquisition import public_demand, requested
from .consequences import public_frame
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text
from scar_stage14.knowledge import Knowledge
from scar_stage17_diagnostics.common import coverage, norm
from scar_stage17_diagnostics.analyze import error_reason

METHODS=('A0','SCAR18','A1','A2','A3','A4')
NAMES={'A0':'Stage17 SCAR','SCAR18':'SCAR18','A1':'Stage17 ReAct+STM','A2':'Stage17 LongContext','A3':'Stage17 AdaPlanner适配','A4':'Stage17 Deterministic DAG'}


def context_facts(request,events):
    text='\n'.join(m['content'] for m in request['messages'])
    flat=norm(text.replace('\\n','\n').replace('\\"','"'))
    facts={};ids=[];records=[]
    for e in events:
        if norm(e['raw_evidence']) not in flat:continue
        ids.append(e['evidence_id']);n=e['product']
        f=facts.setdefault(n,dict(ingredients=None,quantities=None,stations=None))
        for k in ('ingredients','quantities'):
            if e.get(k) is not None:f[k]=e[k]
        if e.get('stations'):f['stations']=sorted(set(f.get('stations') or [])|set(e['stations']))
    for msg in request['messages']:
        if msg['role']!='system':continue
        for line in msg['content'].splitlines():
            try:r=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(r,dict) or r.get('kind')!='recipe':continue
            n=r['key'];records.append(r['id']);f=facts.setdefault(n,dict(ingredients=None,quantities=None,stations=None))
            for k in ('ingredients','quantities','stations'):
                x=r['value'].get(k)
                if isinstance(x,dict) and 'status' in x:
                    x=x['value'] if x['status']=='KNOWN' else None
                if x is None or x=='UNKNOWN':continue
                if any(e['product']==n and (set(e[k])==set(x) if k in ('ingredients','stations') and isinstance(e.get(k),list) and isinstance(x,list) else e.get(k)==x) for e in events):f[k]=x
    return facts,ids,records


def folder(task,method):
    stage='stage18' if method=='SCAR18' else 'stage17'
    return ROOT/'results'/stage/'runs'/f"{task['task_id']}__{method}"


def analyse(task,method,truth,history):
    path=folder(task,method);rows=read_gzip(path/'trajectory.jsonl.gz');requests=read_gzip(path/'requests.jsonl.gz');summary=load(path/'summary.json')
    assert len(rows)==summary['steps']<=100 and summary['initial_state_hash']==task['initial_state_hash']
    if rows:assert summary['success']==rows[-1]['success']
    graph=truth['recipes'];names={r['name'] for r in graph.values()}
    observer=Controller18();kb=Knowledge();events=[]
    for i,h in enumerate(history['history']):
        observer.observe(h['before'],h['action'],h['after'])
        d=kb.observe(h['after'],h['action'])
        events.extend(dict(e,evaluation_step=0,evidence_id=f"{task['task_id']}:prefix{i+1}") for e in d['events'])
    observer.set_goal('craft 1 '+task['target_item'],task['objective_text'])
    kb.observe(history['observation'],'')
    initial=coverage(kb.facts,graph);timeline=[dict(step=0,coverage=initial)]
    first={k:{n:0 for n in ns} for k,ns in initial.items()};used={};partial_ready={};registered=[]
    stat=dict(summary,game=task['game_name'],target=task['target_item'],seed=task['initial_seed'],depth=task['dependency_depth'],recipe_nodes=task['recipe_nodes'])
    counts=C.Counter({k:0 for k in ('cost_usd','input_tokens','output_tokens','cache_hit_tokens','api_failed_requests')});inspects=C.Counter();last_inspect={};current_no_progress=0;longest_no_progress=0
    actions=[];acquisition=[];decision_events=[];contexts=[];errors=[]
    first_death=None;first_native_failure=None;first_carry_harm=None;max_prompt=0
    reasons=C.Counter();tx=[]
    for row in rows:
        step=row['step'];ident=f"{task['task_id']}__{method}:a{step:03d}"
        p=parse_action(row['action']);fb=feedback_text(row['feedback']['text']);m=row['metrics']
        observer.table.observe(row['observation']);pre=public_frame(observer)
        before=coverage(kb.facts,graph)
        for q in [q for q in requests if q['step']==step]:
            facts,ids,records=context_facts(q,events)
            contexts.append(dict(evidence_id=ident,task_id=task['task_id'],method=method,step=step,
                request_id=q['request_id'],coverage=coverage(facts,graph),public_before=before,
                native_evidence_ids=ids,system_recipe_ids=records,prompt_tokens=q.get('usage',{}).get('prompt_tokens'),
                scope='attested literal fields only; not evidence of understanding'))
        publicfacts=copy.deepcopy(kb.facts)
        demand,status,sources=public_demand(observer,p.target)
        own=observer.ownership(p.target)
        ground_before=(observer.table.state.get('ground') or {}).get(p.target,0)
        risk=observer.consequences.check(observer,row['action'])
        past_risk_discards=[d for d in observer.consequences.discards if d['item']==p.target and d['risk_related']]
        observer.observe(row['observation'],row['action'],row['feedback'])
        consequence=observer.outcome18['consequence']
        d=kb.observe(row['feedback'],row['action'])
        assert coverage(kb.facts,graph)==coverage(row['public_knowledge_after'],graph)
        events.extend(dict(e,evaluation_step=step,evidence_id=ident) for e in d['events'])
        cov=coverage(kb.facts,graph);timeline.append(dict(step=step,coverage=cov))
        for k,ns in cov.items():
            for n in ns:first[k].setdefault(n,step)
        for oid,amount in m['actual_production'].items():
            if oid in graph and amount>0:used.setdefault(graph[oid]['name'],step)
        for key in ('invalid','craft_failed','material_rejection','station_rejection'):
            counts[key]+=int(m.get(key,False))
        counts['material_rejection_public']+=int(p.verb=='craft' and bool(re.search(r'Cannot craft a single|not enough|insufficient|do not have sufficient|missing.*material',fb,re.I)))
        counts['craft_attempts']+=p.verb=='craft';counts['productive_crafts']+=bool(m['actual_production'])
        counts['wait_actions']+=p.verb=='wait'
        repeated=p.verb=='inspect' and inspects[p.target]>0
        if p.verb=='inspect':
            counts['repeated_inspections']+=repeated
            counts['identical_feedback_repeat_inspections']+=last_inspect.get(p.target)==fb
            last_inspect[p.target]=fb;inspects[p.target]+=1
        hp_delta=row['physical_after']['health']-row['physical_before']['health']
        counts['hp_loss_events']+=hp_delta<0;counts['gross_hp_loss']+=max(0,-hp_delta)
        counts['explicit_carry_damage_events']+=bool(consequence['explicit_carrying_damage'])
        counts['explicit_carry_damage_reported_hp']+=consequence['explicit_carrying_damage']
        if consequence['explicit_carrying_damage'] and first_carry_harm is None:first_carry_harm=step
        if row['death'] and first_death is None:first_death=step
        if (row['death'] or row['done'] or row['physical_after']['health']<=0) and not row['success'] and first_native_failure is None:first_native_failure=step
        if d['new_relations'] or d['quantity_updates'] or m['actual_production'] or row['physical_after']['target_owned']>row['physical_before']['target_owned']:current_no_progress=0
        else:current_no_progress+=1;longest_no_progress=max(longest_no_progress,current_no_progress)
        if p.verb in ('pick up','store','take out','discard','drop'):
            actual=consequence['actual_acquired']
            record=dict(evidence_id=ident,task_id=task['task_id'],method=method,step=step,action=row['action'],
                verb=p.verb,item=p.target,requested=requested(row['action']),
                actual_acquired=actual,actual_transferred=consequence['actual_transferred'],
                known_demand=demand,demand_status=status,demand_sources=sources,
                owned_before=own,ground_before=ground_before,
                public_state_before=pre,risk_before=risk,feedback=fb,consequence=consequence,
                bulk_new_acquisition=actual>1,
                over_known_demand=bool(demand is not None and actual>max(0,demand-own['lower_bound'])),
                dangerous_acquisition=bool(actual>0 and consequence['explicit_carrying_damage']),
                reacquired_after_risk_discard=bool(actual>0 and past_risk_discards),
                harmful_reacquired_after_risk_discard=bool(actual>0 and past_risk_discards and consequence['explicit_carrying_damage']))
            if method=='SCAR18':
                audit=row['decision']['decision']['stage18']
                prior_action=audit.get('original_s1_candidate')
                prior=parse_action(prior_action or '')
                record.update(original_s1_action=prior_action,
                    original_s1_quantity=requested(prior_action) if prior.target==p.target and prior.verb in ('store','pick up','take out') else None,
                    selected_quantity=requested(row['action']),
                    original_llm_proposal=audit['llm_proposal'],arbitration_reason=audit['reason'],
                    matching_collection_candidates=[v for v in audit.get('acquisition_decisions',[]) if v['item']==p.target],
                    quantity_comparison_scope='Null original quantity means the original final candidate did not acquire this item; speculative candidate records are not executions.')
            acquisition.append(record)
            counts['actual_new_material_units']+=actual
            for name in ('bulk_new_acquisition','over_known_demand','dangerous_acquisition','reacquired_after_risk_discard','harmful_reacquired_after_risk_discard'):counts[name]+=record[name]
        table=row['decision'].get('controller',{}).get('table',row['decision'].get('table'))
        if table is not None:
            reg=coverage(table.get('knowledge',{}).get('facts',{}),graph)
            registered.append(dict(step=step,coverage=reg,public_before=before))
        if method=='SCAR18':
            audit=row['decision']['decision']['stage18'];summaryfacts=row['decision']['decision']['fact_summary']
            counts['changed_original_controller']+=audit.get('changed_original_controller',False)
            counts['changed_llm']+=audit.get('changed_llm',False)
            counts['restored_raw_llm']+=audit.get('changed_original_controller',False) and row['action']==audit['llm_proposal']
            counts['old_candidate_risk_rejected']+=audit.get('assessments',{}).get('original_controller',{}).get('risk',{}).get('status')=='REJECT'
            counts['unexecuted_probes_rolled_back']+=audit.get('transaction',{}).get('dropped_probe_count',0)
            counts['acquisition_amount_reduced_steps']+=any(r['selected_quantity']<r['original_quantity'] for r in audit.get('acquisition_decisions',[]))
            counts['bounded_summary_record_changes']+=bool(summaryfacts['added_record_ids'] or summaryfacts['omitted_old_record_ids'])
            counts['public_nominal_condition_rejected_steps']+=any(any(c['kind']=='nominal_single_craft_material' and c['status']=='REJECT' for c in v['conditions']) for v in audit.get('assessments',{}).values())
            reasons[audit['reason']]+=1
            assert len(summaryfacts['records'])<=48 and summaryfacts['characters']<=6000
            request=[q for q in requests if q['step']==step and q['status']=='ok'][-1]
            actualsystem='\n'.join(q['content'] for q in request['messages'] if q['role']=='system')
            assert all(json.dumps(r,ensure_ascii=False,separators=(',',':')) in actualsystem for r in summaryfacts['records'])
            transaction=audit.get('transaction',{})
            if transaction:
                assert transaction['attempt_history_unchanged'] and transaction['failures_unchanged']
                assert transaction['exploration_after']-transaction['exploration_before']==int(bool(transaction['executed_probe']))
                tx.append(ident)
            for n,ex in audit.get('execution_context',{}).get('execution',{}).items():
                if n not in names:continue
                nom=ex.get('nominal_material_conditions',[])
                if nom and not ex['blockers'] and all(c['status']=='SUPPORTED' for c in nom):partial_ready.setdefault(n,step)
            decision_events.append(dict(evidence_id=ident,task_id=task['task_id'],step=step,
                audit=audit,feedback=fb,mechanism_outcome=row.get('mechanism_outcome'),
                actual_production=m['actual_production'],new_relations=d['new_relations'],quantity_updates=d['quantity_updates'],
                hp_delta=hp_delta,success=row['success'],fact_summary=summaryfacts,
                actual_goal_material_gains={n:v-row['physical_before']['possessed'].get(n,0) for n,v in row['physical_after']['possessed'].items() if n in graph and v>row['physical_before']['possessed'].get(n,0)}))
        actions.append(dict(evidence_id=ident,task_id=task['task_id'],method=method,step=step,
            trajectory=str((path/'trajectory.jsonl.gz').relative_to(ROOT)),jsonl_line=step,
            requests=[q['request_id'] for q in requests if q['step']==step],action=row['action'],feedback=fb,
            before_hash=row['physical_before']['state_hash'],after_hash=row['state_hash'],metrics=m,
            public_before=before,public_after=cov,health_before=row['physical_before']['health'],health_after=row['physical_after']['health'],
            target_owned=row['physical_after']['target_owned'],target_produced=row['target_produced_during_task'],
            consequence=consequence,success=row['success']))
    # Retain the prompts of terminal failed logical calls at N+1 too; they have
    # no corresponding executed action but still consumed model context/cost.
    for req in (q for q in requests if q['step']>len(rows)):
        facts,ids,records=context_facts(req,events)
        contexts.append(dict(evidence_id=f"{task['task_id']}__{method}:unexecuted_request_{req['step']}",
            task_id=task['task_id'],method=method,step=req['step'],request_id=req['request_id'],
            coverage=coverage(facts,graph),public_before=coverage(kb.facts,graph),native_evidence_ids=ids,
            system_recipe_ids=records,prompt_tokens=req.get('usage',{}).get('prompt_tokens'),
            terminal_no_environment_action=True,scope='attested literal fields only; final paid attempts retained'))
    for req in requests:
        usage=req.get('usage',{})
        for src,dst in [('prompt_tokens','input_tokens'),('completion_tokens','output_tokens'),('prompt_cache_hit_tokens','cache_hit_tokens')]:counts[dst]+=usage.get(src,0)
        counts['cost_usd']+=req['charged_or_reserved_usd'];max_prompt=max(max_prompt,usage.get('prompt_tokens',0))
        counts['api_failed_requests']+=req['status']!='ok'
        if req['status']!='ok':errors.append(dict(task_id=task['task_id'],method=method,step=req['step'],request_id=req['request_id'],
            status=req['status'],reason=error_reason(req,requests),attempt=req['attempt'],cost=req['charged_or_reserved_usd'],
            recovered=any(x['logical_id']==req['logical_id'] and x['status']=='ok' for x in requests),
            path=str((path/'requests.jsonl.gz').relative_to(ROOT)),jsonl_line=requests.index(req)+1))
    for b in (60,80,100):stat['R'+str(b)]=bool(summary['success'] and summary['steps']<=b)
    stat.update(dict(counts),api_calls=len(requests),peak_input_tokens=max_prompt,
        first_death_event=first_death,first_native_failure=first_native_failure,first_carry_harm=first_carry_harm,
        longest_no_recorded_progress=longest_no_progress,arbitration_reasons=dict(reasons),
        target_made_not_obtained=bool(not summary['success'] and any(r['target_produced_during_task']>0 for r in rows)),
        context_first_tokens=requests[0].get('usage',{}).get('prompt_tokens') if requests else None,
        context_last_tokens=requests[-1].get('usage',{}).get('prompt_tokens') if requests else None)
    final=coverage(kb.facts,graph)
    complete=lambda k:max((first[k][n] for n in names),default=0) if names.issubset(first[k]) else None
    kn=dict(task_id=task['task_id'],method=method,goal=task['target_item'],scope=sorted(names),initial=initial,final=final,
        first=first,first_all_relations=complete('relation'),first_all_quantities=complete('quantity'),
        snapshots={str(b):dict(coverage=timeline[min(b,len(rows))]['coverage'],observed_through=min(b,len(rows)),terminated=len(rows)<b) for b in (20,40,60,80,100)},
        first_successful_craft=used,first_public_nominal_materials_and_known_station_subset_met=partial_ready,
        full_prerequisites_certified=None,
        latency_from_relation={n:used[n]-first['relation'][n] for n in used.keys()&first['relation'].keys()},
        latency_from_quantity={n:used[n]-first['quantity'][n] for n in used.keys()&first['quantity'].keys()},
        known_relation_not_crafted=sorted(set(final['relation'])-set(used)),
        unknown_quantities=sorted(names-set(final['quantity'])),
        complete_station_conditions_unconfirmed=sorted(n for n in names if kb.facts.get(n,{}).get('station_completeness')!='explicit_complete'),
        registered=registered,timeline=timeline,events=[e for e in events if e['product'] in names],
        note='Static closure can be bypassed by native intermediate supply. Full feasibility remains UNKNOWN; material checks concern public accounting and known station subset only. Uncrafted latencies are censored, not 100.')
    return stat,kn,actions,acquisition,decision_events,contexts,errors


def main():
    deny_network()
    tasks=load(RESULTS/'tasks.json');truth=load(ROOT/'results/stage17/evaluator_truth.json')
    histories={r['task_id']:r for r in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    allstats=[];knowledge=[];actions=[];acquisition=[];decisions=[];contexts=[];errors=[]
    for t in tasks:
        for method in METHODS:
            output=analyse(t,method,truth[t['task_id']],histories[t['task_id']])
            for bucket,part in zip((allstats,knowledge,actions,acquisition,decisions,contexts,errors),output):
                if isinstance(part,list):bucket.extend(part)
                else:bucket.append(part)
        print(t['task_id'],'six saved methods analyzed',flush=True)
    assert len(allstats)==144 and sum(r['method']=='SCAR18' for r in allstats)==24
    old={ (r['task_id'],r['method']):r for r in load(ROOT/'results/stage17/per_task.json')}
    for r in allstats:
        if r['method']=='SCAR18':continue
        for k in ('success','steps','api_calls','input_tokens','output_tokens','cost_usd','craft_failed','invalid','material_rejection','station_rejection','repeated_inspections'):
            assert abs(r.get(k,0)-old[r['task_id'],r['method']].get(k,0))<1e-7,(r['task_id'],r['method'],k)
    aggregate={}
    for method in METHODS:
        rr=[r for r in allstats if r['method']==method];kk=[r for r in knowledge if r['method']==method]
        agg={k:sum(r.get(k,0) for r in rr) for k in ('steps','R60','R80','R100','craft_attempts','productive_crafts','craft_failed','invalid','material_rejection','material_rejection_public','station_rejection','repeated_inspections','identical_feedback_repeat_inspections','wait_actions','api_calls','api_failed_requests','input_tokens','output_tokens','cache_hit_tokens','cost_usd','bulk_new_acquisition','over_known_demand','dangerous_acquisition','reacquired_after_risk_discard','harmful_reacquired_after_risk_discard','actual_new_material_units','hp_loss_events','gross_hp_loss','explicit_carry_damage_events','explicit_carry_damage_reported_hp','changed_original_controller','changed_llm','restored_raw_llm','old_candidate_risk_rejected','unexecuted_probes_rolled_back','acquisition_amount_reduced_steps','bounded_summary_record_changes','public_nominal_condition_rejected_steps')}
        successful=[r['steps'] for r in rr if r['success']]
        agg.update(n=24,success=sum(r['success'] for r in rr),success_steps_mean=S.mean(successful) if successful else None,
            success_steps_median=S.median(successful) if successful else None,
            native_failures=sum(r['status']=='game_failure' for r in rr),
            by_game={g:dict(success=sum(r['success'] for r in rr if r['game']==g),total=sum(r['game']==g for r in rr)) for g in ('robot_kingdom','quarantine')},
            statuses=dict(C.Counter(r['status'] for r in rr)),
            goal_relation_public=sum(k['goal'] in k['final']['relation'] for k in kk),
            goal_quantity_public=sum(k['goal'] in k['final']['quantity'] for k in kk),
            all_closure_relations_public=sum(k['first_all_relations'] is not None for k in kk),
            closure_relation_coverage_mean=S.mean(len(k['final']['relation'])/len(k['scope']) for k in kk),
            closure_quantity_coverage_mean=S.mean(len(k['final']['quantity'])/len(k['scope']) for k in kk),
            goal_relation_to_craft_latencies=[k['latency_from_relation'][k['goal']] for k in kk if k['goal'] in k['latency_from_relation']],
            goal_quantity_to_craft_latencies=[k['latency_from_quantity'][k['goal']] for k in kk if k['goal'] in k['latency_from_quantity']])
        aggregate[method]=agg
    lookup={(r['task_id'],r['method']):r for r in allstats};paired={}
    for method in ('A0','A1','A2','A3','A4'):
        cells=C.Counter();detail=[]
        for t in tasks:
            a,b=lookup[t['task_id'],'SCAR18'],lookup[t['task_id'],method]
            label='both_success' if a['success'] and b['success'] else 'only_SCAR18' if a['success'] else 'only_comparator' if b['success'] else 'both_failure'
            cells[label]+=1;detail.append(dict(task_id=t['task_id'],category=label,action_difference=a['steps']-b['steps'],cost_difference=a['cost_usd']-b['cost_usd']))
        paired[method]=dict(cells=dict(cells),tasks=detail)
    divergences=[]
    for t in tasks:
        a=read_gzip(folder(t,'A0')/'trajectory.jsonl.gz');b=read_gzip(folder(t,'SCAR18')/'trajectory.jsonl.gz')
        firstprop=next((i+1 for i,(x,y) in enumerate(zip(a,b)) if x['decision']['decision']['proposed_action']!=y['decision']['decision']['proposed_action']),None)
        actiondiff=next(((x,y) for x,y in zip(a,b) if x['action']!=y['action']),None)
        x,y=actiondiff if actiondiff else ({},{})
        divergences.append(dict(task_id=t['task_id'],first_proposal_difference=firstprop,
            first_action_difference=x.get('step'),old_action=x.get('action'),new_action=y.get('action'),
            same_physical_state_before=bool(x and x['physical_before']['state_hash']==y['physical_before']['state_hash']),
            old_proposal=x.get('decision',{}).get('decision',{}).get('proposed_action'),
            new_proposal=y.get('decision',{}).get('decision',{}).get('proposed_action'),
            interpretation='Descriptive first divergence; different prompts, stochastic proposals and controller histories preclude module-specific causal attribution'))
    write(RESULTS/'per_task.json',allstats);write(RESULTS/'knowledge.json',knowledge)
    write(RESULTS/'analysis.json',dict(methods=aggregate,paired=paired,divergences=divergences,complete=True,api_calls_for_analysis=0))
    write(RESULTS/'response_errors.json',errors)
    for name,values in [('evidence_index',actions),('acquisition_events',acquisition),('decision_events',decisions),('model_context_evidence',contexts)]:gzip_rows(RESULTS/(name+'.jsonl.gz'),values)
    fields=sorted(set().union(*(set(r) for r in allstats))-{'arbitration_reasons'})
    with (RESULTS/'per_task.csv').open('w') as f:
        writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader();writer.writerows(allstats)
    wide=[]
    for t in tasks:
        out={k:t[k] for k in ('task_id','game_name','target_item','initial_seed','dependency_depth','recipe_nodes')}
        for method in METHODS:
            r=lookup[t['task_id'],method]
            out.update({method+'_'+k:r.get(k,0) for k in ('status','success','steps','craft_failed','invalid','repeated_inspections','material_rejection','station_rejection','api_calls','input_tokens','output_tokens','cost_usd','dangerous_acquisition','first_native_failure')})
        wide.append(out)
    with (RESULTS/'paired_24.csv').open('w') as f:
        writer=csv.DictWriter(f,list(wide[0]));writer.writeheader();writer.writerows(wide)
    prior=load(RESULTS/'prior_manifest.json')['files'];assert all(sha(ROOT/p)==h for p,h in prior.items())
    write(RESULTS/'analysis_receipt.json',dict(site='server',passed=True,historical_runs_unchanged=120,all_runs=144,
        new_runs=24,new_api_calls=0,network_guard=True,historical_files_unchanged=len(prior),
        analyzed_actions=len(actions),new_decision_events=len(decisions),frozen_policy_unmodified=True))
    print({m:{k:a[k] for k in ('success','steps','cost_usd','native_failures','dangerous_acquisition')} for m,a in aggregate.items()})


if __name__=='__main__':main()
