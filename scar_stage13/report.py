"""Generate complete Chinese diagnostic reports from reconciled native evidence."""
import collections
import gzip
import json
from pathlib import Path
from scar_stage13.analyze import load,brief,OUT,OLD
from scar_stage12.public import controller
from scar_v3.state import parse_action

ROOT=Path('reports/stage13')
NOTES={
'd12_b2926ff775c6769c':'S1 收集已检查废铁，而曾在 cellar 看到的未检查木板可用“移动→检查”两步披露 wood_strip。基础模型的 enter courtyard 不是相邻移动，不能把覆盖解释为压掉一个已验证有用的建议。这里支持未知入口遗漏，不支持基础模型更懂关联。',
'd12_1c4969f7d6f4b0fc':'S1 选择检查 crucible；公开铁粒配方已存在，同处制作铁粒再检查可以披露 iron_bar。需两步和 2 单位废铁；这支持短程制作探索没有被持续执行，不是未关联原材料入口的例子。',
'd12_8d93a9fe38ae0edb':'检查 hellcoal 没有新增必要配方。有效路线先进入 courtyard，再制作和检查 brimite_ingot，共三步。移动本身是合法准备，不能仅凭第一步没有知识就称该方向无用。',
'd12_0332450ff72f2d8b':'S1 检查 crucible，制作并检查 fiend_alloy 则披露 fiend_alloy_sheet，需要消耗两种各 2 单位材料。J3 在此选对方向，但其文字说随后检查 war_bench，实际共同执行器检查的是产物；不能把实际收益全部归功于解释中的计划。',
'd12_e2783165405ff34b':'有效三步路线与 S1 的第一步完全相同，都是 store 2 fiend_alloy inventory，之后才制作并检查 sheet。Stage12 对运输型单动作提案不自动续接，而 craft 意图可续接；这主要暴露短程评测的意图粒度差异，不能证明当下 S1 动作选错。',
'd12_3a1444e457139495':'基础模型已提出 inspect fiend_alloy_sheet，但 FIFO/S1 改为 inspect inventory；真实单步反事实显示原提案能披露目标配方。它是 17 例中唯一直接支持“控制流程覆盖了有用基础提案”的状态。资源盘点或连续制作可能解释优先级，但长期损益未测。',
'd12_17c5deb0c6ac6acf':'S1 收集 brimite_ore，遗漏 cellar 的未检查木板；后者两步披露 wood_strip。与另一刀坯 family 共享木材依赖结构，因此不能把这两例当作两个独立游戏的泛化证据。',
'd12_03a8396e3b50ad83':'检查 crucible 没有收益；公开 brimite_nugget 配方允许制作后检查，两步披露 brimite_ingot。木条方向另因准备超出四步进入独立窗口敏感性检查，不能混入本状态主指标。',
'd12_1e291e83c3ae6288':'工作台和材料条件足以支持实际制作 fiend_strip，再检查即可披露 rivet；S1 当前优先检查 crucible。基础模型直接制作目标失败，因而这不是“应直接相信基础模型”的证据。',
'd12_2b682b0f9a8b12f4':'已制作、尚未检查的 fiend_strip 就在可观察范围；S1 先检查 inventory，J3 的产物检查一动作披露 rivet。没有运输或制作瓶颈；A–F 的严格支持标签为空，保留为“新产物检查与资源盘点顺序”现象，不强行归入原材料遗漏。',
'd12_8694b7913dc729f7':'S1 收集布料准备已知试制链；cellar 中尚未检查的 scrap_iron 两步披露 iron_nugget。只能证明另一入口有价值；原布料方向在延长窗口也能披露必要知识，因此不存在简单的“当前链完全无用”结论。',
'd12_996d46f5a59bfdc4':'S1 检查 crucible；铁粒和绳索两个公开试制方向均能两步披露必要知识。J3 选绳索，获得 chain_net 配方。多条有用方向并存，不需要事先猜中唯一隐藏路径。',
'd12_eaae67b21b57e5d9':'两步制作并检查 sinew_cord 有效；另一铁条路线先做与 S1 相同的 store 2 iron_nugget inventory，再制作和检查才有效。至少存在可切换方向，但不能把收集本身当作非法或无价值动作。',
'd12_01c83c35e4b3f13b':'当场检查尚未关联的 scrap_iron 一步就能披露 iron_nugget，S1 却检查已探索的 hellcoal。这里是明确的入口覆盖遗漏；无需额外制作、移动或资源消耗。',
'd12_7a79977e9ab99d44':'唯一主窗口有效方向以 S1 相同的收集铁粒动作开头，再制作铁条、检查产物。它支持多步意图应单独评测，也显示把“单动作提案”与“完整短计划”放在同一机会表中会制造表面的首选遗漏。',
'd12_2964f51279aa9f71':'Stage12 把 pick up iron_bar 记为无新配方，而 inspect iron_bar 记为发现 hellfire_bomb。但收取原始反馈已列出带数量的同一目标配方；旧 ResourceTable 仅识别 made of 格式。扩大公开文本识别后，两者都披露同一新必要关系。C2/C3 的唯一分数增益不能视为真正新增信息。',
'd12_5053683c26d2e1de':'S1 检查 crucible，制作并检查铁粒两步披露 iron_bar；J3 在此有效。基础模型取出废铁的提案未带来必要新知识。检查/制作的顺序值得理解，但严格未尝试且停滞的 L 选择条件没有选中本例。'}


def js(x):return '```json\n'+json.dumps(x,ensure_ascii=False,indent=2)+'\n```\n'
def esc(x):return str(x).replace('|','\\|').replace('\n','<br>')
def table(headers,rows):return '\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('|'+'|'.join(esc(v) for v in r)+'|\n' for r in rows)+'\n'
def link(sid):return f'[{sid}](states/{sid}.md)'
def actions(b):return ' → '.join(b['actions_trace']) or '无动作'
def nums(v):return json.dumps(v,ensure_ascii=False)
def write(name,text): (ROOT/name).write_text(text)


def main():
    ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'states').mkdir(exist_ok=True)
    states=load(OLD/'states.json');native={r['state_id']:r['branches'] for r in map(json.loads,gzip.open(OLD/'native_branches.jsonl.gz','rt'))}
    inputs={r['state_id']:r['public'] for r in load(OUT/'public_inputs.json')}
    decisions={r['state_id']:r for r in load(OUT/'decisions.json')};misses=load(OUT/'misses.json');ms={r['state_id']:r for r in misses}
    llm=load(OUT/'llm_pairs.json');ls={r['state_id']:r for r in llm};summary=load(OUT/'method_metrics.json');attr=load(OUT/'attribution_summary.json')
    lsum=load(OUT/'llm_summary.json');sensitivity=load(OUT/'sensitivity.json');pairs=load(OUT/'changed_pairs.json');verdict=load(OUT/'research_judgment.json')
    textaudit=load(OUT/'public_text_novelty_audit.json');texts={r['state_id']:r for r in textaudit['rows']}
    supplements=list(map(json.loads,gzip.open(OUT/'native_supplements.jsonl.gz','rt')))
    assert set(NOTES)==set(ms)
    evidence={'stage12_primary':'冻结原指标：ResourceTable 新登记且属于原生必要依赖的配方；四动作上限。',
        'stage13_rules':'先冻结公开规则与 50 个选择，再读取原生分支评分；不按分数改阈值。',
        'posthoc':'A–F 归因、公开文本解析审计和 6/8 步敏感性都是事后诊断，不能替换主指标。'}
    for s in states:
        sid=s['state_id'];d=decisions[sid];l=ls[sid];pub=inputs[sid];ctrl=controller(s['public_controller'],s['observation'])
        names=set(ctrl.visible())|set(ctrl.table.recipes)|{n for r in ctrl.table.recipes.values() for n in r.get('ingredients',[])}
        quantities={n:ctrl.ownership(n) for n in sorted(names)}
        body=f"# 冻结状态 {sid}\n\n目标：`{s['public_view']['target_action']}`。来源 Stage {s['source_stage']} / {s['source_method']} / `{s['source_task']}`，零基行号 {s['source_index']}，剩余 {s['remaining_actions']} 动作。\n\n"
        body+='[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。\n\n'
        if sid in ms:body+='## 遗漏解释\n\n'+NOTES[sid]+'\n\n'+js(ms[sid]['tags'])
        body+='## 决策时公开证据\n\n'+js(s['public_view'])+'\n公开持有量下界与是否精确（地面数量另见 current.ground；UNKNOWN 不补成 0）：\n\n'+js(quantities)
        body+='\n原始观察：\n\n```text\n'+s['observation']['text']+'\n```\n'
        body+='\n已知地点可见或历史观察到、尚未检查的对象（历史存在需重确认）：\n\n'+js(sorted((set(ctrl.visible()) | {n for place in ctrl.table.places.values() for n,amount in place['objects'].items() if amount>0})-set(ctrl.table.inspected)))
        body+='\n基础提案、FIFO 和实际 S1 选择：\n\n'+js({'base_proposal':s['frozen_base_proposal'],'FIFO':s['rule_decisions']['J0']['stage10']['frozen_F0_candidate'],'actual_S1':s['rule_actions']['J0'],'reason':s['rule_decisions']['J0']['reason'],'mechanisms':s['rule_decisions']['J0'].get('mechanisms',{}),'queue':s['rule_decisions']['J0'].get('queue'),'graph':s['rule_decisions']['J0'].get('graph')})
        body+='\n公开特征、覆盖选择、分层入口账本：\n\n'+js(d)
        body+='\n## 历史进展依据\n\n仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。\n\n'
        body+=table(['行号','执行动作','公开新配方','持有量增加/制作/新地点','进展','未关联入口检查'],[[h['index'],h['action'],','.join(h['new_recipes']),f"{h['public_acquisition']}/{h['public_production']}/{h['new_place']}",h['progress'],h['unconnected_inspection']] for h in pub['history']])
        body+='## 完整候选及公开依据\n\n'+js(s['candidates'])
        body+='\n## J0 与 J3 配对及去重排名\n\n'+js(l)
        body+='\n## 主窗口全部原生分支\n\n含原菜单及 Stage12 的自由提案补充分支；没有删除失败。new_key_recipes 是截至该步的累计新增集合，不能跨步相加。goal 仅为本短分支末局部持有目标，绝不表示本轮完成正式长程闭环。\n\n'
        for cid,b in native[sid].items():
            body+=f"### {cid}\n\n"+js(brief(s,b))
            for r in b['trace']:
                body+=f"\n第 {r['index']+1} 步：`{r['action']}`；拒绝={r['rejected']}；累计必要配方={nums(r['new_key_recipes'])}；消耗={nums(r['action_consumption'])}；环境损失={nums(r['environment_key_loss'])}。\n\n```text\n{r['feedback']}\n```\n"
        extra=[r for r in supplements if r['state_id']==sid]
        if extra:
            body+='\n## 本轮零 API 补充\n\n[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。\n\n'
            for r in extra:
                body+=f"### {r['kind']} / {r['candidate']['id']}\n\n"+js(brief(s,r['branch']))
        body+='\n## 公开文本新颖性独立审计\n\n将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。\n\n'+js({'initial_public_text_necessary_recipes':texts[sid]['initial_public_text_necessary_recipes'],'selected':texts[sid]['selected']})
        write(Path('states')/(sid+'.md'),body)
    a='# S1 遗漏原因分析\n\n本报告逐一保留 Stage12 定义的全部 17 个遗漏；另外 33 个状态也都有逐状态证据页。27 个状态存在四步内有效候选，S1 命中 10 个。\n\n'
    a+='**结论：遗漏是混合机制，不能统一归因为缺乏语义相关性判断。** 4 例有未关联入口的有效反事实；13 例最短有效候选也需要多动作。后者中 3 例有效路线与 S1 第一步完全相同，反映单动作与多步意图的评测粒度差异。仅 1 例直接证实基础模型有效提案被覆盖。另有 1 例属于公开配方文本格式未被解析，不能算真实信息遗漏。\n\n'
    a+='## 证据层级与类型统计\n\nA–F 可重叠，数字不能相加为 17。A/B/C/F 的“支持”指真实替代路线存在或其成本可见，不等于这些因素单独导致完整任务失败。E 是公开轨迹代理；名称联想、长期收益和全局最优顺序均未证实。\n\n'
    definitions={'A':'未关联入口有必要知识收益（原材料/未识别中间物公开代理）','B':'存在多步有效链','C':'有效链有移动、收集准备或拒绝','D':'原基础提案有效且被 S1 覆盖','E':'最近三步同一公开配方连通分量且无公开必要知识增长','F':'有效链至少三动作或实际耗材/损失'}
    a+=table(['类型','定义','支持状态数'],[[k,definitions[k],attr['tags'][k]] for k in definitions])
    a+=f"最短有效窗口分布：{nums(attr['minimum_useful_actions'])}。13 例至少需一个准备动作；材料成本并不等于稀缺资源的净浪费。17 例中 {attr['overrides']} 例改了基础提案，但只有 D 的 1 例验证了被覆盖方向更有知识收益。\n\n"
    a+=table(['状态','family / 来源行','S1 动作','最短有效动作数','标签','解释'],[[link(r['state_id']),f"{r['family']} / {r['source_method']}:{r['source_index']}",r['S1_action'],r['minimum_useful_actions'],''.join(k for k,v in r['tags'].items() if v['supported']) or '严格 A–F 无支持',NOTES[r['state_id']]] for r in misses])
    a+='## 全部 17 例的反事实路径\n\n下表中的所有有效候选均保留。重复候选 ID 不代表独立实验机会；按意图去重的审计另见 LLM 报告。资源消耗列为原生动作实际消耗，目标相关性只是评测层信息。\n\n'
    for r in misses:
        a+=f"### {r['state_id']} / {r['family']}\n\n"+NOTES[r['state_id']]+'\n\n'
        a+=f"公开目标、依赖图、知识缺口、已检查列表、材料/手位/容器/工作台/地点、全部候选依据和逐动作反馈见 {link(r['state_id'])}。剩余 {r['remaining_actions']} 动作；基础提案 `{r['base_proposal']}`；FIFO `{r['fifo_candidate']}`；S1 `{r['S1_action']}`。\n\n"
        a+=table(['候选','真实动作','新必要配方','准备步数','消耗','环境损失'],[[b['candidate_id'],actions(b),','.join(b['new_key_recipes']),b['preparation_actions_until_first_necessary_recipe'],nums(b['consumption']),nums(b['environment_loss_quantities'])] for b in r['useful_candidates']])
    a+='## 分 family 与公开条件\n\n'+table(['family','遗漏数','A/B/C/D/E/F'],[[f,x['misses'],'/'.join(str(x['tags'][k]) for k in 'ABCDEF')] for f,x in attr['by_family'].items()])
    a+='全部公开条件频数：\n\n'+js(attr['by_public_conditions'])
    a+='\n## 四步窗口以外\n\n'
    a+=f"预先选定全部 {sensitivity['branches']} 个 action_limit 分支，涉及 {sensitivity['states']} 个状态，延长至最多八步（仍受剩余预算限制）。前四步逐字段一致。六步新增 {sensitivity['newly_useful_at6_branches']} 个有效分支，八步新增 {sensitivity['newly_useful_at8_branches']} 个，分布于 {len(sensitivity['newly_useful_at8_states'])} 个状态；这是同方向窗口敏感性，不是覆盖策略成绩。\n\n"
    a+=table(['状态','八步内实际路径','新必要配方','首次发现准备步数'],[[link(r['state_id']),actions(r['at8']),','.join(r['at8']['new_key_recipes']),r['at8']['preparation_actions_until_first_necessary_recipe']] for r in sensitivity['rows'] if r['gain_at8']])
    a+='[全部成功与失败的延长窗口记录](../../results/stage13/sensitivity.json)。4 步无收益不能说明长期无用，尤其原有方向常包含材料收集、未知工作台拒绝、移动后重试与产物检查。\n\n'
    a+='## 归因边界\n\n不能从这些冻结分支确认 S1 在下一真实闭环动作一定不会继续制作或检查；三例相同首步尤其不能作这种推断。也不能把“公开必要配方长期不增长”当成真实停滞：在目标配方未知时，新发现中间配方可能暂时连不到目标。C1 的严格触发没有出现，说明这个公开代理在当前轨迹上过窄，不能事后放宽再重报独立验证。\n\n'
    a+='[机器可读完整归因](../../results/stage13/misses.json)、[统计](../../results/stage13/attribution_summary.json)、[公开文本审计](../../results/stage13/public_text_novelty_audit.json)。\n'
    write('S1遗漏原因分析.md',a)
    b='# LLM 互补性分析\n\n**当前没有证据支持在 S1 上增加 LLM 语义探索决策。** J3 的原始四步指标仍为新增 4、丢失 8、净 −4；4 个正例分布于 4 个 family，但合并同 family 的负例后只有 1 个 family 净正。预冻结的单一公开互补条件 L 未触发，结果等于 S1。这个结论针对本轮条件，不能证明所有可能的简单条件都不存在。\n\n'
    b+='## 全部 12 个差异状态\n\n'+table(['状态','family','正/负','S1 路径及必要配方','J3 路径及必要配方','不同 Top3 是否含有效','下位有效候选'],[[link(r['state_id']),r['family'],r['pair_class'],actions(r['J0'])+' / '+','.join(r['J0']['new_key_recipes']),actions(r['J3'])+' / '+','.join(r['J3']['new_key_recipes']),r['distinct_top3_useful'],','.join(r['effective_lower_rank_ids'])] for r in llm if r['pair_class'] in {'gain','loss'}])
    b+='四个正例中，scale、chain_net、hunter_gauntlets 是“公开配方制作→检查产物”；rivet 是检查已有新产物。它们可由普通短计划产生，不证明名称语义预测准确。scale 的解释还将后续信息源说成工作台，而实际收益来自产物检查。八个负例中六个优先访问工作台，两个重复检查最终目标；工作台确是公开执行前提，但不等价于未知配方的信息入口。\n\n'
    b+='## 去重后的返回排名\n\n按照检查目标合并 inspect/visit，按照制作并检查的产物合并不同批量的 craft 意图；运输原子动作单独保留。保留原排名第一次出现的代表，不从低于 Top3 的未返回候选补位，不挑别名中结果更好的分支。\n\n'
    b+=f"原返回 {lsum['returned_original_ids']} 个 ID，实际 {lsum['returned_distinct_directions']} 个不同方向；{lsum['states_with_rank_alias']} 个状态有重复排名意图，同意图别名的必要知识结果分歧为 {lsum['alias_groups_with_outcome_disagreement']}。去重 Top3 覆盖 {lsum['distinct_top3_effective_states']}/50（{lsum['distinct_top3_effective_states']}/27 有机会状态），Top2 覆盖 {lsum['distinct_top2_effective_states']}/50。首选无用但较低排名有效有 {lsum['top1_miss_with_lower_effective']} 例；另有 {lsum['opportunity_but_no_effective_direction_returned']} 例菜单存在机会却未返回有效方向。\n\n"
    b+=f"J0/J3 实际探索意图相同 {lsum['same_intent_states']}/50；J3 首选未关联入口带来知识为 {lsum['raw_entry_top1_effective']}，不同 Top3 中为 {lsum['raw_entry_top3_effective']}。不能把排名覆盖当成已经执行的收益，也不能无成本试遍 Top3。\n\n"
    b+='## 可观测互补条件\n\nL 只在 C2 的停滞/冷却触发成立、J3 提出从未尝试且未检查、有公开制作配方、估计成本有界的新方向时启用，并沿用 C3 的执行保护。方向成本来自公开路线和材料条件；实际原生动作数仅在诊断表中独立列出。四个正例都有此前关于所选物品的尝试记录，多数没有达到无进展门槛或处在入口冷却期，因此 L 没有调用它们。保持阈值冻结，不根据四个正例反推“更合适”的门槛。\n\n'
    b+='公开关系支持分为：已有配方/依赖、只有工作台前提、已有试制配方但下游连接未证实、仅对象/产物可见。自动统计的“同提及公开边”只作查阅索引，不是对推理正确性的语义证明。仅凭生成解释无法证明模型主要依赖名称联想；未披露的下游连接始终标为假设。\n\n'
    b+=table(['公开证据类型','状态数'],lsum['evidence_classes'].items())
    b+='**Oracle Upper Bound：14/50。** 它用事后标签在 J0/J3 中逐状态取优，保留 10 并增加 4；不可实现、未训练、未部署，不能作为融合算法的结果。\n\n'
    b+='## 其余 38 例与全部公开特征\n\n所有状态都保留在下表和独立证据页中。配方是否完整是当前公开表的保守判断；新知识间隔与原生必要关系不同。字段来源和全量值见 [50 行配对数据](../../results/stage13/llm_pairs.json)、[按配对类别的公开条件分布](../../results/stage13/llm_summary.json)。\n\n'
    b+=table(['状态','类别','同方向','公开无进展步数','独立入口数','新产物','J3 先前尝试','重复检查/工作台','公开配方支持','估计 J0/J3 步数','实际 J0/J3 步数'],[[link(r['state_id']),r['pair_class'],r['same_exploration_intent'],r['public_features']['no_public_progress_streak'],r['public_features']['uninspected_independent_entry_intents'],r['public_features']['fresh_uninspected_product'],r['public_features']['j3_previously_attempted'],r['public_features']['j3_repeat_inspection_or_station'],r['public_features']['j3_public_recipe_support'],f"{r['public_features']['s1_estimated_actions']}/{r['public_features']['j3_estimated_actions']}",f"{r['J0']['actions']}/{r['J3']['actions']}"] for r in llm])
    b+='## 成本与执行负面结果\n\n'+table(['方法','必要知识状态','总动作','拒绝动作','无新公开配方重复检查','无产出制作','环境损失状态','已知执行延迟状态','可完成目标动作被改写且窗口未完成'],[[m]+[summary[m][k] for k in ['useful','actions','rejections','repeated_inspect_without_new_public_recipe','craft_without_output_or_new_recipe','environment_key_loss','known_necessary_execution_delayed','harmful_goal_override']] for m in ['C0','J3','L']])
    b+='最后一列只是短窗口内错失即时执行的诊断，不是完整任务失败。J3 替换一次可实际制作的最终 bandage_roll 动作为库存检查后，四步窗口没完成；完整原生反馈见该状态页。纯覆盖 C2/C3 仅恢复了 J3 未恢复的铁条检查状态，而且该增益由解析格式差异解释；两种方案都未达到采用门槛。\n\n扩大公开文本识别后，J0 为 11、J3 仍为 6，J3 变为新增 4、丢失 9；这是补充敏感性，原 4/8 主结果保留。\n'
    write('LLM互补性分析.md',b)
    c='# 探索覆盖机制实验\n\n**结论 NO-GO。** 固定 C2/C3 在冻结旧指标上由 10 提高到 11，保留原 10，收益仅一个 family；独立公开文本审计发现唯一新增其实是旧解析器漏登记收取反馈中的配方。没有跨 family 的真实新信息净收益证据，不继续调阈值或堆叠排序。\n\n'
    c+='## 冻结方法\n\n原始 50 状态、315 个菜单候选、同一基础模型提案。C0–C3 所有选择都命中 Stage12 既有候选，直接复用已双重回放且本地复现的原生分支。补充分支仅服务归因与窗口敏感性。冻结时间、输入哈希、代码哈希及选择见 [freeze](../../results/stage13/freeze.json)、[协议](../../results/stage13/protocol.json)、[完整选择](../../results/stage13/decisions.json)。没有重新跑对比方法的付费轨迹。\n\n'
    protocol=load(OUT/'protocol.json')
    for m in ['C0','C1','C2','C3','L']:c+=f"- **{m}**：{protocol[m]}。\n"
    c+='\n所有门槛只使用公开记录：3 步窗口；4 动作入口冷却；一次最多 4 动作，保留 2 动作预算。路线成本是公开估计，不保证成功或不超时；原生四步上限才是真正硬限制。入口分开记录已检查且无信息、已检查且有信息、初始化已检查但本轮前缀不详、已制作未检查、曾阻塞、未关联入口、公开必要节点，可同时具有多种状态。每个候选保留上次尝试行号和真实反馈。\n\n'
    c+='C1 的“同分支”用公开配方的无向连通分量表示，且要求三步目标都在同一分量。这里没有符合全部条件的状态，所以 C1 与 S1 完全相同。C2 的进展包括新公开配方、真实持有量增加、成功制作和首次进入地点；不会因一次移动/收集就触发。既有地点移动仍计入无进展窗口，这是固定代理的局限。C3 复用 S1 的 base_progress；数量 UNKNOWN 仍可能被保护，不能称保护动作已获原生合法保证。\n\n'
    c+='## 完整主指标\n\n'+table(['方法','有效/27机会','恢复17中','丢失原10','净变化','正净 family','动作','新必要配方数','动作/配方','未关联入口有效/10机会'],[[m,f"{summary[m]['useful']}/27",len(summary[m]['gains']),len(summary[m]['losses']),summary[m]['net'],summary[m]['positive_net_families'],summary[m]['actions'],summary[m]['native_new_necessary_rule_count'],round(summary[m]['actions_per_necessary_recipe'],3),f"{summary[m]['raw_entry_useful']}/10"] for m in ['C0','C1','C2','C3','L']])
    c+=table(['方法','改选状态','拒绝动作','无效重复检查','无产出制作','环境损失状态','无关关键耗材状态','已知必要执行动作','已知执行延迟','目标执行覆盖'],[[m]+[summary[m][k] for k in ['changed','rejections','repeated_inspect_without_new_public_recipe','craft_without_output_or_new_recipe','environment_key_loss','unrelated_key_input_consumption','known_necessary_execution_actions','known_necessary_execution_delayed','harmful_goal_override']] for m in ['C0','C1','C2','C3','L']])
    c+='\n未关联入口仅为公开代理；本轮没有新增这类入口收益。每个方法的总动作都是 50，是冻结分支之和；不是 50 个独立任务，也不是 40 步闭环成本。已知必要执行按选择前公开图定义，图尚不完整时可能漏记实际必要材料。\n\n'
    c+=table(['family','C0','C1','C2','C3','L','J3'],[[f]+[summary[m]['by_family'][f]['useful'] for m in ['C0','C1','C2','C3','L','J3']] for f in summary['C0']['by_family']])
    c+='## 所有改选状态：含零收益\n\n'
    for p in pairs:
        c+=f"### {p['method']} / {p['state_id']}\n\n{link(p['state_id'])}。原路线 `{actions(p['original'])}` → 新路线 `{actions(p['alternative'])}`。必要配方净变化 {p['delta_necessary_rules']}，动作增加 {p['alternative']['additional_actions_vs_C0']}。\n\n"
        c+=js({'trigger_features':p['features'],'original':p['original'],'alternative':p['alternative']})
    c+='\nC2 在 fiend_helm 晚期把一次被原生拒绝的制作换成检查 charcoal_stylus：少一次拒绝，但没有必要知识，也没有完成任务。C3 因最终目标保护保留了原制作，说明执行保护也会保留 UNKNOWN 条件下的失败动作。\n\n'
    c+='C2/C3 在 hellfire_bomb 将收取铁条换成检查铁条，旧登记指标多一条必要配方；然而收取反馈已逐项给出目标配方，包括 0.5 iron_bar。信息内容与检查同源，只是格式不同。没有继续修改解析器/策略去追求本批状态更高分数。\n\n'
    c+='## 公开文本格式敏感性\n\n'+table(['方法','旧登记指标有效','两种公开配方格式均识别后有效','相对 C0 真正新增/丢失'],[[m,summary[m]['useful'],textaudit['summary'][m]['useful'],f"{len(textaudit['summary'][m]['gains_vs_C0'])}/{len(textaudit['summary'][m]['losses_vs_C0'])}"] for m in ['C0','C1','C2','C3','L','J3']])
    c+='[完整公开文本审计](../../results/stage13/public_text_novelty_audit.json) 同时检查决策前初始化/历史/当前公开文本，避免把已经披露的信息重复算新。此诊断没有更改冻结分数。\n\n'
    c+='## 决策与限制\n\n预冻结门槛要求净增至少 2、至少 2 个 family 净正、最多丢失原有效 1 个，资源/目标执行风险有界。所有方案未通过；即使不采用这组门槛，唯一分数增益也不能证明新信息收益。结论限定于这些具体固定规则，不能证明所有覆盖机制必然无效。50 个状态已经多轮分析，不能称独立验证；没有完整闭环成功率，本轮没有新成功任务分数。\n\n'+js(verdict['gates'])
    write('探索覆盖机制实验.md',c)
    d='# Stage 13 实验总报告\n\n**整体判断：NO-GO，保留 S1 参考，不把本轮覆盖或 LLM 融合纳入主算法，不继续在这批状态上堆叠优先级。**\n\n'
    d+='本轮从 `9a3bac2f49e4b8bd786ba61b2cefe9d005c5fb7b` 出发，只用原 10 个 robot_kingdom family 的 50 个冻结状态。复用 Stage12 的 315 个菜单候选、363 个原生分支与全部模型判断；新增模型 API **0**、新增费用 **0 美元**、新增付费闭环 **0**。累计模型费用保持 **36.888925758 美元**。\n\n'
    d+='## 三个问题的回答\n\n'
    d+='1. **S1 为什么漏掉 17 例？** 4 例有未关联入口的有效替代；13 例最短有效方向需 2–3 步，不能把多步收益都解释为首动作选错，其中 3 例实际有效路线与 S1 首动作相同。只有 1 例实证基础模型有用提案被 FIFO 覆盖。另有新产物检查与库存盘点的顺序差异，以及 1 例配方文本解析遗漏。相关性、覆盖、执行连续性和记录粒度混在一起，单一归因不成立。\n\n'
    d+='2. **LLM 有无可提前利用的互补价值？** J3 新增 4、丢失 8，去重后的 Top3 覆盖 15/27，但这不是免费可执行的收益。唯一预冻结公开互补条件 L 没有触发，不能稳定识别这 4 个正例。Oracle Upper Bound 为 14/50，仅是事后理论上界。当前没有证据支持增加 LLM 语义探索决策，也不能证明所有其他条件均不可能。\n\n'
    d+='3. **简单覆盖是否更可靠？** C1 没有触发；C2/C3 从 10/27 增至 11/27、保留原 10，表面收益仅 hellfire_bomb 一个 family。进一步核对原文发现，收取铁条已经用带数量格式披露配方，旧解析器没有登记；把两种公开配方格式都识别后，C0/C1/C2/C3 全部 11/27，新增信息净收益为 0。C2 另减少一次拒绝，却花一次动作检查了无必要信息的物品；没有跨 family 的可靠覆盖收益。\n\n'
    d+=table(['方法','旧主指标有效/50','新增/丢失','公开文本审计有效/50'],[[m,summary[m]['useful'],f"{len(summary[m]['gains'])}/{len(summary[m]['losses'])}",textaudit['summary'][m]['useful']] for m in ['C0','C1','C2','C3','L','J3']])
    d+='## 验证范围\n\n服务器新增 70 个原生分支：19 个未缓存的基础模型提案、51 个预选截断分支的八步敏感性。每分支执行两次，本地再独立执行两次，逐字段一致；每遍 347 个真实动作。全部 51 个延长分支的前四步与 Stage12 完全一致。六步新增 10 个有知识分支，八步新增 15 个，说明四步无收益不等于长期无价值；这些结果未混入 C0–C3 主成绩。\n\n'
    d+='新增策略代码、输入、候选选择与参数在评分前冻结。149 项单元与依赖回归测试通过。历史 2094 个文件逐哈希保护；没有修改旧代码、旧分数或旧报告。完整性检查包含全 50 状态的来源行、公开历史前缀、所有动作和反馈、全 17 遗漏、全 12 正负差异、50 行公开特征及全部改选配对。原生 worker 禁用网络连接。\n\n'
    d+='这些都是开发状态上的局部诊断，family 之间共享同一游戏配方结构。单步合法、短程知识、补全必要依赖、完整任务成功是不同层次；本轮只评前三类证据，最后一项未运行。未证明覆盖规则能提高完整成功率。记录层面的解析问题可作为明确工程问题留档，但不在本轮借机修改规则、重新调分或扩展实验。\n\n'
    d+='[17 例完整归因](S1遗漏原因分析.md) · [LLM 全部配对](LLM互补性分析.md) · [覆盖规则与全部负面结果](探索覆盖机制实验.md) · [零 API 复现](复现指南.md) · [完整性检查](../../results/stage13/publication_checks.json)\n'
    write('实验总报告.md',d)
    e='''# Stage 13 零 API 复现指南

先在本仓库安装原项目依赖与 pytest，配置外置 AgentOdyssey 引擎。上游固定提交 `248430692a9d4a61d38c6c03ab2126287faaf450`，Python 3.12。不要把引擎、环境目录、模型密钥或下载依赖加入本仓库。

## 已发布材料与边界

- `results/stage13/freeze.json`：规则、输入、选择、补充分支计划的冻结哈希。
- `results/stage13/prior_manifest.json`：2094 个历史文件的保护清单。
- `public_inputs.json`、`decisions.json`、`source_audit.json`：只含决策前公开输入，规则不接收 family/隐藏配方/原生效果。
- `native_supplements.jsonl.gz`：服务器新增 70 个分支及完整前后观察、反馈、动作、耗材与真值评分。
- `native_supplements.jsonl.gz.verification.json`、`local_replay.verification.json`：服务器双回放和本地独立双回放。
- `misses.json`、`llm_pairs.json`、`changed_pairs.json`、`sensitivity.json`：全量归因、正负例、改选与窗口敏感性。
- `public_text_novelty_audit.json`：事后格式敏感性；不修改 Stage12 主指标。

所有 C0–C3 主分支直接引用 Stage12 既有原生结果，无需付费重跑。这里的 pickle 快照是本项目自生成、已固定哈希的原生状态；仅加载仓库可信快照。

## 环境与回放

在仓库根目录执行，Python 路径按实际虚拟环境调整：

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export AGENTODYSSEY_ROOT=/path/to/external/agentodyssey
python -m pytest tests/test_stage7.py tests/test_stage8.py tests/test_stage9.py tests/test_stage10.py tests/test_stage11.py tests/test_stage12.py tests/test_unknown17.py tests/test_sequence.py scar_stage13/test_policy.py scar_stage13/test_diagnostics.py -q
python -m scar_stage13.native --verify results/stage13/native_supplements.jsonl.gz --output /tmp/scar-stage13-replay --workers 8
python -m scar_stage13.analyze
python -m scar_stage13.text_audit
python -m scar_stage13.report
python -m scar_stage13.publication
```

重放器禁用 worker 的 socket.connect，整个流程不需要模型密钥。每次补充分支内部独立执行两次，并逐字段比较已发布记录；延长分支还要求原四步前缀完全相同。`--verify` 不改原始回放文件。服务器原运行路径 `/root/scar_workspace/project`，引擎在 `/root/scar_workspace/dependencies/agentodyssey`；本地独立环境位于 `/mnt/Space0/scar_dependencies`。

若要重新生成补充原生分支，可将 `--verify` 去掉并将 `--output` 指向新的临时 `.jsonl.gz` 路径；不要覆盖发布文件。完整重跑旧 363 分支是可选的昂贵零 API 检查，Stage12 已有服务器/本地全量复现，本轮不要求重复。

## 冻结与来源核验

`scar_stage13.prepare` 是一次性准备器，只能在基线 `9a3bac2` 的临时工作副本、尚无 freeze 时运行；不要删除已发布 freeze 去重调本轮规则。已发布版本使用 `publication` 重算公开历史、输入哈希和策略选择并与冻结文件比较。

C1/C2 阈值、冷却、预算、C3 保护和唯一 L 选择条件没有评分后修改。`analyze`、`text_audit`、`report`、`publication` 是冻结之后新增的诊断/出版代码，按最终 artifact_manifest 哈希保护，不属于事前策略文件。事后审计发现的格式问题只进入独立结果，不回流策略。

配方集合每步为“相对分支初始状态累计”，统计应取并集，不能把每一步相加。Top3 去重按检查目标或制作产物，保留原排名最先出现的代表，不用正确答案选代表。公开估计成本与原生实际动作数分字段存储；后者不参与选择。

没有做参数搜索、留一族调参、独立泛化或新完整闭环。若重算结果与发布值不同，应先核对冻结哈希、引擎版本和随机种子，不能以替换负例、增加 API 调用或继续同状态调阈值来消除差异。
'''
    write('复现指南.md',e)
    atomic_notes={'notes':NOTES,'evidence_layers':evidence,'complete_miss_count':17,'no_policy_effect':True}
    from scar.io import atomic_json
    atomic_json(OUT/'interpretation_notes.json',atomic_notes)
    print(json.dumps({'reports':5,'state_pages':50,'misses':17,'pair_differences':12}))

if __name__=='__main__':main()
