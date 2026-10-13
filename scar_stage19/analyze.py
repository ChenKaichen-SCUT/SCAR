"""Post-freeze offline analysis; never imported by a policy or formal runner.

Hidden evaluator metadata labels necessary recipe names only. No hidden values
are used to fill public knowledge or fed back to any action selector.
"""
import collections as C
import csv
import json
import re
import statistics as S
from .common import ROOT, RESULTS, REPORTS, load, write, read_gzip, gzip_rows, deny_network
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text

METHODS=('A0','SCAR18','SCAR19','A1','A2','A3','A4')
NAMES={'A0':'Stage17 SCAR','SCAR18':'SCAR18','SCAR19':'SCAR19','A1':'ReAct+STM',
       'A2':'LongContext','A3':'AdaPlanner适配','A4':'Deterministic DAG'}


def avg(values): return S.mean(values) if values else None
def rate(n,d): return n/d if d else None
def fmt(value, digits=3): return '—' if value is None else f'{value:.{digits}f}'
def pct(value): return '—' if value is None else f'{100*value:.1f}%'
def cell(value): return str(value).replace('|','\\|').replace('\n',' ')
def markdown(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join(
        '| '+' | '.join(cell(v) for v in row)+' |\n' for row in rows)


def public_cover(facts,names):
    relation=sorted(n for n in names if facts.get(n,{}).get('ingredients') and facts[n].get('certainty')!='AMBIGUOUS_CONFLICT')
    quantity=sorted(n for n in relation if isinstance(facts[n].get('quantities'),dict))
    stations=sorted(n for n in names if facts.get(n,{}).get('stations'))
    return dict(relation=relation,quantity=quantity,known_required_object_subset=stations)


def analyse_task(task,truth):
    taskid=task['task_id']; folder=RESULTS/'runs'/f'{taskid}__SCAR19'
    summary=load(folder/'summary.json'); rows=read_gzip(folder/'trajectory.jsonl.gz'); requests=read_gzip(folder/'requests.jsonl.gz')
    successful_requests={q['step']:q for q in requests if q['status']=='ok'}
    assert len(rows)==summary['steps']<=100
    names={r['name'] for r in truth['recipes'].values()}
    oid_to_name={oid:r['name'] for oid,r in truth['recipes'].items()}
    stat=dict(summary,game=task['game_name'],target=task['target_item'],seed=task['initial_seed'],
              depth=task['dependency_depth'],recipe_nodes=task['recipe_nodes'])
    counts=C.Counter(); inspected=C.Counter(); last_feedback={}; sources=C.Counter()
    evidence=[]; acceptances=[]; ended={}; intent_progress={}; prereqs={}; context=[]
    timeline=[]; first={k:{} for k in ('relation','quantity')}; produced={}; produced_all={}; registry_first={}
    initial=public_cover(rows[0]['public_knowledge_before'] if rows else {},names)
    for kind in first:
        first[kind]={n:0 for n in initial[kind]}
    timeline.append(dict(step=0,coverage=initial)); streak=longest=0
    last_request_terminals=set(); previous_acceptance=None; trigger_counts=C.Counter(); replan_after=C.Counter()
    for row in rows:
        step=row['step']; action=row['action']; p=parse_action(action); fb=feedback_text(row['feedback']['text'])
        ident=f'{taskid}__SCAR19:a{step:03d}'; m=row['metrics']; d=row['decision']['decision']
        controller=row['decision']['controller']; outcome=row['mechanism_outcome']; source=d['stage19'].get('source')
        sources[source]+=1; counts['controller_only_actions']+=not d['llm_called']
        counts['controller_only_nonwait_actions']+=not d['llm_called'] and p.verb!='wait'
        counts['controller_only_wait_actions']+=not d['llm_called'] and p.verb=='wait'
        for key in ('invalid','craft_failed','material_rejection','station_rejection'):
            counts[key]+=bool(m.get(key))
        counts['craft_attempts']+=p.verb=='craft'; counts['productive_crafts']+=bool(m['actual_production'])
        counts['wait_actions']+=p.verb=='wait'
        counts['material_rejection_public']+=p.verb=='craft' and bool(re.search(r'Cannot craft a single|not enough|insufficient|do not have sufficient|missing.*material',fb,re.I))
        if p.verb=='inspect':
            counts['repeated_inspections']+=inspected[p.target]>0
            counts['identical_feedback_repeat_inspections']+=last_feedback.get(p.target)==fb
            inspected[p.target]+=1; last_feedback[p.target]=fb
        delta_hp=row['physical_after']['health']-row['physical_before']['health']
        counts['hp_loss_events']+=delta_hp<0; counts['gross_hp_loss']+=max(0,-delta_hp)
        counts['material_loss_events']+=bool(m.get('unaccounted_resource_loss'))
        counts['unaccounted_resource_units_lost']+=sum(m.get('unaccounted_resource_loss',{}).values())
        if row['death'] and stat.get('first_death_event') is None:stat['first_death_event']=step
        if not row['success'] and (row['death'] or row['done'] or row['physical_after']['health']<=0) and stat.get('first_native_failure') is None:
            stat['first_native_failure']=step
        cov=public_cover(row['public_knowledge_after'],names); timeline.append(dict(step=step,coverage=cov))
        for kind in first:
            for name in cov[kind]:first[kind].setdefault(name,step)
        registered=controller['table'].get('knowledge',{}).get('facts',{})
        for name in public_cover(registered,names)['relation']:registry_first.setdefault(name,step-1)
        for oid,amount in m['actual_production'].items():
            if amount>0:
                produced_all.setdefault(p.target,step)
                if oid in oid_to_name:produced.setdefault(oid_to_name[oid],step)
        progress=bool(row['knowledge_delta']['new_relations'] or row['knowledge_delta']['quantity_updates']
                      or m['actual_production'] or row['physical_after']['target_owned']>row['physical_before']['target_owned'])
        streak=0 if progress else streak+1; longest=max(longest,streak)
        if d['subgoal_acceptance']:
            acceptances.append(dict(evidence_id=ident,**d['subgoal_acceptance']))
        for terminal in controller.get('intent_log19',[]) + outcome.get('latest_intent_end',[]):
            ended[terminal['id']]=terminal
        active=d.get('active_subgoal')
        if source=='persistent_subgoal' and active:
            record=intent_progress.setdefault(active['id'],dict(steps=[],crafted_products=[],new_recipes=[],new_preconditions=[]))
            record['steps'].append(step)
            if m['actual_production']:record['crafted_products'].append(p.target)
            record['new_recipes']+=row['knowledge_delta']['new_relations']
            record['new_preconditions']+=outcome['new_preconditions']
        prereqs.update(copy_json(outcome.get('preconditions',{})))
        if d['llm_called']:
            # Structured evidence actually rendered in this request. This is a
            # lower bound, not an inference about model understanding/recall.
            prompt=successful_requests[step]['messages'][-1]['content']
            actual_records=[json.loads(line) for line in prompt.split('STRUCTURED PUBLIC EVIDENCE:\n',1)[1].splitlines()]
            visible_rules={r['key']:r['value'] for r in actual_records
                           if r.get('id','').startswith('recipe19:')}
            trigger_counts[d['planning_trigger'].get('kind','unspecified')]+=1
            before_terminals={r['id']:r for r in controller.get('intent_log19',[])}
            for terminal in (before_terminals[i] for i in before_terminals.keys()-last_request_terminals):
                replan_after[terminal['status']]+=1
            if previous_acceptance is not None and not previous_acceptance['accepted']:
                counts['logical_requests_after_previous_rejection']+=1
            previous_acceptance=d['subgoal_acceptance'];last_request_terminals=set(before_terminals)
            context.append(dict(evidence_id=ident,public_before=public_cover(row['public_knowledge_before'],names),
                controller_before=public_cover(registered,names),
                structured_prompt_relations=sorted(n for n,r in visible_rules.items() if n in names and r.get('ingredients')),
                record_count=len(actual_records),characters=d['fact_summary']['characters'],
                canonical_source='literal archived request messages, before post-response choose',
                secondary_summary_matches_literal_request=actual_records==d['fact_summary']['records'],
                scope='No-request steps are intentionally absent; not evidence of missing controller knowledge.'))
        evidence.append(dict(evidence_id=ident,trajectory=str(folder.relative_to(ROOT)/'trajectory.jsonl.gz'),
            line=step,action=action,feedback=fb,source=source,llm_called=d['llm_called'],
            trigger=d['planning_trigger'],acceptance=d['subgoal_acceptance'],active_subgoal=active,
            native_death=row['death'],native_done=row['done'],success=row['success'],
            known_relations=cov['relation'],new_relations=row['knowledge_delta']['new_relations'],
            production=m['actual_production'],station_rejection=m['station_rejection'],
            material_rejection=m['material_rejection'],unaccounted_resource_loss=m.get('unaccounted_resource_loss'),
            prerequisites=copy_json(outcome.get('preconditions',{}))))
    for request in requests:
        usage=request.get('usage',{})
        counts['input_tokens']+=usage.get('prompt_tokens',0);counts['output_tokens']+=usage.get('completion_tokens',0)
        counts['cache_hit_tokens']+=usage.get('prompt_cache_hit_tokens',0)
        counts['cost_usd']+=request['charged_or_reserved_usd'];counts['api_failed_requests']+=request['status']!='ok'
    counts['api_calls']=len(requests)
    counts['logical_subgoal_requests']=len({r['logical_id'] for r in requests})
    accepted=[a for a in acceptances if a['accepted']]
    counts['accepted_subgoals']=len(accepted);counts['rejected_subgoals']=sum(not a['accepted'] for a in acceptances)
    for acceptance in accepted:
        ident=acceptance['intent_id']
        if ident not in ended:
            active=rows[-1]['mechanism_outcome'].get('active_intent') if rows else None
            ended[ident]=dict(active or {},id=ident,status='censored_at_episode_end',termination_reason=summary['status'])
        ended[ident]['measured_effects']=intent_progress.get(ident,{})
    accepted_ends=[ended[a['intent_id']] for a in accepted]
    counts['completed_subgoals']=sum(r['status']=='completed' for r in accepted_ends)
    counts['multi_step_subgoals']=sum(r.get('steps',0)>=2 for r in accepted_ends)
    counts['completed_multi_step_subgoals']=sum(r['status']=='completed' and r.get('steps',0)>=2 for r in accepted_ends)
    counts['subgoal_execution_actions']=sum(r.get('steps',0) for r in accepted_ends)
    counts['failed_subgoals']=sum(r['status'] in ('failed','blocked','expired') for r in accepted_ends)
    counts['subgoals_with_recipe_gain']=sum(bool(r.get('measured_effects',{}).get('new_recipes')) for r in accepted_ends)
    counts['subgoals_with_crafting_progress']=sum(bool(r.get('measured_effects',{}).get('crafted_products')) for r in accepted_ends)
    counts['censored_subgoals']=sum(r['status']=='censored_at_episode_end' for r in accepted_ends)
    proposals=C.Counter((a['proposal']['type'],a['proposal']['target'],a['proposal']['entry']) for a in acceptances)
    counts['repeated_subgoal_proposals']=sum(n-1 for n in proposals.values())
    # Each failure/discovery is traceable to actual feedback and action indexes.
    for key,rec in prereqs.items():
        rec['key']=key;rec['task_id']=taskid
        rec['parent_in_static_material_recipe_closure']=rec['product'] in names
        rec['discovery_evidence']=f"{taskid}__SCAR19:a{rec['first_step']:03d}" if rec['first_step'] else 'public_tutorial'
        rec['satisfied_latency']=None if rec['first_satisfied_step'] is None else rec['first_satisfied_step']-rec['first_step']
        first_success=next((r['step'] for r in rows if r['step']>rec['first_step'] and
            parse_action(r['action']).target==rec['product'] and bool(r['metrics']['actual_production'])),None)
        rec['first_parent_craft_success_step']=first_success
        rec['latency_to_parent_craft_success']=None if first_success is None else first_success-rec['first_step']
        rec['trace']=[e['evidence_id'] for e in evidence if e['line']>=rec['first_step'] and
                      (e['source']=='public_prerequisite' or parse_action(e['action']).target in (rec['product'],rec['required_object']))]
    final=timeline[-1]['coverage']
    knowledge=dict(task_id=taskid,necessary_recipe_names=sorted(names),initial=initial,final=final,
        first_public=first,first_structured_registration=registry_first,first_craft=produced,
        relation_to_craft_latency={n:produced[n]-first['relation'][n] for n in produced.keys()&first['relation'].keys()},
        quantity_to_craft_latency={n:produced[n]-first['quantity'][n] for n in produced.keys()&first['quantity'].keys()},
        known_not_crafted=sorted(set(final['relation'])-set(produced)),
        unknown_relations=sorted(names-set(final['relation'])),unknown_quantities=sorted(names-set(final['quantity'])),
        first_all_relations=max(first['relation'].values()) if names<=first['relation'].keys() else None,
        snapshots={str(b):dict(coverage=timeline[min(b,len(rows))]['coverage'],observed_through=min(b,len(rows))) for b in (20,40,60,80,100)},
        model_context=context,scope='Hidden closure labels necessity only; no hidden quantities/stations fill public facts. Unfinished latencies are censored.')
    stat.update(counts)
    for key in ('invalid','craft_failed','material_rejection','station_rejection','craft_attempts','productive_crafts',
                'wait_actions','repeated_inspections','api_calls','input_tokens','output_tokens','cost_usd',
                'logical_subgoal_requests','accepted_subgoals','completed_subgoals','controller_only_actions'):
        stat.setdefault(key,0)
    stat.update({f'R{b}':summary['success'] and summary['steps']<=b for b in (60,80,100)})
    stat.update(controller_only_ratio=rate(stat['controller_only_actions'],len(rows)),
        subgoal_acceptance_rate=rate(len(accepted),len(acceptances)),
        subgoal_completion_rate=rate(counts['completed_subgoals'],len(accepted)),
        actions_per_subgoal_call=rate(counts['subgoal_execution_actions'],counts['logical_subgoal_requests']),
        longest_no_recorded_progress=longest,action_sources=dict(sources),
        valid_request_triggers=dict(trigger_counts),terminal_events_before_replanning=dict(replan_after),
        goal_relation_to_craft_latency=knowledge['relation_to_craft_latency'].get(task['target_item']),
        public_preconditions_discovered=len(prereqs),public_preconditions_satisfied=sum(r['first_satisfied_step'] is not None for r in prereqs.values()),
        necessary_recipes_known=len(final['relation']),necessary_recipes_total=len(names),
        peak_input_tokens=max([q.get('usage',{}).get('prompt_tokens',0) for q in requests]+[0]))
    failure=None
    if not summary['success']:
        labels=[]
        if knowledge['unknown_relations']:labels.append('必要配方名称仍未全部公开（不等于已隔离唯一根因）')
        if knowledge['known_not_crafted']:labels.append('已有公开必要配方尚未完成制作')
        if any(r['first_satisfied_step'] is None for r in prereqs.values()):labels.append('公开区域前提未解除')
        if stat['material_rejection']:labels.append('真实材料不足制作拒绝')
        if stat.get('first_native_failure'):labels.append('原生终止／死亡')
        if stat['wait_actions'] or stat['repeated_inspections']:labels.append('出现 wait 或重复检查')
        if summary['status'] in ('method_exception','model_parse_exception','api_uncertain_abort','api_budget_abort','environment_exception','worker_crash'):
            labels.append('运行／API中止，保留在分母')
        key_evidence=[e for e in evidence if e['station_rejection'] or e['material_rejection'] or e['native_death'] or e['native_done']
                      or e['source']=='no_admissible_public_action' or e['acceptance'] and not e['acceptance']['accepted']]
        failure=dict(task_id=taskid,status=summary['status'],labels=labels,knowledge=knowledge,
                     prerequisites=list(prereqs.values()),evidence=key_evidence,last_actions=evidence[-5:],
                     interpretation='Observed overlapping symptoms; not strict causal attribution or proof of one module failure.')
    errors=[dict(task_id=taskid,request_id=q['request_id'],step=q['step'],attempt=q['attempt'],
                 status=q['status'],error_type=q.get('error_type'),http_status=q.get('http_status'),
                 charged_usd=q['charged_or_reserved_usd'],recovered=any(
                     z['logical_id']==q['logical_id'] and z['status']=='ok' for z in requests)) for q in requests if q['status']!='ok']
    # Re-parse saved bytes only, without repairing or replaying a failed request.
    from .planning import validate
    byid={q['request_id']:q for q in requests}
    for error in errors:
        q=byid[error['request_id']];choice=q.get('raw_response',{}).get('choices',[{}])[0]
        content=choice.get('message',{}).get('content','')
        error['finish_reason']=choice.get('finish_reason')
        try:
            parsed=json.loads(content)
        except json.JSONDecodeError as exc:
            error.update(offline_cause='invalid_JSON',offline_detail=str(exc),response_excerpt=content[:400])
        else:
            try:validate(parsed)
            except ValueError as exc:
                error.update(offline_cause='subgoal_schema_violation',offline_detail=str(exc),
                    proposed_type=parsed.get('type'),proposed_completion=parsed.get('completion'))
            else:error.update(offline_cause='transport_or_other',offline_detail=q.get('error_type'))
    return stat,knowledge,evidence,acceptances,accepted_ends,list(prereqs.values()),failure,errors


def copy_json(value): return json.loads(json.dumps(value))


def aggregate(rows):
    keys=('steps','R60','R80','R100','api_calls','input_tokens','output_tokens','cost_usd','craft_attempts',
          'productive_crafts','craft_failed','material_rejection','station_rejection','invalid','repeated_inspections',
          'wait_actions','controller_only_actions','logical_subgoal_requests','accepted_subgoals','rejected_subgoals',
          'completed_subgoals','multi_step_subgoals','completed_multi_step_subgoals','subgoal_execution_actions',
          'failed_subgoals','censored_subgoals','repeated_subgoal_proposals','subgoals_with_recipe_gain',
          'subgoals_with_crafting_progress','public_preconditions_discovered','public_preconditions_satisfied',
          'api_failed_requests','material_loss_events','unaccounted_resource_units_lost','gross_hp_loss')
    a={k:sum(r.get(k,0) for r in rows) for k in keys}
    for key in ('controller_only_nonwait_actions','controller_only_wait_actions','logical_requests_after_previous_rejection'):
        a[key]=sum(r.get(key,0) for r in rows)
    succ=[r['steps'] for r in rows if r['success']]
    a.update(success=len(succ),n=len(rows),success_steps_mean=avg(succ),success_steps_median=S.median(succ) if succ else None,
        api_calls_per_task=a['api_calls']/len(rows),controller_only_ratio=rate(a['controller_only_actions'],a['steps']),
        subgoal_acceptance_rate=rate(a['accepted_subgoals'],a['accepted_subgoals']+a['rejected_subgoals']),
        subgoal_completion_rate=rate(a['completed_subgoals'],a['accepted_subgoals']),
        multi_step_completion_rate=rate(a['completed_multi_step_subgoals'],a['multi_step_subgoals']),
        execution_actions_per_call=rate(a['subgoal_execution_actions'],a['logical_subgoal_requests']),
        native_failures=sum(r['status']=='game_failure' for r in rows),statuses=dict(C.Counter(r['status'] for r in rows)),
        by_game={g:dict(success=sum(r['success'] for r in rows if r['game']==g),n=sum(r['game']==g for r in rows))
                 for g in ('robot_kingdom','quarantine')})
    return a


def main():
    deny_network(); tasks=load(RESULTS/'tasks.json');truth=load(ROOT/'results/stage17/evaluator_truth.json')
    stats=[]; knowledge=[]; evidence=[]; acceptances=[]; intents=[]; prerequisites=[]; failures=[]; errors=[]
    for task in tasks:
        parts=analyse_task(task,truth[task['task_id']])
        s,k,e,a,i,p,f,er=parts; stats.append(s);knowledge.append(k);evidence+=e
        acceptances += [dict(task_id=task['task_id'],**r) for r in a]
        intents += [dict(task_id=task['task_id'],**r) for r in i]
        prerequisites+=p;errors+=er
        if f:failures.append(f)
    historical=load(ROOT/'results/stage18/per_task.json')
    for record in historical:
        if record['method']=='SCAR18':
            previous=read_gzip(ROOT/'results/stage18/runs'/f"{record['task_id']}__SCAR18/trajectory.jsonl.gz")
            record['material_loss_events']=sum(bool(r['metrics'].get('unaccounted_resource_loss')) for r in previous)
            record['unaccounted_resource_units_lost']=sum(sum(r['metrics'].get('unaccounted_resource_loss',{}).values()) for r in previous)
    allstats=historical+stats;lookup={(r['task_id'],r['method']):r for r in allstats}
    aggregates={m:aggregate([r for r in allstats if r['method']==m]) for m in METHODS}
    for method,a in aggregates.items():
        if method!='SCAR19':
            for key in list(a):
                if any(word in key for word in ('subgoal','preconditions','execution_actions_per_call','multi_step')):
                    a[key]=None
            a['logical_requests_after_previous_rejection']=None
            a['controller_only_nonwait_actions']=a['controller_only_wait_actions']=None
            if method!='SCAR18':
                for key in ('controller_only_actions','controller_only_nonwait_actions','controller_only_ratio',
                            'material_loss_events','unaccounted_resource_units_lost'):
                    a[key]=None
    paired={}
    for method in [m for m in METHODS if m!='SCAR19']:
        detail=[];cells=C.Counter()
        for t in tasks:
            a,b=lookup[t['task_id'],'SCAR19'],lookup[t['task_id'],method]
            label='both_success' if a['success'] and b['success'] else 'only_SCAR19' if a['success'] else 'only_comparator' if b['success'] else 'both_failure'
            cells[label]+=1;detail.append(dict(task_id=t['task_id'],category=label,step_delta=a['steps']-b['steps'],
                                              request_delta=a['api_calls']-b['api_calls'],cost_delta=a['cost_usd']-b['cost_usd']))
        paired[method]=dict(cells=dict(cells),tasks=detail)
    # First actual divergence is descriptive only; no random response equality assumption.
    divergences=[]
    for task in tasks:
        a=read_gzip(ROOT/'results/stage18/runs'/f"{task['task_id']}__SCAR18/trajectory.jsonl.gz")
        b=read_gzip(RESULTS/'runs'/f"{task['task_id']}__SCAR19/trajectory.jsonl.gz")
        pair=next(((x,y) for x,y in zip(a,b) if x['action']!=y['action']),None)
        if pair:
            x,y=pair;divergences.append(dict(task_id=task['task_id'],step=x['step'],
                same_physical_state=x['physical_before']['state_hash']==y['physical_before']['state_hash'],
                stage18_action=x['action'],stage19_action=y['action'],stage19_source=y['decision']['decision']['stage19']['source'],
                stage18_feedback=feedback_text(x['feedback']['text']),stage19_feedback=feedback_text(y['feedback']['text']),
                interpretation='Different sampled planners and policies; first divergence is not a module-specific causal estimate.'))
        elif len(a)!=len(b):
            k=min(len(a),len(b));x=a[k] if k<len(a) else None;y=b[k] if k<len(b) else None
            divergences.append(dict(task_id=task['task_id'],step=k+1,
                same_physical_state=a[k-1]['state_hash']==b[k-1]['state_hash'] if k else True,
                stage18_action=x['action'] if x else None,stage19_action=y['action'] if y else None,
                stage19_source=y['decision']['decision']['stage19']['source'] if y else lookup[task['task_id'],'SCAR19']['status'],
                stage18_feedback=feedback_text(x['feedback']['text']) if x else None,
                stage19_feedback=feedback_text(y['feedback']['text']) if y else None,
                interpretation='Identical archived action prefix; one run terminated before its next environment action. No invented action/feedback for the aborted choice.'))
    shared=[t['task_id'] for t in tasks if lookup[t['task_id'],'SCAR19']['success'] and lookup[t['task_id'],'SCAR18']['success']]
    shared_efficiency={m:aggregate([lookup[tid,m] for tid in shared]) for m in ('SCAR18','SCAR19')}
    analysis=dict(complete=True,methods=aggregates,paired=paired,divergences=divergences,api_calls_for_analysis=0,
        both_success_tasks=shared,both_success_efficiency=shared_efficiency,
        error_causes=dict(C.Counter(e['offline_cause']+': '+e.get('offline_detail','').split(': line')[0] for e in errors)))
    for name,data in [('per_task',allstats),('knowledge',knowledge),('analysis',analysis),('subgoal_outcomes',intents),
                      ('prerequisite_outcomes',prerequisites),('failures',failures),('response_errors',errors)]:write(RESULTS/(name+'.json'),data)
    gzip_rows(RESULTS/'evidence_index.jsonl.gz',evidence);gzip_rows(RESULTS/'subgoal_acceptance.jsonl.gz',acceptances)
    fields=sorted(set().union(*(set(r) for r in allstats))-{'arbitration_reasons','action_sources'})
    with (RESULTS/'per_task.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(allstats)
    wide=[]
    for task in tasks:
        entry={k:task[k] for k in ('task_id','game_name','target_item','initial_seed','dependency_depth','recipe_nodes')}
        for method in METHODS:
            entry.update({method+'_'+k:lookup[task['task_id'],method].get(k) for k in
                          ('success','steps','status','api_calls','input_tokens','output_tokens','cost_usd','craft_failed','station_rejection','repeated_inspections','wait_actions')})
        wide.append(entry)
    with (RESULTS/'paired24.csv').open('w') as stream:
        writer=csv.DictWriter(stream,list(wide[0]),lineterminator='\n');writer.writeheader();writer.writerows(wide)
    reports(tasks,lookup,analysis,knowledge,intents,prerequisites,failures,errors)
    write(RESULTS/'analysis_receipt.json',dict(passed=True,new_runs=24,historical_runs_read=144,total_rows=168,
        extra_api_calls=0,necessary_hidden_metadata_scope='recipe name labels only',evidence_actions=len(evidence),
        frozen_policy_modified=False,failed_tasks_rerun=False))
    print(json.dumps(aggregates['SCAR19'],ensure_ascii=False))


def reports(tasks,lookup,analysis,knowledge,intents,prereqs,failures,errors):
    REPORTS.mkdir(exist_ok=True)
    new,old=analysis['methods']['SCAR19'],analysis['methods']['SCAR18']
    pairing=analysis['paired']['SCAR18']; gained=[r['task_id'] for r in pairing['tasks'] if r['category']=='only_SCAR19'];lost=[r['task_id'] for r in pairing['tasks'] if r['category']=='only_comparator']
    comparison=markdown(['方法','成功','R@60 / 80 / 100','动作（含失败）','成功局均值/中位数','请求','输入/输出 token','协议费用美元'],[
        [NAMES[m],f"{a['success']}/24",f"{a['R60']}/24 · {a['R80']}/24 · {a['R100']}/24",a['steps'],
         f"{fmt(a['success_steps_mean'],1)} / {fmt(a['success_steps_median'],1)}",a['api_calls'],
         f"{a['input_tokens']} / {a['output_tokens']}",fmt(a['cost_usd'],6)] for m,a in analysis['methods'].items()])
    table=markdown(['任务（种子；深度/配方数）']+[NAMES[m] for m in METHODS],[
        [f"{t['task_id']} ({t['initial_seed']}; {t['dependency_depth']}/{t['recipe_nodes']})"]+
        [f"{'成功' if (r:=lookup[t['task_id'],m])['success'] else '失败'} / {r['steps']} 步 / {r['api_calls']} 请求" for m in METHODS] for t in tasks])
    pairs=markdown(['对照','双方成功','仅 SCAR19 成功','仅对照成功','双方失败'],[
        [NAMES[m]]+[p['cells'].get(k,0) for k in ('both_success','only_SCAR19','only_comparator','both_failure')]
        for m,p in analysis['paired'].items()])
    (REPORTS/'24任务性能对比.md').write_text('# 24任务完整配对结果\n\n'+comparison+'\n'+table+'\n'+pairs+
        '\n每格包含成功判定、实际动作数（失败也按实际消耗）、模型请求数。完整制作拒绝、无效动作、重复检查、token、费用和终止原因见 `results/stage19/per_task.csv` 与 `paired24.csv`。所有失败保留。\n\n历史方法直接读取冻结结果，没有本轮重跑；配对仅保证任务与物理种子一致，不是重新配对的随机模型采样。\n')
    intent_table=markdown(['任务','子目标','状态','实际步数','完成/中断理由'],[
        [r['task_id'],r.get('type','')+':'+r.get('target',''),r['status'],r.get('steps',0),r.get('termination_reason','')] for r in intents])
    rejection=C.Counter(a['reason'] for a in read_gzip(RESULTS/'subgoal_acceptance.jsonl.gz') if not a['accepted'])
    (REPORTS/'子目标规划与持续执行分析.md').write_text(
        '# 按需规划与持续执行\n\n'
        f"共 {new['api_calls']} 次实际模型请求（含失败尝试），{new['logical_subgoal_requests']} 个逻辑子目标请求；平均每局 {fmt(new['api_calls_per_task'],2)} 次。"
        f"{new['controller_only_actions']}/{new['steps']} 个环境动作未调用 LLM（{pct(new['controller_only_ratio'])}）。\n\n"
        f"全批有 {new['wait_actions']} 次 wait，其中 {new['controller_only_wait_actions']} 次未调用模型；控制器独立的非 wait 动作是 {new['controller_only_nonwait_actions']} 个，不能把所有免调用动作都视为有效进展。\n\n"
        f"接受 {new['accepted_subgoals']}、拒绝 {new['rejected_subgoals']}，接受率 {pct(new['subgoal_acceptance_rate'])}。"
        f"接受意图完成 {new['completed_subgoals']}，按全部接受意图计算完成率 {pct(new['subgoal_completion_rate'])}；"
        f"实际持续至少两步的意图 {new['multi_step_subgoals']} 个，其中完成 {new['completed_multi_step_subgoals']} 个。"
        f"意图累计执行 {new['subgoal_execution_actions']} 步，每次逻辑子目标调用对应 {fmt(new['execution_actions_per_call'],2)} 步意图执行。\n\n"
        f"失败／阻塞／超限意图 {new['failed_subgoals']}，结束时未完成而被截尾 {new['censored_subgoals']}；同类型、对象和入口的重复提案 {new['repeated_subgoal_proposals']} 次（不一定相同公开条件）。"
        f"执行期间发现配方的意图 {new['subgoals_with_recipe_gain']} 个，有实际制作进展的意图 {new['subgoals_with_crafting_progress']} 个。"
        '这些指标描述执行期间发生的事情，不证明每个进展由该提案因果引起。拒绝、原生失败、条件变化及 P3 收尾都在原始日志中保留。\n\n'
        '拒绝理由：`'+json.dumps(rejection,ensure_ascii=False)+'`。\n\n'+intent_table+
        '\n完整证据为 `subgoal_acceptance.jsonl.gz`、`subgoal_outcomes.json` 和各局 `subgoals.jsonl.gz`；不能仅凭接受率判断有效性。\n')
    trigger_counts=C.Counter(); replan_counts=C.Counter()
    for task in tasks:
        record=lookup[task['task_id'],'SCAR19'];trigger_counts.update(record['valid_request_triggers'])
        replan_counts.update(record['terminal_events_before_replanning'])
    kind_table=markdown(['意图类型','接受','完成','累计执行步'],[
        [kind,sum(r['type']==kind for r in intents),sum(r['type']==kind and r['status']=='completed' for r in intents),
         sum(r.get('steps',0) for r in intents if r['type']==kind)] for kind in
        ('ACQUIRE_MATERIAL','CRAFT_PRECONDITION','INSPECT_OBJECT','LOCATE_PRECONDITION','EXPLORE_FRONTIER')])
    with (REPORTS/'子目标规划与持续执行分析.md').open('a') as stream:
        stream.write('\n'+kind_table+'\n最终取得有效回复的 218 次逻辑请求，触发类别：`'+json.dumps(trigger_counts,ensure_ascii=False)+
            '`。两次有效规划请求之间结束的意图状态：`'+json.dumps(replan_counts,ensure_ascii=False)+
            f"`；前一次有效提案被拒绝后再次请求规划 {new['logical_requests_after_previous_rejection']} 次。这些事件可以重叠，计数不包含最终全部解析失败的 8 次逻辑请求；它们没有完成动作决策，完整提示仍保存在请求日志中。\n\n"
            '本批没有接受的 ACQUIRE_MATERIAL 或 CRAFT_PRECONDITION 意图，不能据此证明持续制造子目标已经奏效。\n')
    pretable=markdown(['任务','制作物 → 必要区域对象','发现步','首次满足步','解除延迟','后续首次制作成功步'],[
        [r['task_id'],r['product']+' → '+r['required_object'],r['first_step'],r['first_satisfied_step'],r['satisfied_latency'],r['first_parent_craft_success_step']] for r in prereqs])
    ktable=markdown(['任务','最终必要配方公开数','全部名称公开步','目标名称公开→制作延迟','已公开仍未制作'],[
        [r['task_id'],f"{len(r['final']['relation'])}/{len(r['necessary_recipe_names'])}",r['first_all_relations'],
         r['relation_to_craft_latency'].get(next(t['target_item'] for t in tasks if t['task_id']==r['task_id'])),','.join(r['known_not_crafted'])] for r in knowledge])
    (REPORTS/'前提依赖与知识执行分析.md').write_text(
        '# 公开前提与知识执行\n\n'
        f"记录 {len(prereqs)} 个公开的制作物—必要区域对象关系，其中 {sum(r['first_satisfied_step'] is not None for r in prereqs)} 个在轨迹中达到区域存在条件。"
        '该对象的全部类型、完整工作台列表及取得方法仍可能未知；这里只把真实公开条件的满足算作解除，不把 LLM 猜测算成知识。\n\n'+pretable+
        '\n空值表示轨迹结束前未观察到相应事件，不能用 100 补成延迟。满足某一对象条件不等于所有制作条件均已满足。\n\n'+ktable+
        '\n`knowledge.json` 分别保存公开反馈、控制器登记、实际模型请求中的结构化配方视图，以及 20/40/60/80/100 步覆盖。无模型调用的步骤不视为模型遗忘。隐藏完整配方只提供离线必要名称标签，不补全公开数量或区域前提；原生中间物品供给可能绕过静态制作链。\n\n'
        '名义数量与真实批量语义一致性未在本轮实现。具体前提发现、移动／制作动作与父任务恢复见 `prerequisite_outcomes.json` 的逐动作证据索引。\n')
    pre_actions=C.Counter(e['action'] for e in read_gzip(RESULTS/'evidence_index.jsonl.gz') if e['source']=='public_prerequisite')
    with (REPORTS/'前提依赖与知识执行分析.md').open('a') as stream:
        stream.write('\n正式前提驱动动作分布：`'+json.dumps(pre_actions,ensure_ascii=False)+'`。\n\n'
            '本批正式轨迹没有成功制作新的工作台／furnace。已满足的前提主要依赖公开地点移动，另有放置已持有区域对象与备料；不能将工程单元测试中的递归制作能力写成正式实证成功。'
            '`sharpened_blade` 在 17 个环境动作后，下一步子目标请求的三次响应均失败，因此未进入实际 furnace 构建验证。\n\n'
            '公开地图中的 `room` 来自原始 Quarantine 教程（例如退出教程前可见 furnace），属于历史公开观察；当前地图没有可用返回路线，不能据此假定那个 furnace 仍然可取得。此信息同样存在于各历史方法的公共前缀中。\n')
        mismatches=sum(not c['secondary_summary_matches_literal_request'] for k in knowledge for c in k['model_context'])
        stream.write(f'\n上下文审计发现 {mismatches} 个请求的次级 `fact_summary` 与实际发出的结构化提示不完全相同：它保存了可变表引用，随后 choose 更新了来源标签、最近观测步或材料排列。实际请求中的材料集合、数量和区域条件不变。知识分析以 `requests.jsonl.gz` 中的原始提示为准；逐项差异由独立核验输出 `context_snapshot_audit.json`。没有改写原始日志或冻结策略。\n')
    failtext='# 全部 SCAR19 失败任务审计\n\n不删除不利任务，不将未实现的理论改进当成本轮成绩。下列标签为真实轨迹中的重叠症状，不自动等同唯一根因。\n'
    for failure in failures:
        tid=failure['task_id'];oldrow=lookup[tid,'SCAR18'];newrow=lookup[tid,'SCAR19']
        failtext+=f"\n## {tid}\n\n终止：{failure['status']}，实际 {newrow['steps']} 步；SCAR18 历史结果：{'成功' if oldrow['success'] else '失败'} / {oldrow['steps']} 步。\n\n"
        failtext+='；'.join(failure['labels'])+'。\n\n'
        picks={e['evidence_id']:e for e in failure['evidence'][:2]+failure['evidence'][-3:]+failure['last_actions'][-2:]}
        for e in picks.values():
            failtext+=f"- `{e['evidence_id']}`：`{e['action']}`，来源 `{e['source']}`。原始反馈节选：{cell(e['feedback'][:850])}\n"
        failtext+='\n'
    failtext+='\n完整事件（不截断）保存在 `failures.json`、`evidence_index.jsonl.gz` 和原始轨迹中。不同随机模型路径的分叉只能描述，不能据此隔离严格机制因果。\n'
    failtext+='\n## 相对 SCAR18 的全部六个成败变化\n\n'+markdown(
        ['任务','SCAR18','SCAR19','首次实际分歧步','SCAR18 动作','SCAR19 动作／中止'],[
        [tid,f"{lookup[tid,'SCAR18']['status']} / {lookup[tid,'SCAR18']['steps']} 步",
         f"{lookup[tid,'SCAR19']['status']} / {lookup[tid,'SCAR19']['steps']} 步",
         (d:=next(r for r in analysis['divergences'] if r['task_id']==tid))['step'],
         d['stage18_action'],d['stage19_action'] or d['stage19_source']] for tid in gained+lost])
    failtext+='''
`charcoal_brick`：SCAR19 第 13 步收到缺少 war_bench 的真实拒绝，第 14 步 enter courtyard，第 15 步制作成功、第 16 步取得目标。SCAR18 第 15 步尝试 iron_nugget 失败，随后继续探索，至第 48 步原生终止。这个配对支持新执行路径的可行性，但没有隔离模型采样与控制器的各自贡献。

`pipe_handle`：SCAR19 第 14 步制作被缺少区域前提拒绝，第 15 步回 lobby，第 16 步制作、第 17 步取得目标。SCAR18 第 20 步终止，期间未发起 craft。SCAR19 直接取得公开可见的部分中间材料，不要求静态材料链中的每条配方都必须先发现。

`oil_bomb`：SCAR19 第 17 步缺 war_bench，第 18 步回 courtyard，第 19 步实际制作 charcoal_brick，第 21 步入库存放。第 39–100 步连续 62 次 wait，公开阻碍为 charite/charred_timber/rubble；这一阶段探索累计 9 次、逻辑请求 13 次，尚未到 18 次探索或 24 次请求上限，不能错误归因于额度耗尽。控制器在同公开上下文去重与无可执行入口下不再取得进展；库存仍有 charcoal_brick，公开配方也已齐全，但没有制作 rubble_chunk/oil_flask/oil_bomb。SCAR18 在第 36、43、46 步分别制作上述物品，第 47 步取得最终目标。没有同状态替代策略反事实，不能把失败全部归因于某一条去重或 FIFO 规则。

`repair_kit`、`metal_strip`、`metal_plate`：分别执行 13、7、7 步后，下一次逻辑规划的三个响应均未通过冻结解析，直接中止；尚未进入实际制作。SCAR18 分别在第 39、27、23 步成功。特别是 metal_plate 的前七个环境动作完全相同，首次执行分歧是 SCAR19 在第 8 次动作选择前中止，不能为其编造一个“错误环境动作”。

另一个严重停滞例子 `ruin_spear` 并非新退化任务：第 18–96 步连续 wait 共 79 次，最终真实死亡；此间探索累计 13 次、逻辑请求最高 15 次，也未耗尽固定上限。调用节省与停止学习／执行的问题在同一批记录中同时存在。
'''
    (REPORTS/'失败任务与成败变化.md').write_text(failtext)
    change=markdown(['指标','SCAR18','SCAR19'],[[key,old.get(key),new.get(key)] for key in
        ('success','steps','api_calls','input_tokens','output_tokens','cost_usd','craft_failed','station_rejection','repeated_inspections','wait_actions','native_failures')])
    total=('# SCAR19 实验总报告\n\n'
        f"唯一冻结版本已完成 24 个本地正式任务：成功 **{new['success']}/24**，共 **{new['steps']} 个环境动作、{new['api_calls']} 次模型请求**，"
        f"协议费用 **${new['cost_usd']:.6f}**。SCAR18 历史成绩为 14/24、876 个动作、885 次请求、$0.870619。\n\n"
        '**主要结论：按需调用已经实现，但本批未保持原完成率。8 局因新子目标接口的响应／解析失败而提前中止；总动作、费用及原生死亡下降都受提前中止影响，不能全部解释成效率或安全改进。**\n\n'
        '本轮为开发性验证：24 题均已参与之前开发／失败分析，temperature=0.7，未重新配对模型采样。以下是这批观察值，没有显著性检验，也不宣称独立泛化或严格机制因果。\n\n'+comparison+'\n'+change+
        '\n## RQ1：请求与费用是否减少，任务能力是否保持？\n\n'
        f"模型请求变化 {new['api_calls']-old['api_calls']:+d} 次（{100*(new['api_calls']/old['api_calls']-1):+.1f}%），"
        f"费用变化 ${new['cost_usd']-old['cost_usd']:+.6f}（{100*(new['cost_usd']/old['cost_usd']-1):+.1f}%），"
        f"成功数变化 {new['success']-old['success']:+d}。控制器独立动作比例 {pct(new['controller_only_ratio'])}。"
        '应同时考察成功变化与动作消耗，不能单凭减少请求宣布性能更好。\n\n'
        f"作为次级描述，双方均成功的 {len(analysis['both_success_tasks'])} 题中，动作 {analysis['both_success_efficiency']['SCAR18']['steps']} → {analysis['both_success_efficiency']['SCAR19']['steps']}，"
        f"请求 {analysis['both_success_efficiency']['SCAR18']['api_calls']} → {analysis['both_success_efficiency']['SCAR19']['api_calls']}，"
        f"费用 ${analysis['both_success_efficiency']['SCAR18']['cost_usd']:.6f} → ${analysis['both_success_efficiency']['SCAR19']['cost_usd']:.6f}。"
        '这个事后选定的共同成功子集呈现较低执行消耗，但不能替代全部 24 题评价或消除随机路径差异。\n\n'
        '## RQ2：接受后是否持续执行？\n\n'
        f"接受 {new['accepted_subgoals']} 个子目标，完成 {new['completed_subgoals']} 个；至少持续两步 {new['multi_step_subgoals']} 个，"
        f"其中完成 {new['completed_multi_step_subgoals']} 个。平均每个逻辑请求带来 {fmt(new['execution_actions_per_call'],2)} 步意图执行。"
        f"有制作进展的接受意图 {new['subgoals_with_crafting_progress']} 个。接受率 {pct(new['subgoal_acceptance_rate'])} 并不代表完成率。"
        '所有结束原因与逐动作来源均保留，P3 最终进展和真实风险／条件变化可以终止意图；没有以逐步 LLM 动作被 FIFO 覆盖的形式伪装新接口。\n\n'
        '## RQ3：公开区域前提是否转化为执行？\n\n'
        f"公开前提关系 {len(prereqs)} 个，其中 {sum(r['first_satisfied_step'] is not None for r in prereqs)} 个观察到满足，"
        f"{sum(r['first_parent_craft_success_step'] is not None for r in prereqs)} 个随后出现父物品制作成功。"
        '这三个阶段分别统计，不能把发现或移动直接算成制作成功。详见前提报告，尤其包含 sharpened_blade 的真实结果；没有用其历史工程分支替代正式成绩。\n\n'
        '正式结果主要支持已公开台面位置的确定性查找／移动；尚无新工作台制作成功的正式证据。`sharpened_blade` 在第 18 次动作选择时解析中止，未检验到 furnace 制作环节。\n\n'
        '## RQ4：与 SCAR18 相比哪些改善或退化？\n\n'
        f"新增成功：{', '.join(gained) or '无'}。\n\n退化任务：{', '.join(lost) or '无'}。\n\n"
        f"真实动作变化 {new['steps']-old['steps']:+d}；制作失败变化 {new['craft_failed']-old['craft_failed']:+d}；"
        f"区域前提制作拒绝变化 {new['station_rejection']-old['station_rejection']:+d}；原生失败局数变化 {new['native_failures']-old['native_failures']:+d}。"
        '失败局动作及成本全部计入，模型请求异常不隐藏。所有逐任务胜负见配对表。\n\n'
        f"wait 从 {old['wait_actions']} 增至 {new['wait_actions']}；本轮主要集中于 oil_bomb（62 次）与 ruin_spear（79 次）。这说明调用节省中有一部分来自停滞，不能记作有效自主执行。"
        f"世界物品在扣除动作自身制作消耗后仍减少的事件为 {new['material_loss_events']} 次（SCAR18 为 {old['material_loss_events']} 次）；"
        '它包含环境动态／NPC 影响，不等同于 Agent 丢失的库存或可归因浪费。\n\n'
        '## RQ5：剩余失败来自哪里？\n\n'
        f"剩余失败 {len(failures)} 局，逐局保留公开必要配方缺口、已知未执行、未解除前提、材料拒绝、原生死亡、重复／wait 和运行异常证据。"
        '这些因素可重叠；不能用最终失败反推某个模块必然有问题，也不能把没有隐藏配方视为实现缺陷。数量／批量一致性未在本轮专门修复。详细根因边界、动作序号和原始反馈见失败报告。\n\n'
        '本批不能说剩余失败“主要只是游戏环境问题”：12 个失败中 8 个直接以模型解析中止结束，这是新接口的工程可靠性瓶颈。其余原生失败／步数耗尽仍呈现知识缺口、资源条件和 wait 停滞；它们的独立因果权重无法由单次轨迹隔离。\n\n'
        '## 异常、费用与验证\n\n'
        f"本轮付费响应／格式／调用异常 {len(errors)} 次，{sum(e['recovered'] for e in errors)} 次所在逻辑请求后续取得有效回复；"
        '完整请求、响应、token 与费用见归档及 `response_errors.json`，计费含失败尝试。未选择性重跑失败任务，未调用历史基线，未做消融。'
        '全轨迹原生回放和独立进程最终审计收据分别为 `replay_local.json`、`verification.json`。\n\n'
        '离线对保存的响应重新执行冻结解析器，定位 48 次类型／完成条件不匹配、21 次不合法 JSON 和 3 次证据／不确定性字段格式违反约束。共 48 次失败尝试所属逻辑请求随后恢复，另 8 个逻辑请求连续三次失败造成任务中止。未修复或重新提交这些响应。\n\n'
        '零 API 工程预检、冻结配置、代码、原始轨迹、模型请求、账本、子目标和前提追踪、可重算统计均随仓库发布。完成后停止，不自动开发后续版本。\n')
    (REPORTS/'实验总报告.md').write_text(total)
    errortable=markdown(['任务','请求步/尝试','异常分类','原始解析原因','随后恢复','费用美元'],[
        [e['task_id'],f"{e['step']}/{e['attempt']+1}",e['offline_cause'],e['offline_detail'],e['recovered'],fmt(e['charged_usd'],6)] for e in errors])
    (REPORTS/'模型响应与解析异常审计.md').write_text('# 模型响应与解析异常审计\n\n'
        '仅对已保存原始响应运行 JSON 解析与冻结子目标校验器，不修复模型输出、不补发请求。阶段19新增接口没有用 action=wait 兼容旧接口，但可靠性不足。\n\n'
        '48 次类型和完成条件冲突中，模型常把 LOCATE_PRECONDITION 的入口“检查某物／到达某地”当作整个子目标完成，返回 INSPECTED 或 ARRIVED，违反冻结的 PUBLIC_PATH_OR_RECIPE 约束。'
        '21 次 JSON 语法错误主要出现在将结构化地图原文嵌入字符串证据列表时，键值引号或对象未正确转义。另 3 次违反证据／不确定性列表约束。'
        '这些是接口可靠性证据，不能都归为游戏失败。既有重试协议重复同一请求，最多三次；本轮保留这条协议，没有事后增加修复调用。\n\n'+errortable+
        '\n69 个格式已通过的提案还因证据无法在当次公开 prompt 中逐字定位而被控制器拒绝；这是决策拒绝，不是上述解析异常。不能将所有这种拒绝一概认定为合理或有害，需具体证据及同状态反事实才能确认局部损失。\n')
    (REPORTS/'复现指南.md').write_text('''# SCAR19 本地复现与审计

正式策略及执行协议冻结于 `results/stage19/freeze.json`；冻结代码提交 `f5ad135`。本地引擎与依赖使用 `requirements-cpu.lock`，引擎提交仍为 `248430692a9d4a61d38c6c03ab2126287faaf450`。

```bash
cd /mnt/Space0/AINative/scar_agentodyssey
# 以下为零 API 已存档数据检查，不启动新的正式采样。
bash scripts/run_stage19.sh replay --site local --runtime runtime/stage19/replay-check
bash scripts/run_stage19.sh analyze
bash scripts/run_stage19.sh verify
```

原任务逐条保存在 `results/stage19/tasks.json`，与 Stage17 字节／内容核对。24 局完整轨迹、请求、子目标和前提日志位于 `results/stage19/runs/`。`cost_ledger.json` 为账本导出。`per_task.csv` 包括本轮及 144 条历史方法记录；历史数据仅读取未重新生成样本。`paired24.csv` 为宽表；其他 JSON/JSONL 保存所有中间统计与证据定位。

原生回放直接调用引擎，不运行策略或模型，逐动作比较观察、状态哈希及“本任务制作且实际持有”的成功条件。最终验证在独立进程中禁止网络，核对冻结源码、旧文件、任务、请求类型、费用及报告。历史分支、开发测试和正式闭环明确区分。

本轮正式命令为 `bash scripts/run_stage19.sh batch --runtime /mnt/Space0/AINative/scar_agentodyssey/runtime/stage19 --workers 12 --key-path /mnt/Space0/AINative/miyao.txt`。它只处理唯一冻结的 24 个 SCAR19 任务；完成的成功或失败局都直接返回旧报告，不能通过重复运行实现选择性重采样。不要删除结果来重跑。

新分析代码在冻结后添加，不被正式策略／运行器导入；最终产物清单覆盖分析代码与全部结果。下载的引擎、虚拟环境、密钥及二进制物理快照不上传 GitHub，保留在本地；本轮未调用服务器计算。
''')


if __name__=='__main__':main()
