"""Distinguish first-time failures from already observed repeated rejection."""
from collections import Counter,defaultdict
from scar_stage31.metrics import audit
from scar_stage31.report import save,table
from .common import *

def main():
    offline();data=read(RESULTS/'offline_comparison.json');samples={x['id']:x for x in read(RESULTS/'samples.json')};timelines={}
    for seed in SEEDS:timelines[seed]=audit(rows(parent(seed)/'trajectory.jsonl.gz'))[0]
    cases=[];group=defaultdict(Counter)
    for x in data:
        if x['kind']!='rejected':continue
        a=timelines[x['seed']][x['step']-1];assert a['public_rejected'] and a['action']==x['candidate'];s=samples[x['id']]
        for category in a['rejection_categories']:
            g=group[category];g['samples']+=1;g['same_action_repeated_failure']+=a['repeated_failure'];g['warnings']+=x['warning'];g['changed']+=x['changed'];g['native_accepted_final']+=x['final_accepted']
        related=s['summary']['known_failed_actions']
        cases.append(dict(id=x['id'],seed=x['seed'],step=x['step'],categories=a['rejection_categories'],prior_unresolved_same_location_action_failure=a['repeated_failure'],
            previous_rejection_in_current_task_summary=any(e['action']==x['candidate'] for e in related),warning=x['warning'],risk=x['risk'],changed=x['changed'],final_accepted=x['final_accepted'],
            final_action=x['final_action'],candidate=x['candidate'],prediction=x['prediction']))
    repeat=[x for x in cases if x['prior_unresolved_same_location_action_failure']]
    summary=dict(rejected_samples=len(cases),repeated=len(repeat),repeated_final_accepted=sum(x['final_accepted'] for x in repeat),repeated_changed=sum(x['changed'] for x in repeat),
        previous_same_rejection_in_summary=sum(x['previous_rejection_in_current_task_summary'] for x in cases),
        summary_evidenced_final_accepted=sum(x['previous_rejection_in_current_task_summary'] and x['final_accepted'] for x in cases),
        low_risk_actual_rejection=sum(x['risk']=='low' for x in cases),categories={k:dict(v) for k,v in group.items()},new_model_calls=0)
    write(RESULTS/'offline_failure_coverage.json',dict(summary=summary,cases=cases))
    save(REPORTS/'离线失败覆盖补充.md',f'''# 离线失败覆盖与已知信息边界

70个原生拒绝样本中，按Stage31同地点同动作未解决失败口径，有{summary['repeated']}个重复失败，其中最终动作改变{summary['repeated_changed']}个、原生接受{summary['repeated_final_accepted']}个。有限任务摘要中显式带有同动作失败记录的样本为{summary['previous_same_rejection_in_summary']}个，其中最终接受{summary['summary_evidenced_final_accepted']}个。二者不是同一口径：摘要最多32个历史转移中8个匹配事件，旧同地点失败可能不在摘要，原生STM又可能单独保留反馈。

{table(['失败类别','样本','既有重复失败','warning','改变','最终接受'],[[k,v['samples'],v['same_action_repeated_failure'],v['warnings'],v['changed'],v['native_accepted_final']] for k,v in sorted(group.items())])}

类别按公开反馈匹配，可重叠；不相加成独立样本。low风险预测对应实际原候选被拒共有{summary['low_risk_actual_rejection']}个，但risk指对目标的损害程度，不是动作成功概率，因此不能直接叫这些全部预测错误。未公开的首次前置条件不能通过隐藏规则补给模型，也不能拿事后知道失败当作模型当时应该知道。

逐样本类别、历史失败关系、任务摘要可见性与预测保存在 offline_failure_coverage.json。该补充是零API事后分析，不修改线上摘要或算法，也不据此删除困难样本。
''')
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
