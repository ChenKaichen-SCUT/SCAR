"""Public-prefix-only paper hierarchies. These are never run or given to a model."""
import gzip
import json
import re
from .common import *

def main():
    offline();trees=[];gaps=[]
    for ident in CASES:
        s,rr,qq,path,lines=data(ident,'OracleRecovery')
        prefix=json.loads(gzip.decompress((ROOT/f'results/stage27/checkpoints/{ident}/public_prefix.json.gz').read_bytes()))
        assert all(p['step']<=s['step'] for p in prefix)
        evidence=[dict(step=s['step'],quote=s['failure_reason'],source='saved_failure_feedback')]
        assert s['failure_reason'] in s['post_failure_observation']['text']
        nodes=[dict(id='parent',parent=None,level=0,goal=s['current_goal'],source='original accepted agent goal; not necessarily the whole game objective'),
            dict(id='attempt',parent='parent',level=1,goal='使原先尝试的动作可行：'+s['candidate_action'],relation='chosen_method_not_proven_necessary',
                alternative='原方法是否必要未知；合法替代或生存优先可能合理。'),
            dict(id='recovery',parent='attempt',level=2,goal=CASES[ident],evidence=[0],completion='以公开反馈/实际成功核验缺口，不以目标标题为完成条件。')]
        typ=s['failure_type'];unknown=[]
        if typ in ['missing_lockpick_tool','missing_writing_tool','missing_workbench','missing_furnace']:
            nodes.append(dict(id='source',parent='recovery',level=3,goal='确认所需工具或设施的公开可获得性/可访问性',evidence=[0],kind='information_requirement'))
            unknown.append('这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。')
        elif typ in ['hand_capacity','container_capacity']:
            nodes.append(dict(id='space',parent='recovery',level=3,goal='使已被拒绝的容量约束得到满足，同时重新核验待保留资源',evidence=[0],kind='resource_condition'))
            unknown.append('目标关系本身不决定丢弃/存储哪个物品、能否访问容器或是否牺牲照明。')
        target=s['candidate_action'].split()[-1] if s['candidate_action'].startswith('craft ') else None
        recipes=[]
        if target:
            for p in prefix:
                for line in p['feedback']['text'].splitlines():
                    for m in re.finditer(r'\b'+re.escape(target)+r' \(([^()]*)\)',line):
                        recipes.append(dict(step=p['step'],quote=m.group(0),full_line=line,source='public_prefix_feedback'))
            # Prefer a disclosed quantity recipe; do not infer hidden quantities.
            precise=[e for e in recipes if re.search(r'\d',e['quote'])]
            recipe=(precise or recipes)[-1] if recipes else None
            if recipe:
                evidence.append(recipe);content=recipe['quote'].split('(',1)[1].rstrip(')')
                for i,ingredient in enumerate(content.split(', ')):
                    nodes.append(dict(id=f'component_{i}',parent='attempt',level=2,goal='核验公开材料条件：'+ingredient,evidence=[len(evidence)-1],kind='public_recipe_condition',
                        note='需要重新核验当前持有/可达状态；过去公开并不等于当前拥有。'))
                initial='\n'.join(m['content'] for m in qq[0]['messages'])
                gaps.append(dict(id=ident,target=target,recipe=recipe['quote'],public_step=recipe['step'],initial_request_step=qq[0]['step'],
                    exact_recipe_in_initial_context=recipe['quote'] in initial,request_id=qq[0]['request_id']))
            else:
                nodes.append(dict(id='unknown_recipe',parent='attempt',level=2,goal='获取原制作动作的公开配方条件',kind='unknown_information',evidence=[0]))
                unknown.append('未从截止检查点的公开反馈提取到明确目标配方；不填入隐藏完整配方。')
            unknown.append('列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。')
        for e in evidence:
            assert e['step']<=s['step']
            assert e['quote'] in s['post_failure_observation']['text'] or any(e['quote'] in p['feedback']['text'] for p in prefix if p['step']==e['step'])
        trees.append(dict(id=ident,knowledge_cutoff=s['step'],kind='paper_counterfactual_not_executed',nodes=nodes,evidence=evidence,unknowns=unknown,
            boundary='No action sequence, hidden rule, resource location or reward oracle. A different hierarchy does not by itself choose actions or validate facts.',
            prompt_information_confound='如果把旧配方加入模型 Stack，但原模型上下文没有该配方，就同时改变了信息量，不能把可能收益全部归于层级结构。'))
    for ident,step,needle in [('oracle079_a165',173,'star_metal_sword (1 star_metal_blade, 1 wooden_rod, 1 cloth_strap, 1 goblin_eye)'),
                              ('oracle032_a256',274,'It is too dark to see anything here.')]:
        s,rr,qq,path,lines=data(ident,'OracleRecovery');q=[q for q in qq if q['step']==step][-1]
        gaps.append(dict(id=ident,request_step=step,public_fact=needle,exact_fact_in_accepted_context=needle in '\n'.join(m['content'] for m in q['messages']),request_id=q['request_id'],
            control_summary=next(r for r in rr if r['step']==step)['decision']['attempts'][-1]['summary']['current_goal']))
    write(RESULTS/'paper_goal_stacks.json',trees);write(RESULTS/'public_knowledge_context_audit.json',gaps)
    print(json.dumps(dict(paper_trees=len(trees),new_model_calls=0,oracle_stack_model_replay_executed=False)),flush=True)

if __name__=='__main__':main()
