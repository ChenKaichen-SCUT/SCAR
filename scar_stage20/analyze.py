"""Post-freeze offline statistics and reports; never imported by online agents."""
from collections import Counter, defaultdict
import copy
import csv
import json
import statistics
from .common import ROOT, RESULTS, REPORTS, load, write, read_gzip, gzip_rows, deny_network
from .planning import validate
from scar_stage19.analyze import public_cover, markdown, cell
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text

METHODS=('A0','SCAR18','SCAR19','SCAR20','A1','A2','A3','A4')
NAMES={'A0':'Stage17 SCAR','SCAR18':'SCAR18','SCAR19':'SCAR19','SCAR20':'SCAR20',
       'A1':'ReAct+STM','A2':'LongContext','A3':'AdaPlanner适配','A4':'Deterministic DAG'}


def ratio(n,d):return n/d if d else None
def f(value,d=3):return '—' if value is None else f'{value:.{d}f}'
def pct(value):return '—' if value is None else f'{100*value:.1f}%'


def analyse(task,truth):
    tid=task['task_id'];folder=RESULTS/'runs'/f'{tid}__SCAR20'
    summary=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz');requests=read_gzip(folder/'requests.jsonl.gz')
    terminal=load(folder/'terminal_decision.json')
    names={r['name'] for r in truth['recipes'].values()};id_names={k:r['name'] for k,r in truth['recipes'].items()}
    stat=dict(summary,game=task['game_name'],target=task['target_item'],seed=task['initial_seed'],
        depth=task['dependency_depth'],recipe_nodes=task['recipe_nodes'])
    counts=Counter();logical=defaultdict(list);errors=[];plans=[];evidence=[];ends={};intent_effects=defaultdict(lambda:dict(actions=[],new_recipes=[],crafted=[],possession_gains=[]))
    coverage=[];first={'relation':{},'quantity':{}};crafted={};streak=longest=0;inspected=Counter();recovery_states=Counter();context=[]
    initial=public_cover(rows[0]['public_knowledge_before'] if rows else {},names)
    coverage.append(dict(step=0,coverage=initial))
    for kind in first:first[kind]={name:0 for name in initial[kind]}
    for q in requests:
        logical[q['logical_id']].append(q);u=q.get('usage',{})
        counts['input_tokens']+=u.get('prompt_tokens',0);counts['output_tokens']+=u.get('completion_tokens',0)
        counts['cost_usd']+=q['charged_or_reserved_usd'];counts['retry_requests']+=q['attempt']>0
        counts['retry_cost_usd']+=q['charged_or_reserved_usd'] if q['attempt']>0 else 0
        counts['normalized_requests']+=bool(q.get('normalization_events'))
        counts['failed_response_cost_usd']+=q['charged_or_reserved_usd'] if q['status']!='ok' else 0
        if q['status']!='ok':errors.append(dict(task_id=tid,request_id=q['request_id'],step=q['step'],
            attempt=q['attempt'],category=q.get('interface_error_category','transport_or_other'),
            detail=q.get('interface_error_detail'),cost_usd=q['charged_or_reserved_usd'],
            recovered=any(z['logical_id']==q['logical_id'] and z['status']=='ok' for z in requests)))
    counts['api_calls']=len(requests);counts['api_failed_requests']=len(errors);counts['logical_subgoal_requests']=len(logical)
    for group in logical.values():
        counts['valid_logical_requests']+=group[-1]['status']=='ok'
        counts['unavailable_logical_requests']+=group[-1]['status']!='ok'
        counts['first_attempt_valid']+=group[0]['status']=='ok'
        try:validate(json.loads(group[0].get('raw_response',{}).get('choices',[{}])[0].get('message',{}).get('content','')))
        except (ValueError,TypeError):pass
        else:counts['first_attempt_strict_valid']+=1
    for row in rows:
        step=row['step'];d=row['decision']['decision'];c=row['decision']['controller'];m=row['metrics'];o=row['mechanism_outcome'];p=parse_action(row['action'])
        ident=f'{tid}__SCAR20:a{step:03d}'
        plans += [dict(task_id=tid,step=step,ordinal=i+1,evidence_id=ident,**copy.deepcopy(plan)) for i,plan in enumerate(d['planning_calls'])]
        counts['controller_only_actions']+=not d['llm_called'];counts['controller_only_nonwait_actions']+=not d['llm_called'] and p.verb!='wait'
        counts['wait_actions']+=p.verb=='wait';streak=streak+1 if p.verb=='wait' else 0;longest=max(longest,streak)
        counts['craft_attempts']+=p.verb=='craft';counts['productive_crafts']+=bool(m['actual_production'])
        for k in ('craft_failed','station_rejection','material_rejection','invalid'):counts[k]+=bool(m[k])
        if p.verb=='inspect':counts['repeated_inspections']+=inspected[p.target]>0;inspected[p.target]+=1
        counts['death_events']+=row['death'];counts['material_loss_events']+=bool(m.get('unaccounted_resource_loss'))
        counts['unaccounted_resource_units_lost']+=sum(m.get('unaccounted_resource_loss',{}).values())
        counts['gross_hp_loss']+=max(0,row['physical_before']['health']-row['physical_after']['health'])
        gains={n:v-row['physical_before']['possessed'].get(n,0) for n,v in row['physical_after']['possessed'].items() if v>row['physical_before']['possessed'].get(n,0)}
        transfer=bool(gains) and p.verb in ('pick up','store','take out')
        counts['possession_gain_actions']+=transfer
        counts['possession_units_gained']+=sum(gains.values()) if transfer else 0
        recovery_states[d['recovery']['state']]+=1
        for record in c['intent_log20']+o['latest_intent_end']:ends[record['id']]=record
        active=d['active_subgoal']
        if active and d['stage20']['source']=='persistent_subgoal':
            effect=intent_effects[active['id']];effect['actions'].append(step)
            effect['new_recipes']+=row['knowledge_delta']['new_relations']
            if m['actual_production']:effect['crafted'].append(dict(step=step,production=m['actual_production']))
            if transfer:effect['possession_gains'].append(dict(step=step,gains=gains))
        cov=public_cover(row['public_knowledge_after'],names);coverage.append(dict(step=step,coverage=cov))
        for kind in first:
            for name in cov[kind]:first[kind].setdefault(name,step)
        for oid,quantity in m['actual_production'].items():
            if quantity>0 and oid in id_names:crafted.setdefault(id_names[oid],step)
        for plan in d['planning_calls']:
            records=plan['evidence_snapshot']['records']
            context.append(dict(step=step,status=plan['status'],public_before=public_cover(row['public_knowledge_before'],names),
                controller_before=public_cover(c['table']['knowledge']['facts'],names),
                structured_prompt_relations=sorted(r['key'] for r in records if r['kind']=='recipe' and r['key'] in names and r['value'].get('ingredients'))))
        evidence.append(dict(evidence_id=ident,trajectory=str(folder.relative_to(ROOT)/'trajectory.jsonl.gz'),line=step,
            action=row['action'],feedback=feedback_text(row['feedback']['text']),source=d['stage20']['source'],
            planning_calls=d['planning_calls'],active_subgoal=active,recovery=d['recovery'],
            new_relations=row['knowledge_delta']['new_relations'],production=m['actual_production'],possession_gains=gains,
            craft_failed=m['craft_failed'],station_rejection=m['station_rejection'],material_rejection=m['material_rejection'],
            death=row['death'],done=row['done'],success=row['success']))
    tc=terminal['decision']['controller'];td=terminal['decision']['decision']
    if td.get('executed_action') is None:
        plans += [dict(task_id=tid,step=len(rows)+1,ordinal=i+1,evidence_id=f'{tid}__SCAR20:terminal',**copy.deepcopy(plan))
                  for i,plan in enumerate(td.get('planning_calls',[]))]
    for record in tc['intent_log20']:ends[record['id']]=record
    for active in (tc['intent20'],tc['suspended20']):
        if active and active['id'] not in ends:ends[active['id']]=dict(active,status='censored_at_episode_end',termination_reason=summary['status'])
    acceptances=tc['acceptance20'];accepted=[a for a in acceptances if a['accepted']]
    outcomes=[]
    for acceptance in accepted:
        end=copy.deepcopy(ends[acceptance['intent_id']]);end.update(task_id=tid,measured_effects=intent_effects[end['id']]);outcomes.append(end)
    counts['accepted_subgoals']=len(accepted);counts['rejected_subgoals']=len(acceptances)-len(accepted)
    counts['evidence_id_rejections']=sum(a['reason'] in ('unknown_evidence_id','future_evidence_id') for a in acceptances)
    counts['completed_subgoals']=sum(i['status']=='completed' for i in outcomes)
    counts['multi_step_subgoals']=sum(i['steps']>=2 for i in outcomes)
    counts['completed_multi_step_subgoals']=sum(i['steps']>=2 and i['status']=='completed' for i in outcomes)
    counts['subgoal_execution_actions']=sum(i['steps'] for i in outcomes)
    counts['failed_subgoals']=sum(i['status'] in ('blocked','failed','expired') for i in outcomes)
    counts['cancelled_subgoals']=sum(i['status']=='cancelled' for i in outcomes)
    counts['censored_subgoals']=sum(i['status']=='censored_at_episode_end' for i in outcomes)
    counts['subgoals_with_crafting_progress']=sum(bool(i['measured_effects']['crafted']) for i in outcomes)
    counts['subgoals_with_recipe_gain']=sum(bool(i['measured_effects']['new_recipes']) for i in outcomes)
    counts['subgoals_with_possession_gain']=sum(bool(i['measured_effects']['possession_gains']) for i in outcomes)
    counts['intent_productive_craft_actions']=sum(len(i['measured_effects']['crafted']) for i in outcomes)
    counts['intent_possession_gain_actions']=sum(len(i['measured_effects']['possession_gains']) for i in outcomes)
    counts['repeated_context_requests']=sum(max(0,v-1) for v in tc['context_counts20'].values())
    counts['repeated_subgoal_proposals']=sum(v-1 for v in Counter((a['proposal']['type'],a['proposal']['target'],a['proposal']['entry']) for a in acceptances).values())
    counts['repeated_failed_subgoals']=sum(v-1 for v in Counter((i['type'],i['target'],i['entry']) for i in outcomes if i['status'] in ('blocked','failed','expired')).values())
    prerequisites=[]
    for key,rec in tc['preconditions20'].items():
        r=copy.deepcopy(rec);r.update(task_id=tid,key=key)
        r['satisfied_latency']=None if r['first_satisfied_step'] is None else r['first_satisfied_step']-r['first_step']
        r['first_parent_craft_success_step']=next((x['step'] for x in rows if x['step']>r['first_step'] and parse_action(x['action']).target==r['product'] and x['metrics']['actual_production']),None)
        r['parent_in_material_closure']=r['product'] in names;prerequisites.append(r)
    counts['public_preconditions_discovered']=len(prerequisites)
    counts['public_preconditions_satisfied']=sum(r['first_satisfied_step'] is not None for r in prerequisites)
    counts['preconditions_with_parent_craft']=sum(r['first_parent_craft_success_step'] is not None for r in prerequisites)
    for k in ('api_calls','input_tokens','output_tokens','cost_usd','retry_cost_usd','failed_response_cost_usd','wait_actions',
              'repeated_inspections','craft_attempts','productive_crafts','craft_failed','station_rejection','material_rejection','invalid'):
        counts.setdefault(k,0)
    stat.update(counts);stat.update(longest_wait_streak=longest,controller_only_ratio=ratio(counts['controller_only_actions'],len(rows)),
        first_attempt_valid_rate=ratio(counts['first_attempt_valid'],len(logical)),
        trigger_counts=dict(Counter(p['trigger']['kind'] for p in plans)),
        rejection_reasons=dict(Counter(a['reason'] for a in acceptances if not a['accepted'])),
        recovery_states=dict(recovery_states),peak_input_tokens=max([q.get('usage',{}).get('prompt_tokens',0) for q in requests]+[0]),
        necessary_recipes_known=len(coverage[-1]['coverage']['relation']),necessary_recipes_total=len(names))
    for b in (60,80,100):stat['R'+str(b)]=summary['success'] and summary['steps']<=b
    knowledge=dict(task_id=tid,necessary_recipe_names=sorted(names),initial=initial,final=coverage[-1]['coverage'],first_public=first,
        first_craft=crafted,first_all_relations=max(first['relation'].values()) if names<=first['relation'].keys() else None,
        relation_to_craft_latency={n:crafted[n]-first['relation'][n] for n in crafted.keys()&first['relation'].keys()},
        quantity_to_craft_latency={n:crafted[n]-first['quantity'][n] for n in crafted.keys()&first['quantity'].keys()},
        known_not_crafted=sorted(set(coverage[-1]['coverage']['relation'])-set(crafted)),
        unknown_relations=sorted(names-set(coverage[-1]['coverage']['relation'])),
        unknown_quantities=sorted(names-set(coverage[-1]['coverage']['quantity'])),
        snapshots={str(b):dict(coverage=coverage[min(b,len(rows))]['coverage'],observed_through=min(b,len(rows))) for b in (20,40,60,80,100)},
        model_context=context,scope='Hidden metadata supplies necessity labels only; no hidden quantity/station enters the policy. Unfinished latencies are censored.')
    return stat,knowledge,evidence,plans,outcomes,prerequisites,errors


def aggregate(rows):
    numeric=set().union(*(set(k for k,v in r.items() if isinstance(v,(int,float)) and not isinstance(v,bool)) for r in rows))
    exclude={'seed','depth','recipe_nodes','started','finished','peak_input_tokens','longest_wait_streak','steps','controller_only_ratio','first_attempt_valid_rate'}
    a={k:sum(r.get(k,0) or 0 for r in rows) for k in numeric-exclude}
    success=[r['steps'] for r in rows if r['success']]
    a.update(n=len(rows),success=len(success),steps=sum(r['steps'] for r in rows),
        statuses=dict(Counter(r['status'] for r in rows)),success_steps_mean=statistics.mean(success) if success else None,
        success_steps_median=statistics.median(success) if success else None,
        native_failures=sum(r['status']=='game_failure' for r in rows),longest_wait_streak=max(r.get('longest_wait_streak',0) for r in rows),
        by_game={g:dict(success=sum(r['success'] for r in rows if r['game']==g),n=sum(r['game']==g for r in rows)) for g in ('robot_kingdom','quarantine')})
    for b in (60,80,100):a['R'+str(b)]=sum(r.get('R'+str(b),r['success'] and r['steps']<=b) for r in rows)
    a['api_calls_per_task']=a['api_calls']/len(rows)
    a['controller_only_ratio']=ratio(a.get('controller_only_actions',0),a['steps'])
    a['acceptance_rate']=ratio(a.get('accepted_subgoals',0),a.get('accepted_subgoals',0)+a.get('rejected_subgoals',0))
    a['multi_step_completion_rate']=ratio(a.get('completed_multi_step_subgoals',0),a.get('multi_step_subgoals',0))
    a['first_attempt_valid_rate']=ratio(a.get('first_attempt_valid',0),a.get('logical_subgoal_requests',0))
    a['execution_actions_per_valid_request']=ratio(a.get('subgoal_execution_actions',0),a.get('valid_logical_requests',0))
    return a


def main():
    deny_network();tasks=load(RESULTS/'tasks.json');truth=load(ROOT/'results/stage17/evaluator_truth.json')
    stats=[];knowledge=[];evidence=[];plans=[];intents=[];prereqs=[];errors=[]
    for task in tasks:
        s,k,e,p,i,pre,err=analyse(task,truth[task['task_id']])
        stats.append(s);knowledge.append(k);evidence+=e;plans+=p;intents+=i;prereqs+=pre;errors+=err
    historical=load(ROOT/'results/stage19/per_task.json');allstats=historical+stats
    lookup={(r['task_id'],r['method']):r for r in allstats}
    aggregates={m:aggregate([r for r in allstats if r['method']==m]) for m in METHODS}
    paired={}
    for m in METHODS:
        if m=='SCAR20':continue
        details=[]
        for t in tasks:
            a,b=lookup[t['task_id'],'SCAR20'],lookup[t['task_id'],m]
            category='both_success' if a['success'] and b['success'] else 'only_SCAR20' if a['success'] else 'only_comparator' if b['success'] else 'both_failure'
            details.append(dict(task_id=t['task_id'],category=category,step_delta=a['steps']-b['steps'],request_delta=a['api_calls']-b['api_calls'],cost_delta=a['cost_usd']-b['cost_usd']))
        paired[m]=dict(cells=dict(Counter(r['category'] for r in details)),tasks=details)
    type_counts={kind:dict(accepted=sum(r['type']==kind for r in intents),completed=sum(r['type']==kind and r['status']=='completed' for r in intents),
        multi_step=sum(r['type']==kind and r['steps']>=2 for r in intents),completed_multi_step=sum(r['type']==kind and r['steps']>=2 and r['status']=='completed' for r in intents))
        for kind in ('ACQUIRE_MATERIAL','LOCATE_PRECONDITION','CRAFT_PRECONDITION','INSPECT_OBJECT','EXPLORE_FRONTIER')}
    triggers=Counter(p['trigger']['kind'] for p in plans);rejections=Counter()
    for s in stats:rejections.update(s['rejection_reasons'])
    norm_rejected=0
    for p in plans:
        if p['status']=='ok' and not p['acceptance']['accepted']:
            qs=read_gzip(RESULTS/'runs'/f"{p['task_id']}__SCAR20/requests.jsonl.gz")
            norm_rejected+=any(q['step']==p['step'] and q['ordinal']==p['ordinal'] and q.get('normalization_events') for q in qs)
    common={}
    for m in ('SCAR18','SCAR19'):
        tids=[t['task_id'] for t in tasks if lookup[t['task_id'],'SCAR20']['success'] and lookup[t['task_id'],m]['success']]
        common[m]=dict(task_ids=tids,methods={name:aggregate([lookup[tid,name] for tid in tids]) for name in (m,'SCAR20')} if tids else {})
    analysis=dict(methods=aggregates,paired=paired,types=type_counts,triggers=dict(triggers),rejections=dict(rejections),
        normalized_then_decision_rejected=norm_rejected,error_categories=dict(Counter(e['category'] for e in errors)),
        common_success=common,api_calls_for_analysis=0,development_only=True)
    for name,data in [('analysis',analysis),('per_task',allstats),('knowledge',knowledge),('subgoal_outcomes',intents),('prerequisite_outcomes',prereqs),('response_errors',errors)]:write(RESULTS/(name+'.json'),data)
    gzip_rows(RESULTS/'evidence_index.jsonl.gz',evidence);gzip_rows(RESULTS/'planning_outcomes.jsonl.gz',plans)
    fields=sorted(set().union(*(set(r) for r in allstats)))
    with (RESULTS/'per_task.csv').open('w') as stream:
        w=csv.DictWriter(stream,fields,lineterminator='\n');w.writeheader();w.writerows(allstats)
    wide=[]
    for t in tasks:
        row={k:t[k] for k in ('task_id','game_name','target_item','initial_seed','dependency_depth','recipe_nodes')}
        for m in METHODS:
            for k in ('success','steps','status','api_calls','input_tokens','output_tokens','cost_usd','craft_failed','station_rejection','wait_actions','repeated_inspections'):
                row[m+'_'+k]=lookup[t['task_id'],m].get(k)
        wide.append(row)
    with (RESULTS/'paired24.csv').open('w') as stream:
        w=csv.DictWriter(stream,list(wide[0]),lineterminator='\n');w.writeheader();w.writerows(wide)
    reports(tasks,lookup,analysis,knowledge,intents,prereqs,evidence,errors)
    from .diagnostics import augment
    augment()
    write(RESULTS/'analysis_receipt.json',dict(passed=True,new_runs=24,historical_runs_read=168,evidence_actions=len(evidence),
        extra_api_calls=0,policy_modified=False,failed_tasks_rerun=False,scope='descriptive offline analysis'))
    print(json.dumps(aggregates['SCAR20'],ensure_ascii=False))


def reports(tasks,lookup,a,knowledge,intents,prereqs,evidence,errors):
    new=a['methods']['SCAR20'];old=a['methods']['SCAR19'];older=a['methods']['SCAR18']
    interface=load(RESULTS/'interface_regression.json');preflight=load(RESULTS/'preflight_local.json')
    def save(name,text):(REPORTS/(name+'.md')).write_text('# '+name+'\n\n'+text)
    comparison=markdown(['方法','成功','R@60/80/100','总动作','成功局均值/中位','实际请求','输入/输出token','协议费用美元'],[
        [NAMES[m],f"{v['success']}/24",f"{v['R60']}/{v['R80']}/{v['R100']}",v['steps'],f"{f(v['success_steps_mean'],1)}/{f(v['success_steps_median'],1)}",
         v['api_calls'],f"{v['input_tokens']}/{v['output_tokens']}",f(v['cost_usd'],6)] for m,v in a['methods'].items()])
    pairing=markdown(['对照','双方成功','仅SCAR20成功','仅对照成功','双方失败'],[
        [NAMES[m]]+[v['cells'].get(k,0) for k in ('both_success','only_SCAR20','only_comparator','both_failure')] for m,v in a['paired'].items()])
    table=markdown(['任务（种子；必要深度/配方数）']+[NAMES[m] for m in METHODS],[
        [f"{t['task_id']} ({t['initial_seed']}; {t['dependency_depth']}/{t['recipe_nodes']})"]+
        [f"{'成功' if (r:=lookup[t['task_id'],m])['success'] else '失败'} / {r['steps']}步 / {r['api_calls']}请求" for m in METHODS] for t in tasks])
    save('24任务性能对比',comparison+'\n'+table+'\n'+pairing+
        '\n全部失败、中止、预算保护和主动停止保留在24题分母。完整逐任务 token、费用、制作拒绝、重复检查与终止原因见 `per_task.csv`、`paired24.csv`。历史方法仅读冻结归档，没有重新采样；R列分别为固定24题分母下的成功数。\n')
    save('子目标解析接口修复',
        '正式接口六字段，不要求 completion；由控制器映射完成条件。证据用真实公开快照的内容哈希ID，保留来源与时间；不存在、未来或与入口无关的引用进入决策拒绝，不与JSON错误混为一谈。规范化只做固定无歧义转换，原始响应完整保留。\n\n'+
        markdown(['旧记录组','总数','接口迁移成功','通过公开决策检查'],[
            [k,v['total'],v['schema_restored'],v['public_decision_accepted']] for k,v in interface.items() if isinstance(v,dict) and 'total' in v])+
        f"\n错误接受边界：{interface['negative_mutations_rejected']} 个虚构对象／非法ID变体均被拒绝，另有未来、不相关、不可达、重复键等单元边界。不能据此宣称所有探索提案一定有任务价值。\n\n"
        '旧日志没有新版ID：上述数字是明确标注的离线迁移潜力，先严格读取原文，再把已命名入口绑定到实际公开记录；不猜模型将来会引用什么，不提升旧引文中的猜测。21条原始JSON语法错误不自动修复。完整逐例证据见 `interface_regression.jsonl.gz`。\n\n'+
        markdown(['正式指标','观察值'],[[k,new.get(k,0)] for k in ('logical_subgoal_requests','first_attempt_strict_valid','first_attempt_valid','normalized_requests','retry_requests','retry_cost_usd','api_failed_requests','unavailable_logical_requests','evidence_id_rejections')])+
        f"\n第一次尝试有效率（含允许的确定性规范化）{pct(new['first_attempt_valid_rate'])}；规范化后仍被语义拒绝 {a['normalized_then_decision_rejected']} 个。整局直接解析中止 {new['statuses'].get('model_parse_exception',0)} 局；三次不可用的逻辑请求记入回退审计。不能把语义拒绝下降或JSON可读等同任务进步。\n")
    trigger_table=markdown(['触发类型','逻辑请求记录数'],a['triggers'].items())
    save('按需LLM触发与规划机制',
        '执行顺序保留公开确定性FIFO，并在无可靠动作时展开当前未完成依赖；具体记录目标配方、材料路径、必要区域对象路径或已知执行条件阻塞。已知公开解决方式直接执行。公开候选仅提供探索入口，不宣称隐藏配方关联。\n\n'+trigger_table+
        f"\n本轮 {new['controller_only_actions']}/{new['steps']} 个真实动作无需模型（{pct(new['controller_only_ratio'])}）。接受 {new['accepted_subgoals']}、拒绝 {new['rejected_subgoals']} 个提案，接受率 {pct(new['acceptance_rate'])}。每个有效逻辑请求关联 {f(new['execution_actions_per_valid_request'])} 步意图执行，"
        f"意图执行期内实际生产动作 {new.get('intent_productive_craft_actions',0)} 次、持有量增加的收取动作 {new.get('intent_possession_gain_actions',0)} 次。这里只描述时序关联，不能解释为每个请求的因果增益。\n\n"
        '拒绝理由：`'+json.dumps(a['rejections'],ensure_ascii=False)+'`。\n\n'
        f"相同公开上下文的有限重规划 {new.get('repeated_context_requests',0)} 次；同类型/对象/入口的重复提案 {new.get('repeated_subgoal_proposals',0)} 次，重复失败意图 {new.get('repeated_failed_subgoals',0)} 次。所有触发、公开证据、引用和接受决定见 `planning_outcomes.jsonl.gz`。本轮无全局LLM排序、无多智能体、无每步强制模型调用。\n")
    types=markdown(['类型','接受','完成','实际至少2步','其中完成'],[[k]+[v[x] for x in ('accepted','completed','multi_step','completed_multi_step')] for k,v in a['types'].items()])
    pretable=markdown(['任务','制作物→必要区域对象','首次发现','首次满足','满足延迟','首次后续父制作'],[
        [r['task_id'],r['product']+'→'+r['required_object'],r['first_step'],r['first_satisfied_step'],r['satisfied_latency'],r['first_parent_craft_success_step']] for r in prereqs])
    save('多步子目标执行与停滞恢复',types+
        f"\n多步意图完成率 {pct(new['multi_step_completion_rate'])}（仅实际执行至少2步为分母；这是观察口径，不是强迫拆分动作或事先认证的多步难题集合）。全部接受意图执行 {new['subgoal_execution_actions']} 步，"
        f"{new['completed_subgoals']} 个完成，{new.get('failed_subgoals',0)} 个失败/阻塞/超限，{new.get('cancelled_subgoals',0)} 个取消，{new.get('censored_subgoals',0)} 个在整局结束时截尾。逐个生命周期见 `subgoal_outcomes.json` 与各局 `subgoals.jsonl.gz`、`recovery.jsonl.gz`。\n\n"
        f"wait={new['wait_actions']}，连续最长={new['longest_wait_streak']}；无目的等待占全部动作比例={pct(ratio(new['wait_actions'],new['steps']))}。本策略没有引入有目的wait，wait若出现也不能自动算进展。主动停止 {new['statuses'].get('method_stalled',0)} 局，须保留失败分母。\n\n"
        '预检两处旧停滞均不再形成连续wait，但短分支最终仍显式阻塞，未宣称任务已恢复。每上下文2次／全局24次逻辑规划、每次动作选择2次、每逻辑请求3次尝试；没有以无限调用替换无限等待。\n\n'+pretable+
        f"\n公开必要区域对象关系 {new['public_preconditions_discovered']} 个，实际满足 {new['public_preconditions_satisfied']} 个，后续父物品制作 {new.get('preconditions_with_parent_craft',0)} 个；它们不是三个可以相加的独立收益。条件对象类型仍可为UNKNOWN；满足某个对象不等于完整制作条件均已公开。\n")
    failure_text='全部任务均保留。停止类型与现场症状分开记录；不同随机模型路径不能被当成模块因果效应。\n\n'
    for t in tasks:
        r=lookup[t['task_id'],'SCAR20'];important=t['target_item'] in ('repair_kit','metal_strip','metal_plate','oil_bomb')
        if r['success'] and not important:continue
        k=next(v for v in knowledge if v['task_id']==t['task_id']);events=[e for e in evidence if e['evidence_id'].startswith(t['task_id']+'__')]
        failure_text+=f"\n## {t['task_id']}\n\nSCAR18 {lookup[t['task_id'],'SCAR18']['status']} / {lookup[t['task_id'],'SCAR18']['steps']}步；SCAR19 {lookup[t['task_id'],'SCAR19']['status']} / {lookup[t['task_id'],'SCAR19']['steps']}步；SCAR20 **{r['status']} / {r['steps']}步**。\n\n"
        failure_text+=f"未公开必要配方：{', '.join(k['unknown_relations']) or '无'}；已公开但未制作：{', '.join(k['known_not_crafted']) or '无'}。静态材料链可由现成材料绕过，不将未制作每个中间物自动视作失败原因。\n\n"
        selected={e['evidence_id']:e for e in [x for x in events if x['craft_failed']][:2]+events[-3:]}
        for e in selected.values():failure_text+=f"- `{e['evidence_id']}` `{e['action']}`（{e['source']}）：{cell(e['feedback'][:700])}\n"
        terminal=load(RESULTS/'runs'/f"{t['task_id']}__SCAR20/terminal_decision.json")
        failure_text+='\n最终控制器恢复状态：`'+json.dumps(terminal['decision']['controller']['recovery20'],ensure_ascii=False)+'`。\n'
    failure_text+='\n响应异常明细：\n\n'+markdown(['任务','动作选择步','尝试','类型','后续恢复','费用'],[
        [e['task_id'],e['step'],e['attempt'],e['category'],e['recovered'],f(e['cost_usd'],6)] for e in errors])
    save('解析异常与失败任务分析',failure_text)
    save('费用和完整复现',
        f"实际模型请求 {new['api_calls']} 次、逻辑请求 {new['logical_subgoal_requests']} 次；输入 {new['input_tokens']}、输出 {new['output_tokens']} token，协议费用 ${new['cost_usd']:.9f}。重试请求 {new.get('retry_requests',0)} 次、追加重试费用 ${new.get('retry_cost_usd',0):.9f}；失败响应费用 ${new.get('failed_response_cost_usd',0):.9f}（两者可重叠）。费用按每次返回usage及冻结单价重算，不等同支付平台发票。\n\n"
        '所有原始请求、响应、JSON规范化和费用见各局 `requests.jsonl.gz`、`normalization_events.jsonl.gz` 及 `cost_ledger.json`。共享SQLite逐请求预留，全局3美元／单局0.25美元；所有失败与停止都计入消耗。\n\n'
        '在本地已安装的固定依赖环境中：\n\n```bash\nbash scripts/run_stage20.sh analyze\nbash scripts/run_stage20.sh verify\n```\n\n'
        '上述命令禁止网络，只用保存的轨迹重算。原生回放命令：`bash scripts/run_stage20.sh replay --site local --runtime runtime/stage20/recheck`，不执行策略和模型。已有正式结果不得删除后重采样。`freeze.json` 约束唯一策略与24题；`artifact_manifest.json` 覆盖分析代码和产物。\n\n'
        f"冻结前：{preflight['unit_tests']}项测试、{preflight['historical_factual_steps']}历史动作、{preflight['selected_states']}状态／{preflight['native_branch_actions']}原生分支动作、{preflight['serialization_checks']}恢复检查。完整本地原生回放及独立核验见 `replay_local.json`、`verification.json`。完整实现、原始记录和报告上传GitHub；下载依赖、虚拟环境、密钥与私有运行快照不上传。\n")
    change=[]
    for m in ('SCAR18','SCAR19'):
        gains=[r['task_id'] for r in a['paired'][m]['tasks'] if r['category']=='only_SCAR20'];losses=[r['task_id'] for r in a['paired'][m]['tasks'] if r['category']=='only_comparator']
        change.append(f"对 {m}：新增成功 {len(gains)} 个（{', '.join(gains) or '无'}）；成功转失败 {len(losses)} 个（{', '.join(losses) or '无'}）。")
    common=[]
    for m,v in a['common_success'].items():
        if not v['methods']:continue
        x,y=v['methods'][m],v['methods']['SCAR20'];common.append(f"双方均成功的 {len(v['task_ids'])} 题（{m}→SCAR20）：动作 {x['steps']}→{y['steps']}，请求 {x['api_calls']}→{y['api_calls']}，费用 ${x['cost_usd']:.6f}→${y['cost_usd']:.6f}。")
    total=(f"24局唯一冻结 SCAR20 本地实验全部结束：**成功 {new['success']}/24，动作 {new['steps']}，模型请求 {new['api_calls']}，协议费用 ${new['cost_usd']:.6f}**。\n\n"+
        comparison+'\n本轮为已多次参与开发的24题、单次temperature=0.7模型路径。所有比较均为历史描述，未重新配对模型随机采样，无显著性／独立泛化／模块因果宣称。\n\n'
        '## RQ1：解析终止是否减少？\n\n'+
        f"Stage19的8局直接解析中止变为 {new['statuses'].get('model_parse_exception',0)} 局。第一次尝试有效率 {pct(new['first_attempt_valid_rate'])}；付费无效响应 {new.get('api_failed_requests',0)} 次，最终不可用逻辑请求 {new.get('unavailable_logical_requests',0)} 个。仍需区分接口成功、证据ID合法和有价值的执行，不能合并成单一成功率。\n\n"
        '## RQ2：是否继续节省调用，是否以等待或早停换取？\n\n'+
        f"请求 SCAR18 {older['api_calls']}、SCAR19 {old['api_calls']}、SCAR20 {new['api_calls']}；wait {old['wait_actions']}→{new['wait_actions']}；本轮主动停止 {new['statuses'].get('method_stalled',0)} 局。任务成功 SCAR18 {older['success']}、SCAR19 {old['success']}、SCAR20 {new['success']}。早停确实存在，低动作数不能全部归因效率；本轮费用实际高于SCAR19。\n\n"+
        '\n\n'.join(common)+'\n\n共同成功子集为事后选择，仅作补充，不能替代全部24题分母。\n\n'
        '## RQ3：多步意图及工作台解决是否进步？\n\n'+types+
        f"\n意图执行期发现配方的意图 {new.get('subgoals_with_recipe_gain',0)} 个、出现实际制作 {new.get('subgoals_with_crafting_progress',0)} 个、出现持有量增加 {new.get('subgoals_with_possession_gain',0)} 个。公开区域前提满足 {new['public_preconditions_satisfied']}/{new['public_preconditions_discovered']}，详情分别列发现、满足和父物品制作。正式轨迹中的材料获取意图完成数为0、工作台制作意图接受数为0，因此尚无这两类机制获得任务收益的证据；接口已稳定，不能再把此不足归因于JSON解析。\n\n"
        '## RQ4：具体阻碍触发与有效进展？\n\n'+trigger_table+
        f"\n本轮接受率 {pct(new['acceptance_rate'])}，每有效逻辑请求关联 {f(new['execution_actions_per_valid_request'])} 步意图执行；已验证多步意图完成率 {pct(new['multi_step_completion_rate'])}。具体触发本身是工程可审计性改进，其任务效果必须与上述执行及成败一起看。未做消融，因此不能由同时改动的历史样本断言触发机制单独更有效。\n\n"
        '## RQ5：全部任务的正负变化与剩余问题？\n\n'+'\n\n'.join(change)+'\n\n'+
        markdown(['指标','SCAR18','SCAR19','SCAR20'],[[k,older.get(k),old.get(k),new.get(k)] for k in
            ('craft_failed','station_rejection','material_rejection','repeated_inspections','wait_actions','native_failures','material_loss_events','gross_hp_loss')])+
        '\n世界物品减少包含NPC/环境变化，不能直接称为策略造成的库存损失；知识已公开却未生产的条目与配方公开→制作延迟见 `knowledge.json`。未公开的数量／区域条件仍为UNKNOWN，不填隐藏真值。重点四题及所有失败均有动作序号和原始反馈。\n\n'
        '完整原生回放、独立无网络核验和旧文件哈希检查随结果发布。本轮不因新成绩调整策略、补跑失败或启动后续版本。\n')
    save('实验总报告',total)


if __name__=='__main__':main()
