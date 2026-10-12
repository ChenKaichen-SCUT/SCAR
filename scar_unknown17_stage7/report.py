"""Chinese reports generated from the full paired cohort and local audit."""
import argparse
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
from scar.io import atomic_json
from scar_unknown17.analyze import public_recipe_names

METHODS=['C0','C1','C2','C3','C4','C5']
LABELS={'C0':'原版 Combined','C1':'仅 A：上下文重试','C2':'仅 B：知识缺口','C3':'仅 C：模式切换','C4':'仅 D：资源与收取','C5':'A+B+C+D'}

def pct(x):return 'NA' if x is None else f'{100*x:.1f}%'
def num(x,n=2):return 'NA' if x is None else f'{x:.{n}f}'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x) for x in r)+' |' for r in rows])


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.parse_args()
    out=Path('results/stage7');reports=Path('reports/stage7');reports.mkdir(parents=True,exist_ok=True)
    load=lambda name:json.loads((out/(name+'.json')).read_text())
    groups=load('method_metrics');g=groups['all'];families=load('family_comparison');paired=load('paired_comparisons');verification=load('verification');offline=load('offline_checks');audit=load('decision_audit_summary')
    config=json.loads(Path('configs/protocol_stage7.json').read_text());eps=load('episode_metrics');cases={c['id']:c for c in load('cases')};by={(e['case_id'],e['algorithm']):e for e in eps}
    cf_counts={flag:Counter() for flag in config['switches']['C0']};cf_examples=defaultdict(list)
    for r in map(json.loads,gzip.open(out/'decision_counterfactuals.jsonl.gz','rt')):
        c=cf_counts[r['flag']];c['comparisons']+=1
        if not r['changed']:continue
        c['changed']+=1
        if r.get('alternate_policy_error'):
            c['disabled_policy_error' if r['original_flags'][r['flag']] else 'enabled_policy_error']+=1
            continue
        active,inactive=(r['original_effect'],r['alternate_effect']) if r['original_flags'][r['flag']] else (r['alternate_effect'],r['original_effect'])
        c['enabled_goal_better']+=int(active['physical_after']['goal'] and not inactive['physical_after']['goal'])
        c['enabled_goal_worse']+=int(inactive['physical_after']['goal'] and not active['physical_after']['goal'])
        c['enabled_legal_better']+=int(inactive['rejected'] and not active['rejected'])
        c['enabled_legal_worse']+=int(active['rejected'] and not inactive['rejected'])
        key={cases[r['case_id']]['object_names'][x] for x in cases[r['case_id']]['recipe_graph']}
        ak=public_recipe_names(active['public_feedback']['text'])&key;ik=public_recipe_names(inactive['public_feedback']['text'])&key
        c['enabled_exposes_more_key_names']+=int(bool(ak-ik));c['enabled_exposes_fewer_key_names']+=int(bool(ik-ak))
        if len(cf_examples[r['flag']])<8 and (active['physical_after']['goal']!=inactive['physical_after']['goal'] or active['rejected']!=inactive['rejected'] or ak!=ik):
            cf_examples[r['flag']].append({'case_id':r['case_id'],'task_id':r['task_id'],'index':r['index'],
                'active':active['action'],'inactive':inactive['action'],'active_goal':active['physical_after']['goal'],
                'inactive_goal':inactive['physical_after']['goal'],'active_rejected':active['rejected'],'inactive_rejected':inactive['rejected'],
                'active_key_names':sorted(ak),'inactive_key_names':sorted(ik)})
    local={'counts':{k:dict(v) for k,v in cf_counts.items()},'examples':dict(cf_examples),
        'scope':'enabled versus disabled at identical recorded controller history and same base proposal; toggles across all six histories are dependent, not independent samples'}
    atomic_json(out/'local_effect_summary.json',local)
    pairs={r['a']:r for r in paired if r['b']=='C0'}
    # Judgments separate implementation correctness, local effects and aggregate outcomes.
    judgments={}
    for m,flag in zip(METHODS[1:5],config['switches']['C0']):
        r=pairs[m];gain=len(r['a_only']);loss=len(r['b_only']);net=gain-loss
        judgments[flag]={'config':m,'successes':g[m]['successes'],'C0_successes':g['C0']['successes'],
            'paired_gains':gain,'paired_losses':loss,'net':net,'family_ci95':r['family']['ci95'],
            'implementation_gate':'passed','local_effects':dict(cf_counts[flag]),
            'judgment':'本批有净改善，但需结合负例与局部审计，不构成未见任务泛化证明。' if net>0 else
                '本批没有任务成功数净收益；局部修复是否触发须与闭环结论分开。' if net==0 else
                '本批净负效应；保留全部退化案例，不能因单元正确而宣称任务恢复更好。'}
    judgments['combination']={'successes':g['C5']['successes'],'C0_successes':g['C0']['successes'],
        'paired_gains':pairs['C5']['a_only'],'paired_losses':pairs['C5']['b_only'],
        'strictly_above_best_single':g['C5']['successes']>max(g[m]['successes'] for m in METHODS[1:5]),
        'scope':'六配置不完整识别交互；不同远端采样路径不能作为严格确定性因果证据。'}
    atomic_json(out/'research_judgment.json',judgments)
    total=verification['new_ledger_usd'];tokens=sum(r['input_tokens']+r['output_tokens'] for r in eps);calls=sum(r['api_calls'] for r in eps)
    lines=['# Stage 7 未知规则探索与执行可靠性实验报告','',
        f"本轮完成 17 个既有 family × 6 个 FIFO-Combined 内部配置，共 102 组真实闭环实验。C0 成功 {g['C0']['successes']}/17，C5 成功 {g['C5']['successes']}/17。新增 API 记账费用 ${total:.9f}，项目累计 ${verification['project_total_usd']:.9f}。结果属于多轮使用过的任务上的探索性开发验证。",'',
        '## 协议与冻结','',
        '冻结起点为 `44297e64351262a78a56953ee3f1dee0101d3bd7`。新策略独立置于 `scar_unknown17_stage7/`；历史源文件和数据逐文件 SHA-256 校验不变。使用原有 17 个初始物理快照、公开历史、目标及原种子，每局最多 40 个环境动作；没有新增独立基线、额外种子或长程实验。', '',
        '全部配置使用 DeepSeek Flash、非思考模式、temperature=0.7、max_tokens=768、STM 最近 5 条记忆及原版有界事实摘要。C0 在本批重跑，得到 4/17，旧 Stage 6 的 5/17 不作本轮对照成绩；这也说明非零温度的跨批采样差异不能忽略。四模块仅通过开关改变控制器，未增加模型调用或改写共同 Prompt。D 的数量管理读取公开“获得物品”反馈中的数字，仅用于已有相同配方名称的需求与保留量，不把这些数字注入共同 FIFO 资源表或事实摘要。', '',
        table(['配置','A','B','C','D'],[[m]+[int(x) for x in config['switches'][m].values()] for m in METHODS]),'',
        '增量预算硬上限为 $5，单局保护上限 $0.25。历史名义参考约 $3.24；失败不减步数、不删 family、不补跑成绩较好配置。价格使用已有固定对比记账口径，非供应商当前账单。方法格式中止计入失败；基础设施与预算中止视为未完成，不混入失败率。', '',
        '本批 101 局正常结束，另 1 局 spire_pike / C5 在 26 个动作后因 `_station → _explore → _gap_explore` 递归中止。冻结运行器把一般异常写为 failed；独立事后审计从原检查点和已付费基础提案两次重现 RecursionError，将其归类为方法中止并计入失败分母。原始状态和栈保持不变，未修复策略后补跑；该未执行动作的 API 请求费用仍计入。此缺陷是本轮组合机制的负面结果。','',
        '## 实现和零 API 证据','',
        'A 记录试制/检查的公开材料、工作台、反馈、阻塞类型与下一次重试条件。缺前置条件的试制保留真实动作成本，不耗用有效前向试制配额；只有相关条件变化才解除限制。B 维护目标的公开依赖缺口，按关联物料、新产物、潜在连接、前向试制及广域回退排序，区分信息检查和准备运输，保留延迟价值未知。', '',
        'C 保留原 FIFO 队列，追加公开缺失依赖，优先执行材料和已观察工作台支持的子目标，并记录 EXPLORE/EXECUTE/RECOVER。工作台或材料阻塞不会仅因无关移动解除。D 依据公开需求和后续保留量减少不必要中间批量，保留已拥有的最终目标副本，并优先拾取、取出或转存最后副本；转存数量考虑先移动手中旧副本的语义。', '',
        f"付费前本地和服务器均通过 36 项测试。旧 Combined 的 {offline['parity_actions']} 个动作及旧控制器字段逐步一致；C0 模型请求集成、记忆及摘要一致；{offline['checkpoint_roundtrips']} 个配置状态完成序列化往返。另有 {offline['local_single_steps']} 个旧历史下首次改变动作的真实引擎局部比较，六配置均通过零 API 集成。", '',
        '冻结后另做零 API 复核：17 条旧完整轨迹的 609 次模型输入、动作、记忆及摘要完全一致，并完成 17 个完整代理记忆检查点的保存/恢复；没有修改冻结策略。','',
        '真实数量回归：同一状态下，D 为 bandage_roll 所需的 sinew_cord 选择 2 份，为 orrery_blade 所需的 astrolabe_core 选择 1 份。历史固定续动作反事实分别呈现 craft1/craft2 的目标结果 [失败,成功] 和 [成功,失败]；另一个已制作未收取状态可由公开收取动作完成。这些都是局部引擎证据，不能作为本轮模型成功率。', '',
        '## 真实闭环恢复与成本','',
        table(['配置','R@10','R@20','R@40','成功平均步数','总动作','费用 USD','总 token','每成功成本 USD'],[
            [m,pct(g[m]['recovery_at_10']),pct(g[m]['recovery_at_20']),f"{g[m]['successes']}/17",num(g[m]['mean_success_steps']),g[m]['steps'],num(g[m]['cost_usd'],6),g[m]['input_tokens']+g[m]['output_tokens'],num(g[m]['cost_per_success_all_attempts'],6)] for m in METHODS]),'',
        f"共 {calls} 次 API 请求、{tokens} tokens、{sum(r['steps'] for r in eps)} 个实际环境动作。所有失败、方法中止和费用均保留，完整状态为 `{load('completion')['statuses']}`。", '',
        table(['游戏','family 数']+METHODS,[[game,groups[game]['C0']['n']]+[f"{groups[game][m]['successes']}/{groups[game][m]['n']}" for m in METHODS] for game in ['saltglass','quarantine','robot_kingdom']]),'',
        '## 成对比较与不确定性','',
        table(['对比 C0','新增成功','丢失成功','净百分点','家族 bootstrap 95% 区间'],[[m,len(pairs[m]['a_only']),len(pairs[m]['b_only']),num(pairs[m]['family']['difference']*100,1),'['+', '.join(num(x*100,1) for x in pairs[m]['family']['ci95'])+']'] for m in METHODS[1:]]), '',
        '统计单元是 family，采用 10,000 次成对 bootstrap；另保存按三个源游戏聚类的敏感性分析，三个簇无法支持稳定总体推断。远端模型采样未被严格配对；同初始快照不意味着除模块外所有后续输出一致。六个配置不能识别完整四阶交互。', '',
        '## 知识发现与探索成本','',
        table(['配置','关键配方','中间配方','定向探索动作','新增公开配方数','同状态确认无增益','耗尽试制后错失机会'],[
            [m,f"{g[m]['key_recipe_discovered']}/{g[m]['key_recipe_total']}",f"{g[m]['intermediate_recipe_discovered']}/{g[m]['intermediate_recipe_total']}",g[m]['directed_information_actions'],g[m]['public_new_recipes'],g[m]['same_state_confirmed_no_gain'],g[m]['expired_trial_missed_opportunities']] for m in METHODS]),'',
        '配方“已知”要求公开非空材料名列表，单独知道工作台不算。每条关键规则的首次发现索引在 `episode_metrics.json`。定向动作当步无新增必要配方不直接视为浪费；搬运、移动、生产可检查中间物均可能有延迟价值。“耗尽试制后错失机会”要求旧失败记录、当前真实引擎可制作且试制资格仍耗尽，但不等于该候选一定必要或必然恢复任务。', '',
        table(['配置','B 信息检查','B 准备/运输','B 前向生产','B 获得必要配方','A 条件解除后成功'],[[m,g[m]['gap_action_types'].get('information_inspection',0),g[m]['gap_action_types'].get('preparation_transport',0),g[m]['gap_action_types'].get('forward_production_with_delayed_information_value',0),g[m]['gap_discovered_key_recipe_count'],g[m]['condition_released_successes']] for m in METHODS]),'',
        table(['配置','信息/准备动作成本 USD','相关动作 token','定向动作/新必要配方','信息动作费用/新必要配方 USD'],[[m,num(g[m]['information_action_cost_usd'],6),g[m]['information_action_tokens'],num(g[m]['directed_actions_per_directed_key_gain']),num(g[m]['information_cost_per_discovered_key'],6)] for m in METHODS]),'',
        '以上费用覆盖检查以及被定向机制标注的准备、移动和试制；其余模型/动作费用已计入总成本。每条规则可能由基础提案获得，因此信息费用/全部新必要配方是描述性分摊，不是严格的边际发现成本。','',
        '## 从知识到执行','',
        table(['配置','已知且实际可制作机会','及时执行比例','中间规则延迟*','中间规则未转化/总数','最后规则→目标延迟*','规则齐全仍失败'],[[m,g[m]['known_ready_opportunities'],pct(g[m]['ready_execution_rate']),num(g[m]['intermediate_conversion_lag_with_censor_mean']),f"{g[m]['intermediate_conversion_censored']}/{g[m]['intermediate_conversion_n']}",num(g[m]['last_rule_goal_lag_with_censor_mean']),g[m]['all_known_but_failed']] for m in METHODS]),'',
        '带 * 的描述量包括未执行/未完成轨迹从发现时到第 40 步的剩余时长；递归中止例实际只观察到 26 步，额外标记早停，余至 40 步是协议失败惩罚而非已观察随访，保留截尾标记，不能解释为无截尾的真实平均完成时间。不同配置的发现时间和已发现集合不同，单看该均值不可证明加速。尚未发现的规则单列缺失；制作先于公开规则发现时单列，不记为负延迟。按必要配方名称计数也可能包含已有可取得副本的节点，不表示每个节点都必须再次制作。', '',
        table(['配置','EXPLORE','EXECUTE','RECOVER','未管理','无测得进展往返切换','失败局子目标推进'],[[m]+[g[m]['mode_actions'].get(k,0) for k in ['EXPLORE','EXECUTE','RECOVER','UNMANAGED']]+[g[m]['unproductive_mode_toggles'],g[m]['failed_subgoal_progress_sum']] for m in METHODS]),'',
        '模式切换以公开证据记录。无测得进展的往返切换是诊断指标，不自动等于无理由切换；未开启 C 的配置记为 UNMANAGED，不能把未激活解释为模块无效。', '',
        '## 材料与最终收取','',
        table(['配置','数量非支配率','可避免的保留材料损耗','资源取放循环','制作后仍未收取','可收取却做无关动作','合法→拒绝','基础当步完成被覆盖'],[[m,pct(g[m]['quantity_nondominated_rate']),g[m]['avoidable_reserve_depletion'],g[m]['resource_cycles'],g[m]['produced_goal_but_uncollected_at_end'],g[m]['final_available_unrelated_actions'],g[m]['legal_to_rejected'],g[m]['harmful_goal_overrides']] for m in METHODS]),'',
        '数量非支配率比较相同物理状态的 craft1/2/3/4 原始动作规则：产出更多且消耗不更多。该局部标准不考虑多余产物的未来价值，不能替代后续资源保留审计。保留材料损耗按受影响动作计数，另存证据条数及分类。计入：真实消耗超过更小且有产出的候选并侵入公开后续保留量，或消耗仍需保留的既有最终目标副本，或已有足量公开地面产物且引擎确认可取得却再次制作并侵入后续材料保留量；这仍不是永久不可恢复的证明。所有目标、合法性和资源真值均由策略执行后的独立引擎审计计算。', '',
        '## 决策级单开关反事实','',
        f"对 {audit['decisions']} 个已提交动作进行四次单开关比较，共 {audit['one_flag_comparisons']} 对；原动作重现错误 {len(audit['reproduction_errors'])}。同一 controller checkpoint、公开观察和已记录基础提案，仅切换一个开关；动作有变化时执行相同物理状态的完整单步（包含环境步规则）。",'',
        table(['模块','动作改变','开启后目标更好/更差','开启后合法性更好/更差','披露更多/更少必要配方名'],[[flag,c['changed'],f"{c['enabled_goal_better']}/{c['enabled_goal_worse']}",f"{c['enabled_legal_better']}/{c['enabled_legal_worse']}",f"{c['enabled_exposes_more_key_names']}/{c['enabled_exposes_fewer_key_names']}"] for flag,c in cf_counts.items()]),'',
        f"另有 {len(audit.get('counterfactual_policy_errors',[]))} 次局部开关反事实触发控制器异常，单独保存，不伪造一个环境动作或物理结果。",'',
        '所有六种历史下的局部比较相互相关，不能当作独立样本。已有模块历史状态保持不变；C0 历史没有 A 的长期记录时，临时打开 A 可能不触发。该审计衡量当前决策变化，不冒充整局重新训练/执行的反事实恢复率。配方名披露是该步反馈差异，可能重复历史已知信息，完整首次发现仍以主轨迹为准。', '',
        '## 之前 11 个共同失败任务','',
        table(['分组','family 数']+METHODS,[[label,groups[scope]['C0']['n']]+[groups[scope][m]['successes'] for m in METHODS] for scope,label in [('old_common11','旧共同失败 11'),('old_missing7','旧知识缺失 7'),('old_known4','旧规则齐全 4')]]), '',
        '完整 17 例的六配置动作、发现事件、触发记录及成功→失败退化见 [逐例机制归因](逐例机制归因.md)。旧 7/4 分类仅作为历史分层，不强制本批仍属于同一失败类别。', '',
        '## 分模块判断','']
    for flag,j in judgments.items():
        if flag=='combination':continue
        lines += [f"**{flag}（{j['config']}）**：{j['judgment']} 相对 C0 新增 {j['paired_gains']} 例成功、丢失 {j['paired_losses']} 例；局部开关改变 {j['local_effects'].get('changed',0)} 个动作。",'']
    lines += [f"A 的代码级前置条件修复通过测试；本批记录 {g['C1']['condition_released_successes']} 次 C1 条件解除后成功和 {g['C5']['condition_released_successes']} 次 C5 条件解除后成功。这包含基础候选自行重试，不能全部归功于 A 的覆盖。B/C/D 的闭环价值必须分别结合关键知识覆盖、截尾与未转化比例、真实消耗和最终收取负例判断。",'',
        f"组合 C5 相对同批 C0 新增成功 {len(pairs['C5']['a_only'])} 例、丢失 {len(pairs['C5']['b_only'])} 例；最高单项成功数为 {max(g[m]['successes'] for m in METHODS[1:5])}/17。仅凭总分与模块共现不能证明协同，局部反事实也不能排除后续采样路径的贡献。未完成案例按缺知识、规则已知但资源/执行不足和收取失误逐例保留。本轮不引入复杂在线学习器或 SCAR-V4。",'',
        '## 完整性与复现','',
        f"独立重放 {verification['episodes_replayed']} 局、{verification['actions_replayed']} 个动作，物理状态、拒绝判定和目标结果全部与检查点一致。17 个 family 各六配置初态哈希相同；{verification['protected_prior_file_count']} 个历史文件未改变；API 日志、token 与 SQLite 账本对齐，未结算预留为 {verification['pending_reservations']}。",'',
        '对递归中止的评测归类、冗余制作的材料损耗补充标准和关键负例续动作属于明确标注的事后机制分析，细节记录在 `results/stage7/analysis_decisions.json`。这些调整不修改策略、环境动作或正式成功计数，也不产生新增模型实验。','',
        '交付包括冻结协议、全量公开观察/基础提案/执行动作、请求消息与用量、单步机制日志、全部配对与负例、真实物理反事实和复现脚本。未上传下载的游戏引擎、模型、运行凭据或账本数据库。详见 [复现指南](复现指南.md)。','']
    (reports/'实验报告.md').write_text('\n'.join(lines))
    details=['# Stage 7 逐例机制归因','',
        '此处包含全部 17 个任务，尤其保留旧共同失败、C0→新版本恢复及反向退化。动作索引从 0 开始，发现时间为完成第几个动作。机制触发只是归因线索；远端模型路径不同，只有同状态单步审计提供局部因果比较。','']
    for family in families:
        cid=family['case_id'];details += [f"## {family['target']} · {family['game']}", '',f"Family：`{cid}`。旧 Combined 成功：{family['old_combined_success']}；旧共同失败：{family['old_common_failure']}；旧缺失：{', '.join(family['old_missing']) or '无（名称齐全）'}。",'',
            table(['配置','成功/步数','缺失关键配方','实际触发','有效子目标','已知可制作→执行'],[[m,by[cid,m]['recovery_steps'] or '失败',', '.join(by[cid,m]['missing_key_recipes']) or '无',json.dumps(by[cid,m]['mechanism_trigger_counts'],ensure_ascii=False),by[cid,m]['subgoal_completed'],f"{by[cid,m]['known_ready_executed']}/{by[cid,m]['known_ready_opportunities']}"] for m in METHODS]),'',
            f"相对 C0 的新增恢复：{', '.join(family['C0_failed_new_success']) or '无'}；成功退化：{', '.join(family['C0_success_new_failure']) or '无'}。",'']
        for m in METHODS:
            e=by[cid,m];timeline=e['mechanism_timeline']
            # Show all discoveries, productive actions and explicit resource/goal guards,
            # not a success-only selection. Full all-action traces are linked below.
            critical=[x for x in timeline if x['new_key_recipes'] or x['productive'] or any(k in x['mechanism'] for k in ['D_goal','D_protect_goal','A_suppressed'])]
            details += [f"### {m} {LABELS[m]}",'',
                f"关键配方首次发现：`{json.dumps(e['first_key_recipe_actions'],ensure_ascii=False)}`。条件变化后成功重试：`{json.dumps(e['condition_released_successes'],ensure_ascii=False)}`。",'']
            if critical:
                details += [table(['索引','实际动作','新必要配方','实际产出','触发模块'],[[x['index'],x['action'],', '.join(x['new_key_recipes']) or '—',x['productive'],', '.join(x['mechanism']) or '—'] for x in critical]),'']
            if e['recovery_at_40']:
                finding=f"第 {e['recovery_steps']} 步完成物理持有目标。轨迹中的发现和制作顺序支持上述行为链，但不能把单项或组合开关当作该整局成功的必要原因。"
            elif e['missing_key_recipes']:
                finding='截至上限仍缺少必要配方名称：'+', '.join(e['missing_key_recipes'])+'；不能将失败仅归为执行模式或资源数量。'
            else:
                finding='必要配方名称已齐全，仍未完成；应结合真实材料条件、剩余步数与后续收取审计解释，名称齐全不等于所有数量与工作台条件充分。'
            details += [finding+f" 可避免保留材料消耗 {e['avoidable_reserve_depletion']}，可收取却做无关动作 {e['final_available_unrelated_actions']}，已制作但最终未收取 {e['produced_goal_but_uncollected_at_end']}。",'',
                f"终态局部条件（仅评测真值，不进入策略）：`{json.dumps(e['failure_context'],ensure_ascii=False)}`。",'',
                f"中间规则转化（包含截尾）：`{json.dumps(e['recipe_conversion_records'],ensure_ascii=False)}`。最后必要规则至目标：`{json.dumps(e['last_rule_to_goal'],ensure_ascii=False)}`。",'']
        details += [f"原始六轨迹分别位于 `results/stage7/trajectories_C0.jsonl.gz` 至 `trajectories_C5.jsonl.gz`，按 `{cid}` 查找；所有本例单开关审计在 `decision_counterfactuals.jsonl.gz`。",'']
    (reports/'逐例机制归因.md').write_text('\n'.join(details))
    if (out/'critical_counterfactuals.json').exists():
        from scar_unknown17_stage7.interpret import interpret
        interpret()
    print(json.dumps({'reports_written':2,'cost_usd':total,'judgments':{k:v.get('net') for k,v in judgments.items()}}))

if __name__=='__main__':main()
