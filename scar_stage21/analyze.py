"""Offline complete-denominator evaluation; never imported by the policy."""
from .common import *
deny_network()
import copy
import json
import statistics
from collections import Counter
from .controller import Controller21
from . import knowledge
from .recovery import Recovery
from scar_v3.state import parse_action


def table(headers,rows):
    def cell(x):return str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+
        ['| '+' | '.join(cell(v) for v in r)+' |' for r in rows])+'\n'


def archive(stage,task):
    method=f'SCAR{stage}';folder=ROOT/f'results/stage{stage}/runs'/f"{task['task_id']}__{method}"
    s=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz');qs=read_gzip(folder/'requests.jsonl.gz')
    return s,rows,qs


def stats(stage,task):
    s,rows,qs=archive(stage,task);inspects=Counter();repeated=0
    for r in rows:
        p=parse_action(r['action'])
        if p.verb=='inspect':repeated+=inspects[p.target]>0;inspects[p.target]+=1
    out=dict(task_id=task['task_id'],method=f'SCAR{stage}',game=task['game_name'],target=task['target_item'],
        seed=task['initial_seed'],depth=task['dependency_depth'],recipe_nodes=task['recipe_nodes'],**{k:s[k] for k in ('success','status','steps')},
        api_calls=len(qs),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qs),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qs),
        cache_hit_tokens=sum(q.get('usage',{}).get('prompt_cache_hit_tokens',0) for q in qs),
        cost_usd=sum(q['charged_or_reserved_usd'] for q in qs),invalid=sum(bool(r['metrics']['invalid']) for r in rows),
        craft_attempts=sum(parse_action(r['action']).verb=='craft' for r in rows),
        productive_crafts=sum(bool(r['metrics']['actual_production']) for r in rows),
        craft_failed=sum(bool(r['metrics']['craft_failed']) for r in rows),repeated_inspections=repeated,
        hp_loss=sum(max(0,r['physical_before']['health']-r['physical_after']['health']) for r in rows),
        response_errors=sum(q['status']!='ok' for q in qs),
        prompt_characters=[len(q['messages'][-1]['content']) for q in qs])
    for n in (60,80,100):out[f'R{n}']=int(s['success'] and len(rows)<=n)
    return out


def aggregate(records):
    keys=('steps','api_calls','input_tokens','output_tokens','cache_hit_tokens','cost_usd','invalid','craft_attempts',
        'productive_crafts','craft_failed','repeated_inspections','hp_loss','response_errors','R60','R80','R100')
    out={k:sum(r[k] for r in records) for k in keys}
    out['success']=sum(r['success'] for r in records);out['tasks']=len(records)
    out['by_game']={g:sum(r['success'] for r in records if r['game']==g) for g in ('robot_kingdom','quarantine')}
    out['statuses']=dict(Counter(r['status'] for r in records))
    steps=[r['steps'] for r in records if r['success']]
    out['successful_mean_steps']=statistics.mean(steps) if steps else None
    out['successful_median_steps']=statistics.median(steps) if steps else None
    chars=[n for r in records for n in r['prompt_characters']]
    out['prompt_mean_characters']=statistics.mean(chars) if chars else 0
    out['prompt_max_characters']=max(chars,default=0)
    out['effective_craft_ratio']=out['productive_crafts']/out['craft_attempts'] if out['craft_attempts'] else None
    return out


def main():
    tasks=load(RESULTS/'tasks.json');all_stats=[stats(s,t) for s in (18,19,20,21) for t in tasks]
    current=[r for r in all_stats if r['method']=='SCAR21'];by={(r['method'],r['task_id']):r for r in all_stats}
    totals={f'SCAR{s}':aggregate([r for r in all_stats if r['method']==f'SCAR{s}']) for s in (18,19,20,21)}
    paired={}
    for s in (18,19,20):
        wins=[];losses=[];counts=Counter()
        for r in current:
            old=by[f'SCAR{s}',r['task_id']]
            label='both_success' if r['success'] and old['success'] else 'new_only' if r['success'] else 'old_only' if old['success'] else 'both_failure'
            counts[label]+=1
            if label=='new_only':wins.append(r['task_id'])
            if label=='old_only':losses.append(r['task_id'])
        paired[f'SCAR{s}']=dict(counts=dict(counts),new_successes=wins,regressions=losses)
    grants=[];failures=[];engineering=[];probes=[];rejects=[];errors=[];evidence=[]
    for t in tasks:
        tid=t['task_id'];folder=RESULTS/'runs'/f'{tid}__SCAR21'
        summary,rows,qs=archive(21,t);terminal=load(folder/'terminal_decision.json')
        raw=terminal['decision']['controller'];c=Controller21.from_dict(raw)
        for q in qs:
            if q['status']!='ok':errors.append(dict(task_id=tid,**q))
        for a in c.acceptance20:
            if not a['accepted']:rejects.append(dict(task_id=tid,**a))
        probes += [dict(task_id=tid,**p) for p in c.probe_log21]
        if c.probe21:probes.append(dict(task_id=tid,**c.probe21,status='censored_at_episode_end'))
        for g in c.etbr21.grants:
            event=copy.deepcopy(g);event['task_id']=tid;event['task_success']=summary['success']
            event['task_terminal_status']=summary['status'];event['scope']='observed temporal association; no paired intervention on this formal trajectory'
            branch_rows=[rows[x['step']-1] for x in g['actions']]
            fresh=[d for r in branch_rows for d in r['mechanism_outcome']['stage21']['new_evidence']]
            event['all_new_evidence']=fresh
            event['related_new_evidence']=[d for d in fresh if Recovery.relation(d,g['blocker'])!='UNKNOWN']
            event['probe_action_succeeded']=any(not x['is_transit'] and not rows[x['step']-1]['metrics']['invalid'] for x in g['actions'])
            event['hp_cost']=sum(max(0,r['physical_before']['health']-r['physical_after']['health']) for r in branch_rows)
            event['invalid_actions']=sum(bool(r['metrics']['invalid']) for r in branch_rows)
            event['direct_api_calls']=0;event['direct_api_cost_usd']=0
            before_grant=Controller21.from_dict(rows[g['start_step']]['decision']['decision']['controller_before'])
            strict_entities=before_grant._all_needed(g['blocker']['subject'])
            for place,data in before_grant.table.places.items():
                if set(data['objects']) & strict_entities:strict_entities.add(place)
            trigger=g['evidence']
            event['strict_blocker_entities']=sorted(strict_entities)
            event['trigger_has_specific_blocker_support']=trigger['subject'] in strict_entities or trigger['object'] in strict_entities
            event['trigger_scope_assessment']='BLOCKER_SPECIFIC' if event['trigger_has_specific_blocker_support'] else 'BROAD_GOAL_ONLY_NOT_CURRENT_BLOCKER_PROOF'
            # Reconstruct all downstream stages from the saved trace. The online
            # flag records the FIRST resolution (a path), and therefore does not
            # also mark later physical possession. Preserve that logging limit.
            event['online_material_gain_events']=copy.deepcopy(g['material_gains'])
            event['actual_material_gain_events']=[]
            event['reconstructed_actual_precondition_steps']=[]
            event['reconstructed_parent_resume_step']=None
            event['reconstructed_production_steps']=[]
            for r in rows[g['start_step']:]:
                step=r['step'];p=parse_action(r['action'])
                before_c=Controller21.from_dict(r['decision']['decision']['controller_before'])
                after_c=Controller21.from_dict(rows[step]['decision']['decision']['controller_before'] if step<len(rows) else raw)
                needed=before_c._all_needed(g['blocker']['subject'])
                gained={k:v-r['physical_before']['possessed'].get(k,0) for k,v in r['physical_after']['possessed'].items() if v>r['physical_before']['possessed'].get(k,0)}
                if p.verb in ('pick up','store','take out','buy') and p.target in needed and p.target!=t['target_item'] and gained:
                    event['actual_material_gain_events'].append(dict(step=step,action=r['action'],target=p.target,physical_possession_gain=gained,source='offline_actual_trace_public_dependency_at_action'))
                satisfied=bool((after_c.table.state.get('ground') or {}).get(g['blocker']['subject'],0)) if g['blocker']['requires_ground'] else after_c.ownership(g['blocker']['subject'])['lower_bound']>=g['blocker'].get('required_amount',1)
                if satisfied:event['reconstructed_actual_precondition_steps'].append(step)
                source=r['decision']['decision']['stage20'].get('source')
                if step>g['start_step']+len(g['actions']) and source in ('known_FIFO_execution','public_dependency_execution','P3_finish') and p.target in needed and not r['metrics']['invalid'] and event['reconstructed_parent_resume_step'] is None:
                    event['reconstructed_parent_resume_step']=step
                if p.target in needed|{t['target_item']} and r['metrics']['actual_production']:
                    event['reconstructed_production_steps'].append(step)
            event['progress_steps']=sorted({e['step'] for e in g['stage_events'] if e['stage']=='TASK_PROGRESS' and rows[e['step']-1]['metrics']['actual_production']})
            event['online_precondition_actual_steps']=[e['step'] for e in g['stage_events'] if e['stage']=='PRECONDITION_RESOLVED' and e['kind']=='actual_presence']
            event['precondition_actual_steps']=event['reconstructed_actual_precondition_steps'][:1]
            event['precondition_path_steps']=[e['step'] for e in g['stage_events'] if e['stage']=='PRECONDITION_RESOLVED' and e['kind']=='public_executable_path']
            event['zero_observed_benefit']=not event['related_new_evidence'] and not event['actual_material_gain_events'] and not event['progress_steps'] and not g['precondition_resolved']
            grants.append(event)
        for r in rows:
            audit=r['decision']['decision']['stage20'];selection=audit.get('stage21',{}).get('selection')
            if selection:
                engineering.append(dict(task_id=tid,step=r['step'],action=r['action'],source=audit['source'],selection=selection,
                    knowledge_delta=r['knowledge_delta'],new_typed_evidence=r['mechanism_outcome']['stage21']['new_evidence'],
                    invalid=r['metrics']['invalid'],feedback=r['mechanism_outcome']['feedback'],hp_loss=max(0,r['physical_before']['health']-r['physical_after']['health'])))
            evidence.append(dict(task_id=tid,step=r['step'],trajectory=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),line=r['step'],
                action=r['action'],before_hash=r['physical_before']['state_hash'],after_hash=r['state_hash'],
                new_evidence_ids=[d['evidence_id'] for d in r['mechanism_outcome']['stage21']['new_evidence']],selection=selection))
        if not summary['success']:
            entries=c.probe_entries();block=knowledge.blocker(c);eligible=c.etbr21.eligible(block)
            failures.append(dict(task_id=tid,target=t['target_item'],status=summary['status'],steps=len(rows),remaining_steps=100-len(rows),
                current_location=c.table.state.get('location'),health=rows[-1]['physical_after']['health'] if rows else None,
                risk=c.risk16,normal_exploration_spent=c.exploration_spent,credits_granted=len(c.etbr21.grants),
                blocker=block,last_etbr_check=c.etbr21.last_check,eligible_new_evidence=eligible,legal_public_entries=entries,
                pending_probe=c.probe21,last_probe=c.probe_log21[-1:] if c.probe_log21 else [],
                original_stop=terminal['decision']['decision'].get('recovery'),
                last_actions=[dict(step=r['step'],action=r['action'],feedback=r['mechanism_outcome']['feedback'],new_evidence=r['mechanism_outcome']['stage21']['new_evidence']) for r in rows[-10:]],
                interpretation='Current policy stopped; game unsolvability is not established. Public risk and remaining entries audited separately.'))
    counts=dict(triggers=len(grants),credits_granted=len(grants),credits_used=sum(bool(g['actions']) for g in grants),
        probe_actions=sum(g['probe_used'] for g in grants),transit_actions=sum(g['transit_used'] for g in grants),
        probe_action_success=sum(g['probe_action_succeeded'] for g in grants),
        with_any_new_knowledge=sum(bool(g['all_new_evidence']) for g in grants),with_related_new_knowledge=sum(bool(g['related_new_evidence']) for g in grants),
        new_knowledge_records=sum(len(g['all_new_evidence']) for g in grants),related_knowledge_records=sum(len(g['related_new_evidence']) for g in grants),
        with_material_acquisition=sum(bool(g['actual_material_gain_events']) for g in grants),
        with_actual_precondition=sum(bool(g['precondition_actual_steps']) for g in grants),with_public_path=sum(bool(g['precondition_path_steps']) for g in grants),
        with_parent_resumed=sum(g['parent_task_resumed'] for g in grants),with_actual_production=sum(bool(g['progress_steps']) for g in grants),
        with_final_task_success=sum(g['task_success'] for g in grants),
        final_success_tasks=sorted({g['task_id'] for g in grants if g['task_success']}),
        unique_material_action_events=len({(g['task_id'],x['step']) for g in grants for x in g['actual_material_gain_events']}),
        unique_production_events=len({(g['task_id'],s) for g in grants for s in g['reconstructed_production_steps']}),
        triggers_with_specific_blocker_evidence=sum(g['trigger_has_specific_blocker_support'] for g in grants),
        zero_observed_benefit=sum(g['zero_observed_benefit'] for g in grants),hp_cost=sum(g['hp_cost'] for g in grants),
        invalid_actions=sum(g['invalid_actions'] for g in grants),direct_model_calls=0,direct_cost_usd=0)
    now=totals['SCAR21']
    useful=counts['with_public_path']+counts['with_actual_precondition']+counts['with_parent_resumed']>0
    verdict='GO' if now['success']>14 and useful else 'PARTIAL' if now['success']>=13 and useful and now['cost_usd']<=totals['SCAR18']['cost_usd'] else 'NO-GO'
    results=dict(methods=totals,paired=paired,etbr=counts,research_decision=verdict,
        interpretation='single sample on repeatedly used development tasks; no engineering-vs-ETBR paid ablation; observed chains are not isolated causal effects',
        engineering=dict(evidence_rejects=len(rejects),rejection_reasons=dict(Counter(x['reason'] for x in rejects)),
            ordinary_transit_actions=sum(bool(x['selection']['is_transit']) and not x['selection']['grant_id'] for x in engineering),
            etbr_transit_actions=sum(bool(x['selection']['is_transit']) and bool(x['selection']['grant_id']) for x in engineering),
            ordinary_transits_with_new_evidence=sum(bool(x['selection']['is_transit']) and not x['selection']['grant_id'] and bool(x['new_typed_evidence']) for x in engineering)),
        failures=dict(statuses=dict(Counter(x['status'] for x in failures)),risk_stops=sum(x['risk'] and x['status']=='method_stalled' for x in failures),
            stalled_with_legal_entries=sum(x['status']=='method_stalled' and bool(x['legal_public_entries']) for x in failures),
            risk_stops_before_normal_quota=sum(x['status']=='method_stalled' and x['risk'] and x['normal_exploration_spent']<18 for x in failures)))
    write(RESULTS/'analysis.json',results);write(RESULTS/'task_statistics.json',all_stats)
    write(RESULTS/'etbr_chains.json',grants);write(RESULTS/'failure_audit.json',failures)
    write(RESULTS/'probe_lifecycles.json',probes);write(RESULTS/'formal_rejections.json',rejects)
    gzip_rows(RESULTS/'engineering_events.jsonl.gz',engineering);gzip_rows(RESULTS/'evidence_index.jsonl.gz',evidence)
    gzip_rows(RESULTS/'response_errors.jsonl.gz',errors)
    reports(results,current,by,grants,failures)
    print(json.dumps(results,ensure_ascii=False))


def reports(result,current,by,grants,failures):
    REPORTS.mkdir(exist_ok=True)
    totals=result['methods'];now=totals['SCAR21'];counts=result['etbr']
    stamp='基于Stage20A提交 `2b272295ff2453ff970fd80e709b28479b379687`；本轮仅运行SCAR21一次24题。Stage18—20成绩读取历史冻结结果。24题已反复用于开发，不是独立泛化集。\n\n'
    def save(name,text):(REPORTS/(name+'.md')).write_text('# '+name+'\n\n'+stamp+text.rstrip()+'\n')
    perf=table(['方法','成功/24','Robot/15','Quarantine/9','R@60/80/100','全部动作','成功均值/中位','请求','输入/输出token','协议美元'],[
        [m,f"{s['success']}/24",s['by_game']['robot_kingdom'],s['by_game']['quarantine'],f"{s['R60']}/24, {s['R80']}/24, {s['R100']}/24",s['steps'],
         f"{s['successful_mean_steps']}/{s['successful_median_steps']}",s['api_calls'],f"{s['input_tokens']}/{s['output_tokens']}",f"{s['cost_usd']:.9f}"] for m,s in totals.items()])
    paired=table(['任务','种子','深度/配方节点','18','19','20','21','21状态','动作','请求','输入/输出','美元'],[
        [r['task_id'],r['seed'],f"{r['depth']}/{r['recipe_nodes']}",*['成功' if by[f'SCAR{s}',r['task_id']]['success'] else '失败' for s in (18,19,20)],
         '成功' if r['success'] else '失败',r['status'],r['steps'],r['api_calls'],f"{r['input_tokens']}/{r['output_tokens']}",f"{r['cost_usd']:.8f}"] for r in current])
    efficiency=table(['方法','制作尝试/实际产出','制作拒绝','无效动作','重复检查','全任务累计HP损失'],[
        [m,f"{s['craft_attempts']}/{s['productive_crafts']}",s['craft_failed'],s['invalid'],s['repeated_inspections'],s['hp_loss']] for m,s in totals.items()])
    save('24任务性能比较',perf+'\n'+paired+'\n'+efficiency+'\n逐任务配对计数与新增/退化任务：\n\n```json\n'+json.dumps(result['paired'],ensure_ascii=False,indent=2)+'\n```\n\n成功数、动作、费用均保留全部24题；早停会减少费用和动作，不能将失败任务少行动解释为效率提升。不同阶段的LLM随机轨迹不同，不能作严格因果结论。')
    save('工程修复与公开证据校验',
        '类型化校验识别names、from_location、route、对象位置、容器和公开依赖字段。入口须真实公开且存在当前路线；目标关联可为UNKNOWN。历史32次证据层误拒得到修复，5次合理假设保留，7次因类型/不可达问题继续拒绝；264个负例错误接受0。这是接口修正，不是算法创新。\n\n'
        '7局中转候选遗漏均通过公开BFS重新生成。到过中转地点不等于检查过目的地；尝试记录按当前阻碍和具体探索目的区分。已知锁门不凭空穿越，持有已知钥匙时保留S1取钥匙能力。cog_crossbow影子状态在14/18额度下恢复普通移动，未领ETBR额度。\n\n'
        '移除LLM材料链/工作台链持久意图，改为一次检查或访问加最多3次中转。原确定性材料、数量、区域对象、FIFO和100步P3保留。历史成功任务97个关键状态中95个选择一致，最终取物均保留；这不是整条轨迹等价证明。\n\n'
        '本次实现把risk16扩展成普通有限试探的统一禁行门槛，范围比仅约束ETBR更宽。15局失败全部在原18次额度用完前、仍有公开候选时被此门槛阻止。公开受伤/攻击反馈不等于每个候选行动都危险；这是本次实现的重大限制，不能将停滞归因于ETBR证据机制，也不能把它包装成安全收益。正式结果后未修改该门槛。\n\n'
        '正式运行有176次提案拒绝，其中82次already_inspected、88次no_untried_bounded_probe_entry。紧凑提示没有完整列出已检查集合及可选未尝试候选，存在提示与控制器门槛信息不对称；这与高重复/不可执行提案并存，但未做修改提示后的反事实验证。历史32次字段修正通过不等于当前规划接口已充分可用。\n\n'
        '正式工程事件：\n\n```json\n'+json.dumps(result['engineering'],ensure_ascii=False,indent=2)+'\n```\n\n可重算证据：`evidence_regression.json`、`negative_controls.json`、`transit_regression.json`、`engineering_events.jsonl.gz`、`formal_rejections.json`。')
    save('ETBR算法设计及实现',
        'ETBR使用一般PublicEvidenceDelta和执行阻碍接口。当前游戏适配器提取公开制作关系、材料历史位置、区域前提、地图连接与门锁条件。NPC对话和任务阶段仅通过公开结构化接口单测；没有可靠在线文本解析时返回UNKNOWN，不声称覆盖其他游戏。\n\n'
        '事实内容哈希不含时间戳。初始知识、重复检查、无关物品、模型猜测不能领额度。条件为：目标尚未解决；存在未消费且公开关联当前阻碍的新事实；存在合法、尚未充分尝试的入口；风险和剩余预算允许。\n\n'
        '冻结参数：原18次探索不变；每条新证据最多1个信用，跨阻碍也不重复使用；每阻碍最多2个，每局最多6个。每个信用最多1次有效试探加3次中转；每次实际动作均计入100步。最多24次逻辑模型请求、每次最多3次接口尝试；总$3、单局$0.25。ETBR自身确定性选入口，不额外请求模型。\n\n'
        '执行顺序：P3→可靠FIFO→公开依赖执行→已有有限试探→满足条件的ETBR→可用普通探索。多个普通未知入口时，可按需请求LLM提出一个试探；单入口与ETBR入口不需要模型。\n\n'
        '模型上下文最多8000字符/24条证据，输出最多512 token，不发送完整历史。阶段分别记录PROBE_COMPLETED、NEW_EVIDENCE_OBTAINED、PRECONDITION_RESOLVED（公共路径/真实持有分开）、PARENT_TASK_RESUMED、TASK_PROGRESS。相关性使用公开实体关系，不使用语义全局排名或隐藏地图。\n\n'
        '触发相关性实现的局限：适配器将整个目标依赖及相关地点都放入public_entities，范围大于当前具体阻碍的未完成链。唯一正式触发引用第9步发现charred_timber位于barracks，而第31步阻碍是oil_flask；该依据不能证明oil_flask的取得路径发生变化。故本轮实现尚未严格满足“改变当前阻碍可解决性”的强触发要求。该问题在结果审计中披露，冻结算法未修改。\n\n'
        '固定扩额不是ETBR；一次额外行动碰巧获得有用信息也不能验证本轮证据触发准则优于固定扩额。原生单步影子分支只用于工程验收，不进入24题成功率。')
    text='完整阶段计数（单位为恢复信用；同一后续实际制作可能关联多个信用，另给出去重动作数）：\n\n```json\n'+json.dumps(counts,ensure_ascii=False,indent=2)+'\n```\n\n'
    for g in grants:
        text+=f"## {g['task_id']} / {g['id']}\n\n第{g['start_step']+1}次选择由 `{g['evidence_id']}` 触发；阻碍 `{g['blocker']['subject']}`；依据：`{g['evidence']['subject']} {g['evidence']['relation']} {g['evidence']['object']}`。\n\n"
        text+=table(['动作步','实际动作','是否中转'],[[a['step'],a['action'],a['is_transit']] for a in g['actions']])
        text+='\n阶段事件：\n\n```json\n'+json.dumps(g['stage_events'],ensure_ascii=False,indent=2)+'\n```\n\n'
        text+=f"新增公开事实{len(g['all_new_evidence'])}条，其中与原阻碍有公开关联{len(g['related_new_evidence'])}条；实际材料增加事件{len(g['actual_material_gain_events'])}次；在线记录的制作步{g['progress_steps']}；HP代价{g['hp_cost']}；任务最终成功={g['task_success']}。\n\n"
        text+=f"严格触发依据核查：`{g['trigger_scope_assessment']}`。触发前具体阻碍闭包为 `{g['strict_blocker_entities']}`，不能因属于另一个目标依赖就宣称改变了当前阻碍的路径。\n\n"
        text+='从原始轨迹补齐的实际取得：\n\n'+table(['步数','动作','实际增加物品ID'],[[x['step'],x['action'],x['physical_possession_gain']] for x in g['actual_material_gain_events']])
        text+=f"\n离线补齐：原任务首次恢复动作在第{g['reconstructed_parent_resume_step']}步；实际持有/区域前提首次满足在{g['precondition_actual_steps']}步；公开依赖上的真实制作在{g['reconstructed_production_steps']}步。最终目标收取不计材料取得。在线事件只登记首次路径解除，漏掉了后来实际持有阶段；在线原日志保持不变，补齐结果单独标记。\n\n"
    if not grants:text+='本轮没有ETBR正式触发，不能用影子测试替代正式机制证据。\n'
    text+='\n`etbr_chains.json`保留全部触发证据、前后动作索引和阶段事件。模型调用为0的是ETBR直接执行本身，整局调用另计。后续持有/制作属于实际时序关联，未做同轨迹关闭ETBR的完整反事实，不能把它直接解释为独立机制因果收益。'
    save('探索恢复触发与执行证据',text)
    text='所有失败均保留。控制器无动作不等于游戏不可解。\n\n'+table(['任务','原因','已用/剩余动作','探索/18','ETBR信用','剩余HP','即时风险','剩余合法候选','未消费相关证据'],[
        [f['task_id'],f['status'],f"{f['steps']}/{f['remaining_steps']}",f['normal_exploration_spent'],f['credits_granted'],f['health'],f['risk'],len(f['legal_public_entries']),len(f['eligible_new_evidence'])] for f in failures])
    for f in failures:
        text+=f"\n## {f['task_id']}\n\n阻碍 `{f['blocker']['subject']}`；终止原因 `{f['status']}`；ETBR最后检查 `{json.dumps(f['last_etbr_check'],ensure_ascii=False)}`。\n\n"
        if f['risk'] and f['status']=='method_stalled':text+='公开反馈触发风险门槛，使新普通试探和ETBR均不可选。这是保守策略停止，尚未证明全部候选存在危险，也未证明世界无解。\n\n'
        text+=table(['动作步','动作','真实反馈'],[[r['step'],r['action'],r['feedback']] for r in f['last_actions']])
        text+='\n剩余公开候选：`'+json.dumps(f['legal_public_entries'],ensure_ascii=False)+'`。\n'
    save('失败任务与剩余停滞分析',text)
    costs=table(['方法','输入token','输出token','缓存命中token','请求','协议美元','提示均值字符','提示最长字符'],[
        [m,s['input_tokens'],s['output_tokens'],s['cache_hit_tokens'],s['api_calls'],f"{s['cost_usd']:.9f}",round(s['prompt_mean_characters'],1),s['prompt_max_characters']] for m,s in totals.items()])
    response_errors=read_gzip(RESULTS/'response_errors.jsonl.gz')
    error_table=table(['任务','动作选择步','付费尝试','类型','美元'],[
        [e['task_id'],e['step'],e['attempt'],e['interface_error_detail'],f"{e['charged_or_reserved_usd']:.9f}"] for e in response_errors])
    save('费用、回放与复现',costs+'\n'+error_table+
        '\n5次接口异常均是模型返回16个证据ID，超过冻结schema的6个上限；响应finish_reason均为stop，不是上下文超限或输出截断。每组下一次已审计请求恢复，未重跑环境任务。提示未显式列出6个ID上限，属于接口说明不完整。全部费用保留，不剔除无效响应。\n\n'+
        '\n协议费用按保存的API usage及冻结单价计算；不是服务商账单截图。共享SQLite预留确保全局$3、单局$0.25，计入解析失败和未知计费预留。`cost_ledger.json`为可上传账本，原始密钥与SQLite运行文件不上传。\n\n'
        '断点恢复保存物理RNG、控制器、公开知识、短期记忆和已支付回复缓存。最终失败不重采样。首次后台启动在正式阶段之前退出，没有请求或环境任务记录；随后从同一冻结协议启动原24局，没有重复正式局。\n\n'
        '冻结前23项测试、44次历史拒绝、264个负例、7局路径回归、11个停滞影子状态、97个历史执行状态均通过。7个原生单步影子动作和两游戏共4个初态动作验证记账/保存；不计作完整任务成绩。\n\n'
        '完整复现需要固定版本AgentOdyssey和既有依赖，设置SCAR_DEPENDENCIES。零网络离线命令：\n\n```bash\nbash scar_stage21/run.sh replay --site local --runtime runtime/stage21/replay\nbash scar_stage21/run.sh analyze\nbash scar_stage21/run.sh verify\n```\n\n'
        '完整24轨迹原生回放见`replay_local.json`；独立无网络核验见`verification.json`，核对初态、动作、反馈、哈希、公开决策及费用账本。原生引擎与旧文件哈希由冻结和保护清单核验。`freeze.json`冻结在线算法及运行代码；离线统计和报告代码随后新增，不参与正式策略。')
    conclusion=f"**研究判断：{result['research_decision']}。** SCAR21完成{now['success']}/24，Stage18为14/24、Stage20为12/24。模型请求{now['api_calls']}次，协议费用${now['cost_usd']:.9f}。\n\n"
    conclusion+=perf+'\n'+f"ETBR触发{counts['triggers']}次，{counts['with_related_new_knowledge']}次得到相关新知识，{counts['with_public_path']}次重新获得公开执行路径，{counts['with_actual_precondition']}次首次确认实际前提满足，{counts['with_material_acquisition']}次关联后续实际材料增加，{counts['with_actual_production']}次关联后续真实制作，{len(counts['final_success_tasks'])}个触发任务最终成功。后续事件可能重叠，不能相加；完整阶段分列于恢复报告。\n\n"
    conclusion+=f"失败分布：`{json.dumps(result['failures'],ensure_ascii=False)}`。\n\n"
    conclusion+='唯一恢复链中第31步inspect devil_oil确实公开oil_flask配方，随后第32步起恢复取材，第42步实际持有oil_flask，第43步制作、第44步取得oil_bomb。但触发证据是另一个目标依赖charred_timber的位置，缺少针对当时oil_flask阻碍的充分关联；因此不能宣称严格ETBR触发规则已被验证。\n\n'
    conclusion+='相对Stage20请求数从191增至227，增加36次；协议费用从$0.511070340降至$0.137500812，主要伴随提示压缩与提前停止。15个失败全部是普通试探风险门槛停止，原探索额度尚未耗尽且仍有公开候选。本次实现的风险门槛范围过宽、触发关联过宽和阶段日志过粗应作为实现缺陷披露。它们限制了机制实验的解释力。\n\n'
    if result['research_decision']=='NO-GO':
        conclusion+='当前不支持进入TTCL小规模开发实验。先解释剩余停止条件，尤其普通探索风险门槛与当前候选是否能继续；尚不能把这些工程限制混同于ETBR无效，也不能用便宜的提前失败声称效率优势。此次没有根据结果改动冻结策略、没有消融、补跑或基线重跑。\n\n'
    else:
        conclusion+='当前存在有条件的进一步开发信号；只有工程修复与ETBR收益分离、在独立任务和多种子上验证后，才可判断TTCL小规模实验价值。本轮尚未运行TTCL。\n\n'
    conclusion+='工程验收修复32次字段误拒、保留5次假设、拒绝7次不合法提案并恢复7局公开中转候选；这些不能作为ETBR论文创新。新机制的正式证据仅限实际保存的触发链，历史单步影子结果不替代正式成绩。所有24题保留，单次随机模型样本没有显著优劣结论。'
    save('实验总报告',conclusion)


if __name__=='__main__':main()
