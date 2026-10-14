import json
from .common import *

def table(headers,rr):
    def cell(x):return str(x).replace('|','/').replace('\n',' ')
    return '|'+ '|'.join(headers)+'|\n|'+ '|'.join(['---']*len(headers))+'|\n'+'\n'.join('|'+ '|'.join(cell(x) for x in r)+'|' for r in rr)+'\n'
def link(p):return f'[{p}](../../{p})'
def save(name,content):(REPORTS/name).write_text(content.rstrip()+'\n')

def main():
    offline();s=read(RESULTS/'summary.json');ann=read(RESULTS/'lifecycle_annotations.json');pairs=read(RESULTS/'lifecycle_comparison.json')
    stats=read(RESULTS/'trajectory_statistics.json');ex=read(RESULTS/'extraction_summary.json');trees=read(RESULTS/'paper_goal_stacks.json');gaps=read(RESULTS/'public_knowledge_context_audit.json')
    main='现有证据不支持把本轮长期失败的主要原因归结为缺少 Hierarchical Goal Stack；父子目标关系缺失是结构事实，但其因果作用尚未确认。'
    limits='''全部结果来自 1 条 remnant 母轨迹及其相关分支，10 对检查点不是 10 个独立游戏；Original 后缀彼此重叠。分析覆盖 3,116 个动作出现位置、2,184 个不同源动作。阶段标注由本助手结合完整时间线和原始决策证据审阅，非独立人工盲审。规则计数与语义判断分开保存，不以代码断言冒称语义标签客观无误。

这里的“原目标”是检查点前 Agent 的目标，不自动等于游戏第一章主线，也不保证原失败动作是必要手段。语义回归只说明行为重新对应原目标，不能证明模型内部保留了父子链接；字符串消失同样不能证明遗忘。未做 Oracle Goal Stack 模型重放，因此不能套用该可选实验的“显著提升/无提升”判据。
'''
    phase=table(['阶段','失败/未观察到数量','分母及解释'],[
        ['0 未进入恢复状态','0/10','全部首步提出并登记恢复目标'],
        ['1 不理解临时目标','0/10','理由理解缺口，不等于所有材料/状态都理解正确'],
        ['2 完全没有中间条件或步骤','0/10','6 个局部可操作；4 个部分、未解依赖或错误材料计划'],
        ['3 临时条件未得到完成证据','4/10','不是对潜在未尝试条件的穷尽证明；部分选择了替代路径'],
        ['3 原失败动作在完整后缀未成功','5/10','设施已恢复但材料仍不足、替代方案和生存中断均保留'],
        ['4 原动作成功后全程无语义回归证据','0/5','仅对 5 个原动作已恢复过程计分；不把剩余 5 个混入'],
        ['4 未在检查点后20步内观察到语义回归','1/5','parent_a136；至212已有明确装备探索，不是始终未回归']])
    comparison=table(['检查点','局部条件证据步','原动作成功 Original/Oracle（全后缀）','Oracle 语义回归证据步','恢复规划'],[
        [p['id'],p['condition_evidence_step'] or '未证实',str(p['original']['original_action_success_steps'])+'/'+str(p['oracle']['original_action_success_steps']),p['resume_evidence_by'] or '不适用',p['planning']] for p in pairs])
    save('Stage29实验报告.md',f'''# Stage29 Recovery Execution Failure Analysis

**{s['conclusion']}**。{main}

已完成指引的两项必做离线诊断。未实现 Goal Stack、Planner 或新决策机制；Stage25-AGC-v2、Stage28 轨迹、模型、环境和 prompt 保持冻结。新增模型请求 **0**，新增实验费用 **$0**。可选 Oracle Goal Stack 模型重放未执行；另做了一次不调用模型的同状态原生动作可行性检验，二者不能混称。

## 核心发现

1. **不是普遍缺少分解。** 10/10 个 Oracle 分支都有中间条件或步骤；6 个有局部可操作计划，4 个仍有未解依赖或错误材料假设。lockpick 分支 124/127/143/146 明确保留了“收材料、回工作台、制作”的关系，147 仍因把只持火把误判成手满而丢火把。
2. **不是普遍完成后不回归。** 6/10 有临时条件达成证据，5/10 原失败动作真正成功；这 5 个后来都有与较大原目标相符的意图和行动，其中 4 个在检查点后20步内，另 1 个至212有明确证据。仍需区分慢回归、任务意图与最终完成。
3. **存在结构上的父目标暴露不足。** 控制器最多归档8个目标，模型输入只有当前目标、有限失败记录和最近5条记忆，没有 archive/parent/resume 链。Oracle 的 460/1,558 个动作位置，归档含原目标完整字串而实际模型上下文不含该字串；但这是字面可见性证据，不能单独证明遗忘造成失败。
4. **信息与状态问题仍不能排除。** torch 配方早在母轨迹103/132公开，236的模型上下文已无完整配方，却继续把 cloth 当 torch 材料。剑分支在目标仍 ACTIVE 时把必要的 goblin_eye 丢掉。炉子分支274在上下文仍有 verified=true 黑暗引文时否认黑暗证据。这些是与单纯 Goal Stack 缺失竞争的解释。
5. **局部反事实支持状态/动作瓶颈。** 在 oracle037_a122 第147步前完全相同状态，原动作 drop torch 导致黑暗；离线改为当前已公开可见的 pick up iron_bar 可成功，同时保留 torch。这里只验证局部资源可行性，不证明长期存活、完整任务结果或 Stack 会选择该动作。

## 生命周期统计

{phase}

在完整后缀口径，Original 原动作成功 2/10，Oracle 5/10；Stage28 的20步口径仍是1/10与5/10。两组最终主线奖励均为1，第一章均未完成。本轮没有新任务分数。

{comparison}

“局部条件证据步”有时是后续原动作成功所证明的前置条件曾满足，不表示该条件在动作结束后仍持续满足。设备/工具条件与原动作全部前置条件也不同：oracle037_a122 在123已有工作台，但仍未制成lockpick。

## 能否据此实现 Hierarchical Goal Stack

暂不支持直接把完整 Hierarchical Goal Stack Controller 作为下一版主算法。可以保留父子关系/中断后回归为后续受控对照的候选，但必须和配方/资源信息保留、当前状态判断、完成条件识别及动作执行策略分开。5个原动作成功时控制器均未标记 COMPLETED，模型却仍能自行切换回相关任务；因此“补完成标记”“暴露已有归档”“保留层级”也是不同干预，不能混为同一个机制。

{limits}

详见 [生命周期统计](Recovery生命周期统计.md)、[逐轨迹分类](失败轨迹分类.md)、[Goal Stack反事实](GoalStack反事实分析.md)、[实现判断](HierarchicalGoalStack实现判断.md)。全部原始轨迹仍在原目录，新增分析不覆写它们。
''')
    visibility=table(['检查点','Oracle目标区间数','归档有原字串/上下文无的动作数','首次原字串不在上下文的动作'],[
        [d['id'],d['goal_segments'],len(d['original_archived_context_absent_steps']),d['first_model_context_original_absent']] for d in stats if d['variant']=='OracleRecovery'])
    segs=read(RESULTS/'goal_segments.json')
    behavioral=table(['检查点','版本','动作','公开拒绝','后缀内同动作再次拒绝','目标区间','死亡事件'],[
        [d['id'],d['variant'],d['actions'],d['rejections'],d['repeated_rejections'],d['goal_segments'],sum(x['deaths'] for x in segs if x['id']==d['id'] and x['variant']==d['variant'])] for d in stats])
    save('Recovery生命周期统计.md',f'''# Recovery 生命周期统计

{phase}

{comparison}

分解状态为局部可操作6/10、部分/信息依赖未解3/10、错误材料计划1/10；不是“6成功、4没有规划”。工具来源未知、正确配方未进上下文、子组件方法未解分别保留。原动作实际成功与条件满足是两个指标；未重试不是条件从未满足的证据。

## 语义回归与字面返回

Oracle parent_a054 在58改为武器材料采集；parent_a060 在65转武器制作；parent_a113 在130–132收集/存储制作材料；parent_a136 至212明确装备探索；parent_a270 在274回到装备目标。举证时点给出“至此已观察到”，不冒称穷尽所有同义表达后的首次时刻。对应实际原动作成功到举证时点间隔分别为2、3、15、71、1步。

这五个回归都不要求目标字符串完全相等，也不等同主线完成。parent_a113 在126死亡，后续资源重新收集是原方向的行为证据，不证明旧栈被保留。parent_a136 在141明确返回写quiet这一局部任务，而较大装备/容量目标的明确回归较晚；不能把两层混算。

## 目标存储与可见性

{visibility}

算法根据归档/消息中是否含归一化后的原目标完整字串计数，包含同义扩展中保留该字串的情况；没有该字串不排除语义改写。总计 Original+Oracle 为 {ex['original_goal_archive_but_not_context_actions']} 个动作位置，Oracle为460。归档并未被 summary 输入直接暴露：见 `agents/agc/control.py:summary` 与 `agents/agc_v2/agent.py:_act`。这支持存在架构差异，但不是效果因果实验。

数据：{link('results/stage29/action_audit.jsonl.gz')}、{link('results/stage29/goal_segments.json')}、{link('results/stage29/lifecycle_annotations.json')}、{link('results/stage29/lifecycle_comparison.json')}。`timelines/` 包含全部20条完整后缀的逐动作表，不是抽取有利片段。

## 全后缀行为计数

{behavioral}

同动作再次拒绝只按后缀内相同动作字符串匹配，不要求环境状态相同，因此不是“无意义循环”或“错误重试”的自动判断。目标区间变化可能是同义改写、完成切换、战斗/死亡中断，不能直接计作目标丢失。是否忘记已有进度或没利用资源须查具体证据；oracle037 的146正确记住包中已有材料，与147误判手部空间并存。没有仅按移动/inspect动作把探索计为随机探索，因为无法仅从动作类型识别随机性。

{limits}
''')
    categories=table(['类型','本轮证据','数量','不能推出'],[
        ['A：恢复后忘记父目标','严格从未语义回归未观察到；延迟候选parent_a136','0/5；延迟1/5','延迟不等于遗忘；生存优先可能合理'],
        ['B：恢复目标过大','工具来源、炉子来源、剑的子组件依赖尚未解','候选3/10','都已有部分步骤；不证明完全没有层级分解'],
        ['C：执行中丢失','黑暗子目标被否认一回合；lockpick/剑链被战斗和死亡中断','暂时1、受混杂中断2','275重新恢复光源目标；死亡会改变任务可行性'],
        ['D：层级外约束','各分支均有状态、信息、物品用途、容量/照明或执行约束','证据10/10','没有运行Stack，不能称为10个已验证的Stack失败']])
    sections=[]
    for a in ann:
        p=next(p for p in pairs if p['id']==a['id']);ev=table(['动作','实际动作','当前目标','公开结果（节选）'],[
            [e['step'],e['action'],e['goal']['goal_description'],e['feedback']['text'].split('Current Location:',1)[-1].split('\nI am holding ',1)[0][:320]] for e in a['evidence']])
        sections.append(f"## {a['id']}\n\n原目标：{a['original_goal']}。恢复目标：{a['recovery_objective']}\n\n标签：{', '.join(a['types'])}。\n\n{a['note']}\n\n剩余约束：{a['residual']}\n\n{ev}\n\n[完整Oracle后缀](timelines/{a['id']}__OracleRecovery.md) · [完整Original后缀](timelines/{a['id']}__Original.md)\n")
    save('失败轨迹分类.md','# Stage29 失败轨迹分类\n\n类型允许重叠。以下区分直接观测、候选机制与未证实因果结论。\n\n'+categories+'\n'+ '\n'.join(sections))
    text='# Goal Stack 反事实分析\n\n以下为纸面分析树，不是新增控制器，也没有提供给模型。节点只使用各检查点之前的公开信息，具体引文/截止动作/来源保存于 `paper_goal_stacks.json`。L0是Agent当时目标，不保证等于游戏主线；原尝试只是候选手段，不强行当必要路径。\n\n'
    for t in trees:
        text+=f"## {t['id']}（知识截止动作 {t['knowledge_cutoff']}）\n\n"
        text+=table(['节点','父节点','层级','条件/目标'],[[n['id'],n['parent'],n['level'],n['goal']] for n in t['nodes']])
        text+='\n公开依据：\n\n'+'\n'.join(f'- 动作 {e["step"]}：`{e["quote"]}`' for e in t['evidence'])+'\n\n'
        text+='仍未知或不能由层级本身决定：'+'；'.join(t['unknowns'])+'\n\n'
    text+='''## 与信息补充的混杂

parent_a235 的旧 torch 配方公开于103/132，但236实际模型上下文未包含完整配方；若“理想Stack”补入 wooden_rod 和 mountain_sulfur，干预同时补回了旧知识。oracle079_a165 的完整剑配方在166上下文可见，173已不在；当时目标仍ACTIVE，模型却说 goblin_eye 不需要。相反，oracle032_a256 在274的上下文仍有 verified=true 的黑暗引文，却说没有直接黑暗证据。前者涉及信息保留/利用，后者涉及已在上下文证据的判断，不能都称为父目标丢失。

这些检查是特定完整字串/关系的证据，不等同测量模型内部记忆。全文和请求ID保存在 public_knowledge_context_audit.json。

## 已执行的原生局部反事实

在 oracle037_a122 的147步前复原相同物理状态/环境RNG；24步保存响应前缀精确回放，未调用模型。公开状态显示手持1个torch、地上可见iron_bar。原理由本身考虑了pick up iron_bar，却先错误认为手满并执行drop torch。

|同状态动作|实际原生结果|可支持的判断|
|---|---|---|
|drop torch（保存原动作）|状态哈希与旧轨迹一致；变暗|原分支精确重现|
|pick up iron_bar（公开可见候选）|成功；手中同时保留torch与iron_bar|存在不牺牲照明的局部可行行动|

这个对照是局部动作可行性证据，不能证明该动作长期更优、不会死亡、能够完成lockpick或第一章，更不能证明Goal Stack会选择它。它说明至少这一局部错误发生在目标与材料计划仍明确的情况下，单纯保留目标名称没有解决状态判断。

## 未执行的可选 Oracle Goal Stack Replay

本轮没有调用模型进行Stack提示续跑，也没有生成该实验的成功率。优先完成离线机制筛查，是因为当前存在多个竞争解释；“理想Stack”若补入旧配方、当前库存推断或替模型决定材料优先级，会混合信息、规划与层级三个干预。未执行不等于Stack无提升，也不构成关闭该研究方向的证据。

若后续另行安排，需信息等量对照，并保留合法替代、条件失效和死亡后的重新评估；这些均未在Stage29实现。
'''
    save('GoalStack反事实分析.md',text)
    save('HierarchicalGoalStack实现判断.md',f'''# Hierarchical Goal Stack 是否值得实现

**不建议现在直接实现完整 Hierarchical Goal Stack Controller 作为下一版主算法。** {main}

## 已确认的事实

- 只有一个活跃目标，旧目标最多8个归档，没有显式父子/恢复链接，归档未直接进入模型上下文。
- 模型仍能表达多步恢复计划、在战斗后恢复任务，并在5个原动作成功案例中重新出现对应父目标的行为。
- 目标保持期间仍可发生当前手部状态误判、必要材料丢弃、无效物品用途、照明/容量冲突。
- 旧公开配方不总在实际模型输入中；有时已在输入中的有效证据也会被否认。

## 不能成立的排他结论

不能据此说“主要限制不是信息、记忆或单步行动能力，只是缺少层级管理”。Stage27/28也没有排除这些竞争解释。本轮没有Stack模型重放，所以既未证明Stack有效，也未证明Stack无效。目标归档结构缺少链接，与某个具体失败由该缺失造成，是不同层次的命题。

## 研究价值的边界

父子关系和中断后回归仍值得作为较小的受控诊断候选；重点应是能否在信息相同的情况下增加可验证的执行进展。与此同时，需要分别评估公开配方保留/再呈现、当前资源事实、目标完成条件与动作可行性。单纯把所有这些能力打包为“Goal Stack”会失去机制可解释性。

工程层面可见的问题包括：归档不暴露、仅按字面命令判完成、当前状态误读、已存在证据被错误降为无效。它们并非都能由栈结构自然解决，也不能从本轮推断修复后的长期收益。研究层面尚未隔离的是：在资源和生存约束频繁变化时，如何维持有效的条件依赖、识别失效并选择适当回归时机。这里只提出待验证问题，没有实现方案。

{limits}

本轮新模型调用0、费用$0，生产Agent修改0；未开发Stage30或任何Goal Stack机制。
''')
    save('README.md','''# Stage29 复现入口

[总报告](Stage29实验报告.md) · [生命周期](Recovery生命周期统计.md) · [分类](失败轨迹分类.md) · [纸面反事实与原生探针](GoalStack反事实分析.md) · [实现判断](HierarchicalGoalStack实现判断.md)

使用既有Python环境及冻结AgentOdyssey，设置与Stage28相同的 `AGENTODYSSEY_ROOT`、`PYTHONPATH`、`PYTHONHASHSEED=0` 和 `HF_HUB_OFFLINE=1`。所有Stage29程序使用网络禁用器，没有付费provider入口。

```bash
python -m scar_stage29.extract
python -m scar_stage29.annotations
python -m scar_stage29.stacks
python -m scar_stage29.native_probe
python -m scar_stage29.summarize
python -m scar_stage29.verify
python -m scar_stage29.report
python -m scar_stage29.audit
```

annotations.py 是透明的语义标注及证据动作号，统计代码不将其伪装成自动真值；修改标注后须重新汇总。native_probe 只在隔离副本重放保存响应及2个候选环境动作。没有Oracle Goal Stack模型续跑。

action_audit.jsonl.gz 为完整3116动作出现位置；goal_segments.json 为目标区间；lifecycle_annotations.json 为原始证据；paper_goal_stacks.json 为限定知识截止点的纸面树；public_knowledge_context_audit.json 为配方/引文的实际输入可见性；evidence_index.jsonl.gz 将绝对动作号映射到原文件行号和请求ID。不同Original后缀相互重叠，不作独立样本推断。

旧Stage28数据已做完整原生回放，Stage29验证其冻结哈希并复用收据；新增局部探针单独精确重放。audit的私钥排除扫描仅在本地私钥存在时执行，公开复算无需密钥或模型服务。下载依赖不上传。
''')
    print(json.dumps(dict(reports=6,new_model_calls=0)),flush=True)

if __name__=='__main__':main()
