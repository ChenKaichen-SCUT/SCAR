"""Chinese reports generated on the server from immutable experiment evidence."""
import collections as C
import json
import statistics as S
from pathlib import Path
from .common import ROOT, RESULTS, REPORTS, load, write, read_gzip, deny_network
from .posthoc import METHODS, NAMES, folder


def table(headers,rows):
    def cell(v):
        if v is None:return '—'
        return str(v).replace('|','\\|').replace('\n','<br>')
    return '|'+ '|'.join(headers)+'|\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('|'+ '|'.join(cell(v) for v in r)+'|\n' for r in rows)+'\n'


def evidence(task,method,step,label=None):
    stage='stage18' if method=='SCAR18' else 'stage17'
    name=label or f'{task}:a{step:03d}'
    return f'[{name}](../../results/{stage}/runs/{task}__{method}/trajectory.jsonl.gz)（JSONL 第 {step} 行）'


def f(x,digits=3):return '—' if x is None else f'{x:.{digits}f}'
def mean(x):return S.mean(x) if x else None


def main():
    deny_network();REPORTS.mkdir(exist_ok=True,parents=True)
    tasks=load(RESULTS/'tasks.json');analysis=load(RESULTS/'analysis.json');agg=analysis['methods'];old,new=agg['A0'],agg['SCAR18']
    stats=load(RESULTS/'per_task.json');lookup={(r['task_id'],r['method']):r for r in stats}
    knowledge=load(RESULTS/'knowledge.json');kl={(r['task_id'],r['method']):r for r in knowledge}
    events=read_gzip(RESULTS/'decision_events.jsonl.gz');acq=read_gzip(RESULTS/'acquisition_events.jsonl.gz')
    contexts=read_gzip(RESULTS/'model_context_evidence.jsonl.gz');cf=read_gzip(RESULTS/'same_state_effects_server.jsonl.gz')
    cf_receipt=load(RESULTS/'same_state_effects_receipt.json');preflight=load(RESULTS/'preflight_server.json')
    bytask={t['task_id']:read_gzip(folder(t,'SCAR18')/'trajectory.jsonl.gz') for t in tasks}
    baserows={t['task_id']:read_gzip(folder(t,'A0')/'trajectory.jsonl.gz') for t in tasks}
    index={r['evidence_id']:r for r in events}
    reasons=C.Counter(r['audit']['reason'] for r in events)
    risk_matches=sum(any(a.get('matched_consequences',{}).get('evidence') for a in e['audit'].get('acquisition_decisions',[])) for e in events)
    decision_keys=[('需求收取候选数量减少',new['acquisition_amount_reduced_steps']),('公开名义数量检查出现 REJECT',new['public_nominal_condition_rejected_steps']),
        ('新旧摘要选中记录发生变化',new['bounded_summary_record_changes']),('相对原控制器候选改变动作',new['changed_original_controller']),
        ('相对原候选改变且最终等于原 LLM 提案',new['restored_raw_llm']),('未执行探针回滚',new['unexecuted_probes_rolled_back']),
        ('后果记忆参与收取条件匹配',risk_matches),('原控制器候选被后果证据判 REJECT',new['old_candidate_risk_rejected'])]
    old_cf=cf_receipt['old_candidate_comparisons'];llm_cf=cf_receipt['raw_llm_comparisons']
    common=[t for t in tasks if lookup[t['task_id'],'A0']['success'] and lookup[t['task_id'],'SCAR18']['success']]
    bothfail=[t for t in tasks if not lookup[t['task_id'],'A0']['success'] and not lookup[t['task_id'],'SCAR18']['success']]
    common_old=sum(lookup[t['task_id'],'A0']['steps'] for t in common);common_new=sum(lookup[t['task_id'],'SCAR18']['steps'] for t in common)
    performance=table(['方法','R@60','R@80','R@100','Robot','Quarantine','成功均值/中位动作','全部动作','API 请求','输入/输出 token','协议 USD'],[
        [NAMES[m],f"{agg[m]['R60']}/24",f"{agg[m]['R80']}/24",f"{agg[m]['R100']}/24",
         f"{agg[m]['by_game']['robot_kingdom']['success']}/15",f"{agg[m]['by_game']['quarantine']['success']}/9",
         f"{f(agg[m]['success_steps_mean'],1)} / {f(agg[m]['success_steps_median'],1)}",agg[m]['steps'],agg[m]['api_calls'],
         f"{agg[m]['input_tokens']:,} / {agg[m]['output_tokens']:,}",f(agg[m]['cost_usd'],6)] for m in METHODS])
    paired=table(['对照','双方成功','仅 SCAR18 成功','仅对照成功','双方失败'],[
        [NAMES[m]]+[analysis['paired'][m]['cells'].get(k,0) for k in ('both_success','only_SCAR18','only_comparator','both_failure')] for m in ('A0','A1','A2','A3','A4')])
    task_table=table(['任务','游戏','目标','种子','依赖深度/制作节点']+[NAMES[m] for m in METHODS],[
        [t['task_id'].split('-')[1],t['game_name'],t['target_item'],t['initial_seed'],f"{t['dependency_depth']}/{t['recipe_nodes']}"]+
        [('成功' if lookup[t['task_id'],m]['success'] else '失败')+f" / {lookup[t['task_id'],m]['steps']}" for m in METHODS] for t in tasks])
    protocol='''本轮只有一个完整 SCAR18 版本、24 局正式实验。五种 Stage17 方法直接读取原始归档，没有重跑、补跑或排除失败。24 局均在服务器执行，初始种子、目标、教程前缀、原生环境和成功判定与 Stage17 一致。内外预算均为 100 个环境动作；无效动作、检查、等待都计步。

这些任务已用于发现问题，属于开发性验证。temperature=0.7，每任务只有一次新模型采样；事实摘要也改变了输入。轨迹分叉不等于单个模块的因果效果，不作显著优于基线或独立泛化结论。隐藏依赖闭包只用于离线必要性标签，不补全公开配方数量或工作台条件。

最新用户要求“本地不跑。只要在服务器跑”。冻结前已完成的本地零 API 验收保留；正式实验之后只做服务器原生回放、独立进程的同状态单步复核和统计。没有进行或声称完成正式后的本地回放。
'''
    write_report=lambda name,text:(REPORTS/name).write_text(text.rstrip()+'\n')

    code=f'''# SCAR18 代码改进说明

SCAR18 在冻结的 Stage16 `S1_P1_P3` 上实现需求收取、公开后果记忆、条件仲裁与目标执行上下文。正式代码冻结提交为 `2c2f7ec`，基线 Stage16 为 `1b650b41dea958d22e8415d8b23770f2454a8028`，Stage17 最终诊断为 `ab6faaa21dda4073dd52c920ca6a705e75a93e3a`。

{protocol}
## 实现与数据边界

|模块|实现|
|---|---|
|[acquisition.py](../../scar_stage18/acquisition.py)|已公开的直接名义需求减当前公开持有量；未知需求最多试取 1 个新增地面单位。`store` 先转移手中物品，因此请求数包括必要的手中转移；P3 的单个地面缺口仍可生成 `store 2`。不按 `craft N` 线性扩大需求。|
|[consequences.py](../../scar_stage18/consequences.py)|保存真实行动、库存/位置/装备、生命变化、原文、作用条件。明确携带伤害与敌人攻击相关性分开。单物品变化匹配公开受影响数量才能建立条件性物品关联；丢弃后伤害停止加强证据。数量、位置或装备变化允许有界尝试。|
|[execution_context.py](../../scar_stage18/execution_context.py)|复用 P1 与 `PublicRuleState`：只沿已公开目标依赖链，列出名义数量、当前可访问材料、工作台已知子集、既往失败、库存时效和 UNKNOWN。检查直接影响条件判断，摘要保持 STM5、48 条/6000 字符。|
|[controller.py](../../scar_stage18/controller.py)|在副本生成原 S1/P1/P3 与改进候选，检查数量与后果，仲裁后提交实际对应状态。丢弃未执行探针的计数、标记和尝试；观察真实反馈仅一次。FIFO、定向探索和 `craft N` 批量实现继承。|
|[arbitration.py](../../scar_stage18/arbitration.py)|保留 SUPPORTED/REJECT/UNKNOWN；已证伪前提优先排除，存在公开证据才支持风险移除或直接目标行动，否则保留结构化默认行为。替代动作只来自原 S1。|
|[agent.py](../../scar_stage18/agent.py)|一次正常动作请求；保存新旧摘要、模型原提案、候选、最终动作、条件、事务状态。没有额外语义排序模型调用。|

摘要顺序以源代码 `rank()` 为准：目标、目标配方、目标阻碍、近期去重风险、当前 FIFO 首节点阻碍、当前物品/容器、失败、已知相关配方、未知项、其余旧事实。每个记录尽量完整放入，超限记录跳过；全文始终受 6000 字符限制。原始反馈、全量结构化状态和实际请求另存，摘要省略不等于环境没公开。

## 事务语义

候选探针只在最终执行动词与目标匹配时提交一个探索额度。被放弃探针恢复 `exploration_spent/trials/probes`，清空 `pending_probe/explore_pending`；仲裁选中另一路径则恢复候选前 FIFO 与执行意图。FIFO 的公开规划更新和真实执行尝试分开记录；不匹配最终动作的 visit 计数恢复。失败记录与尝试日志只能由实际 `observe()` 更新。本次全部 {new['steps']} 个正式决策均通过这些保存日志不变量，回滚 {new['unexecuted_probes_rolled_back']} 个未执行探针。

## 冻结前验收及明确取舍

两地验收各完成 {preflight['unit_tests']} 项单元测试、635 步旧轨迹原生回放与 62 个单步分支。六个原来当步终止的状态均避免终止；56 个正面控制状态纳入检查。配方发现和制作正面维度均保留。四个状态少取得一种额外材料，但公开持有量已满足即时名义需求、持有物未损失、健康不差且腾出手位；验收将其列为有证据的收取取舍，原“额外材料”维度损失仍完整保存，未删去这些样本。

{table(['机制记录','正式触发步数/计数'],decision_keys)}
## 冻结后识别的实现局限（没有修改或重跑）

1. 需求与后果收取检查主要规范化 `store ... inventory`。原 LLM 使用已装备容器的显式名字时，同义动作没有统一进入该规则；正式记录有 4 次此类 store，其中一次取得 3 个 rubble，其余只是转移手中物品。不能因此声称该缺口已造成死亡，也不能称同义动作覆盖完整。这是普通接口工程问题。
2. 正式携带伤害反馈涉及混合物品。该记忆拒绝凭匿名“受影响物品总数”认定单个物品有害，因而没有得到可用于收取限制的物品关联：风险匹配和后果 REJECT 均为 0。不能把整体危险收取下降归因于后果记忆已成功学习规则。
3. 最外层仲裁的“恢复模型以避免控制器风险”“支持移除已知危险”“必要制作优于被动候选”专用分支均未触发；条件检查已经在继承的 S1 选择过程中改变候选。应区分完整管线的动作变化和新仲裁分支的实证支持。
4. 名义数量与历史公开库存不是原生可执行性证明。工作台完整性、批量消耗、动态损失、混合携带风险仍可能未知；进入一个合法地点也不保证生存。

这些局限和负面反事实纳入最终结论。冻结后的新增文件只做读取、回放和报告，不被正式策略导入，也未改变任何参数。
'''
    write_report('代码改进说明.md',code)

    material_keys=[('bulk_new_acquisition','单次新增持有量 >1'),('over_known_demand','超过当前公开即时名义缺口'),('dangerous_acquisition','取得物品同一步出现明确携带伤害'),('reacquired_after_risk_discard','风险相关丢弃后再取得'),('harmful_reacquired_after_risk_discard','上述再取得同一步再次携带伤害'),('actual_new_material_units','公开反馈确认的新增持有单位'),('explicit_carry_damage_events','明确携带伤害步'),('explicit_carry_damage_reported_hp','反馈报告的携带伤害 HP'),('native_failures','原生失败任务')]
    mt=table(['指标']+[NAMES[m] for m in METHODS],[[label]+[agg[m][key] for m in METHODS] for key,label in material_keys])
    dangerous=[r for r in acq if r['method']=='SCAR18' and r['dangerous_acquisition']]
    danger_table=table(['任务/步','动作','新增持有','携带伤害 HP','物品因果归属'],[[evidence(r['task_id'],'SCAR18',r['step']),r['action'],r['actual_acquired'],r['consequence']['explicit_carrying_damage'],r['consequence']['item_attribution']] for r in dangerous])
    material=f'''# 需求收取与负面后果分析

SCAR18 的大批新增收取从 {old['bulk_new_acquisition']} 次降至 {new['bulk_new_acquisition']} 次，伴随明确携带伤害的收取从 {old['dangerous_acquisition']} 次降至 {new['dangerous_acquisition']} 次，危险丢弃后的有害再收取从 {old['harmful_reacquired_after_risk_discard']} 次降至 {new['harmful_reacquired_after_risk_discard']} 次。但“超过已知即时名义缺口”由 {old['over_known_demand']} 增至 {new['over_known_demand']} 次，不能写成所有过量收取指标都改善。

{mt}
## 统计口径

收取量取自公开成功反馈；`store N` 中先搬运原来手中物品的部分不计新增持有。`take out` 从已携带容器到手中也不计新增。物品单位包括容器、原料、中间物和目标，不能理解成同等重量。“大量”是可重算阈值 **新增量 >1**，不是危险阈值。

即时名义需求仅使用当时 P1 已公开的目标依赖关系及数量，不读取隐藏配方，不按批量线性乘算。超过这个缺口只是诊断代理指标，不证明长远一定无用；未知需求不会被填成 0。重复危险收取要求先有当前轨迹公开携带风险与丢弃停止反馈关联，普通整理背包的丢弃不算。

明确携带伤害 HP 是原文中的独立伤害量之和，不等于总 HP 净减少；敌人攻击、回血、死亡复活和 HP 下限会使两者不同。原生失败依据原生 done/death/HP0 综合判断，不会将复活后的 HP100 误判成存活。

## 局部证据与归因边界

旧六个危险状态的同物理/RNG 单步回放中，需求约束动作均避免当步终止；这是工程修复的直接局部证据。正式新轨迹与旧候选的 {old_cf['n']} 个同状态比较中，新动作在 {old_cf['actual_advantage_dimensions'].get('higher_post_action_health',0)} 个分支有更高行动后 HP，在 {old_cf['alternate_advantage_dimensions'].get('higher_post_action_health',0)} 个分支更低。维度可重叠，不能直接相减为成功率净收益。

正式风险条件匹配 **{risk_matches} 次**，原控制器候选被后果证据判 REJECT **{new['old_candidate_risk_rejected']} 次**。以下七次携带伤害的物品归属均为 UNKNOWN：小量收取后，风险来自混合携带状态，反馈没有标注各物品的因果贡献。该版本没有对匿名风险类做可靠集合推理。因而本轮更支持“需求约束减少大批收取”，不支持“后果记忆已在正式任务上主动阻断风险”这一独立机制结论。

{danger_table}
## 剩余限制

控制器没有永久物品黑名单；数量/地点/装备改变的有界尝试在单元测试中覆盖。但有界取一件仍可能把混合携带总量推过风险门槛；先前风险没有形成单物品关联时，当前实现不能防止这种累积。显式容器名字与 `inventory` 未统一，普通拾取与全部同义转移的约束也不完全相同。以上均保留在正式结果，没有冻结后补丁。

原生失败从 13/24 降到 10/24；两者都失败的 10 个任务中，8 个 Robot 任务存活步数增加，`sharpened_blade` 从 78 步缩短至 48 步，`pipe_handle` 都为 20 步。更长存活可能允许更多推进，也会暴露于更多敌人活动，不等于有效任务进展。

完整证据：[acquisition_events.jsonl.gz](../../results/stage18/acquisition_events.jsonl.gz)、[同状态分支](../../results/stage18/same_state_effects_server.jsonl.gz)、[逐动作索引](../../results/stage18/evidence_index.jsonl.gz)。数据包括五个历史对照，统计可由 `scar_stage18.posthoc` 重算。
'''
    write_report('需求收取与负面后果分析.md',material)

    local_losses=[r for r in cf if 'avoids_immediate_terminal_failure' in r['alternate_advantage_dimensions']]
    losses=table(['原始证据','实际动作','反事实动作','候选来源','实际/反事实结果'],[
        [evidence(r['task_id'],'SCAR18',r['step']),r['actual_action'],r['alternate_action'],','.join(r['alternate_labels']),
         f"实际当步死亡；反事实 HP {r['alternate_gains']['health']}，未终止"] for r in local_losses])
    dimnames=sorted(set(old_cf['actual_advantage_dimensions'])|set(old_cf['alternate_advantage_dimensions'])|set(llm_cf['actual_advantage_dimensions'])|set(llm_cf['alternate_advantage_dimensions']))
    dims=table(['单步维度','新动作优于旧候选','旧候选优于新动作','实际优于原 LLM','原 LLM 优于实际'],[
        [k,old_cf['actual_advantage_dimensions'].get(k,0),old_cf['alternate_advantage_dimensions'].get(k,0),llm_cf['actual_advantage_dimensions'].get(k,0),llm_cf['alternate_advantage_dimensions'].get(k,0)] for k in dimnames])
    arbitration=f'''# 控制器仲裁分析

876 个正式环境动作中，{new['changed_original_controller']} 个与旧控制器同状态候选不同，{new['changed_llm']} 个仍覆盖原 LLM 提案，{new['restored_raw_llm']} 个相对旧候选变化后回到了原 LLM 提案。原 SCAR 为 635 步中 471 次覆盖；覆盖率由 {471/635:.1%} 变为 {new['changed_llm']/new['steps']:.1%}，但次数由 471 增至 {new['changed_llm']}，不能只选一个有利数字。

{table(['最终理由（原始日志值）','次数'],sorted(reasons.items()))}
上表只有“双方动作相同”“保留结构化默认”“保留控制器对被拒模型提案的纠正”三类。外层仲裁中的特殊恢复分支未触发；158 次候选差异包含需求约束、公开数量条件、先前状态变化与探针事务修复等联合影响。85 次回到原 LLM 行动不能都归为一个新仲裁分支的功劳。

## 同状态原生证据

服务器从 SCAR18 保存的每个行动前状态与 RNG 分别执行实际动作、不同的旧控制器候选和不同的原 LLM 提案，共重放 876 个实际动作、716 个不同替代动作。旧候选比较 158 个，原 LLM 比较 558 个。旧候选是在 SCAR18 已发生历史上的影子选择，不是重跑旧 SCAR 整局。

{dims}
这些维度可同时出现，额外材料种类也不等于必要材料数量充分。实际控制器相对原模型仍有 124 个额外公开配方关系分支、71 个额外材料种类分支、7 个额外制作种类分支，说明直接取消控制器会丢掉真实局部收益；原模型也有 24 个额外关系、66 个额外材料和 1 个额外制作种类分支，说明保留控制器仍有代价。

## 必须保留的负面反事实

{losses}
`cog_assembly` 第 52 步，模型 `wait` 能保留 HP4，实际 `enter ruins` 受到攻击并死亡：这是保留下来的控制器覆盖局部损失。`iron_nugget` 第 48 步，旧候选 `craft 2 crucible` 虽会因材料不足失败，却在同状态保留 HP3；实际 `enter cellar` 死亡。这证明“拒绝不可制作动作”与“替代路线更安全”并不等价。不是建议永远执行无效制作，更不证明替代分支最终能完成任务。

## 条件、风险和状态一致性

每步日志保留原始提案、原 S1/P1/P3、约束后候选、最终动作、三值条件、Execution Context、公开风险、实际反馈及副本提交情况。未执行探针共回滚 121 个；保存日志逐步检查探索增量等于实际探针提交量，尝试历史与失败记录在 choose 内不增加。API 请求只来源于原动作调用及原协议重试。

后果风险匹配为 0，因此不能说上述仲裁已通过风险记忆验证。名义数量条件出现 REJECT 的 117 步和控制器纠正模型的 108 步也不是彼此独立的模块收益。完整联合版本有正反两面的局部证据，缺乏消融，不拆分模块贡献。

完整记录：[decision_events.jsonl.gz](../../results/stage18/decision_events.jsonl.gz)、[same_state_effects_server.jsonl.gz](../../results/stage18/same_state_effects_server.jsonl.gz)、[同状态复核回执](../../results/stage18/same_state_effects_receipt.json)。
'''
    write_report('控制器仲裁分析.md',arbitration)

    availability=[]
    for method in METHODS:
        cc=[r for r in contexts if r['method']==method]
        known=[r for r in cc if next(t['target_item'] for t in tasks if t['task_id']==r['task_id']) in r['public_before']['relation']]
        shown=sum(next(t['target_item'] for t in tasks if t['task_id']==r['task_id']) in r['coverage']['relation'] for r in known)
        availability.append([NAMES[method],agg[method]['goal_relation_public'],agg[method]['goal_quantity_public'],agg[method]['all_closure_relations_public'],f(agg[method]['closure_relation_coverage_mean']),f(agg[method]['closure_quantity_coverage_mean']),f"{shown}/{len(known)}" if known else '不适用'])
    ktable=table(['方法','目标关系公开/24','目标数量公开/24','闭包关系齐全/24','关系覆盖均值','数量覆盖均值','公开目标关系在实际请求可核验'],availability)
    timing=table(['任务','成功/动作','目标关系首公开','数量首公开','全部闭包关系','名义材料与已知站点子集首满足','首次目标制作','关系→制作延迟','数量→制作延迟'],[
        [t['target_item'],('成功' if lookup[t['task_id'],'SCAR18']['success'] else '失败')+f"/{lookup[t['task_id'],'SCAR18']['steps']}",
         kl[t['task_id'],'SCAR18']['first']['relation'].get(t['target_item']),kl[t['task_id'],'SCAR18']['first']['quantity'].get(t['target_item']),
         kl[t['task_id'],'SCAR18']['first_all_relations'],kl[t['task_id'],'SCAR18']['first_public_nominal_materials_and_known_station_subset_met'].get(t['target_item']),
         kl[t['task_id'],'SCAR18']['first_successful_craft'].get(t['target_item']),kl[t['task_id'],'SCAR18']['latency_from_relation'].get(t['target_item']),
         kl[t['task_id'],'SCAR18']['latency_from_quantity'].get(t['target_item'])] for t in tasks])
    common_lags=[]
    for t in common:
        x,y=kl[t['task_id'],'A0'],kl[t['task_id'],'SCAR18'];g=t['target_item']
        if g in x['latency_from_relation'] and g in y['latency_from_relation']:common_lags.append((x['latency_from_relation'][g],y['latency_from_relation'][g]))
    knowledge_report=f'''# 知识到执行转化分析

SCAR18 的目标配方关系公开由 20/24 增至 24/24，精确名义数量由 19/24 增至 23/24；完成任务由 10/24 增至 14/24。失败的 10 个新任务全都已公开目标配方名称，因此剩余瓶颈不能概括为“没找到目标配方”。

{ktable}
## 三种知识状态的区分

环境公开：从逐条原生反馈重新运行 P1 解析，保留原文与首次公开时刻。结构化登记：读取实际控制器决策时的 P1 表；ReAct、LongContext、AdaPlanner 没有同构配方表，登记量不能记作零。进入模型：检查真实请求中的原始证据或有先前公开反馈支持的事实记录，UNKNOWN 包装不转为已知；仅字符串提到产品名不算知道配方。

模型当前展示增加不证明模型使用了知识。完整知识时间线、20/40/60/80/100 步快照、登记对照和请求证据见 [knowledge.json](../../results/stage18/knowledge.json) 与 [model_context_evidence.jsonl.gz](../../results/stage18/model_context_evidence.jsonl.gz)。早停轨迹在后续预算点保留终止时已知信息，明确标记 `terminated`，不冒充又执行了若干步。

## 24 个任务的知识与制作时刻

{timing}
“名义材料与已知站点子集满足”不是完整可执行性证明：工作台列表只是公开子集，批量消耗、动态库存等仍 UNKNOWN。没有任何任务被证明已掌握完整必要前提。表中 `—` 是未公开/未执行/证据不足，不是 100 步延迟；教程中已公开的知识记为 0。隐藏闭包只标记必要性，天然中间物供给可能绕过其中某个配方。

在各自成功并公开关系的目标上，关系到制作延迟均值为原 SCAR {f(mean(old['goal_relation_to_craft_latencies']),2)} 步、SCAR18 {f(mean(new['goal_relation_to_craft_latencies']),2)} 步；成功集合不同，不能直接解释成效率退化或提升。双方都成功的同 10 个任务，相应平均延迟为 {f(mean([x for x,y in common_lags]),2)}→{f(mean([y for x,y in common_lags]),2)} 步。更长存活带来的新成功往往包括较长探索链，本轮没有“知识一公开就全面更快执行”的证据。

## 直接证据

`war_banner` 的目标关系/数量在第 11/12 步已公开，但 18、25、27、35、45 步的 `craft 2 war_parchment` 仍返回材料不足。日志中的公开名义需求为 0.25 salvage_cloth，公开账面持有量逐次增大，却没有成功。它说明“名义数量检查通过”不能保证原生执行，不足以隔离是特殊制作语义、库存/物品身份还是其他规则问题；本轮不以隐藏配方来补答案。

`sharpened_blade` 第 43 步尝试 `craft 2 forged_blade`，公开名义材料满足，但环境首次反馈缺少 furnace。`iron_nugget` 第 14 步反馈缺少 crucible，之后也没有实际完成目标。两者都不能在配方名称公开时被归入“所有知识齐全”。上述失败原文及前提在逐任务成败报告与逐动作索引中可定位。

117 个决策步出现公开名义材料条件 REJECT，证明结构化知识实际进入候选条件管线；876 步保存了新旧摘要差异与真实请求。与此同时，材料不足拒绝 4→6、站点拒绝 24→28、重复检查 20→40。知识可见性与最终制作次数提高了，执行浪费并未全面降低；更长生存和模型采样差异可能共同影响这些数值。

这支持继续区分“关系已知—数量已知—公开材料就绪—工作台完整性未知—成功制作—取得目标”，而不是把全部阶段合成一个知识覆盖指标。
'''
    write_report('知识到执行转化分析.md',knowledge_report)

    efficiency=table(['指标','原 SCAR','SCAR18'],[[label,old[key],new[key]] for key,label in [
        ('craft_attempts','制作尝试'),('productive_crafts','真正产生物品的制作'),('craft_failed','制作失败'),('invalid','无效/被拒动作'),
        ('material_rejection','材料不足制作拒绝'),('station_rejection','工作台制作拒绝'),('repeated_inspections','重复检查目标名'),
        ('identical_feedback_repeat_inspections','同目标且反馈相同的重复检查'),('wait_actions','wait'),('api_failed_requests','异常请求（含恢复重试）')]])
    detailed=[]
    for t in tasks:
        for m in METHODS:
            r=lookup[t['task_id'],m]
            detailed.append([t['target_item'],NAMES[m],r['status'],r['steps'],r.get('craft_failed',0),r.get('invalid',0),r.get('repeated_inspections',0),r['api_calls'],
                f"{r['input_tokens']}/{r['output_tokens']}",f(r['cost_usd'],6)])
    perf=f'''# 24 任务性能对比

SCAR18 完成 14/24（58.3%），原 SCAR 为 10/24（41.7%）。新增成功：`oil_bomb`、`repair_kit`、`rubble_chunk`、`oil_flask`；没有原成功任务变失败。Robot 由 3/15 到 7/15，Quarantine 保持 7/9。历史 LongContext 为 13/24；本轮不能据此宣称普遍或显著超越。

{protocol}
## 总体指标

{performance}
所有 SCAR18 成功都在 60 步内，因此 R@60=R@80=R@100；没有通过降低预算挑选任务。每任务一次正式采样，10 次原生失败全部计入分母。完整实际费用含 9 个异常响应重试，共 885 次请求；不是只计算 876 个最终被执行动作的调用。

## 逐任务配对

单元格为“成功/失败 / 实际环境动作数”。依赖深度和制作节点数沿用冻结任务定义，仅作离线结构描述。

{task_table}
{paired}
## 效率、失败和费用

{efficiency}
有效制作比例：原 SCAR {old['productive_crafts']}/{old['craft_attempts']}={old['productive_crafts']/old['craft_attempts']:.1%}，SCAR18 {new['productive_crafts']}/{new['craft_attempts']}={new['productive_crafts']/new['craft_attempts']:.1%}；该比例不等于目标必需制作比例。双方都成功的 10 局总动作 {common_old}→{common_new}，平均 {common_old/len(common):.1f}→{common_new/len(common):.1f}。因此没有相同成功集合上的平均动作效率提升。

全部任务动作由 635 增至 876（+{new['steps']/old['steps']-1:.1%}），输入 token 由 1,925,510 增至 2,766,866，协议费用由 $0.606272 增至 $0.870619（+{new['cost_usd']/old['cost_usd']-1:.1%}）。每个完成任务摊分全部费用为 ${old['cost_usd']/old['success']:.6f}→${new['cost_usd']/new['success']:.6f}；该指标也受新旧任务集合影响。缓存命中率分别为 {old['cache_hit_tokens']/old['input_tokens']:.1%}、{new['cache_hit_tokens']/new['input_tokens']:.1%}；LongContext 历史高缓存命中使它的协议费用更低，不能只用总输入 token 推断花费。

每任务全指标：[per_task.csv](../../results/stage18/per_task.csv)。24 行宽表包括全部六方法成功、实际步数、制作失败、无效、重复检查、请求、token、费用和终止状态：[paired_24.csv](../../results/stage18/paired_24.csv)。以下保留逐方法明细，未把失败或 DAG 省略。

{table(['目标','方法','终止状态','动作','制作失败','无效','重复检查','请求','输入/输出 token','USD'],detailed)}
'''
    write_report('24任务性能对比.md',perf)

    divergence={r['task_id']:r for r in analysis['divergences']}
    changes=[];failure_cases=[]
    for t in tasks:
        tid=t['task_id'];a,b=lookup[tid,'A0'],lookup[tid,'SCAR18'];k=kl[tid,'SCAR18'];rr=bytask[tid];d=divergence[tid]
        category='双方成功' if a['success'] and b['success'] else '旧败新胜' if b['success'] else '旧胜新败' if a['success'] else '双方失败'
        entry=f"## {t['target_item']}：{category}\n\n"
        entry+=f"旧：{a['status']}，{a['steps']} 步，${a['cost_usd']:.6f}；新：{b['status']}，{b['steps']} 步，${b['cost_usd']:.6f}。实际动作差 {b['steps']-a['steps']:+d}。"
        entry+=f"目标关系首公开 {k['first']['relation'].get(t['target_item'],'未公开')}；数量首公开 {k['first']['quantity'].get(t['target_item'],'未公开')}；首次实际制作 {k['first_successful_craft'].get(t['target_item'],'未完成')}。\n\n"
        entry+=f"首次模型提案不同：第 {d['first_proposal_difference']} 步；首次实际动作不同：第 {d['first_action_difference']} 步。该分歧前物理状态相同：{d['same_physical_state_before']}。旧 `{d['old_action']}`（提案 `{d['old_proposal']}`）；新 `{d['new_action']}`（提案 `{d['new_proposal']}`）。这是描述性分叉，不能当作整局因果归因。\n\n"
        selected={r['step'] for r in rr[-3:]}
        selected.update(r['step'] for r in rr if r['metrics']['craft_failed'])
        selected.update(r['step'] for r in rr if r['success'])
        selected.update(r['step'] for r in cf if r['task_id']==tid and 'avoids_immediate_terminal_failure' in r['alternate_advantage_dimensions'])
        if category=='旧败新胜':selected.update(r['step'] for r in rr if r['metrics']['actual_production'])
        erows=[]
        for r in rr:
            if r['step'] not in selected:continue
            fb=r.get('mechanism_outcome',{}).get('feedback') or r['feedback']['text']
            meaningful=[line for line in fb.splitlines() if any(s in line for s in ('Cannot ','successfully crafted','I picked up','I stored','I took out','I entered','I was attacked','I have died','draining ','I waited','I discarded','I attacked'))]
            quote=' / '.join(meaningful)[:950] or fb[:550]
            erows.append([evidence(tid,'SCAR18',r['step']),r['action'],quote])
        entry+=table(['动作证据','实际动作','原始反馈节选'],erows)
        if not b['success']:
            stationsteps=[r['step'] for r in rr if r['metrics']['station_rejection']]
            materialsteps=[r['step'] for r in rr if r['metrics']['material_rejection']]
            risksteps=[r['step'] for r in rr if r.get('mechanism_outcome',{}).get('consequence',{}).get('explicit_carrying_damage')]
            caps=[r['step'] for r in rr if r['decision']['controller'].get('exploration_spent',0)>=18]
            classifications=['目标关系已公开但任务未完成（描述，不等同完整前提齐全）','最后一步原生攻击/死亡，全部保留']
            if stationsteps:classifications.append('存在已观察工作台障碍')
            if materialsteps:classifications.append('存在原生材料不足拒绝')
            if risksteps:classifications.append('存在明确携带伤害；单物品因果归属未确定')
            losses_here=[r for r in local_losses if r['task_id']==tid]
            if losses_here:classifications.append('有已验证同状态局部生存损失')
            entry+='审计结论：'+'；'.join(classifications)+'。\n\n'
            entry+=f"站点拒绝步：{stationsteps}；材料拒绝步：{materialsteps}；携带伤害步：{risksteps}；探索额度到达 18 的首步：{caps[0] if caps else '未达到'}；wait {b.get('wait_actions',0)} 次。仍未制作的已公开闭包配方：{', '.join(k['known_relation_not_crafted'])}。配方节点可能被天然物资绕过，因此不据此推定所有这些制作都必不可少。\n\n"
            failure_cases.append(dict(task_id=tid,labels=classifications,station_rejection_steps=stationsteps,material_rejection_steps=materialsteps,
                carrying_harm_steps=risksteps,exploration_cap_first_step=caps[0] if caps else None,
                selected_evidence_steps=sorted(selected),same_state_terminal_losses=[r['evidence_id'] for r in losses_here]))
        changes.append(entry)
    write(RESULTS/'failure_evidence_index.json',failure_cases)
    change_intro='''# 逐任务成败变化

新增成功四个，没有成功转失败；双方都成功十个、双方都失败十个。动作更长不能单独理解为进步：它可能是减少提前死亡，也可能是重复检查和等待。以下保留全部 24 个任务，包括不变失败、效率退化与明确负面单步证据。原始轨迹链接是压缩 JSONL，动作号即解压后的行号；教程步数不计在这些动作号内。

没有将不同随机模型轨迹的分叉解释为严格因果效应。失败标签可以重叠；仅将原生反馈直接显示的问题列为证据，不从最终失败倒推某个模块必然有错。

'''
    write_report('逐任务成败变化.md',change_intro+'\n'.join(changes))

    newerrors=[r for r in load(RESULTS/'response_errors.json') if r['method']=='SCAR18']
    error_table=table(['任务','动作请求步','attempt（从0计）','原因','后续恢复','费用 USD'],[[r['task_id'],r['step'],r['attempt'],r['reason'],r['recovered'],f(r['cost'],6)] for r in newerrors])
    total=f'''# SCAR18 实验总报告

本轮已完成唯一版本 SCAR18 的实现、冻结、24 局正式闭环、服务器原生回放与同状态离线复核。成功 **14/24**，原 SCAR **10/24**；新增成功 4 个、成功转失败 0 个。新增协议费用 **$0.870619**，低于 $3 总保护上限。五个历史对照均未重跑，Stage10–17 旧文件逐个哈希核对未变。

{protocol}
{performance}
## RQ1：是否减少过量危险收取、重复危险操作和提前死亡？

整体观察支持需求收取修复有价值：大批新增取得 38→4 次，伴随携带伤害的收取 31→7 次，有害丢弃后重取 8→0 次，携带伤害原文报告 1172→52 HP，原生失败 13→10 局。六个已保存旧危险状态的单步原生分支均避免当步终止，是直接局部证据。

限制也明确：超过即时已知名义需求的事件 15→18；不应声称所有“过量”指标都下降。正式风险记忆匹配与后果 REJECT 为 0，混合携带状态的匿名反馈没有形成物品归属。因此不能把总体改善拆成后果记忆的独立效果。

## RQ2：是否保留 S1 的价值并减少有害覆盖？

控制器仍有正面价值：新轨迹同状态比较中，相对原 LLM 有 124 个额外公开关系、71 个额外材料种类和 7 个额外制作种类分支。覆盖率从 74.2% 到 63.7%，但总覆盖次数 471→558；158 次与旧影子候选不同，85 次回到原始提案。

不能把这全部归功于最外层仲裁：其特殊恢复分支未触发，条件检查已在继承管线内部改变候选。仍有两处明确负面局部证据：`cog_assembly` 第52步原 LLM `wait` 避免当步死亡；`iron_nugget` 第48步旧候选失败制作也避免当步死亡，而实际改为移动后死亡。合法路线和材料条件改善不保证生存。

## RQ3：已公开规则是否更有效转化为执行？

目标关系公开 20→24 局、数量公开 19→23 局，实际完成 10→14 局；117 步的名义数量 REJECT 与逐步真实请求证明知识进入了决策，并非只留在日志里。但剩余 10 个失败任务全部已经知道目标关系，工作台完整性仍 UNKNOWN。制作失败 28→34、重复检查 20→40、wait 7→23。双方同成功任务的平均动作 22.2→22.9，没有全面更快的证据；知识到制作的条件成功延迟见专门报告。

因此可说完整版本得到更多实际完成，不能说“知道规则后已经可靠执行”。较长存活和不同模型提案同样可能贡献发现与完成。

## RQ4：性能、效率、风险与成本的正负变化？

Robot 3/15→7/15；Quarantine 7/9→7/9，七个原成功任务全部保持，但部分慢了 1–3 步。新增成功是 `oil_bomb`、`repair_kit`、`rubble_chunk`、`oil_flask`。`sharpened_blade` 都失败且从 78 步降至 48 步；`pipe_handle` 都在20步失败。其余八个双方失败 Robot 任务存活更久，仍没有完成，不能用“活得更久”替代成功率。

总动作 +241，输入 token +841,356，协议费用 $0.606272→$0.870619；成功任务动作均值 22.2→27.0（成功集合变化），同十个成功任务总动作 222→229。有效制作比例 41.7%→47.7%，但失败制作和检查绝对数上升。没有整体动作成本或 token 成本下降。与 LongContext 的14比13仅是这组开发任务上的描述性结果。

## RQ5：工程问题与后续独立机制问题？

普通工程问题：同义容器动作尚未统一经过收取保护；公开账本的“exact”只是可见计数齐备，不能排除环境动态；需要明确区分手中转移和新取得、候选构造和真正执行、日志分支存在和实际触发。探针事务修复在本轮有可审计的一致性证据，但没有消融就不能量化它对成功数的贡献。

可能具有独立研究价值的机制问题：混合库存下匿名负面后果的集合归因与条件迁移；部分已知配方下针对真正缺失前提的试验选择；在环境危险随时间变化时联合评估信息/材料进展与生存成本；名义数量、批量语义、工作台未知与可访问状态之间的可执行性证据闭合。这些只是由失败案例支持的研究判断，不是已证明有效的新算法，也不是现在启动下一阶段的授权。

`war_banner` 多次 0.25 名义数量看似满足但原生材料拒绝、`forged_blade` 第43步才公开 furnace、两个当步死亡反事实，为这些区分提供具体例子。不能仅凭一次采样宣布论文机制成立。

## 异常请求、核验与费用

9 个模型异常响应均为缺少动作/推理必需字段，全部在冻结的3次尝试协议内恢复；其中一个逻辑请求连续两次异常。全部原始响应、费用、后续成功请求都保存，没有终止局重跑。费用以冻结费率与实际 usage 计算，含重试；是协议记账，不是服务商账单对账。

{error_table}
服务器原生重放核对24条轨迹、876个动作的前后观察、物理状态哈希和成功证明；独立离线进程另做876个实际动作加716个替代单步分支。所有离线检查禁用网络。用户要求只在服务器跑后，没有再做本地测试/回放。此限制明确记录在 [verification_scope.json](../../results/stage18/verification_scope.json)。

报告与机器记录：逐任务宽表、144方法-任务长表、公开知识时间线、逐请求上下文证据、逐步仲裁事件、材料/后果事件、失败证据索引、同状态分支、费用账本、冻结哈希、服务器核验回执。冻结策略没有因任何正式结果修改，完成后停止；不启动 Stage19，不做消融，不重跑失败。
'''
    write_report('实验总报告.md',total)

    reproduce='''# SCAR18 复现指南

## 版本与输入

完整冻结清单见 `results/stage18/freeze.json`，首次冻结代码提交 `2c2f7ec`。继承 Stage16 `1b650b41dea958d22e8415d8b23770f2454a8028`，历史诊断提交 `ab6faaa21dda4073dd52c920ca6a705e75a93e3a`；AgentOdyssey 必须使用 `248430692a9d4a61d38c6c03ab2126287faaf450`。第三方引擎按原项目方法单独安装，不在本仓库重复上传。

任务与前缀从 Stage17 原文件逐字复制并校验哈希：15 个 robot_kingdom、9 个 quarantine；后者教程28步不计入100步。温度0.7、DeepSeek Flash、thinking disabled、输出768、STM5、48事实/6000字符；不修改基础动作提示。依赖深度与隐藏必要闭包仅供评价。

## 本次执行位置

正式实验、正式后的统计和核验均只在服务器 `/root/scar_workspace/project`。运行时目录 `/root/scar_workspace/runtime_stage18` 保留原始请求缓存、准确断点与工作日志。本地仅编辑、同步、提交；已经完成的冻结前本地验收属于历史记录，不代表正式后本地复核。

所有以下命令在服务器运行，环境变量按实际第三方依赖安装路径设置：

```bash
cd /root/scar_workspace/project
export AGENTODYSSEY_ROOT=/root/scar_workspace/dependencies/agentodyssey
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH=.
```

## 无模型调用的重算与核验

```bash
/root/scar_workspace/venv/bin/python -m scar_stage18.posthoc
/root/scar_workspace/venv/bin/python -m scar_stage18.replay --site server --runtime /root/scar_workspace/runtime_stage18/replay_check
/root/scar_workspace/venv/bin/python -m scar_stage18.local_effects
/root/scar_workspace/venv/bin/python -m scar_stage18.report
/root/scar_workspace/venv/bin/python -m scar_stage18.verify
```

`local_effects` 的 local 指“单步局部因果效果”，不是本机执行；它在服务器运行。离线模块强制禁用网络，不会新建模型提案。原生回放只执行归档动作，不重新运行对比策略。报告生成读取原始统计及已有分支；verify 检查历史文件、冻结文件、24局数量、请求/账本一致性和所有报告。

## 正式运行协议的历史记录

当时运行的是 `python -m scar_stage18.batch --runtime /root/scar_workspace/runtime_stage18 --workers 6`。本轮已结束，不要用新目录重新运行或删除已完成 summary；这些动作会产生额外采样，违反本轮协议。程序遇到已归档任务直接返回。只允许尚未结束的同一局从精确断点恢复，且复用保存的 logical request cache；不确定是否付费的中断请求中止而不重新抽样。API密钥保留在服务器私有文件中，不进入仓库或报告。

全局新增费用保护 $3、单局 $0.25；每次调用预留费用，成功/异常按真实用量结算，未知用量保守保留。正式前已保存成本估算。此次885次请求中9次格式异常均恢复，实际876动作、24个完整终止记录，协议总费用 $0.870619332。

## 记录说明

|文件|内容|
|---|---|
|`runs/*/summary.json`|全部成功/失败与终止原因、实际动作数、初末哈希|
|`runs/*/trajectory.jsonl.gz`|每行一个环境动作；原始观察、实际动作、完整反馈、决策状态、公开知识、机制和评价|
|`runs/*/requests.jsonl.gz`|每个真实请求尝试，含完整提示/返回、解析结果、usage、费用、logical id、重试|
|`per_task.csv` / `paired_24.csv`|144行方法-任务长表 / 24行六方法配对宽表|
|`knowledge.json` / `model_context_evidence.jsonl.gz`|公开/登记/进入请求知识、时刻、延迟、终止标志和出处|
|`decision_events.jsonl.gz` / `acquisition_events.jsonl.gz`|每步候选、最终动作、条件、收取数量、后果匹配、事务提交|
|`evidence_index.jsonl.gz` / `failure_evidence_index.json`|原始动作/请求路径、JSONL行号、状态哈希及失败证据|
|`same_state_effects_server.jsonl.gz`|完整单步正负反事实，禁止解读成整局改进或消融|
|`cost_ledger.json`|全局费用账本，与全部请求尝试逐项对应|
|`preflight_*`|冻结前零API工程验收，含四处明确材料取舍|
|`replay_server.json` / `same_state_effects_receipt.json` / `verification.json`|服务器核验回执|
|`prior_manifest.json` / `artifact_manifest.json`|原历史文件与本次交付文件SHA256|

费用、成功判定、动作数从真实轨迹重算；不依赖模型“我已完成”的叙述。最终目标必须本局制作且实际持有，地面产物不算成功。原生死亡即停止，即使引擎在反馈里复活为100HP也仍算失败。

统计与报告代码是冻结后增加的只读分析文件，不被正式策略导入；策略和运行器哈希保持冻结值。失败原样保留，不以分析发现反向修补本轮结果。
'''
    write_report('复现指南.md',reproduce)
    write(RESULTS/'mechanism_summary.json',dict(decision_counters=dict(decision_keys),arbitration_reasons=dict(reasons),
        conditional_consequence_matching_steps=risk_matches,terminal_local_losses=[dict(task_id=r['task_id'],step=r['step'],action=r['actual_action'],alternative=r['alternate_action'],labels=r['alternate_labels']) for r in local_losses],
        common_success_tasks=len(common),common_success_old_actions=common_old,common_success_new_actions=common_new,
        new_formal_request_errors=newerrors,summary_scope='Joint engineering version; no module-isolated causal gain claims'))
    print('Generated 8 Chinese reports on server; all 24 tasks retained.')


if __name__=='__main__':main()
