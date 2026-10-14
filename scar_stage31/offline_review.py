"""Coverage and counterexamples, including unflagged historical errors."""
from collections import Counter
from agents.rec_v1.state import failed,visible
from .common import *

EXAMPLES=[
 ('oracle037_a122','OriginalRecovery',147,'命中既往照明损失；Stage29 已验证保留光源仍能拾取铁条的局部替代。'),
 ('oracle079_a165','OriginalRecovery',173,'命中与公开配方矛盾的组件丢弃；本轮制作探针事前已失败，不能声称防止了剑制作损失。'),
 ('oracle079_a165','OracleGoalStack',173,'组件关系仍在但丢照明，命中历史条件关联。'),
 ('parent_a060','OracleGoalStack',70,'命中木板保有风险；尚缺其他前置条件，未隔离长期损害。'),
 ('parent_a060','OracleGoalStack',77,'命中转存光源后变暗的经验条件风险。'),
 ('parent_a136','OriginalRecovery',224,'负例：预测移走光源，但实际容器已满，转存失败，未丢照明。'),
 ('parent_a270','OracleGoalStack',271,'漏检：丢弃包内 cloth，理由却以为释放手部空间；没有唯一配方目标。'),
 ('parent_a270','OracleGoalStack',272,'同一容量语义误解继续；不是 Tracker 已保存全部事实就必然能判定。'),
 ('parent_a270','OracleGoalStack',273,'继续丢包内材料，仍 ALLOW；REC 没有全容量/恢复目标模型。'),
 ('parent_a270','OracleGoalStack',274,'原模型认为容器仍满而离开；REC 不识别所有恢复目标冲突。'),
 ('parent_a136','OracleGoalStack',138,'漏检持有/包内对象混淆。'),
 ('parent_a235','OracleGoalStack',236,'公开旧 torch 配方可以进入 Tracker，但错误收集 cloth 本身不触发四条约束；不能宣称拦截无关采集。'),
 ('parent_a235','OracleGoalStack',237,'继续把 cloth 转存满容器，首次此状态尝试可 ALLOW。')]

def main():
    offline();rr=rows(RESULTS/'offline_action_audit.jsonl.gz');native=read(RESULTS/'offline_native_validation.json')
    lookup={(x['id'],x['variant'],x['step']):x for x in rr};v={(x['id'],x['variant'],x['step']):x for x in native['cases']}
    c=Counter();episodes=[]
    for x in rr:
        kinds={z['kind'] for z in x['assessment']['reasons']};bad=failed(x['feedback']);c['rejected_actions']+=bad
        dark=visible(x['observation']) and not visible(x['feedback']) and 'too dark to see' in x['feedback']['text'].lower()
        if dark and x['action'].startswith(('drop ','store ','unequip ')):
            c['all_removal_visibility_losses']+=1;c['flagged_removal_visibility_losses']+='observed_condition_loss_risk' in kinds
            episodes.append(dict(id=x['id'],variant=x['variant'],step=x['step'],detected='observed_condition_loss_risk' in kinds,source=x['source'],line=x['line']))
        if 'required_resource_custody_risk' in kinds:c['resource_risks_actually_rejected']+=bad;c['resource_risks_actually_accepted']+=not bad
        if bad and kinds:c['any_flag_on_rejected_action']+=1
    examples=[dict(id=i,variant=var,step=n,note=note,evidence=lookup[i,var,n],native_validation=v.get((i,var,n))) for i,var,n,note in EXAMPLES]
    write(RESULTS/'offline_coverage_review.json',dict(counts=dict(c),visibility_loss_events=episodes,
        local_visibility_effects_confirmed=sum(x['visibility_action_effect_confirmed'] for x in native['cases']),
        resource_probe_verdicts=dict(Counter(x['resource_or_facility_verdict'] for x in native['cases'] if x['resource_or_facility_verdict'])),
        examples=examples,reviewer='Assistant inspection of archived public evidence and native probes; not blind independent human labeling.',
        unbiased_precision_recall_available=False,reason='No exhaustive task-harm labels; resource risks are mostly unresolved and this is the development corpus.',new_model_calls=0))
    print(json.dumps(dict(c)),flush=True)

if __name__=='__main__':main()
