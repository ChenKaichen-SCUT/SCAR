"""Chinese reports and complete family-level decision evidence from raw results."""
from pathlib import Path
from scar_stage14.common import load,records
ROOT=Path('results/stage15');OUT=Path('reports/stage15');METHODS=[f'P{i}' for i in range(7)]


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in r)+' |' for r in rows)+'\n'


def write(name,text):
    OUT.mkdir(exist_ok=True,parents=True);(OUT/name).write_text(text.strip()+'\n')


def main():
    a=load(ROOT/'aggregate_metrics.json');metrics=load(ROOT/'episode_metrics.json');pairs=load(ROOT/'paired_comparisons.json');completion=load(ROOT/'completion.json')
    indexed={(m['family'],m['algorithm']):m for m in metrics};families=sorted({m['family'] for m in metrics})
    primary=table(['配置','R@10','R@20','R@40','成功局动作数','全部动作','输入/输出 token','费用 USD'],[[m,a[m]['R10'],a[m]['R20'],a[m]['R40'],','.join(map(str,a[m]['success_steps'])),a[m]['steps'],f"{a[m]['input_tokens']}/{a[m]['output_tokens']}",f"{a[m]['cost_usd']:.6f}"] for m in METHODS])
    family_table=table(['family',*METHODS],[[f,*[('成功' if indexed[f,m]['R40'] else '失败')+f"（{indexed[f,m]['steps']}步）" for m in METHODS]] for f in families])
    comparisons=table(['比较','R@40 差值','胜出 family','退化 family','描述性配对 bootstrap 95% 区间'],[[p['comparison'],f"{p['delta_R40']:+.1%}",', '.join(p['wins']) or '无',', '.join(p['losses']) or '无',str(p['paired_family_bootstrap_95_descriptive'])] for p in pairs])
    qualification='仅最初的10个 robot_kingdom 开发 family，每个配置每个 family 一次，原固定物理种子、40步上限。不是独立泛化测试。相同物理种子不使 temperature=0.7 的 API 模型采样配对；差值不能单凭一局就作因果归因，区间仅为描述性证据。'
    write('实验总报告.md',f'''# Stage15 实验总报告

本批70局全部纳入统计；真实取得目标是唯一的整局成功标准。P0为本批新运行的冻结S1，P1为在线知识修复，P2/P3/P4/P5分别只增加数量/收尾/保护/续行，P6同时启用四项。

{primary}

{qualification}

## 成败与独立消融

{family_table}

{comparisons}

## 验收、冻结与费用

216项测试通过；44个历史原生状态×7种配置=308个分支，每遍1566个动作，服务端和本地各两遍一致。原S1的311个历史动作及5个成功任务得到完整物理复现。短分支内原先成功的10个检查点结果均保留；这些检查点有同family重叠，不能当作10个独立任务成功率。预冻结发现的状态别名和过期意图问题及修复见 `results/stage15/pre_freeze_revisions.json`，此前API调用为零。

冻结文件为 `results/stage15/freeze.json`，历史2432个文件保持哈希不变。正式批次后不修改策略、不重排模块、不选择性补跑。所有策略只接收公开观测，原生消耗、隐藏依赖图及反事实批量只在动作选择后由评测器计算。

实际新增费用为 {completion['cost_usd']:.9f} USD，保守账本为 {completion['conservative_cost_usd']:.9f} USD；5美元全局、0.20美元单局保护。费用使用沿用协议的固定峰值单价及实际API usage，非账户发票。原估计1.570053391美元。状态分布：`{completion['statuses']}`。原始响应、请求失败尝试、费用及全部轨迹均保留。

## 必答问题

具体证据和有界结论见本目录各专题报告及 `研究判断.md`。不能把配方登记完整、合法性改善、局部生产或子目标闭环直接等同于 R@40 改善。
''')
    knowledge=table(['配置','名称关系正确登记/公开','数量正确记录/公开','模型摘要数量正确展示/展示机会','重复无新增信息检查','制作成功/尝试','材料不足拒绝','局部被更优批量支配'],[[m,f"{a[m]['registered_relations']}/{a[m]['public_relations']}",f"{a[m]['correct_quantity_records']}/{a[m]['public_quantity_records']}",f"{a[m]['model_correct_quantity_exposures']}/{a[m]['model_quantity_exposures']}",a[m]['repeat_information_inspections'],f"{a[m]['craft_success']}/{a[m]['craft']}",a[m]['insufficient_material_rejection'],a[m]['batch_dominated']] for m in METHODS])
    batch=load(ROOT/'historical_batch_semantics.json')['rows'];fulfilled=[r for r in batch if r['both_requested_fulfilled']]
    write('知识解析与数量执行.md',f'''# 在线知识与数量执行

统一使用冻结Stage14解析器，只接受真实原生披露：检查中的 made of 名称、取得物品中的数字和小数配方、制作失败明确给出的工作台要求。名称与数量分时升级；UNKNOWN不补1；冲突条目保留证据但撤出可执行表。保留来源、披露时间、重复/冲突事件。旧表将制作到库存检查的平均消耗写成名义配方的路径被隔离，这些观察仍以作用域明确的样本保留。

P1实际接入控制器 ResourceTable 和发送给模型的 PublicFacts；不是只改离线评分。摘要继续48条/6000字符上限及原STM5基础提示。精确配方数量标注为名义单次配方，批量消费保持UNKNOWN。名称排序沿用Stage14统一解析器。

{knowledge}

名称和数量比例按每局结束时已经真实披露的唯一配方计算，再汇总；不同局重复出现的配方是不同观测机会。模型摘要计数为逐决策展示机会，不能视作独立样本。重复检查指标排除inventory和已识别容器，仅计已检查对象且本次无新名称、数量或工作台信息，仍不能证明所有此类动作无价值。

## 批量真实语义

冻结前审计237个历史制作状态。其中请求1和2均如数产出的状态有{len(fulfilled)}个，材料消耗不按2倍线性缩放的有{sum(not r['linear'] for r in fulfilled)}个。例如 sinew_cord 请求1与2都消耗1 salvage_cloth，但产量分别1与2。其余状态还包括产量被原料限制的情况，不能把请求量当实际产量。历史原生批量审计只用于确认设计边界，不把隐藏真值样本注入在线控制器。

P2复用FIFO、公开数量及既有获取函数：先修复明确的一次名义需求缺口；对未满足公开父目标按一次操作累加共享需求；满足上下文严格匹配时可参考已观察样本。仅在有多父目标需求时提高请求量，未知批量仍保留S1默认，绝不按当前下界全局缩成craft1。没有开发独立数量规划器。

每次原生制作的请求、实际产量、消耗和同状态1–4批量效果见 `native_audit.jsonl.gz`；每次在线数量依据见 `decision_analysis.jsonl.gz`。动作消耗通过动作规则单独执行与完整环境步分别核算，不混入NPC或环境损失。局部支配是同状态下产量不低、任何材料消耗均不高且至少一项严格更好的比较；当前需求之上的产量只是过量风险代理，不直接称为浪费。真正材料边际效用/全局最优批量仍UNKNOWN。

必要配方产出所耗材料按真实动作记录在 `episode_metrics.json/necessary_production_consumption`，表示用于已知评测必要中间生产，不等于对最终成功的因果贡献。
''')
    closure=table(['配置','收尾选中动作','基模可直接完成但被延误','保护收取动作','保护步损血','公开关键材料损失量','全局累计损血'],[[m,a[m]['finish_selected'],a[m]['goal_actions_delayed'],a[m]['protection_actions'],a[m]['protection_health_loss'],a[m]['critical_loss_units'],a[m]['health_loss']] for m in METHODS])
    timing=table(['family','配置','配方名称齐全后动作','最终制作步','实际取得步','R@40'],[[m['family'],m['algorithm'],m['actions_after_all_names_known'],m['final_craft_step'],m['final_acquisition_step'],m['R40']] for m in metrics if m['family'] in ['chain_net','hellfire_bomb','hunter_gauntlets']])
    write('目标收尾与材料保护.md',f'''# 最终目标收尾与关键材料保护

P3只控制最终物品直接取得、最终制作，以及最多一个本地缺失直接材料的收尾。没有重引入Stage11 READY排序，也没有递归重规划。直接取得优先；只有公开名义配方足够时考虑制作，未知工作台作为未证实条件记录。剩余操作数是下界而非保证成功的最优路径；单个中间步骤窗口最多6步且不超过总40步。必要材料既无法当前取得又无公开配方时拒绝进入该收尾路径。产出地面物品不算持有完成。

P4仅在离开位置或已经观察到该处资源损失时保护公开依赖；每位置/材料最多一次，不按剩余空间囤积。明确需求按缺口，未知数量只作一次存在性保护尝试，不登记为数量事实。容量满/手位满/直接目标收取优先/当前持续损血等风险会抑制保护。未观察物品体积时非满容器也不代表保证可装，原生反事实保留失败和风险。不会按隐藏未来消失时间选择材料。

{closure}

关键损失量仅统计在该动作前已通过公开依赖确认的材料；全世界环境损失另列，不能用评测器隐藏图给在线保护补信息。健康损失累加每步正向减少，不等于终点血量差。保护动作是开关实际选中次数，可能与原动作同义，净额外成本须看逐例配对，不能每个选中都宣称多花一步。

## 重点任务时序

{timing}

两种blade_blank、bomb、hunter的历史资源损失检查点均纳入原生分支；其公开依赖未建立或健康风险触发时，保护模块允许不干预。不能因为离线知道其将消失就改规则。`preflight_server/native_branches.jsonl.gz` 同时保留基线和全部模块分支。P4对若干初期公开材料产生真实取得动作，亦保留不应收取及无法安全收取的负例。

成败变化的模型提案、同公开状态旧S1规则动作、P1动作、新动作、公开条件、反馈及后续均见 `all_success_changes.jsonl.gz`；此处的影子S1使用当前公开历史，并不声称冻结S1会到达同一状态。
''')
    continuation=table(['配置','实际续行段','续行动作','生产+检查完成段','最终成功'],[[m,a[m]['continuation_plans'],a[m]['continuation_actions'],a[m]['continuation_completed'],a[m]['R40']] for m in METHODS])
    plans=table(['family','配置','起始步（0起）','接受目标','动作','产量','新增关系/数量','结束原因','检查完成','整局成功'],[[m['family'],m['algorithm'],c['start'],c['product'],c['actions'],c['produced'],str(c['new_relations'])+'/'+str(c['quantity_updates']),c.get('stop'),c['completed'],m['R40']] for m in metrics for c in m['continuations']])
    write('探索额度有限续行.md',f'''# 探索额度达到18后的有限续行

P5必须已有被真实动作接受的公开探索目标；过期意图、无材料或已知工作台无路可达不获额度。保留原18次上限，仅对活跃意图允许每局最多7个真实额外动作，且包含在总40步内。新目标配方信息、直接收尾机会、风险、首次动作失败、生产检查完成或额度耗尽均终止。不调用模型二次规划，不提高全局探索上限。

{continuation}

{plans}

Stage14的helm七步历史续行包含一次探得缺少工作台的失败。本轮依指引15“失败立即结束”更严格地停止，因此不能借用旧七步结果宣称本轮完成。冻结前原生检查中helm在取得两项材料后遇工作台拒绝即退出；另有其他family中的公开试制可完成生产/检查，但是否支持全任务由正式R@40独立判断。

多个检查点可能属于同一family及同一物理前缀。新增数量知识和产物只属于子目标层面的证据，不等于最终任务收益，更不证明7是最优上限。
''')
    detail_index={d['task_id']:d for d in records(ROOT/'decision_analysis.jsonl.gz')}
    per=OUT/'families';per.mkdir(parents=True,exist_ok=True)
    for family in families:
        text=f'# {family}：完整七配置\n\n'
        text+=table(['配置','成功','动作','新费用'],[[m,indexed[family,m]['R40'],indexed[family,m]['steps'],f"{indexed[family,m]['cost_usd']:.6f}"] for m in METHODS])
        for method in METHODS:
            metric=indexed[family,method];d=detail_index[metric['task_id']]
            text+=f'\n## {method}\n\n任务：`{metric["task_id"]}`；最终缺失必要配方：`{metric["missing_necessary_names_final"]}`。\n\n'
            text+=table(['步','模型提案','当前公开状态旧S1动作','P1动作','实际动作','原生结果','目标'],[[r['index']+1,r['base_proposal'],r['old_controller_action'],r['P1_action'],r['executed_action'],('拒绝' if r['semantic_rejection'] else '合法')+f"；产量{r['native']['actual_output']}；损血{r['native']['health_loss']:g}",r['full_goal']] for r in d['rows']])
        (per/(family+'.md')).write_text(text)
    write('消融实验与逐例分析.md',f'''# 完整消融及逐例证据

{qualification}

{family_table}

{comparisons}

每个family均有七种配置全动作表：[families/](families/)。任何失败、预算中止、方法中止均作本批分母的一部分，不选择性删除。所有成败变化的完整条件/反馈/后续轨迹保存于 `results/stage15/all_success_changes.jsonl.gz`，而非仅展示有利案例。

归因分四层：动作是否合法；单步真实产出/资源取得；接受目标是否多步完成；是否40步内真实取得最终目标。前三层改变不能替代第四层。P1与P0还会因事实摘要改变后续模型提案；同批API随机性同样会改变提案，因此本次差值只是工程组件的有限样本观测。

bootstrap以10个family为重采样单位，固定seed314159、10000次，保留每个family中所有配置；非独立测试集，不能声称统计显著优越。全零差值产生的[0,0]区间只是本批十个差值完全相同的重采样结果，不代表真实总体没有不确定性。未为提高分数重试失败任务或重排P6模块。
''')
    write('复现指南.md','''# Stage15复现

从提交对应的仓库根目录运行。依赖与环境安装沿用仓库README及Stage11复现指南；外部AgentOdyssey固定提交 `248430692a9d4a61d38c6c03ab2126287faaf450`，Python3.12。第三方引擎、模型、密钥和运行时缓存均不上传。

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export AGENTODYSSEY_ROOT=/path/to/agentodyssey
python -m pytest -q scar_stage14/test_knowledge.py scar_stage15/test_controller.py
python -m scar_stage15.preflight --output /tmp/stage15-preflight --repeats 2 --workers 8
python -m scar_stage15.replay --output /tmp/stage15-replay --repeats 1 --workers 8
python -m scar_stage15.publication
```

以上均为零API，不需要密钥。preflight复用冻结Stage11初态、Stage10真实动作前缀及Stage15历史公开状态；replay完整复演已保存70局动作并校验每步观测、物理资源状态、真正持有目标、动作拒绝以及物理随机状态。相同动作前缀的不同临时目录不影响物理哈希。服务端完整审计与独立本地副本结果见verification文件。

重新计算分析（不改策略、不调用API）：

```bash
python -m scar_stage15.analyze
python -m scar_stage15.report
python -m scar_stage15.judgment
python -m scar_stage15.publication
```

报告中的原始来源均在results/stage15，原始70局按P0–P6分别存为trajectories_P*.jsonl.gz；完整请求/响应、token及失败尝试为requests_P*.jsonl.gz。先核查freeze.json和prior_manifest.json，再核查publication_manifest.json。每行压缩JSONL为一个完整episode；decision_analysis和native_audit可按task_id及index联接。

只有明确希望额外付费复现时才运行下列命令；它不是本批的自动补跑指令：

```bash
python -m scar_stage15.run --runtime /new/empty/runtime --key /private/key-file --workers 12
```

运行器拒绝已存在tasks.json的正式目录；维持70局、原10family、40步、5美元总保护及0.20美元单局保护。采样响应无法保证与本批相同。不要运行prepare/freeze覆盖已发布证据；它们是一开始建立离线验收与冻结协议的脚本，不是读取结果的步骤。
''')
    print('Six reports and ten complete family action tables written.')

if __name__=='__main__':main()
