"""Evidence-backed interpretation of the completed negative experiment."""
import collections,gzip,json
from pathlib import Path
from scar.io import atomic_json
from scar_v3.state import parse_action
from scar_unknown17_stage7.report import table,num
OUT=Path('results/stage8');REPORT=Path('reports/stage8')

def augment():
    groups=json.loads((OUT/'method_metrics.json').read_text());new=groups['new'];reg=groups['regression']
    checks=json.loads((OUT/'negative_counterfactuals.json').read_text())['records'];cases={c['id']:c for c in json.loads((OUT/'cases.json').read_text())}
    metrics=json.loads((OUT/'episode_metrics.json').read_text());by={(r['case_id'],r['algorithm']):r for r in metrics}
    chains=[];knowledge=[]
    for method in ['P3','P4']:
        for ep in map(json.loads,gzip.open(OUT/f'trajectories_{method}.jsonl.gz','rt')):
            c=cases[ep['case_id']];graph={c['object_names'][k]:{c['object_names'][d] for d in r['ingredients']} for k,r in c['recipe_graph'].items()}
            last=None;length=best=0
            for row in ep['rows']:
                p=parse_action(row['executed_action'])
                if p.verb=='craft' and row['semantic_rejection']:last=None;length=0
                elif p.verb=='craft' and p.target in graph and 'successfully crafted' in row['action_rule_feedback']:
                    length=length+1 if last in graph[p.target] else 1;best=max(best,length);last=p.target
            chains.append({'case_id':c['id'],'method':method,'cohort':c['cohort'],'longest_linked_productive_chain':best,
                'scope':'consecutive productive necessary crafts whose next product consumes previous product; ignore transport/inspection, reset on rejected craft; descriptive evaluation using native graph'})
    for c in cases.values():
        if c['cohort']!='new':continue
        a,b=by[c['id'],'P4'],by[c['id'],'P3'];knowledge.append({'case_id':c['id'],'P4_only':sorted(set(a['first_key_recipe_actions'])-set(b['first_key_recipe_actions'])),
            'P3_only':sorted(set(b['first_key_recipe_actions'])-set(a['first_key_recipe_actions']))})
    atomic_json(OUT/'mechanistic_interpretation.json',{'knowledge_differences':knowledge,'productive_chains':chains,
        'positive_fixed_suffixes':sum(r['strict_local_improvement'] for r in checks),'all_suffix_tests':len(checks),
        'no_new_api_calls':True,'no_policy_changes':True,'verdict':'NO-GO; neither repaired version should replace frozen reference'})
    linked={scope:{m:sum(r['longest_linked_productive_chain'] for r in chains if r['method']==m and r['cohort']==scope) for m in ['P3','P4']} for scope in ['regression','new']}
    section=['## 为什么正确性回归通过，闭环反而下降','',
        '**可靠性计数改善没有转化为恢复。** 两个新版本未出现递归中止，失败拾取重复为0，容量拒绝和材料损耗下降；但把无法支持的候选替成 wait 后，仍可能停在原地。MRR 旧/新集合的显式无候选 wait 为64/73，RCR为80/39；确认同状态无进展次数分别为79/81和84/59。非法动作减少不能被解释为有效计划增加。','',
        '**bandage_roll：新增的容量死结。** 两个新版本第7索引拾起一根 sinew_cord 后，手中已有旧 bandage_roll，双手占满。它们随后未生成把手中绳子和地上剩余绳子一并转存的动作。P3在索引14、P4在索引13开始的同一真实状态，只把 wait 换成 `store 2 sinew_cord inventory`，再接相同的制作/拾取两步，就能完成目标；wait 分支失败。旧 Stage7 回归状态的库存容量已被检查，而新闭环在库存 load 未知时先拾一份，形成了不同状态。这解释了为什么旧快照验收不能覆盖新轨迹。','',
        '**fiend_alloy_scale：把默认需求下界当作充分数量。** 新控制器先仅取得1份 hellcoal_concentrate，只能生产1份 fiend_alloy。把当时批量改成2的反事实仍被引擎截成1，不能把失败简单归咎于 craft 参数。RCR后来已取得第二份煤，但索引18因“已拥有1份、默认需求1”阻止基础模型再次制作 fiend_alloy；此处改为真实 craft1，再接相同后续制作/收取可恢复。MRR在索引16先回已知煤所在地点、再接固定续动作同样可恢复。这些是公开需求尚未连接完整时的过度抑制，不证明任务缺乏恢复路径。','',
        '**stone_blade：已知规则仍未有效执行。** 新版本都发现了3条必要规则，但过早尝试根目标引发共享队列的材料配额增长，之后又受手部约束影响。P3索引29的真实状态其实已支持 `craft 1 stone_blade`，再拾取即可完成；实际选择 wait。P4索引26先把手持 knapped_edge 转存，接一次边刃制作及收取、根目标制作/收取即可完成。原检查点单纯改为 craft2 knapped_edge 仍只产1，批量独因假设被保留并否定。','',
        table(['任务/版本','索引','实际动作','诊断替代','相同续动作后 原/替代成功'],[[cases[r['case_id']]['goal']['name']+'/'+r['method'],r['index'],r['original_action'],r['alternative_action'],str(r['original_fixed_suffix']['goal'])+'/'+str(r['alternative_fixed_suffix']['goal'])] for r in checks]),'',
        '以上10个事后诊断全部保留，其中6个有固定续动作下的目标改善、4个没有。续动作由评测者给出，每条均在原40步余量以内并两次真实重放；不属于新的自主恢复，也不加入正式成功率。没有据此修复策略并补跑。','',
        '**B/C/D 的额外价值不足。** 新集合P4发现24/31条必要规则，P3为23/31；唯一集合差是 hunter_helm 中的 iron_bar。P4新轨迹上的 B 单开关比较有87次动作变化，开启后9次合法性更差，没有当步多披露必要名称或完成目标的增益，故不能把那1条跨轨迹差直接归因于B。C仅3次改变动作，1次改善当步合法性，没有新增恢复。D在全部P4记录状态中单独切换均不改变最终动作，其数量/收取决定被共同约束覆盖；这批没有额外资源收益证据。','',
        f"按真实依赖边衡量、拒绝制作后重新计数的连续正确制作链长度之和，旧集合 P3/P4 为 {linked['regression']['P3']}/{linked['regression']['P4']}，新集合为 {linked['new']['P3']}/{linked['new']['P4']}。这只是描述性执行指标，不支持C维持了更长恢复链的强主张。",'',
        f"新集合两者均0/8，P4费用 ${new['P4']['cost_usd']:.6f}，反而略低于P3的 ${new['P3']['cost_usd']:.6f}；P3还有1次旧集合格式中止。因此不能套用‘同成绩而MRR更稳定更便宜’这一条件。P4活跃控制表示更大，但没有新增成功。结论是两者都不替换冻结版本，不能只因MRR更简单就宣布其胜出。",'',
        '**中止与数据限制。** P3/brimite_blade_blank 的27个环境动作之后发生连续3次 JSON解析失败，归类为模型格式中止；不是递归中止。3293个HTTP响应均标注 deepseek-flash，其中21个格式无效（部分在固定重试内恢复），全计费用。新8例中1例匿名结构与更早任务重合，7例敏感性中三个冻结参考各1次成功、新版本仍各0次；结论不因此反转。','']
    for file in ['实验报告.md','机制归因.md']:
        p=REPORT/file;s=p.read_text();marker='\n## 为什么正确性回归通过，闭环反而下降'
        if marker in s:s=s.split(marker)[0]
        p.write_text(s.rstrip()+'\n\n'+'\n'.join(section)+'\n')

if __name__=='__main__':augment()
