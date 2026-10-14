"""Generate Stage25 reports from the effective three-run scope."""
from .common import *


def table(headers,records):
    def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(cell(x) for x in r)+' |' for r in records])
def pct(x):return '—' if x is None else f'{100*x:.1f}%'
def md(name,text):(REPORTS/name).write_text(text.strip()+'\n')


def main():
    offline();check_freeze()
    mm=read(RESULTS/'metrics.json');cost=read(RESULTS/'cost_reconciliation.json');dd=read(RESULTS/'diagnostics.json');con=read(RESULTS/'conclusion.json')
    r={(x['game'],x['method']):x for x in mm};diag={x['game']:x for x in dd};v={g:r[g,'AGC-v2'] for g in GAMES}
    formal=cost['groups']['formal'];cancel=cost['groups']['user_cancelled']
    scoretable=table(['游戏','Stage18 主/辅','Stage24 主/辅','Stage25 主/辅','Stage25 动作','第一章完成动作'],[
        [g,f"{r[g,'Stage18-Fixed']['main']}/{r[g,'Stage18-Fixed']['supplementary']}",f"{r[g,'AGC']['main']}/{r[g,'AGC']['supplementary']}",f"{v[g]['main']}/{v[g]['supplementary']}",v[g]['actual_actions'],v[g]['first_chapter_step'] or '未完成'] for g in GAMES])
    costs=table(['游戏','请求','输入 token','输出 token','最高单次输入 token','计价费用 USD'],[
        [g,v[g]['requests'],v[g]['input_tokens'],v[g]['output_tokens'],v[g]['max_input_tokens'],f"{v[g]['cost_usd']:.9f}"] for g in GAMES])
    md('科研总结报告.md',f'''
# Stage25 实验报告

结论：**{con['classification']}**。AGC-v2 缓解了本次样本中的提前中断，metropolis 恢复到主线 {v['metropolis']['main']}；但 mark 从 11 降至 {v['mark']['main']}，remnant 仍为 {v['remnant']['main']}。没有证据支持“两个机制已经解决三游戏的长期任务问题”。目前不建议直接进入 500 步正式评测。

{scoretable}

主/辅分别是官方 Main Quest Reward / Supplementary。三局均以 300 动作上限结束；mark、metropolis 完成第一章，三个游戏均未完成全主线。Stage18、Stage24 复用既有结果，无基线重跑。Stage24 remnant/mark 使用已获授权修复并续跑的最终结果；其原始首跑主线分别为 0/8，最终为 1/11，metropolis 始终为 4。

## 实际范围与冻结

按用户最新要求，正式实验仅 **remnant、mark、metropolis 各一次，全部 seed42**，三局初始物理状态与两版基线精确匹配。九局原协议保留为历史；六个 seed43/44 局在收到范围更正后取消，不算失败，不纳入性能统计。取消原因与分数无关。[范围修订](用户缩减实验范围.md) 是最终有效口径。

算法冻结提交 `c7a509c90bd87b0db520d3f56a3c209754d380b2`；范围修订提交 `99a0bcf`。Stage18/Stage24 原代码和引擎未改。置信度阈值固定 0.4；0.2/0.4/0.6 仅对旧轨迹离线重算触发次数，没有为阈值额外采样模型，也没有依据本轮成绩改参。详细更新量、重试上限见[预登记](AGC-v2设计与预登记.md)。

新增版本独立于旧 AGC。保留基础提示、STM5、公开反馈和模型配置；增加通用置信度摘要与动作重试。引文不匹配按用户批准降为置信度信号。语法失败最多额外 3 次请求，目标重评估最多额外 1 次；每次执行动作仍由 LLM 提出，三局控制器自动替代动作均为 0。

## 三个研究问题

**RQ1：未完全保持 mark 的 Stage24 收益。** 主线 11→10，第一章完成从 a118 延后至 a162；相对 Stage18 的 0 仍有恢复，但不能说与 v1 持平或更好。a82 丢下已写 kindness 的 paper_0；a163 公开指令再次要求持有该纸条，a164–176 却先进入交易和硬币收取循环，之后又搜索可写物品。公开知识、库存约束和长期任务物品保留仍未结合成稳定执行。两条不同模型轨迹的分叉不是模块的严格因果效应。

**RQ2：观察到 metropolis 得分恢复，没有观察到更少 reset。** 主线 4→{v['metropolis']['main']}，a24 完成第一章，a34 获取 witness_marron 的主线增量。目标替换由 {r['metropolis','AGC']['counters']['goal_resets']} 增至 {v['metropolis']['counters']['goal_resets']}；后段仍有材料/容量和移动循环。因此，不能用得分恢复证明“减少过度 reset”。Stage24 a82–300 连续持有同一目标的既有证据本就不支持把过度 reset 视作已确立主因。

**RQ3：本局动作可靠性有所改善，但未带来 remnant 主线改善。** 从 a91 后的语法拒绝终止变为运行到 300；a175 一次、a177 两次非法 `write quiet` 提案被过滤后，模型自行给出可执行动作。a177 的第二次重试在同一状态返回有效攻击，说明当前重试链可以恢复执行；不能据此证明另一条 Stage24 轨迹一定会恢复。remnant a39 后主线不再增加，后续受战斗、恢复和资源操作占据。

## 成本、核验与局限

{costs}

正式三局：{formal['requests']} 次请求、{formal['actions']} 个环境动作、计价 **${formal['cost_usd']:.9f}**。六局取消前已发生 {cancel['requests']} 次请求、{cancel['actions']} 个动作、**${cancel['cost_usd']:.9f}**。本阶段合计 **${cost['cost_usd']:.9f}**，取消费用没有藏入三局平均值。费用按返回 usage 和保存单价重算并与本地账本逐条对账；没有供应商账单，不能称为最终发票金额。

三局共 900 个动作和全部 {formal['requests']} 个成功模型响应上下文已做禁网精确回放：原生状态哈希、反馈、奖励、模型输入、仲裁结果和最终记忆全部一致；分析新增模型调用为 0。4889 个冻结项目文件、278 个引擎文件通过完整性核验。六次取消拦截发生在 API 发送之前，账本记录零费用，不是六次付费失败调用。

只有每游戏一次模型采样；环境 seed 并不锁定供应商的随机采样。没有显著性、稳定泛化或模块独立因果结论。两项修改与引文门槛变化同时存在；新版本拥有完整 300 步，而旧版两局提前终止，必须同时看奖励和实际动作。低 wait、原生 invalid=0、新状态多，都不代表完成任务。

完整结果见[三游戏结果对比](三游戏结果对比.md)、[置信度分析](置信度与目标重评估分析.md)、[动作与失败审计](动作可靠性与失败模式分析.md)、[下一步判断](500步评测建议.md)。发布提交、文件及行数见[Git 变更记录](Git变更记录.md)。
''')
    full=table(['游戏','方法','主线','辅助','实际动作','结束原因','第一章动作','wait','相邻重复率'],[
        [x['game'],x['method'],x['main'],x['supplementary'],x['actual_actions'],x['status'],x['first_chapter_step'] or '未完成',x['counters']['waits'],pct(x['repeated_action_ratio'])] for x in mm])
    progress=table(['游戏','方法','首次新状态','新状态数','新区域','字面子目标完成','无新信息8步窗口率','≥8步无主线区段占比'],[
        [x['game'],x['method'],x['first_new_state_step'],x['counters']['new_states'],x['counters']['new_areas'],x['counters'].get('status_COMPLETED',0) if x['method']!='Stage18-Fixed' else '—',pct(x['long_no_information_ratio']),pct(x['long_no_quest_ratio'])] for x in mm])
    allcost=table(['游戏','方法','请求','输入 token','输出 token','计价 USD'],[[x['game'],x['method'],x['requests'],x['input_tokens'],x['output_tokens'],f"{x['cost_usd']:.9f}"] for x in mm])
    cancelled=table(['取消局','已执行动作','已发出请求','计价 USD'],[[c['case'],c['actions'],c['requests'],f"{c['cost_usd']:.9f}"] for c in cost['cases'] if not c['formal']])
    md('三游戏结果对比.md',f'''
# 三游戏结果对比

正式样本仅 seed42，每游戏一次。旧版数据只读复用。主线/辅助由原引擎 `challenge_eval.py` 重新汇总，命令、脚本哈希及 JSON 见 `results/stage25/official_scoring_command.json` 和 `official_scores.json`。

{full}

`step_limit` 为300步用尽，`agent_decision_exhausted` 为模型提案未通过旧控制器的有限重试。所有全主线完成数均为0。Stage24两局提前停止不能把未执行步数算作失败动作，也不能与完整300步比较仅看次数不看分母。

{progress}

新状态、区域、信息均基于真实公开观察的相同解析器。新状态签名有界，不是隐藏完整世界状态的穷尽去重。子目标完成是字面动作/地点满足触发的 COMPLETED 次数，不等于官方子任务数；Stage18没有同构AGC字段，记为“—”。无信息率仅统计已满8步且公开 informative 总和为0的窗口结束点；≥8步无主线区段占比是另一指标，包含可能合理的准备工作，不直接称为浪费率。

{allcost}

上表旧版费用是历史参考，未计入本阶段新增费用。Stage24旧轨迹含其授权续跑前后所有已付费响应，故请求数可能高于动作数加最终轨迹的重评估数。正式三局的费用合计 ${formal['cost_usd']:.9f}。

## 取消费用独立披露

{cancelled}

这些局因用户缩减范围而取消，绝不进入成绩表或视为算法失败。合计 ${cancel['cost_usd']:.9f}；加正式三局，本阶段费用 ${cost['cost_usd']:.9f}。原批处理器的 `completion.json` 仍保留 `complete=false` 历史记录；`effective_completion.json` 按最终三局范围确认完成，未篡改原运行状态。

## 对比条件

同引擎提交 `{ENGINE_COMMIT}`、同初始物理状态哈希、相同seed42、模型参数、原生成功判定和300步动作上限。初始环境历史相同；各算法控制状态和提示摘要按版本不同，不能声称模型输入逐字相同。模型采样不可强制复现，保存响应可精确离线回放。旧Stage24 remnant/mark是获授权修复后的混合续跑轨迹，这一差异已明确保留。

可重算来源：`metrics.json`、`comparison.csv`、`request_index.csv`、`comparison_fairness.json`、`cost_reconciliation.json`。所有路径均相对于仓库的 `results/stage25/`。
''')
    goalrows=[]
    for x in mm:
        if x['method']=='Stage18-Fixed':continue
        c=x['counters'];windows=x['reset_windows']
        goalrows.append([x['game'],x['method'],f"{x['mean_goal_duration']:.2f}",c['goal_resets'],sum(y['main_success'] for y in windows),pct(x['reset_main_success_rate']),pct(x['reset_main_success_rate_uncensored']),c.get('confidence_review_calls_executed','—') if x['method']=='AGC-v2' else '—'])
    gt=table(['游戏','方法','平均同文本目标动作','替换次数','替换后有主线增量窗口','全部窗口成功率','排除右删失后','置信度重评估请求'],goalrows)
    lt=table(['游戏','低置信度后实际替换','其中有主线增量','右删失窗口','零动作窗口','最长同文本目标','共同 stale 代理动作'],[[g,diag[g]['low_confidence_resets'],diag[g]['low_confidence_resets_with_main_gain'],diag[g]['right_censored_reset_windows'],diag[g]['zero_action_reset_windows'],max(x['length'] for x in v[g]['goal_segments']),v[g]['counters']['stale_goal_steps']] for g in GAMES])
    md('置信度与目标重评估分析.md',f'''
# 置信度与目标重评估分析

![置信度和主线奖励](figures/confidence_and_reward.png)

图中置信度为执行动作后的数值；红色竖线为实际目标登记替换。PDF同名文件可导出。曲线原始数据逐步保存在 `step_metrics/*AGC-v2.jsonl.gz`，全部增减事件在原轨迹 `control_after.events`。

{gt}

目标平均长度按连续相同目标文本的实际动作数计算。替换包括模型主动换目标、完成后换目标及新公开指令，不等于错误 reset；同义改写也算文本改变。阈值触发重评估不强制清空、不提供新目标。每个环境决策至多一次额外目标重评估，其后允许模型保留合法提案，记录 soft release。

{lt}

替换后成功窗口定义：替换后到下一次替换前，最多20个实际动作，官方主线增量>0。公开反馈产生的替换从下一动作开始，执行前模型替换从当前动作开始；同一边界替换可能有零动作窗口，仍保留分母。最后不足20步的窗口标为右删失；下一次替换提前结束是预定义竞争结束条件。窗口计数是描述，不是reset因果效应。全部起止、旧/新目标、前后奖励、目标相关事件、字面完成次数见 `metrics.json` 的 `reset_windows`。

共同 stale 代理要求目标连续≥12步且共同公开停滞检测为真，只用于旧新版本一致测量；它不是在线reset规则，也不是完整根因标签。多动作循环、新敌人到来和反复改变目标可能绕过该代理，不能用低 stale 数证明长期规划已经解决。

## 机制证据和局限

metropolis 得分增加，但目标替换从12增至{v['metropolis']['counters']['goal_resets']}，不满足“得分恢复且reset下降”的联合条件。旧版a82–300同一材料目标持续219步；新版没有同样的219步文本锁，但a34后仍缺主线增量。恢复第一章与解决后续材料/任务链是两个不同问题。

remnant a245–250 是置信度代理失真的直接例子：目标为 `Recover health and stamina after defeating the goblin warrior`，a246后置信度0.76；a247/249攻击同时分别受到4/5 HP损失，置信度却升至0.84/1.00，因为新的战斗事件与目标共享词汇。它只能证明词汇相关新事件，不证明“恢复生命和体力”已推进。记录保留该负面例，不回调阈值。

mark a41–67 保持“制作并持有铜剑”的同文本目标27步，a67取得主线增量；这说明该轨迹存在跨多步的有效目标保持，但没有同状态模块消融，不能把收益归因于置信度。a81–99保持制作钥匙目标19步也最终取得主线增量，同时a82丢下后续所需纸条，显示局部目标推进与长期物品保持可以发生冲突。

未核验引文不会成为下一步可核验公开事实。无硬动作错误的未核验提案数分别为 remnant {v['remnant']['counters']['unverified_syntax_valid_proposals']}、mark {v['mark']['counters']['unverified_syntax_valid_proposals']}、metropolis {v['metropolis']['counters']['unverified_syntax_valid_proposals']}；具体引文、采纳动作及硬条件分开保存在 `diagnostics.json`。引用为真的事实也可能已过时，逐字匹配不能保证当前目标正确。

离线阈值敏感性结果见 `offline_threshold_audit.json`；它使用固定旧动作，没有新反馈分叉，不能据此预测0.2或0.6的得分。没有追加阈值实验。
''')
    actiontable=table(['游戏','方法','原生invalid','公开失败反馈','语法拒绝提案','缺action提案','动作重试请求','连续同动作失败对数','最长连续同动作失败','硬拒绝终止'],[[x['game'],x['method'],x['counters']['native_invalid'],x['counters']['public_failures'],x['rejection_reasons'].get('action_not_in_public_action_syntax',0),x['rejection_reasons'].get('missing_action',0),x['counters'].get('action_retry_calls_executed',0) if x['method']=='AGC-v2' else '—',x['counters']['consecutive_failed_pairs'],x['longest_consecutive_failed_actions'],x['status']=='agent_decision_exhausted'] for x in mm])
    anomalytable=table(['游戏','异常响应条目','length结束','JSON解析异常','请求总数'],[[g,len(v[g]['anomalies']),sum(q['raw_response']['choices'][0]['finish_reason']=='length' for q in rows(RESULTS/'runs'/case_id(g,42)/'requests.jsonl.gz')),sum(bool(q.get('parse_exception')) for q in rows(RESULTS/'runs'/case_id(g,42)/'requests.jsonl.gz')),v[g]['requests']] for g in GAMES])
    tailtable=table(['游戏','最后主线增量动作','后续无主线增量动作','结局'],[[g,diag[g]['last_main_progress_step'],diag[g]['tail_without_main_progress'],'300步耗尽'] for g in GAMES])
    md('动作可靠性与失败模式分析.md',f'''
# 动作可靠性与失败模式分析

{actiontable}

原生 `invalid` 是引擎 `step_invalid_action` 字段；公开失败反馈包括材料、位置、容量等语义失败，两者不能混用。旧v1也检查语法，因此它的原生invalid=0不代表没有非法模型提案。语法检查通过不等于动作在当前世界可执行。AGC-v2未读隐藏可执行性、任务图或配方来替换模型动作。

{anomalytable}

每条异常的游戏/步数/请求ordinal/request_id/finish_reason在 `metrics.json:anomalies`，与实际重试、执行和原反馈的对应在 `diagnostics.json:action_retry_decisions` 及 `evidence_index.jsonl.gz`。length与JSON错误可能重叠，不能简单相加。输出上限沿用768 tokens，没有为长推理特别扩容；基础LLM输出耗尽长度时可能只剩reasoning或残缺JSON，随后由冻结的通用动作重试流程处理，不更换模型、不修改响应。

## remnant：语法中断缓解，主线停滞未解决

旧v1在第92次决策两次提出 `write note on paper_7`，违反接口参数数量，执行动作停在91；不是两次环境拒绝。新版a175首案 `write quiet` 缺少写入对象，通用提示后模型改为defend；a177前两案相同非法write，第三案攻击goblin_warrior_15并造成10伤害。两处均无控制器自动生成动作。a177直接证明已保存的重试响应能在同一环境状态得到可执行提案；没有付费重跑或跨版本强行共享不同输入响应。

a39进入library获得唯一主线奖励。a40公开指引要求先武装，a42锁门、a46开门后黑暗、a48取火把，随后长期围绕战斗、生存和资源操作。主线不再增加，死亡与战斗统计保留在 `scores`。不能因a177避免停止就宣称它已解决任务规划。

## mark：保留首章能力，纸条和容量链仍失败

a77成功写kindness；a81尝试存paper_0时环境明确找不到small_pouch_0，a82将paper_0丢下。a163主线公开要求“Hold the note you've written kindness on”，a164进入目标区域、a165对话后，a166开始购买tear_of_forest但硬币不足。a167非法批量拾取提案被拒后，合法drop torch又导致黑暗；a170拾币，a171因手满拒绝，a173丢币，a176再次丢币却已不在手中。a275尝试在iron_ore上写kindness，语法合法但环境明确不可写。动作filter处理格式，并未处理长期物品保留、容器操作和真正的任务前置条件。

该链条是原始公开反馈的直接证据，不等同于纸条一旦丢失就不可恢复。新版没有复现旧v1因非逐字引文停止，但主线少1且首章慢44步，负面结果完整计入。

## metropolis：首章恢复，库存和制作链仍未推进

a24通过talk to alex_smith触发首章完成，a34对话witness_marron获得第8点主线。a50检查clerks_bench公开看到工作台描述；a60拾iron_bar被手容量拒绝；a80拾gavel_timber公开了相关配方，a100存writ_token，a150仍在拾材料，a200门锁拒绝。这些例子表明已经存在公开材料/工作台知识，却没有持续主线进展；不能将所有失败都归于规则未发现。

a245两次 `drop 1 wax_seal` 参数数目错误，中间还发生目标重评估，最终模型提出语法合法的 `equip wax_seal`，环境仍拒绝不可装备物品；a246同类语法重试后最终wait。它们直接说明“通过filter并继续运行”并不保证得到有用或可执行的动作。

{tailtable}

三个游戏尾段都很长。逐步失败反馈、目标变化、低置信度放行、最长目标与行动频次完整保存在 `diagnostics.json`；不删除无收益或负面动作。连续“完全相同、相同上下文、且失败”的过滤器无法自动识别pick/drop、移动往返、战斗与恢复交替等循环，这些循环不一定产生连续相同失败。

## 证据边界

三局共900个动作无控制器生成替代动作；硬拒绝会增加同一模型调用，软目标提示也会改变后续采样，故仍会影响轨迹。当前证据支持“有些格式/解析故障可以在冻结重试内恢复”，不支持“所有动作可靠性问题已解决”。没有同状态模块消融，不把不同随机轨迹的分叉解释为严格因果效应。

逐任务原始文件：`results/stage25/runs/<game>__s42__AGC-v2/trajectory.jsonl.gz` 和 `requests.jsonl.gz`；动作编号从1开始，恰对应轨迹JSONL行号。`case_evidence/<game>.json` 提供重点原始观察/反馈摘录，`evidence_index.jsonl.gz` 提供全900步与每次请求的可追溯索引。
''')
    md('500步评测建议.md',f'''
# 是否进入500步正式评测

**暂不建议直接进入。** 本轮判定为 `{con['classification']}`，不是完整workflow改善。三游戏虽无提前中断，但mark未达到v1主线11、remnant主线仍为1，三个游戏末段均存在长时间无主线增量。不能仅增加200步来掩盖这些问题，本轮没有运行500步或开发下一版本。

可以保留的工程价值是有限重试和证据置信度降级：本次三个样本均避免了接口/引文硬终止，原始失败响应及新增调用全部可核验。尚需研究的是如何区分目标相关信息与真实进展、怎样保留未来仍需的任务物品、如何让已公开规则转化为容量/数量/制作顺序，以及如何识别多动作循环。词汇相关性的置信度不是语义进度估计，reset计数也不是稳定性本身。

当前不把这几个现象都包装为新的论文机制。语法/解析重试属于普通工程可靠性；跨目标物品依赖、公开知识利用与语义进度识别可能具有独立研究价值，但要先有跨任务直接证据和清楚的可证伪假设。一次三游戏采样不足以确定普遍瓶颈，也不能隔离两个模块各自的贡献。

若后续另行立项，先固定当前失败证据与评价口径，再决定是否做独立采样或同状态消融；本阶段不自动追加模型调用、不修改冻结算法，也不重跑失败局。进入500步正式评测至少应有充分理由相信更长预算用于任务推进，而不是延长已经观察到的资源/战斗循环。
''')
    md('README.md','''
# Stage25：AGC-v2

正式范围：三个游戏各一次，seed42，300步；另六局按用户要求取消并单独记费。

- [科研总结报告](科研总结报告.md)
- [三游戏结果对比与费用](三游戏结果对比.md)
- [置信度和目标重评估](置信度与目标重评估分析.md)
- [动作可靠性及失败模式](动作可靠性与失败模式分析.md)
- [500步评测建议](500步评测建议.md)
- [最终范围修订](用户缩减实验范围.md)
- [原始冻结设计](AGC-v2设计与预登记.md)
- [Git变更和发布记录](Git变更记录.md)

实现：`agents/agc_v2/`。实验、禁网回放、统计与报告代码：`scar_stage25/`。原始轨迹/请求和可重算统计：`results/stage25/`。下载的引擎、虚拟环境、API密钥、SQLite运行账本不入Git；公开逐请求记录足以重算费用。

在已有依赖环境中，设置 `AGENTODYSSEY_ROOT` 和 `PYTHONPATH` 指向匹配引擎与本仓库，使用该虚拟环境Python执行：

```bash
python -m scar_stage25.verify --game remnant --seed 42
python -m scar_stage25.verify --game mark --seed 42
python -m scar_stage25.verify --game metropolis --seed 42
python -m scar_stage25.analyze
python -m scar_stage25.diagnose
python -m scar_stage25.report
```

这些分析入口禁用网络，不产生模型调用。`account`在保留原始本地SQLite账本的机器执行，以核对所有收费和六次零费用取消拦截；已发布 `cost_reconciliation.json`。图表需要matplotlib。冻结的原`batch`入口仍是九局历史协议，**不要调用它复现最终范围**；如日后明确授权新实验，应逐游戏显式指定seed42并使用独立输出目录，避免覆盖已有结果。
''')
    print(json.dumps(dict(reports=6,classification=con['classification'],new_model_calls=0)))


if __name__=='__main__':main()
