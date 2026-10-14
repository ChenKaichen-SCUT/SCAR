"""Generate Chinese reports and standalone figures from saved statistics."""
import json
from collections import Counter
from .common import *

def table(headers,records):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(str(v).replace('\n',' ') for v in r)+' |\n' for r in records)

def save(name,text):
    REPORTS.mkdir(parents=True,exist_ok=True);(REPORTS/name).write_text(text)

def main():
    summary=read(RESULTS/'summary.json');ver=read(RESULTS/'verification.json');prep=read(RESULTS/'preparation.json')
    judgments=read(RESULTS/'understanding_judgments.json');pairs=read(RESULTS/'paired_comparison.json');ss={s['id']:s for s in samples()}
    allg=summary['action_groups']['all'];pg=summary['action_groups']['parent'];labels=summary['understanding_groups']['all']['labels']
    correct=labels.get('Correct grounding',0);pct=100*correct/336
    delta=allg['B_minus_A_acceptance_pp'];n=allg['A']['n'];rec=summary['recovery']
    conclusion=dict(classification='EXPLANATION_CAPACITY_PRESENT_NO_STATE_SUFFICIENCY_GAIN' if pct>=80 and delta<10 else 'MIXED_DIAGNOSTIC_EVIDENCE',
        correct_grounding_rate=correct/336,B_minus_A_acceptance_pp=delta,
        state_grounding_as_primary_bottleneck_confirmed=False,implement_grounded_state_controller=False,
        production_agent_modified=False,independent_parent_episodes=1)
    write(RESULTS/'conclusion.json',conclusion)
    rates=table(['范围','配对数','A 接受','B 接受','B−A（百分点）','双方接受 / 仅 A / 仅 B / 均不接受'],[
        [g,summary['action_groups'][g]['A']['n'],summary['action_groups'][g]['A']['accepted'],summary['action_groups'][g]['B']['accepted'],
         f"{summary['action_groups'][g]['B_minus_A_acceptance_pp']:+.2f}",
         ' / '.join(str(summary['action_groups'][g]['paired_acceptance'].get(k,0)) for k in ['both_accepted','A_only','B_only','neither_accepted'])] for g in ['all','parent','branches']])
    understanding_table=table(['类别','数量','比例'],[[k,labels.get(k,0),f'{100*labels.get(k,0)/336:.2f}%'] for k in ['Correct grounding','Partial grounding','Wrong grounding','No grounding']])
    metric_table=table(['首步指标','A','B'],[[k,allg['A'][k],allg['B'][k]] for k in ['syntax_valid','accepted','native_rejection','trigger_repeat_rejected','past_failed_action_rejected','new_public_state','new_information','new_area','accepted_held_gain','accepted_noncombat_information','progress_proxy','main_reward','death']])
    recovery_table=table(['母轨迹三步指标','A','B'],[[k,rec['A'][k],rec['B'][k]] for k in ['n','turns','executed','accepted','rejections','invalid','all_three_accepted','any_main','main_reward','original_action_retry_success']])
    cost_table=table(['测试','新请求','usage 计费（USD）','平均输入 token'],[[c,summary['costs_by_condition'][c]['requests'],f"{summary['costs_by_condition'][c]['cost_usd']:.9f}",f"{summary['costs_by_condition'][c]['mean_input_tokens']:.1f}"] for c in ['understanding','A','B']])
    caveats='''
## 解释边界

这是 1 条母轨迹及其 10 条相关分支的条件化诊断，不是 336 个独立任务。无显著性或跨游戏优劣结论。

实验一提供显式失败反馈并要求解释；它测可被提示激发的解释能力，不等于行动前预测能力。规则评分核验直接原因和恢复条件，不证明自由文本每句推理都正确；没有独立人类评审者一致性统计。

B 的静态补充有明确限度：`known_requirements` 主要整理公开拒绝，未穷举所有成功拾取时公开的制作配方；`known_tools` 是含 tool/workbench/furnace 的原始引文集合，不是已验证工具本体。它保留历史事实并警示可能过期，没有实现状态失效更新。它还增加历史覆盖和输入长度。因此结论限于这份预登记的补充，不能据此排除更完整状态表示的价值，更不能把负结果解释为 State Grounding 在任何实现上无用。

A 首次请求与保存请求逐字一致；三步短链的后续请求追加自身真实反馈，已不是历史原请求。两组均用原始提案直接原生验证，未运行 AGC 仲裁，因此这不是 AGC-v2 新版本成绩。当前目标以原 schema 的 goal_description 与理由记录。

相同初始状态和环境 RNG 可以核验局部可行性；供应商模型采样没有可控配对 seed，不能把每次分叉归因于结构字段。新信息可能只是战斗、失败或物品变化，接受动作也可能无效循环。三步不足以判长期可完成性。
'''
    save('Stage27实验报告.md',f'''# Stage27 实验报告：状态理解与前置条件维护诊断

**结论：没有确认“模型不能理解失败原因”是 remnant 的主要瓶颈，也没有获得足以直接开发 Grounded State Controller 的证据。**

模型对显式失败反馈的 Correct grounding 为 **{correct}/336（{pct:.2f}%）**。在拒绝后的 {n} 对原生动作测试中，原始输入 A 接受 **{allg['A']['accepted']}/{n}**，结构化补充 B 接受 **{allg['B']['accepted']}/{n}**，差值 **{delta:+.2f} 个百分点**。结果支持“解释能力存在，在线应用仍可能出错”；不支持简单断言“补上一份状态 JSON 即解决长期推进”。

## 完成内容

- 母轨迹 34 次 + Stage26 分支 302 次公开拒绝，完整收录 336 条，覆盖 {len(prep['subtype_counts'])} 类公开缺口。
- 336 个理解测试；334 对首步 A/B 测试；母轨迹 34 对最多三步短回放。两条发生在绝对第 300 步的拒绝仅做理解测试，均未超过原 300 步。
- 冻结生产代码、模型/采样参数、基础 prompt、原环境和轨迹；仅新增诊断脚本、题目与报告。未实现改进 Agent，未重跑正式游戏。
- 模型 `{MODEL['model']}`，temperature={MODEL['temperature']}、top_p={MODEL['top_p']}、presence_penalty={MODEL['presence_penalty']}、thinking={MODEL['thinking']}、输出上限 {MODEL['max_tokens']}；沿用 Stage25 参数。
- 所有 {ver['exact_model_contexts']} 个新请求上下文及 {ver['exact_native_actions']} 个新原生动作离线复核通过；全部原生副本由已保存状态恢复。

## 实验一：失败理解

{understanding_table}

## 实验二：状态补充

{rates}

原始历史失败动作没有直接充当唯一 A；两组均新采样，防止样本选择造成虚假的 B 优势。主线奖励、资源与循环另列，不以环境接受代替任务成功。

{recovery_table}

## 费用与异常

{cost_table}

合计 **{summary['new_requests']} 次请求，{summary['input_tokens']:,} 输入 token、{summary['output_tokens']:,} 输出 token，${summary['cost_usd']:.9f}**。按每次响应 usage 与保存的单价核算，非供应商发票。JSON 解析失败 {summary['invalid_json']} 次，输出截断 {summary['truncated']} 次；完整保留，未质量重采样。分析/裁判/核验新增 API 调用 0。

不可执行提案分类：{summary['unusable_proposals']}，具体方法/样本/步号/原文见 `response_anomalies.json`。首步 A 4 个、B 7 个不可用；另有 A/B 各 1 个母轨迹第三步不可用。另记录批处理主进程在全部作业及完成清单写完后的汇总打印 NameError（缺少 json 导入）；1004 个子作业均退出 0，独立复核已确认完整。未改冻结脚本或重跑模型。

B 对重复历史失败动作的再次拒绝从 A 的 {allg['A']['past_failed_action_rejected']} 次降至 {allg['B']['past_failed_action_rejected']} 次，但整体接受数更低，获得手持资源的次数也没有增加。这是局部指标改善与整体恢复无明显收益并存，不能选择性只报有利指标。

## 最终回答

状态与前置条件**应用/维护**存在具体失误，但这与“LLM 本身看不懂失败”是不同命题。本轮解释测试总体通过，而输入补充未达到预登记的明显改善标准。目标控制、状态应用、资源调度及长程执行策略仍交织，不能确认其中一项已经成为可隔离的主要瓶颈。

当前决定：**暂不将 State Grounding 确认为下一阶段优化方向，不开发 Grounded State Controller。** 保留动态事实失效、手持/地面/容器区分和多前置条件协调为待验证机制问题。
{caveats}
''')
    urows=[]
    for typ,count in prep['subtype_counts'].items():
        ls=summary['understanding_groups'][typ]['labels'];urows.append([typ,count,*[ls.get(k,0) for k in ['Correct grounding','Partial grounding','Wrong grounding','No grounding']]])
    audited=sum(j['reviewer']!='public_rule_screen' for j in judgments.values())
    save('PreconditionUnderstanding统计.md',f'''# Precondition Understanding Replay

所有 336 次真实公开拒绝都进入测试，未依据回答删样本。

{understanding_table}

{table(['公开失败类型','样本','Correct','Partial','Wrong','No'],urows)}

## 核验方法

`scar_stage27/grade.py` 按公开失败类别核验原因、缺失条件和恢复优先项；`understanding_judgments.json` 保存逐条标签、命中规则与证据复核说明，单独的 `understanding_adjudications.json` 保存可复用的语义裁决输入。{audited} 条经过本助手进一步公开证据语义复核（包括母轨迹全部 34 条）；剩余为规则评价，不能称全部经独立人工评审。复核未盲化，没有独立评审者一致性统计。所有解析失败同样进入分母。

核心因果识别与完整恢复建议分开存储。典型 Partial 包括：把写字所需手持工具放宽成装备工具，把地面钥匙说成已持有，把门锁与黑暗的共现误当共同拒绝原因，以及死亡复活后未一致更新位置。词法漏掉同义表达的案例通过保存证据复核纠正；不调用模型裁判。

本结果表明显式拒绝通常可以被解释。它不保证模型行动前能检查全部前置条件，也不证明 workflow 是唯一责任方。模型经提示能解释与在原始行动提示下稳定利用，是两项不同能力。

完整数据库：`results/stage27/failure_database.jsonl.gz`；原始回答、来源和标签：`understanding_answers.jsonl.gz`。每个样本都有 step/goal/observation/inventory/location/previous_actions/candidate_action/environment_response/failure_reason，及原轨迹行号。
''')
    strata=table(['失败类型','n','A 接受','B 接受','B−A pp'],[[k,v['A']['n'],v['A']['accepted'],v['B']['accepted'],f"{v['B_minus_A_acceptance_pp']:+.2f}"] for k,v in summary['action_groups'].items() if k not in ['all','parent','branches']])
    goals=read(RESULTS/'parent_goal_audit.json');gc={c:dict(Counter(g['label'] for g in goals if g['condition']==c)) for c in ['A','B']}
    save('StateSufficiency对比结果.md',f'''# State Sufficiency Test

{rates}

## 首步原生反馈

{metric_table}

`accepted` 的分母包含不可解析/非法提案；`past_failed_action_rejected` 只数重复历史失败动作且本次仍被拒绝，不把条件改变后的成功重试误判成错误。`new_public_state` 使用既有公开状态签名（最多记 256 个）；新状态不等于主线推进。`accepted_held_gain` 只数手持净增加，不包括容器内不可见增加；`progress_proxy` 是接受且手持增加/新区域/新的非战斗反馈之一，仍可能只是局部操作。

{strata}

## 三步恢复

{recovery_table}

短链只针对原定母轨迹 34 个检查点；没有根据首步结果挑选继续。失败/非法回答不重采样。A 与 B 的差异有正有负，完整 334 对表在 `results/stage27/paired_comparison.csv`，完整动作、理由、状态和奖励在各 `probes/*/[AB]/result.json`。

## 目标一致性

全部 668 个首步输出的原目标、新目标、理由与证据可核验性保存于 `action_quality.csv`。引文命中只能证明引用来自公开文本，不能自动证明目标合理。

母轨迹 68 个首步目标另外做语义复核，结果：

{table(['目标判断','A','B'],[[k,gc['A'].get(k,0),gc['B'].get(k,0)] for k in ['maintained_supported_goal','supported_adjustment','uncertain_or_partly_satisfied']])}

临时从采集转为存活/战斗有现实攻击支持；目标保持合理仍可伴随动作错误。a260 健康已为 100，继续恢复健康的必要性不足，但耐力信息不充分，保留“部分已满足/不确定”，不武断判整体目标失效。其余分支目标提供逐条输出与引文核验，不冒充全部完成独立语义标注。
{caveats}
''')
    selected=['parent_a032','parent_a037','parent_a054','parent_a135','parent_a270','parent_a290']
    cases=['# 典型成功、失败与无进展案例\n\n同时展示正、负和双方相同的结果；其余配对全部保存在逐条表，不作排除。\n']
    evidence=[]
    for ident in selected:
        s=ss[ident];chains={c:read(RESULTS/'probes'/ident/c/'result.json')['chain'] for c in ['A','B']}
        lines=[]
        for c,chain in chains.items():
            for x in chain:
                from agents.agc.state import extract
                lines.append([c,x['step'],x.get('action'),x['accepted'],x.get('reward',{}).get('quest',0),extract(x['feedback'])['feedback'].splitlines()[0] if x.get('feedback') else 'invalid proposal'])
        cases.append(f"\n## {ident}：{s['candidate_action']} 被拒绝之后\n\n"+table(['条件','绝对步','动作','接受','主线增量','原始反馈首行'],lines))
        write(RESULTS/'case_evidence'/f'{ident}.json',dict(sample=s,chains=chains))
    cases.append('''
## 证据解释

- a032：B 先拿钥匙，第二步进入 library；A 首步再试进入被拒，第三步也进入。是节约一步的局部恢复，三步主线结局相同。
- a037：两组都按“拿钥匙→进入→对话”成功恢复，说明原始输入本就支持恢复。
- a054：两组均“丢火把→捡火把→丢铁条”，三个动作全被接受，但没有获得主线推进；接受率明显高估策略质量。
- a135：A 先存 cloth 释放手，B 改为缺工具的 write；A 第三步又遇到装备槽冲突。两组都存在多条件执行问题，不能只报 A 首步的优势。
- a270：B 理由称 armory/library 都锁着，转去 disassemble cloth，被拒；同一初始状态 A 的 enter armory 确实成功。这核验了 B 的当前门锁断言有误，但不证明增加某字段必然造成该错误。B 包含标为历史的旧门锁记录，仍被当作当前事实，是时效性风险案例。
- a290：B 先拿笔，随后写纸被拒（纸未手持），再取纸又被手满拒绝。理解单条错误不等于协调“笔、纸、手容量”多个条件；A 也在第三步把 cloth 当成可写物失败。

没有把这些短链提升或分叉解释为严格长期因果效应；没有修改算法或据此追加采样。
''')
    save('典型成功失败案例.md','\n'.join(cases))
    save('下一阶段方向判断.md',f'''# 是否将 State Grounding 作为下一阶段方向

**本轮不确认其为已经隔离的主要瓶颈，不直接开发新控制器。**

实验一 Correct 为 {correct}/336；实验二首步 B−A 为 {delta:+.2f} pp，未达到预登记的 +10 pp 明显改善标准。母轨迹三步主线增量 A/B 为 {rec['A']['main_reward']}/{rec['B']['main_reward']}。因此“LLM 根本不能理解拒绝，所以需要状态抽取”这条推论不获支持。

公开轨迹仍显示地面/手持/容器混淆、历史门锁被当成当前约束，以及写字工具、纸与容量的条件冲突。它们支持**在线状态应用和多条件协调存在问题**，不等于证明一个更强结构表示必然解决任务。解释正确而执行不稳，可同时来自信息检索、提示诱导、事实失效处理、资源调度、短视动作选择与规划；本轮没有把这些机制逐项隔离。

用户指引的 B/C 叙述均含“理解正确而结构补充无提升”，分类语义重叠。因此采用两条直接可核验的轴报告：**显式失败解释能力存在；所测结构化历史补充无明确收益**，不人为选一个字母制造更强结论。

普通工程问题包括对象标识符、手持与装备字段混用，以及解析/输出边界。研究候选包括随世界变化撤销旧事实、在不完整公开知识下管理多项前置条件、在材料/容量/战斗约束下保持可持续进展。它们目前是后续待验证问题，不是本轮已成立的新算法贡献。没有实现任何其中的机制，也没有启动 Stage28。

不能把现有 B 当成完美 Grounding Oracle：历史记录不做自动失效、配方知识未完整汇总、较长输入可能引入干扰。没有提升只能否定这份具体补充的明显短期收益，不能否定所有状态表示，也不能反过来用“实现可能不够好”忽略本轮负结果。
''')
    save('README.md','''# Stage27

- [实验报告](Stage27实验报告.md)
- [失败理解统计](PreconditionUnderstanding统计.md)
- [状态信息对比](StateSufficiency对比结果.md)
- [正负案例](典型成功失败案例.md)
- [研究判断](下一阶段方向判断.md)
- [预登记协议](预登记诊断协议.md)

代码 `scar_stage27/`；数据 `results/stage27/`。`failure_database.jsonl.gz` 为完整失败库；`paired_comparison.csv` 为 334 对表；`understanding_judgments.json` 为逐条规则/语义标签；`request_index.csv` 为每次付费请求索引。环境快照包含隐藏状态，只用于无网络原生核验，提示构建只读取公开 fixture。

可重算顺序：`python -m scar_stage27.grade`、`python -m scar_stage27.analyze`、`python -m scar_stage27.verify`、`python -m scar_stage27.report`、`python -m scar_stage27.audit`。这些命令均不新增模型调用。Python/依赖配置与 Stage26 相同。不要为重算报告运行 `batch`；它是产生新诊断回答的入口，已付费请求在私有 runtime 中有缓存。
''')
    # Standalone, exportable plots; no model-generated illustrations.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,4));groups=['all','parent','branches'];x=list(range(3));w=.36
    for offset,c,color in [(-w/2,'A','#4477AA'),(w/2,'B','#CC6677')]:
        values=[100*summary['action_groups'][g][c]['accepted']/summary['action_groups'][g][c]['n'] for g in groups]
        ax.bar([i+offset for i in x],values,w,label=c,color=color)
        for i,v in enumerate(values):ax.text(i+offset,v+1,f'{v:.1f}%',ha='center',fontsize=9)
    ax.set_xticks(x,['All checkpoints','Parent only','Dependent branches']);ax.set_ylim(0,105);ax.set_ylabel('Native acceptance (%)');ax.legend();ax.set_title('Stage27: paired post-rejection proposals (one parent)');fig.tight_layout()
    (REPORTS/'figures').mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(REPORTS/'figures'/f'paired_acceptance.{ext}',dpi=180)
    plt.close(fig)

if __name__=='__main__':main()
