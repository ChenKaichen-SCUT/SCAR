"""Evidence-based interpretation of this frozen exploratory cohort.

Retains negative cases and distinguishes behavior changes from mode labels. The
named trace review is explicitly specific to the published Stage7 cohort.
"""
import json
from pathlib import Path
from scar.io import atomic_json


def interpret():
    out=Path('results/stage7');reports=Path('reports/stage7')
    g=json.loads((out/'method_metrics.json').read_text())['all'];judgment=json.loads((out/'research_judgment.json').read_text())
    pairs={r['a']:r for r in json.loads((out/'paired_comparisons.json').read_text()) if r['b']=='C0'}
    cf=json.loads((out/'local_effect_summary.json').read_text())['counts']
    a,b,c,d,full=(g[m] for m in ['C1','C2','C3','C4','C5']);base=g['C0']
    statements={
        'retry_context_fix':{
            'verdict':'支持保留 A 的上下文资格修复；不等于所有新增成功均被严格因果确认。',
            'reason':f"C1 为 {a['successes']}/17，对照 {base['successes']}/17；新增 key_blank、master_keycard，未丢失 C0 成功。必要配方 {base['key_recipe_discovered']}→{a['key_recipe_discovered']}/68；旧试制资格耗尽后的候选机会 {base['expired_trial_missed_opportunities']}→{a['expired_trial_missed_opportunities']}。记录 {a['condition_released_successes']} 次条件解除后成功，其中 {a['trigger_counts'].get('A_forward_released_retry',0)} 次属于前向试制重试。成本仍从 ${base['cost_usd']:.3f} 增至 ${a['cost_usd']:.3f}，且存在有害候选覆盖；应把状态正确性和整局效益分开。"},
        'knowledge_gap_exploration':{
            'verdict':'B 的额外知识效率收益证据弱，当前实现还存在不可忽视的递归缺陷。',
            'reason':f"C2 只比 C0 多 1 例 brass_blank；关键规则 {base['key_recipe_discovered']}→{b['key_recipe_discovered']}/68，定向动作均为 {base['directed_information_actions']}，每条定向新规则动作 {base['directed_actions_per_directed_key_gain']:.2f}→{b['directed_actions_per_directed_key_gain']:.2f}，信息动作费用/新必要规则反而 ${base['information_cost_per_discovered_key']:.6f}→${b['information_cost_per_discovered_key']:.6f}。旧 7 例缺知识任务没有新增恢复。已提交状态的同提案局部审计没有发现 B 当步披露更多必要配方名；这不排除后续运输/生产价值，但不能认定搜索显著更高效。C5 中止检查点仅关闭 B 可消除递归，此版本不宜直接推广。"},
        'explore_execute_switch':{
            'verdict':'不支持当前 C 已可靠改善知识到执行；有明确的生产优先级错误。',
            'reason':f"C3 为 {c['successes']}/17，新增 bar_mail、brass_blank，同时丢失 bandage_roll。真正 ready-execution 触发仅 {c['trigger_counts'].get('C_ready_execution',0)} 次；brass_blank 的该触发为 0，其 37 个同状态单 C 开关比较也均不改变动作，不能将其成功当作该机制有效证据。中间未转化 {base['intermediate_conversion_censored']}/{base['intermediate_conversion_n']}→{c['intermediate_conversion_censored']}/{c['intermediate_conversion_n']}，包含截尾的描述延迟 {base['intermediate_conversion_lag_with_censor_mean']:.2f}→{c['intermediate_conversion_lag_with_censor_mean']:.2f}，不足以宣称显著改善。bandage_roll 第 8 索引已有 2 根落地绳，C 却再次制作并耗尽最后一份布。关闭 C 的同状态动作改为收取，配相同两步目标续动作可完成；这是局部反例，不是模型补跑。"},
        'resource_goal_guard':{
            'verdict':'D 的需求批量与最终收取有局部价值，但可见物合法性和即时完成候选保护仍不可靠。',
            'reason':f"C4 为 {d['successes']}/17，新增 bar_mail；其公开数量提示支持直接请求 3 根 rustbar，19 步完成。可避免保留材料损耗动作 {base['avoidable_reserve_depletion']}→{d['avoidable_reserve_depletion']}，基础候选当步可完成却被覆盖 {base['harmful_goal_overrides']}→{d['harmful_goal_overrides']}。但合法候选替成拒绝动作 {base['legal_to_rejected']}→{d['legal_to_rejected']}，资源循环 {base['resource_cycles']}→{d['resource_cycles']}。全量局部开关中 D 使单步目标更好 {cf['resource_goal_guard'].get('enabled_goal_better',0)} 次、更差 {cf['resource_goal_guard'].get('enabled_goal_worse',0)} 次；key_blank 需要两份时，它用拾取一份覆盖了能取得两份的转存。另会在幻影物品上重复拾取，不能将可见直接当作已证实可取得。"},
        'combination':{
            'verdict':'组合总分有额外收益迹象，但当前 C5 尚不可靠；优先修复已确认的简单机制缺陷，不支持升级复杂在线学习器。',
            'reason':f"C5 {full['successes']}/17，高于最高单项 {max(g[m]['successes'] for m in ['C1','C2','C3','C4'])}/17；相对 C0 新增 4 例、丢失 1 例。成对差 17.6 个百分点，家族 bootstrap 95% 区间为 [{pairs['C5']['family']['ci95'][0]*100:.1f}, {pairs['C5']['family']['ci95'][1]*100:.1f}]，不能排除零差异。旧共同失败 11 例只新增 key_blank、bar_mail 两例恢复。组合仍有 bandage_roll 退化、{full['avoidable_reserve_depletion']} 次可避免保留材料损耗、spire_pike 递归中止及幻影拾取循环。轨迹显示 A 重试、B 连接探索、C 执行与 D 收取可在成功链中相接，但局部单步证据不足以把总分差认定为确定协同。"}}
    for flag,statement in statements.items():judgment[flag].update(statement)
    judgment['interpretation_scope']='post-hoc analysis of original 70f01fa99cc2 cohort only; no policy changes, no paid reruns'
    atomic_json(out/'research_judgment.json',judgment)
    paras=['## 分模块最终判断','']
    for flag in statements:
        paras += [f"**{flag}：{statements[flag]['verdict']}**",'',statements[flag]['reason'],'']
    paras += ['以上不把带截尾均值解释为无截尾平均恢复时间，也不把同一轨迹多次局部反事实当作独立样本。A/B/C/D 的计数均保留零激活情形；详细负例见 [递归中止说明](递归中止说明.md) 及 [逐例机制归因](逐例机制归因.md)。','']
    p=reports/'实验报告.md';text=p.read_text();start=text.index('## 分模块判断') if '## 分模块判断' in text else text.index('## 分模块最终判断');end=text.index('## 完整性与复现',start)
    text=text[:start]+'\n'.join(paras)+'\n'+text[end:];p.write_text(text)
    notes={
        'sequence-d6341439ebbc42c8':'key_blank：C1 在索引 14 缺 furnace 试制失败，抵达后索引 17 再制 iron_bar，索引 19 检查发现目标配方，24 步收取完成。C5 在索引 4 失败、7 重试、9 检查、11 制作、12 拾取，13 步完成。这里记录了 A 的跨条件重试以及 B/C/D 后续动作链；不能把 13 对 24 步全部视为模块组合因果收益。',
        'sequence-0b1c0d36cbf3727b':'master_keycard：C1 的 iron_bar 索引 9 缺炉失败、14 试制成功、16 检查，30 步完成；C5 相应索引为 9/12/14，26 步完成。A 的有效试制资格没有因站点失败永久耗尽，是可核对的行为证据。此例并非旧 11 个所有方法共同失败之一。',
        'sequence-7f16db9519b84e2d':'bar_mail：C4 在索引 14 按公开目标数量制作 3 根 rustbar，17 制作目标、18 拾取。C3 在索引 14 制作 2 根，16 又制并被引擎截为 1 根，恰好凑足 3 根；这种“先再制后收取”的优先级在此有利，在 bandage_roll 却造成失败。不能把该个例直接泛化为 C 的稳定计划优势。C5 在索引 15 制作 3 根、18 制作目标、19 收取。',
        'sequence-6403512cf4de780d':'brass_blank：C2 在 40 步边界恢复，C3 为 37 步且 C_ready_execution 触发为 0。C5 在索引 4 缺 kiln 失败、8 制 rustbar、10 检查得到目标规则，但索引 12–29 连续拾取显示为 brass_blank 的盐雾幻影，均被原引擎拒绝；公开失败反馈没有阻止 D 再次覆盖合法制作提案。幻影消失后索引 30 真正制作、31 拾取才完成。这是成功轨迹中仍须保留的严重机制负例。',
        'sequence-48401b39ba565b57':'bandage_roll：C0/C1 13 步成功，C3/C5 均失败。共同前缀到索引 6 已制作 2 根 sinew_cord，索引 7 检查后剩余 1 布。索引 8，C3 再制 2 根，C5 在 D 缩量后仍再制 1 根，都消耗最后一份布；已落地的 2 根本可直接收取。相同检查点仅关闭 C，动作变成 store 2 sinew_cord inventory；追加相同的 craft1/pickup 目标两步，关闭 C 分支成功，原分支失败。完整原闭环失败保留，局部分支不计正式成功。',
        'sequence-8d8d1a4fc7768d57':'spire_pike：C5 索引 1–7 的最终目标优先先遭遇幻影拒绝，之后第 26 个已提交动作后发生工作台查询与探索递归。原已付费基础提案为 pick up orrery_blade，控制器未返回动作。两次零 API 重现；单独关闭 B 才解除此局部递归。原 failed 状态不变，评测作为方法中止计入失败；未增加第 27 步或修复后补跑。',
        'sequence-7e32e0ff916aaa50':'orrery_blade：所有六配置失败。旧状态反事实证明一份 astrolabe_core 可保留后续材料，但不代表新闭环必然恢复。C5 虽在索引 33 只制 1 个 core，之前已经分别多次制作和运输 rustbar / brine_glass，末段又受手部容量和取放影响；索引 39 仍在尝试搬运原料。40 步执行预算和调度仍未解决，不能把数量回归通过当成整局成功。'}
    dpath=reports/'逐例机制归因.md';detail=dpath.read_text()
    for cid,note in notes.items():
        anchor=f'Family：`{cid}`。';pos=detail.index(anchor);end=detail.index('\n\n',pos)
        detail=detail[:end]+f'\n\n**机制复核**：{note}'+detail[end:]
    dpath.write_text(detail)

if __name__=='__main__':interpret()
