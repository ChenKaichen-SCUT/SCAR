"""Generate all50 state evidence pages and complete paired comparison tables."""
import gzip
import json
from pathlib import Path

from scar_stage10.report import table

OUT=Path('results/stage12/diagnostic')
REPORT=Path('reports/stage12')


def block(value):
    return '```json\n'+json.dumps(value,ensure_ascii=False,indent=2)+'\n```'


def load(name):
    return json.loads((OUT/(name+'.json')).read_text())


def main():
    (REPORT/'states').mkdir(parents=True,exist_ok=True)
    states=load('states');metrics={(r['state_id'],r['method']):r for r in load('state_metrics')}
    native={r['state_id']:r for r in map(json.loads,gzip.open(OUT/'native_branches.jsonl.gz','rt'))}
    judgments=load('judgments');index=['# Stage 12 全部冻结状态与成败配对',
        '以下为局部知识发现诊断，成功计数不是整局恢复率。来源 index 从0计；所有状态、好坏候选及判断均保留。',
        table(['状态','family','来源 / index','公开抽样槽','候选','J0','J1','J2','J3'],
            [['['+s['state_id']+'](states/'+s['state_id']+'.md)',s['public_view']['target_action'],
              'Stage'+str(s['source_stage'])+' '+s['source_method']+' / '+str(s['source_index']),s['sampling_slot'],len(s['candidates'])]+
             [int(metrics[s['state_id'],m]['useful']) for m in ['J0','J1','J2','J3']] for s in states])]
    for s in states:
        sid=s['state_id'];b=native[sid]['branches'];page=['# '+sid+'：'+s['public_view']['target_action'],
            '来源：Stage'+str(s['source_stage'])+' / '+s['source_task']+' / index '+str(s['source_index'])+'。',
            '## 当时的公开观察、知识和 STM5',block({'observation':s['observation'],'public_knowledge':s['public_view'],'memory':s['memory']}),
            '## 原模型提案与两个规则参考',block({'historical_model_proposal':s['frozen_base_proposal'],'rule_actions':s['rule_actions'],'rule_decisions':s['rule_decisions']}),
            '## 同一公开候选池',block({'retained':s['candidates'],'cropped':s['cropped_candidates']}),
            '## 新模型判断（主判断与预先指定的重复分开）',block([j for j in judgments if j['state_id']==sid]),
            '## 四方法的主选择与真实结果',
            table(['方法','候选/提案','实际短分支','新增必要配方','原生拒绝数','停止原因'],
                [[m,metrics[sid,m]['selected_id'],[r['action'] for r in b[metrics[sid,m]['selected_id']]['trace']] if metrics[sid,m]['valid'] else [],
                  metrics[sid,m]['new_key_recipes'],metrics[sid,m]['rejections'],b[metrics[sid,m]['selected_id']]['stop'] if metrics[sid,m]['valid'] else 'invalid'] for m in ['J0','J1','J2','J3']]),
            '## 所有候选的真实分支（包括未选择候选）']
        for key,branch in b.items():
            page+=['<details><summary>'+key+' / '+branch['candidate']['kind']+' / '+branch['candidate']['target']+'</summary>',block(branch),'</details>']
        (REPORT/'states'/(sid+'.md')).write_text('\n\n'.join(page)+'\n')
    index+=['## 全部预先声明的配对比较',
        table(['比较','净有用首选','新增状态','丢失状态','净改善family数','family bootstrap95%区间'],
            [[p['comparison'],p['net_useful'],p['gains'],p['losses'],p['positive_net_families'],p['family_bootstrap_ci95']] for p in load('paired_comparisons')]),
        '## 冻结门槛逐项结果',block(load('gate'))]
    (REPORT/'全部状态与配对证据.md').write_text('\n\n'.join(index)+'\n')
    print(json.dumps({'state_pages':len(states),'api_calls':0}))


if __name__=='__main__':main()
