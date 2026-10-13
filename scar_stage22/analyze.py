"""Post-freeze, offline-only statistics and official score aggregation."""
import argparse
from collections import Counter
import csv
import gzip
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
from .config import ROOT, RESULTS, REPORTS, ENGINE, METHODS, GAMES


def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with gzip.open(path, 'rt') as stream: return [json.loads(s) for s in stream]
def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def gzwrite(path, data):
    with gzip.open(path,'wt',encoding='utf-8') as stream:
        for row in data: stream.write(json.dumps(row,ensure_ascii=False)+'\n')
def table(headers, records):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(x).replace('|','\\|').replace('\n',' ') for x in row)+' |' for row in records])
def feedback(obs):
    text = obs['text']
    m = re.search(r'Current Location:[^\n]*\n(.*?)(?:\nI am holding |\nMy level is |\Z)',text,re.S)
    return (m[1] if m else text).strip()
def public_goal(text):
    return re.findall(r'(?:Required action:|Your (?:task|goal) is|Objective:|Current tasks:)\s*([^\n]+)',text,re.I)


def official_scores():
    out = RESULTS/'official_scores'; out.mkdir(exist_ok=True)
    scores = {}
    for method in METHODS:
        args = [sys.executable,str(ENGINE/'challenge_eval.py')]
        for game in GAMES: args += ['--'+game,str(RESULTS/'runs'/f'{game}__{method}')]
        plain = subprocess.run(args,capture_output=True,text=True,check=True)
        machine = subprocess.run(args+['--json'],capture_output=True,text=True,check=True)
        (out/f'{method}.txt').write_text(plain.stdout)
        (out/f'{method}.json').write_text(machine.stdout)
        (out/f'{method}.stderr.txt').write_text(plain.stderr+machine.stderr)
        write(out/f'{method}.command.json',dict(command=args,source_commit='248430692a9d4a61d38c6c03ab2126287faaf450',unmodified=True))
        scores[method] = json.loads(machine.stdout)
    return scores


def run_statistics(game, method):
    from scar_stage16.knowledge import PublicTable
    folder = RESULTS/'runs'/f'{game}__{method}'
    summary = read(folder/'summary.json'); trajectory = rows(folder/'trajectory.jsonl.gz'); requests=rows(folder/'requests.jsonl.gz')
    public_knowledge=PublicTable();public_knowledge.observe(read(folder/'initial_public.json')['observation'])
    inspect = Counter(); events=[]; counters=Counter(); roles=Counter(); phase_cost=Counter(); seen_feedback={}; waits=0; longest_wait=0
    quest_events=[]; recipes=set(); prompt_lengths=[]; overrides=[]; rejection_events=[]; goal_changes=[]
    last_goal=None
    for r in trajectory:
        step = r['step']; action=r['action']; fb=feedback(r['feedback']); ident=f'{game}__{method}:a{step:03d}'
        kind=[]
        if r['reward'].get('quest',0):
            quest_events.append(dict(step=step,action=action,increment=r['reward']['quest'],cumulative=r['scores']['quest'],feedback=fb)); kind.append('quest_reward')
        current_goal=public_goal(r['feedback']['text'])
        if current_goal and current_goal!=last_goal:
            goal_changes.append(dict(step=step,public_goal=current_goal));last_goal=current_goal
        if action.startswith('inspect '):
            target=action[8:]; counters['inspect_actions']+=1
            counters['repeat_inspections']+=inspect[target]>0
            counters['identical_feedback_repeat_inspections']+=seen_feedback.get(target)==fb
            seen_feedback[target]=fb;inspect[target]+=1
        if action.startswith('craft '):
            counters['craft_actions']+=1
            success='successfully crafted' in fb
            counters['successful_craft_actions']+=success
            if not success: kind.append('craft_without_success_feedback')
            counters['material_rejections']+=bool(re.search(r'Cannot craft a single|not enough|insufficient|sufficient materials|missing.*material',fb,re.I))
        semantic=bool(re.search(r'Cannot |Invalid |not enough|do not have|can\x27t ',fb,re.I))
        counters['semantic_rejection_feedback']+=semantic
        if semantic: rejection_events.append(dict(step=step,action=action,feedback=fb));kind.append('public_rejection')
        if r['invalid_action']:kind.append('official_invalid')
        waits=waits+1 if action=='wait' else 0;longest_wait=max(longest_wait,waits)
        counters['wait_actions']+=action=='wait'
        public_knowledge.observe(r['feedback'],action)
        new=set(public_knowledge.recipes)-recipes
        if new:kind.append('public_recipe_names');recipes.update(new)
        if r.get('decision'):
            d=r['decision'];a=d['stage18'];counters['controller_overrides']+=d['intercepted']
            if d['intercepted']:
                overrides.append(dict(evidence_id=ident,step=step,proposal=d['proposed_action'],actual=action,
                                      reason=a['reason'],final_assessment=a['final_assessment'],
                                      public_feedback=fb,reward=r['reward']))
                kind.append('controller_override')
        if step>max(0,len(trajectory)-10):kind.append('final_ten_steps')
        if kind:
            events.append(dict(evidence_id=ident,game=game,method=method,step=step,kinds=kind,
                          trajectory=f'results/stage22/runs/{game}__{method}/trajectory.jsonl.gz',
                          line=step,observation=r['observation'],action=action,feedback=r['feedback'],
                          reward=r['reward'],scores=r['scores']))
    anomalies=[]
    for q in requests:
        roles[q['phase']]+=1;phase_cost[q['phase']]+=q.get('cost_usd',0)
        if q.get('usage'):prompt_lengths.append(dict(step=q['step'],ordinal=q['ordinal'],phase=q['phase'],tokens=q['usage']['prompt_tokens']))
        issues=[]
        if q['status']!='ok':issues.append(q['status'])
        if q.get('parse_exception'):issues.append(q['parse_exception'])
        if q.get('raw_response'):
            choice=q['raw_response']['choices'][0]
            if choice['finish_reason']!='stop':issues.append('finish_reason:'+str(choice['finish_reason']))
            parsed=q.get('parsed_json')
            if q['phase']=='action' and (not isinstance(parsed,dict) or not all(k in parsed for k in ('action','reasoning')) or not isinstance(parsed.get('action'),str)):
                issues.append('official_action_parser_fallback')
        if issues:
            corresponding=trajectory[q['step']-1]
            anomalies.append(dict(game=game,method=method,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],issues=issues,
                raw_response=q.get('raw_response'),status=q['status'],actual_action=corresponding['action'],
                controller_proposal=(corresponding.get('decision') or {}).get('proposed_action'),
                next_action=trajectory[q['step']]['action'] if q['step']<len(trajectory) else None))
    n=len(trajectory); s=summary.get('scores',{})
    stat=dict(game=game,method=method,status=summary['status'],steps=n,done=summary.get('done',False),
              main_quest_complete=bool((trajectory[-1].get('main_quest_progress') or {}).get('complete',False)),
              main_quest=s.get('quest',0),side_quest=s.get('side_quest',0),exploration=s.get('exploration',0),
              craft=s.get('craft',0),defeat=s.get('unique_kill',0),
              supplementary_total=sum(s.get(k,0) for k in ('side_quest','exploration','craft','unique_kill')),
              requests=len(requests),input_tokens=summary['input_tokens'],output_tokens=summary['output_tokens'],
              cost_usd=summary['cost_usd'],peak_reference_cost_usd=sum(q.get('peak_rate_reference_cost_usd',0) for q in requests),
              charged_or_reserved_usd=summary['charged_or_reserved_usd'],invalid_actions=summary['invalid_actions'],
              elapsed_seconds=summary['elapsed_seconds'],decision_seconds=sum(r['decision_time'] for r in trajectory),
              calls_by_role=dict(roles),cost_by_role=dict(phase_cost),max_input_tokens=max([r['tokens'] for r in prompt_lengths],default=0),
              min_input_tokens=min([r['tokens'] for r in prompt_lengths],default=0),
              last_quest_gain_step=quest_events[-1]['step'] if quest_events else None,
              steps_since_quest_gain=n-(quest_events[-1]['step'] if quest_events else 0),
              quest_events=quest_events,goal_changes=goal_changes,public_recipe_names_discovered=sorted(recipes),
              longest_wait_run=longest_wait,anomaly_requests=len(anomalies),error=summary.get('error'),
              initial_state_hash=summary.get('initial_state_hash'),**counters)
    stat['official_agent_return_input_tokens']=sum(r['agent_return_input_tokens'] for r in trajectory)
    stat['official_agent_return_output_tokens']=sum(r['agent_return_output_tokens'] for r in trajectory)
    stat['cache_hit_tokens']=sum(q.get('usage',{}).get('prompt_cache_hit_tokens',q.get('usage',{}).get('prompt_tokens_details',{}).get('cached_tokens',0)) for q in requests)
    stat['cache_hit_fraction']=stat['cache_hit_tokens']/stat['input_tokens'] if stat['input_tokens'] else 0
    stat['model_response_names']=sorted({q['raw_response'].get('model','') for q in requests if q.get('raw_response')})
    return stat, events, anomalies, overrides, trajectory, prompt_lengths


def main():
    official=official_scores(); stats=[];evidence=[];anomalies=[];overrides=[];curves=[];prompt_curves=[];trajectories={}
    for game in GAMES:
        for method in METHODS:
            s,e,a,o,t,p=run_statistics(game,method)
            stats.append(s);evidence+=e;anomalies+=a;overrides+=o;trajectories[(game,method)]=t
            curves.append(dict(game=game,method=method,step=0,main_quest=0,supplementary=0))
            curves.extend(dict(game=game,method=method,step=r['step'],main_quest=r['scores'].get('quest',0),
                               supplementary=sum(r['scores'].get(k,0) for k in ('side_quest','exploration','craft','unique_kill'))) for r in t)
            prompt_curves.extend(dict(game=game,method=method,**r) for r in p)
    write(RESULTS/'per_run.json',stats);gzwrite(RESULTS/'evidence.jsonl.gz',evidence)
    write(RESULTS/'model_anomalies.json',anomalies);gzwrite(RESULTS/'controller_overrides.jsonl.gz',overrides)
    for name,rr in [('progress_curves.csv',curves),('prompt_curves.csv',prompt_curves)]:
        with (RESULTS/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');writer.writeheader();writer.writerows(rr)
    scalar_fields=['game','method','status','steps','done','main_quest','side_quest','exploration','craft','defeat','supplementary_total','requests','input_tokens','output_tokens','cost_usd','invalid_actions','elapsed_seconds','max_input_tokens']
    with (RESULTS/'main_results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=scalar_fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(stats)
    averages=[]
    for method in METHODS:
        rr=[s for s in stats if s['method']==method]
        averages.append(dict(method=method,main_quest_mean=statistics.mean(r['main_quest'] for r in rr),
                          supplementary_total_mean=statistics.mean(r['supplementary_total'] for r in rr),
                          total_steps=sum(r['steps'] for r in rr),requests=sum(r['requests'] for r in rr),
                          input_tokens=sum(r['input_tokens'] for r in rr),output_tokens=sum(r['output_tokens'] for r in rr),
                          cost_usd=sum(r['cost_usd'] for r in rr),native_done=sum(r['done'] for r in rr)))
    write(RESULTS/'method_aggregates.json',averages)
    for aggregate in averages:
        actual=official[aggregate['method']]['aggregate']
        for key in ('main_quest_mean','supplementary_total_mean'):
            assert abs(aggregate[key]-actual[key])<1e-10, (aggregate['method'],key)
    plot(curves,prompt_curves)
    write_reports(stats,averages,trajectories,anomalies)
    write(RESULTS/'analysis_receipt.json',dict(passed=True,runs=len(stats),actions=sum(s['steps'] for s in stats),requests=sum(s['requests'] for s in stats),api_calls=0,source='all 15 first runs; no exclusions',analysis_files=[str(Path(__file__).relative_to(ROOT))]))


def plot(curves,prompts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir=REPORTS/'figures';figdir.mkdir(exist_ok=True)
    colors=['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00']
    styles=['-','--','-.',':',(0,(5,2,1,2))]
    fig,axes=plt.subplots(1,3,figsize=(13,3.5),sharex=True,layout='constrained')
    for ax,game in zip(axes,GAMES):
        for method,color,style in zip(METHODS,colors,styles):
            rr=[r for r in curves if r['game']==game and r['method']==method]
            ax.step([r['step'] for r in rr],[r['main_quest'] for r in rr],where='post',label=method,color=color,linestyle=style,linewidth=1.5)
        ax.set(title=game,xlabel='Environment actions',xlim=(0,300));ax.grid(alpha=.2)
    axes[0].set_ylabel('Raw Main Quest Reward');axes[-1].legend(fontsize=7,loc='upper left')
    fig.suptitle('300-step research pilot / DeepSeek Flash / one run per combination',fontsize=10)
    for ext in ('png','pdf'):fig.savefig(figdir/f'main_quest_progress.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,3.5),sharex=True,layout='constrained')
    for ax,game in zip(axes,GAMES):
        for method,color in zip(METHODS,colors):
            rr=[r for r in prompts if r['game']==game and r['method']==method and r['phase']=='action']
            ax.plot([r['step'] for r in rr],[r['tokens'] for r in rr],label=method,color=color,linewidth=1)
        ax.set(title=game,xlabel='Environment action index',xlim=(0,300));ax.grid(alpha=.2)
    axes[0].set_ylabel('Actual action-request input tokens');axes[-1].legend(fontsize=7)
    for ext in ('png','pdf'):fig.savefig(figdir/f'context_growth.{ext}',dpi=180)
    plt.close(fig)


def write_reports(stats,averages,trajectories,anomalies):
    lines=['# 三游戏五算法完整结果','', '**300 步 / DeepSeek Flash / 非 TTCL 正式排名。每组合一次，全部保留。**','',
      '**配对限制：官方初始化没有固定进程哈希种子，metropolis 的主线地点参数也存在差异；分差不是严格同状态的算法因果效应。详见运行事件审计。**','',
      table(['游戏','方法','主线','支线','探索','制作','战斗(唯一)','辅助总和','动作','终止'],
            [[s[k] for k in ('game','method','main_quest','side_quest','exploration','craft','defeat','supplementary_total','steps','status')] for s in stats]),'',
      '## 官方三游戏无权平均','',table(['方法','主线均值','辅助总和均值','环境done局数'],[[s['method'],f"{s['main_quest_mean']:.6f}",f"{s['supplementary_total_mean']:.6f}",f"{s['native_done']}/3"] for s in averages]),'',
      '各方法的未修改官方脚本输出在 `results/stage22/official_scores/`；主要排序只看原始主线均值，并列才看辅助总和均值。不按动作成本或归一化奖励重新排名。','',
      '## 成本、效率及异常','',table(['游戏','方法','API请求','输入token','输出token','usage计价美元','官方无效动作','反馈拒绝次数','重复检查','最长连续wait','最长输入token'],
      [[s['game'],s['method'],s['requests'],s['input_tokens'],s['output_tokens'],f"{s['cost_usd']:.6f}",s['invalid_actions'],s.get('semantic_rejection_feedback',0),s.get('repeat_inspections',0),s['longest_wait_run'],s['max_input_tokens']] for s in stats]),'',
      '官方无效动作严格取环境 info 标志；反馈拒绝是文本筛查，二者不可互换。重复检查指再次检查相同对象，可能具有重新确认库存的合理用途，不能全部算浪费。费用按请求返回的缓存命中、输入输出 usage 与核验价目计算，不冒充账户发票。','',
      f'保留 {len(anomalies)} 条异常请求索引，详见 `model_anomalies.json`。没有为了格式或结果重新抽样；官方 parser 的 fallback 行为保留。Voyager 所有额外角色调用计入请求数和成本。','',
      table(['游戏','方法','总时长秒','决策累计秒','输入缓存命中率','动作/其他角色调用'],
        [[s['game'],s['method'],f"{s['elapsed_seconds']:.1f}",f"{s['decision_seconds']:.1f}",f"{s['cache_hit_fraction']:.2%}",json.dumps(s['calls_by_role'])] for s in stats]),'',
      '总时长包含加载、CPU 检索、暂停恢复及并发竞争；决策累计时长包含模型和检索。它们不是隔离硬件下的速度基准。输入缓存命中率使用真实 API usage。','',
      '## 进度与上下文','', '![主线奖励曲线](figures/main_quest_progress.png)','', '![请求上下文长度](figures/context_growth.png)','',
      'PDF 与可重算 CSV 同时保存。重叠曲线可能遮盖彼此，逐步精确数值以 CSV 为准。所有请求上限相同，LongContext 没有专属截断、摘要或提高额度。']
    (REPORTS/'三游戏五算法主结果表.md').write_text('\n'.join(lines)+'\n')
    for game in GAMES:
        interpretation={
            'remnant':'五方法均只有 1 个主线奖励，说明本游戏对本批所有方法都形成瓶颈。Stage18 的旧目标和 wait 问题见控制器诊断。对照的末期证据也不能忽略：NoMemory a300 使用带数量的 pick up，原生报格式错误；STM a300 战斗死亡并丢失物品；LongContext a300 进入黑暗的 armory；Voyager a300 检查空纸且处于黑暗。a271–300 内 Voyager 13 次 talk to chronicler_lyra，LongContext 13 次 defend，说明它们同样没有继续兑现主线。不能仅由黑暗或死亡断言某一记忆模块是根因。',
            'mark':'Stage18 与 NoMemory 主线均为 0，STM/LongContext 为 10，Voyager 为 3；这些都是阶段奖励，均未完成整个主线。Stage18 的教程数量覆盖与目标滞留具有逐步证据。STM/LongContext 的最后主线奖励在 a186/a165，随后也没有终局完成；a271–300 中 LongContext 反复 take out/store fiber_bundle，Voyager 11 次 equip copper_sword、8 次 talk to librarian_rowan，a300 仍收到人物自我介绍。不能把它们的高于 SCAR 得分夸大为游戏成功或普遍避免重复。',
            'metropolis':'五局主线地点参数不完全配对，以下只作描述性比较。Stage18 在 a31 到达 7 分后停止新增奖励；LongContext 在 a167 到达 8 分后也停滞。NoMemory a300 制作 iron_bar 被原生拒绝，明确缺少当前位置的 statute_forge；STM a300 仍在处理背包物品；Voyager a300 的主线提示仍要求把 evidence dossier 送到 evidence_room，说明其 4 分不代表完成第一章全部交付。阶段分数、配方发现、实际取物和目标提交必须分开。SCAR a91 公开门锁变化未更新的局部问题另见控制器诊断。'}[game]
        lines=[f'# {game}：逐方法失败与进度证据','', '只分析该组合唯一一次真实轨迹。以下动作编号从 1 起；模型与环境随机分叉不是模块因果实验。','',interpretation,'',
               'SCAR 的同状态证据及明确的归因边界见 [控制器贡献与失败诊断](控制器贡献与失败诊断.md)。','']
        for method in METHODS:
            s=next(s for s in stats if s['game']==game and s['method']==method);t=trajectories[(game,method)]
            lines += [f'## {method}','',f"主线 {s['main_quest']}；辅助 {s['supplementary_total']}；动作 {s['steps']}；终止 `{s['status']}`；最后主线奖励在动作 {s['last_quest_gain_step']}；其后 {s['steps_since_quest_gain']} 步未新增主线奖励。",'',
                      f"制作动作 {s.get('craft_actions',0)}，带成功制作反馈 {s.get('successful_craft_actions',0)}，材料拒绝 {s.get('material_rejections',0)}；公开配方名称发现 {len(s['public_recipe_names_discovered'])} 类；控制器覆盖 {s.get('controller_overrides',0)} 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。",'']
            if s['error']:lines += ['基础设施异常：`'+json.dumps(s['error'],ensure_ascii=False)+'`','']
            if s['quest_events']:
                lines += ['主线奖励动作：','',table(['动作','执行','本步奖励','累计'],[[r['step'],r['action'],r['increment'],r['cumulative']] for r in s['quest_events']]),'']
            lines += ['最后十步：','',table(['动作','执行','累计主线','官方无效'],[[r['step'],r['action'],r['scores'].get('quest',0),r['invalid_action']] for r in t[-10:]]),'']
            if t:
                lines += ['最后一步原始公开反馈（完整观测在轨迹中）：','', '```text',feedback(t[-1]['feedback']),'```','']
            lines += [f'完整轨迹：`results/stage22/runs/{game}__{method}/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。','']
        text='\n'.join(lines)
        (REPORTS/f'{game}_逐游戏案例.md').write_text('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n')


if __name__=='__main__':main()
