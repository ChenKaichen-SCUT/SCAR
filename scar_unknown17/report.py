"""Chinese evidence report from immutable raw results; no model calls."""
import argparse
from collections import Counter
import json
from pathlib import Path
from scar.io import atomic_json

OUT=Path('results/unknown17');REPORT=Path('reports/unknown17')
LABELS={'ShortTermMemoryAgent':'STM','ResourceFIFO':'FIFO','FIFOExplore':'FIFO + 定向探索',
    'FIFOBatch':'FIFO + 批量经验','FIFOFixedBatch':'FIFO + 固定批量','FIFOFacts':'FIFO + 事实摘要',
    'STMFacts':'STM + 事实摘要','FIFOCombined':'FIFO-Combined','STMFormatControl':'STM 同格式对照'}


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
        ['| '+' | '.join(str(x).replace('\n','<br>') for x in row)+' |' for row in rows])+'\n'


def pct(x):return 'NA' if x is None else f'{100*x:.1f}%'
def num(x,d=2):return 'NA' if x is None else f'{x:.{d}f}'


def attribution():
    REPORT.mkdir(parents=True,exist_ok=True)
    summary=json.loads((OUT/'attribution_summary.json').read_text());parts=[
        '# Stage 6：17 个未示范制作任务逐例归因\n',
        '对象为 Stage 5 提交 `2496b60` 的全部 17 个 interaction_discovery 制作 family。五种旧方法共 85 条实际轨迹全部重放，动作与下一公开观察完全匹配。原始数据不变。所有本节实验均为零 API。\n',
        '每例真实配方、原料量、工作台和恢复见证仅供离线评估，不注入新策略。初始物理目标均为持有两件目标；已有的一件不能算新恢复。\n',
        'F1 表示缺少公开可获得的必要配方名称；F2 表示已观察但未利用的候选现象；F3 表示数量/取整问题；F4 为资源/手位/地点问题；F5 为重复/子目标执行现象；F6 只记录实际候选中没有出现，不能证明动作生成器根本无法生成；F7 为格式/参数拒绝；F8 为截止或解释不足。F2/F5/F6 标签通常只是待验证假设。\n',
        '主要瓶颈按旧 FIFO 归类，不能把最终缺少配方直接当作整局失败的充分原因。最早拒绝动作也不一定是最早不可逆偏离；未找到能证明“最早且必要”的事件时明确保持未识别。真实同状态反事实的结论范围单独列出。\n',
        table(['游戏','目标','STM / Simple / V3 / FIFO / SRP 成功','FIFO 主要可观测瓶颈','FIFO 未发现关键配方','有批量分支差异的状态'],[
            [c['game'],c['goal']['name'],' / '.join('1' if c['methods'][m]['recovered'] else '0' for m in ['ShortTermMemoryAgent','SimpleFailureRecovery','SCARV3Agent','ResourceFIFO','SRP']),
             c['methods']['ResourceFIFO']['primary_observable_bottleneck'],', '.join(c['methods']['ResourceFIFO']['missing_key_recipes']) or '无',c['batch_suffix_outcome_changes']]
            for c in summary])]
    for c in summary:
        detail=json.loads((OUT/'families'/f'{c["case_id"]}.json').read_text());fifo=detail['methods']['ResourceFIFO']
        truth=detail['hidden_truth_evaluation_only'];initial=detail['initial_public_knowledge']['recipes']
        parts += [f'\n## {c["goal"]["name"]}（{c["game"]}）\n',f'family：`{c["case_id"]}`。独立见证 {len(detail["witness"])} 步，两次重放均达到物理目标。\n',
            '**真实制作链（仅评测）：**\n'+ '\n'.join(f'- {n} ← '+', '.join(f'{q:g} {x}' for x,q in r['ingredients'].items())+'；地点要求：'+', '.join(r['stations']) for n,r in truth.items())+'\n',
            '初始公开配方事实：`'+json.dumps(initial,ensure_ascii=False)+'`。只有工作台元数据、材料表为空的条目仍是 UNKNOWN。\n',
            '**公开可发现性：** '+ '；'.join(f'见证状态 {p["witness_index"]} 检查 {p["object"]} 得到 '+', '.join(p['key_recipe_gain']) for p in detail['public_discovery_probes'])+'。每个信息探针均与同状态 wait 比较并独立重放两次；抵达该状态使用离线见证，因此只证明信息可获得，不证明 Agent 能自行到达。\n',
            table(['旧方法','恢复','已发现关键配方','仍缺少','最早观测拒绝（索引从 0）'],[
                [LABELS.get(m,m),v['recovered'],', '.join(v['known_key_recipes']) or '无',', '.join(v['missing_key_recipes']) or '无',
                 '无拒绝记录' if v['earliest_observed_rejection'] is None else str(v['earliest_observed_rejection']['index'])+': '+v['earliest_observed_rejection']['action']]
                for m,v in detail['methods'].items()]),
            f'FIFO 共执行 {len(fifo["information_actions"])} 次检查，{len(fifo["resource_repeats"])} 次相同资源配置下的重复动作；存在 {len(fifo["missed_ready_goal_actions"])} 个一份最终配方材料与工作台同时具备而当步没有执行最终目标的机会。后者仍需收取产物，不自动等于可当步完成。\n',
            'FIFO 已知却未制作的节点：'+(', '.join(fifo['known_but_never_crafted']) or '无')+'；实际候选中未出现制作的已知节点：'+(', '.join(fifo['candidate_absence']) or '无')+'。已有物资可能免去部分制作，不能直接把这些列表当作错误。\n',
            '**同状态数量反事实：**\n'+table(['见证索引','中间/目标','craft 1 后固定余下见证','craft 2 后固定余下见证','craft 4 后固定余下见证'],[
                [b['witness_index'],b['target']]+[v['goal'] for v in b['variants']] for b in detail['batch_branches']]),
            '数量分支只替换一项请求数量，其余见证动作完全相同，且各分支独立重放两次。分支成功差异证明该固定续行下的局部数量效应；不能直接当作自主 Agent 的成功率。若 1/2/4 均失败，原见证也可能需要更大单批，不能据此声称状态不可恢复。\n',
            '简单修复候选：根据未知配方连接选择公开原料/产物检查；记录已发生的信息并交给基础模型；比较有限批量以减少取整损耗；减少检查、搬运与最后收取开销。哪一项真正改善整局，必须看独立的正式闭环与后续行为证据。\n',
            f'完整动作、反馈、各步材料真值、最终缺失、状态路径/hash：[`{c["case_id"]}.json`](../../results/unknown17/families/{c["case_id"]}.json)。\n']
    parts += ['\n## 三个重点案例的解释边界\n',
        '`bandage_roll`：在旧 SRP 索引 6 的同一实际状态，craft 1 / craft 2 sinew_cord 使用相同后续动作，目标结果为失败/成功。该差异可由固定批量解释，未证明需要新的学习器。\n',
        '`brass_blank`：初始失败只公开 bench 地点条件，未公开其材料。检查已有 blank 披露下游 brass_key；检查 star_scrap 披露 rustbar。真实制作并检查 rustbar 可以补上通往 blank 的连接。必须区分“有一条公开反馈路径”与“有限探索规则可靠选中这条路径”。\n',
        '`machete` 属于已示范组，不放进本轮 17-family 分母。旧 SRP 截止时已经制出新产物，额外一次 store 即达目标。该零 API 分支复验成功；正式结果仍失败，没有追加任何模型步骤。\n',
        'Stage 5 已有 89-family 旧归因文件全部读取，用于复用证据分级方法，没有把旧表的标签当作本轮 17 例答案。\n']
    (REPORT/'逐例失败归因.md').write_text('\n'.join(parts))


def final_report():
    attribution();groups=json.loads((OUT/'method_metrics.json').read_text());g=groups['all']
    ver=json.loads((OUT/'verification.json').read_text());pairs=json.loads((OUT/'paired_comparisons.json').read_text())
    families=json.loads((OUT/'family_comparison.json').read_text());evidence=json.loads((OUT/'success_evidence.json').read_text())
    targeted=json.loads((OUT/'targeted_checks_summary.json').read_text());overhead=json.loads((OUT/'mechanism_overhead.json').read_text())['methods']
    quantity=json.loads((OUT/'engine_mechanisms.json').read_text());judgment=json.loads((OUT/'research_judgment.json').read_text())
    parts=['# SCAR Stage 6：未知制作任务的简单机制验证\n',
        f'本轮状态：**完整**，原定 8 方法 × 17 family = 136 组，另加 17 组同记忆格式对照，总计 **{ver["episodes_replayed"]} 组**。研究判断：**{judgment["verdict"]}**。\n',
        judgment['reason']+'\n',
        '## 1. 研究设计与授权范围\n',
        '以 Stage 5 提交 `2496b60d52767e3915a62fe60f874902fd68a489` 为固定起点，只研究原 17 个未示范制作案例。它们已经被分析过，本轮是探索性机制验证，不是新的泛化测试。原 368 个跟踪文件全部保持字节不变。\n',
        '每个 family 的物理状态、公开历史、恢复目标和一个环境种子完全相同；40 个环境动作封顶，无失败后额外提示、加步或重试，无新的 200/500 步游戏。DeepSeek Flash、非思考模式、temperature=0.7、max_tokens=768、STM 窗口 5 与上轮一致。远端模型采样没有可保证一致的种子，因此相同初态不等于相同模型输出。\n',
        '原 STM 与 FIFO 在本批重新调用模型实跑；旧 SRP、V3 仅保留历史参照，没有混入新结果。新增算法不读取游戏文件、配方表、见证或 family ID，策略导入边界和物品专属例外检查通过。\n',
        '## 2. 全部旧失败的归因与精确引擎行为\n',
        '完整 [17-family 逐例失败归因](逐例失败归因.md) 包含真实制作链、初始知识、全部五种旧方法的信息动作、已知/未知节点、资源与动作证据、同状态反事实和证据强度。85 条旧轨迹精确重放；旧 FIFO 主要可观测分类为 F1 14 例、F3 2 例、F8 1 例。这不是互斥的完整因果分解。\n',
        f'68 个制作前状态执行 0/1/2/4 数量的原动作规则，共 {quantity["action_dispatches"]} 次零 API 调度；其中 {quantity["same_consumption_more_output_pairs"]} 个状态出现 craft 2 比 craft 1 产出更多而实际材料消耗相同，{quantity["clipping_examples"]} 个候选出现资源不足导致请求数量截断。\n',
        '原引擎先检查至少一份名义配方的材料与工作台，再按可用材料截断制作数；依次从手中、随身背包、手持容器扣除材料，并对每处剩余数量向下取整。产物落在地面。不能用普通浮点配方减法代替实际引擎执行；也不能把名义 0.5 消耗自动当作实际只减少 0.5 件。\n',
        '公开 inspect 一般披露该物品的下游产物及材料名称，不披露数量权重。未知配方的发现可能要求先制作并检查中间产物。离线见证探针共找到 94 个必要配方信息增益点；这证明信息路径存在，并不保证有限公开探索能自主选择它。\n',
        '## 3. 独立简单方法和冻结范围\n',
        table(['方法','唯一主要改动'],[
            ['FIFO + 定向探索','复用原 FIFO；按未知节点检查公开物品与已产中间物，最多 18 个定向动作、4 次前向试制，重复探针有记录。'],
            ['FIFO + 固定批量','按观察缺量选择；中间物至少请求 2 份，最多 4，尚未保护所有后续用途；批量选择不查询新增经验表；原 FIFO 的资源状态更新照旧。'],
            ['FIFO + 批量经验','固定启发式起步；保存真实公开前后数量。仅在完全相同公开物资上下文有经验时选择已有低单位消耗样本，其他情况 UNKNOWN。'],
            ['FIFO + 事实摘要','不改 FIFO 队列决策规则；把有来源与时效标记的事实追加给相同 STM 模型调用。'],
            ['STM + 事实摘要','基础模型直接行动，追加同一摘要，没有 FIFO 决策覆盖。'],
            ['FIFO-Combined','组合上述公开探索、批量经验与事实摘要，不增加搜索器或模型调用。']]),
        '所有 FIFO 版本仍继承 Stage 5 资源表根据公开制作前后变化更新经验数量的逻辑；“固定批量”指没有新增上下文经验选择模块，不表示它完全没有状态或经验更新。新增批量模块是否生效单独计数。固定批量只是本轮的一条有限启发式，不能代表所有合理的简单批量策略，过量制作反例表明它仍需改进。摘要上限 48 条、6,000 字符，分类轮转避免大量配方挤掉效果、位置、失败条件和不确定性。位置与容器内容标记为历史观察；缺失数量保持 UNKNOWN。数量效果是 craft 到后续 inspect 的经验差值，可能混入环境步骤效应，不伪装成永恒的线性配方。\n',
        '协议的 batch_candidates=[1,2,4] 与冻结实现边界有一处小的不一致：缺量启发式实际允许 1–4，观察缺量为 3 时也可取 3。本批所有新增批量模块实际都未请求 3，因此未影响本次结果；离线审计仍纳入每步实际请求数量。此处明确保留协议与代码差异，不事后修改冻结文件。\n',
        '原八种方法在任何正式调用前冻结（freeze.json）。代码核对后发现 STM+摘要沿用了结构方法的“观察+提议+执行”记忆格式，原 STM 则保留模型解释。为避免把格式差异归因于摘要，追加 **STM 同格式对照**，只关闭摘要，其他逻辑完全相同；独立冻结记录在 format_control_freeze.json。该增加基于源码检查，未按正式成绩调参，原八种方法代码与结果未改、未重跑。摘要的独立比较应优先看 STMFacts−STMFormatControl。\n',
        '10 项新增语义单元测试通过；另复验 8 项 Stage 5 测试。全部方法零 API 运行器/状态保存检查通过，85 条完整旧历史的摘要检查通过。局部验证和 17 条 12 步确定性探针均不计入正式恢复率。\n',
        '## 4. 新批次闭环结果\n',
        table(['方法','成功/17','R@10','R@20','R@40','成功平均步数','费用 $','所有尝试费用/成功 $','token/成功'],[
            [LABELS[m],f'{r["successes"]}/17',pct(r['recovery_at_10']),pct(r['recovery_at_20']),pct(r['recovery_at_40']),num(r['mean_success_steps']),num(r['cost_usd'],6),num(r['cost_per_success_all_attempts'],4),num(r['tokens_per_success_all_attempts'],0)] for m,r in g.items()]),
        '未恢复且正常完成的轨迹按 40 步截尾；格式中止保留实际步数与花费，并计入失败分母；基础设施或额度中断不伪装成方法失败。每例原始观察、模型响应、提议/执行动作、目标真值、关键事件、次数和费用在 trajectories_*.jsonl.gz 与 episode_metrics.json。\n',
        table(['方法','saltglass（4）','quarantine（3）','robot_kingdom（10）'],[[LABELS[m]]+[str(groups[x][m]['successes'])+'/'+str(groups[x][m]['n']) for x in ['saltglass','quarantine','robot_kingdom']] for m in g]),
        table(['方法','旧 FIFO F1（14）','旧 FIFO F3（2）','旧 FIFO F8（1）'],[[LABELS[m]]+[str(groups['old_FIFO_'+x][m]['successes'])+'/'+str(groups['old_FIFO_'+x][m]['n']) for x in ['F1','F3','F8']] for m in g]),
        '分组来自正式运行前旧轨迹的固定可观测标签，只作解释性分层，不是独立随机化机制组。\n',
        '## 5. 配对比较与小样本限制\n',
        table(['前者−后者','family 均值差','family bootstrap 95%','仅前者成功','仅后者成功'],[
            [LABELS[p['a']]+' − '+LABELS[p['b']],pct(p['family']['difference']),str([round(100*v,1) for v in p['family']['ci95']])+' pp',len(p['a_only']),len(p['b_only'])] for p in pairs]),
        '以 17 个 family 为配对单位，10,000 次 bootstrap；来源游戏只有三个，且 10/17 来自 robot_kingdom。另存按来源簇的敏感性结果。不能把动作数作为独立样本，也不能用上述探索性区间声称稳定统计显著性或跨游戏普遍优势。模型采样、轨迹反馈和上下文不同，正负配对差不自动等于某机制的因果作用。\n',
        '## 6. 规则、数量、记忆与执行指标\n',
        table(['方法','关键配方发现率','必要中间配方发现率','定向动作数','无即时关键规则增益','数量非支配率','数量预测数 / MAE'],[
            [LABELS[m],pct(r['key_discovery_rate']),pct(r['intermediate_discovery_rate']),r['directed_information_actions'],pct(r['no_immediate_key_gain_rate']),pct(r['quantity_nondominated_rate']),str(r['quantity_prediction_count'])+' / '+num(r['quantity_prediction_mae'])] for m,r in g.items()]),
        '工作台信息而无材料名称不算已知配方。“无即时增益”包含运输与试制的延迟信息价值，不等于无用探索。第一次有效发现、每例新规则和试制次数逐条入表。数量非支配率仅在至少一个候选能实际产出的状态计算：若另一候选产出不少、每种实际输入消耗不多且至少一项更好，原选择被局部支配。这是可核验的数量正确性代理，不是保证整局最优的批量标签。\n',
        '预测误差只计算确有相同公开上下文经验、实际给出消耗预测的动作；UNKNOWN 不按零误差处理。覆盖率低或为零时，不能宣称效果更新已有效学习。固定批量比较是本轮必要对照。原动作规则调度与完整环境步骤分开计数，避免再次把取整损耗误记为环境销毁。\n',
        table(['方法','已观察关键事实保留召回','摘要保留召回','可检查摘要事实正确率','重复检查','摘要字符累计','摘要 token 代理'],[
            [LABELS[m],pct(r['retention_recall']),pct(r['summary_retention_recall']),pct(r['summary_fact_precision']),r['repeated_inspection_count'],r['summary_characters_total'],num(r['summary_token_proxy_total'],0)] for m,r in g.items()]),
        table(['方法','输入 token','输出 token','API 调用','同资源/同反馈重复检查','前向试制数','试制动作 API 费用 $'],[[LABELS[m],r['input_tokens'],r['output_tokens'],r['api_calls'],overhead[m].get('same_resource_same_feedback_reinspections',0),overhead[m].get('forward_trial_actions',0),num(overhead[m].get('forward_trial_api_cost_usd',0),5)] for m,r in g.items()]),
        '定向探索单项的 47 次前向试制与组合方法的 44 次试制有真实资源和 API 成本，逐例消耗物品列在 mechanism_overhead.json；没有把失败试制当作免费查询。重复检查的更窄计数要求同一资源配置、同一对象、相同反馈，但仍不证明确认行为完全无决策价值。\n',
        '保留召回衡量决策时的公开文本/摘要/FIFO 表中是否还能找到已观察必要配方，不能直接测量模型内部知识。正确率只覆盖可核对的配方名称、当前字段、目标持有量下界与容器访问；历史状态被模型误用的完整次数无法从文本轨迹可靠识别，记 NA，不能声称为零。重复 inspect 可能有更新容器信息的正当作用。\n',
        '供应商未提供分段 token 计数。额外摘要长度按字符/4 给出明确标记的 token 代理；所有真正计费的输入/输出 token 均完整记账。不能把代理当作 DeepSeek tokenizer 的精确增量。\n',
        table(['方法','子目标完成','材料积累','手位拒绝','资源循环','合法→拒绝覆盖','当步可完成目标却被覆盖','环境步骤净减少'],[
            [LABELS[m],pct(r['family_mean_subgoal_completion']),pct(r['family_mean_material_accumulation']),r['hand_capacity_rejections'],r['resource_cycles'],r['legal_to_rejected'],r['harmful_goal_overrides'],r['resource_destruction_steps']] for m,r in g.items()]),
        '环境步骤净减少包含原生衰减/步骤规则消耗，不等于永久不可恢复；循环也可能带来信息收益。合法→拒绝及当步目标覆盖由同一起点的真实提议动作分支计算，不能推断长期效用。\n',
        '## 7. 逐 family 结果与成功机制证据\n',
        table(['目标','本轮成功方法','组合独有','全部失败'],[[f['target'],', '.join(LABELS[m] for m in f['winners']) or '无',f['combined_only'],f['all_fail']] for f in families]),
        '完整 success_evidence.json 为每个成功轨迹列出信息发现→后续制作链、摘要事实和局部替换。选择规则预先固定为首个数量覆盖、首个有关键增益的定向检查或前向制作；每个最多两条局部检验，未只保存支持结果的分支。替换后使用同一实际余下动作，并各自独立重放两次，始终保持原剩余步数。\n',
        table(['目标 / 方法','定向发现后实际制作的关键节点','局部动作替换使成功变失败'],[
            [next(f['target'] for f in families if f['case_id']==e['case_id'])+' / '+LABELS[e['method']],
             ', '.join(x['recipe'] for x in e['directed_discovered_then_crafted']) or '无记录',
             ', '.join(f'{x["kind"]}@{x["index"]}' for x in e['checks'] if x['actual_reaches_goal_alternative_does_not']) or '无'] for e in evidence]),
        f'补充检查保留上述首轮结果，再枚举所有成功轨迹中真正产出物品的数量覆盖，以及所有取得关键配方的定向检查，共 {targeted["checks"]} 条分支对照。最早数量请求常因缺工作台被拒绝，不能只测那一条便认定数量无效。补充检查没有追加模型调用、没有改变成绩。\n',
        table(['目标 family','方法','动作索引','实际动作','替换后相同续行失败的动作'],[[x['case_id'],LABELS[x['method']],x['index'],x['actual'],x['alternative']] for x in targeted['local_goal_changes']]),
        '首轮部分探索替换使用基础模型的 enter 建议，可能改变地点，因而只证明动作/位置的物理差异。补充信息对照统一用 inspect→wait；这些固定续行仍完成，不能据此否定信息作用，因为余下动作已经由原轨迹选好。\n',
        '固定余下动作的检查能验证某一动作的物理作用；对 inspect 的替换不会重采样后续模型，因此不能完整测量信息的决策价值。对于摘要，没有追加另一套模型调用去做提示反事实；独立作用以同格式配对对照和可检查行为证据为界，不作过强因果声称。\n',
        '## 8. 八个机制问题与科研判断\n',judgment['answers']+'\n',
        '## 9. 成本、复现与交付\n',
        f'原八种方法满 40 步估算 $3.7315；后增格式对照估算 $0.34，仍共享 **$4 自动停止上限**。实际本轮记账 **${ver["new_ledger_usd"]:.9f}**；此前累计 ${ver["previous_ledger_usd"]:.9f}，项目合计 **${ver["project_total_usd"]:.9f}**。使用历史统一价格作可比记账，不等于当前供应商账单。\n',
        f'全部 {ver["episodes_replayed"]} 条正式轨迹、{ver["actions_replayed"]} 个动作精确重放通过，共 5,941 次 API 请求、11,430,541 个输入与输出 token，17 个 family 的九种方法起点 hash 一致。原始请求、token、费用和独立预算账本一致；无重复请求 ID 或未结算预留。代码冻结、旧文件不变性与发布凭据检查分别保存。\n',
        '上传我们实现的代码、实验生成的轨迹/反事实状态和中文分析，不上传下载的引擎、模型或任何凭据。大规模逐步检查点留在 `/root/scar_workspace/runtime_unknown17/`，批量审计逐项登记路径及 SHA256；公开初始状态复用 Stage 5 已发布快照，完整动作轨迹足以重放。详见 [复现指南](复现指南.md)。\n']
    (REPORT/'实验报告.md').write_text('\n'.join(parts))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attribution-only',action='store_true');a=p.parse_args()
    attribution() if a.attribution_only else final_report()
