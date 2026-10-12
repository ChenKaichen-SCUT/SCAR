"""Render tables and all 40 action chains from published evidence; zero API."""
import collections
import gzip
import json
from pathlib import Path

OUT = Path('results/stage10')
REPORT = Path('reports/stage10')
METHODS = ['S0', 'S1', 'S2', 'S3']
LABELS = {'knowledge_discovery': '知识发现不足',
          'known_knowledge_not_converted_to_plan': '知识已发现但没有转化为计划',
          'material_or_action_execution': '材料或动作执行问题'}


def load(name):
    return json.loads((OUT/(name+'.json')).read_text())


def cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(map(cell, headers))+' |',
                      '| '+' | '.join('---' for _ in headers)+' |']+
                     ['| '+' | '.join(map(cell, row))+' |' for row in rows])


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    methods = load('method_metrics'); cases = load('cases'); metrics = load('episode_metrics')
    by = {(m['case_id'], m['algorithm']): m for m in metrics}
    eps = {e['task_id']: e for method in METHODS
           for e in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt'))}
    effects = {(e['task_id'], e['index']): e for e in map(json.loads, gzip.open(OUT/'decision_effects.jsonl.gz', 'rt'))}
    risks = {r['task_id']: r for r in load('public_risk_audit')['records']}
    columns = [('成功数', 'successes'), ('实际动作', 'steps'), ('R@10', 'recovery_at_10'),
               ('R@20', 'recovery_at_20'), ('R@40', 'recovery_at_40'), ('成功局平均动作', 'mean_success_steps'),
               ('输入token', 'input_tokens'), ('输出token', 'output_tokens'), ('请求数（含格式重试）', 'api_calls'),
               ('费用USD', 'cost_usd'), ('全局成本/成功局', 'cost_per_success_all_attempts'),
               ('原生拒绝', 'semantic_rejections'), ('实际wait', 'actual_wait_actions'),
               ('连续wait对数', 'consecutive_wait_pairs'), ('最长wait串', 'maximum_wait_streak'),
               ('同公开条件无进展重复', 'same_context_no_gain_repeats'), ('同条件失败重复', 'same_context_failed_repeats'),
               ('重复inspect', 'repeated_inspection_count'), ('关键配方发现数/43', 'key_recipe_discovered'),
               ('发现后制作数', 'discovered_then_crafted'), ('发现后制作比例', 'discovery_to_craft_rate'),
               ('全关键名称已知仍失败', 'all_known_but_failed'), ('局部可制作但未执行动作数', 'known_ready_missed'),
               ('环境资源损失步数', 'resource_destruction_steps'), ('资源循环', 'resource_cycles'),
               ('有害覆盖基础目标动作', 'harmful_goal_overrides'), ('有害覆盖基础目标数量', 'harmful_target_quantity_overrides'),
               ('三值否决（S0无该日志）', 'condition_vetoes'), ('UNKNOWN单独被否决', 'unknown_only_vetoes'),
               ('引擎合法动作被否决', 'legal_action_vetoes'), ('手满拒绝', 'hand_capacity_rejections'),
               ('新增收集选择', 'collection_selections'), ('收集后真实资源增益', 'collection_with_native_gain'),
               ('收集被拒绝', 'collection_rejections'), ('暂存/返回/取回动作', 'storage_actions'),
               ('方法中止', 'method_abort'), ('格式中止', 'format_abort')]
    numbers = ['# Stage 10 可重算统计表', '由 `python -m scar_stage10.report` 从发布数据生成；所有费用采用冻结计价口径。',
               table(['指标']+METHODS, [[label]+[round(methods[m][key], 9) if isinstance(methods[m][key], float) else methods[m][key]
                                                    for m in METHODS] for label, key in columns]),
               '同条件重复统一使用 ResourceController 的公开上下文，S0 为18而非使用旧重试键所得的68；该修正仅在评价器中，策略冻结不变。',
               '配方“已知”指公开原料名称，不代表完整数量或所有执行条件已知。局部可制作表示原生 craft 1 可执行，不能直接等同全局最优动作。',
               '## 原生容量与公开健康风险',
               table(['配置', '背包满状态', '双手满状态', '最大背包负载/容量', '外部容器可见状态', '死亡次数', '诅咒告警步数'],
                     [[m, load('capacity_coverage')[m]['full_inventory_states'], load('capacity_coverage')[m]['full_hands_states'],
                       str(load('capacity_coverage')[m]['maximum_inventory_load'])+'/20',
                       load('capacity_coverage')[m]['with_external_container_states'],
                       load('public_risk_audit')['summary'][m]['death_events'],
                       load('public_risk_audit')['summary'][m]['curse_warning_steps']] for m in METHODS]),
               'S2/S3 各2个外部容器状态来自死亡后掉落的自有背包，不能视为正常可用的安全暂存设施。死亡事件只依据公开反馈计数，不把相关性解释成收集模块的独立因果效果。',
               '## 配对 family 结果',
               table(['目标']+METHODS, [[c['goal']['name']]+[('成功/'+str(by[c['id'],m]['steps'])) if by[c['id'],m]['recovery_at_40'] else '失败/40' for m in METHODS] for c in cases]),
               '## 预先声明的配对比较',
               table(['比较', '成功率差', 'family bootstrap 95%区间', '新增', '丢失'],
                     [[p['new']+'−'+p['old'], p['difference'], p['ci95'], [x['target'] for x in p['gained']], [x['target'] for x in p['lost']]] for p in load('paired_comparisons')]),
               '10个长期开发 family，每个仅一个物理种子；模型采样不配对。区间不支持独立泛化或统计优越性，[0,0]也不证明等效。']
    (REPORT/'可重算统计表.md').write_text('\n\n'.join(numbers)+'\n')
    detail = ['# Stage 10 逐例机制归因', '所有 index 均从0开始；例如 index39 为第40个动作。分类可重叠，是可观察证据，不是已识别的唯一根因。具体判断结合[实验报告](实验报告.md)；40局完整链见[行动链](行动链.md)。']
    chains = ['# Stage 10 全部40局行动链', '从0计 index；原始轨迹保存候选列表、三值条件、公开证据、完整观察、控制器状态、实际效果及原模型请求。下表只压缩展示决策链，没有删去失败动作。']
    for c in cases:
        detail += ['## '+c['goal']['name'], 'family：`'+c['family']+'`；case：`'+c['id']+'`。',
                   table(['配置', '结果/动作', '已知关键配方', '发现后制作', '缺失配方', 'wait', '损失步数', '残余类别'],
                         [[m, ('成功/' if by[c['id'],m]['recovery_at_40'] else '失败/')+str(by[c['id'],m]['steps']),
                           f"{by[c['id'],m]['key_recipe_discovered']}/{by[c['id'],m]['key_recipe_total']}",
                           f"{by[c['id'],m]['discovered_then_crafted']}/{by[c['id'],m]['discovered_recipe_count']}",
                           by[c['id'],m]['missing_key_recipes'], by[c['id'],m]['actual_wait_actions'],
                           by[c['id'],m]['resource_destruction_steps'], [LABELS[x] for x in by[c['id'],m]['residual_categories']]] for m in METHODS])]
        for method in METHODS:
            metric = by[c['id'],method]; ep = eps[metric['task_id']]; rows = ep['rows']
            detail += ['### '+method, 'task：`'+ep['task_id']+'`。',
                       '末态可访问材料（评测器，非策略输入）：`'+json.dumps(rows[-1]['physical_after']['accessible'], ensure_ascii=False)+'`。',
                       '配方发现与执行：', table(['配方', '发现后动作数', '首次制作后动作数', '发现后制作'],
                           [[r['recipe'], r['discovered_after_action'], r['first_successful_craft'], r['converted_after_discovery']] for r in metric['recipe_conversion_records']])]
            if not metric['recovery_at_40']:
                detail += ['原生拒绝：'+str(metric['semantic_rejections'])+'；全关键名称已知时刻（执行动作数）：'+str(metric['all_known_after_action'])+'；局部可制作未执行：'+str(metric['known_ready_missed'])+'。',
                           '环境实际资源损失：`'+json.dumps(metric['resource_destruction'], ensure_ascii=False)+'`。',
                           '前8条局部可制作但未执行证据（全集见 episode_metrics.json）：',
                           table(['index', '局部可制作', '实际动作', '原FIFO'], [[r['index'],r['nodes'],r['action'],r['queue']] for r in metric['missed_ready_records'][:8]])]
                for u in metric['plan_updates_after_knowledge']:
                    detail += [f"新知识 index{u['discovery_index']}：`{u['new_key_recipes']}`；随后至多4步队列与行为：",
                               table(['index','动作','FIFO','局部可制作','新增配方'], [[n['index'],n['action'],n['queue'],n['ready'],n['recipe_gain']] for n in u['next_decisions']])]
            for death in risks[ep['task_id']]['death_events']:
                detail += [f"公开死亡事件：index{death['index']}，动作 `{death['action']}`。原始反馈见 public_risk_audit.json；携带资源并不等于安全。"]
            chains += ['## '+c['goal']['name']+' / '+method, 'task：`'+ep['task_id']+'`。',
                       table(['index', '模型提案', '实际动作', '原生拒绝', '决策原因', '新关键配方', '已知可制作', '目标达成'],
                             [[r['index'], r['proposed_action'], r['executed_action'], r['semantic_rejection'],
                               r['structured'].get('reason', r.get('reason')), effects[ep['task_id'],r['index']]['new_key_recipes'],
                               effects[ep['task_id'],r['index']]['known_ready_nodes'], r['diagnostic_goal_reached']] for r in rows])]
    detail += ['## 事后两步知识桥接诊断', '评测器使用隐藏目录选择下述状态，策略没有这些知识。每分支重放两次、只消耗原剩余40步内的两个动作，均未完成整局目标；不能算作自主规划成绩。',
               table(['配置/目标', 'index', '实际两步', '诊断两步', '新增原本缺失的配方'],
                     [[r['method']+'/'+next(c['goal']['name'] for c in cases if c['id']==r['case_id']), r['index'],
                       r['branches']['actual_two_actions']['actions'], r['branches']['known_production_then_inspect']['actions'],
                       r['branches']['known_production_then_inspect']['terminal_missing_recipes_revealed']] for r in load('knowledge_counterfactuals')['records']])]
    (REPORT/'逐例机制归因.md').write_text('\n\n'.join(detail)+'\n')
    (REPORT/'行动链.md').write_text('\n\n'.join(chains)+'\n')
    print(json.dumps({'reports_generated': 3, 'episodes': len(eps), 'actions': sum(len(e['rows']) for e in eps.values()), 'api_calls': 0}))


if __name__ == '__main__':
    main()
