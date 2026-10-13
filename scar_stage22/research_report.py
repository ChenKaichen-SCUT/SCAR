"""Recompute post-freeze research interpretation from all first-run artifacts."""
from collections import Counter
import json
import re
from .config import RESULTS,REPORTS,METHODS,GAMES
from .analyze import read,rows,write,gzwrite,table


def main():
    stats=read(RESULTS/'per_run.json');averages=read(RESULTS/'method_aggregates.json')
    verification=read(RESULTS/'verification.json');cf=rows(RESULTS/'same_state_local_contrasts.jsonl.gz')
    by={(s['game'],s['method']):s for s in stats}
    summaries=[];decisions=[];case_evidence=[]
    for game in GAMES:
        t=rows(RESULTS/'runs'/f'{game}__Stage18-Fixed'/'trajectory.jsonl.gz')
        contrasts=[r for r in cf if r['game']==game]
        targets=Counter(r['decision']['controller_before']['target'] for r in t)
        case_steps={'remnant':{5,11,17,18,29,36,58,86,87,300},
                    'mark':{5,11,17,18,31,179,180,181,300},
                    'metropolis':{6,31,32,33,34,35,45,50,70,74,85,90,91,100,122,175,244,300}}[game]
        case_evidence.extend(dict(evidence_id=f'{game}__Stage18-Fixed:a{r["step"]:03d}',
            source=f'results/stage22/runs/{game}__Stage18-Fixed/trajectory.jsonl.gz',line=r['step'],record=r)
            for r in t if r['step'] in case_steps)
        for r in t:
            d=r['decision'];a=d['stage18'];assess=a['assessments']['llm']
            decisions.append(dict(game=game,step=r['step'],evidence_id=f'{game}__Stage18-Fixed:a{r["step"]:03d}',
                proposal=d['proposed_action'],executed=r['action'],override=d['intercepted'],reason=a['reason'],
                proposal_assessment=assess,controller_target=d['controller_before']['target'],
                public_recipe_count=len(d['controller_before']['table']['recipes']),
                actual_reward=r['reward'],native_invalid=r['invalid_action']))
        summaries.append(dict(game=game,targets=dict(targets),override_steps=sum(r['decision']['intercepted'] for r in t),
            verified_local_contrasts=len(contrasts),
            actual_advantage=Counter(k for r in contrasts for k in r['actual_advantage_dimensions']),
            proposal_advantage=Counter(k for r in contrasts for k in r['proposal_advantage_dimensions']),
            actual_advantage_ids=[r['evidence_id'] for r in contrasts if r['actual_advantage_dimensions']],
            proposal_advantage_ids=[r['evidence_id'] for r in contrasts if r['proposal_advantage_dimensions']]))
    write(RESULTS/'controller_diagnostic.json',summaries);gzwrite(RESULTS/'all_stage18_decisions.jsonl.gz',decisions)
    gzwrite(RESULTS/'case_evidence.jsonl.gz',case_evidence)
    replay_rows=[[r['game'],r['method'],r.get('verified_actions',r['actions'] if r['passed'] else 0),r['passed'],
                  (r.get('first_mismatch') or {}).get('step','—')] for r in verification['native_replays']]
    audit=['# 控制器贡献、失败诊断与证据边界','',
        '本分析不修改策略、不新增模型请求，不进行完整策略消融。动作编号从 1 起。所有原始提案、候选、条件证据、实际动作和上下文在原始轨迹中；900 条决策的精简索引见 `all_stage18_decisions.jsonl.gz`。','',
        table(['游戏','覆盖/300','严格同状态局部比较','实际动作优势维度计数','原提案优势维度计数'],
            [[s['game'],s['override_steps'],s['verified_local_contrasts'],dict(s['actual_advantage']),dict(s['proposal_advantage'])] for s in summaries]),'',
        '优势维度为单步官方主线/四辅助奖励、避免原生 invalid、教程阶段前进。未包含全部长期或生存收益；某一方没有这些优势不代表完全等价。反复出现的同一路径损失不是独立样本，不能把它们相加为可追回的最终分数。','',
        '## 可以证明与不能证明的贡献','',
        '可以证明原状态管理和条件仲裁确实参与了决策：全部 900 步按保存的原始回复重新构造，模型上下文、动作和控制器决策状态逐字核对。Stage18 三局原生 invalid 均为 0，但大量 wait 也会减少 invalid，因而不能把零 invalid 单独当成高效执行或有效规则利用。metropolis 的 7 分全部在 a31 前获得，主要得分动作由 LLM 提出并被保留；没有消融证据把这 7 分分配给状态管理模块。','',
        '局部正向证据也全部保留：remnant 与 mark 的 a18 把 `pick up coin` 改为 `store 1 coin inventory`，实际推进教程，而同状态原提案没有；remnant a86 把 `craft 1 paper` 改成 `enter armory`，实际增加 exploration=1。a18 位于此前数量覆盖造成的教程滞后之后，因此不能把这次补救独立算作整个控制器的净收益。这些小范围正效应不抵消或排除其他负面任务。','',
        '## remnant：目标通道与停滞','',
        'a29 完成教程并公开主线 The Tide and the Ember；a36 进入 library 获得第 1 个主线奖励。之后至 a300 没有新增主线奖励。结构化目标保留教程的 `enter hall`，与真实主线阶段分离。该现象可在 a36、a58、a87、a300 的 `controller_before.target` 直接核对。','',
        '全局有 179 次覆盖、148 次 wait，最长连续 wait 44 步。a58 的原提案 `attack goblin_warrior_2` 被改为 `enter library`；这只是候选分歧，是否局部有害必须看反事实收据，不能仅凭动词推测。a300 拾取 torch 的提案被默认 wait 覆盖，但该状态不在严格回放已验证前缀内，故不宣称已验证局部损失。五算法本游戏主线均只有 1 分，不能用此样本宣称 SCAR 在主线优于它们。','',
        '## mark：教程数量与未转化为主线行动','',
        'a5 原提案 `store 1 coin small_pouch_2` 改成 `pick up coin`；a11 `store 1 coin inventory` 再次改成拾取；a17 `store 2 coin inventory` 被压成 `store 1 coin inventory`。三个同状态原生分支均显示原提案会推进教程，而实际动作没有，属于已验证的局部执行损失。原收取/存储数量规则把教程动作误当制作式需求处理，不能用新策略事后修正本轮。','',
        'a31 已进入主线 The Borrowed Mark，后续内部目标却继续是 `enter hall`。a179–181 原提案 `attack fen_cutthroat_8` 均改成 wait；同状态分支原提案获得 1 个 unique_kill，实际没有。这是同一敌人相关的一组局部损失，不能当成三局独立发现。','',
        'Stage18 全局 214 次覆盖、190 次 wait，主线 0。STM 与 LongContext 都得到 10 分，最后新增主线奖励分别在 a186/a165。它们确实继续完成了主线阶段；不同模型样本及信息顺序使本比较不是“移除控制器就必然多得 10 分”的严格反事实。基线逐个得分动作、最终公开目标及失败反馈见本游戏报告。','',
        '## metropolis：已知材料、库存阻塞与过时路由判断','',
        'a32 的公开任务已包括获取武器、击败敌人、找到证人并记录口令。a33 拾取 gavel_timber 公开了 gavel_club 的材料关系；a34 双手为 2 timber，但尚无 binding_thread。a35 的 `craft 1 gavel_club` 被替换不能直接算有害，因为原提案材料不齐。a50 后陆续持有 gavel_splint 与 clerks_bench，双手容量成为持续约束；a70 制作提案和 a85/a90 拾取提案被拒绝有公开条件依据。','',
        '另一方面，a45 曾反馈 courtroom 门锁着；a91 原生公开反馈已明确写出 `The path to courtroom groans open as tonight\'s laws take effect.`，但后续 guard 仍为 REJECT。a122–a244（不含 a219–a221）的 120 个原提案 `enter courtroom` 被改成 wait；逐一从匹配的物理和 RNG 状态执行该提案时，原生环境实际允许进入，并各自获得 exploration=1。实际轨迹没有该进展。这证明这段覆盖存在局部损失，而且已有公开的条件变化没有撤销旧判断；不能把 120 次重复的一步机会相加成 120 分收益，也没有验证它能带来更多主线奖励。关键完整原始记录另存于 `case_evidence.jsonl.gz`。','',
        'a74 `enter market_square` 的公开门锁失败与 a100 同路线覆盖是另一情况；不能仅因为 courtroom 的 guard 有问题就断言所有路线拒绝都错。终局主线 7、197 次 wait，最长连续 wait 98 步，a31 后 269 步无新增主线奖励。LongContext 得 8 分，其他方法分数见主表；本游戏地点配置不完全配对，差额更不能解释为模块因果效应。','',
        '## 根因分类与研究边界','',
        table(['方面','证据支持程度','判断'],[
            ['知识发现/配方依赖','metropolis a33 已公开相关武器配方，后续材料与库存没协调；其他必要性未作 oracle 覆盖分析','不能概括为所有失败都是未发现配方'],
            ['目标规划/任务状态','remnant、mark 目标停在 enter hall；metropolis 原结构化目标空字符串','跨游戏直接证据较强；原制作控制器缺少对多阶段自然语言主线的适用性'],
            ['数量和容量','mark a5/a11/a17 局部原生反事实；metropolis 双手满','数量规则作用域及库存恢复是实际瓶颈'],
            ['控制器覆盖','mark 教程/战斗和 metropolis courtroom 局部反事实','存在已验证局部损失；无完整总效果消融'],
            ['长期记忆','目标未同步、旧门锁证据保持 REJECT','支持条件失效和状态表示问题，不能由单轮归为模型遗忘'],
            ['工程/协议','模型调用无终止性异常，官方初始化哈希顺序不固定','既有算法适用范围与评测复现问题须分开；不掩盖协议不足']]),'',
        '## 原生回放覆盖','',table(['游戏','方法','逐状态核验动作数','完整通过','首次不匹配动作'],replay_rows),'',
        '完整性核对覆盖全部正式轨迹，原生回放仅覆盖上表前缀。首次不一致的各项检查保存在 `verification.json`。分析代码未修补正式轨迹或把分歧后的反事实纳入已验证证据。公开知识统计仅为解析器观察到的配方名称，不等于 oracle 必要知识覆盖。']
    (REPORTS/'控制器贡献与失败诊断.md').write_text('\n'.join(audit)+'\n')
    total_cost=sum(s['cost_usd'] for s in stats);calls=sum(s['requests'] for s in stats)
    scar=next(s for s in averages if s['method']=='Stage18-Fixed')
    comparisons=[]
    for method in METHODS[1:]:
        other=next(s for s in averages if s['method']==method)
        comparisons.append([method,f"{scar['main_quest_mean']-other['main_quest_mean']:+.6f}",
            '/'.join(str(by[g,'Stage18-Fixed']['main_quest']-by[g,method]['main_quest']) for g in GAMES)])
    lc=next(s for s in averages if s['method']=='LongContextAgent')
    summary=['# 300 步实验科研总结','',
        '**结论：NO-GO——不建议直接把当前冻结版本延长到 500 步作为正式评测。** 这不是终止 SCAR 研究，也不是算法显著劣于所有基线的判断；它针对本轮原 Stage18 适配版及当前评测基础设施。','',
        f'指引要求的 15/15 个组合均完成，每局唯一一次、300 个真实环境动作，共 4500 步、{calls} 次模型请求。没有剔除负面任务、重跑游戏或添加后续阶段策略。usage 计价合计 **${total_cost:.6f}**；并非账户发票。全部三游戏主线仍未完整完成。','',
        '**300 步 / DeepSeek Flash / 非 TTCL 正式排名。** 官方排名还要求 500 步与合规 Qwen 模型。本轮使用官方原始评分，但不能因此称为官方排名结果。','',
        table(['方法','remnant','mark','metropolis','主线无权均值','辅助总和均值'],[
            [a['method'],*[by[g,a['method']]['main_quest'] for g in GAMES],f"{a['main_quest_mean']:.6f}",f"{a['supplementary_total_mean']:.6f}"] for a in averages]),'',
        '## Stage18-Fixed 是否高于基线','',table(['对照','主线均值差（Stage18−对照）','逐游戏差 remnant/mark/metropolis'],comparisons),'',
        '主线均值仅高于 NoMemory，低于 STM 和 LongContext；与 Voyager 的主线均值相同，但辅助均值 4.000000 低于 Voyager 的 5.666667，按官方并列规则居后。remnant 没有主线优势；mark 明显落后于 STM 和 LongContext 的该次轨迹；相对部分基线的正差主要来自 metropolis。单次轨迹和不完全配对的地点配置不支持跨游戏稳健优势或显著性推断。不能把 mark 的负面结果排除后再宣称有效。','',
        '## 状态与决策机制是否有实际贡献','',
        '结构化记忆确实进入模型上下文，仲裁确实改变动作，900 步离线保存回复重构逐项吻合。但参与执行不等于净收益。三局正式 invalid 都为 0，同时 wait 分别为 148/190/197，主线长期停滞。已发现教程数量覆盖和过期路由判断的局部负效应，详细动作与原生反事实见 [控制器诊断](控制器贡献与失败诊断.md)。当前没有模块消融，不能把正向总分归因于某个机制。','',
        '## 效率、成本与异常','',
        table(['方法','模型请求','输入token','输出token','usage美元','环境动作'],[[a['method'],a['requests'],a['input_tokens'],a['output_tokens'],f"{a['cost_usd']:.6f}",a['total_steps']] for a in averages]),'',
        f"Stage18 总输入较短，但本轮费用 ${scar['cost_usd']:.6f}，LongContext 为 ${lc['cost_usd']:.6f}。LongContext 三局输入缓存命中率约 98%，Stage18 约 4%；因此不能把压缩上下文直接等同于实际省钱。稳定追加历史更利于前缀缓存是符合记录的解释，未做缓存消融，不能证明唯一原因。",'',
        'LongContext 没有特殊摘要、截断或额度处理。请求 token 最大值、finish_reason、解析异常、每局时长和 Voyager 课程/critic/提炼额外调用全部纳入主表与 `model_anomalies.json`。坏输出沿用官方 parser 的 fallback，不付费重采样。总时长受 CPU 检索、并发与恢复影响，不作公平硬件速度排序。','',
        '## 为什么不直接进入 500 步','',
        '三个 Stage18 轨迹在 a36 / 无主线奖励 / a31 后分别停滞 264/300/269 步。预算用完时仍有大量未完成主线，但没有“再给 200 步便可完成”的证据。目标解析与动态主线不匹配、历史拒绝条件失效后仍阻断行动、容量恢复缺位，应先作为独立问题界定，而不能在这轮偷偷加入后续机制。','',
        '当前环境 seed=42 没有锁住进程哈希顺序，metropolis 主线地点实际不完全一致；支线和 DAG 集合顺序还限制逐步回放。正式比较前应先冻结并验证确定性初始化/恢复协议，并准备合规 Qwen 计算资源。这些是评测工程前提。具体公开句式未被解析、数量规则应用到教程存储动作等首先属于工程或表征适配问题，不应包装成研究贡献。任务切换时的目标状态、负面知识何时失效、未知可行行动与保守控制如何协调，才是可能需要跨场景独立验证的机制问题；本轮几个实例尚不能证明论文选题成立。本轮只提出问题，不开发下一阶段。','',
        '## 可复算与版本','',
        '原 Stage18：`2c2f7ecc03b0e326f26cdf85ce13e2415b374e33`；运行前冻结：`7621a9417294ce3cc1ce54d1b09bb049eae9e631`；官方环境：`248430692a9d4a61d38c6c03ab2126287faaf450`。最终发布提交见目录 README 和 GitHub 提交历史。','',
        '统计来自全部唯一原始轨迹。官方 `challenge_eval.py` 原始文本/JSON、真实请求、逐步反馈、最终配置、费用账本、曲线 CSV/PDF、决策证据索引和零 API 分析代码一并保存。冻结源文件和原有阶段文件逐一核对未变。原生全状态回放的通过范围单独报告，不能与所有原始数据的完整性核对混为一谈。']
    (REPORTS/'300步实验科研总结.md').write_text('\n'.join(summary)+'\n')
    anomalies=read(RESULTS/'model_anomalies.json')
    (REPORTS/'模型调用与解析异常.md').write_text('# 模型调用与解析异常\n\n'+
        table(['游戏','方法','动作步','同一步调用序号','异常','实际动作','下一步动作','request_id'],
              [[r['game'],r['method'],r['step'],r['ordinal'],'; '.join(r['issues']),r['actual_action'],r['next_action'],r['request_id']] for r in anomalies])+\
        '\n\n完整原始响应见 `results/stage22/model_anomalies.json` 和每局 requests。finish_reason=length 只能确认输出触及上限，不自动等同输入上下文超限。官方 action parser 对缺字段或解析失败返回 wait 提案，未重抽答案；Stage18 之后仍经过原控制器：remnant a99 将 fallback wait 改为 inspect rust_scrap，其余 10 次实际执行 wait。下一步沿原状态继续，没有重跑。非动作角色按官方默认处理。\n')


if __name__=='__main__':main()
