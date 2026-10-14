"""Recomputable evidence tables and Chinese Stage22-B reports; zero API."""
import csv
import json
import re
from collections import Counter
from .common import *
from .analyze import FACTS,spans

LABEL={'Stage18-Fixed':'Stage18-Fixed','ShortTermMemoryAgent':'STM','LongContextAgent':'LongContext'}
CORE_FACTS=['oak_rod_objective','oak_rod_recipe_relation','oak_rod_exact_recipe','oak_log_visible_library',
    'workbench_visible_hall','copper_sword_objective','librarian_objective','kindness_disclosure','stalls_objective','torch_objective']
FACT_LABEL={'tutorial_finished':'教程结束','guide_offer':'向导主动提供任务提醒',
    'oak_rod_objective':'制作 oak_rod 的主线指令','oak_rod_recipe_relation':'oak_rod 由 oak_log 制作',
    'oak_rod_exact_recipe':'精确配方 0.5 oak_log','oak_rod_station_rejection':'制作拒绝揭示缺少工作台',
    'oak_log_visible_library':'library 地面可见 oak_log','workbench_visible_hall':'hall 地面可见 workbench',
    'copper_sword_objective':'制作 copper_sword 的指令','librarian_objective':'前往图书管理员所在区域的指令',
    'kindness_disclosure':'纸条需写 kindness','stalls_objective':'前往 stalls 的指令','torch_objective':'制作火把的指令',
    'chapter_1_complete':'第一章完成事件','chapter_2_intro':'第二章介绍事件'}


def csvwrite(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def md(name,parts):
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/name).write_text('\n'.join(line.rstrip() for line in '\n\n'.join(parts).splitlines())+'\n')


def ev(method,step):return f'[a{step}](关键证据原文.md#{method.lower()}-a{step:03d})'


def evidence(audits,agents):
    index=[];compact=[]
    selected={
      'Stage18-Fixed':[5,11,17,18,21,30,31,32,33,35,37,40,51,52,63,64,65,67,68,69,70,93,100,179,183,184,200,216,270,271,277,300],
      'LongContextAgent':[28,29,31,32,33,34,35,36,37,38,39,52,53,56,63,66,84,85,94,95,96,104,117,118,121,131,165,205,223,236,300],
      'ShortTermMemoryAgent':[28,32,34,35,36,37,38,39,40,41,44,45,46,50,51,52,66,77,78,81,166,186,268,300]}
    excerpt=['# 关键证据原文','这是完整 900 步审计的便捷摘录，不是筛选后的实验样本。所有步骤和内部状态见 [结果目录](../../results/stage22b/)。aN 表示第 N 个实际环境动作；公开反馈在 aN 后产生，并进入 aN+1 的决策。Markdown 展示仅去掉行尾空格；压缩 JSONL 与 CSV 的 observation_json/feedback_json 保留逐字原文。']
    for method in METHODS:
        for r,a in zip(audits[method],agents[method]):
            n=r['step'];d=a['decision'];proposal=d['proposed_action'] if d else r['selected_action']
            base=dict(method=method,step=n,evidence_id=r['evidence_id'],request_id=r['model_request_id'],
                agent_state_jsonl=f'agent_audit/{method}.jsonl.gz:{n}',public_jsonl=f'step_audit/{method}.jsonl.gz:{n}',
                native_jsonl=f'native/{method}.jsonl.gz:{n}' if r['hidden_world_available'] else '',
                original_trajectory=f'../stage22/runs/mark__{method}/trajectory.jsonl.gz:{n}',
                original_request=f'../stage22/runs/mark__{method}/requests.jsonl.gz:{n}')
            index.append(base)
            compact.append(dict(method=method,step=n,agent_goal=r['agent_internal_goal'],
                last_public_instruction=json.dumps(r['public_objective_before'],ensure_ascii=False),
                actual_quest=json.dumps(r['actual_quest_before'],ensure_ascii=False),
                location_before=r['public_before']['location'],location_after=r['public_after']['location'],
                hands_before=json.dumps(r['public_before']['hands'],ensure_ascii=False),
                hands_after=json.dumps(r['public_after']['hands'],ensure_ascii=False),
                proposal=proposal,actual_action=r['selected_action'],overridden=proposal!=r['selected_action'],
                arbitration=d['stage18']['reason'] if d else '',
                public_world_delta=json.dumps(r['public_world_delta'],ensure_ascii=False),
                native_verified=r['hidden_world_available'],quest_score=r['scores']['quest'],
                observation_json=json.dumps(r['observation'],ensure_ascii=False),
                feedback_json=json.dumps(r['feedback'],ensure_ascii=False),
                saved_state=base['agent_state_jsonl'],history_jsonl=base['public_jsonl']))
            if n not in selected[method]:continue
            excerpt += [f'<a id="{method.lower()}-a{n:03d}"></a>\n## {LABEL[method]} a{n}',
                f"实际动作：`{r['selected_action']}`；原提案：`{proposal}`；主线累计：{r['scores']['quest']}。\n\n"
                f"内部显式目标：`{r['agent_internal_goal']}`（基线为 None，不能据此断言模型没有目标）。完整内部状态与历史：`{base['agent_state_jsonl']}`。",
                '动作前 observation：\n\n```text\n'+r['observation']['text'].strip()+'\n```',
                '原模型 reasoning：\n\n```text\n'+str(r.get('model_reasoning') or '(响应缺少可解析 reasoning；见原始 request)')+'\n```',
                '动作后原始反馈：\n\n```text\n'+r['feedback']['text'].strip()+'\n```']
            if d:excerpt += ['控制器公开判断摘录：\n\n```json\n'+json.dumps(dict(
                target=a['internal_before']['controller']['target'],goal_query=d['execution_context']['goal'],
                original_s1=d['stage18']['original_s1_candidate'],bounded=d['stage18']['bounded_candidate'],
                reason=d['stage18']['reason'],assessments=d['stage18']['assessments']),ensure_ascii=False,indent=2)+'\n```']
    csvwrite(RESULTS/'evidence_index.csv',index);csvwrite(RESULTS/'step_ledger.csv',compact)
    md('关键证据原文.md',excerpt)


def contrasts(agents):
    prior=read(source('Stage18-Fixed')/'initial_public.json')['observation']['text']
    prior_by_step={}
    for r in agents['Stage18-Fixed']:
        prior_by_step[r['step']]=prior;prior+='\n'+r['feedback']['text']
    all_cf=[]
    for i,r in enumerate(rows(ROOT/'results/stage22/same_state_local_contrasts.jsonl.gz'),1):
        if r['game']!='mark':continue
        n=r['step'];actual=agents['Stage18-Fixed'][n-1]
        assert r['before_hash']==actual['original_state_hash_before'] and r['actual']['feedback']==actual['feedback']
        new=[k for k,p in FACTS.items() if not re.search(p,prior_by_step[n]) and re.search(p,r['alternate']['feedback']['text']) and not re.search(p,r['actual']['feedback']['text'])]
        all_cf.append(dict(step=n,evidence_id=r['evidence_id'],executed=r['executed'],proposal=r['proposal'],
            original_source_line=i,same_state_hash=r['before_hash'],
            actual_advantage_dimensions=r['actual_advantage_dimensions'],proposal_advantage_dimensions=r['proposal_advantage_dimensions'],
            proposal_additional_public_disclosures=new,actual_feedback=r['actual']['feedback'],alternate_feedback=r['alternate']['feedback'],
            actual_hp=r['actual']['hp'],alternate_hp=r['alternate']['hp'],scope=r['scope']))
    assert len(all_cf)==214
    gzwrite(RESULTS/'mark_controller_contrasts.jsonl.gz',all_cf)
    result=dict(total_overrides=214,reused_native_branches=214,new_native_one_action_branches=0,
        actual_advantage_steps=[r['step'] for r in all_cf if r['actual_advantage_dimensions']],
        proposal_advantage_steps=[r['step'] for r in all_cf if r['proposal_advantage_dimensions']],
        proposal_new_knowledge_steps=[r['step'] for r in all_cf if r['proposal_additional_public_disclosures']],
        scope='One-step dimensions, not independent trials or a recoverable total-score estimate')
    write(RESULTS/'controller_contrasts_summary.json',result)
    return all_cf,result


def figures(audits,knowledge):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,1,figsize=(10,5.8),sharex=True,gridspec_kw={'height_ratios':[2,1.25]},layout='constrained')
    palette=['#c54c40','#568f57','#376d9d']
    for method,color in zip(METHODS,palette):axes[0].step([r['step'] for r in audits[method]],[r['scores']['quest'] for r in audits[method]],where='post',label=LABEL[method],color=color,lw=1.8)
    axes[0].set_ylabel('Cumulative main-quest reward');axes[0].legend(loc='upper left',ncol=3,fontsize=9);axes[0].grid(alpha=.2)
    heat=np.array([[r['selected_action']=='wait' for r in audits['Stage18-Fixed']],
        [r['objective_in_model_context'] for r in knowledge],
        [bool(r['internal_literal_evidence_paths']) for r in knowledge],
        [r['goal_completed_in_tutorial_but_still_target'] for r in knowledge]],dtype=int)
    axes[1].imshow(heat,aspect='auto',interpolation='nearest',extent=[.5,300.5,3.5,-.5],cmap='Blues',vmin=0,vmax=1)
    axes[1].set_yticks(range(4),['Actual wait','Oak objective in prompt','Oak objective in saved state','Stale enter-hall goal'])
    axes[1].set_xlabel('Original environment action / decision index')
    for ax in axes:
        ax.set_xlim(1,300)
        for n in [31,63]:ax.axvline(n,color='#777777',ls=':',lw=.9)
    figdir=REPORTS/'figures';figdir.mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(figdir/f'mark_diagnostic.{ext}',dpi=180)
    plt.close(fig)
    csvwrite(RESULTS/'figure_data.csv',[dict(step=n,**{LABEL[m]:audits[m][n-1]['scores']['quest'] for m in METHODS},
        scar_wait=bool(heat[0,n-1]),objective_in_prompt=bool(heat[1,n-1]),objective_in_saved_state=bool(heat[2,n-1]),stale_goal=bool(heat[3,n-1])) for n in range(1,301)])


def main():
    forbid_network();check_freeze()
    metrics=read(RESULTS/'metrics.json');ms={m['method']:m for m in metrics};sc=ms['Stage18-Fixed']
    audits={m:rows(RESULTS/'step_audit'/f'{m}.jsonl.gz') for m in METHODS}
    agents={m:rows(RESULTS/'agent_audit'/f'{m}.jsonl.gz') for m in METHODS}
    knowledge=rows(RESULTS/'stage18_information_use.jsonl.gz')
    facts=read(RESULTS/'information_matrix.json');fm={(r['method'],r['fact']):r for r in facts}
    eng=read(RESULTS/'engineering_checks.json');witness=read(RESULTS/'public_recovery_witnesses_summary.json')
    evidence(audits,agents);cf,cs=contrasts(agents);figures(audits,knowledge)
    classes=dict(A_steps=[r['step'] for r in knowledge if 'A_explicit_goal_text_not_retained' in r['classes']],
        B_steps=[r['step'] for r in knowledge if 'B_goal_evidence_retained_but_goal_channel_stale' in r['classes']],
        B_saved_but_not_in_prompt_steps=[r['step'] for r in knowledge if 'B_goal_evidence_retained_but_goal_channel_stale' in r['classes'] and not r['objective_in_model_context']],
        C_not_obtained_core_facts=[k for k in CORE_FACTS if fm['Stage18-Fixed',k]['first_public_step'] is None],
        C_core_fact_denominator=CORE_FACTS,D_verified_runtime_failures=[],
        scope='A/B use 237 decisions after first explicit oak objective. C uses 10 post-hoc public facts, not independent tasks. D means no confirmed correct-action transport failure, not proof of absence.')
    write(RESULTS/'classification.json',classes)
    method_table=table(['方法','主线奖励','第一章完成','全主线完成','实际动作','wait','最长连续 wait','教程结束'],
        [[LABEL[m['method']],m['main_quest'],next((r['step'] for r in m['quest_gains'] if r['total']==10),'未达'),m['main_quest_complete'],m['steps'],m['wait_actions'],m['longest_wait'],m['tutorial_finished_step']] for m in metrics])
    md('mark环境失败案例分析.md',[
      '# mark 环境失败案例分析',
      '**最终分类：DESIGN_LIMIT。** 当前直接证据指向过期目标及围绕该目标工作的控制与记忆表示；未确认会丢弃 observation、动作或已保存记忆的运行时故障。保持 Stage18-Fixed 及所有既有轨迹不变，本轮没有新模型请求、正式重跑或补丁版。',
      '指引中“LongContext 成功完成 mark”需限定为**拿到 10 个主线阶段奖励并完成第一章**。STM、LongContext 在 a300 的 `main_quest_progress.complete` 均为 false，不能写成全游戏通关。',method_table,
      '## 冻结范围与审计完整性',
      '来源为 Stage22 提交 `4696a5ce734f9cfbf4c99c39e52412f43c0cd3be`，引擎 `248430692a9d4a61d38c6c03ab2126287faaf450`。4368 个已有项目文件及 278 个官方源码文件按 SHA-256 核验不变。三方法各 300 步，共 900 步的 observation、原回复、动作、完整保存状态、历史动作和公开物品/位置变化已整理。使用原回复重构时，900 次请求上下文与动作逐字相同，三个最终记忆及 save/load 回环一致。未观察到的 LLM 隐状态不在审计能力内。',
      '原生全状态严格回放：Stage18 300、LongContext 300、STM 224，共 824 步。STM a225 反馈、奖励、done 相同但全状态哈希不同，随后 76 步只使用原始公开轨迹与精确重构的 Agent 状态，隐藏世界变化标为不可用。未固定 Python 哈希顺序是既有可重复性风险，不能未经隔离就认定本次差异的唯一原因。分析器曾修正深拷贝归档，事件保存在 `analysis_events.json`；最终统计使用不可变快照核验后的回放，保留失败结果。',
      '完整字段和逐行索引见 [step_ledger.csv](../../results/stage22b/step_ledger.csv)、[evidence_index.csv](../../results/stage22b/evidence_index.csv)。公开容器数量是最后一次可见记录，不能当成隐藏当前库存。基线没有结构化目标字段；“最新公开指令”“事后环境阶段”“模型 reasoning”分别记录，不把其中任何一项伪称为 LLM 的真实内部目标。',
      '## 失败如何形成',
      '1. 教程 a30 要求 `enter hall`，a31 正确进入大厅并收到 `Tutorial Finished.`；此后旧目标一直保留到 a300。a31–300 同一目标持续 270 次决策，其中 a32–300 共 269 次已过期。\n2. a32 在 library 看见 oak_log 和主动提醒任务的 remy。a33、a35 原模型提议 `talk to remy`，控制器改为 `enter hall`。两条同状态原生反事实都能当场取得 oak_rod 指令，确认的是局部知识机会损失，不是整局 10 分的因果解释。\n3. a37 拾取 paper_0，a40 拾取 goblin_token，双手被占。a41–50 改做检查，a51 尝试进入锁住的 armory，a52–62 连续 wait。\n4. a63 终于与 remy 对话，公开 “Craft an oak rod” 和所需 oak_log。但目标字段仍是 `enter hall`，a65、a67 的拾取提案又有真实手部容量障碍，缺少先腾出手再取材的有效执行。\n5. a68、a69 原模型提出进入 library，控制器保留 wait；至 a70，第一次任务指令已从 STM5 与其他当时保存状态中消失。后续重复获知任务也未改变目标。\n6. a183 的任务对话因同时出现受伤而进入后果记录，之后可以在保存状态找到指令，但事实摘要未将它作为当前目标送入模型。持续保存本身没有解决决策触发。',
      '对应原文：'+', '.join(ev('Stage18-Fixed',n) for n in [31,32,33,35,40,63,65,67,68,70,183,200,300])+'。',
      '![主线奖励、wait、指令可见性和旧目标](figures/mark_diagnostic.png)',
      '图下半部逐决策展示原始事实；蓝色表示该条件成立。模型输入中的任务指令只按明确原文定位，不代表模型的潜在理解。上下两部分均来自原轨迹，没有用分支结果替换实际分数。',
      '## 首次不可恢复错误：当前证据不能定位',
      '最早清楚的教程后表示偏差是 a32 仍保留已完成的 `enter hall`；最早有同状态证据的主线信息获取损失是 a33。这两者都不是已经证明的不可恢复状态。用预登记的七个实际状态做公开信息人工诊断路径，均能取得第一阶段奖励：',
      table(['原动作前','剩余原预算','分支动作','增加主线奖励','仍在原预算内'],[[w['start_before_action'],w['original_remaining_actions'],w['branch_actions'],w['new_quest_reward'],w['within_original_budget']] for w in witness]),
      '这些路径只使用已公开的 NPC 指令、可见物品和此前看见的两个房间；必要时先 drop 腾出手，再取 oak_log、回 workbench、craft 并拾取 oak_rod。a33/a35 的首步沿用原 LLM 对话提案。每条分支从完全相同的物理状态和 RNG 状态出发，并确认未改动正式回放父状态。所有七条分支都保留，详见 [完整分支](../../results/stage22b/public_recovery_witnesses.jsonl.gz)。',
      '这只是“第一阶段仍可达”的存在性证据，不是自动 Agent 的表现，不是 Stage18-Fixed-Patched 的 A/B，也不证明余下整条主线能在原 300 步内完成。a300 的 7 步分支超出原剩余 1 步，单独标注，不能计作原预算内恢复。没有遍历整条任务图或证明最短剩余路径，因此不声称找到了首次全任务不可恢复错误。',
      '## 状态滞留与探索',
      table(['指标','Stage18','STM','LongContext'],[[name,*[m[key] for m in metrics]] for name,key in [
        ('wait 总数','wait_actions'),('wait 连续块数','wait_blocks'),('连续 ≥5 步 wait 块数','long_wait_blocks_5'),('这些长 wait 块消耗动作','long_wait_actions_5'),('最长 wait','longest_wait'),('相邻同动作重复次数','same_action_repeat_steps')]]),
      'Stage18 190 次 wait 中，原 LLM 仅提议 wait 2 次，其余 188 次由覆盖产生；总覆盖 214/300。12 个长 wait 段消耗 164 步，最长 a216–242 共 27 步。全 300 次决策 FIFO 均为空，exploration_spent 最大为 0，**不是 FIFO 堵塞或探索额度耗尽**。同动作/周期重复只是机械计数，连续攻击可能必要，不能一律判为浪费。',
      '256 次决策中人已经在 hall，`get_goal_status()` 仍按“持有 hall 物品至少 1 个”返回 complete=false。这是制作物品式目标表示用于移动任务的语义失配，不是世界没有上报位置。非教程区域访问数为 Stage18 2、STM 10、LongContext 6。Stage18 已到过取材 library，也看过 hall 的工作台，所以第一阶段不能归因为没有探索到所需房间；更晚的区域缺失与第一阶段停滞相互关联，不能算成独立根因。',
      '闭环证据为：旧 `enter hall` → hall 被当作物品需求 → 对话/移动不构成 known_goal_progress → 重复候选被限制后 wait → 未推进主线 → 旧目标继续保留。该链由状态与决策日志支持；尚无完整政策消融为各环分配整局因果贡献。'])
    info_table=table(['公开事实/事件首次出现','Stage18','STM','LongContext'],[[FACT_LABEL[k],*[fm[m,k]['first_public_step'] or '未出现' for m in METHODS]] for k in FACT_LABEL])
    md('Stage18与LongContext路径差异.md',[
      '# Stage18 与 LongContext 路径差异',
      '这里比较的是 LongContext 完成第一章的路径，不是完整 mark 通关。跨方法只有一个随机模型样本，初始配方展示顺序未完全控制；路径比较为描述性证据。只有单独列出的同状态原生分支支持局部因果判断。',
      '## 信息第一次出现',info_table,
      '教程已让 Stage18 在 a21 保存 oak_rod→oak_log 的配方名称关系，不能写成“oak_rod 配方完全不知道”。原公开名字关系没有精确数量，a63 NPC 所说需要 1 oak_log 也不能当作精确消耗 1。LongContext a34 拾取木材后得到 `oak_rod (0.5 oak_log)`；a35 制作失败公开缺少 workbench，再于 a36 回 hall、a37 制作、a38 拾取。Stage18 没有执行到这些经验。',
      '## 关键分歧与反馈利用',
      table(['阶段','LongContext 实际行为','Stage18 实际行为','证据范围'],[
        ['教程结束后找目标','a31 获得向导提醒，a32 talk to remy','a32 获得提醒，a33/35 talk 提案被改回 hall；a63 才对话','a33/35 同状态分支证实目标知识机会损失'],
        ['切换到 oak_rod 制作','a33 前往 library；a34 取材','a64 library；a65/67 拾取受双手占用约束，实际回 hall','模型原提案也不是当前可成功执行的拾取'],
        ['发现工作台条件并恢复','a35 制作被拒；a36 hall；a37 成功；a38 收取','hall 工作台一直公开，但没有执行 oak_rod 制作','a35→36 是首段明确反馈修正；不是首个全局错误消除证明'],
        ['第一奖励后的新目标','a39 NPC 提供 copper_sword 指令','没有第一奖励，未收到此下一阶段指令','不能把下游未披露当独立记忆丢失'],
        ['容量/锁门绕过','a52/53 重试锁门、a56 手满、a63–66 往返；a84 drop pen、a85 pick small_pouch_0，最后 a94 取得铜剑','a40 起纸张与战利品占手；没有形成推进 oak_rod 的收纳/腾手路径','LongContext 也有无效重复，不能只选其顺利片段'],
        ['字词条件','a96 得到 kindness，a104 写入 paper_0','从未收到该主线条件','属于下游信息未获得'],
        ['第一章完成与剩余预算','a165 累计 10 分；后续第二章仍未完成，a223–236 有拾取/丢弃循环','a300 仍在最初阶段','不存在“长记忆解决全部长程任务”的证据']]),
      '关键原文：'+', '.join(ev('LongContextAgent',n) for n in [32,34,35,36,37,38,39,52,53,56,84,85,94,96,104,165,223,236])+'。',
      '“第一次调整目标”按可观察行为定义：a32 收到任务后，a33–38 转入相应取材、制作与收取；拿到第一奖励后 a39 寻求下一阶段。LongContext 没有单独 goal 字段，不能把行为判断冒充读到了内部目标变量。其全历史保存会让 a32 指令进入后续每次模型输入，但这不等同于模型每次都有效利用。',
      'STM 提供重要对照：它也是 5 条短记忆，仍在 a35 drop pen 腾手，a37 得到工作台拒绝后 a38 回 hall，a40 取得 oak_rod；a44 收纳 paper_0、a45 拾 key、a46 解锁 armory，a50 获得铜剑。最终 a186 完成第一章。这反驳了“只要 STM5 就必然拿不到第一阶段奖励”的解释，尚不足以隔离控制器和额外提示的独立效应。',
      '## 十次主线阶段奖励',
      table(['累计主线奖励','STM 动作/步骤','LongContext 动作/步骤'],[[i,
        f"a{ms['ShortTermMemoryAgent']['quest_gains'][i-1]['step']} {ms['ShortTermMemoryAgent']['quest_gains'][i-1]['action']}",
        f"a{ms['LongContextAgent']['quest_gains'][i-1]['step']} {ms['LongContextAgent']['quest_gains'][i-1]['action']}"] for i in range(1,11)]),
      '全部 20 次原始奖励事件连同完整反馈见 [quest_gain_events.json](../../results/stage22b/quest_gain_events.json)。Stage18 在 a1–300 无主线奖励事件；教程制作 key 的成功不计为这一主线目标进展。',
      '## 保存、登记、进入模型是三件事',
      'Stage18 第一次 oak_rod 指令在 a63 公开：a64 时它在当前 observation、表中 feedback 和后果暂存；a65–69 时在 STM5，a70 起这段原文在全部当时保存状态中找不到。a93 等后续对话再披露相同目标，但目标字段始终不变。a183 后原文进入持久 consequences 记录；例如 a200 的 `/controller/consequences/records/23/feedback` 仍含指令，却没有进入当次模型输入。',
      '九次披露在 a63、93、123、153、183、211、243、270、277。a64–300 共 237 次后续决策中，明确原指令有 141 次仍在保存状态/当前观测，只有 54 次进入模型输入，87 次保存但未入上下文；另 96 次原文既不在保存状态也不在当前观测。结构化事实摘要中出现该明确指令为 0 次，当前目标登记 oak_rod 为 0 次。用原文路径匹配可重算这些计数；不把措辞改写或潜在语义当成可观察变量。',
      '长期记忆并非唯一问题：公开配方名称关系持续登记，多个决策也确实看见任务指令，但控制器依然围绕 hall 仲裁。有效研究问题是“信息如何被登记成当前可执行目标，以及何时触发其使用”；本轮不实现新机制。'])
    md('失败类型分类统计.md',[
      '# 失败类型分类统计',
      '只有一个 Stage18 mark 失败局。下列数目是同一轨迹内的步骤或公开事实，不是多个独立失败样本，也不是可加成 100% 的因果归因。A/B 使用首次明确任务披露后的 a64–300 共 237 次决策；C 使用列出的 10 项事后知识清单；D 使用 900 次请求/执行审计及已验证原生范围。',
      table(['类别','可操作定义','数量','直接证据与限制'],[
        ['A 信息未保存','任务明确原文此前公开，但当前 observation 和所有已保存内部字符串均不含原文','96/237 次决策','a70 开始首段丢失；属于 STM5 和持久记录类别范围，非已证明的落盘 bug；不等于所有配方知识都丢失'],
        ['B 保存但未触发','明确任务原文仍在保存状态/当前 observation，但 controller.target 仍 enter hall','141/237 次决策','其中 54 次原文进模型、87 次未入模型；a64–69、a200 等；表示失配有直接证据，整局因果份额未隔离'],
        ['C 完全未获得','10 项公共知识清单中，全轨迹从未公开该项','6/10 项','精确 oak_rod 配方及后续五项任务指令/条件；后续五项受第一阶段未完成限制，不能作为五个独立探索失败'],
        ['D 信息/决定正确但执行失败','正确提案已下发，接口却丢弃、误解或错误执行','确认 0 项','900 动作和完整观测传递检查通过；不表示任何未覆盖隐藏状态问题均不存在']]),
      'C 的固定清单：'+', '.join(f'`{k}`' for k in CORE_FACTS)+'。未获得的是：'+', '.join(f'`{k}`' for k in classes['C_not_obtained_core_facts'])+'。工作台拒绝只是基线获得条件的一种途径，未经历拒绝不等于必然缺乏完成任务的知识，因此不把它加入 C 的必要知识计数。章完成事件也不作为知识条目分母。',
      'A 与 B 在这个严格原文字段定义下互斥并覆盖 237 次决策；同一局同时存在 A、B、C。最早 a32–63 的 32 次教程后决策发生在明确任务尚未实际公开前，单列为发现阶段，不硬套“已知目标记忆丢失”。元提示、oak_log 位置和名称配方已公开，仍可以支持去问 NPC。',
      '## 机械重复统计',
      table(['方法','同动作连续块（≥2）','相邻相同动作次数','最小周期 1–4 的极大重复段','非教程实际区域数'],[[LABEL[m['method']],m['same_action_blocks_2'],m['same_action_repeat_steps'],len(m['exact_periodic_loops']),len(m['visited_non_tutorial_areas'])] for m in metrics]),
      '相邻相同动作次数定义为每段连续同动作长度减一再求和。周期段至少重复两次，对相同周期删除完全包含的短段；不同周期和不同对齐方式可能重叠，不相加估计损失。例：Stage18 a31–34 与 a32–35 是同一往返段的不同对齐，不算两个独立错误。连续攻击、吃食物或必要的分批存入可能有效。原始所有周期、动作段与 wait 段均在 `metrics.json`。',
      'Stage18 的长 wait 全部列出：',table(['起始动作','结束动作','长度'],[[x['start'],x['end'],x['length']] for x in sc['wait_runs'] if x['length']>=5]),
      '## 控制覆盖的正负对照',
      table(['原动作','LLM 提案 → 实际','同状态原生证据','能支持的结论'],[
        ['a5/a11/a17','按教程存入 → 拾取/缩减存入','原提案能让教程阶段前进，实际该步未前进','局部教程机会损失；其中 a17 是原设计的一次有界存入，不是 JSON 解析错量'],
        ['a18','pick up coin → store 1 coin inventory','实际动作推进教程，原拾取因手满失败','控制器确有一次局部有益修正；它发生在前面延误后的状态'],
        ['a33/a35','talk to remy → enter hall','原提案获得 oak_rod 指令，实际没有；当步奖励两者都为 0','已验证局部知识获取损失，奖励单指标会漏掉'],
        ['a65/a67','pick up oak_log → enter hall','原拾取同样因手满失败','不能称为有用拾取被压制；仍需多步腾手执行'],
        ['a179/a180/a181','attack fen_cutthroat_8 → wait','原攻击击败敌人，实际 wait；a179 原分支 HP47，实际 HP34','局部战斗/存活损失；同一敌人多步机会，不能相加为三次独立收益']]),
      f"全部 {cs['total_overrides']} 次覆盖均保留，没有只挑负例。沿用 Stage22 单步奖励/教程维度，实际动作占优步骤为 {cs['actual_advantage_steps']}；原提案占优步骤为 {cs['proposal_advantage_steps']}；本轮补充的新任务知识机会为 {cs['proposal_new_knowledge_steps']}。这些维度不完备，没有优势标记不代表两个动作完全等价。",
      '机器可重算结果：[classification.json](../../results/stage22b/classification.json)、[逐步信息用途](../../results/stage22b/stage18_information_use.jsonl.gz)、[214 个覆盖反事实](../../results/stage22b/mark_controller_contrasts.jsonl.gz)。'])
    md('工程问题排查与修复边界.md',[
      '# 工程问题排查与修复边界',
      '没有确认可在本轮约束内修复、并足以解释 mark 主线 0 分的传输、动作下发或状态持久化故障。发现了明确的目标表示和控制适用范围问题，不能为了把它叫作工程修复而修改冻结的目标逻辑。未建立 Stage18-Fixed-Patched，也没有伪称完成补丁 A/B。',
      table(['排查项','证据/复现','结果与影响范围','最小处置/本轮是否修改'],[
        ['特殊 API / 环境动作','原生 step(dict) 后 update_scores；Stage18 300 和 LC300 精确哈希；STM224 前缀通过','没有 mark 专属调用接口丢动作的证据；a225 以后 STM 隐藏世界变化不做强断言','保留现有调用；无修改'],
        ['action 解析','逐个用官方 response_parser 解析原回复，900 次与原 proposal/动作一致','Stage18 无 fallback；STM a268 缺 action；LC a205 空白 JSON；后两者在第一章完成之后','沿用官方 wait fallback；不重新采样，不把生成缺字段算执行接口故障'],
        ['observation 传递','900/900 当步完整 observation.text 是原请求的子串；与原提示精确重构一致','没有遗漏 NPC 文本、房间位置或裁剪观测的证据','不改传输'],
        ['memory 更新/落盘','900 步精确请求重构；三个最终记忆及 save/load 回环一致','没有已经保存记录意外丢失；STM5 正常淘汰并不保证任务指令持久化','不扩记忆、不添加任务记录类别'],
        ['token/历史截断','全部原请求 status=ok、finish_reason=stop；LC 完整历史单调追加并逐字进入输入','无输入超限/应用端裁剪证据；Stage18 原有 48 条/6000 字符事实选择确实限制可见记录','保留原配置；任务对话未形成结构化目标并非仅把上限调大可证明解决'],
        ['prompt 拼接','同一游戏各方法共享官方系统/动作提示，Stage18 只附注册事实；900 输入逐字核对','跨游戏官方动作空间有差异：remnant 有 lockpick 等，不要求三游戏提示相同','无 mark 特定提示补丁'],
        ['wait','190 实际 wait，原提案 wait2；a68/69 exact arbitration 复现','主要来自 no_public_candidate 后结构化默认选择；不是 API 默认 wait 或动作词碰撞','修改回退和 UNKNOWN 仲裁属于策略改变，本轮不做'],
        ['目标生命周期','真实 a64 观测含 Craft an oak rod，PublicState.goal 仍 None；controller 保留 enter hall','原 regex 仅识别 Required action/Your task is/Objective；不会把 NPC 自然语言选作新目标','新增 NPC 语义目标转换、撤销旧目标会改目标规划，受本轮禁止'],
        ['完成状态类型','真实 a32/64/68 等状态在 hall，get_goal_status 对 hall 做 ownership 查询，complete=false','制作/持有式完成接口扩到移动和连续主线后的语义失配；不是地理信息没传到','一般任务的完成谓词、目标清除与后续选择需明确新协议；不加 mark 专用分支'],
        ['指令在存储中却未进入摘要','a200 consequences.records[23].feedback 含目标，原 render 仅优先携带伤害等已注册类别','记忆存在，但不是已选目标/配方类；确定的设计覆盖不足','把 NPC 指令抽为任务记忆或加触发机制是新记忆策略，本轮不做'],
        ['回放确定性','原生 STM a225 反馈等同、全状态 hash 不同；Python hashseed 在原跑未固定','影响复现置信度；不能据此解释实际 Stage18=0','未来协议固定 hashseed、集合排序和初态产物哈希；本轮不重跑或改官方引擎']]),
      '## 最小复现与冻结依据',
      '`python -m scar_stage22b.engineering` 使用保存的真实状态复现 7 个目标表示检查和 7 个仲裁检查，不调用模型、不修改控制器。输出 [engineering_checks.json](../../results/stage22b/engineering_checks.json)。逐请求全文/解码/费用检查见 [request_audit.jsonl.gz](../../results/stage22b/request_audit.jsonl.gz)。',
      '关键源码：`scar_v3/state.py:PublicState.observe` 的公开目标 regex；`scar_sequence/planner.py:Controller.observe` 仅在解析到非空新目标时更新；`scar_stage16/state.py:PublicRuleState.get_goal_status` 以持有物数量判定；`scar_stage18/execution_context.py:assess` 的 known_goal_progress 只为相关 craft/pick up/take out/store 赋真；`scar_stage18/arbitration.py:choose` 在证据未决时保留控制器；`scar_stage10/controller.py:choose` 无可接纳候选时 wait。',
      '这不是为了回避缺陷：`enter hall` 被当物品需求确实是不合适的语义。只是 Stage22 冻结协议已明确记录此能力边界，见 [既有工程审计](../stage22/工程修复与算法差异审计.md)：原 Stage18 接收外部制作目标，TTCL 仅启用已有 follow_public；“缺少可解析目标时不推断新目标”。更改多目标类型、NPC 指令转换和旧目标撤销会改变这项冻结方法的能力，不能作为无算法改变的补丁。单独让 location==hall 显示 complete 也尚未解决后续 oak_rod 目标从何而来的问题；没有未经 A/B 就声称它会提升分数。',
      '## 输入与费用核对（沿用旧实验账本）',
      table(['方法','原请求数','输入 token','输出 token','首/末输入','最大输入','usage 计价美元','cache-hit 输入比例'],[[LABEL[m['method']],m['requests'],m['input_tokens'],m['output_tokens'],f"{m['input_first']}/{m['input_last']}",m['input_max'],f"{m['cost_usd']:.9f}",f"{m['cache_hit_tokens']/m['input_tokens']:.1%}"] for m in eng['methods']]),
      '这是已经发生的 Stage22 费用，本轮新增请求、token 和模型费用均为 0。LongContext 输入 token 远多于 Stage18，但该次实际 usage 计价费用更低，因为输入缓存命中率和对应价格不同；不能宣称 Stage18 本例有实际费用优势。只讨论固定旧账本，不使用未来价格推算。',
      'Stage18 摘要最大 5942 字符，251 次决策可用记录多于选中记录；这是预设的证据选择，而非传输截断。oak_rod 明确任务从未成为结构化目标记录，因此既不能把缺失全部归因于 6000 字符限制，也不能断言提高上限足以解决它。',
      '## 修复与 A/B 门槛',
      '本轮工程修复门槛未满足，已执行补丁数 0、补丁 A/B 数 0。7 条人工可达路径和 214 个旧单步原生反事实是诊断证据，绝不标成补丁方法的成功率。分析归档代码的深拷贝修正只防止日志引用随回放变化，不改变任何实验动作、模型输入或方法分数。若将来授权新方法，须单独命名、冻结、按泛化游戏验证；本轮到诊断为止。'])
    md('500步评测建议与最终结论.md',[
      '# 500 步评测建议与最终结论',
      '**唯一最终分类：DESIGN_LIMIT。建议暂不进入 TTCL 500-step 正式评测。** 本轮没有算法改动、失败重跑、额外模型调用或补丁性能声明。',
      '主线 0 分最清楚的解释是当前方法对持续变化的自然语言任务缺乏适用的目标表示和更新通道。教程结束后 269 次仍保留 `enter hall`，256 次位置已满足却按物品持有判未完成。公开任务反复出现而未成为当前目标；控制仲裁把对话和路线行动排除在已知目标进展之外，188 个非 wait 原提案最终变为 wait。局部同状态反事实支持若干知识获取/战斗机会被压制，但不证明换掉一个模块就会拿到基线的全部 10 分。',
      '单独增加 200 步可能增加碰到 NPC、随机移动或机会行动的次数，但现有轨迹没有证据说明旧目标会因时间自行失效，最后 a283–300 仍连续 wait。七条离线人工路径表明环境并非早早物理无解，却不等同于原方法有能力执行这些路径；因此现在花费预算延长正式评测，无法有效检验一个已经明确的修复假设。',
      '## 什么已经知道、什么还不知道',
      table(['问题','结论','证据边界'],[
        ['只因缺少规则知识吗？','不是。名称配方、木材位置、工作台位置已公开，a63 后多次明确任务也公开','精确 oak_rod 数量未获得；下游主线条件确实未知，但很可能是早期不推进的结果'],
        ['只因长期记忆短吗？','不是。STM5 基线也拿到 10 分；Stage18 多次有明确目标信息却不执行','A 96 步原文丢失与 B141 步保存未触发都存在；没有记忆/控制器独立消融'],
        ['显式控制器有局部负效应吗？','有，a33/35 对话被改写导致失去当步目标知识；a179–181 有战斗损失','a65/67 拾取原提案本身手满失败，a18 控制器也有正作用；不能全盘把覆盖判坏'],
        ['基础工程传输坏了吗？','未发现。900 上下文/动作重构、最终记忆和 save/load 一致','原生 STM 只核验到224步，未覆盖范围不能做强工程保证'],
        ['算法显著不如基线吗？','本例明显落后，但不能作总体显著性结论','一游戏每方法一次采样；配方展示顺序、不同模型路径未严格成对控制'],
        ['是否只有 mark 特定规则问题？','mark 暴露了更一般的动态任务/移动目标表示缺口','跨游戏普遍性尚未验证，不能声称已证明通用新机制有效']]),
      '## 后续工作边界',
      '普通工程工作包括：固定运行时哈希顺序、保存可独立恢复的初态/RNG、给不支持的目标类型提供明确诊断、把各知识层和覆盖原因记录齐全。这些可以提升可复现性和可解释性，但本轮证据不支持把它们等同于性能提升。',
      '可能构成独立研究问题的是：公开任务从动作指令转为 NPC 自然语言后，如何确认旧目标失效并建立新的完成谓词；如何使持久保存的信息按当前任务被触发，而不是只写入日志；在知识不完备时，如何让信息获取行动与显式控制器的约束兼容。这些都需要新的研究协议，不能包装成 regex 修复或 mark 专用规则。此处仅列可检验问题，不实现新模块。',
      '恢复正式评测的前提应是：先确定改变的是工程契约还是算法机制；若确有工程补丁，独立 Patched 与原版 A/B，并同时检查原有制作任务不退化；若研究新目标/记忆机制，先在未参与设计的多游戏公开任务转移上冻结验证。之后再讨论统一的 500 步预算和更充分采样。当前 300 步、DeepSeek Flash 轨迹不是官方 Qwen/500 步排行结果，也不应直接并列排名。',
      '资料完整性：没有排除失败局或截掉基线后半程的循环；原轨迹、原请求和正式分数均保持不变。A/B/C 统计不是因果比例，人工分支不是算法提升，首次不可恢复全任务状态仍未定位。'])
    md('README.md',[
      '# Stage22-B：指引23 零新增模型调用诊断',
      '**结论：DESIGN_LIMIT；不启动 500 步正式评测。** 冻结 Stage18-Fixed，审计 mark 的 Stage18、STM、LongContext 共 900 步。原生全状态匹配 824 步；Stage18 与 LongContext 各300，STM224。新增模型请求/费用为 0；未修改算法，未跑补丁 A/B。',
      '- [mark 环境失败案例分析](mark环境失败案例分析.md)\n- [Stage18 与 LongContext 路径差异](Stage18与LongContext路径差异.md)\n- [失败类型分类统计](失败类型分类统计.md)\n- [工程问题排查与修复边界](工程问题排查与修复边界.md)\n- [500 步评测建议与最终结论](500步评测建议与最终结论.md)\n- [关键证据原文](关键证据原文.md)',
      '## 数据与统计口径',
      '`results/stage22b/step_audit/`：各300行，完整 observation、最新公开指令、事后实际阶段、所选动作、动作历史、反馈、公开库存/位置差分与世界状态引用。`agent_audit/`：各300行，完整保存状态前后、完整模型 messages、模型 reasoning 和控制决定。`native/`：只发布严格匹配的原生完整状态与变化；STM缺失后76步不补造。压缩 JSONL 从1开始的行号与动作号一致。',
      '[逐步CSV台账](../../results/stage22b/step_ledger.csv)、[900步证据索引](../../results/stage22b/evidence_index.csv)、[指标JSON](../../results/stage22b/metrics.json)、[信息首次公开](../../results/stage22b/information_matrix.json)、[工程检查](../../results/stage22b/engineering_checks.json)、[分类统计](../../results/stage22b/classification.json)、[七条公开可达分支](../../results/stage22b/public_recovery_witnesses_summary.json)均可重算。`mark_controller_contrasts.jsonl.gz` 保留全部214次旧原生覆盖反事实，并补充目标知识获取维度。',
      '隐藏世界与完整任务定义仅用于事后阶段标注、原生哈希/反馈验证；没有进入正式 Agent 输入。人工可达分支用原公开文本选择动作，原生引擎自然负责执行隐藏规则。它只证明第一阶段可达，不是补丁政策。所有方法主线 complete 均为 false；两基线的10分指完成第一章。',
      '## 重算',
      '使用已准备的官方引擎和原始结果，无需 API 密钥。导出路径后依次执行：\n\n```bash\nexport AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey_stage22\nexport PYTHONPATH="$PWD:$AGENTODYSSEY_ROOT"\nexport HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1\n/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.analyze\n/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.engineering\n/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.report\n/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.verify\n```',
      '如需从原数据重构 Agent，按三个方法分别执行 `python -m scar_stage22b.reconstruct --method METHOD`；如需重新原生回放，执行 `python -m scar_stage22b.native --method METHOD`。它们从 `results/stage22/runs/mark__METHOD` 读取，不依赖未上传的付费请求缓存；所有分析入口均禁止网络连接。原始 Python 哈希顺序未固定，所以重新原生回放可能在不同步骤停止，脚本必须保留首个不一致，不允许反复重试到匹配为止。重算现有统计不需要重新原生回放。',
      '分析期间的快照深拷贝修正和原始/最终回放收据见 `analysis_events.json`。源码哈希及成品校验见 `verification.json` 与 `artifact_manifest.json`；压缩文件的 gzip 时间戳可能随重新生成改变，但统计和记录内容应一致。原 Stage22 的完整轨迹、模型请求、配置和结果保持原提交，不上传下载的引擎、依赖或密钥。'])
    write(RESULTS/'diagnostic_conclusion.json',dict(verdict='DESIGN_LIMIT',proceed_to_500_steps=False,
        audited_decisions=900,native_verified_steps=824,old_overrides_reused=214,
        manual_first_stage_witnesses=len(witness),manual_witness_actions=sum(r['branch_actions'] for r in witness),
        full_quest_recovery_proven=False,earliest_full_quest_irrecoverable_step=None,
        algorithm_changes=0,patches=0,patched_ab_runs=0,new_formal_runs=0,new_model_requests=0,new_model_tokens=0,new_model_cost_usd=0))
    print(json.dumps(dict(reports=7,evidence_rows=900,verdict='DESIGN_LIMIT',new_api_calls=0)),flush=True)


if __name__=='__main__':main()
