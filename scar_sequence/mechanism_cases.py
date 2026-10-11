"""Post-hoc explanatory cases and zero-API physical counterfactuals.

Selected for explicit success/failure contrasts, never used to tune frozen policy
or change denominators. Positive path replay is not a new model result.
"""
import argparse
import contextlib
import gzip
import json
from pathlib import Path
import tempfile
from scar.environment import restore,state_digest
from scar.diagnostics.build import transition
from scar_sequence.supplement import goal_reached
from scar.io import atomic_json


DESCRIPTIONS={
 'sequence-3d1ba557c7dabb5d':'已示范 iron_scale：SRP 批量制作两个 iron_bar，再依次 iron_sheet→iron_scale；FIFO 逐个制作也成功，说明普通队列已能维护链。STM 多次直接重试终产物，没有补齐中间链。',
 'sequence-7ef74a089f1ce41d':'已示范 machete：SRP 第 37 索引已经制作目标，但第 39 索引只把原先手持那件存入背包；40 步截止仍少收地面新产物。属于运输/检查/取物开销，不能归因于未知规则。',
 'sequence-48401b39ba565b57':'未知 bandage_roll：SRP/FIFO 先 craft 1 sinew_cord，消耗一整份 cloth，只得到一份 cord；STM 用 craft 2 一次获得两份，保留另一份 cloth 完成目标。作用量与批次相关，简单线性单份成本不足。',
 'sequence-697aafaff2ad5b74':'未知 fiend_rivet：SRP 的基础 Agent 真正做出 fiend_strip，随后检查发现最终配方并完成；FIFO 的基础建议转为直接重试 fiend_rivet。唯一 SRP/FIFO 胜负不一致案例包含模型探索差异，不能单独证明依赖图必要。',
 'sequence-6403512cf4de780d':'未知 brass_blank：公开检查现有 blank 只介绍其下游 brass_key；原材料检查介绍 rustbar，缺少连接到目标的已观察反向配方。SRP/FIFO 后续依赖基础探索，多次主线交谈及存取，没有持续发现/完成缺失中间转换。',
}


def replay_branch(path,actions,goal):
    endings=[];trace=[]
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env=restore(path,tmp);current=[]
            for action in actions:
                row=transition(env,action);current.append(dict(row,state_hash=state_digest(env),goal=goal_reached(env,goal)))
            endings.append(state_digest(env));trace=current
    return {'actions':actions,'trace':trace,'goal':trace[-1]['goal'],'independently_replayed_twice':endings[0]==endings[1],
            'final_hash':endings[-1]}


def build(runtime,output='results/sequence'):
    root=Path(runtime);out=Path(output);cases={r['id']:r for r in json.loads((out/'dataset/cases.json').read_text())}
    data={key:{'case_id':key,'interpretation':value,'selection':'posthoc illustrative, not independent test or policy tuning','methods':{}} for key,value in DESCRIPTIONS.items()}
    for method in ['ShortTermMemoryAgent','SimpleFailureRecovery','SCARV3Agent','ResourceFIFO','SRP']:
        with gzip.open(out/f'trajectories_{method}.jsonl.gz','rt') as f:
            for episode in map(json.loads,f):
                if episode['case_id'] not in data:continue
                data[episode['case_id']]['methods'][method]={'recovery_steps':episode['summary']['recovery_steps'],
                    'actions':[{'index':r['index'],'proposed':r['proposed_action'],'actual':r['executed_action'],
                        'rejected':r['semantic_rejection'],'feedback':r['action_rule_feedback'],
                        'goal':r['diagnostic_goal_reached'],'physical_before':r['physical_before'],'physical_after':r['physical_after']}
                        for r in episode['rows']]}
    tasks=json.loads((root/'tasks.json').read_text())
    task=lambda cid:next(t for t in tasks if t['id']==cid and t['algorithm']=='SRP')
    cid='sequence-48401b39ba565b57';run=root/'runs'/task(cid)['task_id']
    before=run/'steps/0006/environment.pkl'
    variants=[]
    for amount in [1,2]:
        actions=[f'craft {amount} sinew_cord','inspect inventory','store 2 sinew_cord inventory','craft 1 bandage_roll','pick up bandage_roll']
        variants.append(replay_branch(before,actions,cases[cid]['goal']))
    data[cid]['batch_size_counterfactual']={'starting_before_index':6,'variants':variants,
        'same_suffix':True,'api_calls':0,'interpretation':'A verified batch-effect example. An informed deterministic batch rule could also solve it; online-learning necessity is not established.'}
    cid='sequence-7ef74a089f1ce41d';run=root/'runs'/task(cid)['task_id']
    data[cid]['after_cap_counterfactual']=replay_branch(run/'steps/0040/environment.pkl',['store 1 machete inventory'],cases[cid]['goal'])
    data[cid]['after_cap_interpretation']='One zero-API diagnostic branch at the capped state. Formal Recovery@40 remains failure; this is not a 41-step model evaluation.'
    atomic_json(out/'typical_cases.json',list(data.values()))
    print(json.dumps({'cases':len(data),'batch_goal_results':[r['goal'] for r in variants],
                      'machete_one_extra_action':data[cid]['after_cap_counterfactual']['goal'],'api_calls':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',default='results/sequence');a=p.parse_args()
    with open(Path(a.runtime)/'mechanism_cases.log','w') as log,contextlib.redirect_stderr(log):build(a.runtime,a.output)
