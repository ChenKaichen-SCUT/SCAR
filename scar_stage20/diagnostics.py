"""Descriptive diagnostics from fixed archives; never imported by the policy."""
from collections import Counter
import json
import statistics
from .common import ROOT, RESULTS, REPORTS, load, write, read_gzip
from scar_stage19.analyze import markdown,cell


def augment():
    tasks=load(RESULTS/'tasks.json');task_by={t['task_id']:t for t in tasks}
    a=load(RESULTS/'analysis.json');stats=load(RESULTS/'per_task.json')
    lookup={(r['task_id'],r['method']):r for r in stats}
    plans=read_gzip(RESULTS/'planning_outcomes.jsonl.gz');intents=load(RESULTS/'subgoal_outcomes.json')
    intent_by={(i['task_id'],i['id']):i for i in intents};knowledge=load(RESULTS/'knowledge.json')
    k_by={k['task_id']:k for k in knowledge}
    traces={t['task_id']:read_gzip(RESULTS/'runs'/f"{t['task_id']}__SCAR20/trajectory.jsonl.gz") for t in tasks}
    def append(name,body):
        p=REPORTS/(name+'.md');p.write_text((p.read_text()+'\n'+body).rstrip()+'\n')
    costs={}
    for stage in ('stage19','stage20'):
        requests=[q for p in sorted((ROOT/'results'/stage/'runs').glob('*/requests.jsonl.gz')) for q in read_gzip(p)]
        inp=[q['usage']['prompt_tokens'] for q in requests];hit=sum(q['usage']['prompt_cache_hit_tokens'] for q in requests)
        costs[stage]=dict(requests=len(requests),mean_prompt_tokens=statistics.mean(inp),median_prompt_tokens=statistics.median(inp),
            peak_prompt_tokens=max(inp),total_prompt_tokens=sum(inp),cache_hit_tokens=hit,cache_hit_fraction=hit/sum(inp),
            finish_reasons=dict(Counter(q['raw_response']['choices'][0]['finish_reason'] for q in requests)),
            cost_usd=sum(q['charged_or_reserved_usd'] for q in requests))
    stops=[];comparison=[]
    for task in tasks:
        tid=task['task_id'];r=lookup[tid,'SCAR20'];term=load(RESULTS/'runs'/f'{tid}__SCAR20/terminal_decision.json')['decision']['controller']
        k=k_by[tid]
        stops.append(dict(task_id=tid,status=r['status'],steps=r['steps'],remaining_actions=100-r['steps'],
            exploration_spent=term['exploration_spent'],logical_requests=term['plan_calls20'],max_context_requests=max(term['context_counts20'].values(),default=0),
            blocker=term['blocker20'],recovery=term['recovery20'],health=traces[tid][-1]['physical_after']['health'],
            first_all_material_relations=k['first_all_relations'],unknown_relations=k['unknown_relations'],unknown_quantities=k['unknown_quantities'],
            known_not_crafted=k['known_not_crafted']))
        if not r['success'] or task['target_item'] in ('oil_bomb','repair_kit','metal_strip','metal_plate'):
            for stage,method in (('stage18','SCAR18'),('stage19','SCAR19')):
                old=read_gzip(ROOT/'results'/stage/'runs'/f'{tid}__{method}/trajectory.jsonl.gz');new=traces[tid]
                first=next((i for i,(x,y) in enumerate(zip(old,new)) if x['action']!=y['action']),min(len(old),len(new)))
                def branch(rows):
                    return [dict(step=x['step'],action=x['action'],feedback=x.get('mechanism_outcome',{}).get('feedback',x['feedback']['text']),
                        state_hash=x['state_hash']) for x in rows[first:first+3]]
                comparison.append(dict(task_id=tid,comparator=method,first_different_or_terminated_step=first+1,
                    common_prefix_actions=first,common_prefix_physical_hash_equal=first==0 or old[first-1]['state_hash']==new[first-1]['state_hash'],
                    comparator_branch=branch(old),SCAR20_branch=branch(new),
                    interpretation='Observed divergence of different policy/model trajectories; not a strict causal intervention'))
    trigger_effects={}
    for kind in sorted(a['triggers']):
        ps=[p for p in plans if p['trigger']['kind']==kind]
        accepted=[intent_by[p['task_id'],p['acceptance']['intent_id']] for p in ps if (p.get('acceptance') or {}).get('accepted')]
        trigger_effects[kind]=dict(requests=len(ps),accepted=len(accepted),completed=sum(i['status']=='completed' for i in accepted),
            actual_intent_actions=sum(i['steps'] for i in accepted),multi_step_completed=sum(i['steps']>=2 and i['status']=='completed' for i in accepted),
            intents_with_any_recipe_gain=sum(bool(i['measured_effects']['new_recipes']) for i in accepted),
            intents_with_necessary_recipe_gain=sum(bool(set(i['measured_effects']['new_recipes'])&set(k_by[i['task_id']]['necessary_recipe_names'])) for i in accepted),
            production_actions=sum(len(i['measured_effects']['crafted']) for i in accepted),
            possession_gain_actions=sum(len(i['measured_effects']['possession_gains']) for i in accepted))
    evidence_rejections=[]
    for p in plans:
        acc=p.get('acceptance')
        if not acc or acc['reason']!='evidence_unrelated_to_execution_entry':continue
        prop=p['proposal'];refs=acc['evidence_refs'];records=p['evidence_snapshot']['records']
        evidence_rejections.append(dict(task_id=p['task_id'],step=p['step'],ordinal=p['ordinal'],proposal=prop,refs=refs,
            target_supported_by_named_non_goal_reference=any(r['kind'] not in ('goal','blocker') and prop['target'] in r['names'] for r in refs),
            entry_named_elsewhere_in_prompt=any(prop['entry'] in r['names'] for r in records),
            entry_is_referenced_frontier_from_location=any(r['kind']=='public_frontier' and r['value'].get('from_location')==prop['entry'] for r in refs),
            scope='static citation-binding diagnostic only; no counterfactual execution or proof of harmful rejection'))
    oldk=load(ROOT/'results/stage19/knowledge.json');knowledge_summary={}
    for method,ks in (('SCAR19',oldk),('SCAR20',knowledge)):
        known_all=[k for k in ks if k['first_all_relations'] is not None]
        lat=[v for k in ks for v in k['relation_to_craft_latency'].values()]
        knowledge_summary[method]=dict(necessary_relation_instances=sum(len(k['final']['relation']) for k in ks),
            necessary_quantity_instances=sum(len(k['final']['quantity']) for k in ks),material_relations_complete_tasks=len(known_all),
            successful_after_complete_relations=sum(lookup[k['task_id'],method]['success'] for k in known_all),
            failed_despite_complete_material_relations=[k['task_id'] for k in known_all if not lookup[k['task_id'],method]['success']],
            completed_recipe_latency_count=len(lat),completed_recipe_latency_mean=statistics.mean(lat) if lat else None,
            completed_recipe_latency_median=statistics.median(lat) if lat else None)
    diagnostic=dict(costs=costs,terminal_states=stops,trigger_effects=trigger_effects,evidence_binding_rejections=evidence_rejections,
        knowledge_summary=knowledge_summary,trajectory_divergences=comparison,
        intent_terminal_statuses=dict(Counter(i['status'] for i in intents)),new_model_requests=0,policy_modified=False)
    write(RESULTS/'mechanism_diagnostics.json',diagnostic)
    # All appendices are regenerated by analyze; no manual result edits required.
    startup=('## 启动异常和授权例外\n\n首次启动24局都在真实首步之后、写轨迹时因日志字段错误中断，模型请求和费用为0。'
        '按用户明确授权，只把运行器 `outcome19` 改为 `outcome20`，经离线首步状态/公开反馈/控制器完全一致核验后，从原第2步继续。'
        '策略冻结提交为 `0df6661`，日志修复与续跑准备提交为 `74a2e8b`。513个正式动作包含原先的24个首步。'
        '全部原异常单独保留，不将其当作额外24个独立实验，也不隐瞒冻结后日志修复。最终完整回放取代原零行回放；见《启动异常与授权续跑》。\n')
    append('费用和完整复现',startup);append('实验总报告',startup)
    cost_table=markdown(['方法','平均/中位/峰值输入token','输入缓存命中token','缓存命中比例','费用'],[
        [m,f"{c['mean_prompt_tokens']:.1f}/{c['median_prompt_tokens']:.1f}/{c['peak_prompt_tokens']}",c['cache_hit_tokens'],f"{100*c['cache_hit_fraction']:.1f}%",f"${c['cost_usd']:.9f}"] for m,c in costs.items()])
    cost_text=('## 调用更少，费用更高\n\n'+cost_table+'\nSCAR20请求数比SCAR19减少34.1%，输入token增加67.1%，协议费用增加73.7%。'
        '新版证据窗口从48条/6000字符扩大到64条/14000字符，并添加来源、时间、拒绝历史和生命周期；实际平均输入由3363增至8534 token。'
        '缓存命中比例也由29.9%降至4.8%。这是同时发生的协议与上下文变化，无法仅归因于子目标类型改进。'
        '191个响应均以stop结束，无输出上限截断或上下文超限错误；未给长输入特殊重试。当前结果支持节省请求数，不支持相对SCAR19节省token或费用。\n')
    append('费用和完整复现',cost_text);append('实验总报告',cost_text)
    trigger_table=markdown(['阻碍','逻辑请求','接受','完成','执行步','有必要配方增益的意图','多步完成'],[
        [k]+[v[f] for f in ('requests','accepted','completed','actual_intent_actions','intents_with_necessary_recipe_gain','multi_step_completed')] for k,v in trigger_effects.items()])
    append('按需LLM触发与规划机制','## 从具体触发到实际进展\n\n'+trigger_table+
        '\n150/191（78.5%）请求仍在目标配方未知时发出；对象已经明确，但并非已形成必要制作链上的精确子问题。'
        '34次材料路径与7次区域对象路径请求更具体。接受意图期间的配方增益与后续制作要分开：本轮意图执行期没有制作/收取增益，'
        '但oil_bomb等任务确实在意图发现配方后由确定性模块完成制作，不能把“执行期0制作”解释为LLM毫无作用。\n')
    target_supported=sum(r['target_supported_by_named_non_goal_reference'] for r in evidence_rejections)
    entry_public=sum(r['entry_named_elsewhere_in_prompt'] for r in evidence_rejections)
    fromloc=sum(r['entry_is_referenced_frontier_from_location'] for r in evidence_rejections)
    append('子目标解析接口修复',
        f"## 语义引用仍有接口边界\n\n86次语义拒绝中44次为 `evidence_unrelated_to_execution_entry`。其中{target_supported}次被引记录支持目标名称，{entry_public}次入口出现在提示其他记录中，{fromloc}次入口出现在被引前沿的 `from_location` 字段中；这些计数可重叠。"
        '当前代码要求引用记录的names直接含entry，而系统提示允许证据支持target或entry；因此引用成功与关系验证仍有更窄的实现边界，不能把44次全部称为模型没有公开依据。'
        '例如war_banner第6次动作选择，模型提议从courtyard进入barracks，引用了barracks前沿（其from_location为courtyard），但courtyard不在该记录names中而被拒。'
        '这是静态字段关系证据，没有执行同状态反事实，故不能宣称该拒绝已经验证造成局部损失。完整原文/ID在 `mechanism_diagnostics.json`。'
        '\n\n正式191次回复都首次有效，因而“三次坏回复后降级”仅在零API回归中被触发，本轮实跑没有提供该异常分支的新增任务级证据。\n')
    stop_rows=[r for r in stops if r['status']=='method_stalled']
    stop_table=markdown(['任务','动作/剩余','探索已用/18','逻辑规划已用/24','最终阻碍','必要材料配方首次齐全'],[
        [r['task_id'],f"{r['steps']}/{r['remaining_actions']}",r['exploration_spent'],r['logical_requests'],
         r['blocker'].get('kind','')+':'+r['blocker'].get('item',''),r['first_all_material_relations']] for r in stop_rows])
    append('多步子目标执行与停滞恢复','## 早停的实际边界\n\n'+stop_table+
        '\n11局显式停滞中10局用满18次探索，cog_crossbow仅用14次；各局都未达到24次全局规划上限。'
        '`method_stalled`表示本状态在既定单次选择/同上下文限制和当前控制器路径下未得到动作，不证明游戏无解，也不证明全部公共地点已访问。'
        '剩余70–80步不能记为节省了同等成功工作量。所有局保留失败分母。\n\n'
        '多步比例从Stage19的8/84升至51/105，但多步完成从2/8到8/51（25.0%→15.7%）；持续更久没有同步提高完成比例。'
        '2个ACQUIRE分别为oil_bomb的oil_flask（第7–8步检查scrap_iron、sinew_cord）与gate_cipher的cog（第17–19步移动/检查）；均取消后由新意图替代，期间无实际收取。'
        '59个LOCATE有8个完成，其中6个多步。完成只证明有公开供给或公开递归配方路径，数量与未知区域条件仍可能不完整。'
        '105个意图终态完整划分为51完成、41取消、9超限、4阻塞，另无截尾。工作台前提12/14得到满足，主要由已知路径确定性执行，不能记为CRAFT_PRECONDITION的成果。\n')
    ks_table=markdown(['方法','必要配方关系实例','精确数量实例','材料链配方全公开任务','其中成功','完成制作延迟样本/均值/中位'],[
        [m,k['necessary_relation_instances'],k['necessary_quantity_instances'],k['material_relations_complete_tasks'],k['successful_after_complete_relations'],
         f"{k['completed_recipe_latency_count']}/{k['completed_recipe_latency_mean']:.1f}/{k['completed_recipe_latency_median']:.1f}"] for m,k in knowledge_summary.items()])
    k_table=markdown(['任务','齐全时刻','未公开数量的配方','已知但未制作','公开→制作延迟'],[
        [task_by[k['task_id']]['target_item'],k['first_all_relations'],', '.join(k['unknown_quantities']) or '无',
         ', '.join(k['known_not_crafted']) or '无',json.dumps(k['relation_to_craft_latency'],ensure_ascii=False)] for k in knowledge])
    append('24任务性能对比','## 已知规则利用与知识条件\n\n'+ks_table+'\n'+k_table+
        '\n必要性标签只来自离线隐藏材料依赖闭包。材料配方名称齐全不等于材料来源、数量、工作台位置或全部区域条件齐全；现成材料也可绕过某些配方。'
        '因此cog_assembly、iron_nugget、hellcoal_concentrate、gate_cipher虽各自材料链配方关系已齐全仍失败，不能直接归为“全部执行知识已具备却不用”。'
        '它们分别仍阻塞于cog来源、crucible区域对象路径、hellcoal来源、cog来源。延迟统计仅包含最终制作发生的条目，未完成者截尾，不比较为已完成延迟0。'
        '每20步覆盖见 `knowledge.json`；早停后的快照沿用终态并标明observed_through，未伪造后续交互。模型证据窗口是裁剪子集；控制器P1登记与公开反馈关系由独立核验逐步比对，不能把被公开等同于曾进入模型请求。\n')
    focused=('## 重点任务的实际变化\n\n'
        '- **oil_bomb**：Stage19为100步失败，其中62次wait；本轮第6步由检查salvage_cloth公开目标关系，第15–16步查找charcoal_brick，第26–28步发现oil_flask/rubble_chunk，第39步制作oil_flask、第42步制作oil_bomb、第43步取得目标，成功。该条轨迹支持发现后由确定性模块完成生产；不能把不同模型轨迹差异直接归因于单个修复。\n'
        '- **repair_kit**：Stage19在13步后解析中止；本轮第15步已公开repair_kit，第21步公开oil_flask，第22–23步收取devil_oil，随后因rubble_chunk取得路径未知、探索18/18而停滞。当前可见rubble仍未检查；未执行该同状态反事实，不能断言一次检查必然完成任务。Stage18曾39步成功。\n'
        '- **metal_strip**：Stage19在7步后解析中止；本轮第16步公开metal_plate关系，未制作metal_plate，也未公开metal_strip关系，21步停滞。Stage18第25步取得metal_plate时才公开metal_strip，27步成功；这说明两条轨迹在通过实际制作取得新知识上存在差异，不意味着允许本轮控制器偷看旧轨迹的隐藏答案。\n'
        '- **metal_plate**：Stage19在7步后解析中止；本轮探索了ward/morgue，但未检查公开可见的scrap_metal，目标关系仍未知，21步停滞。Stage18第16步检查scrap_metal公开关系，23步成功。本轮不存在解析异常可以解释这个失败。\n'
        '- **pipe_club**：从Stage19的26步成功变为本轮18步死亡；本轮第10步进入ward、第11步检查desk，之后转去rooftop/morgue，未像旧轨迹第13步那样检查duct_tape发现目标关系。第18步环境死亡的反馈/health/death旗标保留。不得把不同路线下的攻击结果直接解释为某模块的严格因果效应。\n'
        '- **ruin_spear**：Stage19的79次wait消失，但本轮30步仍失败。第13步公开ruin_spear关系，第22–29步收取sinew_cord/salvage_cloth，第30步制作sinew_cord受到区域条件拒绝；终态必要knapped_edge路径未知。由“等待至96步死亡”改为显式停滞，不是任务级恢复。\n\n'
        '首次动作分歧、两条轨迹其后3步的真实反馈和状态哈希见 `mechanism_diagnostics.json.trajectory_divergences`；原始完整轨迹始终为证据。\n')
    append('解析异常与失败任务分析',focused)
    append('实验总报告','## 对本轮机制的明确判断\n\n'
        '工程可靠性确有改善：本次没有格式异常、坏ID、wait或策略运行器异常；首步日志事故已单独如实记载。但仍有44次入口证据绑定拒绝，'
        '提示的target/entry关系与校验器只认entry.names存在边界不一致，详见解析报告。材料路径定位、探索配额分配和从发现到生产的转换是剩余问题。\n\n'
        '按需LLM的请求数量优势在共同成功的11题上仍存在（88→55次），但动作204→208、费用0.0905→0.1172美元，不能称为全面效率提升。'
        '本轮总成功数与Stage19相同，oil_bomb新增成功被pipe_club退化抵消，且比Stage18少2题。现有证据支持接口修复和有限的多步发现能力；'
        '不支持已经解决材料获取/工作台制作子目标机制，也不支持在这些开发题上显著优于历史方法。正式实验结束后仅添加离线统计与核验代码，没有再修改算法或补跑。\n')
