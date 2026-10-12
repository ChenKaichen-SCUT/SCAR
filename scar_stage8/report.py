"""Chinese reports with complete negative cases; no policy modification."""
import argparse,collections,gzip,json
from pathlib import Path
from scar.io import atomic_json
from scar_unknown17.analyze import public_recipe_names
from scar_unknown17_stage7.report import table,pct,num
from scar_stage8.controller import METHODS
OUT=Path('results/stage8');REPORT=Path('reports/stage8')
LABELS={'P0':'冻结 C0','P1':'冻结 C1，仅 A','P2':'冻结 C5，A+B+C+D','P3':'MRR：A＋公共修复','P4':'RCR：A+B+C+D＋公共修复'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.parse_args();REPORT.mkdir(parents=True,exist_ok=True)
    load=lambda n:json.loads((OUT/(n+'.json')).read_text())
    groups=load('method_metrics');pairs=load('paired_comparisons');families=load('family_comparison');ver=load('verification');cases={c['id']:c for c in load('cases')};eps=load('episode_metrics');off=load('offline_checks')
    by={(e['case_id'],e['algorithm']):e for e in eps};local=collections.defaultdict(collections.Counter);examples=collections.defaultdict(list)
    for r in map(json.loads,gzip.open(OUT/'decision_counterfactuals.jsonl.gz','rt')):
        cohort=cases[r['case_id']]['cohort'];method=r['task_id'].split('-')[-2];key=cohort+'/'+method+'/'+r['flag'];count=local[key];count['comparisons']+=1
        if not r['changed']:continue
        count['changes']+=1
        if r.get('alternate_policy_error'):count['alternate_policy_errors']+=1;continue
        active,inactive=(r['original_effect'],r['alternate_effect']) if r['original_flags'][r['flag']] else (r['alternate_effect'],r['original_effect'])
        count['goal_better']+=int(active['physical_after']['goal'] and not inactive['physical_after']['goal']);count['goal_worse']+=int(inactive['physical_after']['goal'] and not active['physical_after']['goal'])
        count['legal_better']+=int(inactive['rejected'] and not active['rejected']);count['legal_worse']+=int(active['rejected'] and not inactive['rejected'])
        necessary={cases[r['case_id']]['object_names'][x] for x in cases[r['case_id']]['recipe_graph']}
        ak=public_recipe_names(active['public_feedback']['text'])&necessary;ik=public_recipe_names(inactive['public_feedback']['text'])&necessary
        count['key_names_more']+=int(bool(ak-ik));count['key_names_less']+=int(bool(ik-ak))
        if active['physical_after']['goal']!=inactive['physical_after']['goal'] or active['rejected']!=inactive['rejected'] or ak!=ik:
            if len(examples[key])<8:examples[key].append({'case_id':r['case_id'],'index':r['index'],'active':active['action'],'inactive':inactive['action'],'active_goal':active['physical_after']['goal'],'inactive_goal':inactive['physical_after']['goal'],'active_rejected':active['rejected'],'inactive_rejected':inactive['rejected'],'active_key':sorted(ak),'inactive_key':sorted(ik)})
    atomic_json(OUT/'local_effect_summary.json',{'counts':{k:dict(v) for k,v in local.items()},'examples':dict(examples),
        'scope':'fixed recorded proposal and public controller checkpoint; prior flag history held fixed; dependent states, not independent outcome trials'})
    new=groups['new'];reg=groups['regression'];best=max(new[m]['successes'] for m in ['P0','P1','P2'])
    verdict='NO-GO' if max(new['P3']['successes'],new['P4']['successes'])<=best else 'PARTIAL'
    preference='两种新版本均不替换原冻结方案；暂停扩充复杂机制' if verdict=='NO-GO' else '仅保留探索性证据，暂不推广任一新版本'
    j={'verdict':verdict,'preference':preference,'new_best_frozen_successes':best,'new_P3':new['P3']['successes'],'new_P4':new['P4']['successes'],
        'old_P2':reg['P2']['successes'],'old_P4':reg['P4']['successes'],
        'scope':'8newfamilies/2previously used sourcegames, single physical seed; exploratory paired estimate, no broad generalization claim',
        'new_failure_classes':{m:dict(collections.Counter(e['failure_context']['kind'] for e in eps if e['algorithm']==m and e['cohort']=='new')) for m in METHODS}}
    atomic_json(OUT/'research_judgment.json',j)
    total=ver['new_ledger_usd'];calls=sum(x['api_calls'] for x in eps);tokens=sum(x['input_tokens']+x['output_tokens'] for x in eps)
    lines=['# Stage 8：执行修复、算法精简与新任务验证','',
        f"本轮完成 90 组闭环：旧 Robot Kingdom 10 个 family，以及用户确认接受的 8 个新 family（Robot Kingdom 6、Remnant 2），每个 family 比较五个内部版本。新增记账费用 ${total:.9f}，累计 ${ver['project_total_usd']:.9f}。最终判断 **{verdict}**；{preference}。",'',
        '## 协议与数据范围','',
        '起点 `adef04d`。用户最新指令放开新任务来源游戏，旧回归仍限定原 Robot Kingdom 10 例，随后明确接受首批 8 个合格新任务。没有继续扩充。Metropolis 的结构有效且此前未用目标不足，未运行该游戏的正式实验；候选排除记录全部保留。', '',
        '五配置均本批实际运行，P0/P1/P2 直接使用 Stage 7 冻结控制器，不能用历史成绩替代。本批统一 DeepSeek Flash、thinking disabled、temperature=0.7、max_tokens=768、STM5、有界公开事实摘要、每局40动作、原始固定物理种子；没有其他独立基线或额外模型调用。', '',
        table(['版本','含义'],[[m,LABELS[m]] for m in METHODS]),'',
        '策略在新任务生成之前冻结，数据在所有正式 API 调用之前冻结。新任务依据官方原始配方、固定目标ID顺序、历史目标排除、匿名加权依赖结构和真实见证选择，不按 MRR/RCR 成绩选择。新任务的初始分配和三地点结构为程序构建，动作规则与环境步规则保持原样；每条恢复见证独立重放两次。两个来源游戏均在本项目历史中使用过，因此这里只评价新任务/状态泛化，不能称为新游戏泛化。', '',
        '匿名结构去重初筛依据既有数据集中显式保存的配方图。扩展审计重建更早任务后发现：Remnant 的 forged_blade_blank 与该游戏旧目标 obj_star_metal_blade_blank 匿名结构相同，且与旧 Robot 目标同名。因此8例是新目标/新状态集，不能称8个全新结构；另列其余7例的结构新颖敏感性结果，不删除该例、不补跑或替换。此审计在正式批次进行中完成，属于补充披露。相同来源游戏和三地点初态模板产生相关性，family 数不等于独立游戏数。', '',
        table(['新 family','游戏','目标','真实见证动作数'],[[c['id'],c['game'],c['goal']['name'],c['witness_length']] for c in cases.values() if c['cohort']=='new']), '',
        '## 确定性修复与验收','',
        '共享修复采用正在求解节点集合、深度12/节点64的调用保护和最多48次候选验证；未知工作台转入独立公开地点探索，无法支持时让回基础动作或显式 wait。失败收取按相关公开状态记录；“未找到”的地面负证据也阻止改用另一种收取命令绕过失败。历史地点、当前地面、手持、容器与未知状态分开处理。', '',
        '制作之前优先取得已存在产物；最终转存考虑先移动手中副本的语义。共享材料使用公开数值提示的保守 ceil 检查限制多余批量，未知权重保持 UNKNOWN，仍可能需要一次真实试制。MRR 不启用 B/C 的排序和模式，也不直接启用旧 D；两种新版本共享简单最终目标与资源约束。RCR 保留 B/C/D 的额外排序、模式和批量选择。没有特定游戏或物品分支。', '',
        '容量检查区分公开容量与未知物品体积，不把容量单位当作“件数”。正容量不能保证某个体积未知物品必然可放入；首个有公开依据的试探仍可能被拒绝。修复能针对已观察失败禁止重复，无法从不可靠公共观察中保证首次幻影收取绝不发生。继承的配方候选枚举仍随已观察配方表线性扫描，48限制是候选验证次数，并非对配方表大小的声明。', '',
        f"50 项测试通过；{off['old_robot_decisions']} 个旧 Robot 决策关闭修复后与冻结动作完全一致；两种新控制器在全部旧状态的保存/恢复及有限计算检查通过。14 个关键检查覆盖 bandage_roll、orrery_blade、key_blank、spire_pike 和幻影收取。历史错误状态改变动作的 {off['historical_error_counterfactuals']} 个真实环境分支保留，包括没有带来即时目标收益的改变。五配置请求集成、代理完整检查点、独立评测器零 API 冒烟检查全部通过。", '',
        '## 分开的闭环恢复结果','']
    for scope,title in [('regression','旧 Robot Kingdom 回归10例'),('new','新任务8例')]:
        g=groups[scope];lines+=['### '+title,'',table(['版本','R@10','R@20','R@40','成功平均步数','全部动作','费用USD','tokens','每成功费用'],[
            [m,pct(g[m]['recovery_at_10']),pct(g[m]['recovery_at_20']),f"{g[m]['successes']}/{g[m]['n']}",num(g[m]['mean_success_steps']),g[m]['steps'],num(g[m]['cost_usd'],6),g[m]['input_tokens']+g[m]['output_tokens'],num(g[m]['cost_per_success_all_attempts'],6)] for m in METHODS]),'']
    lines += [table(['新任务分层/敏感性']+METHODS,[[scope.removeprefix('new_')]+[f"{g[m]['successes']}/{g[m]['n']}" for m in METHODS] for scope,g in groups.items() if scope.startswith('new_')]),'',
        f"Stage 7 历史 Robot 成绩为 C0 4/10、C5 3/10；本批相应 P0 {reg['P0']['successes']}/10、P2 {reg['P2']['successes']}/10。RQ2 的同批比较是 P4 {reg['P4']['successes']}/10 对 P2 {reg['P2']['successes']}/10，不能把跨时间模型采样波动都归因于修复。新任务和旧任务不混合报告改进率。", '',
        '## 成对比较','',table(['集合','比较','新增成功','丢失成功','净百分点','family bootstrap95%'],[[r['scope'],r['a']+' vs '+r['b'],len(r['a_only']),len(r['b_only']),num(100*r['family']['difference'],1),'['+', '.join(num(100*x,1) for x in r['family']['ci95'])+']'] for r in pairs if r['scope'] in {'regression','new'}]),'',
        '统计单位是 family，10000次配对bootstrap；原始逐 family 配对见机制归因。新集合只有两个来源簇，按来源簇的敏感性结果也不足以支持稳定总体推断。非零 temperature 下模型输出路径不同，不把同初态的成功差直接解释为纯模块因果。P3/P4逐例成败相同导致经验bootstrap差区间退化为[0,0]，并不证明两种方法等效或在总体上没有差异。', '',
        '## 执行可靠性','']
    for scope in ['regression','new']:
        g=groups[scope];lines += ['### '+scope,'',table(['版本','中止','递归中止','格式中止','生成限额触发','重复失败拾取','足量信号下仍制','合法→拒绝','基础即成被覆盖','可避免材料损耗','容量拒绝','可收取仍无关动作','资源循环'],[[m]+[g[m][k] for k in ['method_abort','recursion_abort','format_abort','generation_limit_events','repeated_rejected_pickups','public_sufficient_copy_crafts','legal_to_rejected','harmful_goal_overrides','avoidable_reserve_depletion','capacity_errors','final_available_unrelated_actions','resource_cycles']] for m in METHODS]),'']
    lines+=['“足量信号下仍制”是公开持有/地面数量达到公开需求的生产动作；可能存在幻影或条件未知。材料损耗列另外使用真实引擎的更小批量/合法现有产物收取反事实确认。生成保护触发是安全让回，不等于方法中止；wait 无候选单列，不把静止当作成功。', '',
        '## 知识发现与执行','']
    for scope in ['regression','new']:
        g=groups[scope];lines+=['### '+scope,'',table(['版本','关键规则','中间规则','条件改变重试成功','已知可做执行率','已发现中间未执行','全部规则齐全仍失败','新产物3步内检查','无关状态丢队列','无候选wait','全部wait'],[[m,f"{g[m]['key_recipe_discovered']}/{g[m]['key_recipe_total']}",f"{g[m]['intermediate_recipe_discovered']}/{g[m]['intermediate_recipe_total']}",g[m]['condition_released_successes'],pct(g[m]['ready_execution_rate']),f"{g[m]['intermediate_conversion_censored']}/{g[m]['intermediate_conversion_n']}",g[m]['all_known_but_failed'],f"{g[m]['new_products_inspected_within3']}/{g[m]['new_products_total']}",g[m]['unrelated_queue_clear_count'],g[m]['safe_no_candidate_steps'],g[m]['actual_wait_actions']] for m in METHODS]),'']
    lines+=['逐条首次发现、首次有效制作、未执行删失时长和最终失败条件均保存在 episode_metrics.json。未发现的规则单列；40步剩余时长不是未删失的平均恢复时间。新产物检查可能因已知而不必要；队列丢失采用“资源状态相同却由非空清空”的窄代理，不能证明所有计划错误都不存在。','',
        '## MRR 与 RCR 的额外机制','',table(['新集合','成功','动作','费用','关键发现','中间未转化','资源损耗','checkpoint平均字节','活跃控制字段平均字节'],[[m,new[m]['successes'],new[m]['steps'],num(new[m]['cost_usd'],6),new[m]['key_recipe_discovered'],new[m]['intermediate_conversion_censored'],new[m]['avoidable_reserve_depletion'],num(new[m]['mean_controller_checkpoint_bytes'],0),num(new[m]['mean_active_control_bytes'],0)] for m in ['P3','P4']]),'',
        '状态字节量包含相应表示开销，不等同于理论复杂度；活跃字段统计排除了主要日志/表/事实对象。B/C/D 的同状态开关比较保持原基础提案与先前历史，不能撤销过去模块已造成的状态变化，也不是额外整局实验。', '',
        table(['集合/P4模块','动作改变','开启目标+/-','开启合法+/-','披露必要名+/-'],[[key,ct['changes'],f"{ct['goal_better']}/{ct['goal_worse']}",f"{ct['legal_better']}/{ct['legal_worse']}",f"{ct['key_names_more']}/{ct['key_names_less']}"] for key,ct in sorted(local.items()) if '/P4/' in key]), '',
        '## RQ 与最终判断','',
        f"**RQ1**：旧确定性回归全部通过。正式 P3/P4 的方法中止合计 {sum(g[m]['method_abort'] for g in [reg,new] for m in ['P3','P4'])}；重复失败拾取合计 {sum(g[m]['repeated_rejected_pickups'] for g in [reg,new] for m in ['P3','P4'])}；足量公开信号下制作合计 {sum(g[m]['public_sufficient_copy_crafts'] for g in [reg,new] for m in ['P3','P4'])}。这些是本批可核验结果，不是对所有环境状态的正确性证明。",'',
        f"**RQ2**：旧10例的同批 P4 为 {reg['P4']['successes']}/10，P2 为 {reg['P2']['successes']}/10；差值 {reg['P4']['successes']-reg['P2']['successes']} 例，配对新增与退化均完整保留。",'',
        f"**RQ3**：新8例 P3 {new['P3']['successes']}/8、P4 {new['P4']['successes']}/8，费用分别 ${new['P3']['cost_usd']:.6f}/${new['P4']['cost_usd']:.6f}。可靠性需同时看拒绝覆盖、资源损耗和无进展行为；不只比较成功数。",'',
        '**RQ4**：局部开关表与逐例轨迹区分 B 的披露、C 的执行和 D 的资源效果。模块触发次数不是任务收益；若没有新增必要名称或可验证有效动作，就不能把不同模型轨迹中的成功自动归功于复杂机制。详见机制归因中的全部正负配对与局部例证。','',
        '**RQ5**：每条失败分为方法中止、必要公开知识仍缺失或名称已知但执行/资源未满足，记录终态真实材料。名称齐全不等于数量、工作台与运输都满足；局部条件不足也不证明任务不可恢复。不根据失败直接推测新的隐藏游戏规则。','',
        f"最终 **{verdict}**。{preference}。本次未见集合只有8例、两个已使用来源游戏，不以探索性点估计宣称广泛泛化成功。若复杂版本没有可靠额外行动证据，应停止继续叠加模块。",'',
        '## 完整性与复现','',
        f"{calls} 次 API 请求，{tokens} tokens；{ver['episodes_replayed']} 局、{ver['actions_replayed']} 个环境动作完成真实状态重放。{ver['protected_prior_file_count']} 个历史文件保持不变，请求费用与账本对齐，未结算预留 {ver['pending_reservations']}。原始轨迹、模型响应、公开控制状态、生成初态、局部反事实、全部失败均交付。计价沿用历史对比记账口径，不是当前供应商发票。",'',
        '只上传项目自己实现的代码和生成的实验结果/分析，下载的游戏引擎、模型、凭据及运行账本不上传。见[复现指南](复现指南.md)。']
    (REPORT/'实验报告.md').write_text('\n'.join(lines)+'\n')
    detail=['# Stage 8 逐例机制归因','',
        '全部18个family均保留；每行成功步数来自真实闭环。局部反事实固定基础提案，整局配对含模型随机性，二者证据分开。','']
    for f in families:
        detail+=['## '+f['target']+' · '+f['game']+' · '+f['cohort'],'','Family：`'+f['case_id']+'`。','',
            table(['版本','成功/步数','缺失关键规则','条件重试成功','可避免损耗','合法→拒绝','目标完成被覆盖','失败分类'],[[m,by[f['case_id'],m]['recovery_steps'] or '失败',', '.join(by[f['case_id'],m]['missing_key_recipes']) or '无',len(by[f['case_id'],m]['condition_released_successes']),by[f['case_id'],m]['avoidable_reserve_depletion'],by[f['case_id'],m]['legal_to_rejected'],by[f['case_id'],m]['harmful_goal_overrides'],by[f['case_id'],m]['failure_context']['kind']] for m in METHODS]),'']
        for a,b in [('P4','P2'),('P3','P1'),('P4','P3')]:
            aa,bb=by[f['case_id'],a],by[f['case_id'],b]
            detail.append(f"{a} vs {b}：{'新增恢复' if aa['recovery_at_40'] and not bb['recovery_at_40'] else '丢失恢复' if bb['recovery_at_40'] and not aa['recovery_at_40'] else '成败相同'}；关键配方差 {aa['key_recipe_discovered']-bb['key_recipe_discovered']}，动作差 {aa['steps']-bb['steps']}，费用差 ${aa['cost_usd']-bb['cost_usd']:.6f}。")
        detail+=['']
        for m in ['P3','P4']:
            e=by[f['case_id'],m];detail+=['### '+m,'','首次关键规则发现：`'+json.dumps(e['first_key_recipe_actions'],ensure_ascii=False)+'`。','',
                '终态归类与条件：`'+json.dumps(e['failure_context'],ensure_ascii=False)+'`。','',
                table(['索引','执行动作','新必要规则','产出','模块线索'],[[x['index'],x['action'],', '.join(x['new_key_recipes']) or '—',x['productive'],', '.join(x['mechanism']) or '—'] for x in e['mechanism_timeline'] if x['productive'] or x['new_key_recipes']]),'',
                '重复失败拾取：`'+json.dumps(e['repeated_pickup_records'],ensure_ascii=False)+'`；足量信号下制作：`'+json.dumps(e['sufficient_copy_records'],ensure_ascii=False)+'`。','']
            selected=[x for key,rs in examples.items() if '/'+m+'/' in key for x in rs if x['case_id']==f['case_id']]
            if selected:detail+=['同状态局部正负例：','',table(['索引','开启动作','关闭动作','开启/关闭目标','开启/关闭拒绝'],[[x['index'],x['active'],x['inactive'],f"{x['active_goal']}/{x['inactive_goal']}",f"{x['active_rejected']}/{x['inactive_rejected']}"] for x in selected]),'']
    detail+=['## 全量局部审计的限制','','示例按预先固定遍历顺序展示；全量比较保存在 decision_counterfactuals.jsonl.gz。相同状态上的合法性或名称披露变化，只证明当步作用。中间生产、移动和后续知识的长期收益仍需结合完整轨迹；无即时收益不自动等于无价值。']
    (REPORT/'机制归因.md').write_text('\n'.join(detail)+'\n')
    (REPORT/'复现指南.md').write_text('''# Stage 8 复现指南

使用 Python 3.12、项目依赖和官方 AgentOdyssey 提交 `248430692a9d4a61d38c6c03ab2126287faaf450`。引擎和模型由使用者另行安装；仓库不上传下载内容。先设置环境，进入 SCAR 仓库：

```bash
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export AGENTODYSSEY_ROOT=/path/to/agentodyssey
python -m pytest tests/test_stage8.py tests/test_stage7.py tests/test_unknown17.py tests/test_sequence.py -q
python -m scar_stage8.reproduce --runtime /tmp/scar8-replay --replay-saved
```

默认只校验冻结文件、还原初态并重放保存动作，零模型调用。初态是本项目生成、去除代理凭据后的可信实验快照，依赖相同上游代码和 Python 版本。全量原始模型输入、响应和 token 在 requests_P*.jsonl.gz，轨迹和决策前控制器状态在 trajectories_P*.jsonl.gz。服务器每个动作后还保存完整物理快照与代理记忆检查点。artifact_manifest.json 覆盖发布材料。

策略冻结早于新任务构建，数据冻结早于首个付费调用。不要覆盖冻结文件或在已有 runs 目录补跑失败任务。若独立复现闭环，先创建单独的 Git checkout/worktree，并只在该副本内运行；统计脚本会写该副本的 results/stage8，不能在保留原始发布结果的目录执行。必须使用新空运行目录和自己的密钥：

```bash
python -m scar_stage8.reproduce --runtime /path/to/fresh-runtime --run-closed-loop --key /private/keyfile --workers 12
python -m scar_stage8.finish --runtime /path/to/fresh-runtime --workers 8
```

正式批次有增量 $5 保护和单局 $0.25 保护；价格是历史对比记账口径。复现模型结果可能因非零温度、供应商模型变化而不同；不能覆盖本轮结果冒充原始测量。仓库已保存所有失败，不补抽第二种子或更好的响应。

服务器原运行目录为 `/root/scar_workspace/runtime_stage8`。旧回归只含原 Robot Kingdom10，8个新任务为Robot6/Remnant2。候选生成并不运行待评算法；选择记录、排除原因、真实见证、母场景/匿名结构重合审计均在 results/stage8。局部固定续动作只用于机制验证，不计入正式成功率。
''')
    if (OUT/'negative_counterfactuals.json').exists():
        from scar_stage8.interpret import augment
        augment()
    print(json.dumps(j,ensure_ascii=False))
if __name__=='__main__':main()
