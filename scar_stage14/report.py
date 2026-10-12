"""Chinese reports generated from immutable evidence and independent diagnostics."""
import json
from collections import defaultdict
from pathlib import Path
from scar_stage14.common import ROOT,OLD,load,records,episodes

OUT=Path('reports/stage14')
LABEL={'original':'原始 Stage12','parser_only':'仅校正解析计分','executor_only':'仅统一意图执行','both':'两者统一'}


def table(headers,rows):
    def cell(x):return str(x).replace('|','／').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(cell(x) for x in row)+' |' for row in rows])+'\n'


def put(name,text):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n')


def yn(x):return '是' if x else '否'
def names(x):return '、'.join(x) or '无'


def main():
    stats=load(ROOT/'knowledge_statistics.json');runs=load(ROOT/'episode_knowledge_summary.json')
    metric=load(ROOT/'calibrated_method_metrics.json');rs=load(ROOT/'residual_summary.json');ws=load(ROOT/'residual_witness_summary.json')
    states=load(ROOT/'residual_states.json');full=load(ROOT/'full_episode_failure_audit.json')
    m={(r['panel'],r['window'],r['method']):r for r in metric}
    panels=table(['评价口径（最多4步）','J0 S1','J1 确定性排序','J2 简单Prompt','J3 显式候选LLM'],[
        [LABEL[p]]+[f"{m[p,4,j]['useful']}/50；{m[p,4,j]['actions']}动作" for j in ['J0','J1','J2','J3']] for p in LABEL])
    families=table(['family','公开配方／轨迹对','已登记','终末遗漏','数量缺口','只补登记的重复检查'],[
        [f,r['public_relations_sum_per_run'],r['registered_disclosed_relations_sum_per_run'],r['never_registered_sum_per_run'],r['quantity_missing_or_different_sum_per_run'],r['registration_only_reinspections']]
        for f,r in sorted(stats['formal']['family'].items())])
    stage_table=table(['阶段','轨迹','公开配方／轨迹对','登记','终末遗漏','遗漏率','数量缺口','登记延迟均值*','重复检查'],[
        [stage,r['runs'],r['public_relations_sum_per_run'],r['registered_disclosed_relations_sum_per_run'],r['never_registered_sum_per_run'],f"{r['never_registered_fraction']:.2%}",r['quantity_missing_or_different_sum_per_run'],f"{r['mean_registration_delay_when_registered']:.3f}",r['registration_only_reinspections']]
        for stage,r in stats['formal']['stage'].items()])
    fm=load(ROOT/'disclosure_registration_by_format_action.json')
    format_table=table(['首次披露动作／格式','关系首次公开','最终登记','最终遗漏','首次数字披露','终末数量缺口'],[
        [key,r.get('public_relations',0),r.get('finally_registered',0),r.get('never_registered',0),r.get('explicit_quantity_first_disclosures',0),r.get('quantity_missing_or_different_final',0)] for key,r in fm.items()])
    put('公开知识解析审计.md',f'''# Stage14 公开知识解析审计

本轮处理全部 90 条正式轨迹、2837 个动作、50 个冻结状态、363 条 Stage12 分支和70条 Stage13补充分支。冻结基线为 `80d8009`，不改历史成功率，不把离线解析器接入 S1。

## 知识口径与实现

K1 是真实环境反馈已公开的知识；K2 是当时控制器实际登记的结构；K3 是保存请求、事实摘要或持久工作流状态中可访问的信息。K3 中出现文本不证明模型理解或使用它。

`scar_stage14/knowledge.py` 只接收有来源证明的原生观察。检查反馈须具有原生检查头和制作关系段；获得物品反馈须具有完整的原生获得物品句式。整个配方列表必须符合语法，普通描述中的相似括号不能成为已确认规则。模型输出不作为事实来源。

配方保留 product、ingredients、quantities、stations、source_action、observed_step、raw_evidence、certainty，以及首次关系时间、首次数字时间和每次证据事件。仅材料名称时数量保持 UNKNOWN；不会补为1。缺工作台反馈只证明已披露的必要工作台子集。成功制作只证明产物出现，不能由此杜撰配方；本语料的数量配方由收取／存放的获得物品反馈披露。

同一步、同一原始观察跨历史和当前状态输入只处理一次。以后重复披露保留事件但不重复增加知识集合；名称之后出现数字是数量升级。0.25、0.5 等小数按实际文本保留。来源冲突单列 AMBIGUOUS，不计入已确认关系。

旧 ResourceTable 主要识别 `made of` 名称关系；数量通常来自后续制作与库存观察的经验样本。经验耗材还可能混入环境损耗，不能当成普适配方真值。本轮数字披露与旧结构不一致的记录统一称“数量缺口／不一致”，不把全部解释成完全缺失。

## 全部正式轨迹

{stage_table}

*延迟只对最终登记项求均值，单位为环境步；未登记项保留右删失。计数单位为“轨迹×配方”，不是跨90次试验去重后的游戏配方目录，也不是独立样本。

合计2298个公开关系／轨迹对，1984个最终登记，314个遗漏；1632个已登记名称仍缺失或不符合明确数字披露。82次检查只把已有公开关系补入旧登记，未增加关系、数量或工作台知识。它们是登记重复的证据，不证明这些动作在修复后的闭环中一定可以省去。

{families}

## 动作与格式

{format_table}

名称遗漏全部来自数字形式的获得物品披露：645个首次关系中314个最终没有登记；`inspect` 名称形式的1653个首次关系最终全部登记。格式和动作行是同一证据的不同分组，不能相加。

真实制作失败给出215个新增工作台披露事件，没有新增材料关系；制作成功不会被本实现凭空转成配方。2423个获得物品披露事件中，2111次补充了明确数量；2248个检查披露事件中，595个仅为重复。事件数和配方数不同，详见逐事件文件。

按 Stage／方法／family 的完整分层、每个配方的首次登记延迟、各分支的知识前后状态均保存在结果目录。分支统计重用相同历史，单独汇总，不能与正式轨迹合并；其登记时间沿用真实历史前缀，不以冻结状态的时间冒充首次登记时间。

## RQ1：历史“没有发现”的重新判定

旧报告共37条轨迹含48个“必要配方未发现”的轨迹／配方对。只有1个可明确改判：Stage10 S2 的 `fiend_helm` 任务中，`fiend_alloy` 已公开而未登记，即1/48个缺失声明、1/37条含缺失声明的轨迹。Stage10 S1 的10条完整轨迹中此类终末改判为0；不能据此宣称多数完整任务失败都来自解析。

在50个冻结状态决策前，必要配方名称的 K1−K2 缺口均为0。另有1个原始遗漏状态在执行 `pick up iron_bar` 后获得必要配方，但旧分支计分器漏记；它属于当步新增反馈的解析问题，不能说该状态决策前已经知道这条配方。

逐动作有71次“必要配方已公开却在事实摘要中写为 UNKNOWN”；288次决策中存在未登记关系，但原始配方文本仍可在保存模型请求中访问。两者是时点计数，不能当作71或288个独立失败任务。

## 时间边界与 K3

全部2837个决策均与实际保存的模型请求和响应精确对齐。90条初始化历史、50个历史前缀均满足披露时间不晚于决策时间；Stage13 `case.history` 和 `pub.history` 在这些真实样本中未发生未来信息泄漏。解析器对超过 cutoff 的观察拒绝处理。

K2 的每步还通过原控制器恢复、使用原保存 proposal 执行 choose/observe，逐一核对下一步保存的配方结构。没有新模型推断。最后一个动作后的 K2 用同一冻结控制器重建并明确标注，不伪称另有保存快照。

## 正确性与限制

独立于抽取结果编写的35条真实反馈标注覆盖名称、数量、小数、工作台、制作成功无配方及负例，包含36条正关系：TP36、FP0、FN0；此测试集 precision=recall=1.0，数量与工作台标签全部一致。标注人为本轮同一分析者，非外部盲评；这不是对所有未来语言格式的准确率保证。

49项解析测试覆盖重复、名称升级、未知数量、冲突、普通叙述、模型猜测及未来输入。解析器冻结后未修改。完整回归另包含16项执行器测试和库存完成状态的真实反馈回归检查。

证据：[逐动作时间线](../../results/stage14/episode_timeline.jsonl.gz)、[逐配方摘要](../../results/stage14/episode_knowledge_summary.json)、[独立标注](../../results/stage14/parser_gold.json)、[时间审计](../../results/stage14/history_time_audit.json)、[请求对齐](../../results/stage14/request_context_audit.json)、[格式统计](../../results/stage14/disclosure_registration_by_format_action.json)。

本轮只证明信息当时有机会被获得或使用。没有开展修正解析器后的付费闭环，旧 R@40 完全不变。
''')
    sensitivity=table(['窗口','J0 有效／动作','J1 有效／动作','J2 有效／动作','J3 有效／动作','有机会的状态'],[
        [w]+[f"{m['both',w,j]['useful']}/50；{m['both',w,j]['actions']}" for j in ['J0','J1','J2','J3']]+[m['both',w,'J0']['all_observed_opportunities']] for w in [4,6,8]])
    clarity=table(['方法','明确意图状态','不完整意图状态','完成当前声明动作／意图','有效明确意图','材料损失状态','无关制作耗关键材料状态'],[
        [j]+[m['both',4,j][k] for k in ['explicit_intent','incomplete_exploration_intent','intent_complete','useful_explicit','environment_key_loss','unrelated_key_input_consumption']] for j in ['J0','J1','J2','J3']])
    strata=table(['同一组四方法均有明确意图','状态数','有效状态','动作'],[
        [r['method'],r['n'],r['useful'],r['actions']] for r in load(ROOT/'comparison_strata.json') if r['window']==4])
    costs=table(['方法','4步拒绝状态','4步动作拒绝数','关键材料消耗状态','有效状态每个对应总动作数'],[
        [j,m['both',4,j]['rejected'],m['both',4,j]['rejections'],m['both',4,j]['critical_consumption'],f"{m['both',4,j]['actions_per_useful']:.2f}"] for j in ['J0','J1','J2','J3']])
    fmet=load(ROOT/'family_metrics.json')
    ft=table(['family','J0 原始→统一','J1 原始→统一','J2 原始→统一','J3 原始→统一'],[
        [f]+[str(next(r['useful'] for r in fmet if (r['panel'],r['window'],r['method'],r['family'])==('original',4,j,f)))+'→'+str(next(r['useful'] for r in fmet if (r['panel'],r['window'],r['method'],r['family'])==('both',4,j,f))) for j in ['J0','J1','J2','J3']] for f in sorted(stats['formal']['family'])])
    put('统一多步意图评价.md',f'''# Stage14 统一多步意图评价

## 冻结规则

J0、J1、J2、J3 的原始选择和所有模型回答保持不变。只规范化它们当时表达的意图，并使用同一个公开执行器。没有重新采样 J2/J3，没有训练或修改排序器。

候选分为 Inspect、Acquire、Move、Craft-and-Inspect、Prepare-and-Explore，以及没有合理延伸的 Atomic。明确后续目标来自候选元数据、各方法自己的保存决策或 J2 原始 reasoning 的人工标注。相同动作但不同声明目标保留不同意图；不借用竞争方法的目标。原始第一动作逐项保留，即使非法也不能事后换成可行动作。

未说明后续目的的收取／移动只完成自身声明，单列意图不完整，不补出目标配方专用后缀。J2 的目的与其公开支持程度分别记录：声明某个产品不等于配方已知，未知配方仅可在已知条件下做有界真实尝试。制作后检查实际产物是所有方法统一的评价闭合规则，不自动证明原模型曾承诺检查。

执行器沿用冻结公开 K2、S1 的材料获取和批量规则；只走已知工作台路径，不另建排序器，不递归合成缺失材料。每次真实反馈后重新检查公开条件；失败不视为成功。真正制作出来并公开可访问的产物才能进入制作后检查。同上下文重复动作、不可满足条件、结束或最多8步都会停止，且不超过原40步任务剩余动作。

明确关系和数量只进入独立 K1 记录；本轮不将新解析器接入控制器规划。因而四组是“解析计分×执行粒度”的校准，不是新解析器在线决策的2×2消融，也不能外推闭环成功率。

## 四组主结果

有效指在该分支初始知识之外，至少新增一条评测器离线标注为目标必要的配方名称关系。数量补充、工作台补充和重复披露单独统计，不冒充新配方。

{panels}

原始指标逐状态、逐方法精确复现 Stage12。所有4步口径中有知识机会的状态仍为27/50。统一后，J0 从10升至14：解析计分单独修正1例，完整准备意图另修正3例。J1 从11升至17，说明解析与续行存在交互；不能只报告最终数字。J2/J3 没有从此次校准获得额外有效状态。

## 意图可比性、成本与风险

377个去重的状态／意图对中，323个明确、54个不完整；包括162个 Prepare、102个 Inspect、60个 Craft-and-Inspect、27个 Acquire、24个 Move、2个 Atomic。原363个候选全部覆盖，另保留相同原始动作所携带的不同明确目标。保存的所有60条 J2、60条 J3回答及原排名均未重采样；主表只使用 replicate=0。

{clarity}

完成当前声明不等于完成探索：例如不完整 Move 到达地点可以完成移动，但仍没有可比较的后续探索目标。明确意图的严格共同子集也单列：

{strata}

{costs}

动作成本包括失败、准备和后续检查。关键材料消耗、无关耗材、环境资源损失分开记录。生产用途正确的材料消耗不是自动判为损害；环境损失也不是自动归因于策略。逐候选保留 before/after、合法性、完成步数、停止原因与实际耗材。

## 6／8步敏感性与 family 分组

{sensitivity}

窗口变长也让机会集合从27增至30、31，不能把增长全归因于方法改进。每个窗口都使用同一个8步执行的前缀，没有重新选后缀或采样。

{ft}

每个family各5个主检查点，按family报告配对净变化，不把50个相似历史状态当独立样本，不报告伪精确的显著性。配对增益与损失均见 [family配对结果](../../results/stage14/paired_family_comparisons.json)。这些是已反复开发的旧任务，不是独立泛化测试。

## 真实重放与完成状态勘误

330个意图完整复用历史确定性前缀；47个缺失意图各在服务器执行两次，再由独立本地执行两次。每次169个动作，历史匹配前缀66项完全相同。缓存只在公开执行器先选定动作后查找相同完整动作前缀，不按原生收益挑轨迹。

冻结执行器的原始完成标签漏认了库存专用措辞 `I inspected my inventory.`，影响6个已缓存的单步检查。事后评分依据真实成功反馈纠正为已完成；保留原始停止标签和勘误文件。没有修改冻结执行器、动作、观察、原生状态或任何配方收益，也没有为此重跑实验。该修正防止把库存检查错误归入物理失败，已加真实反馈回归测试。

来源：[冻结协议](../../results/stage14/intent_protocol.json)、[意图与来源](../../results/stage14/candidate_intents.json)、[方法映射](../../results/stage14/intent_references.json)、[J2人工解释](../../results/stage14/J2_intent_annotations.json)、[逐窗口候选指标](../../results/stage14/candidate_window_metrics.jsonl.gz)、[知识事件](../../results/stage14/intent_knowledge_timeline.jsonl.gz)、[逐状态四组指标](../../results/stage14/calibrated_state_metrics.json)、[完成状态勘误](../../results/stage14/completion_scoring_amendment.json)。
''')
    old17=table(['原遗漏状态','family','F标签','校准4／6／8步有效'],[
        [f"[{r['state_id']}](states/{r['state_id']}.md)",r['family'],names(r['tags']),'/'.join(yn(r['both_useful'+str(w)]) for w in [4,6,8])] for r in states if r['was_original17_miss']])
    s1=sorted([r for r in full if r['stage']==10 and r['method']=='S1'],key=lambda r:r['family'])
    s1table=table(['family','历史成功','真正仍未公开的必要配方','全配方公开动作序号*','已知却从未制作成功','真实环境损失'],[
        [f"[{r['family']}](episodes/{r['task_id']}.md)",yn(r['success']),names(r['necessary_still_undisclosed']),r['all_necessary_public_after_action'] or '未齐',names(r['known_but_never_successfully_crafted']),'; '.join(f"index{x['index']}: {x['named_items']}" for x in r['actual_environment_resource_losses']) or '无'] for r in s1])
    witness=load(ROOT/'residual_witness_audit.json')
    wtable=table(['方法','family／目标','起点index','固定续行完成','动作数','分类'],[
        [r['method'],r['family']+'／'+r['target'],r['start_index'],yn(r['native_intent_complete']),len(r['native_actions']),r['classification']] for r in witness])
    put('残余失败机制分析.md',f'''# Stage14 残余失败机制分析

## 原17个遗漏的重分类

50个原冻结状态中，决策前必要配方名称的 K1−K2 缺口为0。原17个遗漏中，1个由当步数字反馈解析修正，3个由准备动作获得完整续行机会修正，共4/17个；剩余13个。不能继续把旧17例当作17例真实选择错误。

三个相同首步例为 `fiend_alloy_scale` 的收取合金、`chain_net` 与 `hellfire_bomb` 的收取铁粒。历史日志明确写了制作目标，且原完整轨迹最终分别在4、4、12个动作内完成对应链条。它们证明粒度偏差或延迟，不能直接证明永久放弃计划。

{old17}

剩余13例中，10例在已观察候选集合内确实错过了4步可获得的新必要关系，标为局部 F3；另3例在6步内可完成原合理方向，标为 F5 窗口限制＋F6，不强判为错误方向。标签允许重叠，但这里不把“检查库存”的成功动作误标成物理失败。局部方向收益不代表整条任务的最优性。

F1 是已有公开信息没有登记，F2 是原合理前缀被截短计分，F3 是条件化的局部方向遗漏，F4 是已开始的公开意图中断，F5 是实际材料／前提／窗口限制，F6 是证据尚不能隔离根因。逐例判断和原始反馈均保存在 [50状态归因](../../results/stage14/residual_states.json) 与 [连续性条件](../../results/stage14/continuity_audit.json)。

## 完整轨迹核对，保留成功任务

全部90条历史轨迹（39成功、51失败）均完成知识—动作—产物—资源审计。S1/E0/E1的30条是冻结参考组；其他方法的数据保留为历史参照，不伪称 S1 重复。

{s1table}

*此列从1计动作完成序号；`index` 从0计。已知但未制作不自动等于规划失败：物品可能已有、材料可能不足，或者公开信息是在任务后期才齐备。

`forged_blade_blank` 和 `brimite_blade_blank` 的 `wooden_rod` 关系确实没有公开；它们并非终末解析漏记。已有 `wood_strip` 关系却未制作，同时公开材料来源的 `scorched_plank` 在环境中损失。记录同时支持知识入口未推进和物理资源问题，不能只选一个解释。

`fiend_helm` 的目标配方确实仍未公开；已知的 `fiend_alloy`、`hellcoal_concentrate`、`stitched_panel`、`padded_lining` 没有成功生产。另有真实 cloth 损失和下面的内部额度中断，属于混合证据。

`hellfire_bomb` 在第29个动作后才有全部必要关系，剩11步；`hellcoal_concentrate` 和 `oil_flask` 没有成功制作，devil_oil 已发生环境损失。不能把“知道了却没成功”直接解释为自主工作流失效。

`hunter_gauntlets` 在第18个动作后已有全部必要关系，相关中间产物后来确实制作过，但目标未完成，并存在 sinew_cord 损失及制作数量失败。`chain_net` 是必须保留的正例：虽然链条长且有失败尝试，S1 最终在40步内成功，不能仅截取早期状态称其放弃计划。

90条逐轨迹分析见 [完整任务审计](../../results/stage14/full_episode_failure_audit.json) 和本目录 episodes 页面；它们链接原 Stage10/11 保存反馈，不使用新模型回答。没有证明资源损失一定是不可避免的，也没有证明任务总体已经无解。

## 严格连续性与必要补充验证

原50个状态没有满足完整严格条件的 F4。为避免据此漏掉完整轨迹中的未完成意图，对参考30条轨迹中69个首次“任务×明确探索目标”记录做全量检查：46个在原轨迹中闭合，23个未闭合。1个保存的准备目标已被另一产品的制作覆盖，实际未接受，不计 F4；其余22个全部进入冻结补充计划，不按新原生收益筛选。

从旧可信初始化快照精确重放原历史前缀，恢复22个检查点；没有新增任务、family、种子或模型回答。主比较仍是原50个状态。补充分支在剩余40步内最多8步，执行器没有变化；服务器双回放、本地独立恢复前缀与双回放均一致，每次86动作。

{wtable}

22条中8条固定续行完成、11条材料／公开前提受阻、3条到8步窗口仍未闭合。完成的8条中5条在原轨迹转向前已出现新数量、工作台或前提信息，严格归因为 F6／条件变化，不能凭反事实成功就认定无故中断。

另外3条来自 `fiend_helm` 的 S1/E0/E1，均从 index18 的 `enter cellar` 开始，目标为 `stitched_panel`。原轨迹随后转向，未完成该链。固定续行是：

```text
enter cellar
store 1 bandage_roll inventory
store 1 sinew_cord inventory
craft 2 stitched_panel
enter courtyard
craft 2 stitched_panel
inspect stitched_panel
```

第一次制作以真实反馈发现工作台条件，之后按已知路线到 courtyard 并成功。原转向前第一步无新配方／数量／站点、无该步资源损失或紧急风险；下一步真实可行。因此保存为 F4 的“内部配额边界中断”子类。三个历史方法共享同一个物理状态、同一family，不是三个独立机制案例。

其公开触发条件清楚：保存决策的 exploration.spent=18、limit=18，下一步探索机制退出。它是已知策略配额引发的中断，不是无法解释的潜在记忆故障。这里仍有原任务22个环境动作，但固定续行需7步，4／6步敏感性窗口不足。该续行只补充必要配方 `stitched_panel` 的数量，新增必要配方名称为0；制作了真实中间物品，未证明完整 `fiend_helm` 任务因此成功。

若将“无故中断”严格限定为排除已有配额解释，则这样的无解释 F4 为0；公开可行链的配额边界中断记录为3、独立family／物理状态均为1。两种口径均不能支持跨多个任务反复出现且超出普通确定性续接能力的问题。

补充证据：[22条完整原生反馈](../../results/stage14/residual_native_branches.jsonl.gz)、[八项判定条件](../../results/stage14/residual_witness_audit.json)、[69条最终分类](../../results/stage14/full_reference_commitments_final.json)。

## 科研判断

本轮结论为 **NO-GO：不开发新探索／工作流机制，不启动付费闭环**。这是研发决策，不是声称所有剩余失败已经被完全解释。全任务层面的因果改进和跨family系统性仍为 INCONCLUSIVE。

已确认解析和评价基础问题，但它们仅修正原17个局部遗漏中的4个，不能说多数失败已被工程问题解释。仍有方向选择、信息利用、数量与资源瓶颈；唯一清楚的配额中断机制由冻结普通续接即可处理，且没有跨family重复证据。今后若研究该问题，应先把普通确定性续接作为强基线；本轮到此停止。
''')
    put('实验总报告.md',f'''# Stage14 实验总报告

**结论：NO-GO，不启动新算法或付费闭环。** 已完成公开知识校准、统一多步意图评价，以及真实残余失败核对。基线为 Stage13 `80d8009`，Stage10 S1 冻结不变。

## 三个研究问题

| 问题 | 本轮证据 |
| --- | --- |
| RQ1：没有发现是否只是没登记？ | 90条正式轨迹中，旧48个终末必要配方缺失声明仅1个改判（S2/fiend_helm 的 fiend_alloy）；S1 的终末改判为0。314个一般关系／轨迹对遗漏、1632个数量缺口确实存在。 |
| RQ2：错误方向是否被不公平截短？ | 原17个局部遗漏，1个解析计分问题、3个有明确目标的准备动作被截短，共修正4个。S1有效新必要关系状态从10/50到14/50。 |
| RQ3：是否需要新的连续性机制？ | 主50状态无严格F4；完整轨迹补充发现3条内部18次探索额度边界中断，均为fiend_helm同一物理状态。普通固定续接7步可完成，仅新增必要数量信息。没有跨family、超出确定性续接能力的证据。 |

## 四组主结果

数字是“获得新的必要配方的状态数／50；环境动作总数”，不是任务成功率。

{panels}

全部统一后6／8步时 J0为18／19，J1为21／23，J2均4，J3均6；机会状态也从27增至30／31。完整分层、成本和负例见 [统一多步意图评价](统一多步意图评价.md)。

解析校正只改变 K1 计分，规划仍使用历史 K2。未把新解析器合入 S1，未改历史 R@40，未进行校正后在线因果验证。对完整任务成功和系统性泛化的判断仍是 INCONCLUSIVE。

## 范围与验证

- 原10个 robot_kingdom family；全部90条正式历史轨迹、2837动作、50个主冻结状态；历史363＋70条分支全部审计。
- 377个统一意图，330个完整复用；47个新意图分支每次169动作。
- 22个完整轨迹残余验证分支每次86动作；原历史前缀逐观察复原。
- 合计69个新原生分支，服务器各执行两次，本地独立各执行两次，状态、反馈、目标及资源记录逐字段一致。每次255动作；跨四次执行共1020动作，另有历史前缀恢复的零API动作。
- 全部模型请求2837/2837对齐，时间审计通过，未来信息泄漏0。35条独立编写的真实反馈标注，关系TP36／FP0／FN0；只适用于该测试集。
- 解析49项、执行器16项、库存完成状态1项以及149项既有回归均通过；详见测试XML与发布检查。
- 2185个旧文件受哈希保护；冻结解析器／执行器未改变。库存特殊措辞只作完成状态统计勘误，已完整披露。
- **新增LLM调用0、模型费用0美元、付费闭环0；累计已记录模型费用仍为36.888925758美元。**

## 交付索引

[公开知识解析审计](公开知识解析审计.md)；[统一多步意图评价](统一多步意图评价.md)；[残余失败机制分析](残余失败机制分析.md)；[复现指南](复现指南.md)。

原始证据与完整机器可读统计保存在 [results/stage14](../../results/stage14)，自研代码在 [scar_stage14](../../scar_stage14)。所有50个主状态与90条完整轨迹均有可追踪页面，不只保留正例。没有上传引擎源码、模型、虚拟环境或密钥。
''')
    put('复现指南.md','''# Stage14 复现指南

基线：Stage13 `80d800968c33c61a492227e72a332999c40bc022`。Python3.12；外置 AgentOdyssey 引擎固定上游提交 `248430692a9d4a61d38c6c03ab2126287faaf450`。依赖和引擎放在仓库之外。仓库中的压缩快照是本项目生成的实验状态，仅使用受哈希保护的可信文件。

## 已冻结内容

`parser_freeze.json` 保护统一解析器与人工金标；`executor_freeze.json` 保护意图规范化、人工J2解释、公开输入、执行器与协议；`replay_freeze.json` 保护47条补充分支选择；`residual_replay_freeze.json` 保护22条完整轨迹残余验证。冻结后未用新收益调策略。分析、报告、发布检查是独立事后代码；其最终版本由 artifact_manifest 保护。

`prior_manifest.json` 保护2185个旧文件。`completion_scoring_amendment.json` 披露库存成功措辞的完成标签修正，影响6个缓存分支的状态标签，行为和知识分数不变。不能删 freeze 重调规则然后声称事前冻结。

## 无API复算

在仓库根目录执行，替换外置引擎路径：

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export AGENTODYSSEY_ROOT=/path/to/external/agentodyssey
python -m pytest tests/test_stage7.py tests/test_stage8.py tests/test_stage9.py tests/test_stage10.py tests/test_stage11.py tests/test_stage12.py tests/test_unknown17.py tests/test_sequence.py scar_stage13/test_policy.py scar_stage13/test_diagnostics.py scar_stage14 -q
python -m scar_stage14.audit
python -m scar_stage14.native --verify results/stage14/native_intent_branches.jsonl.gz --output /tmp/stage14-intent-verify --workers 8
python -m scar_stage14.verify_checkpoints
python -m scar_stage14.residual_replay run --verify results/stage14/residual_native_branches.jsonl.gz --output /tmp/stage14-residual-verify
python -m scar_stage14.analyze_intents
python -m scar_stage14.residual
python -m scar_stage14.analyze_residual_witnesses
python -m scar_stage14.report
python -m scar_stage14.publication --verify
```

`--verify` 仅将新产生结果逐字段对照已发布分支，不覆盖分支证据。每个验证调用内部执行两次。worker 禁用网络 socket.connect，不需要模型凭据。服务器路径 `/root/scar_workspace/project`，Python `/root/scar_workspace/venv/bin/python`；本地独立环境在 `/mnt/Space0/scar_dependencies`。

`verify_checkpoints` 只按保存的真实历史动作恢复22个前缀，并断言每条观察及最终物理状态一致，不覆盖已发布文件；其快照是衍生状态，不是新增任务或种子。cloudpickle 含临时 run_dir/config_path，所以双机独立生成的快照字节哈希可以不同；物理状态、反馈、动作效果与随机状态必须一致。双机各自的序列化哈希及共同物理摘要均保存在 server_verification。发布快照统一采用服务器原始文件。若只需复算指标，可跳过原生验证，直接使用已发布分支运行 analysis 链。

一次性准备器 `setup`、`prepare_intents`、`replay`、`residual_replay plan/materialize` 已完成，已发布版本不应再次运行；materialize 是最初的冻结一次性写入器，不适用于字节不稳定的跨目录重新生成，复核请使用上面的只读工具。复现实验不需要重新支付API或重跑旧363条分支。

## 数据定位

- `episode_timeline.jsonl.gz`：2837行真实决策，K1/K2前后、K3请求来源、反馈及时间界限。
- `episode_knowledge_events.jsonl.gz`：首次、重复、数量和工作台升级的原始证据。
- `branch_knowledge_timeline.jsonl.gz`：旧363＋70条分支的逐动作校准。
- `candidate_intents.json`、`intent_references.json`：377个统一意图与所有候选／方法／重复回答映射。
- `reused_intent_branches.jsonl.gz`：330个缓存前缀及来源；`native_intent_branches.jsonl.gz`：47个新真实分支。
- `intent_knowledge_timeline.jsonl.gz`、`candidate_window_metrics.jsonl.gz`、`calibrated_state_metrics.json`：4／6／8窗口及四组计分。
- `residual_states.json`、`continuity_audit.json`：原50状态、原17遗漏、连续性条件。
- `full_episode_failure_audit.json`：全部90个成功／失败任务；`full_reference_commitments_final.json`：69条首次任务／目标记录最终分类。
- `residual_native_branches.jsonl.gz`、`residual_witness_audit.json`：22条残余见证与判定条件。
- `native_intent_branches.jsonl.gz.verification.json`、`local_native.verification.json`、`residual_native_branches.jsonl.gz.verification.json`、`local_residual.verification.json`：双机各两次原生比对。
- `artifact_manifest.json`、`publication_checks.json`、`server_verification.json`：历史保护、最终内容哈希与双机核对。

K1/K2新增关系在分支内按初始集合差去重；每步字段可能是累计集合，不能累加成新增总数。family分组是统计单位，方法重复、状态与分支均相关。所有“必要”标签只在选定动作后由评测器用于计分；意图模块只接收白名单公开状态。公开数值缺口与真实资源损失不能混为配方未知。

本轮不提供修正后在线成功率；新机制研发判断为 NO-GO。不运行下一阶段算法、付费闭环或隐含自动监控。
''')
    # Complete drilldowns: all 50 states and all 90 formal episodes.
    source_states={s['state_id']:s for s in load(OLD/'states.json')}
    ct={r['state_id']:r for r in load(ROOT/'continuity_audit.json')}
    sr=load(ROOT/'calibrated_state_metrics.json')
    for r in states:
        sid=r['state_id'];s=source_states[sid];c=ct[sid]
        t=table(['口径','J0新必要配方','J1','J2','J3'],[[LABEL[p]]+[names(next(x['new_necessary'] for x in sr if (x['state_id'],x['panel'],x['window'],x['method'])==(sid,p,4,j))) for j in ['J0','J1','J2','J3']] for p in LABEL])
        put('states/'+sid+'.md',f'''# {sid}：{r['family']}

原 Stage{r['source_stage']} {r['source_method']}，源任务 `{s['source_task']}`，index={r['source_index']}，剩余动作{s['remaining_actions']}。原始J0动作 `{s['rule_actions']['J0']}`；旧17遗漏：{yn(r['was_original17_miss'])}。

{t}

标签：{names(r['tags'])}。4／6／8步有效：{yn(r['both_useful4'])}／{yn(r['both_useful6'])}／{yn(r['both_useful8'])}。决策前必要K1−K2：{names(r['necessary_K1_not_K2_before'])}。

原轨迹目标闭合：{json.dumps(c['actual_closure'],ensure_ascii=False)}。

归因证据：

```json
{json.dumps(r['evidence'],ensure_ascii=False,indent=2)}
```

连续性逐条件：

```json
{json.dumps(c['gates'],ensure_ascii=False,indent=2)}
```

原始公开观察：

```text
{s['observation']['text']}
```

全部分支前后观察见 [原生意图结果](../../../results/stage14/native_intent_branches.jsonl.gz) 或 [复用结果](../../../results/stage14/reused_intent_branches.jsonl.gz)，以 state_id／intent_id 连接。首次信息和升级见 [知识时间线](../../../results/stage14/intent_knowledge_timeline.jsonl.gz)。
''')
    epmap={ep['task_id']:ep for _,_,ep,_,_ in episodes()}
    timeline=defaultdict(list)
    for r in records(ROOT/'episode_timeline.jsonl.gz'):timeline[r['task_id']].append(r)
    for r in full:
        ep=epmap[r['task_id']];tl=timeline[r['task_id']]
        rows=[[a['index'],f"`{a['executed_action']}`",names(b['K1_delta']['new_relations']),names(b['K1_delta']['quantity_updates']),names(b['K2_new_registered_relations']),a['feedback']] for a,b in zip(ep['rows'],tl)]
        put('episodes/'+r['task_id']+'.md',f'''# Stage{r['stage']} {r['method']}：{r['family']}

历史成功：{yn(r['success'])}；动作：{r['steps']}；本轮未重新运行闭环。原始来源 [{r['source_file']}](../../../{r['source_file']})。

终末真实未公开必要配方：{names(r['necessary_still_undisclosed'])}；历史缺失改判：{names(r['historical_missing_reclassified'])}；已知却没有成功制作过：{names(r['known_but_never_successfully_crafted'])}。这些是观察事实，不单独证明因果。

真实资源损失：

```json
{json.dumps(r['actual_environment_resource_losses'],ensure_ascii=False,indent=2)}
```

逐动作知识与原始反馈（index从0计）：

{table(['index','动作','新公开关系','新数量','新登记关系','原始反馈'],rows)}
''')
    print({'reports':5,'state_pages':50,'episode_pages':90})

if __name__=='__main__':main()
