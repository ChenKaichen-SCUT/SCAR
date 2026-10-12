"""Render all frozen family decisions and recovery records without cherry-picking."""
import gzip
import json
from pathlib import Path
from scar_stage9.controller import METHODS

OUT = Path('results/stage9')
REPORTS = Path('reports/stage9')


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(cell(x) for x in row)+' |' for row in rows])+'\n'


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    families = json.loads((OUT/'family_comparison.json').read_text())
    knowledge = {(k['method'], k['case_id']): k for k in json.loads((OUT/'knowledge_diagnostics.json').read_text())}
    episodes = {(m, e['case_id']): e for m in METHODS for e in map(json.loads, gzip.open(OUT/f'trajectories_{m}.jsonl.gz', 'rt'))}
    lines = ['# Stage 9 主动恢复机制分析', '',
        '全部16个 family 均为反复参与开发的 Robot Kingdom 任务。下列索引均从0开始。完整基模型提案、公开观察、执行前控制器、原始反馈、物理状态与用量见 results/stage9/trajectories_F*.jsonl.gz；没有删去失败或退化。', '',
        '四个层次分开：合法动作、真实阻碍解除、原受阻动作成功重试、最终任务完成。GPAR 的103个事件中，31个成功重试原动作，68个因无公开路径或深度限制取消，1个因重复求解取消，3个在40步结束时仍未完成。没有把合法移动或普通 inspect 自动计为物理进展。', '',
        '三个真实失败后成功返回、继而完成任务的事件链出现在 padded_tunic（两条）和 fiend_rivet（一条）；F1也能完成这两个 family。因此事件链证明机制确实执行过，不证明它对成功必要。', '',
        '主要负面结果：bandage_roll 的两次单份 sinew_cord 制作耗尽后续仍需的 cloth；fiend_alloy_scale 首次仅收取一份 ingot，留在原地的一份在第14个完整环境动作后消失；war_strap 中材料失败在位置/容器状态变化后反复重试；fiend_helm 的F2最长连续等待8步。详见实验报告和四个保留对照分支的 negative_counterfactuals.json。', '',
        'F1/F2各自决策前状态上只切换 active_recovery 的1206次比较，有47次改变动作。它是保留已发生历史的单步局部反事实；F2历史中积累的恢复记录不会凭空变成另一条完整F1轨迹。', '']
    for family in families:
        cid = family['case_id']
        lines += ['## '+family['target']+' — '+cid, '', '数据层：'+family['cohort']+'。', '',
            table(['配置', '成功', '动作', '拒绝', '等待', '关键配方', '费用USD'], [
                [m, '是' if r['recovery_at_40'] else '否', r['steps'], r['semantic_rejections'], r['actual_wait_actions'],
                 str(knowledge[m,cid]['key_recipe_discovered'])+'/'+str(knowledge[m,cid]['key_recipe_total']), f"{r['cost_usd']:.6f}"]
                for m, r in family['methods'].items()])]
        for method in ['F1', 'F2']:
            metric = family['methods'][method]; ep = episodes[method, cid]; k = knowledge[method, cid]
            lines += ['### '+method, '',
                '未获得的关键配方名称：'+(', '.join(k['missing_key_recipes']) or '无')+'。'+
                f"原目标字段丢失 {metric['goal_lost_steps']} 次；最长等待 {metric['max_wait_streak']} 步。", '',
                table(['索引', '基模型提案', '执行动作', '拒绝', '恢复事件', '引擎反馈首行'], [
                    [r['index'], r['proposed_action'], r['executed_action'], r['semantic_rejection'],
                     (r['structured'].get('stage9', {}).get('recovery_selection') or {}).get('event_id', '—'),
                     r['action_rule_feedback'].split('\n')[0]] for r in ep['rows']])]
            if method == 'F2':
                lines += [table(['事件', '来源', '受阻动作', '结束状态', '恢复动作数', '原动作成功索引', '后续任务成功'], [
                    [p['event_id'], p['origin'], p['blocked_action'], p['status'], len(p['attempts']),
                     p['root_resumed_index'], p['task_success_after_resume']] for p in metric['recovery_chains']])]
                for p in metric['recovery_chains']:
                    if not p['attempts']: continue
                    lines += [f"事件 {p['event_id']} 的逐步物理审计：", '',
                        table(['索引', '恢复动作', '合法', '条件解除', '材料/产物进展', '仅位置准备', '原动作返回'], [
                            [a['index'], a['selected_action'], a['selected_legal'], a['relevant_condition_release'],
                             a['physical_progress'], a['location_preparation'], a['root_resumed']] for a in p['attempts']])]
    lines += ['## 固定续动作的补充诊断', '',
        '以下由评测器提供相同后续动作，均在原40步余额内、每个分支独立重放两次。它们不是自主恢复成绩，也没有用于修改冻结策略。', '']
    for r in json.loads((OUT/'negative_counterfactuals.json').read_text())['records']:
        lines += [f"- {r['method']} / {r['case_id']} / index={r['index']}：`{r['original_action']}` → `{r['alternative_action']}`；原分支完成={r['original']['goal']}，替换分支完成={r['alternative']['goal']}。"]
    (REPORTS/'主动恢复机制分析.md').write_text('\n'.join(lines).rstrip()+'\n')
    groups = json.loads((OUT/'method_metrics.json').read_text())
    lines = ['# Stage 9 可重算统计表', '']
    for scope, methods in groups.items():
        lines += ['## '+scope, '', table(['配置', 'N', '成功', 'R@10', 'R@20', 'R@40', '动作数', '费用USD', 'token/成功', '等待'], [
            [m, r['n'], r['successes'], r['recovery_at_10'], r['recovery_at_20'], r['recovery_at_40'], r['steps'],
             f"{r['cost_usd']:.9f}", r['tokens_per_success_all_attempts'], r['actual_wait_actions']] for m,r in methods.items()])]
    (REPORTS/'可重算统计表.md').write_text('\n'.join(lines).rstrip()+'\n')
    print('Wrote all16 family paths, positive/negative recovery records, and statistics tables')


if __name__ == '__main__': main()
