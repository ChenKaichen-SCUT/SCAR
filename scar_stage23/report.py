"""Generate the seven Stage23 reports from immutable run evidence."""
from collections import Counter
import subprocess
from .common import *


def table(headers,data):
    def cell(x):return '—' if x is None else str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(cell(x) for x in r)+' |' for r in data])+'\n'


def save(name,text):
    (REPORTS/name).write_text(text.strip()+'\n')


def main():
    from scar_stage22b.common import forbid_network
    forbid_network();check_freeze()
    records=read(RESULTS/'metrics.json');aggregate=read(RESULTS/'aggregate.json');cost=read(RESULTS/'cost_reconciliation.json')
    verdict=read(RESULTS/'conclusion.json')['verdict'];contrasts=read(RESULTS/'paired_contrasts.json')
    assert verdict=='CONTROLLER_LIMIT_CONFIRMED', 'Reassess narrative if evidence changes; do not reuse this interpretation.'
    assert all(read(RESULTS/'verification'/f'{case_id(n)}.json')['passed'] for n in CASES)
    lookup={(r['start'],r['variant']):r for r in records}
    short={VARIANTS[0]:'Origin',VARIANTS[1]:'Reset',VARIANTS[2]:'Oracle'}
    pct=lambda x:f'{100*x:.1f}%'
    scope='本实验只有 **1 条 mark / seed42 母轨迹**，从动作前 a33、a35、a52、a64、a70、a100、a179、a193、a244、a271 分叉；不是 10 个独立任务或 30 次独立试验。所有分支均执行到绝对动作 300；共享前缀不重复计入续跑动作。'
    boundary='按用户确认的口径，保留原 goal、事实表、STM5 和模型输入生成链，只解除原“未解决证据时保留默认动作”仲裁分支的旧目标约束。公开条件 REJECT、库存/路线/材料检查及其他原控制逻辑仍保留；它们仍可能返回与旧目标有关的动作。因此 Oracle 是时机参照，不是解除全部控制限制后的数学上界。'
    criterion='付费运行前已固定描述性判据：至少 5/10 个检查点获得 ≥1 主线奖励，或至少一个检查点完成第一章。Reset 为 3/10、0 章；Oracle 为 3/10、1 章，故归为 `CONTROLLER_LIMIT_CONFIRMED`。这里的“普通 Reset 未达门槛”不等于“没有提升”。判据没有统计显著性含义，不能据此证明复杂状态更新机制必不可少。'
    summary_table=table(['版本','第一章完成','有主线增量','≥3 奖励','奖励和/均值','续跑动作','wait','非 wait 接受率','进展代理比例'],[
        [short[r['variant']],f"{r['chapter1_completed']}/10",f"{r['main_progress_checkpoints']}/10",f"{r['gain_at_least_3']}/10",f"{r['total_main_reward']}/{r['mean_main_reward']:.1f}",r['total_actions'],f"{r['wait_count']} ({pct(r['wait_count']/r['total_actions'])})",pct(r['accepted_nonwait']/r['total_actions']),pct(r['observable_progress_actions']/r['total_actions'])] for r in aggregate])
    paired=table(['检查点','剩余动作','Origin 奖励','Reset 奖励','Oracle 奖励','第一章完成位置（O/R/C）'],[
        [case_id(n),301-n,*[lookup[n,v]['final_main_reward'] for v in VARIANTS],'/'.join(str(lookup[n,v]['chapter1_step'] or '未完成') for v in VARIANTS)] for n in CASES])
    cost_table=table(['版本','新增请求','新增输入 token','新增输出 token','新增费用 USD'],[
        [short[r['variant']],r['new_model_requests'],r['input_tokens_new'],r['output_tokens_new'],f"{r['new_model_cost_usd']:.9f}"] for r in aggregate])
    frozen=read(RESULTS/'execution.json')['freeze_commit']
    source=read(RESULTS/'protocol.json')['source_commit']
    numstat=subprocess.check_output(['git','diff','--numstat',source,frozen],cwd=ROOT,text=True)
    changes=[]
    for line in numstat.splitlines():
        added,removed,path=line.split('\t');changes.append(dict(path=path,added=added,removed=removed))
    write(RESULTS/'frozen_change_ledger.json',dict(source_commit=source,experiment_commit=frozen,files=changes,
        old_algorithm_files_modified=0,new_python_lines=sum(int(x['added']) for x in changes if x['path'].endswith('.py')),
        reset_policy_file='scar_stage23/reset.py',reset_policy_file_lines=len((ROOT/'scar_stage23/reset.py').read_text().splitlines())))
    save('Stage23实验报告.md',f'''# Stage23 实验报告

最终分类：**{verdict}**。解除默认仲裁锁后，Stage18 在部分状态恢复了真实主线推进；Oracle 的 a35 分支在第 276 步完成第一章。普通 Reset 的最高主线奖励为 7，尚未完成第一章。不能将结果写成“普通 Reset 无效”或“Stage18 完全没有规划能力”。

{scope}

{summary_table}

{paired}

所有 30 个槽位完成；20 条干预续跑、10 段原轨迹后缀，总计 5307 个逻辑动作。完整主线任务完成数三版本均为 0；Oracle 的唯一第一章完成最终处于 chapter=1/stage=0（第二章开头）。原生 done 均未提前触发。

## 实验边界与冻结

{boundary}

实验实现独立提交：`{frozen}`；来源提交：`{source}`。所有旧算法文件修改数为 0；新增实验 Python 共 {sum(int(x['added']) for x in changes if x['path'].endswith('.py'))} 行，其中 reset 适配文件 98 行，其余用于回放、检查点、复用、记录和执行。完整 55 文件及增删行数见 [冻结修改清单](../../results/stage23/frozen_change_ledger.json)。新增的分析与核验代码在结果提交中单独保存，没有进入实验控制链。结果发布提交号记录于 [发布记录](../../results/stage23/publication.json)。

普通触发器只读取原公开观测和登记目标计数：同一登记目标 12 次反馈未变，或目标尝试连续失败 3 次，或当前公开位置/显式指令与旧目标不符。按 OR 触发，不调参。早期普通 Reset 在 a34/a36 触发，Oracle 在 a33/a35 触发；另八处两者立即激活，后续动作和环境哈希全部相同，采用同状态、同输入的配对响应复用。这八对不是八次独立的 Oracle 改善证据。

## 核心问题

Q1：普通 Reset 能恢复部分任务推进：3 个检查点获得 1、7、3 奖励；另外 7 个仍为 0。a33 的 wait 反而从 190 增至 205，a52 从 190 增至 191，a179 从 88 增至 92，不能只呈现改善任务。

Q2：Oracle 在 a33/a35 同状态、同输入、同一原响应下将 `enter hall` 改为原提案 `talk to remy`，立即获得公开任务信息，局部信息阻塞的因果证据成立。随后 a35 完成第一章，证明至少存在可以继续推进的采样轨迹。但后续输入和随机响应已分叉，不能把奖励 10 对 7 严格归因于提前 1 步本身。

Q3：改善并非只有更多随机走动：记录到制作并收取 oak_rod/copper_sword、写入 kindness、解锁 stalls、获得 torch、进入 backstreets、击败 page_gnawer 等原生主线里程碑。但较晚 8 处只有 a100 获得奖励，且 Oracle 新访问区域中部分发生在第一章完成之后；不能把所有新区域/新状态都当成有效任务探索。

{criterion}

## 费用与完整性

{cost_table}

总计新增 **{cost['new_requests']} 次**模型请求，输入 {cost['input_tokens']:,}、输出 {cost['output_tokens']:,} token，按返回 usage 与调用时段官方单价核算 **${cost['usage_priced_usd']:.9f}**。这是 usage 计价金额，不是账户发票。调用时单价和逐请求账本全部保存；[官方价格来源](https://api-docs.deepseek.com/quick_start/pricing/)。

干预分支复用 165 个 Stage22 原响应、1156 个配对新响应；Origin 另外有 1769 个重叠后缀逻辑决策引用原响应。复用不重复收费。新增请求全部成功，无重试、未结预留费或模型 JSON/截断异常；逻辑输入最大 3495 token，输出限制保持 768。没有对低分分支重跑，没有修改算法后再试。离线分析与回放新增模型调用为 0。

原始 300 步环境轨迹已逐步核验，关闭 reset 后 300 步原 Agent 决策一致，30 个初始模型上下文一致；20 条干预续跑的全部 3538 步已离线复现原生状态哈希、反馈、奖励、模型上下文、完整决策和最终记忆。4478 个冻结项目文件及 278 个引擎文件哈希不变。详见 [核验回执](../../results/stage23/verification/) 与 [费用复核](../../results/stage23/cost_reconciliation.json)。

## 解释限制与建议

本轮支持控制器存在可恢复的信息阻塞，并显示简单默认仲裁释放不足以稳定完成任务。它没有隔离残留的旧目标提示、其他控制检查、材料/容量执行和基础 LLM 规划的分别贡献。首次不可恢复错误位置均记为“未证实”：最终预算耗尽、死亡或零奖励不能证明环境已不可恢复。Stage22-B 在 a271 的同状态人工公开信息路径可于剩余 30 步中的 7 步取得首奖励，更不能将这个检查点零分解释为物理无解。

不将当前 Reset 升级为正式 Stage18.1，也不据此关闭 TTCL 研究线。若后续另行授权，值得先研究目标有效性与残余约束的状态更新语义及独立样本验证；本阶段到此收束，未开发 Stage18.1。
''')
    final_table=table(['检查点','版本','动作数','主线奖励','章/阶段（原生从 0 编号）','第一章完成','终止','首次不可恢复错误'],[
        [r['case'],short[r['variant']],r['actual_actions'],r['final_main_reward'],f"{r['final_quest_state']['chapter']}/{r['final_quest_state']['stage']}",'是' if r['chapter1_completed'] else '否','动作 300 上限','未证实'] for r in records])
    strata=table(['分层','版本','检查点数','有奖励','第一章完成','奖励和'],[
        [r['group'],short[r['variant']],r['checkpoints'],r['gained_main_reward'],r['chapter1_completed'],r['reward_sum']] for r in read(RESULTS/'stratified.json')])
    save('三版本轨迹对比.md',f'''# 三版本轨迹对比

{scope}

{paired}

{final_table}

## 分层核对

primary_early 是 a33/a35；other_checkpoints 为其余八处。这一分层与下面按剩余预算分层相互重叠，不能求和作为额外样本。

{strata}

所有对比起点的公开观测、物理状态、环境随机数和已存记忆相同；原模型、提示模板、STM5、输出限制、成功判定与绝对动作预算相同。Origin 原后缀不重新采样；跨不同检查点不共享新回复。同检查点两干预版若状态、动作号、messages 一致，复用同一个随机响应。八个较晚检查点两干预版整条路径相同，只有 a33/a35 出现政策路径分叉。

逐步原始记录、决策与请求位置见 [5307 行证据索引](../../results/stage23/evidence_index.csv)，可重算 30 行指标见 [paired30.csv](../../results/stage23/paired30.csv)。奖励节点的完整反馈见 [quest_milestones.json](../../results/stage23/quest_milestones.json)。
''')
    behavior=table(['检查点','版本','首次 stale（母轨迹）','reset','reset 前连续 wait','reset 当步动作','首次仲裁释放','首次新事实','再次告知 oak 任务','首次主线奖励'],[
        [r['case'],short[r['variant']],32,r['first_reset'],r['waits_immediately_before_reset'] if r['first_reset'] else None,r['reset_first_action'],r['first_effective_release'],r['first_new_fact_after_reset'],r['first_oak_goal_refresh_after_reset'],r['first_quest_gain']] for r in records])
    novelty_table=table(['检查点','版本','新状态签名','新区域','接受非 wait','进展代理动作','wait 比例'],[
        [r['case'],short[r['variant']],r['new_state_discoveries'],r['new_area_count'],f"{r['accepted_nonwait']}/{r['actual_actions']}",r['observable_progress_actions'],pct(r['wait_ratio'])] for r in records])
    save('reset前后行为变化分析.md',f'''# reset 前后行为变化分析

{behavior}

reset 为动作仲裁前激活时刻；“首次仲裁释放”是第一次命中新增释放分支，可能晚于 reset。“首次新事实”只统计 Stage22-B 的 13 类固定公开知识标记，相对整个共享前缀已见知识去重，不是所有自然语言信息。空值不代表没有任何新信息。已知任务被再次告知单列，不能算成新发现。原文本与更一般状态变化均保留在逐步指标里。

{novelty_table}

新状态签名只含位置、手持、装备、地面物品名称及 NPC 名称，排除时间、HP、stamina 和地面数量；地面刷新或 NPC 自行活动也能改变签名。新区域由动作后的公开位置计算，若同一步进入后死亡复活，该区域不会计入公开最终位置口径（例如 Oracle-a35 的 a166）。因此它不是隐藏地图遍历总数。

“接受非 wait”排除 invalid_action 及公开 Cannot/Invalid/教程拒绝反馈；这是可复算的文本判据，不等于任务相关。“进展代理”还要求主线增量、制作奖励、新知识标记、新区域、新持有物名称或首次击杀之一。它仍可能包括支线或无关物品，严格任务推进看原生 quest 奖励。

a35 Oracle：a35 对话获得任务，a40 收取 oak_rod，a50 收取 copper_sword，a94 写 kindness，a166 到达 stalls，a194 收取 torch，a271 到 backstreets，a276 完成第一章。这个序列支持“解除阻塞→获得信息→连续任务推进”。a33 两干预版只得到 1 奖励后再次停滞；a271 虽减少 10 个 wait，却没有奖励或进展代理动作，不能称为恢复。

a100 的两干预版到 a294 才取得首奖励，a297/a299 再推进两阶段。首奖励延迟 194 个绝对步差，表明可推进并不等于高效。该分支不是“仅早期机会点有效”的例外排除项，已纳入全部结果。
''')
    stale_table=table(['检查点','版本','旧 goal 文本最长连续长度（含前缀）','续跑未释放默认权决策','release 激活决策','命中释放分支','提案仍不同于执行'],[
        [r['case'],short[r['variant']],r['longest_old_goal_text_run_including_shared_prefix'],r['stale_authority_decisions'],r['reset_active_decisions'],r['arbitration_releases'],r['remaining_overrides']] for r in records])
    save('stale_goal统计.md',f'''# stale goal 统计

{boundary}

母轨迹 a31 登记 `enter hall`，a32 起出现已在目标地点却保留原目标的 stale 状态；三个版本 goal 文本均持续到 a300（a31–300 共 270 次决策）。这不是 reset 未触发，而是用户指定保留原结构化输入的结果。

{stale_table}

表中的“默认权”仅指新增 gate 针对的未解决证据默认仲裁分支。Origin 合计 1769 次未释放，Reset 为早期 a33/a35 两次，Oracle 为 0。**0 不代表清除了所有旧目标影响**：REJECT 后的原控制器修正、候选生成及模型可见目标仍在。因而不能使用此数声称控制器所有目标约束都已解除。

所有 reset 事件的触发原因和计数见 [metrics.json](../../results/stage23/metrics.json) 的 reset_events；目标字段、原始提案、评估和实际执行见 [逐步证据索引](../../results/stage23/evidence_index.csv)。没有根据成功与否重新定义 stale 起点，也没有把后期失败倒推为某个触发器必然错误。
''')
    wait_table=table(['检查点','版本','wait/动作','比例','最长连续 wait','最长 wait 区间'],[
        [r['case'],short[r['variant']],f"{r['wait_count']}/{r['actual_actions']}",pct(r['wait_ratio']),r['longest_wait'],
         ', '.join(f"{w['start']}–{w['end']}" for w in r['wait_runs'] if w['length']==r['longest_wait'])] for r in records])
    blocked=table(['检查点','版本','剩余 REJECT 条件计数（可重叠）'],[
        [r['case'],short[r['variant']],', '.join(f'{k}={v}' for k,v in sorted(r['post_reset_rejected_conditions'].items()))] for r in records if r['variant']!=VARIANTS[0]])
    save('wait行为统计.md',f'''# wait 行为统计

合计 wait：Origin 1311/1769（74.1%），Reset 1146/1769（64.8%），Oracle 1086/1769（61.4%）。这是重叠检查点后缀的描述性加权汇总，不是独立试验总体估计。普通 Reset 减少 165 次 wait，仍有大量停滞。

{wait_table}

{blocked}

上表每一项是条件出现次数，同一动作可能既触发 materials 又触发 nominal_single_craft_material，不能相加作为“被拒动作数”。这些计数不直接说明拒绝有害：例如 a271 分支 a272 在手持 2 cloth 时提出拾取 oak_log，原有 hands 检查拒绝有当前公开证据。

原目标默认权释放后，仍可能出现“基础模型重复不可行提案→保留的条件检查拒绝→控制器 wait”。a33 Reset 最后仍提出缺少 resin_clump 的 oak_dagger 制作，a52/193 长时间重复满手拾取。它们提示容量释放、材料执行、记忆与剩余控制交互还未隔离；不能仅凭 REJECT 就称这些防护本身有害。没有离线证明它们在同状态可成功的提案，不标记为已验证局部损失。
''')
    counter_table=table(['检查点','对照','首次动作分歧','Origin 动作','干预动作','同状态/同输入/同响应'],[
        [r['case'],r['comparison'],r['first_action_divergence'],r.get('origin_action'),r.get('variant_action'),
         '/'.join('是' if r.get(k) else '否' for k in ['same_state_at_divergence','same_context_at_divergence','same_raw_response_at_divergence'])]
        for r in contrasts if r['comparison'].startswith('Stage18-Origin')])
    evidence=rows(RESULTS/'key_evidence.jsonl.gz')
    def quote(case,variant,step):
        r=next(x for x in evidence if x['case']==case and x['variant']==variant and x['step']==step)
        return f"`{r['trace']}`\n\n提案 `{r['proposal']}` → 执行 `{r['action']}`；quest={r['quest_score']}。\n\n```text\n{r['feedback']['text'].strip()}\n```\n"
    save('关键反事实案例.md',f'''# 关键反事实案例

{counter_table}

20 个首次动作分歧均核验为同物理状态、同模型上下文、同一保存响应。可将这些局部动作差别归于仲裁干预；获得信息或奖励要依据随后的原生反馈，不能只凭原提案措辞判断价值。之后轨迹和模型输入分叉，整局差值不能当作单一步骤的严格因果效应。

## a33/a35：直接恢复被覆盖的对话

Origin a33/a35 原提案为 talk to remy，均被替换为 enter hall；Oracle 立即执行该提案，环境公开 oak_rod 任务。普通 Reset 在 a34/a36 激活后，分别于 a35/a37 获得相同任务信息。

{quote('mark-a035','Oracle-Reset',35)}

## a35 Oracle：第一章实际完成

奖励时序：40→1，50→2，52→3，94→4，96→5，163→6，166→7，194→8，271→9，276→10。a166 同时死亡且复活，后续仍推进，死亡不能直接标为不可恢复。a35 Reset 的奖励为 7，其 a125 已进入 stalls，随后未完成 torch 阶段；两条不同随机响应路径不能用于宣称“早 1 步释放必然多完成 3 阶段”。

{quote('mark-a035','Oracle-Reset',276)}

## a33 Reset：部分恢复后的再停滞

{quote('mark-a033','Stage18-Reset',300)}

该步材料检查明确记录 resin_clump owned=0，而原提案要求制作 oak_dagger；候选原样放行是否能成功没有另做反事实验证，不能把覆盖直接归为有害。这个分支获得过首奖励，但最终 wait 比原后缀更多。

## a271：释放仍未推进，不等于状态物理无解

{quote('mark-a271','Stage18-Reset',271)}

下一步 a272 的模型提出 pick up oak_log，原有 hands 检查记录 {{cloth: 2.0}}，实际 enter hall；该动作完整评估见原轨迹第 2 行。到 a300 无主线奖励。Stage22-B 已保存同起点、仅公开信息的人工 7 动作首阶段恢复见证，仍在原剩余 30 动作内；本轮未重跑这条见证，也不把人工路径算成 Agent 成绩。

更完整的选定原文与决策见 [key_evidence.jsonl.gz](../../results/stage23/key_evidence.jsonl.gz)，全部步均可从 [evidence_index.csv](../../results/stage23/evidence_index.csv) 定位。没有删去七个零主线奖励检查点。
''')
    save('Stage18.1开发建议.md',f'''# 是否继续开发 Stage18.1

**结论类别：{verdict}。当前版本不应直接作为 Stage18.1 发布。**

{criterion}

可以确认的是：保持原规划、记忆和提示生成链，仅改变默认仲裁，确实能在某些状态恢复公开信息获取和多阶段执行；Oracle-a35 完成第一章，排除了“解除这部分阻塞后在任何所测状态都无法继续”的绝对说法。普通 Reset 的 a33/a35/a100 同样有部分恢复，不符合“完全无提升”的字面叙述。类别使用的是预登记的完成门槛，而不是改写这些正向证据。

尚未确认的是：更复杂的触发器是否能稳定解决问题，额外的智能模块是否必要，以及失败主要来自基础 LLM 规划、旧目标提示、材料执行、STM5 还是其他保留控制检查。只有一个母轨迹、两个真正不同的早期释放时机、每条新输入一次随机响应，无法估计跨种子可靠性；八个后期 B/C 完全相同，不能扩大证据强度。

工程上，已满足的移动目标仍被登记且参与候选/提示是明确的状态语义问题；generic reset 的释放口径及完成判据需要一致。但这不授权本轮修改目标解析、提示、容量策略或控制器其余分支。研究上，可讨论的独立问题是：公开证据随环境变化时，代理怎样维护目标有效期、撤销过期约束，并保留可校验的行动依据。当前结果只提供研究动机，尚不是新机制有效性的证据。

建议保留这份最小消融为诊断结果；暂不开发或宣称 Stage18.1 有效，也不按 DESIGN_LIMIT_CONFIRMED 关闭 TTCL 线。若下一阶段另行授权，应先明确是否允许改变模型可见的 stale goal、如何单独隔离剩余条件检查，并采用独立母轨迹/种子评价。不能在同一失败轨迹上不断调阈值直到成功，不能新增 mark 专用行动规则充当通用修复。

本阶段实际执行到此结束：未新增规划、反思、记忆、探索模块，未重跑 remnant/metropolis，未开始 Stage18.1。
''')
    save('README.md',f'''# Stage23：Minimal Controller Reset Ablation

结论 **{verdict}**；1 条母轨迹、10 个检查点、30 个完整轨迹槽位。第一章完成 Origin/Reset/Oracle = 0/0/1；有主线增量 = 0/3/3；新增模型请求 {cost['new_requests']}，usage 费用 ${cost['usage_priced_usd']:.9f}。

- [实验报告](Stage23实验报告.md)
- [三版本轨迹对比](三版本轨迹对比.md)
- [reset 前后行为变化](reset前后行为变化分析.md)
- [stale goal 统计](stale_goal统计.md)
- [wait 统计](wait行为统计.md)
- [关键反事实案例](关键反事实案例.md)
- [Stage18.1 开发建议](Stage18.1开发建议.md)
- [运行前协议](预登记实验协议.md)
- [机器可读结果](../../results/stage23/aggregate.json)、[费用](../../results/stage23/cost_reconciliation.json)、[证据索引](../../results/stage23/evidence_index.csv)

## 离线重算

使用冻结的 AgentOdyssey 引擎和现有 Python 环境，设置 `AGENTODYSSEY_ROOT` 与 `PYTHONPATH` 后，在仓库根目录运行：

```bash
export PYTHONHASHSEED=0
export AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey_stage22
export PYTHONPATH="$PWD:$AGENTODYSSEY_ROOT"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.analyze
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.audit
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.verify --start 35
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.report
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.package
```

`verify --start` 可依次传入 33、35、52、64、70、100、179、193、244、271 重放全部分支；这些分析入口主动禁用网络，不会调用模型。完整物理分叉快照、原 Agent 记忆、原始模型请求/响应、决策及终点记忆均已归档，运行时缓存和密钥不上传。原环境代码与下载依赖不重复上传。

请勿将 `batch` 当作分析入口；它是冻结的实验执行器。已完成分支有幂等保护，本轮没有为低分再次采样。
''')
    print('Generated seven reports, README and frozen modification ledger.')


if __name__=='__main__':main()
