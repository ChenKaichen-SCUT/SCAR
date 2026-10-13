"""Generate all human reports from audit artifacts and original evidence."""
from .common import *
deny_network()
from collections import Counter


def cell(value):
    if value is None:return '—'
    return str(value).replace('|','\\|').replace('\n','<br>')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(cell(v) for v in row)+' |' for row in rows])+'\n'
def js(value):return json.dumps(value,ensure_ascii=False,indent=2)
def save(name,text):(REPORTS/(name+'.md')).write_text(('# '+name+'\n\n'+text).rstrip()+'\n')
def short(tid):return tid.split('-',3)[-1]


def main():
    summary=load(RESULTS/'summary.json');stalls=load(RESULTS/'stall_audit.json');rejects=load(RESULTS/'rejection_audit.json')
    intents=load(RESULTS/'intent_audit.json');crafts=load(RESULTS/'craft_proposal_audit.json');branches=load(RESULTS/'branch_analysis.json')
    raw_branches={r['id']:r for r in read_gzip(RESULTS/'counterfactual_results.jsonl.gz')}
    tests=load(RESULTS/'test_receipt.json');extraction=load(RESULTS/'extraction_receipt.json');receipt=load(RESULTS/'counterfactual_receipt.json')
    stamp=('基于Stage20最终提交 `a034a69756432daebd16114854d8d266ff90a2d0`。本轮为只读事后审计，模型请求0、token 0、费用0；'
        '没有开发Stage21、改变旧策略或重新采样任务。动作编号为正式任务内动作数；终态“第N+1次动作选择”可以没有执行动作。\n\n')
    classes=('分类允许重叠。A=确证无尚未尝试且有公共依据的探索入口；B=公共入口存在但被控制器过滤（**广义包含18次固定额度过滤**）；'
        'C=B中同时有此前已公开、与当前必要依赖相关的新证据且额度耗尽；D=原始实际拒绝原因为 `not_a_current_dependency_or_blocker`，'
        '且提案仍有合法公共入口和可有界验证的材料假设。单纯ID字段匹配问题不直接算D。\n\n'
        '另单列不涉及额度的候选遗漏，避免把“B=11”误读为11局都有相同BFS错误。A=0表示11局均找到可尝试入口，并不表示知道每个入口最终有用；'
        '未被单步回放验证的知识价值以及整个任务能否恢复均为UNKNOWN。\n\n')
    overview=table(['任务','停步/剩余','探索/18','逻辑请求/24','分类','非额度遗漏候选'],[
        [r['target'],f"{r['steps']}/{r['remaining_actions']}",r['exploration_spent'],r['planning_calls'],
         ','.join(k for k,v in r['categories'].items() if v is True),'; '.join(r['nonquota_omission_witnesses']) or '无'] for r in stalls])
    text=stamp+classes+f"计数：A={summary['stall_counts']['A']}，B={summary['stall_counts']['B']}，C={summary['stall_counts']['C']}，D={summary['stall_counts']['D']}。"
    text+=f"其中{summary['nonquota_omission_tasks']}局存在独立于额度的中转/访问历史候选遗漏，10局耗尽探索18次，cog_crossbow为14次。\n\n"+overview
    text+='\n候选枚举仅使用真实公开物品、公开配方、容器、邻居和历史已知路线。未知门锁保留UNKNOWN，已知锁门且无手持钥匙的路线排除；历史出现过的room/furnace不等于现在可达。动作全集限于制作任务的检查、移动、收取、容器取物、已公开制作和必要放置；未声称穷举战斗、NPC交易或所有游戏交互。\n'
    for r in stalls:
        text+=f"\n## {r['task_id']}\n\n当前目标 `{r['final_goal']}`，阻碍 `{r['current_blocker'].get('kind')}:{r['current_blocker'].get('item')}`。"
        text+=f"剩余{r['remaining_actions']}步；探索{r['exploration_spent']}/18，逻辑请求{r['planning_calls']}/24；终态can_request={r['can_request_at_terminal']}。"
        text+='这表明停滞由局部动作/同上下文请求边界共同确定，并非100步或24次总规划上限耗尽。\n\n'
        text+=f"FIFO `{r['FIFO']['queue']}`；当前地点 `{r['public_map']['location']}`。公开配方/取得路径仍缺：`{r['public_recipe_gaps']}`（部分节点可能是原材料，缺配方不等于必须制作）；数量UNKNOWN：`{r['quantity_unknown']}`。\n\n"
        text+=table(['最后动作','执行内容','来源','探索已用','原始反馈节选'],[[x['step'],x['action'],x['source'],x['exploration_spent'],x['feedback'][:450]] for x in r['last_15_actions']])
        relevant=r['relevant_evidence']
        text+='\n与当前公开必要依赖相关的新证据：'+('; '.join(f"a{x['step']} {x['action']} → {x['new_related_relations'] or x['new_related_area_requirements']}" for x in relevant) or '未能确认；不使用隐藏配方补足相关性')+'。\n\n'
        candidates=[x for x in r['candidates'] if x['eligible_public_trial'] and x['possible_new_knowledge'] and x['action'].startswith(('inspect ','enter '))]
        text+=table(['公开候选','公开来源','同上下文执行/回退尝试','未执行过滤','经由路线'],[[x['action'],','.join(x['sources']),f"{x['same_context_actual_visits']}/{x['entry_attempts_same_context']}",','.join(x['nonexecution_filters']),js(x['route_witnesses'])] for x in candidates])
        text+='\n同状态单步验证：\n\n'+table(['动作','环境接受','新增公开配方','即时HP损失','证据ID'],[
            [b['action'],b['native_action_accepted'],', '.join(b['new_relations']) or '无',b['player_hp_loss'],b['id']]
            for b in branches if b['task_id']==r['task_id'] and b['at_completed_step']==r['steps']])
        text+='\n分类证据：`'+js(r['categories'])+'`。'
        if r['categories']['C']:text+=' C仅说明相关新线索后仍被固定额度截断，不证明追加探索一定找到材料。'
        if r['direct_D_witnesses']:text+=' D对应原始提案：`'+', '.join(r['direct_D_witnesses'])+'`。'
        text+='\n\n完整公开配方数量、材料持有、工作台要求、地图、FIFO、访问哈希、规划历史、全部候选（含拒绝项）见 `results/stage20_audit/stall_audit.json` 同task_id；原始终态、15步完整原反馈及检查点哈希见 `terminal_states.jsonl.gz`。\n'
    text+='\n## 最有辨识度的边界\n\n'
    text+='cog_crossbow第20步后，`enter courtyard`的语法、已知条件、访问次数和探针额度全部允许；目的地cellar有公开未检查charite/devil_oil/rubble。回退只看相邻courtyard本身是否有未检查对象，丢掉中转动作。原生单步进入courtyard成功且无HP损失，但没有新增配方，故仅确证可执行中转遗漏。\n\n'
    text+='repair_kit第21步已公开oil_flask→rubble_chunk关系，第23步后探索18/18；单步检查当时可见rubble公开rubble_chunk与crucible，旧known_step在该公开反馈之后能给出 `store 1 rubble inventory`。只执行了检查，后续收取未执行，也未证明整局成功。\n\n'
    text+='war_banner无此前可证明相关的新必要配方，不能硬归C；但终态检查salvage_cloth确实公开war_banner。metal_plate同样在终态仍缺目标关系。因此“只有先获得目标相关新证据才续给额度”未必能覆盖所有固定额度失败。\n'
    save('11局探索停滞归因',text)

    counts=summary['rejection_counts'];text=stamp+f"44次互斥分类：①可确定字段匹配误拒 **{counts['I']}**；②有公共入口的有界待验证假设 **{counts['II']}**；③还有确实应拒绝的问题 **{counts['III']}**；④UNKNOWN **{counts['IV']}**。\n\n"
    text+=('①是证据检查层的误拒，并非认证整条意图可以无条件执行；剩余额度、重复、已经满足的子目标和风险仍需单独检查。②保留材料与最终目标的关系UNKNOWN，'
        '不把假设写入配方。③包含4次把地点当作LOCATE物品前提，以及3次历史room/furnace无当前公开路线；不通过改写类型或对象名将其算为合法。\n\n'
        '影子校验读取names、frontier.from_location、route、当前对象location，以及blocker中由真实地图派生的public_entries。目标名称出现在goal或自由文本中不构成入口证据。'
        '未知ID、未来ID、不存在对象、无路线地点和已知锁门都拒绝。未知门锁仍为可试但未经证实可达；反事实中3个锁门拒绝说明不能把UNKNOWN当作确定可执行。\n\n')
    text+=f"对44个原状态分别做6种负例，共{tests['negative_controls']}例；不存在入口、断开的历史地点、唯一已知锁门路线、虚构目标、未知ID、未来ID均拒绝，错误接受0。这只覆盖这些测试边界，不是任意输入的完备性证明。\n\n"
    text+=table(['序号','任务/动作选择','原类型→目标/入口','分类','判定'],[[n,r['id'],r['proposal']['type']+' '+r['proposal']['target']+'/'+r['proposal']['entry'],r['shadow']['category'],r['shadow']['reason']] for n,r in enumerate(rejects,1)])
    for n,r in enumerate(rejects,1):
        text+=f"\n## {n:02d} {r['id']}\n\n原请求 `{r['request_id']}`，状态索引 `{r['state_index']}`。原返回 `evidence_unrelated_to_execution_entry`，影子分类 **{r['shadow']['category']}**。\n\n原提案（未改写）：\n\n```json\n{js(r['proposal'])}\n```\n\n"
        text+=table(['原ID','类型/对象','names','原结构化值'],[[e['id'],e['kind']+'/'+e['key'],e['names'],js(e['value'])] for e in r['original_records']])
        text+='\n影子字段关系与入口判定：\n\n```json\n'+js(r['shadow'])+'\n```\n'
    text+='\n32次误拒中可出现与目标尚无因果证明的探索，但这并非旧check真正验证的命题：旧check只测试entry是否直接出现在非goal/blocker记录names中。D类因果关联门槛应另外通过实际not_a_current_dependency_or_blocker定位，不能用44次拒绝数替代。\n'
    save('44次证据误拒分析',text)

    text=stamp+'审计59个LOCATE_PRECONDITION、2个ACQUIRE_MATERIAL，以及2个被拒CRAFT_PRECONDITION提案。五个阶段分开计算；最后一列允许后续确定性控制器完成，不归功于该条意图。\n\n'
    text+=table(['类型','接受','意图完成','至少检查一次','发现公开路径','意图期实际收取目标','意图期持有/区域前提满足','整局后续父制作'],[
        [kind,v['accepted'],v['completed']]+[v['stages'][k] for k in ('first_inspect','first_public_path','first_actual_target_transfer','first_requirement_satisfied','first_parent_craft_success')] for kind,v in summary['intents'].items()])
    text+=('\n父制作按意图记录关联计数，多条意图可指向同一任务和同一次父制作，不能求和为独立收益。LOCATE只需发现路径，意图期收取为0本身不构成失败；'
        f"8个完成LOCATE中有{summary['completed_LOCATE_with_later_parent_production']}个随后发生父制作，另一个iron_nugget在发现区域crucible约束后失败。\n\n")
    text+=table(['LOCATE终态原因','数量'],summary['intents']['LOCATE_PRECONDITION']['terminal_reasons'].items())
    text+='\n## 可确定的机制边界\n\n'
    text+=('1. `_entry_step()`抵达entry后按名称顺序检查当前可见未检查物；目标缺配方时无法凭空执行收取。入口耗尽便挂起，后续提案可以替换；它没有任意猜测新材料来源的能力。'
        '59条LOCATE中的51条未完成，最早可见中断不等同最终终止原因：部分先挂起、恢复后才因风险取消，报告保留两者。\n\n'
        '2. 两个ACQUIRE都未曾建立目标实际供给路径。oil_bomb的sg20_4在第7–8步检查scrap_iron/sinew_cord，第8步完成后的下一次选择发现barracks入口已无可继续对象；'
        '目标oil_flask仍无公开配方或供给，探索只用5/18，意图尚余4步。gate_cipher的sg20_6第17–19步进入watchtower、检查iron_bar/war_parchment_0，cog来源仍未知。'
        '两者都在“未知目标取得路径→入口搜索耗尽”处挂起并被替换，不能称为已经拿到材料却被P3夺走，也不能声称已知可执行收取被执行器破坏。\n\n'
        '3. `_known_path()`验证公共可达供给或递归材料/已知区域要求，未证明精确数量和全部尚未公开条件。iron_nugget第12步因已知scrap_iron配方路径完成LOCATE，'
        '实际制作随后暴露crucible要求。它证明“发现路径”与“满足实际制作前提”需要分别记录，尚不能证明应强制保持原LOCATE直到最终制作。\n\n'
        f"4. 61条重点意图有{summary['resume_events']}次恢复事件，涉及{summary['resumed_intents']}个意图，说明挂起/恢复并非全部失效；实际P3抢占中断为{summary['P3_interruptions']}。"
        '19次LOCATE最终风险取消均应对照真实HP变化和公开攻击反馈，不能仅凭结束原因断言是无必要的抢占。没有同状态多步风险反事实，不判断继续执行更好。\n\n'
        '5. 两个CRAFT提案分别是rubble_chunk（配方尚未公开）和wood_plank（公开配方存在，但与wood_stake的必要关联未获公开证明）。二者都在接受之前停止；'
        '它们不是实际已证实必需的工作台制作提案，当前数据没有工作台制作执行器尝试失败的证据。只因0接受就重写执行器缺乏依据。\n\n')
    text+='## 全部重点意图索引\n\n'+table(['意图','目标/入口','起止/动作数','状态','首次中断：已执行步数→选择步','阶段：检查/路径/收取/满足/父制作'],[
        [r['id'],r['target']+'/'+r['entry'],f"{r['start_step']}–{r['end_step']}/{r['steps']}",r['status'],
         '—' if not r['first_failure_node'] else f"{r['first_failure_node']['first_observable_node']}→{r['first_failure_node']['action_selection_step']} {r['first_failure_node']['category']}",
         '/'.join(str(v) if v is not None else '—' for v in r['stages'].values())] for r in intents])
    for r in intents:
        text+=f"\n## {r['id']}\n\n提案 `{r['planning_state_id']}`：`{r['type']}`，目标 `{r['target']}`，入口 `{r['entry']}`；原制作父目标 `{r['parent']}`。"
        text+=f"状态 `{r['status']}`，最终原因 `{r['termination_reason']}`；原任务确定性执行首次恢复={r['original_goal_execution_resumed']}，动作 `{r['first_resumed_action']}`。\n\n"
        text+=table(['动作序号','实际执行','新公开配方','公共路径/真实收取/前提满足','原始反馈节选'],[
            [x['step'],x['action'],x['new_relations'],f"{x['public_path']}/{x['actual_target_transfer']}/{x['required_possession_or_area_satisfied']}",x['feedback'][:380]] for x in r['timeline']])
        text+='\n生命周期：`'+js(r['lifecycle'])+'`。\n\n最早可观察中断节点：\n\n```json\n'+js(r['first_failure_node'])+'\n```\n'
        text+='\n父制作尝试（包含失败，不只统计成功）：`'+js(r['parent_attempts'])+'`。\n'
    text+='\n## 两个CRAFT提案原始证据\n\n'
    for r in crafts:text+='```json\n'+js(r)+'\n```\n\n'
    save('多步子目标失效机制',text)

    research=stamp+'''**研究判断：PARTIAL。先做普通工程修正；当前只推荐一个值得独立对照验证的新机制。**

| 问题 | 当前直接证据 | 最小处理性质 | 是否需要新算法机制 |
| --- | --- | --- | --- |
| entry只查names，忽略from_location、route、对象location、嵌套public_entries | 32次证据检查层误拒；264负例未错误接受 | 类型明确的字段关联与提示/校验器一致性 | 否，普通工程修正 |
| 回退只看相邻地点有没有新物品，遗漏通往更远公开入口的中转 | 7局有非额度候选遗漏；cog_crossbow 14/18停滞时进入courtyard原生成功 | 在已知公开图上保留必要中转候选；访问计数绑定待解除阻碍 | 否，已有图搜索/候选管理问题 |
| LOCATE字段使用地点、历史room不可达 | 4个类型语义错误、3个无当前路线的提案 | 明确子目标类型与可达性，不把不合法内容强制归一化 | 否 |
| 有实际公开线索后仍被18次额度硬截断 | 7局满足C；repair_kit与sharpened_blade各有单步公开必要配方及恢复known_step证据 | 仅修字段和BFS仍不改变硬额度 | 有条件需要证据触发的有界恢复 |
| ACQUIRE不要求已经证明最终依赖时如何允许验证 | metal_plate第11次选择被依赖归属门槛拒绝；同状态store 1 scrap_metal公开目标配方，实际inspect desk未公开 | 将可试假设和已验证执行义务分层、每次只做有限公开动作 | 有研究潜力，但单独机制证据仍少，先作为接口/阶段语义修正 |
| 多步意图取消是否意味着执行器失效 | 两个ACQUIRE始终无实际供给路径；8个LOCATE完成有7个随后父制作；0次P3抢占 | 五阶段日志、明确挂起/恢复原因、保留父目标义务 | 尚未证明需要复杂的新持续执行算法 |

## 唯一优先研究候选：证据触发的有界探索恢复

**已有证据。** repair_kit第21步获得oil_flask→rubble_chunk线索，停在23步；原生单步检查rubble公开rubble_chunk，旧控制器即可提出继续收取。sharpened_blade终态检查iron_bar公开forged_blade，同样重新出现已知执行动作。两者仍剩余约80步，且没有修改数量/批量规则。固定18次额度不随新知识变化，这个限制不会因单纯字段匹配修复而消失。

**最小机制定义（本轮未实施）。** 一个新公开事实必须改变当前阻碍的公开依赖、取得路径或区域前提，且从未为该事实发放过恢复机会，才发放小额、有上限的后续探索机会。证据与阻碍、候选公共入口及预期验证结果均留痕；重复检查/重复ID/仅时间变化不补额度。安全条件、风险、总动作100步和全局费用限制继续有效。具体奖励步数在未来新实验冻结前确定，不根据本轮反事实挑选。

**尚缺证据。** 只验证了单步信息/可执行性，未验证收取、后续数量、区域条件、最终取物或整体成本。7个C任务并非7个已证实可被恢复的任务。war_banner与metal_plate终态此前没有可证明目标相关新配方，单纯依赖此触发条件可能无法帮它们。新增探索也有即时受伤风险，不能把剩余预算视作免费收益。

**预期验证方式。** 未来如获授权，先固定“证据字段+公开中转+意图状态语义”工程基线，再比较该基线、同最坏额外额度的固定小扩额、证据触发小扩额。保留全部失败；对照每次补额是否得到新关系、真实材料、区域前提与父制作，最后才报告任务成功率、全部动作和费用。在新独立任务族与多种子验证，不能继续把当前24个开发题当作独立泛化集。当前没有启动这项实验。

## 对“可验证的子目标持续执行”的判断

其五阶段核验和父义务登记有必要，当前首先属于普通工程设计：检查入口完成≠找到公共路径≠取得材料≠满足区域前提≠成功制作父物品。类型别名、已有路径却继续LOCATE、风险取消与恢复日志应先明确。

本轮不将“更长意图保持”列为第二个独立研究算法：已有10次恢复事件，两个ACQUIRE尚未找到真实供给，多数失败LOCATE还处于未知路径/入口搜索；这不足以证明强行保留原意图会比挂起或重新提出假设更好。只有工程基线中反复出现“已验证可执行前提却在无新风险时被丢弃”的同状态证据，才适合再研究独立的持续执行机制。当前不能为论文创新强加更复杂的记忆、排序或求解器。
'''
    save('算法改进必要性评估',research)
    total=stamp+f"**判定：PARTIAL。** 完成11个停滞任务、44次指定拒绝、59个LOCATE、2个ACQUIRE与2个CRAFT提案的逐例审计。重建{extraction['decisions_reconstructed']}次历史决策，191个真实规划快照/接受结果完全一致。\n\n"
    total+=classes+overview+'\n'
    total+=f"A/B/C/D计数为 **0/11/7/1**，其中非额度候选遗漏7局；32次可确定证据层误拒、5次公共有界假设、7次其他应拒绝问题、0次无法分类。{tests['negative_controls']}个负例错误接受0。\n\n"
    total+=('D的直接例是metal_plate第11次动作选择：合法scrap_metal入口存在，LLM明确承认它与目标的关系尚未知，实际被依赖归属门槛拒绝。'
        '同状态一次store 1 scrap_metal公开metal_plate配方，原动作inspect desk没有该信息。该结果验证一个局部信息损失；不证明接受整条意图就会成功。'
        'cog_assembly、repair_kit、sharpened_blade还有被ID门槛先挡住的类似材料假设；它们不算实际D门槛直接触发，完整字段关系在44次报告中。\n\n')
    total+=f"原生单步反事实 **{summary['native_branches']}** 个，接受{summary['native_accepted']}、锁门拒绝3；14个分支公开新配方，7个分支有玩家HP损失。"
    total+=f"为恢复4个拒绝状态，仅回放{receipt['factual_prefix_actions']}个保存的事实动作（教程前缀另计{sum(x['initial_history_actions'] for x in receipt['factual_prefixes'])}步）；其余终态直接恢复已保存检查点。没有新闭环任务或模型重新采样。\n\n"
    total+=('独立核验进程再次执行相同37个分支、47个事实前缀动作和28个教程动作，逐项比对状态哈希与反馈；没有新增反事实候选。'
        '因此包含核验的实际原生动作调用合计224次：74次单步分支、94次事实前缀及56次教程动作。37是不同反事实的数量，并非全部原生动作调用数。详见 `verification.json`。\n\n')
    total+=('子目标结论：LOCATE 59个仅8个确认公共路径，不能等同拿到材料或全部工作台条件；其中7个随后由确定性模块完成父制作。ACQUIRE 2个都在未知材料路径、局部入口耗尽处挂起后被替换，0个取得目标。'
        'CRAFT两个分别在未公开配方/未证明当前依赖的接受门槛停止，并没有实际工作台制作失败轨迹。61个重点意图无P3抢占中断。\n\n'
        '工程修正优先：证据字段关联、公开图中转候选、类型语义与五阶段完成记录。独立研究仅优先考虑“新公开证据触发的有界探索恢复”；更复杂的持续执行机制目前证据不足。详见《算法改进必要性评估》。\n\n')
    total+='## 可重算交付\n\n'
    total+='| 内容 | 文件 |\n| --- | --- |\n| 全部191次规划前公开状态与原请求索引 | `planning_states.jsonl.gz`、`state_index.json` |\n| 11局原始终态、检查点哈希、候选全集 | `terminal_states.jsonl.gz`、`stall_audit.json` |\n| 44次原提案/ID/字段关系分类 | `rejection_audit.json` |\n| 61个重点意图逐动作与最早中断 | `intent_audit.json` |\n| 2个CRAFT拒绝 | `craft_proposal_audit.json` |\n| 事先保存的公开选择规则与单步原始反馈 | `counterfactual_plan.json`、`counterfactual_results.jsonl.gz` |\n| 单步与原动作比较 | `branch_analysis.json` |\n| 测试、独立核验和保护清单 | `test_receipt.json`、`verification.json`、`protected_manifest.json` |\n\n'
    total+='上述结果位于 `results/stage20_audit/`，代码位于 `scar_stage20_audit/`。本地固定依赖已安装时：\n\n```bash\nbash scar_stage20_audit/run.sh extract\nbash scar_stage20_audit/run.sh branches\nbash scar_stage20_audit/run.sh analyze\nbash scar_stage20_audit/run.sh test\nbash scar_stage20_audit/run.sh report\nbash scar_stage20_audit/run.sh verify\n```\n\n'
    total+=('完整原生复核还需要本机保留的 `runtime/stage20/runs/` 物理检查点、`runtime/stage20/budget.sqlite` 及固定版本AgentOdyssey环境；'
        '这些私有运行文件未上传，不能声称仅克隆GitHub即可重放原生分支。已有公开审计产物和Stage20轨迹足以重新执行 `analyze`、`test`、`report`，'
        '不需要读取API密钥或重新获取模型回复。默认依赖位置为 `/mnt/Space0/scar_dependencies`，可用 `SCAR_DEPENDENCIES` 指向其他已安装位置。\n\n')
    total+='每个进程在加载环境前阻断网络；未读取API密钥，也不调用模型或嵌入接口。extract重建的是已保存回复驱动的决策，branches只执行已列出的单步候选。没有因单步结果追加挑选有利分支。下载依赖和私有物理检查点不上传，只提交自有审计代码、状态索引、原始单步反馈与报告。Stage17—20所有跟踪文件逐字节保留。\n'
    save('零API审计总报告',total)


if __name__=='__main__':main()
