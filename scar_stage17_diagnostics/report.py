"""Chinese reports and human-readable evidence. Reads diagnostic outputs only."""
import collections as C
import statistics as S
from .common import *
from scar.agents.scar.state import feedback_text

NAMES={'A0':'SCAR','A1':'ReAct+STM','A2':'LongContext','A3':'AdaPlanner适配','A4':'Deterministic DAG Planner'}
STATUS={'success':'成功','game_failure':'原生失败/死亡','step_limit':'100步上限','model_parse_exception':'响应/解析异常'}
DIM={'proposal_preserves_more_health':'原提案保留更多HP','proposal_avoids_immediate_terminal_failure':'原提案避免当步失败','proposal_extra_closure_production':'原提案新增闭包产物','proposal_extra_closure_relation':'原提案新增闭包配方','proposal_extra_relevant_material_type':'原提案新增相关材料类型'}
DATA='../../results/stage17/diagnostics/'

def esc(x):return str(x).replace('|','\\|').replace('\n','<br>')
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(esc(x) for x in r)+'|' for r in rows])+'\n'
def frac(x,n):return f'{x}/{n} ({x/n:.1%})' if n else '—'
def names(xs):return ', '.join(xs) if xs else '∅'
def step(x):return '未达到' if x is None else str(x)
def ref(t,m='A0',s=None):
    tid=t['task_id'] if isinstance(t,dict) else t
    return f'[{m} 第{s}步]({DATA}evidence/{tid}.md#{m.lower()}-a{s:03d})' if s is not None else f'[{tid[4:6]} 证据]({DATA}evidence/{tid}.md)'
def dump(name,lines):
    (ROOT/'reports/stage17'/name).write_text('\n\n'.join(lines).rstrip()+'\n')

def run():
    deny_network();baseline()
    tasks=load(RESULTS/'tasks.json');runs=load(OUT/'per_run.json');kn=load(OUT/'knowledge.json');stats=load(OUT/'statistics.json')
    rmap={(r['task_id'],r['method']):r for r in runs};kmap={(k['task_id'],k['method']):k for k in kn}
    actions=read_gzip(OUT/'action_evidence.jsonl.gz');amap={a['evidence_id']:a for a in actions};audit=read_gzip(OUT/'controller_audit.jsonl.gz')
    contexts=read_gzip(OUT/'model_context_evidence.jsonl.gz');cf=read_gzip(OUT/'counterfactual_local.jsonl.gz');cfmap={r['evidence_id']:r for r in cf}
    errors=load(OUT/'response_errors.json');notes=load(ROOT/'scar_stage17_diagnostics/case_notes.json')
    evidence=OUT/'evidence';evidence.mkdir(exist_ok=True)
    index=[]
    # Full native feedback, no silently clipped quotations, all five methods.
    for t in tasks:
        tid=t['task_id'];parts=[f"# {tid}：逐动作原始证据",f"游戏 {t['game_name']}；目标 {t['target_item']}；种子 {t['initial_seed']}。动作号均从评测开始计数，quarantine另有28步统一教程。以下完整保留反馈；完整前后观察、物理状态和模型消息在原始gzip中。"]
        for m in METHODS:
            rr=rmap[tid,m];parts += [f'## {m} {NAMES[m]}',f"{STATUS[rr['status']]}；实际 {rr['steps']} 步；[原始轨迹](../../runs/{tid}__{m}/trajectory.jsonl.gz)；[全部请求](../../runs/{tid}__{m}/requests.jsonl.gz)。"]
            for a in [a for a in actions if a['task_id']==tid and a['method']==m]:
                s=a['step'];parts+=[f"<a id=\"{m.lower()}-a{s:03d}\"></a>\n### {m} 第{s}步 `{a['action']}`",f"证据ID `{a['evidence_id']}`；原始JSONL第{s}行；HP {a['health_before']}→{a['health_after']}；death字段 {a['death']}。复活可能恢复HP，须结合终止/死亡反馈。\n\n```text\n{a['feedback']}\n```"]
                index.append(dict(evidence_id=a['evidence_id'],task_id=tid,method=m,step=s,markdown=f'evidence/{tid}.md#{m.lower()}-a{s:03d}',raw_path=a['raw_path'],jsonl_line=s,request_ids=a['requests']))
                if m=='A0':
                    au=next(x for x in audit if x['evidence_id']==a['evidence_id']);branch=cfmap[a['evidence_id']]
                    parts += [f"原LLM提案 `{au['proposal']}`；S1 `{au['S1_candidate']}`；P1 `{au['P1_action']}`；P3 `{au['P3_action']}`；覆盖 {au['overridden']}；来源 {names(au['layers'])}；公开支持 {names(au['proposal_public_support'])}；队列 `{au['queue']}`；探索累计 {au['exploration_spent']}。"]
                    if branch['alternate']:
                        b=branch['alternate'];parts += [f"同状态单步原提案回放，起点 `{branch['before_hash']}`，结果 `{b['state_hash']}`；局部差异 {names(branch['local_dimensions'])}；实际动作优势 {names(branch.get('actual_advantages',[]))}。\n\n```text\n{feedback_text(b['feedback']['text'])}\n```"]
        (evidence/f'{tid}.md').write_text('\n\n'.join(parts)+'\n')
    gzip_rows(OUT/'evidence_index.jsonl.gz',index)
    write(OUT/'evidence_index.json',dict(tasks=[dict(task_id=t['task_id'],file=f"evidence/{t['task_id']}.md",runs={m:rmap[t['task_id'],m]['steps'] for m in METHODS}) for t in tasks],actions=len(index),requests='Original requests.jsonl.gz; request_id joins model_context_evidence and response_errors.'))

    # 1. Full paired performance and cost report.
    lines=['# Stage17 逐任务性能对比',
      '**120/120组全部结束，24个任务×5方法全部进入分母。** 最后两局AdaPlanner已经结束：scrap_buckler在56个实际动作后解析异常，oil_flask执行100步仍未成功；不是把未完成任务预先判失败。DAG的24局完整计入。',
      '本轮只做离线统计和原生单步回放，没有改动算法、重跑模型任务或新增API请求。冻结输入见[哈希清单]('+DATA+'input_manifest.json)。全部配对数据见[24行宽表CSV]('+DATA+'paired_24.csv)、[120行明细CSV]('+DATA+'per_run.csv)。',
      '“深度/节点”指静态制作依赖深度/配方节点数，作为结构复杂度；天然可拾取的中间物可能绕过部分节点，不能称为必须实际执行的最短制作深度。每个目标均为“本局制作至少1件且持有至少1件”。所有任务100步上限；种子仅配对物理初态，不配对模型随机数。',
      '单元格格式：结果及实际动作数；制作失败/无效动作/重复检查；模型请求数；输入/输出token；协议费用USD；终止原因。重复检查是同对象名再次inspect，不自动等于浪费；无效动作沿用冻结的反馈正则口径，额外原生invalid标记也保存在逐动作数据中。']
    body=[]
    for t in tasks:
        cells=[]
        for m in METHODS:
            r=rmap[t['task_id'],m];cells.append(f"{'成功' if r['success'] else '失败'} {r['steps']}步<br>制/无/重 {r['craft_failed']}/{r['invalid']}/{r['repeated_inspections']}<br>请求 {r['api_calls']}；T {r['input_tokens']}/{r['output_tokens']}<br>${r['cost_usd']:.6f}<br>{STATUS[r['status']]}")
        body.append([ref(t),t['game_name'],t['target_item'],t['initial_seed'],f"{t['dependency_depth']}/{t['recipe_nodes']}",*cells])
    lines += [table(['任务','游戏','目标','种子','深度/节点',*NAMES.values()],body),'## 逐任务胜负与条件动作比较',table(['对照','双方成功','仅SCAR成功','仅对照成功','双方失败','共同成功：SCAR−对照平均步数','共同成功：SCAR较快/较慢'],[[NAMES[m],p['counts'].get('both_success',0),p['counts'].get('scar_only',0),p['counts'].get('other_only',0),p['counts'].get('both_fail',0),f"{p['both_success_action_delta_mean']:+.2f}",f"{p['both_success_scar_faster']}/{p['both_success_other_faster']}"] for m,p in stats['paired'].items()]),
      '每个任务的四格分类保存在[statistics.json → paired.tasks]('+DATA+'statistics.json)。SCAR相对LC为2胜5负，DAG为2胜2负。相对ReAct的共同成功平均步数有优势，但9个共同成功任务中仅3个更快，6个更慢，均值受ReAct的长尾任务影响。SCAR相对LC的8个共同成功任务平均反而慢1步，不能用两者不同成功子集的均值宣称SCAR更高效。',
      table(['任务','对ReAct','对LongContext','对AdaPlanner','对DAG'],[[t['task_id'][4:6],*[{'both_success':'双方成功','scar_only':'仅SCAR成功','other_only':'仅对照成功','both_fail':'双方失败'}[next(p['category'] for p in stats['paired'][m]['tasks'] if p['task_id']==t['task_id'])] for m in ('A1','A2','A3','A4')]] for t in tasks]),
      '## 预算与有效制作',table(['方法','R@60','R@80','R@100','成功平均/中位动作','所有任务动作','产出制作/尝试','目标闭包产出制作/尝试','材料拒绝/站点拒绝','无效/重复检查(相同反馈)'],[[NAMES[m],frac(round(s['R60']*24),24),frac(round(s['R80']*24),24),frac(s['success'],24),f"{s['success_steps_mean']:.2f}/{s['success_steps_median']}",s['total_actions'],frac(s['productive_crafts'],s['craft_attempts']),frac(s['closure_productive_crafts'],s['craft_attempts']),f"{s['material_rejection']}/{s['station_rejection']}",f"{s['invalid']}/{s['repeated_inspections']} ({s['identical_feedback_repeat_inspections']})"] for m,s in stats['methods'].items()]),
      '产出制作表示至少产出一件，部分产出也计入；闭包产出仅是相关性口径，天然材料可绕行，不能等同有效任务进展。DAG有193次制作尝试、176次无产出，比SCAR的48次/28次高得多。SCAR总动作较少同时含13次提前原生失败和1次解析终止，不能把提前死亡节省的动作算效率收益。全方法都没有“已制作最终目标但终局未取得”的失败；这不否认中途存在制作后未立即收取。',
      '## 用量、缓存与费用',table(['方法','请求总数/每任务均值','输入/输出token','每任务总token均值','缓存命中率','协议总费用/每任务均值','失败请求费用','最长输入token'],[[NAMES[m],f"{s['api_calls']}/{s['api_calls']/24:.2f}",f"{s['input_tokens']}/{s['output_tokens']}",f"{(s['input_tokens']+s['output_tokens'])/24:.1f}",'—' if s['cache_hit_rate'] is None else f"{s['cache_hit_rate']:.2%}",f"${s['cost_usd']:.6f}/${s['cost_usd']/24:.6f}",f"${s['failed_request_cost']:.6f}",s['context_max_tokens']] for m,s in stats['methods'].items()]),
      '计费使用所有已保存实际usage，缓存命中/未命中/输出每百万token按冻结协议$0.006/$0.3/$1.2计价，合计$'+f"{sum(s['cost_usd'] for s in stats['methods'].values()):.6f}"+'；未知账单请求预留项本轮为0。**没有账户发票/扣款流水，不能把协议计算值冒充实际扣款。** 不额外调用账单或模型接口。SCAR输入token明显少于LC，但缓存命中率9.87%对94.31%，实际usage按协议计算反而更贵（$0.606272对$0.510989）；缓存与模型定价决定成本结论。',
      '### LongContext每任务长度变化',table(['任务','首次输入token','末次输入token','最大输入token','截断记录','响应length结束次数'],[[t['task_id'][4:6],*[rmap[t['task_id'],'A2'][k] for k in ('context_first_tokens','context_last_tokens','context_max_tokens','context_truncated_flags','response_length_finishes')]] for t in tasks]),
      'LC最大实际输入37,497 token，低于冻结客户端配置的1,000,000窗口。没有输入截断、转STM或特殊超限处理；本轮没有上下文长度拒绝。response finish_reason=length是输出预算截断，不能当成输入上下文溢出。逐请求长度及原消息索引见[model_context_evidence.jsonl.gz]('+DATA+'model_context_evidence.jsonl.gz)。',
      '### AdaPlanner额外调用',table(['阶段','全部网络尝试','通过验证次数'],[[p,stats['methods']['A3']['phases'].get(p,0),stats['methods']['A3']['successful_phases'].get(p,0)] for p in ('plan','plan_check','ask_LLM','revision','resume')]),
      '24次初始规划；修订337次尝试、306次通过验证，续行314次尝试、302次通过验证。通过revision并不一定完成其后的plan_check/resume，不能把全部306次都当成已安装的计划版本。逐任务api_phases、successful_api_phases、completed_plan_versions已保存；plan_check等费用均计入总额。',
      '## 响应/解析异常：最终7组，不是6组',
      '此前进度时的6组后来新增AdaPlanner scrap_buckler。最终108次异常网络响应中，21次属于7个终止逻辑请求（每个最多3次），其余87次在同一冻结重试协议内恢复；没有事后重跑失败任务。']
    errrows=[]
    for t in tasks:
        for m in METHODS:
            ee=[e for e in errors if e['task_id']==t['task_id'] and e['method']==m and e['terminal']]
            if ee:errrows.append([ref(t),NAMES[m],rmap[t['task_id'],m]['steps'],ee[0]['step'],ee[0]['phase'],'<br>'.join(f"尝试{e['attempt']+1}: {e['reason']}" for e in ee),'停止，保留实际步数；不补跑'])
    lines += [table(['任务','方法','实际环境动作','失败决策序号','阶段','离线复核原始原因','处理'],errrows),
      '所有异常的request_id、原始文件行号、完整响应、finish_reason和重试是否恢复见[response_errors.json]('+DATA+'response_errors.json)。结构无效包括空steps；resume要求顶层步骤ID而非任意嵌套ID，失败响应不能绕过该约束。',
      '进一步核查：ruin_club三个plan_check响应均含空then分支而被验证器拒绝，scrap_buckler最终revision也有同样问题。oil_bomb三次resume均选择嵌套步骤10，pipe_club三次均选择嵌套步骤8，违反顶层ID契约。原响应表达了继续执行子分支的意图，因此这些失败主要体现模型输出与适配器接口的冲突，不能归为游戏推理能力不足。',
      '## 信息与执行协议核对',
      '120份summary均匹配各自任务的同一initial_state_hash，120条轨迹原生双端重放已通过。相同原生地图、资源、NPC、健康、天气规则；共同禁用在线世界扩展。初始公开历史相同：robot无前缀，quarantine有28步共同教程，之后才开始100步评测。成功均由环境制作计数与实际持有判定。首次死亡/原生终止/模型异常/100步按统一停止协议处理。',
      '相同可见证据不代表相同模型prompt：ReAct保留STM5、LC完整历史、SCAR结构化摘要+STM5、Ada每次上下文只含最近3次交互和持久变量/计划；这些记忆差异就是被比较的机制。Ada初始也接收同一教程，但模型不逐字看到全部28步，不能宣称五者输入字符串完全相同。',
      'SCAR内部收尾时钟已按用户授权适配100步，Stage16原函数体/其他常量保持冻结。DAG独立从公开观察建立图，方法工厂只接收目标、前缀和观察，不接收evaluator_truth；隐藏依赖图仅用于本次离线必要性与结果标注。离线反事实也没有调用DAG或SCAR策略，更未向在线任务注入隐藏配方。',
      'Ada完整保留规划、独立代码检查、计划内询问、反馈断言、修订、独立续行及变量延续这些流程；但其受限JSON DSL不是官方Python执行，未移植跨任务技能库/ALFWorld专用少样例，不能称为官方AdaPlanner的完整等价复现。2048输出上限、完整计划反复输出与严格DSL验证产生可见截断/结构错误，6个异常任务对结果影响很大；不得将适配器的6/24直接宣称成原论文方法的能力上限。源代码对应见[原适配审计](对比算法官方代码与适配审计.md)。']
    lines += ['DSL还限制了变量的使用：ask_LLM回答能保存并替换进后续动作/问题，但if的contains在当前环境观察上判断，不能像任意Python那样直接对变量答案作一般分支判断。部分响应却用contains:"yes"去测试刚才询问的回答，与实际解释语义不符；这是明确的移植能力边界。空then分支被拒绝也会使原本可表达的“此分支无事可做”计划无法执行。这里只诊断并披露，没有修改适配器或补跑。']
    dump('逐任务性能对比.md',lines)

    # 2. Knowledge discovery vs utilization.
    lines=['# Stage17 规则知识发现与执行分析',
      '**SCAR在配方名称覆盖上更强，LongContext在本轮已知目标配方后的完成表现更好；没有证据支持“SCAR只是发现规则不如LC”。** 这两项是事后描述，不是随机化的知识模块消融。',
      '没有预先划分已知/未知任务。逐步从真实原生反馈重建披露事件；物品inspect通常给材料名称，首次取得材料常给精确数量，制作失败可能给缺失工作台。模型猜测与自己写的计划不作为环境知识。初始教程重新解析，即使Ada ruin_club执行0步也不会凭空丢弃已有公开知识。',
      '三层分别记录：①所有已经真实公开的原生证据；②A0/A4控制器当时登记的知识，A1/A2/A3没有等价配方表，记为“不适用”而非0；③每次实际模型请求中确实存在的原生证据字符串或经原生证据验证的系统摘要字段。第三层只表示文本可用性，不是理解或正确利用；语义改写未被字面匹配覆盖的情况保留不确定性。Ada无模型调用的动作不伪造新上下文。',
      '“必要”有三个操作化范围：目标配方（成功要求本局制作目标，因此不可绕过）、隐藏图离线标注的静态祖先闭包、与算法轨迹独立生成的可行见证实际制作集合。后两者不是最小必要集合：天然中间物允许绕过；见证只是某条可行路线。因此公开却没制作祖先，不自动等于失败或不利用知识。严格按用户要求，隐藏配方只用于离线标注目标必要性/材料范围，未读取其数量和站点来补齐知识状态，也不进入决策或反事实提案。',
      '20/40/60/80/100步统计为“截至该预算实际得到的知识”，提前终止保持末值并标记observed_through/terminated；不会假设死后继续获得知识。关系、精确数量、公开站点分别计算；未披露站点时保持UNKNOWN，不能用隐藏真值为空来宣称已知无需工作台。缺站点反馈只公开必要条件子集；成功制作只证明当时配置可行，没有逐项声明穷尽条件。因此完整工作台条件未经证实，不能凭离线全配方宣布“全部知识已经齐全”。',
      table(['方法','目标名称已公开','目标数量已公开','闭包名称全部公开','见证路线名称全部公开','末态闭包名称/数量平均覆盖','已获目标数量中的成功'],[[NAMES[m],f"{s['knowledge']['goal_relation_discovered']}/24",f"{s['knowledge']['goal_quantity_discovered']}/24",f"{s['knowledge']['all_relations']}/24",f"{s['knowledge']['all_witness_relations']}/24",f"{s['knowledge']['final_relation_macro']:.1%}/{s['knowledge']['final_quantity_macro']:.1%}",frac(s['knowledge']['successful_after_goal_quantity'],s['knowledge']['goal_quantity_discovered'])] for m,s in stats['methods'].items()]),
      'SCAR闭包名称74.5%对LC64.5%，但数量覆盖63.2%对63.6%，目标数量公开均19/24；独立见证范围全部名称公开15/24对16/24，说明“SCAR发现更强”依赖覆盖口径。双方都已获目标数量的15个配对任务中，SCAR独胜1、LC独胜2、双方成功8、双方失败4；这比非配对10/19对13/19更可比，但仍受存活、材料和路线选择混杂。',
      table(['方法','20步 关系/数量','40步','60步','80步','100步'],[[NAMES[m],*[f"{s['knowledge']['checkpoints'][str(b)]['relation']:.1%}/{s['knowledge']['checkpoints'][str(b)]['quantity']:.1%}" for b in (20,40,60,80,100)]] for m,s in stats['methods'].items()]),
      'SCAR第20步关系覆盖高（63.9%对LC48.4%），并没有带来更高最终成功率。DAG最终名称与数量覆盖也很高（83.5%/69.3%），完成仍只有10/24，进一步说明披露覆盖不等于可执行计划。',
      '## 公开、登记和模型上下文的落差',table(['方法','公开关系未登记的动作','公开数量未登记的动作','请求缺少部分已公开关系证据','请求缺少部分已公开数量证据'],[[NAMES[m],s['knowledge']['structured_missing_relation_actions'] if m in ('A0','A4') else '不适用',s['knowledge']['structured_missing_quantity_actions'] if m in ('A0','A4') else '不适用',s['knowledge']['requests_with_public_relation_omissions'] if m!='A4' else '无模型',s['knowledge']['requests_with_public_quantity_omissions'] if m!='A4' else '无模型'] for m,s in stats['methods'].items()]),
      'SCAR没有出现本指标可检测的公开配方关系/数量未登记，却有101次请求缺部分已公开关系、60次缺数量文本；其结构化表与有限摘要不能混为一谈。摘要有48条/6000字符上限，公开知识已登记不代表都进模型上下文。LC实际请求中已公开关系/数量证据保留完整；ReAct/Ada有限窗口更常遗漏。这里不能把遗漏次数直接解释成错误数，尤其不能把材料损失记忆、危险规则和配方记忆混成同一个维度。',
      '## 逐任务全方法知识账本',
      '下面“时序”依次为20/40/60/80/100步的关系数/精确数量数，分母为该任务静态配方节点数；括号为实际终止动作。首次全关系/全数量允许为未达到。末列分开列出没有站点披露的配方和只公开部分要求的配方；两者都未证实完整条件。全部事件、逐动作登记、逐请求上下文和负延迟均见[knowledge.json]('+DATA+'knowledge.json)。负延迟意味着先成功制作后才有精确披露，未改写成0。']
    for t in tasks:
        tid=t['task_id'];br=[];details=[]
        for m in METHODS:
            k=kmap[tid,m];r=rmap[tid,m]
            br.append([NAMES[m],names(k['initially_public_recipes']),names(k['newly_public_recipes']),'; '.join(f"{len(k['snapshots'][str(b)]['coverage']['relation'])}/{len(k['snapshots'][str(b)]['coverage']['quantity'])}" for b in (20,40,60,80,100))+f" (止{r['steps']})",f"{step(k['first_all_relations'])}/{step(k['first_all_quantities'])}",names(k['unknown_quantities']),'未披露: '+names(k['no_station_requirement_disclosed'])+'<br>部分要求: '+('; '.join(n+':'+','.join(v) for n,v in k['partially_disclosed_stations'].items()) or '∅')])
            delays='; '.join(f"{n}:关系@{k['first']['relation'].get(n,'?')}→制作@{s} (Δ{s-k['first']['relation'][n] if n in k['first']['relation'] else '?'})，数量Δ{k['latency_from_quantity'].get(n,'未披露')}" for n,s in k['first_successful_craft'].items()) or '无闭包产物制作'
            details.append([NAMES[m],names(k['known_relation_not_crafted']),names(k['known_quantity_not_crafted']),delays])
        lines += [f"### {tid[4:6]} {t['game_name']} / {t['target_item']}（闭包{t['recipe_nodes']}，见证集合：{names(kmap[tid,'A0']['witness_scope'])}）",ref(t),table(['方法','初始公开关系','新增关系','时序关系数/数量数','首次全部关系/数量','末态数量未知','工作台公开情况（非完整条件）'],br),table(['方法','名称已公开但未制作','数量已公开但未制作','公开到首次制作延迟'],details)]
    lines += ['## 关键对照解读',
      'charcoal_brick：SCAR第21步名称、第22步数量，LC第31步才公开；SCAR先耗损生命，LC继续整理可访问材料并在第66步制作。这里SCAR不是输在发现先后。repair_kit：LC第3步发现并最终实际完成rubble_chunk→oil_flask→repair_kit，SCAR第12步发现却插入非必要iron_nugget、两步wait和有害负重，最后接口异常。cog_assembly与oil_flask则是SCAR未发现目标配方就提前终止，包含发现缺口，但更早的过量负重与重收循环有直接证据。',
      '长记忆的优势本轮体现为完整证据保留和若干较长材料安排过程成功；尚无同状态“仅换记忆”实验，不能把LC所有多出的成功都归因于长期记忆。SCAR的公开表无关系/数量登记遗漏，主要问题更接近公开状态到目标相关、安全执行之间的落差。']
    dump('规则知识发现与执行分析.md',lines)

    # 3. Every SCAR failure; no selective omission.
    classifications=[]
    lines=['# Stage17 SCAR失败原因归因',
      '**14个失败任务全部纳入：13个原生失败/死亡、1个响应解析异常；没有100步耗尽，没有已制作最终目标却未取得的失败。** A–H允许重叠，表示有证据的现象/机制，不是唯一因果标签。',
      'A：配方未发现（partial仅表示闭包部分未发现，未证明不可绕行）；B：已公开知识未转成对应制作链；C：材料/制作数量不一致；D：负重、库存、工作台、攻击等环境约束；E：同状态回放确认原提案具有局部信息/产出/生存优势；F(local)：探索额度、wait或停滞，但没有100步预算耗尽；G：已制最终目标却未取得；H：接口异常或不能隔离。所有分类需结合下文限定，不将B直接当成“已经具备可行执行条件”。',
      '原生攻击死亡可能复活至100HP；腐蚀也可能直接令done为真、HP为0而death字段为false。诊断联合使用原始反馈、done、death、实际HP和统一终止状态。世界总量减少还包含NPC/世界动态，库存减少包含主动转移；未把原统计resource_loss_events等同于制作损耗。']
    for t in tasks:
        tid=t['task_id'];r=rmap[tid,'A0']
        if r['success']:continue
        note=notes[tid[4:6]];k=kmap[tid,'A0'];cs=[c for c in cf if c['task_id']==tid]
        evidence_cf=[c for c in cs if any(x in c['local_dimensions'] for x in ('proposal_preserves_more_health','proposal_avoids_immediate_terminal_failure','proposal_extra_closure_production','proposal_extra_closure_relation'))]
        tags=note['tags']+(['E(local)'] if evidence_cf else [])
        classifications.append(dict(task_id=tid,tags=tags,annotated_steps=note['steps'],counterfactual_steps=[c['step'] for c in evidence_cf],analysis=note['analysis'],comparison=note['comparison']))
        lines += [f"## {tid[4:6]} {t['target_item']}：{STATUS[r['status']]}，{r['steps']}步",'证据标签：'+', '.join(tags)+'。',note['analysis'],f"目标关系首次 {step(k['first']['relation'].get(t['target_item']))}；目标数量首次 {step(k['first']['quantity'].get(t['target_item']))}。未知精确数量：{names(k['unknown_quantities'])}；已公开关系但未制作：{names(k['known_relation_not_crafted'])}。"]
        erows=[]
        for s in note['steps']:
            a=amap[eid(t,'A0',s)];d=next(x for x in audit if x['evidence_id']==a['evidence_id'])
            raw=a['feedback'].splitlines();quotes=[x for x in raw if x.startswith(('Cannot','Only enough','I successfully','I stored','I discarded','The malevolent','The creeping','I was attacked','I have died','I waited'))]
            quote=' '.join(quotes) if quotes else next((x for x in raw if x.strip()),'')
            erows.append([ref(t,'A0',s),d['proposal'],a['action'],quote])
        lines += [table(['动作证据','原始LLM提案','实际动作','原始反馈摘录'],erows)]
        if evidence_cf:
            lines += [table(['同状态动作','原提案→实际','直接验证的局部差异'],[[ref(t,'A0',c['step']),c['proposal']+' → '+c['actual_action'],names([DIM.get(x,x) for x in c['local_dimensions']])] for c in evidence_cf]),'局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。']
        lines += ['**成功对照的实际路线与分歧：** '+note['comparison']]
        comparisons=[]
        for m in ('A1','A2','A3','A4'):
            other=rmap[tid,m]
            if not other['success']:continue
            kk=kmap[tid,m];ar=[a for a in actions if a['task_id']==tid and a['method']=='A0'];br=[a for a in actions if a['task_id']==tid and a['method']==m]
            firstdiff=next((i+1 for i,(a,b) in enumerate(zip(ar,br)) if a['action']!=b['action']),None)
            comparisons.append([NAMES[m],firstdiff,step(kk['first']['relation'].get(t['target_item'])),step(kk['first']['quantity'].get(t['target_item'])),ref(t,m,kk['first_successful_craft'][t['target_item']]),ref(t,m,other['steps'])])
        if comparisons:lines += [table(['成功对照','首次动作不同','目标关系首次','数量首次','首次目标制作','成功取得'],comparisons)]
    write(OUT/'failure_classifications.json',classifications)
    tags=C.Counter(x for c in classifications for x in c['tags'])
    lines += ['## 证据强度与不成立的归因',table(['重叠标签','任务数'],sorted(tags.items())),
      '最重复、最直接的机制证据是robot任务中过量诅咒材料负重，以及丢弃后被控制器重新收取。A0的12个robot失败任务中，除war_banner外11个都出现明确腐蚀反馈；6个末步原生失败可被同状态原提案避免。这个结论的证据强于“全部因为规则没发现”或“都是LLM失误”。',
      'F严格意义上的100步耗尽为0；只在repair_kit（2次wait）和sharpened_blade（5次wait）有明确局部停滞，不能称它们最后死于动作预算用完。G为0。制作批量/数量不一致有具体证据，但“请求2仅产1”并不自动造成任务失败；早期大量收取的主要损失是负重环境约束。闭包配方未制作不能忽略天然物品旁路。',
      '不同方法的轨迹从早期就分叉，之后NPC、时间、资源和模型状态也不同。比较成功路线只用于提出解释；只有保存原生状态和随机数的单步回放允许宣称对应一步的局部反事实效应。未开发或验证任何Stage18算法。']
    dump('SCAR失败原因归因.md',lines)

    # 4. Controller audit includes every action, positive and negative evidence.
    actual_dimensions=C.Counter(x for c in cf for x in c.get('actual_advantages',[]))
    lines=['# Stage17 控制器动作覆盖审计',
      f"SCAR全部635个动作已审计，471次提案与执行不同（{471/635:.1%}）。635步事实重放全部匹配原始哈希；每次覆盖均从同一物理状态、同一随机数状态离线执行原LLM提案一次，共471个分支。没有调用模型、控制器重规划或重跑任务。",
      '原提案、S1候选、P1选出动作、P3最终动作、覆盖来源、公开支持、真实知识/材料/产出收益均在[controller_audit.jsonl.gz]('+DATA+'controller_audit.jsonl.gz)。完整分支反馈、状态哈希和物理差异在[counterfactual_local.jsonl.gz]('+DATA+'counterfactual_local.jsonl.gz)，每个动作还有[逐任务可读证据]('+DATA+'evidence_index.json)。',
      '覆盖来源保留多层链：S1的FIFO/探索/收取/批量、S1既有条件保护与公开备选、P3最终收尾。日志中的P1_action指S1使用P1公开知识表后、P3介入前的候选，不是一个独立的P1动作策略。某个动作可以经过多层，不把stage10的retain_F0误读成没有覆盖基础LLM。层计数允许重叠，不能相加解释总次数。每层具体candidate/action、batch原动作、探索source/reason均保存于saved_S1_mechanisms；无法从日志单独再细分的S1内部原因明确合并记录。',
      table(['来源','发生于覆盖动作的次数'],stats['audit']['layers'].items()),
      '“公开支持”只标识看见物品、相邻路径、公开配方等部分证据，绝不等于材料/工作台/手部空间全满足。P1条件检查若没有评估原提案，保留空值，不虚构ALLOW。实际收益以新的原生披露、增加的持有材料或原生制作计数标注，移动/装备等准备行为不因缺少即时收益就自动视为无用。',
      '## 对指定五类现象逐项核查',
      '1. **检查新物品被覆盖：11次“尚未登记inspect”的候选。** 其中很多是war_parchment或war_bench，离线检查返回可制作None，不构成有害覆盖。iron_nugget第10步`inspect scrap_iron`被改成检查木材，离线确实提前公开目标配方；metal_strip第13步也有同类信息机会损失。没有证据支持把全部11次都当作新产物价值被压制；所有匹配行在下面全动作表与机器记录。',
      '2. **必要制作被改为检查/移动/wait：9次。** splint第21步原提案`craft 1 splint`可在同状态成功，实际`inspect inventory`没有产出，验证了一次局部制作机会损失；事实轨迹第22步仍制作、第23步成功。其他8次原提案均不能成功制作，例如repair_kit第27/28步缺war_bench，sharpened_blade第71步缺workbench，metal_strip第22/25步材料不足。没有验证“控制器反复压制大量已可执行的必要制作”。',
      '3. **关系齐全仍做非即时必要操作：11次自动筛选。** 筛选只要求闭包名称齐，不代表数量、工作台、材料和健康都齐。最明显的复杂失败sharpened_blade第47步全关系/数量齐，但第56步缺furnace，仍有真实执行条件缺口。splint的库存检查可验证单步延迟；不能把所有检查归为有害。',
      '4. **收取或最终目标提案被覆盖：9次目标动作匹配。** 目标制作/拾取的原提案并非都可执行；已验证的即时制作损失只有上述splint。所有失败任务G类为0；没有验证一个本可当步完成“制成且持有”的原提案被控制器阻止。',
      '5. **探索上限、FIFO停滞、wait：115个动作处于exploration_spent≥18，实际wait7步。** repair_kit第27–28步、sharpened_blade第34–36及39–40步；后续仍能执行其他动作，不能把达到探索额度解释为整局无动作可用。queue_unchanged_streak记录连续相同队列，但多步材料收集也可合法保持队首，所以不自动标记死锁。',
      '## 同状态验证的局部差异（双向）',table(['原提案一侧的维度优势','次数'],[[DIM.get(k,k),v] for k,v in stats['audit']['local_dimensions'].items()]),table(['实际执行一侧的维度优势','次数'],actual_dimensions.items()),
      '原提案有27次保留更多HP、6次避免当步终止、16次额外公开闭包关系、1次额外制作闭包产物、41次增加不同相关材料类型；维度可以重叠。控制器实际动作也有32次额外公开闭包关系、22次增加相关材料类型、1次额外闭包制作、3次保留更多HP。不同材料类型/数量与信息收益不能直接相减，不能把471次覆盖分成简单好坏二元标签。',
      '对6次避免当步失败的严格局部结果，原始动作造成终止、原提案同状态未终止，这个生存维度无需猜测；但cog_crossbow末步原提案本身手满，且某些实际动作也获取相关材料，存在行动维度取舍。没有把这些分支延伸成整局成功，也未估算“去掉FIFO能多成功几局”。',
      '源码与日志对照定位到具体缺口：[Controller._acquire](../../scar_sequence/planner.py)在已装备容器时按当前地面材料总量构造store，未按传入amount缺口裁剪；因此“缺1件”也可能变成收13/17件。[ResourceController.assess](../../scar_stage10/controller.py)校验来源、容量、站点等，未把已观察的腐蚀副作用转成收取上限。[BaselineController.finish](../../scar_stage16/controller.py)的risk16约束P3主动收尾，但没有阻止S1继续收取。该组合与多次“discard→inspect→重收”原始反馈一致。源码解释的是当前局部行为来源，不是证明一个未实现的修复能提升整局成功率。',
      '## 635个动作总表',
      '信息/数量/站点列为当步新增知识条数，材料列为新增持有物品类型数，产出列为正向制作计数的对象。覆盖列“—”表示与原提案相同；详细前置证据与条件检查在机器数据和链接证据中。']
    for t in tasks:
        lines += [f"### {t['task_id'][4:6]} {t['target_item']}",table(['证据','LLM提案','S1 → P1 → P3/实际','覆盖层','公开支持','新知(关系/数量/站点)','材料/产出','原提案局部优势'],[[ref(t,'A0',a['step']),a['proposal'],f"{a['S1_candidate']} → {a['P1_action']} → {a['actual']}",names(a['layers']) if a['overridden'] else '—',names(a['proposal_public_support']),f"{len(a['actual_new_relations'])}/{len(a['actual_quantity_updates'])}/{len(a['actual_station_updates'])}",f"{len(a['actual_material_gains'])}/{a['actual_production']}",names([DIM.get(x,x) for x in a['local_counterfactual_dimensions']])] for a in audit if a['task_id']==t['task_id']])]
    dump('控制器动作覆盖审计.md',lines)

    # 5. Research judgment grounded in this dataset, no novelty assertion.
    lines=['# Stage17 下一阶段研究判断',
      '**本轮支持的结论是：SCAR有结构化探索和部分动作效率优势，但没有总完成率优势；最扎实的短板证据是公开环境后果未约束执行、以及控制器覆盖带来的局部生存损失。** 尚不足以把一个“长期记忆模块”或“规则发现模块”确定为唯一论文主线。',
      '所有120组均保留，最终成功数SCAR10、ReAct11、LongContext13、AdaPlanner适配6、DAG10；一次温度0.7采样，只有24个相关任务、两个来源游戏，不能宣布显著优于或劣于基线。每任务一个物理种子不是重复模型采样；同游戏共享材料规则，任务也并非24个完全独立机制样本。',
      '## RQ1：真正优势与弱点',
      table(['对照','本轮可支持的SCAR优势','本轮明确弱点/限制'],[
       ['LongContext','早期名称披露与静态闭包名称覆盖更高；输入token更少；scrap_buckler、metal_strip为SCAR独胜。','2胜5负；已获目标数量后的完成10/19对13/19；8个共同成功任务平均慢1步；协议费用更高；LC已公开证据在实际上下文中保留更完整。'],
       ['ReAct+STM','总体无效动作32对228、材料制作拒绝4对42；共同成功平均少10步，总费用较低。','成功少1局；共同成功9局中6局SCAR更慢，优势主要来自ReAct少数长尾；quarantine为7/9对8/9。'],
       ['AdaPlanner适配','10/24对6/24；共同成功平均少14步，规划/修订调用与费用明显少。','仅能约束这份JSON适配实现；Ada有6个接口异常，未移植完整官方执行/技能体系，不能据此否定原方法。'],
       ['DAG','共同成功8局全部更快、平均少5.75步；制作拒绝远少；quarantine7/9对5/9。','总成功同为10/24；robot3/15对5/15；DAG无需API且最终知识覆盖更高，SCAR没有模型费用优势。']]),
      '按任务结构，robot SCAR3/15、LC6/15；quarantine SCAR与LC均7/9，但各自失败的任务并不完全相同。高深度任务war_banner、cog_crossbow、ruin_spear、sharpened_blade五方法均失败，不能宣称SCAR已经解决长依赖制作。深度只是离线静态图指标，天然中间物和危险分布同样影响结果。',
      '## RQ2：主要输在哪里',
      '**多任务直接证据最强：环境约束与控制器执行耦合。** 11个robot失败有明确诅咒材料腐蚀；6个失败末步在同状态原提案下不会当步终止。cog_assembly、cog_crossbow、hellcoal_concentrate、ruin_spear、rubble_chunk、oil_flask反复出现“丢弃有害负重→检查→重新大量收取”。这是可定位到动作的局部机制缺陷；单步反事实不能证明修复后能通关。',
      '**知识利用证据比单纯发现不足更广，但定义要谨慎。** SCAR目标关系公开20/24、数量19/24，发现指标不比LC差；charcoal_brick和repair_kit提供已获知识但未有效完成材料路线的具体例子。另一方面cog_assembly、hellcoal_concentrate、rubble_chunk、oil_flask的目标关系确实没发现，其中后两项LC或其他基线成功，发现缺口也不能排除。生存提前终止会反过来截断发现，因此这些不是互斥独立原因。',
      '**制作数量问题存在，不能夸大为第一瓶颈。** SCAR材料不足拒绝仅4次，站点拒绝24次；sharpened_blade请求2实际仅产1是明确批量不匹配。更严重的13/17个scrap_iron是收取数量与负重风险问题，不是制作配方数量推理错误。',
      '**长期记忆尚未隔离。** A0公开配方关系/数量没有登记遗漏，有限模型摘要却有101/60次证据遗漏；LC没有这类遗漏，且几条较长材料整理轨迹成功。这支持研究“结构化知识怎样进入并约束决策”，不支持说“SCAR记不住所有规则所以输”。非配方的危险后果、最新库存与过期状态还需单独区分。',
      '**不能支持的故事：** SCAR失败主要来自100步不够（实际0例上限终止）；大量可行制作被压制（同状态仅验证splint一处，且该局最终成功）；最终产品不收取导致失败（0例）；覆盖越少越好（实际控制器也有信息、材料与生存局部收益）。',
      '## RQ3：工程问题与可独立研究的机制问题',
      table(['问题','更像工程修正的部分','可能形成独立研究问题的部分','需要什么额外证据才能立项'],[
        ['接口与预算','JSON响应截断、缺字段、空计划、resume顶层ID契约；有限输出预算下重复完整计划。','本轮不足以视作未知规则学习机制。','在隔离开发集验证健壮性；不能在此测试集修好后回填原成绩。'],
        ['库存/批量/站点','明确可见的容量、已知缺工作台、按目标缺口收取、避免把drop用于包内材料。','名义配方、可访问库存与条件消费并不等价时，如何构建带证据的可执行模型。','不同游戏中独立的条件制作/库存失效规则；标注观测与实际消费；重复种子与采样。'],
        ['有害后果与控制器仲裁','本轮可明确定位的有害物品丢弃后重收循环、错误优先级与风险状态失效。','在未知副作用下，把失败/危险反馈转成有作用域和时效的行动约束；结构控制器何时让出决策权。','跨游戏未知危险机制，控制器相同状态的多类反事实，联合生存/信息/目标进展指标，预注册不同仲裁策略。'],
        ['规则发现与利用','减少明显无关的固定检查与缺工作台重试。','探索选择能否面向当前可执行瓶颈，而非追求配方名称覆盖；学习“还缺哪种证据才能安全执行”。','名称、数量、站点、副作用分别隐藏的独立任务族；可行路线分层，发现和利用阶段分别测量。'],
        ['长期知识与模型上下文','6000字符摘要优先级、过期库存记录、显式站点条件不进入动作约束。','带来源与时效的知识压缩，怎样保留决策充分的信息，同时允许模型与控制器对证据冲突进行校验。','保持同一公开知识和行动接口的记忆对照，多轮采样；测文本可用、正确使用和环境收益，不只看最终胜率。']]),
      '优先候选主线是“未知副作用下的证据约束执行与控制器仲裁”，因为已有多个任务和同状态局部证据；其次是“面向可执行条件缺口的发现—利用切换”。这只是机制假设和研究可行性排序，未做文献新颖性核查，不能宣称原创或已经具备论文贡献。诅咒物品主要集中在同一个来源游戏，当前证据也不足以声称跨游戏普适。',
      '长期记忆可以作为上述问题的一部分，但独立记忆论文主线当前证据较弱。纯粹“更好覆盖配方图”也缺乏动机：SCAR和DAG覆盖更高而完成率未更高。Ada接口问题应先与算法能力分离，不宜作为SCAR论文优越性的主要支撑。',
      '本轮到诊断为止：没有开发Stage18，没有调整当前任务上的算法，也没有安排新的模型实验。后续若立项，应使用独立开发/测试规则族、多模型采样及更多来源游戏；那是未来研究设计要求，不是本轮新增实验。',
      '## 可重算材料与验证边界',
      '五份报告均由[scar_stage17_diagnostics/report.py](../../scar_stage17_diagnostics/report.py)结合机器统计与显式逐例注释生成。输入快照、宽表、120运行指标、120条知识时间线、全部5042动作证据、635控制器动作、471单步分支、全部异常请求索引都已保存。复算入口和无网络保护见[README](../../scar_stage17_diagnostics/README.md)。原始文件哈希保持不变，所有负面任务和异常费用保留。']
    dump('下一阶段研究判断.md',lines)
    print('wrote five reports and',len(tasks),'complete evidence pages')

if __name__=='__main__':run()
