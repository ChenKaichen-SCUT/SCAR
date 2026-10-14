"""Evidence links for prior failures, paired divergence and every intervention."""
from collections import Counter
from .common import *
from .metrics import source,goal,audit

OLD_CASES={
 31:'缺少开锁工具：公开动作前置条件；不能从失败凭空生成工具获取路线。',
 32:'同样缺开锁工具再次尝试：检查重复失败是否被识别。',
 54:'满手拿铁条：容量与保留照明的冲突，配方保护不自动解决容量配置。',
 60:'制作木板缺工作台：公开设施需求可登记，但 REC 不提供工作台路线。',
 79:'战斗阻断离开：NPC 行为变化，不能把相同动作拒绝永久化。',
 85:'错误装备不可装备光源：首次规则未知；REC 没有通用工具可装备性知识。',
 113:'手满无法从包取木杆：非制作目标，资源需求绑定通常不覆盖。',
 136:'写字缺工具：要求存在但未生成写字任务的通用条件图。',
 235:'制作光源材料不足：可重现公开旧配方；首次失败本身不一定触发动作约束。',
 270:'容器容量不足：不能把公开库存保存等同于完整容量推理。'}

def evidence(folder,rr,qq,n):
    r=next(r for r in rr if r['step']==n)
    return dict(source=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),line=rr.index(r)+1,step=n,action=r['action'],
        proposal=r['decision']['attempts'][-1]['proposal'],observation=r['observation'],feedback=r['feedback'],
        state_hash_before=r['state_hash_before'],state_hash=r['state_hash'],scores=r['scores'],
        request_ids=[q['request_id'] for q in qq if q['step']==n])

def main():
    offline();folder=baseline(42);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');aa,_=audit(rr)
    old=[dict(step=n,note=note,evidence=evidence(folder,rr,qq,n),shadow=aa[n-1]['shadow_assessment']) for n,note in OLD_CASES.items()]
    pairs=read(RESULTS/'paired_comparison.json');out=[]
    for p in pairs:
        branches={}
        for method in ['AGC-v2','REC']:
            folder=source(p['seed'],method);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');a,_=audit(rr)
            selected=set()
            if p['first_action_divergence']:selected.add(p['first_action_divergence'])
            # Deterministic, exhaustive intervention windows plus first/last
            # witnesses of each measured failure type, not cherry-picked wins.
            for r in rr:
                if any(x['check']['decision']=='RECONSIDER' for x in r['decision'].get('rec_records',[])):
                    selected.update(n for n in range(max(1,r['step']-1),min(len(rr),r['step']+1)+1))
            for flag in ['public_rejected','repeated_failure','visibility_lost','removal_visibility_lost','recovery','reacquisition']:
                matches=[x['step'] for x in a if x.get(flag)]
                if matches:selected.update([matches[0],matches[-1]])
            selected.update(r['step'] for r in rr if r['reward']['quest'])
            selected.update(range(max(1,len(rr)-3),len(rr)+1))
            terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
            branches[method]=dict(evidence=[evidence(folder,rr,qq,n) for n in sorted(selected)],terminal=terminal,
                rejection_categories=dict(Counter(c for x in a for c in x['rejection_categories'])))
        out.append(dict(seed=p['seed'],first_action_divergence=p['first_action_divergence'],branches=branches))
    write(RESULTS/'case_review.json',dict(stage25_cases=old,paired_cases=out,
        selection='All REC intervention windows and terminal records; deterministic first/last public metric witnesses; all quest increments; paired first action divergence.',
        new_model_calls=0,strict_long_horizon_counterfactual=False))
    print(json.dumps(dict(old_cases=len(old),pairs=len(out))),flush=True)

if __name__=='__main__':main()
