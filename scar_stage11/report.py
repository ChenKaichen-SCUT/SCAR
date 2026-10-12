"""Generate complete case evidence and comparison tables from published runs."""
import gzip
import json
from pathlib import Path

from scar_stage10.report import cell, table
from scar_stage11.controller import METHODS

OUT = Path('results/stage11')
REPORT = Path('reports/stage11')


def load(name):
    return json.loads((OUT/(name+'.json')).read_text())


def quote(value):
    return '\n'.join(('> '+line).rstrip() for line in str(value).splitlines())


def main():
    (REPORT/'cases').mkdir(parents=True, exist_ok=True)
    methods = load('method_metrics'); cases = load('cases'); metrics = load('episode_metrics')
    by = {(m['case_id'],m['algorithm']):m for m in metrics}
    eps = {e['task_id']:e for method in METHODS for e in map(json.loads,gzip.open(OUT/f'trajectories_{method}.jsonl.gz','rt'))}
    effects = {(e['task_id'],e['index']):e for e in map(json.loads,gzip.open(OUT/'decision_effects.jsonl.gz','rt'))}
    columns = [('成功数','successes'),('R@10','recovery_at_10'),('R@20','recovery_at_20'),('R@40','recovery_at_40'),
        ('实际动作','steps'),('成功局平均动作','mean_success_steps'),('模型请求（含重试）','api_calls'),('输入token','input_tokens'),
        ('输出token','output_tokens'),('固定计价USD','cost_usd'),('原生拒绝','semantic_rejections'),('实际wait','actual_wait_actions'),
        ('最长wait串','maximum_wait_streak'),('同条件无进展重复','same_context_no_gain_repeats'),('重复inspect','repeated_inspection_count'),
        ('关键配方名称发现/43','key_recipe_discovered'),('发现后实际制作数','discovered_then_crafted'),('发现后制作率','discovery_to_craft_rate'),
        ('全部关键名称已知仍失败','all_known_but_failed'),('探索动作','exploration_actions'),
        ('探索：无公开确认目标连接','exploration_without_public_goal_connection'),('探索：真值非依赖对象','exploration_native_nonrelevant_subject'),
        ('公开相关/可能桥接探索动作','public_related_exploration_actions'),('这些探索新增公开规则数','public_related_exploration_new_rules'),
        ('这些探索新增关键规则数','public_related_exploration_new_key_rules'),('首次真实中间物类型','new_intermediate_types'),
        ('尚未检查过的新产物类型','new_uninspected_intermediate_types'),('新产物3动作内检查数','new_intermediate_inspected_within3'),
        ('检查窗口可评价数','new_intermediate_inspection_evaluable'),('检查窗口右删失数','new_intermediate_inspection_censored'),
        ('3动作内检查比例','fresh_product_inspection_within3_rate'),('已知必要且原生可行状态','necessary_feasible_states'),
        ('当步执行数','necessary_executed_now'),('及时执行率','timely_execution_rate'),('3动作内执行数','necessary_executed_within3'),
        ('执行窗口可评价数','necessary_within3_evaluable'),('执行窗口右删失数','necessary_within3_censored'),('3动作内执行率','timely_within3_rate'),
        ('已转化配方的平均发现→制作延迟','mean_discovery_execution_lag'),('模型局部原生进展提案','base_native_useful_proposals'),
        ('局部进展提案原样保留','base_useful_proposals_preserved'),('局部进展提案动作被改写','base_useful_proposals_overridden'),
        ('有害覆盖基础目标达成','harmful_goal_overrides'),('有害覆盖基础目标数量进展','harmful_target_quantity_overrides'),
        ('环境资源损失步数','resource_destruction_steps'),('公开死亡次数','public_deaths'),('方法中止','method_abort'),('格式中止','format_abort')]
    stats = ['# Stage11 可重算统计表', '由 `python -m scar_stage11.report` 从完整轨迹及独立原生评价生成。',
        table(['指标']+METHODS, [[label]+[round(methods[m][key],9) if isinstance(methods[m][key],float) else methods[m][key] for m in METHODS] for label,key in columns]),
        '“无公开确认目标连接”包括诚实标为可能桥接的未知探索，不等于无用；真值非依赖对象也可能披露相关配方。必要可行是局部状态机会，不能当作全局最优行动。模型局部原生进展包括关键物制作，但未保证当前还需要更多副本；动作被改写也包括仅改变制作批量，不等于有害覆盖。仅已实际转化配方的平均延迟必须与未转化数量一起解读。',
        '## 所有预先声明的配对比较',
        table(['比较','R40差','family bootstrap 95%区间','新增成功','丢失成功'],[[p['new']+'−'+p['old'],p['difference'],p['ci95'],[x['target'] for x in p['gained']],[x['target'] for x in p['lost']]] for p in load('paired_comparisons')]),
        '10个长期开发family、一个物理种子。模型采样不严格配对；零宽区间不证明等效，不能据此声称独立泛化。',
        '## 同状态关闭显式优先级',
        table(['开→关','比较动作','动作变化','关闭后合法性改善','关闭后合法性变差','关闭后新增当步成功','关闭后丢失当步成功','开启时新关键规则更多','开启时更少'],
            [[name,v.get('decisions',0),v.get('changed',0),v.get('removing_module_legal_gain',0),v.get('removing_module_legal_loss',0),
              v.get('removing_module_goal_gain',0),v.get('removing_module_goal_loss',0),v.get('module_on_more_new_key_rules',0),v.get('module_on_fewer_new_key_rules',0)] for name,v in load('counterfactual_summary').items()]),
        '每个变化的原生单步分支重放两次。只关闭当前决策机制，保留此前已形成的公开历史与队列；不是整局重跑的因果效果。E1不额外调用模型制造反事实。']
    (REPORT/'可重算统计表.md').write_text('\n\n'.join(stats)+'\n')
    detail = ['# Stage11 逐例机制归因', '所有index从0计，index39是第40个动作。逐步公开观察、模型提案、实际动作、反馈、新配方和目标结果均保留于各family证据页；分析结论见[实验报告](实验报告.md)。']
    chains = ['# Stage11 50局完整行动链', '压缩展示全部动作；完整公开上下文和反馈见[逐例机制归因](逐例机制归因.md)链接的证据页。']
    for case in cases:
        cid=case['id']; name=case['goal']['name']; page=['# '+name+'：五配置公开证据', 'case：`'+cid+'`。不按成绩删选步骤；物理评价不会作为Agent输入。']
        detail += ['## '+name, '[完整公开证据](cases/'+name+'.md)',
            table(['配置','结果/动作','配方发现','缺失配方','已知必要当步执行','新产物3步检查','模型局部进展提案/原样保留','wait'],
                [[m,('成功/' if by[cid,m]['recovery_at_40'] else '失败/')+str(by[cid,m]['steps']),
                  str(by[cid,m]['key_recipe_discovered'])+'/'+str(by[cid,m]['key_recipe_total']),by[cid,m]['missing_key_recipes'],
                  str(by[cid,m]['necessary_executed_now'])+'/'+str(by[cid,m]['necessary_feasible_states']),
                  str(by[cid,m]['new_intermediate_inspected_within3'])+'/'+str(by[cid,m]['new_intermediate_inspection_evaluable']),
                  str(by[cid,m]['base_native_useful_proposals'])+'/'+str(by[cid,m]['base_useful_proposals_preserved']),by[cid,m]['actual_wait_actions']] for m in METHODS])]
        for method in METHODS:
            metric=by[cid,method]; ep=eps[metric['task_id']]; rows=ep['rows']
            detail += ['### '+method, '末态可访问材料（仅评价器）：`'+json.dumps(rows[-1]['physical_after']['accessible'],ensure_ascii=False)+'`。',
                table(['配方','发现index','首次制作index','延迟','未转化'],[[r['recipe'],r['discovery_index'],r['first_craft_index'],r['lag'],r['unconverted']] for r in metric['discovery_execution_delays']]),
                table(['新产物','制作index','首次检查index','3步内','以前已检查','披露关键配方'],[[r['product'],r['production_index'],r['first_inspection_index'],r['inspected_within3'],r['previously_inspected'],r['new_key_recipes_at_inspection']] for r in metric['new_product_inspections']])]
            if not metric['recovery_at_40']:
                detail += ['剩余失败标签：`'+json.dumps(metric['residual_categories'],ensure_ascii=False)+'`。全关键名称已知后动作数：'+str(metric['all_known_after_action'])+'；环境资源损失步数：'+str(metric['resource_destruction_steps'])+'；公开死亡：'+str(metric['public_deaths'])+'。标签为可重叠证据，不能作为已证明的唯一因果解释。']
            useful_overrides=[r for r in rows if not effects[ep['task_id'],r['index']]['base_same_as_selected'] and
                not effects[ep['task_id'],r['index']]['base_effect']['rejected'] and
                (effects[ep['task_id'],r['index']]['base_effect']['new_key_recipes'] or effects[ep['task_id'],r['index']]['base_effect']['successful_key_production'] or effects[ep['task_id'],r['index']]['base_effect']['goal'])]
            detail += ['基础模型已提出但被覆盖的知识/制作/目标进展候选（全部）：',
                table(['index','模型提案','实际动作','实际新关键规则','原提案的局部效果'],[[r['index'],r['proposed_action'],r['executed_action'],effects[ep['task_id'],r['index']]['new_key_recipes'],effects[ep['task_id'],r['index']]['base_effect']] for r in useful_overrides])]
            chains += ['## '+name+' / '+method,
                table(['index','模型提案','实际动作','拒绝','原因','新关键配方','目标达成'],[[r['index'],r['proposed_action'],r['executed_action'],r['semantic_rejection'],r['structured'].get('reason'),effects[ep['task_id'],r['index']]['new_key_recipes'],r['diagnostic_goal_reached']] for r in rows])]
            page += ['## '+method, 'task：`'+ep['task_id']+'`；'+('成功' if metric['recovery_at_40'] else '失败')+'；实际'+str(metric['steps'])+'动作。']
            for r in rows:
                effect=effects[ep['task_id'],r['index']]
                page += ['<details><summary>index '+str(r['index'])+'：'+cell(r['proposed_action'])+' → '+cell(r['executed_action'])+'</summary>',
                    '公开观察：',quote(r['observation']['text']),
                    '模型提案：`'+r['proposed_action']+'`；实际动作：`'+r['executed_action']+'`；原因：`'+str(r['structured'].get('reason'))+'`。',
                    '公开反馈及新观察：',quote(r['next_observation']['text']),
                    '新增公开配方：`'+str(effect['public_new_recipe_names'])+'`；其中关键配方：`'+str(effect['new_key_recipes'])+'`。',
                    '公开确认必要节点：`'+str(effect['public_confirmed_nodes'])+'`；原生可行必要机会：`'+str([n['name'] for n in effect['necessary_native_opportunities']])+'`。',
                    '原生拒绝：'+str(r['semantic_rejection'])+'；实际目标达成：'+str(r['diagnostic_goal_reached'])+'。',
                    '基础提案独立原生效果：`'+json.dumps(effect['base_effect'],ensure_ascii=False)+'`。',
                    '显式选择记录：`'+json.dumps(effect['selected_metadata'],ensure_ascii=False)+'`。','</details>']
        (REPORT/'cases'/(name+'.md')).write_text('\n\n'.join(page)+'\n')
    detail += ['## 全部成败变化', table(['比较','新增','退化'],[[p['new']+'−'+p['old'],[r['target'] for r in p['gained']],[r['target'] for r in p['lost']]] for p in load('paired_comparisons')]),
               '局部进步、基础模型已会提出的动作、没有转化为最终成功的知识，以及所有退化都应结合上述证据判断；相同完成率不能被描述成显式机制已胜出。']
    (REPORT/'逐例机制归因.md').write_text('\n\n'.join(detail)+'\n')
    (REPORT/'行动链.md').write_text('\n\n'.join(chains)+'\n')
    print(json.dumps({'reports_generated':13,'episodes':len(eps),'actions':sum(len(e['rows']) for e in eps.values()),'api_calls':0}))


if __name__=='__main__':
    main()
