"""Rebuild Stage24 tables, figures and evidence-linked research reports."""
from .common import *
from .analyze import final_folder


def table(headers,records):
    def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(cell(x) for x in r)+' |' for r in records])+'\n'


def save(name,text): (REPORTS/name).write_text(text.strip()+'\n')
def pct(x):return f'{100*x:.2f}%'


def main():
    offline();check_freeze();metrics=read(RESULTS/'metrics.json');first=read(RESULTS/'metrics_first_pass.json')
    costs=read(RESULTS/'cost_accounting.json');totals=read(RESULTS/'totals.json');checks=read(RESULTS/'conclusion.json')
    get=lambda g,m:next(r for r in metrics if r['game']==g and r['method']==m)
    b,a=totals;mark=get('mark','AGC');diagnostics=read(RESULTS/'trajectory_diagnostics.json')
    main_table=table(['游戏','方法','主线','辅助','动作','第一章','全主线','终止'],[
        [r['game'],r['method'],r['main_quest'],r['supplementary'],r['actual_actions'],r['first_chapter_step'] or '未完成',
         r['full_quest_complete'],r['status']] for r in metrics])
    first_table=table(['游戏','初次动作','初次主线','初次辅助','初次终止','初次请求','初次费用 USD'],[
        [r['game'],r['actual_actions'],r['main_quest'],r['supplementary'],r['status'],r['requests'],f"{r['cost_usd']:.9f}"] for r in first])
    diag_table=table(['游戏','方法','stale 段/步','reset','INVALID','SUSPICIOUS','wait 数/比例','相邻重复比例','新状态','新区域','平均目标长度'],[
        [r['game'],r['method'],f"{r['counters'].get('stale_goal_episodes',0)}/{r['counters'].get('stale_goal_steps',0)}",
         r['counters'].get('goal_resets',0) if r['method']=='AGC' else 'N/A',r['counters'].get('invalid_triggers',0) if r['method']=='AGC' else 'N/A',
         r['counters'].get('suspicious_triggers',0) if r['method']=='AGC' else 'N/A',f"{r['counters']['waits']}/{pct(r['wait_ratio'])}",pct(r['repeated_action_ratio']),
         r['counters']['new_state_discoveries'],r['counters']['new_area_count'],f"{r['mean_goal_duration']:.2f}"] for r in metrics])
    cost_table=table(['游戏','方法','请求','输入 token','输出 token','最高输入 token','费用 USD'],[
        [r['game'],r['method'],r['requests'],r['input_tokens'],r['output_tokens'],r['max_input_tokens'],f"{r['cost_usd']:.9f}"] for r in metrics])
    save('三游戏结果表.md',f'''# Stage24 三游戏结果表

每游戏一个 seed42、最多 300 个环境动作。AGC 的 remnant/mark 是经用户授权的解析修复续跑，前缀没有重做；metropolis 使用完整原版。不是三个重新从零开始的同版本修复版试验。基线全部引用 Stage22，没有新增基线调用。

{main_table}
最终主线均值 {b['main_mean']:.3f} → {a['main_mean']:.3f}，辅助均值 {b['supplementary_mean']:.3f} → {a['supplementary_mean']:.3f}。第一章完成数 **1/3 → 1/3**：mark 改善抵消了 metropolis 退步；全主线均 **0/3**。AGC 实际动作 644，剩余 256 个动作因本身的硬拒绝终止而未使用，不能称为三个 300 步完整执行。

## 初次结果必须保留

{first_table}
remnant 的第 6 次决策、mark 的第 106 次决策原先因引文换行差异终止；只修复空白匹配，后续分别在第 92、254 次决策因不同硬条件终止。初次结果不是额外独立样本，费用也不和续跑重复累加。

## 共同诊断口径

{diag_table}
stale 段为同一非空目标持续至少 12 步且满足 8 步停滞窗口的连续区段；停滞要求新信息≤1 且同一动作≥5。相邻重复分母为实际动作数−1。新状态、新区域均来自共同公开文本提取器；新区域不含初始区域，首次被发现的状态可以由死亡或非主线变化造成，不能直接当作任务进展。reset 是登记目标替换事件，包含正常教程/任务切换，不能等同于成功从故障恢复。

Stage18 metropolis 的登记目标为空，所以 stale 为 0 且空字段连续段均长 300；这没有“目标有效”的含义。它仍有 172 个通用停滞步。AGC metropolis 的 stale=0 也漏掉了持续 219 步的收集目标与多动作拾取/丢弃循环。详细审计见 [轨迹分析](轨迹分析.md)。INVALID 三局均未触发，不能宣称该分支的有效性已得到验证。

## 请求与费用

{cost_table}
本阶段唯一新增请求 **{costs['unique_new_model_requests']}**，输入 **{a['input_tokens']:,}**、输出 **{a['output_tokens']:,}** token，费用 **${costs['cost_usd']:.9f}**。其中初次运行 417 次 / $0.168099552，修复后新增 247 次 / $0.105534570。已经付费但续跑不再需要的两条原重考虑回复仍计入费用。

664 = 644 个已执行动作所需首请求 + 14 次已执行决策内的额外重考虑 + 4 次最终终止决策请求 + 2 条原终止点遗留且已付费的第二回复。续跑原终止点首回复来自缓存，不另收费。按实际执行动作粗略归一，AGC ${a['cost_usd']/a['actions']:.7f}/动作，旧 Stage18 ${b['cost_usd']/b['actions']:.7f}/动作；不能把总费用下降全部解释为效率优势，提前终止节省了动作预算且损失完成机会。

费用根据每个响应的 usage、调用时段单价核算，已与本地 SQLite 收费账本逐项核对，不是账户发票。没有给 LongContext 或其他基线增加调用。本轮输出上限保持 768；mark 有两条截断/非法 JSON 和三条 JSON 合法但缺少 action 等字段的回复，均由一次预设重考虑继续，详见 [响应异常](../../results/stage24/response_anomalies.json)。

可重算数据：[指标](../../results/stage24/metrics.json)、[CSV](../../results/stage24/three_game_results.csv)、[请求索引](../../results/stage24/request_index.csv)、[官方评分输出](../../results/stage24/official_scores/AGC.json)、[费用对账](../../results/stage24/cost_reconciliation.json)。
''')
    milestones=[]
    for game in GAMES:
        r=get(game,'AGC');milestones.append('### '+game+'\n\n'+table(['动作','动作文本','奖励增量','累计主线'],[[x['step'],x['action'],x['increment'],x['score']] for x in r['quest_milestones']]))
    long=[]
    for d in diagnostics:
        if d['method']=='AGC':
            s=max(d['goal_segments'],key=lambda x:x['length'])
            long.append([d['game'],f"a{s['start']}–a{s['end']}",s['length'],s['quest_gain'],s['informative_steps'],s['goal']])
    save('轨迹分析.md',f'''# Stage24 轨迹分析

所有编号为实际环境动作编号 a1 起；“第 92/254 次决策”没有执行环境动作。逐步原始证据可从 [evidence.jsonl.gz](../../results/stage24/evidence.jsonl.gz) 的 game/method/step 定位，完整 observation、模型原提案、重考虑、最终动作、控制状态和环境反馈均在对应 trajectory.jsonl.gz。

![主线奖励曲线](figures/main_quest.png)

## mark：恢复主线，但第二章仍有库存循环

AGC a28 执行 `enter hall` 后完成字面移动目标；a32 `talk to remy` 获得任务提醒，a33–39 制作并收取 oak_rod。旧 Stage18 a31 进入 hall 后仍持有旧目标，a33/a35 原提案对话被覆盖；AGC 本次没有把模型动作替换成 wait。a39 起连续主线里程碑，a118 击败 page_gnawer 完成第一章，a147 到达 crystal_grotto 获得第二章第一个奖励，最终 11 分。两条模型轨迹早已分叉，不能把全部 11 分作为目标状态模块的严格因果增量。

a157–253 持续“Gather 10 coins…”目标 97 步，其中 `pick up coin` 32 次、`drop coin` 31 次，没有新的主线奖励。手持容量约束反复出现；部分模型回复在同一段内反复推理“需要容器但买容器又需要更多钱”。a197 后控制状态变为 SUSPICIOUS，a198–201 进行了四次软限制重考虑后放行；a201 的新观测再次激活目标，未稳定解决数量/容量问题。不能把零 wait 写成没有浪费或控制器完全解决了恢复。

第 254 次决策：两条模型回复都引用 `I see 8 coin near me.`；真实 observation 是包含 berry、oak_log、resin_clump、coin 等项目的完整物品列表。因此它是事实摘要，不是逐字子串，空白规范化仍不会通过。先提 `talk to harper_stone`，再提 `pick up coin`，被硬证据约束终止。同状态原生回放接受首个对话动作并返回商店信息，但主线增量为 0；这是可执行动作被拒的证据，不证明损失了新的信息或最终分数。原始反馈见 [终止动作审计](../../results/stage24/terminal_native_audit.json)，不能据此推断余下整局可完成。

## remnant：解除教程目标后进入任务，仍未解决装备/照明

修复后 a6 使用缓存原回复继续。a26 进入 hall，a35 用 key 解锁 library 得到主线 1，a36 公开指令要求先取得武器。a38–91 的武器目标持续 54 步，包含往返 armory/hall、战斗和照明相关操作；期间两次死亡。a35 之后 56 个实际动作没有主线增量。结尾 a90 进入黑暗 armory，a91 返回 hall。

第 92 次决策两次生成 `write note on paper_7`，公开签名是 `write <text> <writable_name>`；共享语法检查把未加引号的额外 `on` 作为第三个参数拒绝。同状态原生检查也报 requires format / got 3 parameter(s)，说明不是解析器误拒有效语法。无替代动作、无自动 wait，按预登记终止在 91 个已执行动作。该失败不应被包装成充分利用了 300 步，也不能将停止后的未观察路径当作无规划能力的证明。

## metropolis：多动作循环使通用停滞阈值漏检

a5 已拿 evidence_dossier_0 并到达 4 分；a6/a12 进入 evidence_room 未完成交付。a18 得到公开支线提示，a19 模型自行把制作 gavel_club 作为可能帮助主线的支线，原 reasoning 使用 “may provide tools or progress relevant to cataloguing evidence”。控制器没有提供这一规划。

a19/a41 制作缺工作台，a53 缺材料，a55 拾取材料遭手持容量拒绝。a55 的目标加入 iron_filings、marble_chunk，但附带引文只是一份可见物品列表；能核验引文来自环境，不能由此证明这些都是目标必要材料。a82–300 同一目标持续 219 步，四类材料的拾取/丢弃合计 191 次，实际 craft 奖励为 0。a297/a300 又尝试制作原生反馈称无法制作的 iron_filings。

最后一次主线奖励仍是 a5，其后 295 步没有主线增长；第一章未完成，旧 Stage18 则在 a31 达到 7 分并完成第一章。几乎不 wait 的负面局完整保留。

## 对进展代理的审计

{table(['游戏','最长同目标区间','长度','区间主线增量','被记为 informative','目标'],long)}
最长区间中，remnant 45/54、mark 48/97、metropolis 36/219 步被记为 informative，但主线增量均为 0。公开新状态、新反馈、战斗/复活与物品变化并不必然与目标相关；多种动作交替也可能达不到“8 步中某一动作至少 5 次”的停滞门槛。额外事后 20 步紧窗口诊断同样没有命中这三段，不能用一个窄指标的零值排除长周期循环。原动作频数与奖励平段提供了更直接的描述证据，见 [全部目标区段](../../results/stage24/trajectory_diagnostics.json)。没有据此修改阈值或重跑。

## 全部主线里程碑

{chr(10).join(milestones)}

## 模型异常和恢复

mark a160、a167、a236 的首回复是只包含 reasoning 的合法 JSON；a161、a206 的首回复达到输出上限并产生不完整 JSON。五处均由原定一次重考虑获得动作，分别执行 enter glade、attack fen_cutthroat_0、drop coin、talk to harper_stone、drop coin（按上述编号对应）。没有扩大输出上限、追加多次重试或替换模型。引文拒绝、语法拒绝与传输/JSON 异常分开计数。
''')
    save('Stage18失败模式对应分析.md','''# Stage18 与 AGC 失败模式对应

| 旧证据 | AGC 对应变化 | 本次观察 | 能支持与不能支持的结论 |
| --- | --- | --- | --- |
| mark `enter hall` 已实现仍作为物品式目标约束动作 | 字面进入目标以公开 location 完成；后续目标由同一模型声明 | a28 进入 hall，a32 对话，a39 首奖励，a118 第一章完成 | 当前轨迹避免了旧目标长期覆盖；不能独立分离 tracker 的因果贡献 |
| Stage18 mark 214 次覆盖、190 次 wait，其中 188 次 wait 来自覆盖 | 控制器不再产生替代动作，只 EXECUTE/RECONSIDER | AGC 已执行动作零替换、零 wait | 消除了这种动作替换路径；硬拒绝提前终止仍可能阻断有效行动 |
| 旧表示没有稳定处理移动目标/任务更新 | ACTIVE/SUSPICIOUS/INVALID/COMPLETED 与公开反馈、模型子目标登记 | AGC mark 一次 SUSPICIOUS，三游戏 INVALID 均未触发 | 有运行到的状态更新分支；尚无 INVALID 恢复有效性的实测支持 |
| 库存、材料和主线依赖执行仍可能失败 | 有界同上下文失败记忆，不主动规划替代动作 | mark a157–253 拾币/丢币 63 次；metropolis a82–300 材料拾取/丢弃 191 次 | 单纯去掉旧覆盖不能自动解决数量、容量与依赖执行 |
| Stage18 metropolis a31 后无新增主线、wait 很多 | AGC 几乎无 wait，有更多公开状态 | AGC a5 后没有新增主线，4 分低于旧 7 分 | 更多可见变化并不保证更好主线表现；行为代理不充分 |

Stage23 仍仅是一个 mark 母轨迹的十个检查点：普通 Reset 3/10 有奖励但 0/10 第一章，Oracle 3/10 有奖励且 1/10 第一章；不能与本轮从初态开始的三游戏样本混合计算成功率。该阶段的同状态仲裁证据支持旧控制器确实存在局部信息压制；AGC 是同时更改目标输出、状态摘要、失败记忆和动作仲裁的新 workflow，不是 Stage23 的单开关消融。

AGC 在 mark 的恢复与上述机制诊断相符，但新硬引文门槛先在换行问题处中止两局、后在 mark 的真实物品列表摘要处再次中止。应将控制可靠性同时看成“能否阻止无效循环”和“是否误拒有价值提案”，不能只统计动作替换次数。无同状态后续模型采样，不给整局结果分配严格因果责任。

原证据：[Stage22-B 分析](../stage22b/mark环境失败案例分析.md)、[Stage23 报告](../stage23/Stage23实验报告.md)；本阶段：[逐步索引](../../results/stage24/evidence.jsonl.gz)、[响应及终止证据](轨迹分析.md)。
''')
    save('空白字符修复与续跑记录.md',f'''# 授权修复与续跑记录

实验冻结提交：`0aa82154f8a69b06f23c620dd95298424466b954`。
用户授权修复提交：`0068b85fb7ca14bc9a5dec2ae764578de564c092`。

政策代码只在 `agents/agc/control.py` 替换 1 行、增加 2 行：引文及候选公开文本都执行 `' '.join(text.split())` 后再做子串匹配。没有删改词语、标点、状态阈值、目标或动作。`scar_stage24/common.py` 增加有来源哈希的冻结例外；新增 `repair.py` 专门恢复原检查点。该独立提交共 6 文件、+202/−3 行，含修复前证据和冻结清单。

remnant 保留 a1–5，恢复第 6 次决策；mark 保留 a1–105，恢复第 106 次决策。原检查点 SHA、原请求数/费用和续跑提交保存在 [repair_launch](../../results/stage24/repair_launch/)。两个首响应均原样缓存复用；原第二区别回复没有进入续跑，但仍保留并计费。metropolis 已在原版进程中完整执行，没有切换策略。

{first_table}
最终续跑结果：remnant 91 步 / 主线 1，mark 253 步 / 主线 11；两局均因不同的预设硬门槛再次终止。没有第二轮政策修复，也没有把首次失败记录覆盖。完整初次结果在 `results/stage24/runs/`；两局带原样前缀的续跑结果在 `results/stage24/resumed/runs/`。`quote_correction_review.json` 的 applied=false 表示当时的修复前审查状态，实际授权与应用以 repair_freeze / repair_launch 及此提交为准。

新增模型请求和费用：初次 417 / $0.168099552；修复续跑额外 {costs['new_requests_after_repair']} / ${costs['new_cost_after_repair_usd']:.9f}；合计 {costs['unique_new_model_requests']} / ${costs['cost_usd']:.9f}。修复核验、同状态动作审计、全部回放和分析新增模型调用均为 0。

原版验证使用从冻结 Git 提交提取的严格匹配函数；续跑回放在不可修改前缀使用原函数、从切点起使用规范化函数。验证全部原生哈希、公开反馈、奖励、模型请求上下文、决策和最终记忆，不将后缀修复假装成全局从零已修复策略。
''')
    save('科研总结报告.md',f'''# Stage24：AGC 科研总结

本次数据支持 **mark 的目标锁定得到明显缓解，并转化为真实主线推进**；也暴露了新的格式拒绝和多动作循环问题。三游戏主线均值从 {b['main_mean']:.3f} 到 {a['main_mean']:.3f}，达到运行前登记的五项描述性门槛。但两个 AGC 运行因硬拒绝提前终止，且包含经用户授权的解析修复续跑，因此只报告“本次带修复续跑的 workflow 比较支持局部改进”，不声称原始冻结版稳定有效或方法普遍优于基线。

{main_table}
第一章 **1/3 → 1/3**，全主线 **0/3 → 0/3**；mark 提升，remnant 主线持平，metropolis 退步。首次未修复的 AGC 三局主线 0/8/4，第一章 0/3；初次负面结果没有排除。报告不把少执行的 256 步当作完成效率优势。

## RQ1：是否减少 controller-induced information suppression？

针对旧机制的证据是肯定的：mark 的 `enter hall` 不再滞留，原算法 214 次动作覆盖变为 0，wait 190/300 → 0/253，公开新状态 48 → 121，共同 stale 126 步 → 1 步。a32 获取任务提醒，后续制作、取物、区域解锁和战斗产生主线奖励。

但整体“信息压制已解决”的结论不成立。逐字证据硬检查在空白误差处中止初次两局；修复后 mark 又因真实信息的非逐字摘要中止。对有意义行动的控制限制从替换成 wait 转为拒绝执行的风险仍在。原生单动作反事实仅证明具体动作会怎样反馈，不证明继续放行能完成余下任务。新的 workflow 同时改变多部分输入与决策链，不能把本轮全部差异分配给某一个模块。

## RQ2：是否转化为任务完成提升？

mark 第一章从未完成变为 a118 完成，a147 获得第二章奖励，最终主线 11，属于实际推进。metropolis 从第一章完成/7 分退步为未完成/4 分，remnant 仍为 1 分；因此跨三游戏第一章完成率没有提升。mark 后半程拾币/丢币循环，metropolis 219 步材料收集目标、零成功制作说明消除旧锁定不足以保证数量执行、主线优先级和长期任务恢复。

官方脚本输出与原生 quest 状态共同核对；模型看到的 AGC 状态没有奖励或隐藏主线。详见 [结果表](三游戏结果表.md) 和 [轨迹](轨迹分析.md)。

## RQ3：是否来自通用 workflow 而非游戏规则？

代码审计支持“没有植入本次游戏物品/NPC/地图/任务攻略”。`agents/agc/` 只有通用公开文本解析、状态与有限失败记忆、单模型重考虑；没有 main_quest_progress、reward 或隐藏配方读取。环境/评分/离线分析读取隐藏状态只用于复现和评分，不进入模型上下文。固定六项契约测试与三游戏零 API 预检通过，冻结检查继续保护 4730 个项目文件和 278 个引擎源码文件，仅允许列明的解析修复/冻结校验器改动。

这证明实现未写游戏专用规则，不证明跨游戏泛化或各模块因果必要性。公共文本语法仍依赖该引擎的统一 observation 格式；模型自身先验与单次采样也没有被隔离。INVALID 分支三局零触发，语义目标达成大多依赖模型主动更换，不能说目标有效性判断已经完整验证。

## 研究判断

本轮最明确的问题有三类。第一，硬格式失败后的终止与证据引文契约过于脆弱，是可定位的工程/接口问题；空白误差已有授权修复，其他情况本阶段保留不改。第二，公开证据的来源正确不等于它支持当前目标或数量计划，metropolis 的可见材料列表能通过引文核验却不能证明配方相关性。第三，局部新状态与多动作交替掩盖长期无主线进展，mark/ metropol​is 两局都给出直接行为证据。后两类可作为目标相关进展、目标证据有效性和有界控制下恢复机制的后续研究问题，仍需要独立样本与机制消融。

当前 AGC 应作为诊断原型保留，尚不足以宣称通用可靠 Agent。先界定上述机制及验证指标，再决定是否开发下一阶段；本轮没有新算法迭代、游戏策略修补或新增种子。没有将 AGC 并入 Stage18，也没有改 Stage18 源码。

## 成本与可复现性

本阶段 {costs['unique_new_model_requests']} 次新增模型请求，usage 计价 ${costs['cost_usd']:.9f}；所有基线复用，离线回放/分析零模型调用。两条截断 JSON 与三条缺字段回复保留，未改输出上限。相同模型、300 动作上限、seed42、引擎和评分脚本，初始世界哈希与 Stage18 对照逐游戏一致。AGC 允许每动作最多一次额外重考虑，故按环境动作预算配对，不是按相同模型调用预算比较。

两条修复续跑有混合版本前缀，两个运行提前终止，每游戏只一次随机模型采样；不计算显著性，不声称普遍优势。第一章完成并非完整通关。完整原生回放与费用对账见 [completion](../../results/stage24/completion.json)、[verification](../../results/stage24/verification/)、[费用](../../results/stage24/cost_reconciliation.json)。提交与逐文件增删行数见 [publication](../../results/stage24/publication.json) 和 [change_ledger](../../results/stage24/change_ledger.json)。
'''.replace('metropol​is','metropolis'))
    save('README.md','''# Stage24 交付索引

完成独立 AGC 实现和三游戏唯一一次试验；仅两处用户授权的空白解析修复续跑，保留初次失败。最终主线 remnant/mark/metropolis = 1/11/4；两个硬拒绝提前终止。未运行新基线，未修改 Stage18。

- [科研总结报告](科研总结报告.md)：结论、RQ1–RQ3、限制。
- [AGC 算法设计与预登记](AGC算法设计.md)：冻结前协议。
- [三游戏结果表](三游戏结果表.md)：全部正负结果、诊断、费用。
- [轨迹分析](轨迹分析.md)：里程碑、长期循环、格式失败。
- [Stage18 失败模式对应](Stage18失败模式对应分析.md)。
- [授权修复与续跑](空白字符修复与续跑记录.md)：原版与混合版本来源。
- [代码](../../agents/agc/)、[运行和分析脚本](../../scar_stage24/)。
- [原始运行](../../results/stage24/runs/)、[续跑](../../results/stage24/resumed/runs/)、[日志](../../results/stage24/logs/)。
- [全部证据索引](../../results/stage24/evidence.jsonl.gz)、[逐动作指标](../../results/stage24/step_metrics/)。

离线复算：配置与 Stage22 相同的外部引擎及依赖（不上传下载包），设置 PYTHONHASHSEED=0、AGENTODYSSEY_ROOT 为引擎目录、PYTHONPATH 为项目和引擎目录。执行 `python -m scar_stage24.verify --game GAME --phase first_pass`；remnant/mark 再执行 `--phase resumed`。随后运行 `scar_stage24.analyze`、`scar_stage24.diagnose`、`scar_stage24.response_audit`、`scar_stage24.report`。这些模块禁止网络连接，不访问 API 密钥。`account` 额外依赖本机账本；公开的逐响应记录足以重算金额。`audit_quote` 与 `terminal_audit` 支持原生单动作审计。

不要将 `batch` 或 `repair --game` 当作离线复算命令，它们是付费运行入口。代码冻结与预检记录在 results/stage24；发布提交和文件增删行数见 publication.json / change_ledger.json。仅上传本项目实现、审计证据和结果，没有打包第三方引擎、模型权重、虚拟环境或密钥。
''')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(10.2,3.1),sharex=True)
    for ax,game in zip(axs,GAMES):
        for method,color in [('Stage18-Fixed','#777777'),('AGC','#136c9f')]:
            folder=final_folder(game) if method=='AGC' else source(game);rr=rows(folder/'trajectory.jsonl.gz')
            ax.step([0]+[r['step'] for r in rr],[0]+[r['scores']['quest'] for r in rr],where='post',color=color,label=method)
            if len(rr)<300:ax.plot(rr[-1]['step'],rr[-1]['scores']['quest'],'x',color=color,ms=8)
        ax.set(title=game,xlabel='Executed environment actions',xlim=(0,305));ax.grid(alpha=.2)
    axs[0].set_ylabel('Cumulative Main Quest Reward');axs[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Stage24: one seed per game; AGC includes two authorized continuations',fontsize=10)
    fig.tight_layout();dest=REPORTS/'figures';dest.mkdir(exist_ok=True)
    fig.savefig(dest/'main_quest.png',dpi=200);fig.savefig(dest/'main_quest.pdf');plt.close(fig)
    print('Reports and figures rebuilt; no model calls.')

if __name__=='__main__':main()
